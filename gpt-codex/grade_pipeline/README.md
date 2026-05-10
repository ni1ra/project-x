# grade_pipeline — manual-grade harness

Phase 13 #00P13c1-03 deliverable. Cycle 1 ships the JSONL round-trip; cycle 3+
wires grades back into agent generation as a preference signal.

## Why

lain 2026-05-10 directive: *"YOU claude have the ability to read a big output
file ... and grade it manually. if you do this in big bulks, where you make it
efficient and easy for yourself to manually grade it, this can be used to
further improve it."*

Subjective domains (poetry, philosophy, persona) cannot be auto-graded — see
M-PROJECTX-014 (split-grading firewall: agent that designs the system can't
grade subjective outputs without bias). The harness keeps the asymmetry strict:
the agent emits candidates with NO self-score field; an external grader
(Claude Code in cycle 1+, lain or GPT in audit passes) produces a separate
grades JSONL.

## Schema

**Candidate JSONL** — one entry per line, each:

```json
{"prompt_id": "poetry-001", "candidate_id": "c1", "candidate_text": "...", "persona_signature": "Notice."}
```

**Forbidden fields** (M-PROJECTX-014 firewall — load raises `ValueError`):
`self_score`, `self_grade`, `self_rating`, `agent_score`.

**Grade JSONL** — one entry per line, each:

```json
{"prompt_id": "poetry-001", "candidate_id": "c1", "grader": "claude-code",
 "rubric_dimension_scores": {"technique": 4, "meaning": 3, "voice": 5},
 "notes_text": "scansion correct; image precision lacks; voice distinctive."}
```

Scores: integers 1-5 per dimension (rubrics standardize on 1-5).
`grader`: non-empty (audits the grade's provenance).

## CLI

```bash
# Present a worksheet to stdout — grader reads, drafts grades into a separate JSONL
python3 gpt-codex/grade_pipeline/cli.py present \
    --candidates gpt-codex/grade_pipeline/baseline_2026-05-10/candidates.jsonl \
    --rubric    gpt-codex/benchmark/poetry/rubric.md

# Validate grades JSONL after the grader writes it
python3 gpt-codex/grade_pipeline/cli.py validate \
    --grades gpt-codex/grade_pipeline/baseline_2026-05-10/grades.jsonl

# Lint candidates JSONL early — catches firewall violations before downstream uses
python3 gpt-codex/grade_pipeline/cli.py validate-candidates \
    --candidates gpt-codex/grade_pipeline/baseline_2026-05-10/candidates.jsonl
```

## Cycle 1 use

`baseline_2026-05-10/` is the cycle 1 capability touchpoint (#00P13c1-04). The
agent attempts poetry-001 + philosophy-001 via current `compose_answer` →
candidates JSONL. Claude Code grades immediately via the `present` worksheet
flow → grades JSONL. The brutal score IS the diagnostic surface for the
"what would raise this" cycle 2 framing.

## Cycle 3+ extension (deferred)

Iterative generator: agent generates N candidates per prompt; grader scores;
top-K candidates feed back as in-context priming for the next generation
batch. Out of cycle 1 scope per corpse "cycle 1 ships only the read+grade+write
round-trip."
