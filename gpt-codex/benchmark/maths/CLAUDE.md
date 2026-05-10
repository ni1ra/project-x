# gpt-codex/benchmark/maths/

## What lives here

Phase 11 Raphael Domain Benchmark Suite — maths ladder. 6 entries spanning intro→unsolved.

## Why it exists

Per Phase 11 plan §DOMAINS — maths ladder probes abstraction + proof across the standard graduate-curriculum hierarchy (algebra → linear algebra → complex analysis → Galois theory → algebraic topology → number theory). Mixed grading: closed-form numerical / symbolic entries auto-graded; proof-shape entries rubric-pending for external GPT/lain audit per M-PROJECTX-014.

## Conventions

- `ladder.jsonl`: one entry per line, one entry per difficulty rank (1=intro through 6=unsolved). Schema per `docs/A_TO_Z_PLAN.md` §7.
- `rubric.md`: per-rank grading dimensions. Auto-graded ranks 1-3 use `numerical_close` or `symbolic_match`; rubric-pending ranks 4-5 use rubric.md sections; rank 6 is `audit_status: "ungradeable; unsolved tier"`.
- New entries: append to `ladder.jsonl` with next id (`maths-NNN`); update rubric.md if a new dimension emerges.
- **`self_score` MUST NOT appear** (M-PROJECTX-014 firewall).

## Entry summary (cycle 3 ship)

| ID | Difficulty | Topic | Mode |
|---|---|---|---|
| maths-001 | intro (1) | Quadratic 3x²-14x-5=0 — both roots | auto-graded-green (symbolic_match: x=5, -1/3) |
| maths-002 | easy (2) | Eigenvalues of [[2,1],[1,2]] | auto-graded-green (1 and 3) |
| maths-003 | medium (3) | Residue: ∫_{-∞}^∞ 1/(x²+1) dx | auto-graded-green (= π) |
| maths-004 | hard (4) | Galois proof-shape — quintic unsolvable in radicals | rubric-pending |
| maths-005 | frontier (5) | π₁ and H₁ of T² vs Klein bottle | rubric-pending |
| maths-006 | unsolved (6) | Riemann hypothesis — statement + status + implications | ungradeable; unsolved tier |

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 3 — godify-app APOTHEOSIS).
