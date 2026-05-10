"""Candidate + Grade dataclasses for the manual-grade harness.

M-PROJECTX-014 firewall: no `self_score` on candidates. The agent (Project X
Raphael) emits candidate text; the builder (Claude Code) grades. Self-grading
would erase the asymmetry that makes split-grading meaningful — a candidate
that carried its own score would let the agent's design-bias seep into the
measurement.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


# Schema firewall — appearance of any of these on a Candidate JSONL row is
# treated as a M-PROJECTX-014 violation. `from_dict` raises ValueError naming
# the offending field. Cross-ref: MANIFESTO § Active grading firewall.
FORBIDDEN_CANDIDATE_FIELDS = frozenset({
    "self_score",
    "self_grade",
    "self_rating",
    "agent_score",
})


@dataclass
class Candidate:
    """Agent-emitted candidate awaiting external grading.

    No score field by design — see FORBIDDEN_CANDIDATE_FIELDS. The grader
    produces a separate Grade row keyed by (prompt_id, candidate_id).
    """
    prompt_id: str
    candidate_id: str
    candidate_text: str
    persona_signature: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Candidate":
        violations = FORBIDDEN_CANDIDATE_FIELDS & set(data.keys())
        if violations:
            raise ValueError(
                f"M-PROJECTX-014 firewall: candidate has forbidden field(s) "
                f"{sorted(violations)} — split-grading requires the candidate "
                f"to carry no self-assessment; grades live in a separate "
                f"Grade row produced by an external grader."
            )
        required = {"prompt_id", "candidate_id", "candidate_text"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"candidate missing required fields: {sorted(missing)}")
        return cls(
            prompt_id=data["prompt_id"],
            candidate_id=data["candidate_id"],
            candidate_text=data["candidate_text"],
            persona_signature=data.get("persona_signature", ""),
        )


@dataclass
class Grade:
    """External grade for a (prompt_id, candidate_id) pair.

    rubric_dimension_scores keys come from the rubric.md being applied
    (e.g. "technique", "meaning", "voice", "aesthetic_openness" for poetry;
    each on the 1-5 scale per the rubric per-difficulty notes).
    """
    prompt_id: str
    candidate_id: str
    grader: str
    rubric_dimension_scores: dict[str, int] = field(default_factory=dict)
    notes_text: str = ""

    def __post_init__(self) -> None:
        for dim, score in self.rubric_dimension_scores.items():
            if not isinstance(score, int) or not (1 <= score <= 5):
                raise ValueError(
                    f"rubric dim {dim!r} score {score!r} out of range 1-5 "
                    f"(rubrics standardize on the 1-5 scale)"
                )
        if not self.grader:
            raise ValueError("grade requires a non-empty `grader` (who graded)")

    @classmethod
    def from_dict(cls, data: dict) -> "Grade":
        required = {"prompt_id", "candidate_id", "grader"}
        missing = required - set(data.keys())
        if missing:
            raise ValueError(f"grade missing required fields: {sorted(missing)}")
        return cls(
            prompt_id=data["prompt_id"],
            candidate_id=data["candidate_id"],
            grader=data["grader"],
            rubric_dimension_scores=dict(data.get("rubric_dimension_scores", {})),
            notes_text=data.get("notes_text", ""),
        )


def load_candidates(path: Path | str) -> list[Candidate]:
    """Load + validate candidate JSONL. Raises on firewall violation."""
    out: list[Candidate] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(Candidate.from_dict(json.loads(line)))
            except (ValueError, json.JSONDecodeError) as e:
                raise ValueError(f"{path}:{lineno}: {e}") from e
    return out


def save_candidates(path: Path | str, candidates: list[Candidate]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(asdict(c)) + "\n")


def load_grades(path: Path | str) -> list[Grade]:
    out: list[Grade] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(Grade.from_dict(json.loads(line)))
            except (ValueError, json.JSONDecodeError) as e:
                raise ValueError(f"{path}:{lineno}: {e}") from e
    return out


def save_grades(path: Path | str, grades: list[Grade]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for g in grades:
            f.write(json.dumps(asdict(g)) + "\n")
