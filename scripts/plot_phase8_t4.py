#!/usr/bin/env python3
"""
plot_phase8_t4.py — render T4 capacity-curve charts from result.json files.

Reads gpt-codex/runs/phase8_T4/T4_summary.json and produces:
  - docs/artifacts/T4_capacity_curve.png   (item_recall vs N at D=10000, with Plate prediction)
  - docs/artifacts/T4_bit_accuracy_curve.png  (raw bit_accuracy vs N, theoretical & measured)

Author: Raphael
"""

import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plate_capacity(d: int, m_cleanup: int) -> float:
    return d / (5.4 + 4.4 * math.log2(max(m_cleanup, 2)))


def plate_bit_accuracy_predicted(n: int) -> float:
    """1 - Φ(-1/sqrt(N-1))"""
    if n <= 1:
        return 1.0
    z = 1.0 / math.sqrt(n - 1)
    return 1 - 0.5 * math.erfc(z / math.sqrt(2))


def main(t4_summary_path: Path = Path("gpt-codex/runs/phase8_T4/T4_summary.json"),
         t4_d_summary_path: Path | None = None,
         out_dir: Path = Path("docs/artifacts")):
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = json.loads(t4_summary_path.read_text())
    rows = summary["rows"]
    d = summary["D"]
    ns = sorted(set(r["N"] for r in rows))

    recall_by_n = {n: [r["item_recall"] for r in rows if r["N"] == n] for n in ns}
    bitacc_by_n = {n: [r["bit_acc_mean"] for r in rows if r["N"] == n] for n in ns}

    recall_means = [np.mean(recall_by_n[n]) for n in ns]
    recall_stds = [np.std(recall_by_n[n]) for n in ns]
    bit_means = [np.mean(bitacc_by_n[n]) for n in ns]
    bit_stds = [np.std(bitacc_by_n[n]) for n in ns]
    plate_caps = [plate_capacity(d, n) for n in ns]
    plate_bits = [plate_bit_accuracy_predicted(n) for n in ns]

    # === Figure 1: item recall vs N ===
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(ns, recall_means, yerr=recall_stds, fmt="o-", color="tab:blue",
                label="HDC item recall (3 seeds)", linewidth=2, markersize=8, capsize=5)
    # mark Plate capacity at M=N
    for n, cap in zip(ns, plate_caps):
        ax.axvline(cap, alpha=0.0)  # invisible; for context
    # shade the Plate-1995 capacity zone
    plate_cap_at_max = plate_capacity(d, max(ns))
    ax.axvspan(0, plate_cap_at_max, alpha=0.08, color="tab:green", label=f"Plate-1995 capacity zone (≤ {plate_cap_at_max:.0f})")
    ax.axhline(0.95, linestyle="--", color="tab:red", alpha=0.5, label="0.95 pass-line")
    ax.set_xscale("log")
    ax.set_xlabel("N (items stored)")
    ax.set_ylabel("Item recall after cleanup")
    ax.set_title(f"T4 — HDC capacity cliff at D={d}\n(empirical confirmation of Plate-1995 capacity bound)")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower left", fontsize=9)

    # annotate the cliff
    for n, mean in zip(ns, recall_means):
        ax.annotate(f"{mean:.2f}", (n, mean), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)

    fig.tight_layout()
    out_path = out_dir / "T4_capacity_curve.png"
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"saved {out_path}")

    # === Figure 2: bit accuracy vs N (theory vs measured) ===
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(ns, bit_means, yerr=bit_stds, fmt="o-", color="tab:blue",
                label="HDC measured bit accuracy", linewidth=2, markersize=8, capsize=5)
    ax.plot(ns, plate_bits, "s--", color="tab:orange",
            label="Plate-1995 theory: 1 − Φ(−1/√(N−1))", linewidth=1.5, markersize=7)
    ax.axhline(0.5, linestyle=":", color="grey", alpha=0.5, label="random baseline")
    ax.set_xscale("log")
    ax.set_xlabel("N (items stored)")
    ax.set_ylabel("Per-bit accuracy")
    ax.set_title(f"T4 — bit accuracy vs N at D={d}\n(measured ↔ Plate-1995 theory match-up)")
    ax.set_ylim(0.45, 1.0)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    out_path = out_dir / "T4_bit_accuracy_curve.png"
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"saved {out_path}")


if __name__ == "__main__":
    main()
