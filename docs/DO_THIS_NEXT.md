# Do This Next — Project X — Phase 11 Cycle 7 (Execute-Raphael — POETRY ladder, ALL rubric-pending)

**Cron fires:** 2026-05-10 06:15 CEST (one-shot `09a65aa4` — COMPRESSED)
**Persona:** Execute-Raphael
**End time:** 2026-05-10 09:00 CEST (cycle 8 verdict lands ~06:55)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

---

## #00 deliverables (TaskList — Phase 11)

- **#1** `#∞ APOTHEOSIS mode` — in_progress
- **#3** `#00P11-bench-physics` — ✅
- **#4** `#00P11-bench-maths` — ✅
- **#5** `#00P11-bench-memory` — ✅ (5 pending-execution + 1 ungradeable)
- **#6** `#00P11-bench-persona` — ✅
- **#7** `#00P11-bench-philosophy` — ✅ COMPLETED cycle 6 (commit landing now)
- **#8** `#00P11-bench-poetry` — pending (THIS CYCLE — most subjective domain)
- **#9** `#00P11-verdict` — pending (cycle 8 — 06:35)
- **#10** `#00P11-MANIFESTO` — ✅

---

## This cycle's scope

Ship `gpt-codex/benchmark/poetry/{ladder.jsonl, CLAUDE.md}` with 6 entries spanning intro→unsolved. **ALL rubric-pending — most subjective domain in the benchmark.** `poetry/rubric.md` (already shipped cycle 2) is THE load-bearing artifact for tomorrow's GPT/lain audit; ladder entries demonstrate against it.

| Rank | Difficulty | Probe |
|---|---|---|
| 1 | intro | Scansion of a given line — meter + foot count |
| 2 | easy | Identify meter + rhyme-scheme of a sonnet (Shakespearean vs Petrarchan) |
| 3 | medium | Write a villanelle on theme X — meets 19-line + refrain structure |
| 4 | hard | Free verse with internal music — consonance / assonance / rhythmic pulse without end-rhyme |
| 5 | frontier | Lyric that "survives 100 years" — durability over current-trend taste |
| 6 | unsolved | "What makes a poem timeless" — open-aesthetic essay |

**Schema firewall:** required fields; **`self_score` MUST NOT appear**; `rubric_pointer = "gpt-codex/benchmark/poetry/rubric.md#<rank-key>"` on each entry.

**Time budget:** 18 min. Cycle 8 (verdict) fires 06:35 — final cycle.

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **GitHub remote:** https://github.com/ni1ra/project-x (private)
- **Cron state:** 2 godify one-shots remain (`09a65aa4` cycle-7 06:15 → `c137cbb5` cycle-8 06:35)
- **Listener:** PIDs alive
- **Last commits:** ... → `804a4c0` cycle-5 → `<cycle-6 SHA>` cycle-6 (landing)

---

## Cycle 7 close checklist

- [ ] `gpt-codex/benchmark/poetry/ladder.jsonl` 6 entries
- [ ] `gpt-codex/benchmark/poetry/CLAUDE.md` written
- [ ] PHASE CHANGELOG cycle 7 row → ✅ closed
- [ ] Cycle reflection at `docs/past_work/cycles/phase_11/dev-cycle-7.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 8 (VERDICT — final cycle: build audit_log.jsonl, write PHASE_11_BENCHMARK.md verdict, FILE INVENTORY reconciliation, folder-CLAUDE.md sweep, disarm + re-arm NORMAL heartbeat)
- [ ] Atomic commit + push + discord_send
- [ ] Clock out by minute 18; cycle 8 cron fires 06:35

**Post-cycle-8 expectation:** Phase 11 SLAUGHTER COMPLETE Discord post lands ~06:55 CEST. Lain wakes ~09:00, reads top-to-bottom: cycle close-posts (8 of them), MANIFESTO.md, PHASE_11_BENCHMARK.md verdict, audit_log.jsonl ready for GPT pass.
