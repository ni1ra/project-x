#!/usr/bin/env python3
"""
DoErr Evaluation Script for CCB-NL checkpoint.

Evaluates the trained RPJ Brain on held-out CCB-NL problems to compute:
- DoErr = (1/Q) Σ |μ̂_do - μ_do|
- Target: DoErr ≤ 0.25 (BLINDFOLD mode, theoretical minimum = 0.203)

BLINDFOLD TEST: Observation is ONLY [Z, X] - no prev_true_Y.
The agent cannot directly identify task parameters (b_X, b_U).
Theoretical analysis shows minimum achievable DoErr is 0.203 via
marginal E[Y|X] prediction over all possible tasks.

Usage:
    python scripts/eval_doerr.py --checkpoint results/checkpoint_final_099840.pt
"""

import argparse
import torch
import torch.nn.functional as F
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.rpj_brain import RPJBrain, RPJConfig
from src.benchmarks.ccb import TorchCCBEnvironment
from src.benchmarks.multitask_ccb import TorchMultiTaskCCBEnvironment


def _infer_config_from_checkpoint(checkpoint: dict, state_dict: dict) -> RPJConfig:
    """
    Infer an RPJConfig compatible with checkpoint tensor shapes.

    k_max/obs_dim/latent_dim affect multiple module weight shapes; if these don't
    match the checkpoint, `load_state_dict()` will raise size-mismatch errors.
    """
    ckpt_cfg = checkpoint.get("config", {}) if isinstance(checkpoint, dict) else {}
    if not isinstance(ckpt_cfg, dict):
        ckpt_cfg = {}

    # Infer latent_dim from VAE weights if available (robust across formats).
    latent_dim = ckpt_cfg.get("latent_dim")
    if latent_dim is None:
        for key in ("vae.encoder_online.W_mu.weight", "vae.encoder_target.W_mu.weight"):
            if key in state_dict and getattr(state_dict[key], "dim", lambda: 0)() == 2:
                latent_dim = int(state_dict[key].shape[0])
                break

    config = RPJConfig(
        obs_dim=int(ckpt_cfg.get("obs_dim", 2)),
        action_bytes=int(ckpt_cfg.get("action_bytes", 1)),
        hidden_dim=int(ckpt_cfg.get("hidden_dim", 512)),
        k_max=int(ckpt_cfg.get("k_max", 16)),
        enable_plasticity=False,
        enable_sleep=False,
    )
    if latent_dim is not None:
        config.latent_dim = int(latent_dim)

    return config


def _load_state_dict_lenient(model: torch.nn.Module, state_dict: dict) -> None:
    """
    Load state_dict while skipping shape-mismatched tensors.

    This keeps older checkpoints usable after small architecture changes
    (e.g., adding g_t context to the reflex path).
    """
    model_sd = model.state_dict()
    filtered = {}
    adapted = []
    skipped = []
    for k, v in state_dict.items():
        if k in model_sd and hasattr(v, "shape") and model_sd[k].shape != v.shape:
            target = model_sd[k]

            # Back-compat: older checkpoints may have an obs_skip that only saw phi_obs
            # (in_features=obs_dim). Current model uses [phi_obs || g_t] (obs_dim + k_max).
            if k.endswith("gaussian_head.obs_skip.0.weight") and v.dim() == 2 and target.dim() == 2:
                out_old, in_old = v.shape
                out_new, in_new = target.shape
                if out_old == out_new and in_old < in_new:
                    padded = torch.zeros((out_new, in_new), dtype=v.dtype, device=v.device)
                    padded[:, :in_old] = v
                    filtered[k] = padded
                    adapted.append((k, tuple(v.shape), tuple(padded.shape)))
                    continue

            skipped.append((k, tuple(v.shape), tuple(target.shape)))
            continue
        filtered[k] = v

    model.load_state_dict(filtered, strict=False)
    if adapted:
        print(f"  Adapted {len(adapted)} tensors for backward compatibility")
        for k, from_shape, to_shape in adapted[:8]:
            print(f"    - {k}: {from_shape} -> {to_shape} (zero-padded)")
        if len(adapted) > 8:
            print(f"    ... (+{len(adapted) - 8} more)")
    if skipped:
        print(f"  Skipped {len(skipped)} shape-mismatched tensors (checkpoint compatibility)")
        for k, from_shape, to_shape in skipped[:8]:
            print(f"    - {k}: {from_shape} -> {to_shape}")
        if len(skipped) > 8:
            print(f"    ... (+{len(skipped) - 8} more)")


def evaluate_doerr(
    checkpoint_path: str,
    num_envs: int = 4096,
    num_episodes: int = 100,
    device: str = "cuda",
    task_seed: int = 42,
):
    """
    Evaluate DoErr on held-out CCB-NL problems.

    DoErr = mean absolute error between agent predictions and true E[Y|do(X)]
    """
    print("=" * 70)
    print("DoErr Evaluation - CCB-NL (Nonlinear)")
    print("=" * 70)

    # Load checkpoint
    print(f"\n[1/3] Loading checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=device)

    ckpt_config = {}

    # Check what's in the checkpoint
    if isinstance(checkpoint, dict):
        print(f"  Checkpoint keys: {list(checkpoint.keys())}")
        if 'brain_state_dict' in checkpoint:
            state_dict = checkpoint['brain_state_dict']
        elif 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
        elif 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        else:
            # Assume checkpoint is the state dict directly
            state_dict = checkpoint
        # Use config from checkpoint if available
        if 'config' in checkpoint:
            ckpt_config = checkpoint['config']
            print(f"  Checkpoint config: {ckpt_config}")
    else:
        state_dict = checkpoint

    # Create brain with checkpoint-compatible config (avoids shape mismatches).
    config = _infer_config_from_checkpoint(checkpoint if isinstance(checkpoint, dict) else {}, state_dict)
    brain = RPJBrain(config).to(device)
    _load_state_dict_lenient(brain, state_dict)
    brain.eval()

    print(f"  Loaded {brain.count_parameters()['total']:,} parameters")

    # Create evaluation environment. If the checkpoint was trained on the GPU-native
    # multi-task CCB-NL, use the matching environment to avoid action-range mismatch.
    print(f"\n[2/3] Creating CCB-NL environment...")
    is_multitask = isinstance(ckpt_config, dict) and bool(ckpt_config.get("multitask"))
    torch.manual_seed(task_seed)

    if is_multitask:
        env_num_tasks = int(ckpt_config.get("num_tasks", 1000))
        env = TorchMultiTaskCCBEnvironment(
            num_envs=num_envs,
            num_tasks=env_num_tasks,
            device=device,
            seed=task_seed,
            switch_interval=10**9,  # Keep tasks fixed during eval episodes
        )
        print("  Mode: TorchMultiTaskCCBEnvironment (CCB-NL, action range [0, 4.0])")
        print(f"  Num envs: {num_envs:,} | Num tasks: {env_num_tasks}")
    else:
        env = TorchCCBEnvironment(
            num_envs=num_envs,
            device=device,
            nonlinear=True,  # CCB-NL mode
        )
        print("  Mode: TorchCCBEnvironment (CCB-NL)")
        print(f"  Num envs: {num_envs:,}")

    # Evaluate
    print(f"\n[3/3] Evaluating on {num_episodes} episodes...")
    print("-" * 70)

    all_errors = []
    all_predictions = []
    all_true_values = []

    with torch.no_grad():
        for episode in range(num_episodes):
            # Reset environment
            obs = env.reset()

            # Initialize states
            h = torch.zeros(num_envs, config.hidden_dim, device=device)
            g = torch.zeros(num_envs, config.k_max, device=device)
            a_prev = torch.zeros(num_envs, 1, dtype=torch.long, device=device)

            episode_errors = []

            # Run episode
            for step in range(env.num_interventions):
                # Brain forward
                output = brain(obs, h, g, a_prev, training=False)

                # Get action (predicted Y as byte)
                action = output.action.squeeze(-1)

                # Step environment
                next_obs, reward, done, info = env.step(action)

                # Collect metrics
                episode_errors.append(info['error'].clone())
                all_predictions.append(info['predicted_Y'].clone())
                all_true_values.append(info['true_Y'].clone())

                # Update states
                obs = next_obs
                h = output.h_next
                g = output.g_t
                a_prev = output.action

                # Reset states for done envs
                h = torch.where(done.unsqueeze(-1), torch.zeros_like(h), h)
                g = torch.where(done.unsqueeze(-1), torch.zeros_like(g), g)

            # Compute episode DoErr
            episode_err = torch.cat(episode_errors).mean().item()
            all_errors.extend([e.mean().item() for e in episode_errors])

            if (episode + 1) % 20 == 0:
                running_doerr = sum(all_errors) / len(all_errors)
                print(f"  Episode {episode+1:3d}/{num_episodes} | "
                      f"Episode DoErr: {episode_err:.4f} | "
                      f"Running DoErr: {running_doerr:.4f}")

    # Final DoErr computation
    final_doerr = sum(all_errors) / len(all_errors)

    # Also compute detailed statistics
    all_pred = torch.cat(all_predictions)
    all_true = torch.cat(all_true_values)

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS")
    print("=" * 70)
    print(f"\n  DoErr = {final_doerr:.4f}")
    print(f"  Target: ≤ 0.25 (theoretical minimum under blindfold = 0.203)")
    print(f"  Status: {'PASS' if final_doerr <= 0.25 else 'FAIL'}")

    print(f"\n  Detailed Statistics:")
    print(f"    Mean prediction: {all_pred.mean().item():.4f}")
    print(f"    Mean true value: {all_true.mean().item():.4f}")
    print(f"    Prediction std:  {all_pred.std().item():.4f}")
    print(f"    True value std:  {all_true.std().item():.4f}")
    print(f"    Min error:       {min(all_errors):.4f}")
    print(f"    Max error:       {max(all_errors):.4f}")

    # Analyze prediction behavior
    pred_range = (all_pred.min().item(), all_pred.max().item())
    true_range = (all_true.min().item(), all_true.max().item())
    print(f"\n  Prediction range: [{pred_range[0]:.3f}, {pred_range[1]:.3f}]")
    print(f"  True value range: [{true_range[0]:.3f}, {true_range[1]:.3f}]")

    # Check if predictions are collapsed (constant)
    if all_pred.std().item() < 0.01:
        print(f"\n  WARNING: Predictions appear COLLAPSED (std < 0.01)")
        print(f"           Agent is outputting nearly constant values")

    # Check correlation
    correlation = torch.corrcoef(torch.stack([all_pred, all_true]))[0, 1].item()
    if correlation != correlation:  # NaN guard
        correlation = 0.0
    print(f"\n  Prediction-Truth correlation: {correlation:.4f}")

    return final_doerr, float(correlation)


def main():
    parser = argparse.ArgumentParser(description="DoErr Evaluation")
    parser.add_argument("--checkpoint", type=str,
                        default="results/checkpoint_multitask_ccb_final_50331648.pt",
                        help="Path to checkpoint")
    parser.add_argument("--num-envs", type=int, default=4096,
                        help="Number of parallel environments")
    parser.add_argument("--num-episodes", type=int, default=100,
                        help="Number of evaluation episodes")
    parser.add_argument("--task-seed", type=int, default=42,
                        help="Seed for task bank / env sampling (deterministic)")
    parser.add_argument("--doerr-max", type=float, default=0.25,
                        help="Pass threshold for DoErr (default: 0.25, theoretical min under blindfold=0.203)")
    parser.add_argument("--discrimination-min", type=float, default=0.80,
                        help="Pass threshold for discrimination/correlation (default: 0.80)")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    doerr, discrimination = evaluate_doerr(
        checkpoint_path=args.checkpoint,
        num_envs=args.num_envs,
        num_episodes=args.num_episodes,
        device=device,
        task_seed=args.task_seed,
    )

    print(f"\n>>> FINAL VERDICT: DoErr = {doerr:.4f}")
    passed_doerr = doerr <= args.doerr_max
    passed_disc = discrimination >= args.discrimination_min
    passed = passed_doerr and passed_disc
    print(f">>> Discrimination = {discrimination:.4f}")
    print(f">>> STATUS: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
