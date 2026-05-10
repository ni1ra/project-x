"""Smoke test for the Phase 1-3 compressed-memory historical-control experiment.

Skipped when torch is not installed (audit-C2 — `compressed_memory.py` is
torch-dependent; torch is now an OPTIONAL [legacy] extra in pyproject.toml).
Install with `pip install -e .[legacy]` to exercise this test. The
`pytest.importorskip("torch")` guard at module top means the active organic
suite doesn't ImportError-fail under a torch-free install; this test just
no-ops cleanly.
"""
import pytest

pytest.importorskip("torch")  # audit-C2 quarantine: torch optional via [legacy] extra

from project_x.experiments.compressed_memory import run_experiment


def test_compressed_memory_test_mode_writes_metrics():
    result = run_experiment("test", "pytest-run")
    assert result["mode"] == "test"
    assert result["control"]["name"] == "transformer_control"
    assert result["candidate"]["name"] == "dual_rate_compressed_memory"
    assert result["candidate"]["estimated_memory_bytes"] < result["control"]["estimated_memory_bytes"]
