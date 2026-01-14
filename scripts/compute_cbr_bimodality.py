#!/usr/bin/env python3
"""
Compute CBR (Compute Burst Ratio) Bimodality from Multi-Task Checkpoint.

Per BLUEPRINT.md: CBR_t should be bimodal (Sarle's coefficient > 0.555).
This indicates the brain switches between compute/not-compute phases.

Usage:
    python scripts/compute_cbr_bimodality.py
"""

import sys
from pathlib import Path
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.rpj_brain import RPJBrain, RPJConfig
from src.benchmarks.multitask_ccb import create_multitask_ccb


def compute_bimodality_coefficient(data: np.ndarray) -> float:
    """
    Compute Sarle's bimodality coefficient.

    B = (skewness^2 + 1) / kurtosis

    B > 5/9 (0.555) suggests bimodality.
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

    # Bimodality coefficient - using non-excess kurtosis
    adjusted_kurtosis = kurtosis + 3

    if adjusted_kurtosis < 1e-8:
        return 0.0

    b = (skewness ** 2 + 1) / adjusted_kurtosis
    return b


def compute_k_eff(g_t: torch.Tensor) -> float:
    """
    Compute effective neuromodulator count via participation ratio.

    K_eff = (Σ|g_i|)² / Σ(g_i²)
    """
    g_abs = g_t.abs()
    l1 = g_abs.sum(dim=-1)
    l2_sq = (g_abs ** 2).sum(dim=-1)

    k_eff = (l1 ** 2) / (l2_sq + 1e-8)
    return k_eff.mean().item()


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    checkpoint_path = "results/checkpoint_multitask_ccb_final_50331648.pt"

    print("=" * 60)
    print("CBR BIMODALITY ANALYSIS")
    print("=" * 60)
    print(f"Device: {device}")
    print(f"Checkpoint: {checkpoint_path}")

    # Load checkpoint
    print("\n[1/4] Loading checkpoint...")
    checkpoint = torch.load(checkpoint_path, map_location=device)

    config = checkpoint.get('config', {})
    state_dict = checkpoint['brain_state_dict']

    # Infer num_envs from adapter shape (batched plasticity)
    num_envs = 1
    if 'plasticity.recurrent_adapter.A' in state_dict:
        adapter_shape = state_dict['plasticity.recurrent_adapter.A'].shape
        if len(adapter_shape) == 3:  # [num_envs, out_dim, rank]
            num_envs = adapter_shape[0]
            print(f"  Detected batched plasticity: num_envs={num_envs}")

    brain_config = RPJConfig(
        obs_dim=config.get('obs_dim', 2),
        action_bytes=config.get('action_bytes', 1),
        hidden_dim=config.get('hidden_dim', 512),
        k_max=config.get('k_max', 4),
        lambda_g=0.01,
        enable_plasticity=True,
        enable_sleep=False,
        num_envs=num_envs,  # Use detected num_envs for batched plasticity
    )

    brain = RPJBrain(brain_config)
    brain.load_state_dict(state_dict, strict=False)
    brain.to(device)
    brain.eval()

    print(f"  Parameters: {sum(p.numel() for p in brain.parameters()):,}")

    # Create environment
    print("\n[2/4] Creating multi-task environment...")
    env = create_multitask_ccb(
        num_tasks=100,
        nonlinear=True,
        device=device,
        steps_per_task=10,
        success_threshold=0.3,
    )

    # Collect metrics during inference
    print("\n[3/4] Collecting inference metrics (10 tasks x 50 steps)...")

    all_g_l1 = []
    all_k_eff = []
    all_g_values = []

    num_eval_tasks = 10
    steps_per_task = 50

    for task_id in range(num_eval_tasks):
        obs, _ = env.reset(task_id=task_id)
        obs = obs.to(device)

        h = torch.zeros(1, brain.substrate.hidden_dim, device=device)
        g_prev = torch.zeros(1, brain_config.k_max, device=device)
        a_prev = torch.zeros(1, dtype=torch.long, device=device)

        for step in range(steps_per_task):
            with torch.no_grad():
                output = brain.forward(
                    obs.unsqueeze(0).float(),
                    h,
                    g_prev,
                    a_prev,
                    training=False,
                )

            g_t = output.g_t

            # Collect metrics
            g_l1 = g_t.abs().sum(dim=-1).item()
            k_eff = compute_k_eff(g_t)

            all_g_l1.append(g_l1)
            all_k_eff.append(k_eff)
            all_g_values.append(g_t.cpu().numpy().flatten())

            # Step
            action = output.action.squeeze()
            next_obs, _, terminated, truncated, _ = env.step(action)

            h = output.h_next
            g_prev = output.g_t
            a_prev = action.unsqueeze(0) if action.dim() == 0 else action
            obs = next_obs.to(device)

            if terminated or truncated:
                break

        print(f"  Task {task_id + 1}/{num_eval_tasks} done")

    all_g_l1 = np.array(all_g_l1)
    all_k_eff = np.array(all_k_eff)
    all_g_values = np.array(all_g_values)

    # Compute bimodality
    print("\n[4/4] Computing bimodality coefficients...")

    # CBR proxy: g_L1 (total neuromodulator activity)
    # High g_L1 = "compute burst", Low g_L1 = "habituated/idle"
    cbr_bimodality = compute_bimodality_coefficient(all_g_l1)
    k_eff_bimodality = compute_bimodality_coefficient(all_k_eff)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    print(f"\n=== g_L1 (CBR Proxy) Distribution ===")
    print(f"  Mean: {np.mean(all_g_l1):.4f}")
    print(f"  Std:  {np.std(all_g_l1):.4f}")
    print(f"  Min:  {np.min(all_g_l1):.4f}")
    print(f"  Max:  {np.max(all_g_l1):.4f}")
    print(f"  Bimodality: {cbr_bimodality:.4f}")
    cbr_pass = cbr_bimodality > 0.555
    print(f"  PASS (> 0.555): {'YES' if cbr_pass else 'NO'}")

    print(f"\n=== K_eff Distribution ===")
    print(f"  Mean: {np.mean(all_k_eff):.4f}")
    print(f"  Std:  {np.std(all_k_eff):.4f}")
    print(f"  Min:  {np.min(all_k_eff):.4f}")
    print(f"  Max:  {np.max(all_k_eff):.4f}")
    print(f"  Bimodality: {k_eff_bimodality:.4f}")

    # Per-scalar analysis
    print(f"\n=== Per-Scalar Variance (g_i) ===")
    for i in range(all_g_values.shape[1]):
        var = np.var(all_g_values[:, i])
        print(f"  g_{i}: var={var:.6f}")

    # Histogram for understanding distribution
    print(f"\n=== g_L1 Histogram (10 bins) ===")
    hist, edges = np.histogram(all_g_l1, bins=10)
    for i in range(len(hist)):
        bar = '#' * (hist[i] // 5 + 1) if hist[i] > 0 else ''
        print(f"  [{edges[i]:.3f}-{edges[i+1]:.3f}]: {hist[i]:3d} {bar}")

    print("\n" + "=" * 60)
    print("BLUEPRINT VALIDATION")
    print("=" * 60)
    print(f"  CBR Bimodal (> 0.555): {'PASS' if cbr_pass else 'FAIL'} ({cbr_bimodality:.4f})")

    # Save results
    results = {
        'g_l1_values': all_g_l1,
        'k_eff_values': all_k_eff,
        'cbr_bimodality': cbr_bimodality,
        'k_eff_bimodality': k_eff_bimodality,
        'cbr_pass': cbr_pass,
    }
    torch.save(results, 'results/cbr_analysis.pt')
    print(f"\nResults saved to: results/cbr_analysis.pt")

    return cbr_pass


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)
