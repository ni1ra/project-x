"""Manual-grade harness CLI — Phase 13 #00P13c1-03.

Two commands:

  present  — load candidates JSONL + rubric markdown, format a grading
             worksheet to stdout. The grader (Claude Code in cycle 1+; lain
             via copy-paste in cycle N+; GPT in audit passes) reads the
             worksheet, drafts grades, writes them to a separate JSONL.

  validate — load a grades JSONL, check Grade schema (required fields, score
             range 1-5, non-empty grader). Exit 1 on invalid.

The CLI is presentation-only by design — it does NOT prompt for grades on
stdin. Grading happens out-of-band; the CLI reads/writes the JSONL files
that surround the grading step. This keeps the harness composable: the same
candidates can be re-graded by different graders without re-running anything.

Cycle 1 ships only the read+present+validate round-trip. Cycle 3+ wires
grades back into agent generation as a preference signal.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# The grade_pipeline package lives at gpt-codex/grade_pipeline (hyphenated
# parent dir) — direct imports break. Insert the package dir on sys.path so
# `from schema import ...` resolves to the sibling module.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from schema import (  # noqa: E402
    Candidate,
    Grade,
    load_candidates,
    load_grades,
)


def cmd_present(args: argparse.Namespace) -> int:
    candidates = load_candidates(args.candidates)
    rubric_text = Path(args.rubric).read_text(encoding="utf-8")
    sep = "=" * 60
    print(sep)
    print(f"GRADER WORKSHEET — {len(candidates)} candidate(s)")
    print(f"Rubric: {args.rubric}")
    print(sep)
    print()
    print(rubric_text)
    print()
    print(sep)
    for c in candidates:
        print()
        print(f"--- prompt_id={c.prompt_id}  candidate_id={c.candidate_id} ---")
        if c.persona_signature:
            print(f"persona_signature: {c.persona_signature}")
        print()
        print("candidate_text:")
        print(c.candidate_text)
        print()
        print("# fill grade JSONL row:")
        print('# {"prompt_id": "', c.prompt_id, '", "candidate_id": "',
              c.candidate_id, '", "grader": "<name>", '
              '"rubric_dimension_scores": {...1-5 per dim...}, '
              '"notes_text": "..."}', sep="")
        print()
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        grades = load_grades(args.grades)
    except (ValueError, FileNotFoundError) as e:
        print(f"INVALID grades file: {e}", file=sys.stderr)
        return 1
    print(f"OK — {len(grades)} grade(s) validated.")
    return 0


def cmd_validate_candidates(args: argparse.Namespace) -> int:
    """Round-trip parse on candidates JSONL — surfaces M-PROJECTX-014 firewall
    violations (forbidden fields like self_score) at lint time."""
    try:
        candidates = load_candidates(args.candidates)
    except (ValueError, FileNotFoundError) as e:
        print(f"INVALID candidates file: {e}", file=sys.stderr)
        return 1
    print(f"OK — {len(candidates)} candidate(s) validated (firewall held).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_present = sub.add_parser(
        "present", help="format grading worksheet to stdout"
    )
    p_present.add_argument("--candidates", type=Path, required=True)
    p_present.add_argument("--rubric", type=Path, required=True)
    p_present.set_defaults(fn=cmd_present)

    p_validate = sub.add_parser(
        "validate", help="validate grades JSONL schema"
    )
    p_validate.add_argument("--grades", type=Path, required=True)
    p_validate.set_defaults(fn=cmd_validate)

    p_vc = sub.add_parser(
        "validate-candidates",
        help="lint candidates JSONL — surfaces firewall violations early",
    )
    p_vc.add_argument("--candidates", type=Path, required=True)
    p_vc.set_defaults(fn=cmd_validate_candidates)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
