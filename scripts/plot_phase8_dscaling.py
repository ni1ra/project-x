#!/usr/bin/env python3
"""
plot_phase8_dscaling.py — render the cross-D capacity chart.

Loads all phase8_T4* T4_summary.json files, plots item_recall vs N for each D,
shows how the cliff moves rightward as D scales. Pass-line at 0.95 marked.

Saves docs/artifacts/T4_dscaling_curves.png.
"""

import json
import math
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plate_capacity(d: int, m_cleanup: int) -> float:
    return d / (5.4 + 4.4 * math.log2(max(m_cleanup, 2)))


def main():
    runs_dir = Path("gpt-codex/runs")
    summaries = []
    for sub in sorted(runs_dir.glob("phase8_T4*")):
        f = sub / "T4_summary.json"
        if f.exists():
            data = json.loads(f.read_text())
            summaries.append((data["D"], data))

    if not summaries:
        print("no T4 summaries found")
        sys.exit(1)

    summaries.sort()
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(summaries)))

    for color, (d, summary) in zip(colors, summaries):
        rows = summary["rows"]
        ns = sorted(set(r["N"] for r in rows))
        recall_means = [np.mean([r["item_recall"] for r in rows if r["N"] == n]) for n in ns]
        recall_stds = [np.std([r["item_recall"] for r in rows if r["N"] == n]) for n in ns]
        ax.errorbar(ns, recall_means, yerr=recall_stds, fmt="o-",
                    color=color, label=f"D = {d:,}",
                    linewidth=2, markersize=7, capsize=4)

    ax.axhline(0.95, linestyle="--", color="tab:red", alpha=0.5, label="0.95 pass-line")
    ax.set_xscale("log")
    ax.set_xlabel("N (items stored)")
    ax.set_ylabel("Item recall after cleanup")
    ax.set_title("HDC capacity vs items — cliff moves rightward as D scales\n(Plate-1995 capacity bound: N ~ D/(5.4 + 4.4·log₂ M))")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower left", fontsize=10)
    fig.tight_layout()

    out_path = Path("docs/artifacts/T4_dscaling_curves.png")
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    print(f"saved {out_path}")

    # Also a "cliff position" plot — at what N does recall first dip below 0.95?
    fig, ax = plt.subplots(figsize=(8, 5))
    ds = []
    cliffs_empirical = []
    cliffs_theory = []
    for d, summary in summaries:
        rows = summary["rows"]
        ns = sorted(set(r["N"] for r in rows))
        recall_means = [np.mean([r["item_recall"] for r in rows if r["N"] == n]) for n in ns]
        # find first N where recall drops below 0.95
        cliff_n = None
        for n, r in zip(ns, recall_means):
            if r < 0.95:
                cliff_n = n
                break
        if cliff_n is None:
            cliff_n = ns[-1]  # everything recalled cleanly within sweep range
        ds.append(d)
        cliffs_empirical.append(cliff_n)
        cliffs_theory.append(plate_capacity(d, max(ns)))

    ax.plot(ds, cliffs_empirical, "o-", color="tab:blue", label="empirical cliff (first N with recall < 0.95)", markersize=10, linewidth=2)
    ax.plot(ds, cliffs_theory, "s--", color="tab:orange", label="Plate-1995 theory cap", markersize=8, linewidth=1.5)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("D (vector dimensionality)")
    ax.set_ylabel("Cliff position N (items)")
    ax.set_title("HDC capacity scales linearly with D — empirical confirmation of Plate-1995")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=10)
    fig.tight_layout()

    out_path2 = Path("docs/artifacts/T4_cliff_vs_D.png")
    fig.savefig(out_path2, dpi=120)
    plt.close(fig)
    print(f"saved {out_path2}")


if __name__ == "__main__":
    main()
