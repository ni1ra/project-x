"""Phase 13 #00P13c1-03 grader-min tests.

Covers gpt-codex/grade_pipeline/{schema,cli}.py:
  - Candidate + Grade dataclass validation
  - M-PROJECTX-014 firewall on candidate JSONL (forbidden self_score etc.)
  - Score range validation on grades (1-5 per dimension)
  - JSONL round-trip (save → load preserves content)
  - CLI subprocess invocation: present / validate / validate-candidates

The hyphenated parent dir (gpt-codex/) breaks `import gpt_codex.grade_pipeline`,
so tests load schema.py via importlib.util.spec_from_file_location and exercise
the CLI via subprocess.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GRADER_DIR = REPO_ROOT / "gpt-codex" / "grade_pipeline"
SCHEMA_PATH = GRADER_DIR / "schema.py"
CLI_PATH = GRADER_DIR / "cli.py"


def _load_schema_module():
    """Load schema.py as a module despite hyphenated parent dir.

    Module MUST be registered in sys.modules before exec_module so dataclasses
    can resolve forward refs via sys.modules[cls.__module__]; otherwise the
    @dataclass decorator raises AttributeError on Python 3.12+.
    """
    spec = importlib.util.spec_from_file_location("grade_pipeline_schema", SCHEMA_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["grade_pipeline_schema"] = module
    spec.loader.exec_module(module)
    return module


schema = _load_schema_module()


# =============================================================================
# Candidate firewall — M-PROJECTX-014
# =============================================================================


def test_candidate_basic_construction():
    c = schema.Candidate(
        prompt_id="poetry-001", candidate_id="c1",
        candidate_text="Notice. The poem...", persona_signature="Notice.",
    )
    assert c.prompt_id == "poetry-001"


def test_candidate_from_dict_minimal():
    c = schema.Candidate.from_dict({
        "prompt_id": "poetry-001",
        "candidate_id": "c1",
        "candidate_text": "...",
    })
    assert c.persona_signature == ""


def test_candidate_firewall_rejects_self_score():
    """M-PROJECTX-014: self_score on candidate = firewall violation."""
    with pytest.raises(ValueError, match="M-PROJECTX-014"):
        schema.Candidate.from_dict({
            "prompt_id": "poetry-001",
            "candidate_id": "c1",
            "candidate_text": "...",
            "self_score": 4,
        })


@pytest.mark.parametrize("forbidden", ["self_score", "self_grade", "self_rating", "agent_score"])
def test_candidate_firewall_rejects_each_forbidden_field(forbidden):
    with pytest.raises(ValueError, match="firewall"):
        schema.Candidate.from_dict({
            "prompt_id": "poetry-001",
            "candidate_id": "c1",
            "candidate_text": "...",
            forbidden: 4,
        })


def test_candidate_missing_required_field():
    with pytest.raises(ValueError, match="missing required"):
        schema.Candidate.from_dict({"prompt_id": "p", "candidate_id": "c"})


# =============================================================================
# Grade validation
# =============================================================================


def test_grade_basic_construction():
    g = schema.Grade(
        prompt_id="poetry-001", candidate_id="c1", grader="claude-code",
        rubric_dimension_scores={"technique": 4, "meaning": 3},
        notes_text="scansion correct; image precision lacks",
    )
    assert g.rubric_dimension_scores["technique"] == 4


def test_grade_score_out_of_range():
    with pytest.raises(ValueError, match="out of range"):
        schema.Grade(
            prompt_id="p", candidate_id="c", grader="g",
            rubric_dimension_scores={"technique": 6},
        )


def test_grade_score_zero_rejected():
    with pytest.raises(ValueError, match="out of range"):
        schema.Grade(
            prompt_id="p", candidate_id="c", grader="g",
            rubric_dimension_scores={"technique": 0},
        )


def test_grade_score_non_int_rejected():
    with pytest.raises(ValueError, match="out of range"):
        schema.Grade(
            prompt_id="p", candidate_id="c", grader="g",
            rubric_dimension_scores={"technique": 4.5},
        )


def test_grade_empty_grader_rejected():
    with pytest.raises(ValueError, match="grader"):
        schema.Grade(
            prompt_id="p", candidate_id="c", grader="",
            rubric_dimension_scores={"technique": 3},
        )


# =============================================================================
# JSONL round-trip
# =============================================================================


def test_candidates_save_load_round_trip(tmp_path):
    candidates = [
        schema.Candidate(prompt_id="poetry-001", candidate_id="c1",
                         candidate_text="Notice. The poem.", persona_signature="Notice."),
        schema.Candidate(prompt_id="philosophy-001", candidate_id="c1",
                         candidate_text="Notice. Standard distinction.", persona_signature="Notice."),
    ]
    path = tmp_path / "candidates.jsonl"
    schema.save_candidates(path, candidates)
    loaded = schema.load_candidates(path)
    assert len(loaded) == 2
    assert loaded[0].prompt_id == "poetry-001"
    assert loaded[1].candidate_text == "Notice. Standard distinction."


def test_grades_save_load_round_trip(tmp_path):
    grades = [
        schema.Grade(prompt_id="poetry-001", candidate_id="c1", grader="claude-code",
                     rubric_dimension_scores={"technique": 4, "meaning": 3, "voice": 5},
                     notes_text="scansion correct"),
        schema.Grade(prompt_id="philosophy-001", candidate_id="c1", grader="claude-code",
                     rubric_dimension_scores={"argument_quality": 3, "position_coherence": 4}),
    ]
    path = tmp_path / "grades.jsonl"
    schema.save_grades(path, grades)
    loaded = schema.load_grades(path)
    assert len(loaded) == 2
    assert loaded[0].rubric_dimension_scores["voice"] == 5
    assert loaded[1].grader == "claude-code"


def test_load_candidates_surfaces_firewall_with_lineno(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({
        "prompt_id": "p", "candidate_id": "c", "candidate_text": "...",
        "self_score": 4,  # firewall violation
    }) + "\n")
    with pytest.raises(ValueError, match=r":1:"):
        schema.load_candidates(bad)


def test_load_grades_surfaces_invalid_score(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({
        "prompt_id": "p", "candidate_id": "c", "grader": "g",
        "rubric_dimension_scores": {"technique": 99},
    }) + "\n")
    with pytest.raises(ValueError, match="out of range"):
        schema.load_grades(bad)


# =============================================================================
# CLI subprocess invocation
# =============================================================================


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        capture_output=True, text=True, timeout=30,
    )


def test_cli_present_round_trip(tmp_path):
    candidates_path = tmp_path / "candidates.jsonl"
    rubric_path = tmp_path / "rubric.md"
    schema.save_candidates(candidates_path, [
        schema.Candidate(prompt_id="poetry-001", candidate_id="c1",
                         candidate_text="Notice. The poem.", persona_signature="Notice."),
    ])
    rubric_path.write_text("# Rubric\nDimension: technique (1-5)\n")

    result = _run_cli("present",
                      "--candidates", str(candidates_path),
                      "--rubric", str(rubric_path))
    assert result.returncode == 0
    assert "GRADER WORKSHEET" in result.stdout
    assert "poetry-001" in result.stdout
    assert "Dimension: technique" in result.stdout


def test_cli_validate_passes_on_valid_grades(tmp_path):
    grades_path = tmp_path / "grades.jsonl"
    schema.save_grades(grades_path, [
        schema.Grade(prompt_id="p", candidate_id="c", grader="claude-code",
                     rubric_dimension_scores={"technique": 4}),
    ])
    result = _run_cli("validate", "--grades", str(grades_path))
    assert result.returncode == 0
    assert "OK" in result.stdout


def test_cli_validate_fails_on_invalid_score(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({
        "prompt_id": "p", "candidate_id": "c", "grader": "g",
        "rubric_dimension_scores": {"technique": 99},
    }) + "\n")
    result = _run_cli("validate", "--grades", str(bad))
    assert result.returncode == 1
    assert "INVALID" in result.stderr


def test_cli_validate_candidates_fails_on_firewall_violation(tmp_path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({
        "prompt_id": "p", "candidate_id": "c", "candidate_text": "...",
        "self_score": 4,
    }) + "\n")
    result = _run_cli("validate-candidates", "--candidates", str(bad))
    assert result.returncode == 1
    assert "INVALID" in result.stderr
    assert "M-PROJECTX-014" in result.stderr


def test_cli_validate_candidates_passes_clean(tmp_path):
    clean = tmp_path / "clean.jsonl"
    schema.save_candidates(clean, [
        schema.Candidate(prompt_id="p", candidate_id="c", candidate_text="..."),
    ])
    result = _run_cli("validate-candidates", "--candidates", str(clean))
    assert result.returncode == 0
    assert "firewall held" in result.stdout
