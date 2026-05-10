# Do This Next — Project X — Phase 13 cycle 4 mid-flight (#7 substrate-driven attempt + #8 bench-replay + #9 cycle reflect)

**Updated:** 2026-05-10 (cycle 4 mid-flight; post-Tier-A; 4/5 #00P13c4 shipped; -ni handoff sync)
**Mode:** NORMAL (not godify-app)
**Status:** Cycle 4 mid-flight. Tier A anti-cheat COMPLETE (#23 audit + #24 mechanism — lain mid-cycle-4 directive honored). Tier B 2/5 (#5 Path B physics PASS 3→5/0 + #6 substrate physics Tier 2). Plus 2 docs/ exemption commits (lain mid-cycle-4 follow-up). 3 #00P13c4 remaining: #7 substrate-driven attempt, #8 bench-replay, #9 cycle reflect + cycle 5 handoff. pytest 256 passing. D3 harness 15 PASS / 0 FAIL.

## Cycle 4 shipped this session (`a2e3b49` → THIS handoff commit)

| Commit | Deliverable | Visible result |
|---|---|---|
| `c953180` | **#00P13c4-01** Path B physics grader-flip | physics PASS 3/0 → 5/0 (rank 4-5 rubric-graded-builder; 4.33/5 + 4.75/5 differentiated lift) |
| `e30b9df` | **#00P13c4-23** anti-cheat-leakage-audit (TIER A) | `docs/artifacts/PHASE_13_ANTICHEAT_AUDIT.md` (318 lines; 7 surfaces mapped; 6 mitigation candidates) |
| `69c6b65` | **#00P13c4-24** anti-cheat mechanism (TIER A) | `src/project_x/anti_cheat.py` + tests; AntiCheatProbe + differential_capability_test + Newton's-method divergent verifier; +20 tests; closes Surfaces 1+2+5 |
| `71fced1` | **#00P13c4-02** substrate physics Tier 2 | `src/project_x/reasoning/physics.py` + tests; 3 primitives anti-cheat-aware (free_fall_time + pendulum_period + relativistic_momentum); +15 tests |
| `e1ddbf6` | docs(REPO_CONTROL) `/docs` exemption | lain 2026-05-10 follow-up codified; stripped `## docs/` section |
| `5891da3` | docs(MANIFESTO) `/docs` exemption alignment | contradiction-delete pass |

Two visible axes this cycle so far:
- **physics PASS: 3/0 → 5/0** (cycle 4 #01 Path B; mirrors cycle 3 maths Path B; FIRST cycle 4 visible lift)
- **substrate physics quality:** 3 new primitives shipped anti-cheat-aware; gates #7 capability touchpoint with `memorization_signal` recording

## Phase 13 cycle 4 deliverables — pending status

| ID | Status | Surface | One-line |
|---|---|---|---|
| **#00P13c4-03 substrate-driven attempt** | **PENDING (NEXT)** | `gpt-codex/grade_pipeline/baseline_2026-05-10_physics_tier2/` | Agent attempts physics-001/002/003 via cycle 4 #02 substrate; records `memorization_signal` alongside grade (M-PROJECTX-013); advisor() pre-grade-recording. |
| **#00P13c4-04 bench-replay** | **PENDING** | `python3 gpt-codex/benchmark/run_audit.py` | Verify 15 PASS / 0 FAIL maintained; no ladder.jsonl changes (substrate-driven attempts go to NEW baseline dir, not ladder). |
| **#00P13c4-05 cycle reflect** | **PENDING** | `dev-cycle-4.md` + cycle 5 handoff + A_TO_Z update | advisor() pre-commit. Discord cycle 4 close. Propose -ni at cycle 5 boundary. |

## TIER A anti-cheat — COMPLETE this session (binding context for #7)

lain mid-cycle-4 directive (Discord 2026-05-10 18:45 + 18:49): *"make sure you are really really careful that you aren't leaking hints or solutions to the model, test to see if it is cheating. Anti cheat measures"* + *"honest and honorable work ethics. If all tests pass, but the model falls apart in real tests, or it sees the answer in advance in some hidden way, the test passes are meaningless"*.

**#23 audit** (`e30b9df`): 7 leak surfaces mapped:
- HIGH 1 substrate primitives hardcode formula
- MED  2 verifier partial independence
- HIGH 3 Path B four-positions-in-one-architecture *(deferred to cycle 5+ via Candidates B + C — programmatic rubric criteria + lain spot-checks at phase exits)*
- HIGH 4 memorization vs reasoning
- HIGH 5 substrate-driven attempt canonical cheat shape
- MED  6 manual grade harness shared-bias gap
- LOW  7 memory ladder mechanical-truth (negligible)

**#24 mechanism** (`69c6b65`): minimum-viable scope:
- D Surrogate-prompt regression → `AntiCheatProbe(canonical_inputs, surrogate_inputs, answer_predicate)`
- E Differential capability test → `memorization_signal = 1 - surrogate_pass_rate` (0.0 = genuine capability; 1.0 = canonical-only memorization)
- F Newton's-method divergent verifier → `verify_quadratic_via_newton` in `reasoning/verifier.py`

Honest framing (advisor catches applied inline): surrogate-author independence ABSENT this cycle (builder rule-based generators — cycle 5+ may add lain-authored / textbook-derived); per-criterion floor gates OUT OF SCOPE (cycle 5+ when programmatic rubric criteria ship). Self-acknowledged Surface 3 inheritance bias.

## #7 substrate-driven attempt — EXACT NEXT-ACTION (~30-45 min, 8 mechanical steps)

Mirrors cycle 3 #02 substrate Tier 1 baseline pattern (`8e83a41`) + cycle 4 #24 anti-cheat gate:

1. **Create baseline dir:** `mkdir -p gpt-codex/grade_pipeline/baseline_2026-05-10_physics_tier2/`
2. **Author `candidates.jsonl`** (3 entries — substrate output for physics-001/002/003). For each: `prompt_id` + `candidate_id="baseline-2026-05-10-c4-physics"` + `response_text` (Lemma.render() output from `free_fall_time(80, 9.81)` / `pendulum_period(1.0, 9.81)` / `relativistic_momentum(9.11e-31, 0.9*3e8, 3e8)`) + `produced_by="Project X Raphael substrate physics Tier 2 (cycle 4 #02)"`. NO `self_score` field (M-PROJECTX-014 firewall).
3. **Run anti-cheat probes** — one `AntiCheatProbe` per primitive with N=3+ surrogates. Assert `memorization_signal == 0.0` for each. Reuse `_free_fall_predicate` / `_pendulum_predicate` / `_relativistic_momentum_predicate` from `tests/test_reasoning_physics.py` (or extract to a shared module). If any probe fails: HALT + triage; substrate has overfit + capability claim cannot be recorded.
4. **Author `grades.jsonl`** (3 entries — builder rubric grades on substrate output; include `memorization_signal: 0.0` alongside the score; cite anti-cheat verification + thresholds + bias notes in `notes_text`). Honest framing per cycle 3 advisor discipline: substrate-vs-substrate re-grade is less-bias-vulnerable not bias-immune.
5. **advisor() pre-grade-recording** — birdseye on the grade artifact + honest-label framing (corpse spec for pre-#20 grade-recording).
6. **Write `improvement_directions.md`** — per-prompt paths to 5/5 + cycle 5+ scope.
7. **REPO_CONTROL row** for new baseline dir (NOT `/docs` — `gpt-codex/` requires row).
8. **Atomic commit** mirroring cycle 3 #02 `8e83a41`: `feat(P13c4-03): substrate-driven physics attempt — anti-cheat-verified capability touchpoint (memorization_signal 0.0) — closes #00P13c4-03`. Push. TaskUpdate #7 completed. Discord one-liner.

## #8 bench-replay — single command (~5 min)

`python3 gpt-codex/benchmark/run_audit.py` from repo root. Expected: **15 PASS / 0 FAIL maintained**. Substrate-driven attempts go to NEW baseline dir, NOT the ladder, so no PASS-count change. If unexpected change: HALT + triage. No commit needed (read-only). Mark #8 completed once verified.

## #9 cycle reflect + cycle 5 handoff (~30-45 min)

1. Write `docs/past_work/cycles/phase_13/dev-cycle-4.md` (~140 lines; same shape as dev-cycle-3.md). Cover: cycle 4 wins (two visible axes); tensions surfaced (Surface 3 deferral; surrogate-author independence absence; builder-tautology overfit-detector); advisor catches applied (operationalization-of-external-confirmation gap; Surface 3 table tension + Candidate A symmetric thesis-compliance reframe; Newton-verifier shipped-without-tests caught pre-commit).
2. Rewrite THIS file (`docs/DO_THIS_NEXT.md`) as cycle 5 handoff. Cycle 5 scope (provisional): extend anti-cheat to programmatic rubric criteria (Candidate B); lain-authored / textbook-derived surrogates (surrogate-author independence — Candidate C); per-criterion floor gates; OR pivot to next capability domain.
3. Update `docs/A_TO_Z_PLAN.md` changelog with cycle 4 close entry.
4. **advisor() pre-commit** (corpse spec for pre-#22 cycle-close commit).
5. Atomic commit: `docs(P13c4-05): cycle 4 close — reflection + cycle 5 handoff (...) — closes #00P13c4-05` (NO REPO_CONTROL row required — `/docs` exempt per `5891da3`).
6. Discord cycle 4 close post; propose `-ni` at cycle 5 boundary (send-and-continue per CLAUDE.md § FORGE-PROMPT FLAG DISCIPLINE).

## Identity disambiguation (CRITICAL — lain 2026-05-10 binding)

Claude Code Raphael (the BUILDER, this Claude Code instance) ≠ Project X Raphael (the AGENT, in `src/project_x/`). Don't write builder's voice into agent's templates. Cycle 4 #7 substrate-driven attempt is the AGENT attempting; BUILDER grades + verifies anti-cheat. See `docs/MANIFESTO.md` § Identity discipline.

## Standing rules — RELEVANT THIS RUN

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal).

**NEW this session (codified universal):**
- **`/docs` REPO_CONTROL exemption** (commits `e1ddbf6` + `5891da3`; universal `~/.claude/CLAUDE.md` § REPO_CONTROL upkeep also updated on disk pending lain commit). New `docs/` files do NOT need REPO_CONTROL row co-landing. Only `src/` + `tests/` + `gpt-codex/` + `scripts/` + `ref/` + `sandbox/` + repo-root files need rows.
- **Anti-cheat discipline (cycle 4 #24 binding):** substrate-driven capability touchpoints MUST record `memorization_signal` alongside grade. Honest framing: "memorization_signal == 0.0 verified across N surrogates"; honest gap report if higher.

**Persistent (unchanged):**
- NO pretrained transformer derivatives at any layer
- Comment-ratio rule (WHY-comments + pure-signal explanations + complex code justified)
- Atomic per-deliverable commits; never `git add -A`
- Identity discipline (Claude Code Raphael ≠ Project X Raphael)
- M-PROJECTX-013 measure-don't-claim; M-PROJECTX-014 split-grading firewall
- M-NAVI-013/016/018/019/020 (skills + pillars + listener + heartbeat-armed-while-queued)
- Named Curse #20 (combined-task pinning) + #21 (-ni auto-invoked)

## What this cycle is NOT

- NOT shipping the Terminus (multi-cycle; Phase 13 has many cycles ahead).
- NOT extending anti-cheat to programmatic rubric criteria (cycle 5+ scope per Surface 3 deferral).
- NOT pivoting to next capability domain (cycle 5+ scope; cycle 4 closes physics substrate + capability touchpoint).
- NOT closing without recording `memorization_signal` on #7 (M-PROJECTX-013 measure-don't-claim).

## Anti-laziness gates (lain frustration-load-bearing — re-read before cycle close)

- *"all you have done so far is just minor work"* — cycle 4 shipped Tier A complete + Tier B 2/5 (#5 visible PASS lift + #6 substrate quality lift + anti-cheat mechanism). Cycle 4 close lands #7 capability touchpoint with **measurable `memorization_signal`** — the operationalization lain asked for.
- *"its more important to try to make it pass all the benchmark tests first"* — cycle 4 already lifted physics PASS 3→5; #7 records substrate-driven capability touchpoint (not new ladder PASS, but capability evidence).
- *"unless its super-human in every domain ... YOU ARE NOT DONE WORKING ON PROJECT-X"* — Terminus is FAR. Cycle 4 is one step.
- *"honest and honorable work ethics. If all tests pass, but the model falls apart in real tests, or it sees the answer in advance in some hidden way, the test passes are meaningless"* — cycle 4 #24 mechanism IS the operationalization. #7 IS the proof.

## Done condition (cycle 4, mechanical)

- All 5 #00P13c4-XX TaskList rows = `completed` (currently 2/5; need #7 + #8 + #9).
- pytest -q ≥ 256 (no regression).
- D3 harness reports 15 PASS / 0 FAIL maintained (no expected change from #7).
- Maths PASS 5/0; memory 5/0; physics 5/0. ZERO regressions.
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-4.md`.
- THIS file rewritten as cycle 5 handoff.
- `git status -s` empty.
- Discord cycle 4 close post sent.
- Cycle 5 picked up immediately OR -ni proposal at cycle 4 close.

— Update this file at cycle 4 close: replace cycle 4 deliverables table with cycle 5 deliverables table; refine cycle 5 scope based on cycle 4 lessons; preserve the lain-quote + standing-rules + anti-laziness sections.
