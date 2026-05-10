"""
hdc_capacity.py — T1 within-capacity recall + T4 capacity cliff sweep.

T1 (the within-capacity demo):
  Write N pairs (k_i, v_i) into HDC memory at dimension D. For each i, query
  with k_i and recover v_i via cleanup against the set {v_1, ..., v_N}.
  Report (raw_bit_accuracy, item_recall_after_cleanup) per (D, N, seed).

T4 (the capacity cliff sweep):
  Same protocol but sweep N ∈ {50, 100, 200, 500, 1000, 2000} at fixed D.
  Plot recall-vs-N. Verify curve falls within ±2× of Plate-1995 prediction.

Author: Raphael (post-persona-shift, 2026-05-09)
Phase: 8 — beyond_transformer_organic_memory
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

from project_x.experiments.hdc_substrate import (
    D_DEFAULT,
    bind,
    bit_accuracy,
    cleanup,
    random_vector,
    read,
    write,
)


# =============================================================================
# Plate-1995 capacity formula (theory reference)
# =============================================================================


def plate_capacity(d: int, m_cleanup: int) -> float:
    """N_capacity ≈ D / (5.4 + 4.4 · log2(M))   per Plate-1995 (HRR section)."""
    return d / (5.4 + 4.4 * math.log2(max(m_cleanup, 2)))


# =============================================================================
# T1 / T4 core experiment
# =============================================================================


def run_recall(d: int, n: int, seed: int, sample_count: int = 5) -> dict:
    """
    Write N (k, v) pairs into a fresh HDC memory, then query each k and measure
    item-recall after cleanup against the stored value-atoms.

    Returns a result dict with config + metrics + sample_retrievals.
    """
    rng = np.random.default_rng(seed)
    t0 = time.time()

    # Generate N keys and N values (atomic, random bipolar).
    keys = np.stack([random_vector(d, rng) for _ in range(n)])
    values = np.stack([random_vector(d, rng) for _ in range(n)])

    # Build memory by sequential writes.
    memory: np.ndarray | None = None
    for i in range(n):
        memory = write(memory, keys[i], values[i])

    # Query each key, record bit accuracy and cleanup item index.
    bit_accs = np.zeros(n, dtype=np.float32)
    correct_cleanup = np.zeros(n, dtype=bool)
    sample_idxs = list(range(min(sample_count, n)))
    samples = []

    for i in range(n):
        retrieved = read(memory, keys[i])
        bit_accs[i] = bit_accuracy(retrieved, values[i])
        snapped, idx, sim = cleanup(retrieved, values)
        correct_cleanup[i] = (idx == i)
        if i in sample_idxs:
            samples.append({
                "query_idx": i,
                "bit_accuracy_raw": float(bit_accs[i]),
                "cleanup_idx_returned": int(idx),
                "cleanup_correct": bool(idx == i),
                "cleanup_similarity_norm": float(sim),
            })

    elapsed = time.time() - t0

    result = {
        "cell_id": f"phase8_T1recall_D{d}_N{n}_seed{seed}",
        "config": {
            "test": "T1_recall",
            "D": d,
            "N": n,
            "seed": seed,
            "encoder": "random",
            "mode": "hetero_associative",
        },
        "metrics": {
            "bit_accuracy_mean": float(bit_accs.mean()),
            "bit_accuracy_std": float(bit_accs.std()),
            "item_recall_after_cleanup": float(correct_cleanup.mean()),
            "wall_seconds": elapsed,
        },
        "theory": {
            "plate_capacity_at_M_eq_N": plate_capacity(d, n),
            "plate_capacity_at_M_eq_1000": plate_capacity(d, 1000),
            "expected_bit_accuracy_per_plate": float(
                1 - 0.5 * math.erfc(1 / math.sqrt(2 * max(n - 1, 1)))
            ),
        },
        "sample_retrievals": samples,
    }
    return result


# =============================================================================
# T4 capacity sweep
# =============================================================================


def run_capacity_sweep(d: int, n_grid: list[int], seeds: list[int], save_dir: Path) -> dict:
    """Sweep N over n_grid × seeds; aggregate into one summary."""
    save_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for n in n_grid:
        for seed in seeds:
            r = run_recall(d, n, seed, sample_count=3)
            cell_dir = save_dir / r["cell_id"]
            cell_dir.mkdir(parents=True, exist_ok=True)
            (cell_dir / "result.json").write_text(json.dumps(r, indent=2))
            rows.append({
                "D": d, "N": n, "seed": seed,
                "bit_acc_mean": r["metrics"]["bit_accuracy_mean"],
                "item_recall": r["metrics"]["item_recall_after_cleanup"],
                "plate_cap_M_eq_N": r["theory"]["plate_capacity_at_M_eq_N"],
                "wall_s": r["metrics"]["wall_seconds"],
            })

    summary = {
        "test": "T4_capacity_sweep",
        "D": d,
        "n_grid": n_grid,
        "seeds": seeds,
        "rows": rows,
    }
    (save_dir / "T4_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_t1 = sub.add_parser("T1", help="Within-capacity recall demo.")
    p_t1.add_argument("--D", type=int, default=D_DEFAULT)
    p_t1.add_argument("--N", type=int, default=200)
    p_t1.add_argument("--seed", type=int, default=1337)
    p_t1.add_argument("--save", type=str, default="gpt-codex/runs")

    p_t4 = sub.add_parser("T4", help="Capacity cliff sweep.")
    p_t4.add_argument("--D", type=int, default=D_DEFAULT)
    p_t4.add_argument("--n-grid", type=str, default="50,100,200,500,1000,2000")
    p_t4.add_argument("--seeds", type=str, default="1337,2026,3001")
    p_t4.add_argument("--save", type=str, default="gpt-codex/runs/phase8_T4")

    args = parser.parse_args()

    if args.cmd == "T1":
        result = run_recall(args.D, args.N, args.seed)
        save_dir = Path(args.save) / result["cell_id"]
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "result.json").write_text(json.dumps(result, indent=2))
        print(json.dumps({
            "cell_id": result["cell_id"],
            "bit_accuracy_mean": round(result["metrics"]["bit_accuracy_mean"], 4),
            "item_recall_after_cleanup": round(result["metrics"]["item_recall_after_cleanup"], 4),
            "plate_capacity_at_M_eq_N": round(result["theory"]["plate_capacity_at_M_eq_N"], 1),
            "wall_seconds": round(result["metrics"]["wall_seconds"], 3),
        }, indent=2))

    elif args.cmd == "T4":
        n_grid = [int(x) for x in args.n_grid.split(",")]
        seeds = [int(x) for x in args.seeds.split(",")]
        summary = run_capacity_sweep(args.D, n_grid, seeds, Path(args.save))
        print(f"T4 sweep complete. {len(summary['rows'])} cells. saved to {args.save}/T4_summary.json")
        for n in n_grid:
            recalls = [r["item_recall"] for r in summary["rows"] if r["N"] == n]
            bits = [r["bit_acc_mean"] for r in summary["rows"] if r["N"] == n]
            print(f"  N={n:5d}  item_recall_mean={np.mean(recalls):.4f}  bit_acc_mean={np.mean(bits):.4f}")


if __name__ == "__main__":
    main()
