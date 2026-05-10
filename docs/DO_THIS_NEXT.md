# Do This Next — Project X — Phase 11 CLOSED — Phase 12 candidate framing

**Updated:** 2026-05-10 ~06:55 CEST (Phase 11 godify-app run END_TIME handoff)
**Mode:** APOTHEOSIS exits → NORMAL (heartbeat re-armed; godify cron disarmed)
**Status:** **Phase 11 mechanically closed.** All 8 #00 deliverables shipped + verified per A_TO_Z_PLAN.md §0.4 E1-E10. Awaiting lain wake @ 09:00 + Phase 12 framing decision.

---

## What shipped (Phase 11 — verified at 06:55)

- ✅ All 6 domain ladders @ `gpt-codex/benchmark/<domain>/ladder.jsonl` (36 entries total)
  - 9 auto-graded-green (3 physics + 3 maths + 3 memory)
  - 2 auto-graded-red (memory-004 + memory-005 — predicted Phase 10 strict-dominance failure mode confirmed)
  - 21 rubric-pending (awaits GPT/lain audit tomorrow)
  - 4 ungradeable (open problems honestly named)
- ✅ All 6 domain rubric.md per `gpt-codex/benchmark/<domain>/rubric.md`
- ✅ All 6 domain CLAUDE.md folder docs
- ✅ `gpt-codex/benchmark/audit_log.jsonl` (36 rows; GPT filter on `needs_audit: true`)
- ✅ `docs/artifacts/PHASE_11_BENCHMARK.md` verdict markdown
- ✅ `gpt-codex/benchmark/verdict.md` (cross-link)
- ✅ `docs/MANIFESTO.md` (~600 words; Project X intent + long-arc + Phase 12+ candidates)
- ✅ Project `CLAUDE.md` + Universal `~/.claude/CLAUDE.md` (comment-ratio rule promoted to GLOBAL POLICY this run)
- ✅ Folder-CLAUDE.md sweep (E8 met): `src/project_x/`, `src/project_x/experiments/`, `src/project_x/legacy/`, `tests/`, `docs/`, `docs/artifacts/`, `docs/past_work/`, `gpt-codex/benchmark/` + 6 `<domain>/`, `gpt-codex/runs/`
- ✅ FILE INVENTORY in A_TO_Z_PLAN.md §9 (E6 met)
- ✅ Per-cycle commits 1-8 pushed to `origin/main` at https://github.com/ni1ra/project-x (E10)

## What got DEFERRED honestly (Phase 12+ candidates)

- **Audio listening (Whisper + Discord REST polling).** Whisper installed at `/home/nira/.local/bin/whisper`; integration is its own ~1 cycle.
- **Live training algorithm.** Phase 11 ships static benchmark; closing the loop on memory-004/005 red findings via Hebbian replay informed by benchmark performance is Phase 12+.
- **>6-entry-per-domain ladder extension.** Future cycles can extend.

---

## Phase 12 candidate framing (ranked by leverage from Phase 11 verdict)

1. **Memory retrieval-mode disambiguation** (closes the 2 red findings). Implementation: prompt-shape classifier on `MemoryAgent.process` controller; route `list-all` / `summarize-trajectory` prompts to `retrieve_structural_full_history` (no strict-dominance collapse) vs current-preference prompts to existing `retrieve_structural`. Tests: cycle-8 memory-004/005 entries flip green after fix.
2. **Cortical column ensemble** (Council Idea #2 — Hawkins/Numenta direction). Many sparse HDC modules with voting over Phase 10 fact-graph + binding substrate.
3. **Hebbian-replay-informed live training.** Use Phase 11 auto-graded results as reward signal; replay-consolidate emphasizes failure-mode patterns where agent scored red.
4. **GPT audit on the 21 rubric-pending entries** (tomorrow). Re-calibrate per-domain rubric weighting based on what GPT/lain surfaced as failure modes.
5. **Predictive simulation loop** (Council Idea #3).
6. **Open-ended benchmark ladder** (Council Idea #5).
7. **Audio listening** (Whisper integration).

## How a fresh next-instance should resume (post-09:00 lain ack)

1. **Read** in this order:
   - `~/.claude/CLAUDE.md` (universal protocol — comment-ratio rule, M-NAVI-018 atomic listener invariant, Code Comment Discipline section new this run)
   - `<repo>/CLAUDE.md` (project-scoped rules)
   - `docs/MANIFESTO.md` (project intent)
   - `docs/artifacts/PHASE_11_BENCHMARK.md` (verdict — read end-to-end)
   - `Project X Session Mistakes` wiki (M-PROJECTX-001 through 014; especially 014 design-bias-in-the-probe firewall)
   - `Navi Session Mistakes` wiki (M-NAVI-018 listener pkill-rearm atomic invariant; standing-rule going forward)
   - `gpt-codex/benchmark/audit_log.jsonl` (filter `needs_audit: true` for the 21 rubric-pending entries)
2. **Lain ack expected at ~09:00.** Will provide Phase 12 framing or further direction. Default: priority 1 above (memory retrieval-mode disambiguation) is the highest-leverage close on Phase 11's red findings.
3. **GPT audit pass:** lain may run external GPT against `audit_log.jsonl` filter on `needs_audit: true`. Audit grades feed back into per-domain rubric weighting + flag candidate Phase 12 work areas at the rubric-low tail.

## Battlefield (current state at handoff)

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main` at https://github.com/ni1ra/project-x (private)
- **Commits this run:** 8 atomic (initial + 7 cycle-closes; cycle-8 close landing now)
- **Cron state at handoff:** godify cron `c137cbb5` fired + auto-deleted; NORMAL heartbeat re-armed (15-min cadence per CLAUDE.md Step 0)
- **Listener:** alive — pgrep + atomic re-arm if dead per M-NAVI-018
- **TaskList:** `#∞` flipped APOTHEOSIS → NORMAL; 8 #00 deliverables completed; 1 (`#9` verdict) completes at this commit

## lain authorization log this run (cumulative — for fresh instance context)

- 03:34 + 03:44 + 03:48 — code-comment-ratio rule (project-scope → GLOBAL POLICY)
- 03:48 — gn + final-result-by-morning expectation
- 03:55 — hijack legacy GH repo
- 03:56 — keep name "project x" (renamed `projext-x` → `project-x` on GH)
- 04:25 — flag long inter-cycle wait → compressed cadence to 20m back-to-back; verdict landed ~06:55 (~2h+ slack vs original ~08:50)

## Cycle reflections

- `docs/past_work/cycles/phase_11/dev-cycle-1.md` — plan-setup + GH hijack
- `docs/past_work/cycles/phase_11/dev-cycle-2.md` — physics + cycle-1.5 deliverables
- `docs/past_work/cycles/phase_11/dev-cycle-3.md` — maths + cadence compression
- `docs/past_work/cycles/phase_11/dev-cycle-4.md` — memory pending-execution
- `docs/past_work/cycles/phase_11/dev-cycle-5.md` — persona
- `docs/past_work/cycles/phase_11/dev-cycle-6.md` — philosophy §0-anchored
- `docs/past_work/cycles/phase_11/dev-cycle-7.md` — poetry
- `docs/past_work/cycles/phase_11/dev-cycle-8.md` — verdict + END_TIME handoff (landing now)

---

*— Phase 11 ENDS at 06:55 CEST. lain reads at 09:00 wake. SLAUGHTER COMPLETE.*
