#!/usr/bin/env python3
"""
Benchmark Scoring Script for RPJ Brain v5.

Evaluates a trained checkpoint on BLUEPRINT.md benchmarks:
1. CCB/CCB-NL: DoErr <= 0.05, discrimination >= 0.90
2. OD-NDT: SR_novel >= 0.60, T >= 0.80

Usage:
    python scripts/score_benchmarks.py checkpoint_final_100000.pt [--benchmark ccb|od_ndt|all]
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import torch

from src.core.rpj_brain import create_brain
from src.benchmarks.ccb import CCBEnvironment
from src.benchmarks.od_ndt import create_od_ndt_harness, ODNDTConfig


# =============================================================================
# CCB Benchmark: Causal Discrimination (DoErr)
# =============================================================================

def compute_do_err(
    brain,
    env: CCBEnvironment,
    num_episodes: int = 100,
    device: str = "cpu",
) -> Dict:
    """
    Compute DoErr (Do-calculus Error) on CCB benchmark.

    DoErr = (1/Q) Σ |predicted_Y - true_Y| where true_Y = E[Y | do(X=target_X)]

    For linear CCB: true_Y = b_X * target_X (default b_X=1.0)
    Action byte [0,255] maps to predicted_Y in [-2, 2] via: (byte/255)*4 - 2

    Per BLUEPRINT: DoErr <= 0.05 required.

    Args:
        brain: Trained RPJ Brain
        env: CCB environment
        num_episodes: Number of test episodes
        device: Compute device

    Returns:
        Dictionary with DoErr and supporting metrics
    """
    brain.eval()

    all_errors = []
    all_predicted_Y = []
    all_true_Y = []
    episode_do_errs = []

    for ep in range(num_episodes):
        obs, info = env.reset()
        obs = torch.tensor(obs, dtype=torch.long, device=device).unsqueeze(0)

        # Initialize state
        h, g = brain.init_state(1, device)
        a_prev = torch.zeros(1, dtype=torch.long, device=device)

        episode_errors = []

        # Run full episode (CCB has num_interventions steps per episode)
        done = False
        while not done:
            # Get brain's prediction
            with torch.no_grad():
                output = brain(obs, h, g, a_prev, training=False)

            # Step environment with action
            action_np = output.action.squeeze(0).cpu().numpy()
            next_obs, reward, terminated, truncated, step_info = env.step(action_np)
            done = terminated or truncated

            # Collect per-step error from environment (properly computed)
            # step_info contains: predicted_Y, true_Y, error
            if 'error' in step_info:
                episode_errors.append(step_info['error'])
                all_errors.append(step_info['error'])
                all_predicted_Y.append(step_info['predicted_Y'])
                all_true_Y.append(step_info['true_Y'])

            if not done:
                # Update state for next step
                obs = torch.tensor(next_obs, dtype=torch.long, device=device).unsqueeze(0)
                h = output.h_next
                g = output.g_t
                a_prev = output.action.flatten()

        # Get episode DoErr from environment's internal tracking
        episode_do_err = env.compute_do_error()
        episode_do_errs.append(episode_do_err)

    # Compute overall DoErr = mean absolute error across all predictions
    do_err = float(np.mean(all_errors)) if all_errors else 1.0

    # Discrimination: measures how consistently the agent predicts the causal effect
    # Compute correlation between predicted and true values
    if len(all_predicted_Y) > 1:
        pred_arr = np.array(all_predicted_Y)
        true_arr = np.array(all_true_Y)

        # Correlation-based discrimination
        correlation = np.corrcoef(pred_arr, true_arr)[0, 1]
        if np.isnan(correlation):
            correlation = 0.0

        # Scale: perfect correlation = 1.0 discrimination
        # Random = 0.0 discrimination
        discrimination = max(0.0, correlation)
    else:
        discrimination = 0.0

    return {
        'do_err': float(do_err),
        'mean_episode_do_err': float(np.mean(episode_do_errs)) if episode_do_errs else 1.0,
        'std_episode_do_err': float(np.std(episode_do_errs)) if episode_do_errs else 0.0,
        'discrimination': float(discrimination),
        'num_episodes': num_episodes,
        'num_predictions': len(all_errors),
        'mean_predicted_Y': float(np.mean(all_predicted_Y)) if all_predicted_Y else 0.0,
        'mean_true_Y': float(np.mean(all_true_Y)) if all_true_Y else 0.0,
        'pass_do_err': do_err <= 0.05,
        'pass_discrimination': discrimination >= 0.90,
        'all_passed': do_err <= 0.05 and discrimination >= 0.90,
    }


# =============================================================================
# OD-NDT Benchmark: One-Demo No-Data Transfer
# =============================================================================

class SimplifiedODNDTEnv:
    """
    Simplified OD-NDT environment for testing.

    Real OD-NDT uses a held-out task distribution.
    This simplified version uses CCB with different random seeds.
    """

    def __init__(self, task_id: int = 0, device: str = "cpu"):
        self.task_id = task_id
        self.device = device
        self._env = CCBEnvironment()
        self._success = False
        self._step_count = 0

    def reset(self, task_id: int = None) -> Tuple[torch.Tensor, Dict]:
        if task_id is not None:
            self.task_id = task_id
            # Use task_id as seed for different "tasks"
            np.random.seed(self.task_id)

        obs, info = self._env.reset()
        self._success = False
        self._step_count = 0
        return torch.tensor(obs, dtype=torch.long, device=self.device), info

    def step(self, action: torch.Tensor) -> Tuple[torch.Tensor, float, bool, bool, Dict]:
        action_np = action.cpu().numpy() if isinstance(action, torch.Tensor) else action
        obs, reward, terminated, truncated, info = self._env.step(action_np)

        self._step_count += 1

        # Consider success if positive reward
        if reward > 0:
            self._success = True

        return (
            torch.tensor(obs, dtype=torch.long, device=self.device),
            reward,
            terminated,
            truncated,
            info,
        )

    def get_oracle_action(self, obs: torch.Tensor) -> torch.Tensor:
        """Return oracle (optimal) action."""
        # For CCB, oracle knows the causal Y from do(X)
        # Simplified: return the causal prediction
        obs_np = obs.cpu().numpy() if isinstance(obs, torch.Tensor) else obs
        x_val = obs_np[4] if len(obs_np) > 4 else 0
        # Oracle uses causal: Y = f(X) not Y = f(X, Z)
        oracle_y = x_val % 2  # Simplified causal relationship
        return torch.tensor([oracle_y], dtype=torch.long, device=self.device)

    def get_task_success(self) -> bool:
        return self._success


def run_od_ndt_benchmark(
    brain,
    num_test_tasks: int = 20,
    demo_task_id: int = 0,
    device: str = "cpu",
) -> Dict:
    """
    Run simplified OD-NDT benchmark.

    Per BLUEPRINT: SR_novel >= 0.60, T >= 0.80

    Args:
        brain: Trained RPJ Brain
        num_test_tasks: Number of held-out test tasks
        demo_task_id: Task ID for demonstration
        device: Compute device

    Returns:
        OD-NDT results dictionary
    """
    brain.eval()

    # Create harness
    config = ODNDTConfig(
        num_test_tasks=num_test_tasks,
        sleep_budget=100.0,  # B_sleep_1 = 100J
        device=device,
    )
    harness = create_od_ndt_harness(brain, device=device)
    harness.config = config

    # Create environment
    env = SimplifiedODNDTEnv(device=device)

    # Test task IDs (held-out)
    test_task_ids = list(range(100, 100 + num_test_tasks))

    # Estimate SR_train from training distribution
    # Run a few episodes on training-like tasks
    train_successes = 0
    train_total = 10

    for i in range(train_total):
        env.reset(task_id=i)
        h, g = brain.init_state(1, device)
        a_prev = torch.zeros(1, dtype=torch.long, device=device)

        obs, _ = env.reset(task_id=i)

        for step in range(100):
            with torch.no_grad():
                output = brain(obs.unsqueeze(0), h, g, a_prev, training=False)

            action = output.action.squeeze()
            obs, reward, terminated, truncated, info = env.step(action)

            h = output.h_next
            g = output.g_t
            a_prev = output.action.flatten()

            if terminated or truncated:
                break

        if env.get_task_success():
            train_successes += 1

    sr_train = train_successes / train_total

    # Run OD-NDT evaluation
    print(f"\n[OD-NDT] Estimated SR_train: {sr_train:.3f}")

    try:
        result = harness.run_evaluation(
            env=env,
            demo_task_id=demo_task_id,
            test_task_ids=test_task_ids,
            sr_train=max(sr_train, 0.01),  # Avoid division by zero
        )

        return {
            'sr_train': float(result.sr_train),
            'sr_novel': float(result.sr_novel),
            'transfer_ratio': float(result.transfer_ratio),
            'demo_energy': float(result.demo_energy),
            'sleep_energy': float(result.sleep_energy),
            'num_test_tasks': len(result.test_successes),
            'test_success_rate': float(sum(result.test_successes) / len(result.test_successes)),
            'passed': result.passed,
            'fail_reasons': result.fail_reasons,
            'pass_sr_novel': result.sr_novel >= 0.60,
            'pass_transfer': result.transfer_ratio >= 0.80,
        }
    except Exception as e:
        print(f"[OD-NDT] Error: {e}")
        return {
            'sr_train': float(sr_train),
            'sr_novel': 0.0,
            'transfer_ratio': 0.0,
            'error': str(e),
            'passed': False,
            'pass_sr_novel': False,
            'pass_transfer': False,
        }


def main():
    parser = argparse.ArgumentParser(description="Score benchmarks from trained checkpoint")
    parser.add_argument("checkpoint", type=str, help="Path to checkpoint .pt file")
    parser.add_argument("--benchmark", type=str, default="all",
                       choices=["ccb", "od_ndt", "all"], help="Which benchmark to run")
    parser.add_argument("--episodes", type=int, default=100, help="Number of CCB episodes")
    parser.add_argument("--test-tasks", type=int, default=20, help="Number of OD-NDT test tasks")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or cuda)")
    parser.add_argument("--save-json", action="store_true", help="Save results to JSON")
    args = parser.parse_args()

    print("=" * 60)
    print("RPJ Brain v5 - Benchmark Scoring")
    print("=" * 60)

    # Load checkpoint
    print(f"\nLoading checkpoint: {args.checkpoint}")
    checkpoint = torch.load(args.checkpoint, map_location=args.device)

    # Create brain
    config = checkpoint.get('config', {'obs_dim': 8, 'action_bytes': 1})
    brain = create_brain(
        obs_dim=config['obs_dim'],
        action_bytes=config['action_bytes'],
    )
    brain.load_state_dict(checkpoint['brain_state_dict'])
    brain.to(args.device)
    brain.eval()

    print(f"Loaded checkpoint at timestep {checkpoint.get('timesteps', 'unknown')}")

    results = {
        'timestamp': datetime.now().isoformat(),
        'checkpoint': args.checkpoint,
        'checkpoint_timesteps': checkpoint.get('timesteps', 'unknown'),
    }

    # Run CCB benchmark
    if args.benchmark in ["ccb", "all"]:
        print(f"\n{'=' * 60}")
        print("CCB BENCHMARK (Confounded Causal Bandits)")
        print("=" * 60)

        env = CCBEnvironment()
        ccb_results = compute_do_err(brain, env, num_episodes=args.episodes, device=args.device)
        results['ccb'] = ccb_results

        print(f"\nResults:")
        print(f"  DoErr: {ccb_results['do_err']:.4f} (threshold: <= 0.05)")
        print(f"  Discrimination: {ccb_results['discrimination']:.4f} (threshold: >= 0.90)")
        print(f"  Num predictions: {ccb_results['num_predictions']}")

        do_err_status = "PASS" if ccb_results['pass_do_err'] else "FAIL"
        disc_status = "PASS" if ccb_results['pass_discrimination'] else "FAIL"
        print(f"\n  DoErr: {do_err_status}")
        print(f"  Discrimination: {disc_status}")

    # Run OD-NDT benchmark
    if args.benchmark in ["od_ndt", "all"]:
        print(f"\n{'=' * 60}")
        print("OD-NDT BENCHMARK (One-Demo No-Data Transfer)")
        print("=" * 60)

        od_ndt_results = run_od_ndt_benchmark(
            brain,
            num_test_tasks=args.test_tasks,
            device=args.device,
        )
        results['od_ndt'] = od_ndt_results

        print(f"\nResults:")
        print(f"  SR_train: {od_ndt_results['sr_train']:.4f}")
        print(f"  SR_novel: {od_ndt_results['sr_novel']:.4f} (threshold: >= 0.60)")
        print(f"  Transfer T: {od_ndt_results['transfer_ratio']:.4f} (threshold: >= 0.80)")

        sr_status = "PASS" if od_ndt_results['pass_sr_novel'] else "FAIL"
        t_status = "PASS" if od_ndt_results['pass_transfer'] else "FAIL"
        print(f"\n  SR_novel: {sr_status}")
        print(f"  Transfer: {t_status}")

    # Summary
    print(f"\n{'=' * 60}")
    print("BENCHMARK SUMMARY")
    print("=" * 60)

    all_passed = True

    if 'ccb' in results:
        ccb_pass = results['ccb']['all_passed']
        print(f"CCB: {'PASS' if ccb_pass else 'FAIL'}")
        all_passed = all_passed and ccb_pass

    if 'od_ndt' in results:
        od_ndt_pass = results['od_ndt']['passed']
        print(f"OD-NDT: {'PASS' if od_ndt_pass else 'FAIL'}")
        all_passed = all_passed and od_ndt_pass

    results['all_passed'] = all_passed

    if all_passed:
        print(f"\n>>> ALL BENCHMARKS: PASS <<<")
    else:
        print(f"\n>>> BENCHMARKS: FAIL <<<")

    # Save to JSON if requested
    if args.save_json:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_scores_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {filename}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
