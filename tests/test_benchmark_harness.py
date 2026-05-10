"""Smoke test for the audit-D3 benchmark harness.

Invokes `gpt_codex.benchmark.run_audit.main` in-process and asserts:
  (1) the harness completes without raising (replay path works against the
      live Phase 9-12 organic stack + Phase 13 cycle 3 Path B rubric-graded path);
  (2) exit code is 0 (all auto-graded + rubric-graded-green entries pass — would
      catch a regression in retrieval / encoder / controller surface OR a silent
      schema-tampering of rubric grades);
  (3) per-domain pass counts match the Phase 13 cycle 4 verdict (memory: 5,
      maths: 5 [3 auto-graded + 2 rubric-graded-builder via cycle 3 Path B],
      physics: 5 [3 auto-graded + 2 rubric-graded-builder via cycle 4 Path B] —
      total 15; rubric-pending entries skipped per M-PROJECTX-014 firewall).
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_PATH = REPO_ROOT / "gpt-codex"
if str(HARNESS_PATH) not in sys.path:
    sys.path.insert(0, str(HARNESS_PATH))


def _import_harness():
    """gpt-codex/ uses a hyphen so we exec the file directly rather than
    importing it as a module (Python module names can't have hyphens). The
    `sys.modules[spec.name] = mod` registration BEFORE exec_module is
    load-bearing — `dataclasses.asdict` walks `cls.__module__` through
    sys.modules to resolve generic-alias hints; without registration it
    finds None and AttributeErrors at the asdict() call inside main()."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run_audit_harness",
        REPO_ROOT / "gpt-codex" / "benchmark" / "run_audit.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_audit_harness_all_pass(tmp_path):
    """Live replay of all auto-graded entries should pass against the current
    Phase 9-12 stack. Output JSON has the expected per-domain summary shape."""
    harness = _import_harness()
    json_path = tmp_path / "audit_results.json"

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = harness.main(["--quiet", "--json", str(json_path)])

    assert rc == 0, (
        f"benchmark harness must report exit 0 (all auto-graded pass); "
        f"got {rc}. Output:\n{buf.getvalue()}"
    )
    assert json_path.exists()

    payload = json.loads(json_path.read_text())
    summary = payload["summary"]
    # Phase 13 cycle 6 verdict: minimums after #02 maths expansion (+6 auto-graded passes).
    # Use >= rather than == so future cycle expansions don't break the no-regression test.
    # Strict floor: prior cycle baselines must hold; cycle 6+ may add entries that lift the count.
    assert summary["total_pass"] >= 21, f"regression: total_pass {summary['total_pass']} < cycle-6-floor 21"
    assert summary["total_fail"] == 0, f"regression: total_fail {summary['total_fail']} != 0"
    assert summary["by_domain"]["memory"]["pass"] >= 5
    assert summary["by_domain"]["memory"]["fail"] == 0
    assert summary["by_domain"]["maths"]["pass"] >= 11  # was 5; cycle 6 #02 lifted to 11
    assert summary["by_domain"]["physics"]["pass"] >= 5
    # Rubric-pending domains MUST still be skipped where no rubric_grade landed
    # (poetry / philosophy / persona / physics-conceptual entries that haven't been
    # Path-B graded). M-PROJECTX-014 firewall holds: candidate text exists, no
    # self_score field; promotion to green requires a builder rubric_grade with
    # weighted_aggregate >= threshold (default 4.0/5).
    assert "persona" not in summary["by_domain"]
    assert "poetry" not in summary["by_domain"]
    assert "philosophy" not in summary["by_domain"]
    assert summary["rubric_pending_skipped"] >= 1

    # Each entry result should carry the harness's pass/fail + reason fields.
    entries = payload["entries"]
    assert len(entries) >= 21  # cycle-6-floor; future cycle expansion may lift
    for e in entries:
        assert "id" in e
        assert "domain" in e
        assert "pass" in e and isinstance(e["pass"], bool)
        assert "reason" in e
        if e["domain"] == "memory":
            # Memory entries went through the live replay path → carry actuals.
            assert e["actual_turn_ids"] is not None
            assert e["actual_answer_excerpt"] is not None


class TestPerCriterionFloorGate:
    """Phase 13 cycle 5 #00P13c5-04 — per-criterion floor gate (Surface 3 partial mitigation
    per PHASE_13_ANTICHEAT_AUDIT.md Candidate B).

    Verifies the gate's three properties:
    - Disabled by default (None / absent floor) → existing entries unchanged (legacy behavior).
    - When floor set + ALL dimensions >= floor → PASS.
    - When floor set + ANY dimension < floor → FAIL with detailed reason naming the failing dim.
    - When aggregate alone passes but a dimension is below floor → FAIL (closes the
      uniformly-mediocre 4.01 PASS-loophole the audit identified).

    Tests call `_verify_rubric_graded_entry` directly with synthetic entry dicts —
    avoids needing to mutate the live ladder.jsonl files for unit-test scope.
    """

    def _make_entry(self, dim_scores, aggregate, audit_status, floor=None):
        """Build a synthetic Path B entry dict for the verifier."""
        rg = {
            "weighted_aggregate": aggregate,
            "threshold_for_pass": 4.0,
            "rubric_dimension_scores": dim_scores,
            "grader": "test-builder",
        }
        if floor is not None:
            rg["per_criterion_floor"] = floor
        return {
            "id": "test-001",
            "domain": "test",
            "audit_status": audit_status,
            "rubric_grade": rg,
        }

    def test_floor_disabled_default_preserves_legacy_pass(self):
        """No per_criterion_floor field → existing aggregate-only behavior."""
        harness = _import_harness()
        # cycle 3 maths-004 shape: completeness=3 (below would-be 4.0 floor),
        # but aggregate 4.25 PASSes. Without floor, this MUST still pass.
        entry = self._make_entry(
            dim_scores={"correctness": 5, "completeness": 3, "structural_insight": 5, "voice": 4},
            aggregate=4.25,
            audit_status="rubric-graded-builder; pending external confirmation",
        )
        result = harness._verify_rubric_graded_entry(entry)
        assert result.pass_ is True
        assert "floor" not in result.reason.lower()

    def test_floor_passes_when_all_dimensions_above(self):
        """Floor 4.0 + all dimensions >= 4.0 → PASS with floor-satisfied note."""
        harness = _import_harness()
        entry = self._make_entry(
            dim_scores={"correctness": 5, "completeness": 4, "voice": 4},
            aggregate=4.33,
            audit_status="rubric-graded-builder; pending external confirmation",
            floor=4.0,
        )
        result = harness._verify_rubric_graded_entry(entry)
        assert result.pass_ is True
        assert "per-criterion floor 4.0/5 satisfied" in result.reason

    def test_floor_fails_when_one_dimension_below(self):
        """Floor 4.0 + completeness=3 → FAIL with dim-name in reason."""
        harness = _import_harness()
        entry = self._make_entry(
            dim_scores={"correctness": 5, "completeness": 3, "voice": 5},
            aggregate=4.33,
            audit_status="rubric-graded-builder; pending external confirmation",
            floor=4.0,
        )
        result = harness._verify_rubric_graded_entry(entry)
        assert result.pass_ is False
        assert "completeness=3" in result.reason
        assert "per_criterion_floor=4.0" in result.reason

    def test_floor_closes_uniformly_mediocre_loophole(self):
        """Aggregate 4.01/5 (just-above-threshold) with one dim at 3.5 → floor catches it.

        This is the canonical Surface 3 loophole: aggregate-only thresholds can let a
        uniformly-mediocre entry PASS when a real-gap-on-one-dimension should fail it.
        Floor of 4.0 closes this exact loophole.
        """
        harness = _import_harness()
        entry = self._make_entry(
            dim_scores={"d1": 3.5, "d2": 4.5, "d3": 4.5, "d4": 4.0, "d5": 3.5},  # avg = 4.0
            aggregate=4.0,
            audit_status="rubric-graded-builder; pending external confirmation",
            floor=4.0,
        )
        result = harness._verify_rubric_graded_entry(entry)
        # Aggregate gate alone would PASS (4.0 >= 4.0); floor gate catches the dimensions at 3.5.
        assert result.pass_ is False
        assert "d1=3.5" in result.reason
        assert "d5=3.5" in result.reason
