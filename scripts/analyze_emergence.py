#!/usr/bin/env python3
"""
Emergence Analysis Script for RPJ Brain v5.

Analyzes a trained checkpoint to verify emergence criteria from BLUEPRINT.md:
1. CBR_t (Compute Burst Ratio) - should be bimodal
2. K_eff (effective scalar count) - should be in [2, 6]
3. BI_t (Broadcast Index) - distribution analysis

Usage:
    python scripts/analyze_emergence.py checkpoint_final_100000.pt [--episodes 10]
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import torch

from src.core.rpj_brain import create_brain
from src.benchmarks.ccb import CCBEnvironment


def compute_bimodality_coefficient(data: np.ndarray) -> float:
    """
    Compute Sarle's bimodality coefficient.

    B = (skewness^2 + 1) / kurtosis

    B > 5/9 (0.555) suggests bimodality.

    Args:
        data: 1D array of values

    Returns:
        Bimodality coefficient B
    """
    n = len(data)
    if n < 4:
        return 0.0

    mean = np.mean(data)
    std = np.std(data, ddof=1)

    if std < 1e-8:
        return 0.0

    # Skewness
    skewness = np.mean(((data - mean) / std) ** 3)

    # Kurtosis (excess)
    kurtosis = np.mean(((data - mean) / std) ** 4) - 3

    # Bimodality coefficient
    # Note: Fisher's adjustment for sample size
    adjusted_kurtosis = kurtosis + 3  # Back to non-excess

    if adjusted_kurtosis < 1e-8:
        return 0.0

    b = (skewness ** 2 + 1) / adjusted_kurtosis
    return b


def analyze_cbr_distribution(cbr_values: np.ndarray) -> Dict:
    """
    Analyze CBR distribution for bimodality.

    Per BLUEPRINT: CBR should be bimodal (compute/not-compute phases).

    Args:
        cbr_values: Array of CBR_t values

    Returns:
        Analysis results
    """
    bimodality = compute_bimodality_coefficient(cbr_values)

    # Histogram analysis
    hist, bin_edges = np.histogram(cbr_values, bins=50, density=True)

    # Find peaks (simple local maxima detection)
    peaks = []
    for i in range(1, len(hist) - 1):
        if hist[i] > hist[i-1] and hist[i] > hist[i+1]:
            peaks.append((bin_edges[i], hist[i]))

    return {
        'mean': float(np.mean(cbr_values)),
        'std': float(np.std(cbr_values)),
        'min': float(np.min(cbr_values)),
        'max': float(np.max(cbr_values)),
        'bimodality_coefficient': float(bimodality),
        'is_bimodal': bimodality > 0.555,
        'num_peaks': len(peaks),
        'histogram': hist.tolist(),
        'bin_edges': bin_edges.tolist(),
    }


def compute_k_eff(g_t_batch: np.ndarray) -> float:
    """
    Compute effective scalar count (participation ratio).

    K_eff = (sum Var(g_k))^2 / (sum Var(g_k)^2 + eps)

    Per BLUEPRINT: Should be in [2, 6].

    Args:
        g_t_batch: Array of shape [N, K_max] with global scalar values

    Returns:
        K_eff value
    """
    # Variance across samples for each scalar
    variances = np.var(g_t_batch, axis=0)

    sum_var = np.sum(variances)
    sum_var_sq = np.sum(variances ** 2)

    eps = 1e-8
    k_eff = (sum_var ** 2) / (sum_var_sq + eps)

    return float(k_eff)


def run_emergence_analysis(
    checkpoint_path: str,
    num_episodes: int = 10,
    max_steps_per_episode: int = 500,
    device: str = "cpu",
) -> Dict:
    """
    Run full emergence analysis on a trained checkpoint.

    Args:
        checkpoint_path: Path to checkpoint .pt file
        num_episodes: Number of evaluation episodes
        max_steps_per_episode: Max steps per episode
        device: Compute device

    Returns:
        Analysis results dictionary
    """
    print(f"Loading checkpoint: {checkpoint_path}")

    # Load checkpoint
    checkpoint = torch.load(checkpoint_path, map_location=device)

    # Create brain with same config
    config = checkpoint.get('config', {'obs_dim': 8, 'action_bytes': 1})
    brain = create_brain(
        obs_dim=config['obs_dim'],
        action_bytes=config['action_bytes'],
    )
    brain.load_state_dict(checkpoint['brain_state_dict'])
    brain.to(device)
    brain.eval()

    print(f"Loaded checkpoint at timestep {checkpoint.get('timesteps', 'unknown')}")

    # Create environment
    env = CCBEnvironment()

    # Collect emergence data
    all_cbr = []
    all_bi = []
    all_g_t = []
    all_c_t = []
    episode_rewards = []
    episode_lengths = []

    print(f"\nRunning {num_episodes} evaluation episodes...")

    for ep in range(num_episodes):
        obs, info = env.reset()
        obs = torch.tensor(obs, dtype=torch.long, device=device).unsqueeze(0)

        # Initialize state
        h, g = brain.init_state(1, device)
        a_prev = torch.zeros(1, dtype=torch.long, device=device)

        episode_reward = 0
        episode_length = 0

        for step in range(max_steps_per_episode):
            with torch.no_grad():
                output = brain(obs, h, g, a_prev, training=False)

            # Collect emergence metrics
            all_cbr.append(output.cbr_t.squeeze().cpu().numpy())
            all_bi.append(output.bi_t.squeeze().cpu().numpy())
            all_g_t.append(output.g_t.squeeze().cpu().numpy())
            all_c_t.append(output.c_t.squeeze().cpu().numpy())

            # Step environment
            action = output.action.cpu().numpy().flatten()
            next_obs, reward, terminated, truncated, info = env.step(action)

            episode_reward += reward
            episode_length += 1

            if terminated or truncated:
                break

            # Update state
            obs = torch.tensor(next_obs, dtype=torch.long, device=device).unsqueeze(0)
            h = output.h_next
            g = output.g_t
            a_prev = output.action.flatten()

        episode_rewards.append(episode_reward)
        episode_lengths.append(episode_length)

        if (ep + 1) % 5 == 0:
            print(f"  Episode {ep + 1}/{num_episodes}: reward={episode_reward:.2f}, length={episode_length}")

    # Convert to numpy arrays
    all_cbr = np.array(all_cbr)
    all_bi = np.array(all_bi)
    all_g_t = np.array(all_g_t)
    all_c_t = np.array(all_c_t)

    print(f"\nAnalyzing {len(all_cbr)} timesteps...")

    # Analyze CBR distribution
    cbr_analysis = analyze_cbr_distribution(all_cbr)

    # Compute K_eff
    k_eff = compute_k_eff(all_g_t)
    k_eff_in_range = 2 <= k_eff <= 6

    # Analyze BI distribution
    bi_analysis = {
        'mean': float(np.mean(all_bi)),
        'std': float(np.std(all_bi)),
        'min': float(np.min(all_bi)),
        'max': float(np.max(all_bi)),
    }

    # Analyze c_t distribution
    c_t_analysis = {
        'mean': float(np.mean(all_c_t)),
        'std': float(np.std(all_c_t)),
        'min': float(np.min(all_c_t)),
        'max': float(np.max(all_c_t)),
    }

    # Per-scalar variance for g_t
    g_t_variances = np.var(all_g_t, axis=0).tolist()

    # BLUEPRINT pass criteria
    cbr_pass = cbr_analysis['is_bimodal']
    k_eff_pass = k_eff_in_range

    results = {
        'timestamp': datetime.now().isoformat(),
        'checkpoint': checkpoint_path,
        'checkpoint_timesteps': checkpoint.get('timesteps', 'unknown'),
        'num_episodes': num_episodes,
        'total_steps_analyzed': len(all_cbr),

        # Performance
        'mean_episode_reward': float(np.mean(episode_rewards)),
        'std_episode_reward': float(np.std(episode_rewards)),
        'mean_episode_length': float(np.mean(episode_lengths)),

        # CBR Analysis
        'cbr': cbr_analysis,

        # K_eff Analysis
        'k_eff': k_eff,
        'k_eff_in_range': k_eff_in_range,
        'g_t_variances': g_t_variances,

        # BI Analysis
        'bi': bi_analysis,

        # c_t Analysis
        'c_t': c_t_analysis,

        # BLUEPRINT Pass Criteria
        'pass_criteria': {
            'cbr_bimodal': cbr_pass,
            'k_eff_in_range': k_eff_pass,
            'all_passed': cbr_pass and k_eff_pass,
        },
    }

    return results


def main():
    parser = argparse.ArgumentParser(description="Analyze emergence metrics from trained checkpoint")
    parser.add_argument("checkpoint", type=str, help="Path to checkpoint .pt file")
    parser.add_argument("--episodes", type=int, default=10, help="Number of evaluation episodes")
    parser.add_argument("--max-steps", type=int, default=500, help="Max steps per episode")
    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu or cuda)")
    parser.add_argument("--save-json", action="store_true", help="Save results to JSON")
    args = parser.parse_args()

    print("=" * 60)
    print("RPJ Brain v5 - Emergence Analysis")
    print("=" * 60)

    # Run analysis
    results = run_emergence_analysis(
        checkpoint_path=args.checkpoint,
        num_episodes=args.episodes,
        max_steps_per_episode=args.max_steps,
        device=args.device,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("EMERGENCE ANALYSIS RESULTS")
    print("=" * 60)

    print(f"\nCheckpoint: {results['checkpoint']}")
    print(f"Timesteps: {results['checkpoint_timesteps']}")
    print(f"Episodes analyzed: {results['num_episodes']}")
    print(f"Total steps: {results['total_steps_analyzed']}")

    print(f"\n--- Performance ---")
    print(f"Mean episode reward: {results['mean_episode_reward']:.3f} +/- {results['std_episode_reward']:.3f}")
    print(f"Mean episode length: {results['mean_episode_length']:.1f}")

    print(f"\n--- CBR Analysis (Compute Burst Ratio) ---")
    cbr = results['cbr']
    print(f"Mean: {cbr['mean']:.4f}")
    print(f"Std: {cbr['std']:.4f}")
    print(f"Range: [{cbr['min']:.4f}, {cbr['max']:.4f}]")
    print(f"Bimodality coefficient: {cbr['bimodality_coefficient']:.4f}")
    print(f"Number of peaks: {cbr['num_peaks']}")
    status = "PASS" if cbr['is_bimodal'] else "FAIL"
    print(f"Bimodal: {status} (threshold: 0.555)")

    print(f"\n--- K_eff Analysis (Effective Scalar Count) ---")
    print(f"K_eff: {results['k_eff']:.3f}")
    status = "PASS" if results['k_eff_in_range'] else "FAIL"
    print(f"In range [2, 6]: {status}")
    print(f"Per-scalar variances: {[f'{v:.4f}' for v in results['g_t_variances'][:8]]}")

    print(f"\n--- c_t Analysis (Compute Allocation) ---")
    c_t = results['c_t']
    print(f"Mean: {c_t['mean']:.4f}")
    print(f"Std: {c_t['std']:.4f}")
    print(f"Range: [{c_t['min']:.4f}, {c_t['max']:.4f}]")

    print(f"\n--- BI Analysis (Broadcast Index) ---")
    bi = results['bi']
    print(f"Mean: {bi['mean']:.4f}")
    print(f"Std: {bi['std']:.4f}")
    print(f"Range: [{bi['min']:.4f}, {bi['max']:.4f}]")

    print(f"\n" + "=" * 60)
    print("BLUEPRINT PASS CRITERIA")
    print("=" * 60)
    criteria = results['pass_criteria']
    print(f"CBR Bimodal: {'PASS' if criteria['cbr_bimodal'] else 'FAIL'}")
    print(f"K_eff in [2,6]: {'PASS' if criteria['k_eff_in_range'] else 'FAIL'}")

    if criteria['all_passed']:
        print(f"\n>>> EMERGENCE: PASS <<<")
    else:
        print(f"\n>>> EMERGENCE: FAIL <<<")

    # Save to JSON if requested
    if args.save_json:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"emergence_analysis_{timestamp}.json"

        # Convert numpy bools to Python bools for JSON
        def convert_types(obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(v) for v in obj]
            return obj

        with open(filename, 'w') as f:
            # Remove histogram data for cleaner JSON (can be large)
            results_clean = convert_types(results.copy())
            if 'histogram' in results_clean.get('cbr', {}):
                del results_clean['cbr']['histogram']
                del results_clean['cbr']['bin_edges']
            json.dump(results_clean, f, indent=2)
        print(f"\nResults saved to: {filename}")

    # Return exit code based on pass/fail
    return 0 if criteria['all_passed'] else 1


if __name__ == "__main__":
    sys.exit(main())
