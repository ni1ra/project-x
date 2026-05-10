# gpt-codex/benchmark/physics/

## What lives here

Phase 11 Raphael Domain Benchmark Suite — physics ladder. 6 entries spanning intro→unsolved.

## Why it exists

Per Phase 11 plan §DOMAINS — physics ladder probes 1st-principles physical reasoning across regimes (Newtonian → relativistic → quantum → cosmological). Mixed grading: closed-form numerical entries auto-graded; conceptual entries rubric-pending for external GPT/lain audit per M-PROJECTX-014 (the design-bias trap — the agent that designs the system can't grade subjective outputs without bias).

## Conventions

- `ladder.jsonl`: one entry per line, one entry per difficulty rank (1=intro through 6=unsolved). Schema per `docs/A_TO_Z_PLAN.md` §7.
- `rubric.md`: per-rank grading dimensions. Auto-graded ranks 1-3 use `numerical_close`; rubric-pending ranks 4-5 use the rubric.md sections; rank 6 is `audit_status: "ungradeable; unsolved tier"`.
- New entries: append to `ladder.jsonl` with next id (`physics-NNN`); update rubric.md if a new dimension emerges.
- **`self_score` MUST NOT appear** (M-PROJECTX-014 firewall).

## Entry summary (cycle 2 ship)

| ID | Difficulty | Topic | Mode |
|---|---|---|---|
| physics-001 | intro (1) | Free-fall kinematics — h=80m drop time | auto-graded-green (numerical_close) |
| physics-002 | easy (2) | Simple pendulum period (Lagrangian → small-angle) | auto-graded-green |
| physics-003 | medium (3) | Relativistic momentum of 0.9c electron | auto-graded-green |
| physics-004 | hard (4) | Einstein field equations — terms + geometrization | rubric-pending |
| physics-005 | frontier (5) | LQG vs string theory — QG approaches + challenges | rubric-pending |
| physics-006 | unsolved (6) | Cosmological-constant fine-tuning (10^-122) | ungradeable; unsolved tier |

## Last reviewed

2026-05-10 by Raphael (Phase 11 cycle 2 — godify-app APOTHEOSIS).
