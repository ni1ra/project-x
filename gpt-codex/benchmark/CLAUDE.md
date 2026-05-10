# gpt-codex/benchmark/

## What lives here

Phase 11 Raphael Domain Benchmark Suite — 6 domain ladders × 6 entries each spanning easy→unsolved, with split grading (auto-graded mechanical vs rubric-pending subjective per M-PROJECTX-014).

## Why it exists

Reproducible benchmark of Raphael's competence across domains lain explicitly named (physics, maths, memory, persona, philosophy, poetry). Audit-ready by GPT/lain at 09:00 CEST. The diagnostic that tells us where Raphael actually sits BEFORE live training begins (Phase 12+).

## Conventions

- One folder per domain: `physics/`, `maths/`, `memory/`, `persona/`, `philosophy/`, `poetry/`.
- Each domain folder has: `ladder.jsonl` (6 entries, one per difficulty rank 1-6), `rubric.md` (per-difficulty grading dimensions), `CLAUDE.md` (folder doc).
- Aggregate at cycle 8: `audit_log.jsonl` (one row per entry across all 6 ladders, GPT-readable filter on `needs_audit: true`) + `verdict.md` (cross-linked from `docs/artifacts/PHASE_11_BENCHMARK.md`).
- Entry schema: `~/projext-x/docs/A_TO_Z_PLAN.md` §7. Required fields: `id`, `domain`, `difficulty`, `prompt`, `raphael_response`, `audit_status`. Auto-graded: `auto_grade` block. Rubric-pending: `rubric_pointer`. **`self_score` MUST NOT appear** (M-PROJECTX-014 firewall).
- New entries within an existing ladder: append to `ladder.jsonl` with next id. Entry-write is `>>` append + flush before next entry generates (crash-survival per plan §CRASH SURVIVAL).
- Auto-graded domains: memory (all 6), maths (numerical/symbolic-matchable), physics (closed-form ranks 1-3).
- Rubric-pending domains: poetry (all 6), persona (all 6), philosophy (all 6), physics (conceptual ranks 4-5; rank 6 unsolved is `audit_status: "ungradeable; unsolved tier"`).

## Last reviewed

2026-05-10 by Raphael (Phase 11 godify-app cycle 2).
