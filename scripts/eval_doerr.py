#!/usr/bin/env python3
"""
DoErr Evaluation Script for CCB-NL checkpoint.

Evaluates the trained RPJ Brain on held-out CCB-NL problems to compute:
- DoErr = (1/Q) Σ |μ̂_do - μ_do|
- Target: DoErr ≤ 0.05

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


def evaluate_doerr(
    checkpoint_path: str,
    num_envs: int = 4096,
    num_episodes: int = 100,
    device: str = "cuda",
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

    # Create brain with same config
    config = RPJConfig(
        obs_dim=2,
        action_bytes=1,
        hidden_dim=512,
        k_max=4,
        enable_plasticity=False,
        enable_sleep=False,
    )
    brain = RPJBrain(config).to(device)
    brain.load_state_dict(state_dict, strict=False)
    brain.eval()

    print(f"  Loaded {brain.count_parameters()['total']:,} parameters")

    # Create CCB-NL environment (nonlinear = harder task)
    print(f"\n[2/3] Creating CCB-NL environment...")
    env = TorchCCBEnvironment(
        num_envs=num_envs,
        device=device,
        nonlinear=True,  # CCB-NL mode
    )
    print(f"  Mode: CCB-NL (Y = ReLU(b_X*X² + b_U*U))")
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
    print(f"  Target: ≤ 0.05")
    print(f"  Status: {'✅ PASS' if final_doerr <= 0.05 else '❌ FAIL'}")

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
        print(f"\n  ⚠️  WARNING: Predictions appear COLLAPSED (std < 0.01)")
        print(f"     Agent is outputting nearly constant values")

    # Check correlation
    correlation = torch.corrcoef(torch.stack([all_pred, all_true]))[0, 1].item()
    print(f"\n  Prediction-Truth correlation: {correlation:.4f}")

    return final_doerr


def main():
    parser = argparse.ArgumentParser(description="DoErr Evaluation")
    parser.add_argument("--checkpoint", type=str,
                        default="results/checkpoint_final_099840.pt",
                        help="Path to checkpoint")
    parser.add_argument("--num-envs", type=int, default=4096,
                        help="Number of parallel environments")
    parser.add_argument("--num-episodes", type=int, default=100,
                        help="Number of evaluation episodes")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    doerr = evaluate_doerr(
        checkpoint_path=args.checkpoint,
        num_envs=args.num_envs,
        num_episodes=args.num_episodes,
        device=device,
    )

    print(f"\n>>> FINAL VERDICT: DoErr = {doerr:.4f}")
    if doerr <= 0.05:
        print(">>> STATUS: PASS ✅")
    else:
        print(f">>> STATUS: FAIL ❌ (10x above target)" if doerr > 0.5 else f">>> STATUS: FAIL ❌")


if __name__ == "__main__":
    main()
