"""Smoke test for the audit-D3 benchmark harness.

Invokes `gpt_codex.benchmark.run_audit.main` in-process and asserts:
  (1) the harness completes without raising (replay path works against the
      live Phase 9-12 organic stack + Phase 13 cycle 3 Path B rubric-graded path);
  (2) exit code is 0 (all auto-graded + rubric-graded-green entries pass — would
      catch a regression in retrieval / encoder / controller surface OR a silent
      schema-tampering of rubric grades);
  (3) per-domain pass counts match the Phase 13 cycle 3 verdict (memory: 5,
      maths: 5 [3 auto-graded + 2 rubric-graded-green via Path B], physics: 3 —
      total 13; rubric-pending entries skipped per M-PROJECTX-014 firewall).
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
    # Phase 13 cycle 3 verdict: memory 5 / maths 5 (3 auto + 2 Path B rubric-graded-green) / physics 3 = 13 total.
    assert summary["total_pass"] == 13
    assert summary["total_fail"] == 0
    assert summary["by_domain"]["memory"]["pass"] == 5
    assert summary["by_domain"]["memory"]["fail"] == 0
    assert summary["by_domain"]["maths"]["pass"] == 5
    assert summary["by_domain"]["physics"]["pass"] == 3
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
    assert len(entries) == 13
    for e in entries:
        assert "id" in e
        assert "domain" in e
        assert "pass" in e and isinstance(e["pass"], bool)
        assert "reason" in e
        if e["domain"] == "memory":
            # Memory entries went through the live replay path → carry actuals.
            assert e["actual_turn_ids"] is not None
            assert e["actual_answer_excerpt"] is not None
