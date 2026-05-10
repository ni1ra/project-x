# Do This Next — Project X — Phase 11 Cycle 4 (Execute-Raphael — MEMORY ladder, ALL auto-graded)

**Cron fires:** 2026-05-10 05:15 CEST (one-shot `d21083dd` — COMPRESSED 20m back-to-back)
**Persona:** Execute-Raphael
**End time:** 2026-05-10 09:00 CEST (cycle 8 verdict lands ~06:55 with ~2h+ slack)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

---

## #00 deliverables (TaskList — Phase 11)

- **#1** `#∞ APOTHEOSIS mode` — in_progress
- **#3** `#00P11-bench-physics` — ✅ COMPLETED cycle 2
- **#4** `#00P11-bench-maths` — ✅ COMPLETED cycle 3 (commit landing now)
- **#5** `#00P11-bench-memory` — pending (THIS CYCLE)
- **#6** `#00P11-bench-persona` — pending (cycle 5 — 05:35)
- **#7** `#00P11-bench-philosophy` — pending (cycle 6 — 05:55)
- **#8** `#00P11-bench-poetry` — pending (cycle 7 — 06:15)
- **#9** `#00P11-verdict` — pending (cycle 8 — 06:35)
- **#10** `#00P11-MANIFESTO` — ✅ COMPLETED cycle 2

---

## This cycle's scope

Ship `gpt-codex/benchmark/memory/{ladder.jsonl, CLAUDE.md}` with 6 entries spanning intro→unsolved. **ALL auto-graded** — probes Phase 9-10 HDC stack directly via `agent.process` + expected_turn_id mechanical match. (Memory rubric.md skeleton already landed cycle 2 — enrich auto-grade hooks if a rank-specific dimension surfaces.)

| Rank | Difficulty | Probe | Auto-grade method |
|---|---|---|---|
| 1 | intro | factual recall (single-turn → single-fact) | `expected_turn_id_match` — Raphael's response cites correct turn_id |
| 2 | easy | contradiction resolution (two turns, second supersedes first) | LATEST-wins: `expected_turn_id_match` against superseding turn |
| 3 | medium | multi-hop with citations (two facts joined) | BOTH expected_turn_ids appear in Raphael's cited evidence |
| 4 | hard | temporal reasoning across many turns | `expected_turn_id_match` AND date/sequence ordering correct |
| 5 | frontier | autobiographical episodic-semantic integration | bridges multiple turns into coherent meta-claim; expected_turn_ids ⊆ cited |
| 6 | unsolved | unified theory of memory consolidation | `audit_status: "ungradeable; unsolved tier"` — open theoretical question |

**Auto-grade hooks** (per memory/rubric.md): each entry has an `auto_grade` block with `method: "expected_turn_id_match"`, `expected_turn_ids: list[int]`, `actual_turn_ids: list[int]`, `match: bool`. Cycle 8 verdict-builder runs each entry's prompt through `MemoryAgent.process()` and fills `actual_turn_ids` + `match`.

For cycle 4: I write the entries with EXPECTED behavior fully specified. Cycle 8's verdict-builder is what actually runs `MemoryAgent.process()` against a canonical fixture. Cycle 4 just ships the spec.

**Schema firewall:** required fields present; `self_score` MUST NOT appear; `auto_grade` block on every entry except rank 6 ungradeable; rank 6 has `audit_status: "ungradeable; unsolved tier"`.

**Append-as-you-go:** each entry to `memory/ladder.jsonl` via `>>` append + flush.

**Time budget:** 18 min. Cycle 5 (persona) fires 05:35.

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **GitHub remote:** https://github.com/ni1ra/project-x (private)
- **Cron state:** 5 godify one-shots remain armed (`d21083dd` cycle-4 05:15 → `c137cbb5` cycle-8 06:35) — all COMPRESSED 20-min back-to-back per lain 04:25 flag
- **Listener:** PIDs alive — pgrep + atomic re-arm if dead (M-NAVI-018)
- **Last commits:** `5611c2b` initial → `5f1f4f3` cycle-1 → `d1919e4` cycle-2 → `<cycle-3 SHA>` cycle-3 (landing now)
- **Code refs (memory probes these):**
  - `src/project_x/experiments/semantic_hdc_memory.py` — Layer 3 HDC + structural retrieval + binding
  - `src/project_x/experiments/semantic_memory_agent.py` — Layer 4 MemoryAgent.process + run_tool + replay
  - `tests/test_killer_milestone.py` — Phase 10 EXIT GATE acceptance (capability templates)

---

## When lain returns mid-run

Listener catches Discord. Atomic ack protocol per CLAUDE.md DD-2 + M-NAVI-018:
1. Read msg from listener output file.
2. `discord_send` ack BEFORE substantive work.
3. Atomic re-arm: single Bash with `pkill -f 'discord-wait-for-lain' 2>/dev/null; sleep 1; bash /home/nira/.claude/bin/discord-wait-for-lain.sh general 5` + `run_in_background:true`.
4. Act.

**lain authorization log this run (cumulative):**
- 03:34 — code-comment-ratio rule (project-scope)
- 03:44 — comment-ratio refinement
- 03:48 — promote comment rule to GLOBAL POLICY
- 03:48 — gn + final-result-by-morning
- 03:55 — hijack legacy GH repo
- 03:56 — keep name "project x" (renamed projext-x → project-x)
- **04:25 — flag long inter-cycle wait → compressed cadence to 20m back-to-back; verdict lands ~06:55 with ~2h+ slack**

---

## Cycle 4 close checklist

- [ ] `gpt-codex/benchmark/memory/ladder.jsonl` 6 entries (append-as-you-go)
- [ ] `gpt-codex/benchmark/memory/CLAUDE.md` written (mirrors physics/maths shape)
- [ ] (rubric.md skeleton already landed cycle 2 — enrich if needed)
- [ ] PHASE CHANGELOG cycle 4 row → ✅ closed
- [ ] Cycle reflection at `docs/past_work/cycles/phase_11/dev-cycle-4.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 5 (persona — ALL rubric-pending)
- [ ] Atomic commit `feat(phase11): cycle 4 — memory ladder shipped (all auto-graded)`
- [ ] `git push origin main`
- [ ] `discord_send #general` cycle-4 close
- [ ] Clock out by minute 18; cycle 5 cron fires 05:35
