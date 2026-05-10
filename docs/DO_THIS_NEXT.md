# Do This Next — Project X — Phase 12 Cycle 5 (Execute-Raphael — advisor + reflections + comment-ratio polish)

**Cron fires:** 2026-05-10 12:17 CEST (one-shot `36e02faa`)
**Persona:** Execute-Raphael
**End time:** 2026-05-10 13:28 CEST (cycle 7 verdict lands ~13:20)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

> **Phase 12 mechanical fix is COMPLETE.** Cycle 1 (algorithm) + cycle 2 (controller) + cycle 3 (ladder/audit_log/addendum) + cycle 4 (tests) shipped end-to-end. memory-004 + memory-005 flipped GREEN; pytest 58 passing; benchmark counts 11/0/21/4. Cycles 5-7 are quality + advisor + verdict + handoff.

---

## #00 deliverables (TaskList — Phase 12)

- **#1** `#∞ APOTHEOSIS mode` — in_progress (3h godify-app pickup)
- **#2** `#00P12-retrieval-mode-disambiguation` — ✅ COMPLETED cycle 2
- **#3** `#00P12-flip-memory-reds` — ✅ COMPLETED cycle 3
- **#4** `#00P12-tests` — ✅ COMPLETED cycle 4
- **#5** `#00P12-verdict + END_TIME handoff` — pending (cycle 7 — 13:07)

---

## This cycle's scope — `advisor()` pre-verdict + reflection sanity pass + comment-ratio polish

### Phase A (~5 min) — `advisor()` call

Per CLAUDE.md heartbeat #14 (prev session's "HONEST GAP — advisor() called 0 times"): call `advisor()` BEFORE the cycle 7 verdict to surface blind spots. The advisor sees the entire conversation history (no parameters needed) and catches:
- Phase 12 done-claim quality issues
- Honest framing concerns (am I overclaiming closure? are there subtle regressions I missed?)
- Backwards compatibility blind spots
- Things to address in the verdict markdown that I haven't thought of

Take the advice seriously. If the advisor flags real issues, address inline. If self-test contradicts advice, surface in a reconcile call rather than silently overriding (per CLAUDE.md advisor protocol).

### Phase B (~5 min) — reflection sanity pass

Re-read `dev-cycle-1.md` through `dev-cycle-4.md`. Spot fixes for:
- Stale time references (e.g., if a cycle reflection said "expected ~13:20" but actual landed earlier)
- Honest framing — no overclaiming, no smuggled self-grades
- Cross-references to actual file paths (dev-cycle-X.md references dev-cycle-Y.md? broken?)
- Comment-ratio compliance in the reflection text itself

Don't rewrite — just spot-fix typos / stale facts / broken refs.

### Phase C (~5 min) — comment-ratio polish on Phase 12 source code

Review the Phase 12 source-file deltas:
- `src/project_x/experiments/semantic_hdc_memory.py:retrieve_structural_full_history` — multi-paragraph docstring + 4 WHY-comments
- `src/project_x/experiments/semantic_memory_agent.py` — `_LIST_ALL_HINTS` + `_is_list_all_query` + `MemoryAgent.process` extension + `compose_answer` extension

Spot-check each for:
- Every WHY-comment is load-bearing (removing it would cost a future reader meaningful context)
- No WHAT-comments narrating identifiers
- No commented-out code
- No "TODO without context" placeholders

If any non-load-bearing comments slipped in, trim them. If a WHY-comment is missing on a load-bearing decision, add it.

### Phase D (~5 min) — folder-CLAUDE.md upkeep check

Per godify-app §9.5: every meaningful directory has a local CLAUDE.md. Phase 11 cycle 8 swept this; verify Phase 12 didn't introduce new directories without docs:
- `tests/test_retrieval_modes.py` is in `tests/` which already has CLAUDE.md → no new dir
- All Phase 12 changes are in existing source/docs/cycle dirs → no new dirs

If `tests/CLAUDE.md` mentions test files explicitly, check it lists `test_retrieval_modes.py`. Update if missing.

### Phase E (~5 min) — commit + Discord + close

PHASE CHANGELOG cycle-5 → ✅ closed. dev-cycle-5.md reflection. DO_THIS_NEXT.md cycle-6 (slack cycle scope). Atomic commit. Push. discord_send.

### Time budget

22-25 min substantive. Sub-budget: 5+5+5+5+5 = 25 min. If advisor fires substantial concerns, sacrifice Phase D first (it's a quick check), then Phase C polish.

### Cycle 5 close checklist

- [ ] `advisor()` called and concerns addressed (or surfaced for cycle 7 if non-trivial)
- [ ] Cycle reflections 1-4 spot-checked for stale facts / broken refs
- [ ] Phase 12 source-code comments verified WHY-only per global policy
- [ ] `tests/CLAUDE.md` updated to mention `test_retrieval_modes.py` if missing
- [ ] PHASE CHANGELOG cycle-5 row → ✅ closed
- [ ] Cycle reflection at `docs/past_work/cycles/phase_12/dev-cycle-5.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 6 (slack — Phase 13 prep)
- [ ] Atomic commit `chore(phase12): cycle 5 — advisor + reflection sanity + comment-ratio polish`
- [ ] `git push origin main`
- [ ] `discord_send #general` cycle 5 close
- [ ] Clock out by minute 22; cycle 6 cron fires 12:42

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **Cycle-4 commit:** to land at end of cycle 4 turn (this turn)
- **Cron state:** 3 godify one-shots remain (`36e02faa` cycle 5 12:17 → `21e719fa` cycle 7 verdict 13:07)
- **Listener:** PID 13711 alive — pgrep + atomic re-arm if dead per M-NAVI-018
- **Tests:** **58 passing** (52 baseline + 6 from cycle 4)
- **Memory ladder:** 5 green / 0 red / 0 rubric / 1 ungrade

---

## When lain returns mid-run

Atomic ack protocol per CLAUDE.md DD-2 + M-NAVI-018:
1. Read msg from listener output file
2. `discord_send` ack BEFORE substantive work
3. Atomic re-arm: single Bash + run_in_background:true
4. Act

---

## M-NAVI-019 standing rule (for all 7 cycles)

Heartbeat-armed while `now < 13:28 CEST` AND named work exists. Premature disarm is fake-stop. Cycle 7 verdict cron is the only legitimate disarm signal.

---

## Phase 12 status at cycle 4 close

- ✅ retrieve_structural_full_history (cycle 1) — chronological full-subject path
- ✅ _LIST_ALL_HINTS + classifier + controller routing + compose_answer extension (cycle 2)
- ✅ memory-004/005 flipped red→green; audit_log rebuilt 11/0/21/4; PHASE_11 addendum (cycle 3)
- ✅ test_retrieval_modes.py — 6 tests, all PASS, full suite 58 passing (cycle 4)
- ⏳ advisor + reflection sanity + comment-ratio polish (cycle 5, THIS CYCLE)
- ⏳ slack cycle for Phase 13 prep / GPT audit prep / explorer (cycle 6)
- ⏳ Phase 12 verdict + END_TIME handoff (cycle 7)

The mechanical fix is fully shipped + tested + documented in benchmark JSON. Cycle 5 catches blind spots and polishes; cycle 6 is true slack (highest-leverage Phase 13 prep); cycle 7 lands the verdict.
