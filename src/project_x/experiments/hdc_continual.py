"""
hdc_continual.py — T3 continual learning retention test.

Setup per cell (within-capacity at D=10000):
  - At time t=1..100: write (k_t, v_t) random pairs to memory
  - Snapshot retention of items 1..100 at t=100 (full recall expected)
  - At time t=101..200: write 100 more (k, v) pairs
  - Snapshot retention of items 1..100 at t=200 (within Plate-1995 capacity ~256 at M=N=200)
  - Snapshot retention of items 101..200 at t=200 (recently written; should be high)

Pass-line: first_100_retention_at_t200 ≥ 0.90 across ≥3 seeds.

This is the "no catastrophic forgetting within capacity" test.

Author: Raphael (post-persona-shift, 2026-05-09)
Phase: 8 — beyond_transformer_organic_memory
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from project_x.experiments.hdc_substrate import (
    D_DEFAULT,
    cleanup,
    random_vector,
    read,
    write,
)


def measure_retention(memory: np.ndarray, keys_subset: np.ndarray, expected_indices_in_atom_set: np.ndarray, atom_set: np.ndarray) -> float:
    """Fraction of keys_subset that retrieve correct value via cleanup against atom_set.

    Args:
        memory: HDC accumulator
        keys_subset: keys to query, shape (n, D)
        expected_indices_in_atom_set: for each query, the index in atom_set where the correct value lives
        atom_set: full set of value atoms, shape (M, D)
    """
    n = len(keys_subset)
    correct = 0
    for i in range(n):
        retrieved = read(memory, keys_subset[i])
        snapped, idx, _ = cleanup(retrieved, atom_set)
        if idx == int(expected_indices_in_atom_set[i]):
            correct += 1
    return correct / n


def run_continual_cell(d: int, n_phase1: int, n_phase2: int, seed: int) -> dict:
    """One T3 cell. n_phase1 + n_phase2 should stay within Plate capacity."""
    rng = np.random.default_rng(seed)
    t0 = time.time()
    n_total = n_phase1 + n_phase2

    keys = np.stack([random_vector(d, rng) for _ in range(n_total)])
    values = np.stack([random_vector(d, rng) for _ in range(n_total)])

    # Phase 1: write items 0..n_phase1-1
    M: np.ndarray | None = None
    for i in range(n_phase1):
        M = write(M, keys[i], values[i])

    idx_first = np.arange(n_phase1)
    idx_last = np.arange(n_phase1, n_total)

    retention_at_t100 = measure_retention(M, keys[:n_phase1], idx_first, values[:n_phase1])

    # Phase 2: write items n_phase1..n_total-1
    for i in range(n_phase1, n_total):
        M = write(M, keys[i], values[i])

    # At t=200: cleanup against full value set (all 200 values are now stored)
    first_100_retention_at_t200 = measure_retention(M, keys[:n_phase1], idx_first, values)
    last_100_retention_at_t200 = measure_retention(M, keys[n_phase1:n_total], idx_last, values)

    # Re-measure first-100 against ONLY the first-100 atoms (stricter test of "did the first 100 survive?")
    first_100_retention_strict = measure_retention(M, keys[:n_phase1], idx_first, values[:n_phase1])

    elapsed = time.time() - t0
    return {
        "cell_id": f"phase8_T3continual_D{d}_n1{n_phase1}_n2{n_phase2}_seed{seed}",
        "config": {
            "test": "T3_continual",
            "D": d,
            "n_phase1": n_phase1,
            "n_phase2": n_phase2,
            "seed": seed,
        },
        "metrics": {
            "retention_at_t100": float(retention_at_t100),
            "first_100_retention_at_t200": float(first_100_retention_at_t200),
            "last_100_retention_at_t200": float(last_100_retention_at_t200),
            "first_100_retention_strict_atoms": float(first_100_retention_strict),
            "wall_seconds": elapsed,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--D", type=int, default=D_DEFAULT)
    parser.add_argument("--n-phase1", type=int, default=100)
    parser.add_argument("--n-phase2", type=int, default=100)
    parser.add_argument("--seeds", type=str, default="1337,2026,3001")
    parser.add_argument("--save", type=str, default="gpt-codex/runs/phase8_T3")
    args = parser.parse_args()

    save_dir = Path(args.save)
    save_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(x) for x in args.seeds.split(",")]

    rows = []
    for seed in seeds:
        r = run_continual_cell(args.D, args.n_phase1, args.n_phase2, seed)
        cell_dir = save_dir / r["cell_id"]
        cell_dir.mkdir(parents=True, exist_ok=True)
        (cell_dir / "result.json").write_text(json.dumps(r, indent=2))
        rows.append({
            "seed": seed,
            "retention_at_t100": r["metrics"]["retention_at_t100"],
            "first_100_retention_at_t200": r["metrics"]["first_100_retention_at_t200"],
            "last_100_retention_at_t200": r["metrics"]["last_100_retention_at_t200"],
            "first_100_retention_strict": r["metrics"]["first_100_retention_strict_atoms"],
            "wall_s": r["metrics"]["wall_seconds"],
        })
        print(f"  seed={seed}  t100={r['metrics']['retention_at_t100']:.4f}  first100@t200={r['metrics']['first_100_retention_at_t200']:.4f}  last100@t200={r['metrics']['last_100_retention_at_t200']:.4f}")

    summary = {
        "test": "T3_continual",
        "D": args.D,
        "n_phase1": args.n_phase1,
        "n_phase2": args.n_phase2,
        "seeds": seeds,
        "rows": rows,
        "first_100_retention_at_t200_mean": float(np.mean([r["first_100_retention_at_t200"] for r in rows])),
        "first_100_retention_at_t200_std": float(np.std([r["first_100_retention_at_t200"] for r in rows])),
    }
    (save_dir / "T3_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n  T3 summary: first_100_retention_at_t200_mean={summary['first_100_retention_at_t200_mean']:.4f} ± {summary['first_100_retention_at_t200_std']:.4f}")
    pass_line = 0.90
    status = "PASS" if summary["first_100_retention_at_t200_mean"] >= pass_line else "FAIL"
    print(f"  Pass-line {pass_line}: {status}")


if __name__ == "__main__":
    main()
