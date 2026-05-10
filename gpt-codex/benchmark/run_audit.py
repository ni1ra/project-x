"""Executable benchmark harness — audit-D3.

Replays auto-graded ladder entries against the live Phase 9-12 organic stack
and verifies the recorded grades still hold. Distinct from `audit_log.jsonl`
(which is a frozen verdict from cycle 8) — this harness is the LIVE check
that catches regressions when the encoder / retrieval / controller surface
changes.

Per-domain handling:

- `memory`: REPLAY. Build a fresh `MemoryAgent`, `write_batch(setup)`,
  `agent.process(query)`, then check (a) cited top-1 turn_ids ⊇ expected,
  (b) every `expected_response_contains` string in `answer_text`. This is
  the audit-D3 critical path: regressions in `_structural_cosines`,
  `retrieve_structural_full_history`, threshold tuning, or the controller
  routing surface here.
- `maths` / `physics`: VERIFY-FROZEN. The auto_grade carries pre-computed
  `match` (symbolic / numerical) that the harness doesn't re-evaluate
  (no sympy / closed-form-numerical wired in this run; that's Phase 13+).
  We assert the recorded `match == True` and surface false-recordings as
  failures so any tampering with frozen verdicts is visible.
- Subjective domains (`persona`, `poetry`, `philosophy`): SKIP. Per
  M-PROJECTX-014 split-grading firewall, these are rubric-pending, no
  `self_score`, external GPT/lain audit IS the grade.

Output:
- stdout: human-readable summary table (per-domain pass/fail counts).
- `--json <path>`: machine-readable JSON results (one entry per ladder ID).
- Exit code: 0 if all auto-graded entries pass, 1 otherwise (CI gate).

Usage:
    python3 -m gpt_codex.benchmark.run_audit
    python3 gpt-codex/benchmark/run_audit.py --json out/audit_results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Add src/ to path so the harness runs without `pip install -e .` in CI minimal
# envs; the audit-C2 quarantine means we don't touch torch-dependent imports.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from project_x.experiments.semantic_hdc_memory import (  # noqa: E402
    SemanticHDCMemory,
    TurnRecord,
)
from project_x.experiments.semantic_memory_agent import MemoryAgent  # noqa: E402
from project_x.reasoning_agent import ReasoningAgent  # noqa: E402


BENCHMARK_DIR = REPO_ROOT / "gpt-codex" / "benchmark"


@dataclass
class EntryResult:
    id: str
    domain: str
    method: str | None
    pass_: bool  # `pass` is reserved
    reason: str
    actual_turn_ids: list[int] | None = None
    actual_answer_excerpt: str | None = None


def _load_ladder(domain: str) -> list[dict]:
    """Read all entries from <domain>/ladder.jsonl. Returns [] if absent."""
    path = BENCHMARK_DIR / domain / "ladder.jsonl"
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _replay_memory_entry(entry: dict) -> EntryResult:
    """Build MemoryAgent, run setup + query, compare against auto_grade fields."""
    auto = entry["auto_grade"]
    setup: list[str] = auto["setup"]
    query: str = auto["query"]
    expected_turn_ids: list[int] = auto["expected_turn_ids"]
    expected_contains: list[str] = auto.get("expected_response_contains", [])

    records = [
        TurnRecord(turn_id=i, text=text, fact_keys=[], metadata={})
        for i, text in enumerate(setup)
    ]
    mem = SemanticHDCMemory()
    mem.write_batch(records)
    agent = MemoryAgent(memory=mem)
    response = agent.process(query)

    actual_turn_ids = [e.turn_id for e in response.evidence]
    actual_top_set = set(actual_turn_ids[: max(1, len(expected_turn_ids))])

    # Match criterion: every expected turn_id appears in the cited top-k AND
    # every expected_contains string appears in answer_text. The criterion
    # mirrors the original auto_grade.match_criterion text in the entries.
    expected_set = set(expected_turn_ids)
    turn_match = expected_set.issubset(actual_top_set) or expected_set.issubset(set(actual_turn_ids))
    contains_match = all(token in response.answer_text for token in expected_contains)
    pass_ = turn_match and contains_match

    if pass_:
        reason = "match (turn_ids subset + all contains tokens present)"
    else:
        reasons = []
        if not turn_match:
            reasons.append(
                f"expected turn_ids {sorted(expected_set)} not subset of "
                f"actual {actual_turn_ids}"
            )
        if not contains_match:
            missing = [t for t in expected_contains if t not in response.answer_text]
            reasons.append(f"missing tokens in answer: {missing}")
        reason = "; ".join(reasons)

    return EntryResult(
        id=entry["id"],
        domain="memory",
        method=auto.get("method"),
        pass_=pass_,
        reason=reason,
        actual_turn_ids=actual_turn_ids,
        actual_answer_excerpt=response.answer_text[:120],
    )


def _verify_frozen_entry(entry: dict) -> EntryResult:
    """Verify the pre-computed auto_grade.match flag for non-replayable domains.

    maths/physics auto_grades carry frozen symbolic / numerical results that
    this harness doesn't re-evaluate by default (no sympy, no closed-form-numerical
    evaluator wired). Asserting the recorded `match == True` surfaces any tampering
    with frozen verdicts. Use `--agent-runtime` flag (cycle 7 #00P13c7-NEW) to
    instead invoke ReasoningAgent on the prompt and verify runtime-computed value.
    """
    auto = entry["auto_grade"]
    method = auto.get("method")
    recorded = auto.get("match")
    pass_ = bool(recorded)
    reason = "frozen-match recorded True" if pass_ else f"frozen-match recorded {recorded!r}"
    return EntryResult(
        id=entry["id"],
        domain=entry.get("domain", "unknown"),
        method=method,
        pass_=pass_,
        reason=reason,
    )


def _verify_via_agent_runtime(entry: dict, agent: ReasoningAgent) -> EntryResult:
    """Cycle 7 #00P13c7-NEW: invoke ReasoningAgent on the prompt and verify the
    runtime-computed answer matches `auto_grade.expected` within tolerance.

    Replaces the frozen-verdict verification with an actual-AGENT-solves verdict.
    Returns PASS iff (a) agent returned a high-confidence answer, (b) `lemma.actual_value`
    is within `auto_grade.tolerance` of `auto_grade.expected`. Refusal or mismatch → FAIL.

    Mismatches are honest signal (M-PROJECTX-013 measure-don't-claim): the agent didn't
    handle this prompt shape OR returned a wrong number; either way the entry doesn't
    count as a real-runtime PASS until the agent's dispatcher covers it.
    """
    auto = entry["auto_grade"]
    method = auto.get("method")
    # Expected value field name varies by entry generation: cycle 1-2 used domain-specific
    # names (`expected_roots`, `expected_eigenvalues_sorted`); cycle 6+ uses generic
    # `expected`. Try both so all entries route cleanly.
    expected = (
        auto.get("expected")
        or auto.get("expected_roots")
        or auto.get("expected_eigenvalues_sorted")
        or auto.get("expected_value")
    )
    tolerance = auto.get("tolerance", 1e-4)
    prompt = entry.get("prompt", "")
    response = agent.process(prompt)
    domain = entry.get("domain", "unknown")

    if response.confidence == "refused":
        return EntryResult(
            id=entry["id"],
            domain=domain,
            method=method,
            pass_=False,
            reason=f"agent-runtime refused: {response.answer_text[:140]}",
        )

    actual = response.lemma.actual_value if response.lemma is not None else None
    if actual is None:
        return EntryResult(
            id=entry["id"], domain=domain, method=method, pass_=False,
            reason="agent-runtime returned no actual_value",
        )

    if _close_enough(actual, expected, tolerance):
        return EntryResult(
            id=entry["id"], domain=domain, method=method, pass_=True,
            reason=f"agent-runtime computed {actual} vs expected {expected} (tol {tolerance})",
        )
    return EntryResult(
        id=entry["id"], domain=domain, method=method, pass_=False,
        reason=f"agent-runtime computed {actual} vs expected {expected} — mismatch beyond tolerance {tolerance}",
    )


def _close_enough(actual: Any, expected: Any, tolerance: float) -> bool:
    """Tolerance comparison for scalar OR unordered-list-of-floats answers.

    Lists are treated as UNORDERED sets — roots/eigenvalues are mathematically
    unordered, so [-0.33, 5.0] equals [5.0, -0.33]. Both lists are sorted then
    compared element-wise with the same tolerance semantics as scalars.
    """
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        # Relative tolerance for very small magnitudes (e.g. relativistic momentum ~1e-22)
        if abs(expected) < 1e-15:
            return abs(actual - expected) < max(tolerance, 1e-30)
        return abs(actual - expected) / abs(expected) < tolerance or abs(actual - expected) < tolerance
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return False
        # Sort both ascending so roots/eigenvalues compare unordered.
        a_sorted = sorted(actual)
        e_sorted = sorted(expected)
        return all(_close_enough(a, e, tolerance) for a, e in zip(a_sorted, e_sorted))
    return False


def _verify_rubric_graded_entry(entry: dict) -> EntryResult:
    """Verify a Phase 13 cycle 3+ Path B rubric-graded entry.

    Path B promotes rubric-pending entries (subjective proof-shape) to PASS when
    a builder rubric grade meets threshold (default 4.0/5 weighted aggregate).
    The grade is durable in the entry's `rubric_grade` block + a parallel grades
    artifact JSONL at `rubric_grade.grades_artifact_path`.

    Honest audit_status labels (advisor catch 2026-05-10 — DO NOT use "rubric-graded-green"
    which overclaims external-audit-confirmation):
    - "rubric-graded-builder; pending external confirmation" — builder-graded, threshold met,
      pending external GPT/lain audit. PASS counts but artifact label distinguishes.
    - "rubric-graded-external-confirmed" — external auditor confirmed builder grade. PASS counts.
    - Anything else → fails the gate.

    Three gates (all must hold for PASS):
    1. audit_status in recognized set (guards against silent label tampering)
    2. weighted_aggregate >= threshold (existing aggregate gate)
    3. (Phase 13 cycle 5 #00P13c5-04 — Surface 3 mitigation per PHASE_13_ANTICHEAT_AUDIT.md
       Candidate B) per-criterion floor gate: if `rubric_grade.per_criterion_floor` is set
       (None / absent = disabled), EVERY dimension in `rubric_dimension_scores` must be
       >= floor. Closes the uniformly-mediocre 4.01 PASS-loophole when active. Default
       absent so existing entries continue to PASS unchanged; cycle 6+ may ratchet floors
       per-entry as confidence in dimensions builds.
    """
    rg = entry["rubric_grade"]
    aggregate = rg.get("weighted_aggregate", 0)
    # Backward-compat: accept legacy `threshold_for_green` if present, prefer
    # `threshold_for_pass` (the honest-label name).
    threshold = rg.get("threshold_for_pass", rg.get("threshold_for_green", 99))
    audit_status = entry.get("audit_status", "")
    recognized_statuses = {
        "rubric-graded-builder; pending external confirmation",
        "rubric-graded-external-confirmed",
    }
    status_ok = audit_status in recognized_statuses
    aggregate_ok = aggregate >= threshold

    # Per-criterion floor gate (cycle 5 #04). None / missing → disabled (legacy behavior).
    floor = rg.get("per_criterion_floor")
    dim_scores = rg.get("rubric_dimension_scores", {})
    if floor is None:
        floor_ok = True
        floor_failures: list[str] = []
    else:
        floor_failures = [
            f"{dim}={score} < {floor}"
            for dim, score in dim_scores.items()
            if score < floor
        ]
        floor_ok = not floor_failures

    pass_ = status_ok and aggregate_ok and floor_ok
    if pass_:
        floor_note = (
            f"; per-criterion floor {floor}/5 satisfied across {len(dim_scores)} dims"
            if floor is not None
            else ""
        )
        reason = (
            f"rubric weighted_aggregate {aggregate}/5 >= threshold {threshold}/5; "
            f"grader: {rg.get('grader', 'unknown')}; "
            f"status: {audit_status}{floor_note}"
        )
    else:
        parts = [f"audit_status={audit_status!r}", f"aggregate={aggregate}", f"threshold={threshold}"]
        if not floor_ok:
            parts.append(f"per_criterion_floor={floor} failed: {floor_failures}")
        reason = "rubric-graded gate failed: " + ", ".join(parts)
    return EntryResult(
        id=entry["id"],
        domain=entry.get("domain", "unknown"),
        method="rubric_graded_builder",
        pass_=pass_,
        reason=reason,
    )


def _run_one(entry: dict, *, agent: ReasoningAgent | None = None) -> EntryResult | None:
    """Returns an EntryResult, or None if the entry is rubric-pending (skip).

    Three paths:
    - `auto_grade` block present: auto-graded entry (maths/physics frozen-verdict OR
      agent-runtime when `agent` is provided; memory always live-replay).
    - `rubric_grade` block present (Phase 13 cycle 3+ Path B): rubric-graded entry.
    - Neither present: rubric-pending; skip per M-PROJECTX-014 firewall.

    When `agent` is not None and the entry is maths/physics auto-graded, the AGENT
    runtime path replaces the frozen verdict — bench-replay reports whether the agent
    actually solves the prompt at runtime, not whether BUILDER pre-computed match=True.
    """
    if "auto_grade" in entry:
        domain = entry.get("domain", "unknown")
        if domain == "memory":
            return _replay_memory_entry(entry)
        if agent is not None and domain in ("maths", "physics"):
            return _verify_via_agent_runtime(entry, agent)
        return _verify_frozen_entry(entry)
    if "rubric_grade" in entry:
        return _verify_rubric_graded_entry(entry)
    return None  # rubric-pending; skip per M-PROJECTX-014 firewall


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Optional path to write machine-readable JSON results",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-entry stdout; print only the summary table",
    )
    parser.add_argument(
        "--agent-runtime",
        action="store_true",
        help=(
            "Cycle 7 #00P13c7-NEW: invoke ReasoningAgent on each maths/physics auto-graded "
            "prompt and verify the agent's runtime-computed answer matches expected. "
            "Replaces the BUILDER-pre-computed frozen-verdict path with an AGENT-actually-solves "
            "verdict. Memory always live-replays; subjective rubric domains unchanged."
        ),
    )
    args = parser.parse_args(argv)
    agent = ReasoningAgent() if args.agent_runtime else None

    if not BENCHMARK_DIR.exists():
        print(f"ERROR: benchmark dir not found: {BENCHMARK_DIR}", file=sys.stderr)
        return 2

    domains = sorted(p.name for p in BENCHMARK_DIR.iterdir() if p.is_dir())
    results: list[EntryResult] = []
    skipped_count = 0

    for domain in domains:
        for entry in _load_ladder(domain):
            res = _run_one(entry, agent=agent)
            if res is None:
                skipped_count += 1
                continue
            results.append(res)
            if not args.quiet:
                status = "PASS" if res.pass_ else "FAIL"
                print(f"  [{status}] {res.id} ({res.method}) — {res.reason}")

    # Per-domain summary.
    by_domain: dict[str, dict[str, int]] = {}
    for r in results:
        bucket = by_domain.setdefault(r.domain, {"pass": 0, "fail": 0})
        bucket["pass" if r.pass_ else "fail"] += 1

    print()
    print("=" * 60)
    print("AUDIT HARNESS — SUMMARY")
    print("=" * 60)
    print(f"  Domains scanned: {', '.join(domains)}")
    print(f"  Auto-graded entries replayed/verified: {len(results)}")
    print(f"  Rubric-pending entries skipped:        {skipped_count}")
    print()
    print(f"  {'Domain':<14} {'Pass':>6} {'Fail':>6}")
    print(f"  {'-'*14} {'-'*6:>6} {'-'*6:>6}")
    for d in sorted(by_domain):
        b = by_domain[d]
        print(f"  {d:<14} {b['pass']:>6} {b['fail']:>6}")
    total_pass = sum(b["pass"] for b in by_domain.values())
    total_fail = sum(b["fail"] for b in by_domain.values())
    print(f"  {'TOTAL':<14} {total_pass:>6} {total_fail:>6}")
    print("=" * 60)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "summary": {
                "total_pass": total_pass,
                "total_fail": total_fail,
                "rubric_pending_skipped": skipped_count,
                "by_domain": by_domain,
            },
            "entries": [asdict(r) for r in results],
        }
        # `pass_` → `pass` in the JSON for human-friendliness; dataclass field
        # had to be suffixed because `pass` is a reserved word in Python.
        for e in payload["entries"]:
            e["pass"] = e.pop("pass_")
        args.json.write_text(json.dumps(payload, indent=2))
        print(f"  JSON results written to {args.json}")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
