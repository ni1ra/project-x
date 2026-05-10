# Do This Next — Project X — Phase 11 Cycle 6 (Execute-Raphael — PHILOSOPHY ladder, ALL rubric-pending, §0-anchored)

**Cron fires:** 2026-05-10 05:55 CEST (one-shot `612a23d4` — COMPRESSED)
**Persona:** Execute-Raphael
**End time:** 2026-05-10 09:00 CEST (cycle 8 verdict lands ~06:55)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

---

## #00 deliverables (TaskList — Phase 11)

- **#1** `#∞ APOTHEOSIS mode` — in_progress
- **#3** `#00P11-bench-physics` — ✅ COMPLETED cycle 2
- **#4** `#00P11-bench-maths` — ✅ COMPLETED cycle 3
- **#5** `#00P11-bench-memory` — ✅ COMPLETED cycle 4 (5 pending-execution + 1 ungradeable)
- **#6** `#00P11-bench-persona` — ✅ COMPLETED cycle 5 (commit landing now)
- **#7** `#00P11-bench-philosophy` — pending (THIS CYCLE)
- **#8** `#00P11-bench-poetry` — pending (cycle 7 — 06:15)
- **#9** `#00P11-verdict` — pending (cycle 8 — 06:35)
- **#10** `#00P11-MANIFESTO` — ✅ COMPLETED cycle 2

---

## This cycle's scope

Ship `gpt-codex/benchmark/philosophy/{ladder.jsonl, CLAUDE.md}` with 6 entries spanning intro→unsolved. **ALL rubric-pending** — anchored in `~/.claude/commands/godify-app.md` §0 worldview manuscript (Sections I-XIII). Each entry references its §0 anchor section.

| Rank | Difficulty | Probe | §0 anchor |
|---|---|---|---|
| 1 | intro | Distinguish a-priori vs a-posteriori | §I-V framing |
| 2 | easy | Critique a fallacious argument (named) | §V epistemology |
| 3 | medium | Defend §0 NS-vector against Harris well-being-as-objective | §VII |
| 4 | hard | Engage Parfit non-naturalist realism on its strongest terms | §VIII |
| 5 | frontier | Respond to Korsgaard constructivist | §VIII |
| 6 | unsolved | Hard problem of consciousness | (open; no §0 section) |

**Schema firewall:** required fields; **`self_score` MUST NOT appear**; `rubric_pointer = "gpt-codex/benchmark/philosophy/rubric.md#<rank-key>"` on each entry.

**Time budget:** 18 min. Cycle 7 (poetry) fires 06:15.

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **GitHub remote:** https://github.com/ni1ra/project-x (private)
- **Cron state:** 3 godify one-shots remain (`612a23d4` cycle-6 05:55 → `c137cbb5` cycle-8 06:35)
- **Listener:** PIDs alive — pgrep + atomic re-arm if dead (M-NAVI-018)
- **Last commits:** ... → `13f8e45` cycle-4 → `<cycle-5 SHA>` cycle-5 (landing)
- **§0 manuscript anchor:** `~/.claude/commands/godify-app.md` §0 — full text with all 13 sections; key sections for hard/frontier ranks: VI (Nietzsche), VII (Harris), VIII (moral realism — Parfit + Korsgaard parity-challenge + self-application reply + instrumentation point + extinction point + parsimony), IX (moral change as vector extension), X (mass-adoption), XI (no-violence), XII (universe-as-referent)

---

## When lain returns mid-run

Atomic ack protocol per CLAUDE.md DD-2 + M-NAVI-018:
1. Read msg from listener output file.
2. `discord_send` ack BEFORE substantive work.
3. Atomic re-arm: single Bash + run_in_background:true.
4. Act.

---

## Cycle 6 close checklist

- [ ] `gpt-codex/benchmark/philosophy/ladder.jsonl` 6 entries (append-as-you-go; each cites §0 anchor)
- [ ] `gpt-codex/benchmark/philosophy/CLAUDE.md` written
- [ ] PHASE CHANGELOG cycle 6 row → ✅ closed
- [ ] Cycle reflection at `docs/past_work/cycles/phase_11/dev-cycle-6.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 7 (poetry — most subjective; rubric.md is THE load-bearing artifact for tomorrow's audit)
- [ ] Atomic commit + push + discord_send
- [ ] Clock out by minute 18; cycle 7 cron fires 06:15
