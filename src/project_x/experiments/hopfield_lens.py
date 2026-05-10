"""Post-hoc Modern Hopfield Network energy-regime analysis.

Reads `selector_snapshot` tensors saved in each result.json (cycle 3 wired this) and
computes β-effective + energy-regime classification per cell, no re-running needed.

The Modern Hopfield Network framing (Ramsauer 2020) treats the dual-rate compressed
memory's selector as a Hopfield retrieval head: at inverse-temperature β, the energy
landscape has fixed points at memory patterns; the softmax over selector scores is
the Hopfield retrieval. Three regimes:

  - sub-critical (β too low):  fuzzy retrieval — entropy near log(N), no clear pattern wins
  - capacity-edge (β at threshold): the interesting regime — top pattern dominates but
    near-misses are visible (truth_in_top3 >> top-1 correct, the fuzzy-retrieval signature)
  - super-critical (β too high): single-pattern collapse — entropy near 0, one pattern
    fixed-points regardless of query, high seed variance

We approximate β_eff = log(N) / mean_entropy (per head, then averaged across heads).
At max entropy (uniform softmax), β_eff = 1. At zero entropy (delta), β_eff -> infinity.

Regime classification (entropy ratio = mean_entropy / log(N)):
  > 0.85 -> fuzzy
  0.30 - 0.85 -> capacity-edge
  < 0.30 -> super-critical

Usage:
    python3 -m src.project_x.experiments.hopfield_lens [PREFIX]

Default prefix is 'phase7_lrc'.
"""
from __future__ import annotations

import json
import math
import pathlib
import statistics
import sys
from collections import defaultdict


def load_cells(prefix: str = "phase7_lrc") -> list[dict]:
    runs_dir = pathlib.Path("gpt-codex/runs")
    cells = []
    for cell_dir in sorted(runs_dir.glob(f"{prefix}_*")):
        result_file = cell_dir / "result.json"
        if not result_file.exists():
            continue
        try:
            r = json.loads(result_file.read_text())
        except Exception:
            continue
        cells.append({"name": cell_dir.name, "data": r})
    return cells


def parse_cell_name(name: str, prefix: str) -> tuple[str, int]:
    """phase7_lrc_sanity_heavy8_seed1337 -> ('sanity_heavy8', 1337)"""
    bare = name.replace(f"{prefix}_", "", 1)
    abl, _, seed_str = bare.rpartition("_seed")
    return abl, int(seed_str) if seed_str else 0


def beta_eff_from_entropy(mean_entropy: float, n_blocks: int) -> float:
    """β_eff = log(N) / mean_entropy. Max-entropy (uniform) → β=1. Zero entropy → β=inf."""
    if mean_entropy <= 1e-9:
        return float("inf")
    return math.log(n_blocks) / mean_entropy


def classify_regime(entropy_ratio: float) -> str:
    """entropy_ratio = mean_entropy / log(N), in [0, 1]."""
    if entropy_ratio > 0.85:
        return "fuzzy"
    if entropy_ratio > 0.30:
        return "capacity-edge"
    return "super-critical"


def analyze_cell(cell: dict) -> dict | None:
    """Pull selector_snapshot from candidate side, compute β_eff + regime per head."""
    cnd = cell["data"].get("candidate") or {}
    ss = cnd.get("selector_snapshot")
    if not ss:
        return None
    head_entropies = ss.get("entropy_per_head_mean") or []
    softmax = ss.get("softmax_mean_over_batch") or []
    if not head_entropies or not softmax:
        return None

    # softmax shape: [n_heads][n_blocks]
    n_heads = len(head_entropies)
    n_blocks = len(softmax[0]) if softmax and softmax[0] else 31
    log_n = math.log(n_blocks)

    per_head = []
    for h in range(n_heads):
        ent = head_entropies[h]
        ratio = ent / log_n if log_n > 0 else 0.0
        beta = beta_eff_from_entropy(ent, n_blocks)
        regime = classify_regime(ratio)
        sm = softmax[h] if h < len(softmax) else []
        max_mass = max(sm) if sm else 0.0
        per_head.append({
            "head": h,
            "entropy": ent,
            "entropy_ratio": ratio,
            "beta_eff": beta,
            "regime": regime,
            "max_mass": max_mass,
        })

    mean_ent = statistics.mean(head_entropies)
    mean_ratio = mean_ent / log_n if log_n > 0 else 0.0
    mean_beta = beta_eff_from_entropy(mean_ent, n_blocks)
    cell_regime = classify_regime(mean_ratio)
    mean_max_mass = statistics.mean(h["max_mass"] for h in per_head)

    return {
        "n_heads": n_heads,
        "n_blocks": n_blocks,
        "log_n": log_n,
        "per_head": per_head,
        "mean_entropy": mean_ent,
        "mean_entropy_ratio": mean_ratio,
        "mean_beta_eff": mean_beta,
        "mean_max_mass": mean_max_mass,
        "cell_regime": cell_regime,
    }


def per_ablation_summary(cells: list[dict], prefix: str) -> dict:
    by_abl: dict[str, list] = defaultdict(list)
    for cell in cells:
        abl, seed = parse_cell_name(cell["name"], prefix)
        analysis = analyze_cell(cell)
        if analysis is None:
            continue
        cnd_acc = (cell["data"].get("candidate") or {}).get("delayed_assoc_acc")
        by_abl[abl].append({
            "seed": seed,
            "analysis": analysis,
            "cnd_acc": cnd_acc,
        })

    summary = {}
    for abl, rows in sorted(by_abl.items()):
        n = len(rows)
        ents = [r["analysis"]["mean_entropy"] for r in rows]
        ratios = [r["analysis"]["mean_entropy_ratio"] for r in rows]
        betas = [r["analysis"]["mean_beta_eff"] for r in rows]
        max_masses = [r["analysis"]["mean_max_mass"] for r in rows]
        accs = [r["cnd_acc"] for r in rows if r["cnd_acc"] is not None]
        regimes = [r["analysis"]["cell_regime"] for r in rows]
        regime_counts = {k: regimes.count(k) for k in set(regimes)}

        # Pearson r between entropy_ratio and assoc_acc (sharper retrieval → higher acc?)
        if len(accs) == n and n > 2:
            ent_acc_pairs = [(r["analysis"]["mean_entropy_ratio"], r["cnd_acc"])
                             for r in rows if r["cnd_acc"] is not None]
            xs, ys = zip(*ent_acc_pairs)
            mx, my = statistics.mean(xs), statistics.mean(ys)
            num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
            den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
            r_xy = num / (den_x * den_y) if den_x * den_y > 0 else 0.0
        else:
            r_xy = None

        summary[abl] = {
            "n": n,
            "mean_entropy": statistics.mean(ents),
            "std_entropy": statistics.stdev(ents) if n > 1 else 0.0,
            "mean_entropy_ratio": statistics.mean(ratios),
            "mean_beta_eff": statistics.mean(betas) if all(b != float("inf") for b in betas) else float("inf"),
            "mean_max_mass": statistics.mean(max_masses),
            "regime_counts": regime_counts,
            "mean_cnd_acc": statistics.mean(accs) if accs else None,
            "r_entropy_acc": r_xy,
        }
    return summary


def fmt_summary(summary: dict) -> str:
    lines = []
    log_n_31 = math.log(31)
    lines.append(f"Hopfield-Lens Energy-Regime Analysis — log(N=31)={log_n_31:.3f}")
    lines.append("")
    header = f"{'ablation':<28} {'n':>2} {'mean_H':>7} {'std_H':>7} {'H/logN':>7} {'beta':>5} {'maxP':>5} {'cnd_acc':>8} {'r(H,acc)':>9} {'regime':>15}"
    lines.append(header)
    lines.append("-" * len(header))
    for abl in ['control', 'candidate_sumpool', 'candidate_sumpool_distill', 'sanity_heavy8']:
        s = summary.get(abl)
        if s is None:
            continue
        regime_str = ', '.join(f"{k}={v}" for k, v in sorted(s["regime_counts"].items(), key=lambda kv: -kv[1]))
        beta = s["mean_beta_eff"]
        beta_str = "inf" if beta == float("inf") else f"{beta:>5.2f}"
        acc_str = f"{s['mean_cnd_acc']:.3f}" if s['mean_cnd_acc'] is not None else "  --  "
        r_str = f"{s['r_entropy_acc']:+.2f}" if s['r_entropy_acc'] is not None else "  -- "
        lines.append(
            f"{abl:<28} {s['n']:>2} {s['mean_entropy']:>7.3f} {s['std_entropy']:>7.3f} "
            f"{s['mean_entropy_ratio']:>7.3f} {beta_str} {s['mean_max_mass']:>5.3f} "
            f"{acc_str:>8} {r_str:>9} {regime_str:>15}"
        )
    return "\n".join(lines)


def fmt_per_head_example(cell: dict, analysis: dict) -> str:
    """One-cell worked example showing per-head β_eff and regime."""
    lines = [f"Per-head detail — {cell['name']}:"]
    lines.append(f"  n_blocks={analysis['n_blocks']}, log(N)={analysis['log_n']:.3f}")
    for h in analysis["per_head"]:
        beta = h["beta_eff"]
        beta_str = "inf" if beta == float("inf") else f"{beta:.2f}"
        lines.append(
            f"  head[{h['head']}]: H={h['entropy']:.3f} (ratio={h['entropy_ratio']:.3f}) "
            f"β={beta_str} max_mass={h['max_mass']:.3f} regime={h['regime']}"
        )
    return "\n".join(lines)


def main(prefix: str = "phase7_lrc") -> None:
    cells = load_cells(prefix)
    print(f"Loaded {len(cells)} cells with prefix '{prefix}'")
    if not cells:
        return

    summary = per_ablation_summary(cells, prefix)
    print()
    print(fmt_summary(summary))

    # One worked example: pick a sanity_heavy8 cell (best candidate, most interesting)
    print()
    target = next((c for c in cells if "sanity_heavy8_seed1337" in c["name"]), cells[0])
    a = analyze_cell(target)
    if a:
        print(fmt_per_head_example(target, a))


if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else "phase7_lrc"
    main(prefix)
