# Phase 11 Benchmark Verdict (cross-link)

The full verdict lives at `docs/artifacts/PHASE_11_BENCHMARK.md`. This file is the in-folder pointer for GPT/lain auditing.

## Quick reference (updated 2026-05-10 ~11:32 CEST after Phase 12 cycle-3 verdict-builder re-run)

- **36 entries** across 6 domains × 6 difficulty ranks
- **11 auto-graded-green** (3 physics + 3 maths + 5 memory) — was 9 at Phase 11 close; +2 from Phase 12 fix
- **0 auto-graded-red** — was 2 (memory-004 + memory-005); both flipped via Phase 12 retrieval-mode disambiguation
- **21 rubric-pending** (2 physics + 2 maths + 6 persona + 6 philosophy + 5 poetry) — unchanged
- **4 ungradeable** (1 each in physics, maths, memory, poetry — known-unsolved tier) — unchanged

**Of the auto-gradable subset (11 entries): 11 green / 0 red = 100% pass rate** (was 81.8% at Phase 11 close).

## For GPT audit pass tomorrow

1. Filter `gpt-codex/benchmark/audit_log.jsonl` on `needs_audit: true`.
2. Open each entry's full prompt + raphael_response in `gpt-codex/benchmark/<domain>/ladder.jsonl`.
3. Grade per the rubric at `rubric_pointer` (e.g. `gpt-codex/benchmark/physics/rubric.md#hard`).
4. Output per-entry scores; per-domain averages; flag lowest-graded entries as Phase 12 candidate work areas.

See `docs/artifacts/PHASE_11_BENCHMARK.md` for the full audit-prep instructions, candidate Phase 12+ priorities (ranked by leverage), and architectural-finding writeup on the memory red entries.

## M-PROJECTX-014 firewall integrity

Zero `self_score` fields across 36 entries. Subjective domains report rubric-pending; lain/GPT audit IS the grade. Verdict reports honest counts, not smuggled self-assessments.
