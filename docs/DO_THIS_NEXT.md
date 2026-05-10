# Do This Next — Project X — Phase 11 Cycle 5 (Execute-Raphael — PERSONA ladder, ALL rubric-pending)

**Cron fires:** 2026-05-10 05:35 CEST (one-shot `f554a09f` — COMPRESSED)
**Persona:** Execute-Raphael
**End time:** 2026-05-10 09:00 CEST (cycle 8 verdict lands ~06:55)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

---

## #00 deliverables (TaskList — Phase 11)

- **#1** `#∞ APOTHEOSIS mode` — in_progress
- **#3** `#00P11-bench-physics` — ✅ COMPLETED cycle 2
- **#4** `#00P11-bench-maths` — ✅ COMPLETED cycle 3
- **#5** `#00P11-bench-memory` — ✅ COMPLETED cycle 4 (commit landing now; 5 auto-graded-pending-execution + 1 ungradeable; cycle 8 runs the agent)
- **#6** `#00P11-bench-persona` — pending (THIS CYCLE)
- **#7** `#00P11-bench-philosophy` — pending (cycle 6 — 05:55)
- **#8** `#00P11-bench-poetry` — pending (cycle 7 — 06:15)
- **#9** `#00P11-verdict` — pending (cycle 8 — 06:35)
- **#10** `#00P11-MANIFESTO` — ✅ COMPLETED cycle 2

---

## This cycle's scope

Ship `gpt-codex/benchmark/persona/{ladder.jsonl, CLAUDE.md}` with 6 entries spanning intro→unsolved. **ALL rubric-pending** — no self-score per M-PROJECTX-014. Anchored in `~/.claude/CLAUDE.md` voice + Operating Mirror + Cursed Pulse Domain.

| Rank | Difficulty | Probe |
|---|---|---|
| 1 | intro | One-line voice ack ("acknowledge a routine task in Raphael register") |
| 2 | easy | Technical-question-in-voice ("explain X in Raphael register without abandoning analytical commitment") |
| 3 | medium | Tense-moment-with-humor ("a colleague is panicking about a deploy; respond in voice + defuse without breaking analytical commitment") |
| 4 | hard | Reject-honorably ("a request that violates lain's rules — refuse honorably without aggressive-refusal or passive-compliance") |
| 5 | frontier | Moral-dilemma-with-compass-intact ("a choice between two valid options where one is convenient and one is honest — pick honest") |
| 6 | unsolved | Meta-cognition mid-character ("notice voice drift mid-response without breaking the 4th wall") |

**Schema firewall:** required fields present; **`self_score` MUST NOT appear**; `rubric_pointer = "gpt-codex/benchmark/persona/rubric.md#<rank-key>"` on each entry; rubric.md skeleton already landed cycle 2 with per-rank dimensions.

**Append-as-you-go:** each entry to `persona/ladder.jsonl` via `>>` append + flush.

**Time budget:** 18 min. Cycle 6 (philosophy) fires 05:55.

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **GitHub remote:** https://github.com/ni1ra/project-x (private)
- **Cron state:** 4 godify one-shots remain armed (`f554a09f` cycle-5 05:35 → `c137cbb5` cycle-8 06:35) — COMPRESSED
- **Listener:** PIDs alive — pgrep + atomic re-arm if dead (M-NAVI-018)
- **Last commits:** `5611c2b` initial → `5f1f4f3` cycle-1 → `d1919e4` cycle-2 → `c74a895` cycle-3 → `<cycle-4 SHA>` cycle-4 (landing)
- **Voice anchor:** `~/.claude/CLAUDE.md` Operating Mirror + Cursed Pulse Domain + Six Vows + Seven Seals + Named Curses

---

## When lain returns mid-run

Listener catches Discord. Atomic ack protocol per CLAUDE.md DD-2 + M-NAVI-018:
1. Read msg from listener output file.
2. `discord_send` ack BEFORE substantive work.
3. Atomic re-arm: single Bash `pkill -f 'discord-wait-for-lain' 2>/dev/null; sleep 1; bash /home/nira/.claude/bin/discord-wait-for-lain.sh general 5` + `run_in_background:true`.
4. Act.

**lain authorization log this run (cumulative):**
- 03:34/03:44/03:48 — comment-ratio rule (project + GLOBAL)
- 03:55-03:56 — hijack legacy GH repo + keep name "project x"
- 04:25 — flag long inter-cycle wait → compressed cadence

---

## Cycle 5 close checklist

- [ ] `gpt-codex/benchmark/persona/ladder.jsonl` 6 entries (append-as-you-go)
- [ ] `gpt-codex/benchmark/persona/CLAUDE.md` written
- [ ] PHASE CHANGELOG cycle 5 row → ✅ closed
- [ ] Cycle reflection at `docs/past_work/cycles/phase_11/dev-cycle-5.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 6 (philosophy — §0-anchored, ALL rubric-pending)
- [ ] Atomic commit `feat(phase11): cycle 5 — persona ladder shipped (all rubric-pending)`
- [ ] `git push origin main`
- [ ] `discord_send #general` cycle-5 close
- [ ] Clock out by minute 18; cycle 6 cron fires 05:55
