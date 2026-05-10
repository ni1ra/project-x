# Do This Next — Project X — Phase 13 cycle 2 (math reasoning substrate)

**Updated:** 2026-05-10 (post-cycle-1 close + lain mid-D4 reframe: intelligence first, persona is fine-tuning)
**Mode:** NORMAL (not godify-app)
**Status:** Cycle 1 closed at THIS handoff commit. Last live cycle: P13.C1 — sandbox + persona + grader-min substrate + ONE capability touchpoint (baseline-attempt). 6/6 deliverables shipped; pytest 153 passed; D3 harness 11/0 PASS. Reflection at `docs/past_work/cycles/phase_13/dev-cycle-1.md`. Last commit: `<this-cycle's-SHA>` (filled at next-cycle-open recon).

## lain's reframe (verbatim — cycle 2 priority)

> *"to me, its more important to try to make it pass all the benchmark tests first, achieving the intelligence before giving it any persona. if you want persona to work from start idk what system you have now, but inucluding a benchmark domain with Qs like 'Who are you?' and stuff could reveal if it understands what it is, and how its supposed to act. but this is more fine-tuning. and fine tuning is something to focus on after the core intelligence is there."*  — lain, 2026-05-10 mid-D4

> *"you also need really really good data. better and curated data -> better results for our AI"*  — lain, 2026-05-10 (Phase-level eternal — `#00P13-data-curation` in TaskList)

**Translation for cycle 2:** capability buildout, not persona refinement. Math reasoning substrate first because math has verifiable answers (numerical/symbolic match) and runs cleanly inside the cycle-1 sandbox. Curated data integration: cycle 2 needs a curated MATH derivations corpus (textbook-quality lemma chains + worked examples), not poetry/philosophy entries.

## Cycle 1 baseline scores (the data that justifies cycle 2's priority)

```
poetry-001:     technique 1/5, meaning 1/5, voice 2/5  (weighted aggregate 1.3/5)
philosophy-001: argument_quality 1/5, position_coherence 1/5, section_0_fidelity 1/5, voice 2/5  (weighted 1.2/5)
```

Both prompts returned absent (top cosines 0.030 / 0.016 below threshold 0.32) — agent has no curated corpus + no generator layer. Persona-wrap fired correctly (D2 plumbing works) but plumbing on null evidence is theatre. **D2 stays shipped (benign — doesn't regress memory ladder per D5); cycle 2 doesn't refine D2; cycle 2 builds the intelligence the wrap will later have content to wrap.**

Full reflection + improvement-direction notes: `docs/past_work/cycles/phase_13/dev-cycle-1.md` + `gpt-codex/grade_pipeline/baseline_2026-05-10/improvement_directions.md`.

## Phase 13 cycle 2 deliverables (#00P13c2-XX — pin in TaskList immediately at cycle 2 open)

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c2-01-math-recon** | LOW | Read-only — `gpt-codex/benchmark/maths/ladder.jsonl` + `rubric.md` | Survey all 6 math ladder entries; classify by verification path (numerical-close / symbolic-match / proof-required); identify 2-3 entries scope-fit for cycle 2 generator (likely rank 1-3 closed-form). Output: `docs/artifacts/PHASE_13_C2_MATH_SURVEY.md`. |
| **#00P13c2-02-symbolic-substrate** | HIGH | `src/project_x/reasoning/` (new) — symbolic.py + tests | From-scratch symbolic reasoning primitives: lemma chain dataclass + derivation step recorder + numerical-verification hook. NO sympy (thesis-compliance check needed first; sympy is symbolic-AI not pretrained-transformer but counts as "borrowing other tools" — confirm with lain or default to from-scratch arithmetic + algebra primitives). MINIMUM viable: closed-form arithmetic + linear equation solving, expandable in cycle 3+. |
| **#00P13c2-03-numerical-verifier** | MED | `src/project_x/reasoning/` — verifier.py + tests | Sandbox-bound Python script generator: agent emits a derivation; `numerical_verify(derivation)` writes a verification script to sandbox, runs via `run_python_sandbox` (D1), reads output, reconciles. Closes the verification loop using cycle-1 substrate. |
| **#00P13c2-04-math-baseline-attempt** | **HIGH** | `gpt-codex/grade_pipeline/baseline_<date>/` (new per-cycle baseline subdir) | THE capability touchpoint — analog of cycle 1 D4. Agent attempts ≥ 2 math ladder entries via the new symbolic substrate + numerical verifier. Builder grades using `gpt-codex/benchmark/maths/rubric.md`. Output: per-entry score + improvement directions for cycle 3+. **The score should NOT be 1/5 this time** — substrate is supposed to produce something gradable above absent. If it does score 1/5: that's a structural failure of cycle 2; surface concretely. |
| **#00P13c2-05-bench-replay** | MED | `python3 gpt-codex/benchmark/run_audit.py` | D3 harness re-run; target: maths PASS count lifts above 3/0 if new green entries emerge from substrate-driven re-attempts of previously rubric-pending entries. Memory ladder must still be 5/0; physics still 3/0. ZERO regressions. |
| **#00P13c2-06-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-2.md` + rewrite THIS file | Cycle reflection includes: (a) what shipped + commit SHAs, (b) baseline-attempt scores + improvement-directions, (c) architectural tensions surfaced (e.g., sympy-or-from-scratch question outcome; verification-loop bottlenecks), (d) cycle 3 provisional scope refined per cycle 2 lessons. Rewrite this file as cycle 3 handoff. |

## Identity disambiguation (CRITICAL — lain 2026-05-10 binding)

Same as cycle 1 — Claude Code Raphael (the BUILDER, this conversation) ≠ Project X Raphael (the AGENT, the artifact in `src/project_x/experiments/`). Don't write the builder's voice into the agent's templates. See `docs/MANIFESTO.md` § Identity discipline.

## Order of operations (cycle 2)

1. **Recon (Phase 0 DD):** read MANIFESTO + REPO_CONTROL + A_TO_Z + this file + `docs/past_work/cycles/phase_13/dev-cycle-1.md` (cycle 1 reflection — has the baseline scores + tensions) + `Project X Session Mistakes` wiki + `Navi Session Mistakes` wiki. Verify TaskList has the 6 #00P13c2-XX rows (CREATE if absent — sharpen-todos audit pillar) + `#∞: NORMAL mode operation` still pinned + `#00P13-data-curation` Phase-level row still pinned.
2. **Pillars:** `Skill('skills:pick-skill')` + `Skill('skills:sharpen-todos')`.
3. **Picked execution skill(s):** likely `/run-loop ATOMIC` for the 6-deliverable atomic queue + `/design-before-build` for the symbolic-substrate + verifier interfaces (architectural — sympy-or-from-scratch decision needs design phase) + `/skills:auto-review` per-fix.
4. **Per #00P13c2-XX:** design (with `/design-before-build` for substrate + verifier) → code → test → commit (with REPO_CONTROL row in same commit if new files/dirs) → push → Discord one-liner ack. Same atomic per-deliverable cadence as cycle 1.
5. **Cycle close:** Bench replay → cycle reflection → rewrite this file as cycle 3 handoff → Discord cycle 2 close post → pivot to cycle 3 immediately.

## Cycle 3 provisional scope (next-next handoff target)

**Physics derivation engine.** Closed-form first (extends cycle 2 math substrate to physics — F=ma applications, electromagnetics from Maxwell's equations, thermodynamics from first principles). Sandbox-runnable verification: Python script in sandbox computes a numerical solution; agent's symbolic derivation must match. Iterates against `gpt-codex/benchmark/physics/` ladder.

(Cycle 3's scope will be REFINED in this file at cycle 2 close based on what was learned.)

## Standing rules (load-bearing this run)

See `docs/MANIFESTO.md` § Standing orders. Specifically for cycle 2:

- **NO pretrained transformer derivatives** — symbolic substrate must be from-scratch. sympy decision: defer to lain or default-deny per organic-thesis (sympy is a symbolic computation library, not a transformer, but "borrowing tools" requires explicit thesis-compliance reasoning before adopting).
- **Comment-ratio rule** — every WHY-comment justifies why the substrate exists.
- **REPO_CONTROL row in same commit as new file/dir** (lain pristine-gate, 2026-05-10) — non-negotiable.
- **Identity discipline** — Claude Code Raphael ≠ Project X Raphael.
- **M-NAVI-018:** atomic listener pkill+rearm in single Bash invocation.
- **M-NAVI-019/020:** heartbeat-armed-while-queued-work-exists.
- **M-DRM-060/062 (cycle 1 fresh-catch):** strategic-framing questions go in DO_THIS_NEXT for next-instance to encounter at cycle open, NOT in Discord posts that bounce lain. Only escalate to lain on SHIPPING blockers (math wrong, schema invalid, regression).
- **Curated math corpus (#00P13-data-curation row applied to cycle 2):** if cycle 2 substrate needs grounding examples, they're a curated math derivations corpus — hand-vetted lemma chains + worked closed-form solutions, NOT auto-scraped textbook PDFs.

## What this cycle is NOT

- NOT shipping the Terminus (multi-cycle; cycle 2 is intelligence substrate; physics + poetry/philosophy + chat are cycles 3-N).
- NOT touching `~/.claude/CLAUDE.md` for project-specific reasons.
- NOT direct internet access for the agent (deferred until safety proven).
- NOT a one-cycle phase — Phase 13 is multi-cycle through capability + benchmark iteration.
- NOT persona refinement (deferred per lain reframe; D2 persona stays shipped, returns when persona benchmark domain measures it later).

## Anti-laziness gates (lain frustration-load-bearing — re-read before each cycle close)

- *"all you have done so far is just minor work"* — the audit-fix run was minor; cycle 1 substrate was substantive but still SUBSTRATE not capability. Cycle 2 must ship CAPABILITY (math reasoning loop that actually produces a verifiable derivation). If you find yourself shipping more substrate or refinements without capability progress, you have drifted.
- *"its more important to try to make it pass all the benchmark tests first"* — cycle 2 ships toward benchmark-PASS lift. The math ladder PASS count is the diagnostic. If `D5 bench-replay` doesn't show maths lift (3/0 → 4+/0 by lifting rubric-pending entries to green), cycle 2 didn't ship capability.
- *"unless its super-human in every domain ... YOU ARE NOT DONE WORKING ON PROJECT-X"* — Terminus is FAR. Don't claim done after cycle 2.
- *"i expect you to have a REALLY good reason to use me as blocker"* (lain 2026-05-10 mid-cycle-1) — defensible-default decisions don't need lain confirmation. Heartbeat #5b applies. Strategic-framing questions go in this file for next-cycle pickup.

## Done condition (cycle 2, mechanical)

- All 6 #00P13c2-XX TaskList rows = `completed`
- pytest -q ≥ 153 (cycle 1 baseline; expect ≥ 170-180 with new tests for symbolic substrate + verifier)
- New dirs (`src/project_x/reasoning/`, possibly `gpt-codex/grade_pipeline/baseline_<cycle2-date>/`) each have a REPO_CONTROL row in the same commit
- D3 harness reports maths PASS lifts above 3/0 (target: ≥ 4 PASS — at least one previously rubric-pending entry now green via substrate-driven re-attempt) OR explicit honest report if substrate isn't yet at that bar
- Memory ladder still 5/0; physics still 3/0. ZERO regressions.
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-2.md`
- THIS file rewritten as cycle 3 handoff
- `git status -s` empty
- Discord cycle 2 close post sent (headline = math benchmark lift OR honest "didn't yet meet bar" report)
- Cycle 3 picked up immediately

— Update this file at cycle 2 close: replace cycle 2 deliverables table with cycle 3 deliverables table; refine cycle 3 scope based on cycle 2 lessons; preserve the lain-quote + standing-rules + anti-laziness sections.
