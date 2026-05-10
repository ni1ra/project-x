# Do This Next — Project X — Phase 13 cycle 4 (physics: Path B + substrate Tier 2)

**Updated:** 2026-05-10 (post-cycle-3 close)
**Mode:** NORMAL (not godify-app)
**Status:** Cycle 3 closed at THIS handoff commit. 5/6 #00P13c3-XX shipped (#04 explicitly deferred to cycle 4 #03 per advisor pacing flag) + 3 Tier A instruction-discipline rows shipped (universal CLAUDE.md alignment). Pytest 202 → 221 (+19 cycle 3 D2 tests). Bench-replay 13 PASS / 0 FAIL / 23 rubric-pending (maths 5/0 — Path B contribution; memory 5/0; physics 3/0 — no regressions). Reflection at `docs/past_work/cycles/phase_13/dev-cycle-3.md`.

## Cycle 3 wins recap (two visible axes)

```
maths PASS:        3/0  →  5/0    (cycle 3 #01 Path B grader-flip; visible COUNT lift; FIRST in Phase 13)
maths-001 quality: 4.0/5 → 4.5/5  (cycle 3 #02 Tier 1 substrate extensions; substrate-vs-substrate)
maths-002 quality: 4.0/5 → 4.75/5 (cycle 3 #02 Tier 1; differentiated +0.75 — Vieta invariant axis)
```

## Phase 13 cycle 4 deliverables (#00P13c4-XX — pin in TaskList immediately at cycle 4 open per IMMEDIATE-TASK-ADD discipline)

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c4-01-pathB-physics-rank-4-5-grader-flip** | **HIGH** | `gpt-codex/grade_pipeline/baseline_2026-05-XX_physics_pathB/` + ladder.jsonl + run_audit.py | Path B repeat on physics-004 (Einstein field equations conceptual) + physics-005 (LQG vs string theory comparative). Builder grades existing hand-crafted `raphael_response` against rubric proof-shape dimensions. Honest audit_status: "rubric-graded-builder; pending external confirmation" (NOT "rubric-graded-green" per cycle 3 advisor catch). Apply same threshold-grader-independence-absent disclosure. **Target: physics PASS 3/0 → 4-5/0** (mirrors cycle 3 #01 maths Path B). |
| **#00P13c4-02-substrate-physics-tier2-extensions** | MED | `src/project_x/reasoning/physics.py` (NEW) + `tests/test_reasoning_physics.py` (NEW) | From-scratch closed-form physics primitives: `free_fall_time(h, g)` (1-step, math.sqrt) + `pendulum_period(L, g)` (1-step, math.sqrt + math.pi) + `relativistic_momentum(m, v, c)` (2-step, Lorentz-factor + p=γmv). Each lemma: `add_introduction` (math-WHY: kinematics from constant-acceleration / SHM / Lorentz factor) + `add_invariant_check` where physically meaningful (e.g. relativistic momentum reduces to mv in v << c limit). REPO_CONTROL row in same commit. |
| **#00P13c4-03-substrate-driven-attempt** [carries forward cycle 3 #00P13c3-04 deferred per advisor pacing flag] | HIGH | `gpt-codex/grade_pipeline/baseline_2026-05-XX_physics_tier2/` | Substrate-driven attempt on physics-001 + physics-002 + physics-003 via cycle 4 #02 substrate. Builder grades each via physics rubric. advisor() pre-recording per per-section pick spec. |
| **#00P13c4-04-bench-replay** | MED | `python3 gpt-codex/benchmark/run_audit.py` | Target: physics PASS up from 3/0 (Path B contribution from #01); maths 5/0 (no regression); memory 5/0 (no regression). 23 rubric-pending may drop to 21 if Path B lands clean. |
| **#00P13c4-05-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-4.md` + rewrite THIS file | Same shape as cycles 1-3 D6. advisor() pre-commit. Discord cycle 4 close post; consider `-ni` proposal at this transition (send-and-continue per CLAUDE.md FORGE-PROMPT FLAG DISCIPLINE). |

**Note:** cycle 4 ships 5 deliverables (vs cycle 1-3's 6) by absorbing #00P13c3-04 → #00P13c4-03. Cleaner shape; advisor pacing flag honored.

## Identity disambiguation (CRITICAL — lain 2026-05-10 binding)

Same as cycles 1-3 — Claude Code Raphael (the BUILDER, this conversation) ≠ Project X Raphael (the AGENT, the artifact in `src/project_x/{experiments,persona,reasoning}/`). Don't write the builder's voice into the agent's templates. The agent's reasoning substrate is in `src/project_x/reasoning/`; cycle 4 #02 ships `physics.py` extending the substrate. See `docs/MANIFESTO.md` § Identity discipline.

## Order of operations (cycle 4)

1. **Recon (Phase 0 DD):** read MANIFESTO + REPO_CONTROL + A_TO_Z + this file + `docs/past_work/cycles/phase_13/dev-cycle-3.md` + `docs/artifacts/PHASE_13_C3_PHYSICS_SURVEY.md` + `gpt-codex/grade_pipeline/baseline_2026-05-10_pathB/improvement_directions.md` + `gpt-codex/grade_pipeline/baseline_2026-05-10_math_tier1/improvement_directions.md` + `Project X Session Mistakes` wiki + `Navi Session Mistakes` wiki. Verify TaskList state.
2. **Pillars:** `Skill('skills:pick-skill')` + `Skill('skills:sharpen-todos')`.
3. **Per-deliverable atomic commits** with REPO_CONTROL co-landing.
4. **advisor() at substantive boundaries** — pre-#01 grade recording (M-PROJECTX-013 measure-don't-claim); pre-#03 grade recording (capability touchpoint); pre-#05 commit (cycle close).
5. **Discord one-liner per closure** + Tier B cycle 4 close post + propose -ni at cycle 4 close.

## Standing rules (load-bearing this run — CYCLE-3-CODIFIED additions)

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (NEW SECTIONS):

**Cycle 3 codified globally (Tier A) — apply mechanically:**
- **§ FORGE-PROMPT FLAG DISCIPLINE** (~/.claude/CLAUDE.md): `-ni` is lain-only; `-c` is agent-autonomous; `-ni` proposal via Discord = send-and-continue (NEVER wait). At cycle 4 close, propose `-ni` if context heavy; auto-continue into cycle 5 #01 if lain doesn't catch.
- **R1 § IMMEDIATE-TASK-ADD discipline** (~/.claude/CLAUDE.md): when lain adds tasks to queue mid-session, IMMEDIATELY add EACH ASK as its OWN TaskList row. Don't combine. Don't defer. Auto-compact-survival.
- **Named Curse #20** (combined-task pinning failure) + **Named Curse #21** (forge-prompt -ni auto-invoked) — codified failure modes.

**Persistent rules:**
- NO pretrained transformer derivatives — substrate Tier 2 physics primitives stay hand-rolled (math.sqrt + math.pi only; no scipy.constants, no physics-engine wrappers).
- Comment-ratio rule — every WHY-comment justifies why the primitive exists.
- REPO_CONTROL row in same commit as new file/dir.
- Identity discipline.
- M-NAVI-018: atomic listener pkill+rearm.
- M-NAVI-019/020: heartbeat-armed-while-queued-work-exists.
- M-DRM-060/062: strategic-framing questions go in this file for next-cycle, NOT mid-cycle Discord.
- M-PROJECTX-013 + M-PROJECTX-014: measure-don't-claim + split-grading firewall.

## What this cycle is NOT

- NOT shipping the Terminus (multi-cycle; Phase 13 has many cycles ahead).
- NOT direct internet access for the agent (deferred until safety proven).
- NOT cycle 3's Path B revisited — once is enough; cycle 4's Path B is on PHYSICS rank 4-5, distinct entries.
- NOT closing without producing visible PASS lift if Path B succeeds (rubric thresholds met). If Path B fails on physics-004/005 rubric, surface concretely in cycle 4 reflection (M-PROJECTX-013).

## Anti-laziness gates (lain frustration-load-bearing — re-read before each cycle close)

- *"all you have done so far is just minor work"* — cycle 2 shipped substrate (4.0/5 quality); cycle 3 shipped Path B (3/0 → 5/0 PASS) + Tier 1 (4.5-4.75/5 quality). Cycle 4 SHOULD lift physics PASS (3/0 → 4-5/0) AND ship physics substrate quality. Two-axis cumulative progress.
- *"its more important to try to make it pass all the benchmark tests first"* — cycle 4 #01 IS the path to physics PASS lift.
- *"unless its super-human in every domain ... YOU ARE NOT DONE WORKING ON PROJECT-X"* — Terminus is FAR. Phase 13 cycle 4 is one step.
- *"i expect you to have a REALLY good reason to use me as blocker"* — defensible defaults; Discord propose-and-continue.

## Done condition (cycle 4, mechanical)

- All 5 #00P13c4-XX TaskList rows = `completed`.
- pytest -q ≥ 221 (cycle 3 baseline; expect ~240+ with new physics tests).
- D3 harness reports physics PASS ≥ 4/0 (Path B lift) OR honest gap report if Path B rubric thresholds not met.
- Maths PASS still 5/0; memory 5/0. ZERO regressions.
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-4.md`.
- THIS file rewritten as cycle 5 handoff.
- `git status -s` empty.
- Discord cycle 4 close post sent.
- Cycle 5 picked up immediately OR -ni proposal at cycle 4 close.

— Update this file at cycle 4 close: replace cycle 4 deliverables table with cycle 5 deliverables table; refine cycle 5 scope based on cycle 4 lessons; preserve the lain-quote + standing-rules + anti-laziness sections.
