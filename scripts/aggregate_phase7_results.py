#!/usr/bin/env python3
"""Aggregate Phase 7 baseline + grid results.

Reads gpt-codex/runs/<prefix>_*/result.json, prints a summary table:
  run_id, mean_gpu_util, max_gpu_util, vram_mb, wall_s, band_passed,
  control_assoc_acc, candidate_assoc_acc, ratio, sample_gen_correct.

Usage:
    python3 scripts/aggregate_phase7_results.py [PREFIX]

PREFIX defaults to 'baseline' for the cycle-4 Step 6 scan; pass 'phase7_lrc'
for the cycle-4 Step 13 grid run.
"""
from __future__ import annotations

import json
import pathlib
import sys


def fmt_pct(x):
    if x is None: return "  -- "
    return f"{x:5.1f}"


def main(prefix: str = "baseline") -> None:
    runs_dir = pathlib.Path("gpt-codex/runs")
    cells = sorted(runs_dir.glob(f"{prefix}_*/result.json"))
    if not cells:
        print(f"No cells found for prefix '{prefix}_*' under {runs_dir}")
        return
    print(f"\n=== Phase 7 results — prefix '{prefix}' — {len(cells)} cells ===\n")
    header = f"{'run_id':<48} {'mean':>5} {'max':>5} {'vram':>7} {'wall':>7} {'band':>5} {'ctl_acc':>8} {'cnd_acc':>8} {'ratio':>6} {'sgen_ok':>8}"
    print(header)
    print("-" * len(header))
    rows: list[dict] = []
    for cell in cells:
        try:
            r = json.loads(cell.read_text())
        except Exception as e:
            print(f"[parse-error] {cell}: {e}")
            continue
        run_id = r.get("run_id", cell.parent.name)
        util = r.get("util", {}) or {}
        ctl = (r.get("control") or {}).get("delayed_assoc_acc")
        cnd = (r.get("candidate") or {}).get("delayed_assoc_acc")
        ratio = (cnd / ctl) if (ctl and cnd and ctl > 1e-9) else None
        # sample_generations correct rate (from candidate's eval; control too if present)
        sgens = (r.get("candidate") or {}).get("sample_generations") or []
        n_correct = sum(1 for g in sgens if g.get("correct"))
        sgen_ok = f"{n_correct}/{len(sgens)}" if sgens else "  --  "
        row = {
            "run_id": run_id,
            "mean_gpu": util.get("mean_gpu_util_pct"),
            "max_gpu": util.get("max_gpu_util_pct"),
            "vram_mb": util.get("vram_used_max_mib"),
            "wall_s": util.get("wall_seconds"),
            "band_passed": util.get("band_passed"),
            "ctl_acc": ctl,
            "cnd_acc": cnd,
            "ratio": ratio,
            "sgen_ok": sgen_ok,
        }
        rows.append(row)
        print(
            f"{run_id:<48} "
            f"{fmt_pct(row['mean_gpu'])} {fmt_pct(row['max_gpu'])} "
            f"{(str(row['vram_mb']) if row['vram_mb'] else '   -- '):>7} "
            f"{(f'{row['wall_s']:.1f}s' if row['wall_s'] else '  --  '):>7} "
            f"{('PASS ' if row['band_passed'] else 'FAIL '):>5} "
            f"{(f'{ctl:.3f}' if ctl is not None else '  --  '):>8} "
            f"{(f'{cnd:.3f}' if cnd is not None else '  --  '):>8} "
            f"{(f'{ratio:.2f}x' if ratio is not None else '  -- '):>6} "
            f"{sgen_ok:>8}"
        )
    # Pick best band-passing tuple by lowest wall
    band_passers = [r for r in rows if r["band_passed"]]
    if band_passers:
        best = min(band_passers, key=lambda r: r["wall_s"] or 1e9)
        print(f"\n*** BAND-PASSING WINNER: {best['run_id']} "
              f"(util {fmt_pct(best['mean_gpu'])}%, wall {best['wall_s']:.1f}s, vram {best['vram_mb']} MiB) ***")
    else:
        # No band passers — pick highest-util cell
        if rows:
            top = max(rows, key=lambda r: r["mean_gpu"] or 0)
            print(f"\n*** NO BAND PASSER — best-effort: {top['run_id']} "
                  f"(util {fmt_pct(top['mean_gpu'])}%, wall {(top['wall_s'] or 0):.1f}s) ***")


if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    main(prefix)
