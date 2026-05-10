"""
hdc_compose.py — T2 compositional binding battery.

Tests whether HDC can store role-filler bindings and retrieve a filler given
its role, with cleanup against a known dictionary of candidate fillers.

Setup per run:
  - role atoms:    R = 10 random bipolar vectors {role_0, ..., role_9}
  - filler atoms:  F = 100 random bipolar vectors (large dictionary for cleanup)
  - bindings:      M = sum_i bind(role_i, filler_pi[i])
                   where pi is a random permutation of [0..R-1] selecting fillers
  - query:         for each i, unbind(M, role_i) then cleanup against F
  - pass-line:     compositional_accuracy ≥ 0.80 (mean over 10 queries × 3 seeds)

This is the within-capacity composition test: 10 bindings + 100 candidate
fillers is well below Plate-1995 capacity at D=10000.

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
    bind,
    bit_accuracy,
    cleanup,
    random_vector,
    read,
    unbind,
    write,
)


def run_compose_cell(d: int, n_bindings: int, n_filler_atoms: int, seed: int) -> dict:
    """One T2 cell."""
    rng = np.random.default_rng(seed)
    t0 = time.time()

    roles = np.stack([random_vector(d, rng) for _ in range(n_bindings)])
    fillers = np.stack([random_vector(d, rng) for _ in range(n_filler_atoms)])
    binding_indices = rng.permutation(n_filler_atoms)[:n_bindings]
    bound_fillers = fillers[binding_indices]

    M: np.ndarray | None = None
    for i in range(n_bindings):
        M = write(M, roles[i], bound_fillers[i])

    correct = np.zeros(n_bindings, dtype=bool)
    bit_acc = np.zeros(n_bindings, dtype=np.float32)
    samples = []
    for i in range(n_bindings):
        retrieved = read(M, roles[i])
        bit_acc[i] = bit_accuracy(retrieved, bound_fillers[i])
        snapped, idx, sim = cleanup(retrieved, fillers)
        correct[i] = (idx == int(binding_indices[i]))
        if i < 5:
            samples.append({
                "role_idx": int(i),
                "true_filler_idx": int(binding_indices[i]),
                "retrieved_cleanup_idx": int(idx),
                "retrieved_similarity_norm": float(sim),
                "raw_bit_accuracy": float(bit_acc[i]),
                "correct": bool(idx == int(binding_indices[i])),
            })

    elapsed = time.time() - t0
    return {
        "cell_id": f"phase8_T2compose_D{d}_N{n_bindings}_F{n_filler_atoms}_seed{seed}",
        "config": {
            "test": "T2_compose",
            "D": d,
            "n_bindings": n_bindings,
            "n_filler_atoms": n_filler_atoms,
            "seed": seed,
        },
        "metrics": {
            "compositional_accuracy": float(correct.mean()),
            "bit_accuracy_mean": float(bit_acc.mean()),
            "bit_accuracy_std": float(bit_acc.std()),
            "wall_seconds": elapsed,
        },
        "sample_retrievals": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--D", type=int, default=D_DEFAULT)
    parser.add_argument("--n-bindings", type=int, default=10)
    parser.add_argument("--n-filler-atoms", type=int, default=100)
    parser.add_argument("--seeds", type=str, default="1337,2026,3001")
    parser.add_argument("--save", type=str, default="gpt-codex/runs/phase8_T2")
    args = parser.parse_args()

    save_dir = Path(args.save)
    save_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(x) for x in args.seeds.split(",")]

    rows = []
    for seed in seeds:
        r = run_compose_cell(args.D, args.n_bindings, args.n_filler_atoms, seed)
        cell_dir = save_dir / r["cell_id"]
        cell_dir.mkdir(parents=True, exist_ok=True)
        (cell_dir / "result.json").write_text(json.dumps(r, indent=2))
        rows.append({
            "seed": seed,
            "compositional_accuracy": r["metrics"]["compositional_accuracy"],
            "bit_accuracy_mean": r["metrics"]["bit_accuracy_mean"],
            "wall_s": r["metrics"]["wall_seconds"],
        })
        print(f"  seed={seed}  compositional_accuracy={r['metrics']['compositional_accuracy']:.4f}  bit_acc={r['metrics']['bit_accuracy_mean']:.4f}  wall={r['metrics']['wall_seconds']:.3f}s")

    summary = {
        "test": "T2_compose",
        "D": args.D,
        "n_bindings": args.n_bindings,
        "n_filler_atoms": args.n_filler_atoms,
        "seeds": seeds,
        "rows": rows,
        "compositional_accuracy_mean": float(np.mean([r["compositional_accuracy"] for r in rows])),
        "compositional_accuracy_std": float(np.std([r["compositional_accuracy"] for r in rows])),
    }
    (save_dir / "T2_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n  T2 summary: compositional_accuracy_mean={summary['compositional_accuracy_mean']:.4f} ± {summary['compositional_accuracy_std']:.4f}")
    pass_line = 0.80
    status = "PASS" if summary["compositional_accuracy_mean"] >= pass_line else "FAIL"
    print(f"  Pass-line {pass_line}: {status}")


if __name__ == "__main__":
    main()
