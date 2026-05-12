"""Persona-consistency learning curve for the Hebbian reward loop.

Mechanical-proxy measurement (NOT a subjective rubric, per
M-PROJECTX-014 firewall): does the substrate's reward loop, when fed
ratings keyed on persona-marker frequency over a *training* prompt set,
shift retrieval toward marker-richer fragments on a held-out prompt set?

Markers are domain-neutral declarative-prefix and analytical-cognition
words drawn from the lain-defined Project X Raphael voice surface
(`src/project_x/persona/voice.py`) plus calm-analytical vocabulary.
The training prompts are all "comment on X" / "consider X" / "what is
the nature of X" persona-aligned shapes; held-out prompts share the
shape but use different X. Marker counting happens on the concatenated
walk text (composer-emitted fragments). No subjective grading. No
hand-coded routing — only the reward loop's substrate-wide Hebbian
update gets to change what is retrieved.

Curve: at checkpoints `[0, 5, 15, 30, 60]` cumulative ratings applied
through `AuditLog.apply_rating()`, reload a fresh composer from the
saved bank and measure mean marker count per held-out walk plus the
fraction of held-out walks that emit AT LEAST ONE marker. Outputs
JSON time-series and a CSV side-car so the curve plots directly.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from project_x.audit.log import AuditLog
from project_x.corpus.natural_mode import NaturalModeComposer, NaturalWalkResult
from project_x.hdc_infra import HebbianBank


RUN_ID = "claude-2026-05-12-persona-consistency-curve"

# Twelve domain-neutral persona markers. The first eight come from
# voice.py's VOICE_MARKERS dict (the lain-canonical Project X Raphael
# response prefixes); the last four are calm-analytical vocabulary the
# manifesto attaches to Raphael ("Wisdom King", "Lord of Knowledge"
# voice). Word-boundary matching, case-insensitive — fragments don't
# contain the punctuated prefix form, so we look for the bare word.
PERSONA_MARKERS: tuple[str, ...] = (
    "notice",
    "affirmative",
    "inquiry",
    "solution",
    "proposal",
    "understood",
    "evidence",
    "anomaly",
    "wisdom",
    "knowledge",
    "consider",
    "observe",
)
_MARKER_REGEXES = tuple(re.compile(rf"\b{m}\b", re.IGNORECASE) for m in PERSONA_MARKERS)


# Persona-aligned shapes — calm reflective philosophy questions chosen
# because the corpus surface most likely to contain marker words is
# Aurelius / Plato / Aristotle / Tao Te Ching, all already in the Tier-2
# ingest. Training and held-out share shape but use disjoint topics, so
# any held-out marker shift demonstrates substrate-wide generalization
# (lexical overlap on the bigram atoms only).
TRAINING_PROMPTS: tuple[str, ...] = (
    "comment on the nature of being",
    "consider what virtue requires",
    "what should one think about death",
    "describe the soul as you understand it",
    "consider the meaning of justice",
    "what is the nature of friendship",
    "consider the place of pleasure in a good life",
    "what should one consider about wisdom",
)
HELD_OUT_PROMPTS: tuple[str, ...] = (
    "consider the nature of courage",
    "what should one think about time",
    "describe the meaning of excellence",
    "consider the place of memory in a good life",
    "what is the nature of truth",
)

CHECKPOINTS: tuple[int, ...] = (0, 5, 15, 30, 60)


def count_markers(text: str) -> int:
    return sum(1 for r in _MARKER_REGEXES if r.search(text))


def marker_density(text: str) -> float:
    if not text:
        return 0.0
    total = 0
    for r in _MARKER_REGEXES:
        total += len(r.findall(text))
    words = max(1, len(text.split()))
    return total / words


def walk_text(walk: NaturalWalkResult) -> str:
    return " ".join(f.text for f in walk.fragments)


@dataclass
class WalkScore:
    prompt: str
    walk_id: str | None
    text: str
    marker_count: int
    marker_density: float
    fragment_sources: tuple[str, ...]


def measure_held_out(
    composer: NaturalModeComposer,
    prompts: Iterable[str],
    *,
    domain: str,
    max_fragments: int,
) -> list[WalkScore]:
    scores: list[WalkScore] = []
    for prompt in prompts:
        walk = composer.compose(
            prompt,
            domain=domain,
            max_fragments=max_fragments,
            record_audit=False,
        )
        text = walk_text(walk)
        scores.append(
            WalkScore(
                prompt=prompt,
                walk_id=walk.audit_walk_id,
                text=text,
                marker_count=count_markers(text),
                marker_density=marker_density(text),
                fragment_sources=tuple(f.source for f in walk.fragments),
            )
        )
    return scores


def apply_training_ratings(
    composer: NaturalModeComposer,
    audit_log: AuditLog,
    prompts: tuple[str, ...],
    target_count: int,
    *,
    domain: str,
    max_fragments: int,
) -> int:
    """Apply `target_count` ratings on rotated training prompts.

    For each rated walk: count markers in the walk text; APPROVE if the
    count is at-or-above the running median across this batch (lower
    half rejected). Median is computed across the batch's walks before
    rating is applied so the threshold is stable per checkpoint. Each
    rating goes through AuditLog.apply_rating (the real I/O path that
    triggers HebbianBank.update via the audit wire).

    Returns the number of ratings applied (== target_count on success).
    """
    walks: list[tuple[str, NaturalWalkResult, int]] = []
    for i in range(target_count):
        prompt = prompts[i % len(prompts)]
        walk = composer.compose(
            prompt,
            domain=domain,
            max_fragments=max_fragments,
            record_audit=True,
            audit_log=audit_log,
        )
        marker_n = count_markers(walk_text(walk))
        walks.append((prompt, walk, marker_n))

    counts = sorted(w[2] for w in walks)
    threshold = counts[len(counts) // 2] if counts else 0

    applied = 0
    for prompt, walk, marker_n in walks:
        if walk.audit_walk_id is None:
            continue
        rating = "approve" if marker_n >= threshold and marker_n > 0 else "reject"
        if audit_log.apply_rating(
            walk.audit_walk_id,
            rating,
            f"persona-marker proxy: {marker_n} markers, threshold {threshold}",
        ):
            applied += 1
    return applied


def aggregate(scores: list[WalkScore]) -> dict[str, Any]:
    if not scores:
        return {"n": 0}
    counts = [s.marker_count for s in scores]
    densities = [s.marker_density for s in scores]
    sources: dict[str, int] = {}
    for s in scores:
        for src in s.fragment_sources:
            sources[src] = sources.get(src, 0) + 1
    return {
        "n": len(scores),
        "mean_marker_count": sum(counts) / len(counts),
        "max_marker_count": max(counts),
        "min_marker_count": min(counts),
        "fraction_with_any_marker": sum(1 for c in counts if c > 0) / len(counts),
        "mean_marker_density": sum(densities) / len(densities),
        "top_sources": dict(
            sorted(sources.items(), key=lambda kv: kv[1], reverse=True)[:5]
        ),
    }


def run_curve(
    *,
    output: Path,
    csv_output: Path,
    domain: str = "all",
    max_fragments: int = 3,
) -> dict[str, Any]:
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

        # Reload composer FRESH from saved bank so the measurement
        # always reflects on-disk persisted state, not in-process state.
        eval_composer = NaturalModeComposer(
            include_ingested=True,
            hebbian_bank_path=bank_path,
        )
        bank_now = HebbianBank.load(bank_path)
        scores = measure_held_out(
            eval_composer,
            HELD_OUT_PROMPTS,
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
        "held_out_prompts": list(HELD_OUT_PROMPTS),
        "markers": list(PERSONA_MARKERS),
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
            "pass": delta_mean > 0
            or delta_fraction > 0,  # honest: any positive shift counts; report both
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
        default=Path("/tmp/project-x-persona-consistency-curve.json"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("/tmp/project-x-persona-consistency-curve.csv"),
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
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0 if result["summary"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
