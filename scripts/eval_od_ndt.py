#!/usr/bin/env python3
"""
OD-NDT Evaluation Script

Evaluates the RPJ Brain on the One-Demonstration No-Data Transfer protocol
using the MultiTaskCCB environment.

Key metrics:
- SR_novel: Success rate on held-out tasks
- Transfer T: SR_novel / SR_train
- K_eff during evaluation: Tests "Persistent Emergence" hypothesis

The main hypothesis is that K_eff will STAY ELEVATED during OD-NDT because
the task diversity requires persistent plasticity gating, unlike single-task
CCB where K_eff correctly habituates.

Usage:
    python scripts/eval_od_ndt.py --checkpoint results/checkpoint_ccb_nl_final_50331648.pt

Reference: BLUEPRINT.md Section 4.3
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import torch
import torch.nn as nn
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.rpj_brain import RPJBrain, RPJConfig
from src.benchmarks.multitask_ccb import (
    MultiTaskCCBEnvironment,
    MultiTaskConfig,
    create_multitask_ccb,
    get_demo_and_test_task_ids,
)
from src.benchmarks.od_ndt import ODNDTConfig


@dataclass
class EmergenceMetrics:
    """Metrics for tracking emergence during OD-NDT evaluation."""
    k_eff_values: List[float]       # K_eff at each step
    g_l1_values: List[float]        # g_t L1 norm at each step
    step_errors: List[float]        # Prediction error at each step
    task_successes: List[bool]      # Success per task


def compute_k_eff(g_t: torch.Tensor) -> float:
    """
    Compute effective neuromodulator count via participation ratio.

    K_eff = (Σ|g_i|)² / Σ(g_i²)

    Ranges from 1 (single scalar active) to k_max (all equally active).
    """
    g_abs = g_t.abs()
    l1 = g_abs.sum(dim=-1)
    l2_sq = (g_abs ** 2).sum(dim=-1)

    k_eff = (l1 ** 2) / (l2_sq + 1e-8)
    return k_eff.mean().item()


def load_checkpoint(checkpoint_path: str, device: str = "cpu") -> Tuple[RPJBrain, Dict]:
    """Load a trained RPJBrain from checkpoint."""
    print(f"Loading checkpoint: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location=device)

    # Extract config from checkpoint if available
    if 'config' in checkpoint:
        config_dict = checkpoint['config']
        if isinstance(config_dict, dict):
            # Convert dict to RPJConfig
            config = RPJConfig(
                obs_dim=config_dict.get('obs_dim', 2),
                action_bytes=config_dict.get('action_bytes', 1),
                hidden_dim=config_dict.get('hidden_dim', 512),
                k_max=config_dict.get('k_max', 16),
                lambda_g=config_dict.get('lambda_g', 0.01),
            )
        else:
            config = config_dict
    else:
        # Use default config matching CCB-NL training
        config = RPJConfig(
            obs_dim=2,      # CCB uses 2-byte observations
            action_bytes=1,
            lambda_g=0.01,  # Reduced for K_eff in [2-6]
        )

    # Check if checkpoint has plasticity/sleep modules
    state_dict_key = 'brain_state_dict' if 'brain_state_dict' in checkpoint else 'model_state_dict'
    if state_dict_key in checkpoint:
        state_dict = checkpoint[state_dict_key]
    else:
        state_dict = checkpoint

    has_plasticity = any('plasticity' in k for k in state_dict.keys())
    has_sleep = any('sleep' in k for k in state_dict.keys())

    # Infer num_envs from adapter shape (batched plasticity)
    # For evaluation, we use num_envs=1 since we run single episodes
    checkpoint_num_envs = 1
    if 'plasticity.recurrent_adapter.A' in state_dict:
        adapter_shape = state_dict['plasticity.recurrent_adapter.A'].shape
        if len(adapter_shape) == 3:  # [num_envs, out_dim, rank]
            checkpoint_num_envs = adapter_shape[0]
            print(f"  Detected batched plasticity: num_envs={checkpoint_num_envs}")

    # For EVAL: use num_envs=1 regardless of training config
    # This is correct because we run single episodes during evaluation
    # The SLOW parameters (learning rules, gates) transfer; FAST weights are reset anyway
    eval_num_envs = 1
    print(f"  Using eval num_envs: {eval_num_envs}")

    # Adjust config to match checkpoint
    config.enable_plasticity = has_plasticity
    config.enable_sleep = has_sleep
    config.num_envs = eval_num_envs  # Use single-env for evaluation

    # Create brain and load state
    brain = RPJBrain(config)

    # Filter out fast weight adapters if shapes don't match
    # Fast weights are RESET at episode start anyway (A_0=0, B_0=0 per BLUEPRINT)
    # We only need the SLOW parameters (learning rules, gates, etc.)
    filtered_state_dict = {}
    for k, v in state_dict.items():
        if 'adapter.A' in k or 'adapter.B' in k:
            # Check if this is a batched adapter that needs reshaping
            if len(v.shape) == 3 and eval_num_envs == 1:
                # Skip - fast weights will be initialized fresh
                print(f"  Skipping batched fast weight: {k} (shape {v.shape})")
                continue
        filtered_state_dict[k] = v

    # Handle different checkpoint formats (strict=False for forward compatibility)
    brain.load_state_dict(filtered_state_dict, strict=False)
    print(f"  Plasticity: {'enabled' if has_plasticity else 'disabled'}")
    print(f"  Sleep: {'enabled' if has_sleep else 'disabled'}")

    brain.to(device)
    brain.eval()

    # Ensure plasticity adapters are in the correct dtype (float32)
    if brain.plasticity is not None:
        brain.plasticity.recurrent_adapter.A = brain.plasticity.recurrent_adapter.A.float()
        brain.plasticity.recurrent_adapter.B = brain.plasticity.recurrent_adapter.B.float()
        brain.plasticity.action_adapter.A = brain.plasticity.action_adapter.A.float()
        brain.plasticity.action_adapter.B = brain.plasticity.action_adapter.B.float()

    print(f"  Loaded brain with {sum(p.numel() for p in brain.parameters()):,} parameters")

    return brain, checkpoint


def run_episode_with_tracking(
    brain: RPJBrain,
    env: MultiTaskCCBEnvironment,
    task_id: int,
    max_steps: int = 50,
    use_oracle: bool = False,
    device: str = "cpu",
    enable_in_episode_plasticity: bool = True,
    reset_fast_weights_at_start: bool = True,
    collect_experiences: bool = False,
) -> Tuple[bool, EmergenceMetrics, List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]]:
    """
    Run a single episode with emergence metric tracking.

    Args:
        brain: The RPJ Brain to evaluate
        env: Multi-task CCB environment
        task_id: Which task to run
        max_steps: Maximum steps per episode
        use_oracle: If True, use oracle actions (for demo collection)
        device: Compute device
        enable_in_episode_plasticity: If True, update fast weights within episode
            Per BLUEPRINT Section 2.4: "Fast weights W_t may adapt within an episode"
        reset_fast_weights_at_start: If True, reset A=0, B=0 at episode start.
            Set to False for Persistence Eval (working memory transfer).
        collect_experiences: If True, collect (obs, h, target_action) tuples for sleep.

    Returns:
        (success, metrics, experiences): Episode success, emergence metrics, and
            collected experiences (empty list if collect_experiences=False)
    """
    experiences = []  # For sleep consolidation
    metrics = EmergenceMetrics(
        k_eff_values=[],
        g_l1_values=[],
        step_errors=[],
        task_successes=[],
    )

    # Reset environment
    obs, info = env.reset(task_id=task_id)
    obs = obs.to(device)

    # PERSISTENCE EVAL: Only reset fast weights if explicitly requested
    # For working memory transfer, we KEEP fast weights from demo
    if reset_fast_weights_at_start and brain.plasticity is not None:
        brain.plasticity.reset_fast_weights()

    # Initialize brain state
    h = torch.zeros(1, brain.substrate.hidden_dim, device=device)
    g_prev = torch.zeros(1, brain.config.k_max, device=device)
    a_prev = torch.zeros(1, dtype=torch.long, device=device)

    total_reward = 0.0

    for step in range(max_steps):
        # Forward pass
        with torch.no_grad():
            output = brain.forward(
                obs.unsqueeze(0).float(),  # [1, obs_dim]
                h,
                g_prev,
                a_prev,
                training=False,
            )

        # Track emergence metrics
        g_t = output.g_t
        k_eff = compute_k_eff(g_t)
        g_l1 = g_t.abs().mean().item()

        metrics.k_eff_values.append(k_eff)
        metrics.g_l1_values.append(g_l1)

        # Get action
        if use_oracle:
            action = env.get_oracle_action(obs)
        else:
            action = output.action.squeeze()

        # Collect experience for sleep consolidation (during oracle demo)
        if collect_experiences and use_oracle:
            experiences.append((
                obs.clone().cpu(),
                h.clone().cpu(),
                action.clone().cpu() if isinstance(action, torch.Tensor) else torch.tensor(action),
            ))

        # Step environment
        next_obs, reward, terminated, truncated, step_info = env.step(action)
        next_obs = next_obs.to(device)

        metrics.step_errors.append(step_info['error'])
        total_reward += reward

        # BLUEPRINT Section 2.4: In-episode plasticity update
        # Fast weights adapt within episode via local plasticity
        if enable_in_episode_plasticity and brain.plasticity is not None:
            # Normalize next observation (phi function)
            phi_o_next = (next_obs.float().unsqueeze(0) / 127.5) - 1.0  # [-1, 1]

            # Pad to plasticity obs_dim if needed
            if phi_o_next.shape[-1] < brain.plasticity.config.obs_dim:
                pad_size = brain.plasticity.config.obs_dim - phi_o_next.shape[-1]
                phi_o_next = torch.nn.functional.pad(phi_o_next, (0, pad_size))

            # Get value estimates for TD error
            with torch.no_grad():
                value = output.value.squeeze() if hasattr(output, 'value') else torch.tensor(0.0, device=device)

                # Forward pass for next state value
                next_output = brain.forward(
                    next_obs.unsqueeze(0).float(),
                    output.h_next,
                    output.g_t,
                    action.unsqueeze(0) if action.dim() == 0 else action,
                    training=False,
                )
                value_next = next_output.value.squeeze() if hasattr(next_output, 'value') else torch.tensor(0.0, device=device)

            # Update fast weights
            brain.update_plasticity(
                h_t=output.h_next,
                phi_o_next=phi_o_next,
                reward=torch.tensor([reward], device=device),
                value=value.unsqueeze(0) if value.dim() == 0 else value,
                value_next=value_next.unsqueeze(0) if value_next.dim() == 0 else value_next,
                g_t=output.g_t,
            )

        # Update state
        h = output.h_next
        g_prev = output.g_t
        a_prev = action.unsqueeze(0) if action.dim() == 0 else action
        obs = next_obs

        if terminated or truncated:
            break

    success = env.get_task_success()

    return success, metrics, experiences


def run_sleep_consolidation(
    brain: RPJBrain,
    demo_experiences: List[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]],
    sleep_steps: int = 10,
    sleep_lr: float = 1e-4,
    device: str = "cpu",
) -> float:
    """
    Sleep consolidation phase: Fine-tune slow weights on demo experiences.

    This implements BLUEPRINT Section 2.5 in simplified form:
    - Replay demo experiences
    - Update slow weights (θ) via SGD
    - This consolidates demo knowledge into permanent weights

    Args:
        brain: The RPJ Brain to fine-tune
        demo_experiences: List of (obs, hidden_state, target_action) from demo
        sleep_steps: Number of SGD iterations
        sleep_lr: Learning rate for consolidation
        device: Compute device

    Returns:
        Final consolidation loss
    """
    import torch.nn.functional as F

    # Create optimizer for slow weights only (not fast weights)
    # Exclude plasticity adapters A, B from optimization
    slow_params = [p for n, p in brain.named_parameters()
                   if 'adapter.A' not in n and 'adapter.B' not in n]
    optimizer = torch.optim.Adam(slow_params, lr=sleep_lr)

    brain.train()  # Enable gradients

    total_loss = 0.0
    for step in range(sleep_steps):
        optimizer.zero_grad()
        step_loss = 0.0

        for obs, h, target_action in demo_experiences:
            obs = obs.to(device)
            h = h.to(device)
            target_action = target_action.to(device)

            # Forward pass
            g_prev = torch.zeros(1, brain.config.k_max, device=device)
            a_prev = torch.zeros(1, dtype=torch.long, device=device)

            output = brain.forward(
                obs.unsqueeze(0).float(),
                h,
                g_prev,
                a_prev,
                training=True,
            )

            # Supervised loss on action prediction
            # Use action_mu (continuous) for differentiable loss
            if hasattr(output, 'action_mu'):
                predicted = output.action_mu
                target = target_action.float()
                loss = F.mse_loss(predicted, target)
            else:
                # Fallback to cross-entropy on logits
                logits = output.action_logits
                loss = F.cross_entropy(logits, target_action.long())

            step_loss += loss

        # Average loss over experiences
        step_loss = step_loss / len(demo_experiences)
        step_loss.backward()

        torch.nn.utils.clip_grad_norm_(slow_params, 1.0)
        optimizer.step()

        total_loss = step_loss.item()

    brain.eval()  # Back to eval mode

    return total_loss


def run_od_ndt_evaluation(
    brain: RPJBrain,
    env: MultiTaskCCBEnvironment,
    demo_task_id: int,
    train_task_ids: Optional[List[int]],
    test_task_ids: List[int],
    device: str = "cpu",
    enable_in_episode_plasticity: bool = True,
    persistence_mode: bool = False,
    sleep_consolidation: bool = False,
    sleep_steps: int = 10,
    sleep_lr: float = 1e-4,
) -> Dict:
    """
    Run full OD-NDT evaluation with emergence tracking.

    Protocol (BLUEPRINT-compliant with in-episode plasticity):
    1. Collect demo on demo_task_id (with oracle) - plasticity learns during demo
    2. For each test task:
       - Reset fast weights to zero (A_0=0, B_0=0) per BLUEPRINT
       - Run episode with IN-EPISODE plasticity updates
       - Fast weights adapt within each test episode
    3. Track K_eff throughout

    PERSISTENCE MODE (persistence_mode=True):
    Tests "Working Memory Transfer" instead of Consolidation:
    1. Run demo with oracle - fast weights learn task structure
    2. Keep fast weights intact (no reset) across all test tasks
    3. Tests if learned plasticity persists in volatile memory

    SLEEP CONSOLIDATION MODE (sleep_consolidation=True):
    Implements full Demo -> Sleep -> Test protocol per BLUEPRINT:
    1. Run demo with oracle, collecting (obs, h, target_action) experiences
    2. Sleep phase: Fine-tune slow weights on demo experiences via SGD
    3. Test phase: Evaluate with consolidated slow weights

    Returns:
        Dictionary with results and emergence metrics
    """
    if sleep_consolidation:
        mode_name = "SLEEP CONSOLIDATION (Demo->Sleep->Test)"
    elif persistence_mode:
        mode_name = "PERSISTENCE EVAL (Working Memory Transfer)"
    else:
        mode_name = "IN-EPISODE PLASTICITY"

    print(f"\n{'='*60}")
    print(f"OD-NDT EVALUATION: {mode_name}")
    print(f"{'='*60}")
    print(f"  In-episode plasticity: {'ENABLED' if enable_in_episode_plasticity else 'DISABLED'}")
    print(f"  Persistence mode: {'ENABLED - fast weights persist from demo' if persistence_mode else 'DISABLED - reset per episode'}")
    if sleep_consolidation:
        print(f"  Sleep consolidation: ENABLED ({sleep_steps} steps, lr={sleep_lr})")

    all_metrics = EmergenceMetrics(
        k_eff_values=[],
        g_l1_values=[],
        step_errors=[],
        task_successes=[],
    )

    # Phase 1: Demo collection (with oracle, with in-episode plasticity)
    # In persistence mode, we reset BEFORE demo so demo learns fresh, then KEEP weights
    print(f"\n[Phase 1] Demo collection on task {demo_task_id}...")
    demo_success, demo_metrics, demo_experiences = run_episode_with_tracking(
        brain, env, demo_task_id,
        use_oracle=True,
        device=device,
        enable_in_episode_plasticity=enable_in_episode_plasticity,
        reset_fast_weights_at_start=True,  # Always reset before demo
        collect_experiences=sleep_consolidation,  # Only collect if doing sleep
    )
    print(f"  Demo success: {demo_success}")
    print(f"  Demo K_eff mean: {np.mean(demo_metrics.k_eff_values):.3f}")
    if sleep_consolidation:
        print(f"  Collected {len(demo_experiences)} experiences for sleep consolidation")

    # Check fast weight state after demo (for persistence mode verification)
    if persistence_mode and brain.plasticity is not None:
        fw_norm = (brain.plasticity.recurrent_adapter.A.norm().item() +
                   brain.plasticity.recurrent_adapter.B.norm().item())
        print(f"  Fast weight norm after demo: {fw_norm:.4f}")

    # Sleep Phase: Consolidate demo experiences into slow weights
    if sleep_consolidation and len(demo_experiences) > 0:
        print(f"\n[Phase 1.5] Sleep consolidation...")
        print(f"  Replaying {len(demo_experiences)} demo experiences")
        print(f"  SGD steps: {sleep_steps}, LR: {sleep_lr}")
        sleep_loss = run_sleep_consolidation(
            brain=brain,
            demo_experiences=demo_experiences,
            sleep_steps=sleep_steps,
            sleep_lr=sleep_lr,
            device=device,
        )
        print(f"  Final consolidation loss: {sleep_loss:.6f}")

    # Phase 2: Protocol description
    if persistence_mode:
        print(f"\n[Phase 2] PERSISTENCE EVAL protocol...")
        print("  Fast weights from demo are KEPT (no reset)")
        print("  Testing Working Memory Transfer: can demo knowledge persist?")
        print("  In-episode plasticity continues to refine weights")
    else:
        # Per BLUEPRINT Section 2.4: Fast weights reset to zero at episode start
        print(f"\n[Phase 2] In-episode plasticity protocol...")
        print("  Each test episode starts with A_0=0, B_0=0")
        print("  Fast weights adapt WITHIN episode via learned plasticity rules")

    # Phase 3: Test evaluation with in-episode plasticity
    if train_task_ids:
        print(f"\n[Phase 3] Estimating SR_train on {len(train_task_ids)} train tasks...")
    print(f"\n[Phase 4] Evaluating SR_novel on {len(test_task_ids)} held-out tasks...")
    if not train_task_ids:
        print("  WARNING: SR_train not computed from tasks; defaulting to 1.0 (legacy mode)")

    train_successes: List[bool] = []
    test_successes = []
    test_k_effs = []
    test_errors = []

    def _eval_task(task_id: int, reset_at_start: bool) -> Tuple[bool, EmergenceMetrics]:
        success, task_metrics, _ = run_episode_with_tracking(
            brain, env, task_id,
            use_oracle=False,
            device=device,
            enable_in_episode_plasticity=enable_in_episode_plasticity,
            reset_fast_weights_at_start=reset_at_start,
            collect_experiences=False,
        )
        return success, task_metrics

    # Per BLUEPRINT Section 2.4: Fast weights reset to post-sleep state at episode start.
    # In our implementation, post-sleep fast weights are zeroed (A_0=0, B_0=0).
    reset_at_start = not persistence_mode

    if train_task_ids:
        for i, task_id in enumerate(train_task_ids):
            success, _ = _eval_task(task_id, reset_at_start=reset_at_start)
            train_successes.append(success)

            if (i + 1) % 20 == 0:
                sr = sum(train_successes) / len(train_successes)
                print(f"  Train progress: {i+1}/{len(train_task_ids)} | SR_train: {sr:.3f}")

    for i, task_id in enumerate(test_task_ids):
        # PERSISTENCE MODE: Keep fast weights from demo (no reset)
        # STANDARD MODE: Reset fast weights at start of each episode (A_0=0, B_0=0)
        success, task_metrics = _eval_task(task_id, reset_at_start=reset_at_start)

        test_successes.append(success)
        test_k_effs.extend(task_metrics.k_eff_values)
        test_errors.extend(task_metrics.step_errors)

        # Progress update
        if (i + 1) % 20 == 0:
            sr = sum(test_successes) / len(test_successes)
            k_eff_mean = np.mean(test_k_effs)
            print(f"  Novel progress: {i+1}/{len(test_task_ids)} | SR_novel: {sr:.3f} | K_eff: {k_eff_mean:.3f}")

    # Compute final metrics
    sr_novel = sum(test_successes) / len(test_successes)
    if train_task_ids:
        sr_train = sum(train_successes) / len(train_successes)
    else:
        sr_train = 1.0  # Legacy default (avoids making T==SR_novel by accident)
    transfer_T = sr_novel / sr_train if sr_train > 0 else 0.0

    mean_k_eff = np.mean(test_k_effs)
    std_k_eff = np.std(test_k_effs)
    mean_error = np.mean(test_errors)

    # Pass criteria
    sr_pass = sr_novel >= 0.60
    t_pass = transfer_T >= 0.80
    overall_pass = sr_pass and t_pass

    # Emergence assessment
    # Key hypothesis: K_eff should stay elevated (> 1.5) for persistent emergence
    k_eff_elevated = mean_k_eff > 1.5

    results = {
        'sr_novel': sr_novel,
        'sr_train': sr_train,
        'transfer_T': transfer_T,
        'sr_pass': sr_pass,
        't_pass': t_pass,
        'overall_pass': overall_pass,
        'mean_k_eff': mean_k_eff,
        'std_k_eff': std_k_eff,
        'k_eff_elevated': k_eff_elevated,
        'mean_error': mean_error,
        'demo_k_eff': np.mean(demo_metrics.k_eff_values),
        'num_train_tasks': len(train_task_ids) if train_task_ids else 0,
        'num_test_tasks': len(test_task_ids),
        'train_successes': train_successes,
        'test_k_effs': test_k_effs,
        'test_errors': test_errors,
        'in_episode_plasticity': enable_in_episode_plasticity,
        'persistence_mode': persistence_mode,
    }

    # Print summary
    print(f"\n{'='*60}")
    print("OD-NDT RESULTS")
    print(f"{'='*60}")
    print(f"\n=== Transfer Metrics ===")
    print(f"  SR_train:    {sr_train:.3f}")
    print(f"  SR_novel:    {sr_novel:.3f} (threshold: 0.60) {'PASS' if sr_pass else 'FAIL'}")
    print(f"  Transfer T:  {transfer_T:.3f} (threshold: 0.80) {'PASS' if t_pass else 'FAIL'}")
    print(f"  Overall:     {'PASS' if overall_pass else 'FAIL'}")

    print(f"\n=== Emergence Metrics (Key for PERSISTENT EMERGENCE) ===")
    print(f"  Demo K_eff:  {results['demo_k_eff']:.3f}")
    print(f"  Test K_eff:  {mean_k_eff:.3f} +/- {std_k_eff:.3f}")
    print(f"  K_eff elevated (> 1.5): {'YES' if k_eff_elevated else 'NO'}")
    print(f"  Mean error:  {mean_error:.4f}")

    print(f"\n=== Emergence Interpretation ===")
    if k_eff_elevated:
        print("  [SUCCESS] K_eff remains elevated during multi-task evaluation!")
        print("  This supports the PERSISTENT EMERGENCE hypothesis:")
        print("  - Task diversity maintains plasticity gating")
        print("  - Unlike single-task CCB where K_eff habituates")
    else:
        print("  [WARNING] K_eff collapsed during evaluation")
        print("  Possible causes:")
        print("  - Tasks not diverse enough")
        print("  - Brain not using g_t for adaptation")
        print("  - Need more training on diverse tasks")

    return results


def main():
    parser = argparse.ArgumentParser(description="OD-NDT Evaluation")
    parser.add_argument(
        "--checkpoint",
        type=str,
        default="results/checkpoint_multitask_ccb_final_50331648.pt",
        help="Path to trained checkpoint",
    )
    parser.add_argument(
        "--num-test-tasks",
        type=int,
        default=100,
        help="Number of test tasks",
    )
    parser.add_argument(
        "--num-train-tasks",
        type=int,
        default=100,
        help="Number of train tasks to estimate SR_train (for transfer T = SR_novel/SR_train)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Device to use",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--enable-plasticity",
        action="store_true",
        default=True,
        help="Enable in-episode plasticity updates (BLUEPRINT-compliant)",
    )
    parser.add_argument(
        "--disable-plasticity",
        action="store_true",
        default=False,
        help="Disable in-episode plasticity (for comparison)",
    )
    parser.add_argument(
        "--persistence-eval",
        action="store_true",
        default=False,
        help="PERSISTENCE EVAL: Keep fast weights from demo across test tasks (no reset). "
             "Tests Working Memory Transfer instead of Consolidation. "
             "If SR > 0.60, OD-NDT mechanism is valid (just volatile).",
    )
    parser.add_argument(
        "--sleep-consolidation",
        action="store_true",
        default=False,
        help="SLEEP CONSOLIDATION: Fine-tune slow weights on demo experiences. "
             "Implements Demo -> Sleep -> Test protocol per BLUEPRINT. "
             "Sleep = SGD updates on demo data to consolidate into slow weights.",
    )
    parser.add_argument(
        "--sleep-steps",
        type=int,
        default=10,
        help="Number of SGD updates during sleep consolidation (default: 10)",
    )
    parser.add_argument(
        "--sleep-lr",
        type=float,
        default=1e-4,
        help="Learning rate for sleep consolidation (default: 1e-4)",
    )
    parser.add_argument(
        "--ignore-transfer",
        action="store_true",
        default=False,
        help="Gate only on SR_novel (ignore transfer-T threshold).",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        default=False,
        help="Do not write results artifact to results/.",
    )

    args = parser.parse_args()

    # Handle plasticity flag
    enable_plasticity = args.enable_plasticity and not args.disable_plasticity
    persistence_mode = args.persistence_eval

    # Set seeds
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    print("=" * 60)
    print("RPJ Brain OD-NDT Evaluation")
    print("=" * 60)
    print(f"  Checkpoint: {args.checkpoint}")
    print(f"  Device: {args.device}")
    print(f"  Test tasks: {args.num_test_tasks}")
    print(f"  In-episode plasticity: {'ENABLED' if enable_plasticity else 'DISABLED'}")
    if persistence_mode:
        print(f"  >>> PERSISTENCE EVAL MODE <<<")
        print(f"  Fast weights from demo will PERSIST across test tasks")
    if args.sleep_consolidation:
        print(f"  >>> SLEEP CONSOLIDATION MODE <<<")
        print(f"  Demo->Sleep->Test protocol")
        print(f"  Sleep steps: {args.sleep_steps}, LR: {args.sleep_lr}")

    # Load checkpoint
    brain, checkpoint = load_checkpoint(args.checkpoint, args.device)

    # Create multi-task environment
    env = create_multitask_ccb(
        num_tasks=args.num_test_tasks + max(0, args.num_train_tasks),
        nonlinear=True,
        device=args.device,
        seed=args.seed,
        steps_per_task=10,
        success_threshold=0.3,  # Relaxed threshold for multi-task
    )

    # Get task splits (disjoint demo/train/test IDs)
    if args.num_train_tasks < 1:
        print("ERROR: --num-train-tasks must be >= 1 (needed to define SR_train and demo task)")
        return 2
    if env.config.num_tasks < (args.num_train_tasks + args.num_test_tasks):
        print("ERROR: env task bank too small for requested train/test split")
        return 2

    rng = np.random.default_rng(args.seed)
    all_ids = list(range(env.config.num_tasks))
    rng.shuffle(all_ids)
    train_ids = all_ids[:args.num_train_tasks]
    test_ids = all_ids[args.num_train_tasks:args.num_train_tasks + args.num_test_tasks]
    demo_id = train_ids[0]

    print(f"\n  Demo task: {demo_id}")
    print(f"  Train tasks: {train_ids[:5]}... ({len(train_ids)} total)")
    print(f"  Test tasks: {test_ids[:5]}... ({len(test_ids)} total)")

    # Run evaluation
    results = run_od_ndt_evaluation(
        brain=brain,
        env=env,
        demo_task_id=demo_id,
        train_task_ids=train_ids,
        test_task_ids=test_ids,
        device=args.device,
        enable_in_episode_plasticity=enable_plasticity,
        persistence_mode=persistence_mode,
        sleep_consolidation=args.sleep_consolidation,
        sleep_steps=args.sleep_steps,
        sleep_lr=args.sleep_lr,
    )

    # Save results with appropriate filename
    if not args.no_save:
        if args.sleep_consolidation:
            results_path = Path("results/od_ndt_sleep_results.pt")
        elif persistence_mode:
            results_path = Path("results/od_ndt_persistence_results.pt")
        else:
            results_path = Path("results/od_ndt_results.pt")
        torch.save(results, results_path)
        print(f"\nResults saved to: {results_path}")

    passed = results["sr_pass"] if args.ignore_transfer else results["overall_pass"]
    print(f"\n>>> FINAL VERDICT: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
