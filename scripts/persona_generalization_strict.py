"""Strict-generalization persona-consistency curve.

The 2026-05-12 persona-consistency curve at
`scripts/persona_consistency_curve.py` was caught (advisor) as bigram-
overlap-bounded: three of five held-out prompts shared the bigram
"consider the" with three of eight training prompts. The curve
therefore demonstrated the atom-family mechanism working *as designed*,
not strict generalization to lexically-unrelated prompts.

This script answers the harder question: does the same substrate-wide
Hebbian update lift the held-out marker frequency when the held-out
prompts have **zero bigram overlap** with the training set? In that
regime the substrate has nothing but the prefix-atom (which differs
by leading verb) and the individual token-atom family (which can only
share common-English connectives like "the" and "of") to draw on. If
the curve still lifts, the generalization claim is broader than the
shared-bigram-atom story; if it stays flat, the prior curve's plateau
shape was the bigram-atom mechanism, full stop. Either result is an
honest finding.

Same harness as `persona_consistency_curve.py`: same markers, same
training prompts, same checkpoints, same rating policy, same audit-log
I/O path. Only the held-out prompt set changes.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

# Make sibling script importable without packaging scripts/ — keeps the
# curve harness shared between the in-distribution and strict-generalization
# variants without copying the marker / training-set definitions.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from project_x.audit.log import AuditLog
from project_x.corpus.natural_mode import NaturalModeComposer
from project_x.hdc_infra import HebbianBank

from persona_consistency_curve import (  # noqa: E402
    CHECKPOINTS,
    PERSONA_MARKERS,
    TRAINING_PROMPTS,
    aggregate,
    apply_training_ratings,
    measure_held_out,
)


RUN_ID = "claude-2026-05-12-persona-generalization-strict"


# Five held-out prompts whose bigrams are DISJOINT from every bigram
# in TRAINING_PROMPTS. Verbs at position 0 are deliberately disjoint
# from the training-set verbs ("comment" / "consider" / "what" /
# "describe") so the prefix-atom also misses; the only atom family
# that *could* share signal is the token-atom family on common-English
# connectives like "in" / "the". The substrate has to generalize past
# bigram overlap to lift the held-out marker frequency at all.
HELD_OUT_PROMPTS_STRICT: tuple[str, ...] = (
    "explore courage under adversity",
    "speak frankly about excellence today",
    "examine memory across many lifetimes",
    "evaluate truth against contested opinion",
    "trace beauty through long history",
)


def _bigrams(text: str) -> set[tuple[str, str]]:
    tokens = text.lower().split()
    return {(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)}


def assert_zero_bigram_overlap() -> dict[str, Any]:
    train_bigrams: set[tuple[str, str]] = set()
    for p in TRAINING_PROMPTS:
        train_bigrams |= _bigrams(p)
    held_bigrams: set[tuple[str, str]] = set()
    for p in HELD_OUT_PROMPTS_STRICT:
        held_bigrams |= _bigrams(p)
    overlap = train_bigrams & held_bigrams
    if overlap:
        raise RuntimeError(
            f"strict held-out set has bigram overlap with training: {sorted(overlap)}"
        )
    train_tokens: set[str] = set()
    for p in TRAINING_PROMPTS:
        train_tokens |= set(p.lower().split())
    held_tokens: set[str] = set()
    for p in HELD_OUT_PROMPTS_STRICT:
        held_tokens |= set(p.lower().split())
    shared_tokens = train_tokens & held_tokens
    return {
        "training_bigram_count": len(train_bigrams),
        "held_out_bigram_count": len(held_bigrams),
        "bigram_overlap_count": 0,
        "shared_token_count": len(shared_tokens),
        "shared_tokens": sorted(shared_tokens),
    }


def run_curve(
    *,
    output: Path,
    csv_output: Path,
    domain: str = "all",
    max_fragments: int = 3,
) -> dict[str, Any]:
    overlap_audit = assert_zero_bigram_overlap()
    bank_path = output.with_suffix(".bank.pkl")
    audit_path = output.with_suffix(".walks.jsonl")
    for path in (output, bank_path, audit_path, csv_output):
        if path.exists():
            path.unlink()

    audit_log = AuditLog(audit_path, hebbian_bank_path=bank_path)
    cumulative_applied = 0
    checkpoints_data: list[dict[str, Any]] = []

    for k in CHECKPOINTS:
        delta = k - cumulative_applied
        if delta > 0:
            train_composer = NaturalModeComposer(
                include_ingested=True,
                hebbian_bank_path=bank_path,
            )
            apply_training_ratings(
                train_composer,
                audit_log,
                TRAINING_PROMPTS,
                delta,
                domain=domain,
                max_fragments=max_fragments,
            )
            cumulative_applied = k

        eval_composer = NaturalModeComposer(
            include_ingested=True,
            hebbian_bank_path=bank_path,
        )
        bank_now = HebbianBank.load(bank_path)
        scores = measure_held_out(
            eval_composer,
            HELD_OUT_PROMPTS_STRICT,
            domain=domain,
            max_fragments=max_fragments,
        )
        agg = aggregate(scores)
        checkpoints_data.append(
            {
                "checkpoint_k": k,
                "bank_entry_count": bank_now.entry_count(),
                "aggregate": agg,
                "per_prompt": [
                    {
                        "prompt": s.prompt,
                        "marker_count": s.marker_count,
                        "marker_density": s.marker_density,
                        "fragment_sources": list(s.fragment_sources),
                    }
                    for s in scores
                ],
            }
        )

    baseline = checkpoints_data[0]["aggregate"]
    final = checkpoints_data[-1]["aggregate"]
    monotonic_steps = 0
    for prev, cur in zip(checkpoints_data, checkpoints_data[1:]):
        if cur["aggregate"]["mean_marker_count"] >= prev["aggregate"]["mean_marker_count"]:
            monotonic_steps += 1
    monotonic_fraction = monotonic_steps / max(1, len(checkpoints_data) - 1)
    delta_mean = final["mean_marker_count"] - baseline["mean_marker_count"]
    delta_fraction = (
        final["fraction_with_any_marker"] - baseline["fraction_with_any_marker"]
    )

    result = {
        "run_id": RUN_ID,
        "domain": domain,
        "max_fragments": max_fragments,
        "checkpoints": list(CHECKPOINTS),
        "training_prompts": list(TRAINING_PROMPTS),
        "held_out_prompts_strict": list(HELD_OUT_PROMPTS_STRICT),
        "markers": list(PERSONA_MARKERS),
        "overlap_audit": overlap_audit,
        "paths": {
            "json": str(output),
            "csv": str(csv_output),
            "bank": str(bank_path),
            "audit_log": str(audit_path),
        },
        "data": checkpoints_data,
        "summary": {
            "baseline_mean_marker_count": baseline["mean_marker_count"],
            "final_mean_marker_count": final["mean_marker_count"],
            "delta_mean_marker_count": delta_mean,
            "baseline_fraction_with_any_marker": baseline["fraction_with_any_marker"],
            "final_fraction_with_any_marker": final["fraction_with_any_marker"],
            "delta_fraction_with_any_marker": delta_fraction,
            "monotonic_step_fraction": monotonic_fraction,
            "shift": (
                "lift" if delta_mean > 0 or delta_fraction > 0
                else ("flat" if delta_mean == 0 and delta_fraction == 0 else "regress")
            ),
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    csv_output.parent.mkdir(parents=True, exist_ok=True)
    with csv_output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "checkpoint_k",
                "bank_entry_count",
                "mean_marker_count",
                "fraction_with_any_marker",
                "mean_marker_density",
                "min_marker_count",
                "max_marker_count",
            ]
        )
        for entry in checkpoints_data:
            agg = entry["aggregate"]
            writer.writerow(
                [
                    entry["checkpoint_k"],
                    entry["bank_entry_count"],
                    agg["mean_marker_count"],
                    agg["fraction_with_any_marker"],
                    agg["mean_marker_density"],
                    agg["min_marker_count"],
                    agg["max_marker_count"],
                ]
            )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/project-x-persona-generalization-strict.json"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("/tmp/project-x-persona-generalization-strict.csv"),
    )
    parser.add_argument("--domain", default="all")
    parser.add_argument("--max-fragments", type=int, default=3)
    args = parser.parse_args()
    result = run_curve(
        output=args.output,
        csv_output=args.csv_output,
        domain=args.domain,
        max_fragments=args.max_fragments,
    )
    print(json.dumps({"summary": result["summary"], "overlap_audit": result["overlap_audit"]}, indent=2, sort_keys=True))
    return 0  # always exit 0; the result is the curve, not a pass/fail gate


if __name__ == "__main__":
    raise SystemExit(main())
