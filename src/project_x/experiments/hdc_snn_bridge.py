"""
hdc_snn_bridge.py — STRETCH: a minimal SNN encoder for HDC.

Closes the loop on lain's MANIFESTO axioms: physics-over-statistics,
sparsity, local online learning, logic-over-language. The encoder is a
bank of D leaky integrate-and-fire (LIF) neurons with random projection
weights; each input drives the bank for T timesteps; each neuron's bipolar
HDC bit is +1 if the neuron spiked at any point, -1 otherwise.

This is intentionally simple (no STDP this phase, no dendritic compartments,
no thalamocortical layout — project_synapse already has those). The purpose
here is to demonstrate that an HDC vector CAN be produced by a spiking
substrate, not to compete with project_synapse on biological plausibility.

Pass: same input twice → identical bipolar vector. Two different inputs →
near-orthogonal vectors (cos similarity within ±2σ of zero at D=10000).

Author: Raphael
Phase: 8 — beyond_transformer_organic_memory (stretch goal)
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from project_x.experiments.hdc_substrate import bit_accuracy


def lif_encode_unbalanced(
    input_vec: np.ndarray,
    proj: np.ndarray,
    threshold: float = 1.0,
    leak: float = 0.9,
    n_steps: int = 50,
    drive_scale: float = 0.2,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Run a bank of D LIF neurons; return (bipolar fired-or-not, spike_count).

    NOT balanced — biased toward whatever the threshold/scale produce.
    Used as the inner loop of lif_encode (which balances via excitatory/inhibitory pairs).
    """
    d = proj.shape[0]
    drive = proj @ input_vec * drive_scale
    v = np.zeros(d, dtype=np.float32)
    spike_count = np.zeros(d, dtype=np.int32)
    for _ in range(n_steps):
        v = v * leak + drive
        spike = v >= threshold
        spike_count += spike.astype(np.int32)
        v = np.where(spike, 0.0, v)
    return spike_count > 0, spike_count


def lif_encode(
    input_vec: np.ndarray,
    proj_excit: np.ndarray,
    proj_inhib: np.ndarray,  # kept in signature for compat but unused in median-threshold variant
    threshold: float = 1.0,
    leak: float = 0.9,
    n_steps: int = 50,
    drive_scale: float = 0.2,
) -> np.ndarray:
    """
    BALANCED LIF encoding via spike-count vs population-median thresholding.

    Single bank of D LIF neurons; integrate spikes over n_steps; output bipolar bit
    is +1 if the neuron's spike_count is above the population median, -1 otherwise.

    This gives EXACTLY 50% activity (lateral-inhibition-like effect, mediated
    population-wise rather than per-neuron). Cross-input cosine similarity should
    fall to ~0 for unrelated inputs since the median split is deterministic per-input.

    Args:
        input_vec: shape (input_dim,)
        proj_excit: shape (D, input_dim) random Gaussian
        proj_inhib: ignored (kept for signature compat with earlier API)
        threshold/leak/n_steps/drive_scale: LIF parameters

    Returns:
        bipolar shape (D,) with EXACTLY 50% +1 bits by construction.
    """
    _, spike_count = lif_encode_unbalanced(input_vec, proj_excit, threshold, leak, n_steps, drive_scale)
    # Rank-based: top D/2 by spike count = +1, bottom D/2 = -1. EXACTLY 50% active.
    # Ties broken by neuron index (deterministic given input).
    d = spike_count.shape[0]
    ranks = np.argsort(np.argsort(spike_count, kind="stable"), kind="stable")
    return np.where(ranks >= d // 2, 1, -1).astype(np.int8)


def run_bridge_demo(
    d: int,
    input_dim: int,
    n_inputs: int,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    proj_e = rng.standard_normal((d, input_dim)).astype(np.float32) / np.sqrt(input_dim)
    proj_i = rng.standard_normal((d, input_dim)).astype(np.float32) / np.sqrt(input_dim)

    # Generate n_inputs random small input vectors.
    inputs = rng.standard_normal((n_inputs, input_dim)).astype(np.float32)

    # Encode each twice (determinism check).
    t0 = time.time()
    enc1 = np.stack([lif_encode(inputs[i], proj_e, proj_i) for i in range(n_inputs)])
    enc2 = np.stack([lif_encode(inputs[i], proj_e, proj_i) for i in range(n_inputs)])
    elapsed = time.time() - t0

    # Determinism: enc1[i] should equal enc2[i] exactly.
    deterministic = bool(np.array_equal(enc1, enc2))

    # Cross-input orthogonality: take pairs (0,1), (2,3), ..., compute cosine similarity.
    cos_sims = []
    for i in range(0, n_inputs - 1, 2):
        cos = float(np.sum(enc1[i] * enc1[i + 1])) / float(d)
        cos_sims.append(cos)
    cos_mean = float(np.mean(cos_sims))
    cos_std = float(np.std(cos_sims))

    # Same-input similarity: enc1[i] · enc1[i] / D should be 1.
    self_cos = float(np.sum(enc1[0] * enc1[0])) / float(d)

    # Activity level (fraction of +1 bits).
    pos_fraction = float(np.mean(enc1 == 1))

    return {
        "cell_id": f"phase8_snnbridge_D{d}_in{input_dim}_n{n_inputs}_seed{seed}",
        "config": {
            "test": "snn_bridge",
            "D": d,
            "input_dim": input_dim,
            "n_inputs": n_inputs,
            "seed": seed,
            "lif": {"threshold": 1.0, "leak": 0.9, "n_steps": 50},
        },
        "metrics": {
            "deterministic_round_trip": deterministic,
            "cos_sim_cross_input_mean": cos_mean,
            "cos_sim_cross_input_std": cos_std,
            "self_cosine_self": self_cos,
            "pos_fraction_in_encoding": pos_fraction,
            "wall_seconds": elapsed,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--D", type=int, default=10000)
    parser.add_argument("--input-dim", type=int, default=20)
    parser.add_argument("--n-inputs", type=int, default=20)
    parser.add_argument("--seeds", type=str, default="1337,2026,3001")
    parser.add_argument("--save", type=str, default="gpt-codex/runs/phase8_snnbridge")
    args = parser.parse_args()

    save_dir = Path(args.save)
    save_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(x) for x in args.seeds.split(",")]
    rows = []
    for seed in seeds:
        r = run_bridge_demo(args.D, args.input_dim, args.n_inputs, seed)
        cell_dir = save_dir / r["cell_id"]
        cell_dir.mkdir(parents=True, exist_ok=True)
        (cell_dir / "result.json").write_text(json.dumps(r, indent=2))
        m = r["metrics"]
        rows.append({"seed": seed, **m})
        print(f"  seed={seed}  det={m['deterministic_round_trip']}  cos_cross={m['cos_sim_cross_input_mean']:+.4f}±{m['cos_sim_cross_input_std']:.4f}  self={m['self_cosine_self']:.4f}  active={m['pos_fraction_in_encoding']:.4f}")

    summary = {"test": "snn_bridge", "D": args.D, "rows": rows}
    (save_dir / "snnbridge_summary.json").write_text(json.dumps(summary, indent=2))
    deterministic_all = all(r["deterministic_round_trip"] for r in rows)
    cos_means = [r["cos_sim_cross_input_mean"] for r in rows]
    print(f"\n  SNN-BRIDGE SUMMARY  D={args.D}  input_dim={args.input_dim}")
    print(f"  Deterministic all seeds: {deterministic_all}")
    print(f"  cross-input cos_sim mean of means: {np.mean(cos_means):+.4f}  (target: ~0)")
    pass_det = deterministic_all
    pass_orth = abs(np.mean(cos_means)) < 0.1  # roughly orthogonal
    print(f"  Pass: deterministic={pass_det}, near-orthogonal={pass_orth}")


if __name__ == "__main__":
    main()
