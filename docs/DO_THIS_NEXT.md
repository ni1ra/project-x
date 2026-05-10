# Do This Next — Project X — Phase 13 cycle 5 (predicate-strength fix + Newton-verifier tests + surrogate-author independence + per-criterion floor gates + substrate Tier 3 OR pivot)

**Updated:** 2026-05-10 (cycle 5 handoff; cycle 4 closed at THIS commit)
**Mode:** NORMAL (not godify-app)
**Status:** Cycle 4 CLOSED — 7/7 #00P13c4 shipped (5 Tier B + 2 Tier A; Tier A added mid-cycle via lain's anti-cheat directive) + 2 universal /docs exemption commits + 1 mid-flight handoff sync (9 atomic commits this cycle). pytest 256 passing. D3 harness 15 PASS / 0 FAIL. Anti-cheat mechanism operationalized; physics PASS 3/0 → 5/0; substrate physics 3 primitives shipped anti-cheat-aware; substrate-driven capability touchpoint with measured `memorization_signal == 0.0` across N=5 surrogates per primitive.

## Cycle 4 shipped (full ledger)

| Commit | Deliverable | Visible result |
|---|---|---|
| `c953180` | **#00P13c4-01** Path B physics grader-flip | physics PASS 3/0 → 5/0 (rank 4-5 rubric-graded-builder; 4.33/5 + 4.75/5 differentiated lift) |
| `e30b9df` | **#00P13c4-23** anti-cheat-leakage-audit (TIER A) | `docs/artifacts/PHASE_13_ANTICHEAT_AUDIT.md` (318 lines; 7 surfaces mapped; 6 mitigation candidates) |
| `69c6b65` | **#00P13c4-24** anti-cheat mechanism (TIER A) | `src/project_x/anti_cheat.py` + 20 tests; AntiCheatProbe + differential_capability_test + Newton's-method divergent verifier; closes Surfaces 1+2+5 |
| `71fced1` | **#00P13c4-02** substrate physics Tier 2 | `src/project_x/reasoning/physics.py` + 15 tests; 3 primitives anti-cheat-aware (free_fall_time + pendulum_period + relativistic_momentum) |
| `e1ddbf6` | docs(REPO_CONTROL) `/docs` exemption | lain mid-cycle-4 follow-up codified |
| `5891da3` | docs(MANIFESTO) `/docs` exemption alignment | contradiction-delete pass |
| `5c6e6d6` | docs(DO_THIS_NEXT) -ni handoff sync | mid-flight Plan→Execute Raphael handoff |
| `6ce457d` | **#00P13c4-03** substrate-driven attempt | `gpt-codex/grade_pipeline/baseline_2026-05-10_physics_tier2/` (4 artifacts) — `memorization_signal == 0.0` verified across N=5 surrogates per primitive; capability TOUCHPOINT |
| THIS commit | **#00P13c4-05** cycle reflect + cycle 5 handoff | dev-cycle-4.md + this rewrite + A_TO_Z changelog |

Three visible axes this cycle:
- **physics PASS: 3/0 → 5/0** (cycle 4 #01 Path B; SECOND Phase-13 PASS-count lift)
- **substrate physics quality:** 0 → 3 primitives anti-cheat-aware
- **anti-cheat surface:** ungrounded → mechanism shipped + capability touchpoint with measured `mem_sig == 0.0`

## Phase 13 cycle 5 corpse-provisional deliverables

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c5-01-predicate-strength-fix** | HIGH | `src/project_x/anti_cheat.py` (or `tests/test_reasoning_physics.py` predicate module) + cycle 4 baseline_physics_tier2 re-run | Replace physics-003's `_relativistic_momentum_predicate` with energy-momentum-relation predicate `E² = (pc)² + (mc²)²` for genuine independence (advisor catch 2026-05-10). Re-run anti-cheat probe; confirm `memorization_signal == 0.0` still holds. Update bias_notes + improvement_directions in baseline_physics_tier2/. |
| **#00P13c5-02-newton-verifier-tests** | MED | `tests/test_reasoning_verifier.py` (extension) | Cycle 4 #24 acknowledged-gap closure: dedicated tests for `verify_quadratic_via_newton`. Newton's-method convergence + Vieta deflation + sentinel handling + non-convergent canonical termination. |
| **#00P13c5-03-surrogate-author-independence** | HIGH | `src/project_x/anti_cheat.py` + new probe set | Introduce lain-authored or textbook-derived surrogates for at least one primitive. `AntiCheatProbe.surrogate_author = "lain"` or `"textbook:<ref>"` taxonomy. Materially strengthens anti-cheat verdict. Audit Candidate C operationalization. |
| **#00P13c5-04-per-criterion-floor-gates** | MED | `gpt-codex/benchmark/run_audit.py` + rubric.md surfaces | Audit Candidate B operationalization: programmatic per-dimension floor gates (aggregate ≥ 4.0 AND each dimension ≥ floor). Closes Surface 3 partial — programmatic half. |
| **#00P13c5-05-substrate-tier3 OR pivot** | DEPENDENT | TBD per lain direction at cycle 5 open | Substrate Tier 3 (vector calculus / large-angle pendulum / air-resistance free-fall) OR pivot to next capability domain (memory million-turn? always-on chat daemon?). |
| **#00P13c5-06-bench-replay** | MED | `python3 gpt-codex/benchmark/run_audit.py` | Verify 15 PASS / 0 FAIL maintained. |
| **#00P13c5-07-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-5.md` + DO_THIS_NEXT cycle 6 handoff + A_TO_Z changelog | advisor() pre-commit. Discord cycle 5 close. Propose -ni at cycle 6 boundary. |

## Recommended cycle 5 order (rationale per dependency)

1. **#01 predicate-strength fix** FIRST — advisor catch from cycle 4; quick win that materially strengthens cycle 4's deliverable. Confirms cycle 4 anti-cheat verdict holds with stronger predicate. No new substrate; reuses cycle 4 #02 + #24.
2. **#02 Newton-verifier tests** SECOND — closes cycle 4 acknowledged-gap; isolated test work; no new code paths beyond extending `test_reasoning_verifier.py`.
3. **#03 surrogate-author independence** THIRD — needs lain ack on textbook source or hand-authored surrogate set. Discord-propose pattern fits: "proposing 5 textbook problems from <Halliday/Marion/Griffiths> as surrogate set; ack to proceed."
4. **#04 per-criterion floor gates** FOURTH — depends on rubric.md per-domain inspection; isolated audit + programmatic check; can layer alongside #01-#03.
5. **#05 substrate Tier 3 OR pivot** — lain-direction-dependent. If substrate Tier 3: vector-calculus primitives bridge to E&M / GR scope. If pivot: memory or always-on chat or unsolved-tier physics.
6. **#06 bench-replay** + **#07 cycle reflect** at cycle close.

## #1 predicate-strength fix — exact next-action (~30-45 min, 6 mechanical steps)

1. **Define `_relativistic_momentum_e_p_predicate`** — operates on substrate output `p` and inputs `(m, v, c)`. Independent identity: `E_total = γ·m·c²`, `(p·c)² + (m·c²)² = E_total²`. Substrate's `γ·m·v` doesn't directly yield `E`, so verifying via independently-computed γ closes the asymmetry. Place in shared module or test module.
2. **Update cycle 4 baseline_physics_tier2 generation** — re-author or directly edit grades.jsonl + probe_results.json to use new predicate. (Or write a `cycle5_repredicate.py` script that re-runs probes with new predicate and patches the artifacts.)
3. **Verify `memorization_signal == 0.0` still holds** under the stronger predicate (it should — substrate genuinely computes; only the predicate's ability to discriminate library-import improves).
4. **Update bias_notes** in physics-003 grade entry: replace asymmetry-addendum with verified-independence note. Update `improvement_directions.md` cross-prompt asymmetry table to mark physics-003 STRONG.
5. **REPO_CONTROL row update** — note in physics_tier2 row that asymmetry was closed cycle 5.
6. **Atomic commit:** `feat(P13c5-01): predicate-strength fix — physics-003 E² = (pc)² + (mc²)² predicate (verified-independence; cycle 4 advisor catch closed) — closes #00P13c5-01`. Push. TaskUpdate. Discord one-liner.

## Identity disambiguation (CRITICAL — lain 2026-05-10 binding)

Claude Code Raphael (the BUILDER, this Claude Code instance) ≠ Project X Raphael (the AGENT, in `src/project_x/`). Don't write builder's voice into agent's templates. Cycle 5 #1 predicate-strength fix is BUILDER work (test/verification surface); cycle 5 #5 substrate Tier 3 (if chosen) is BUILDER work that the AGENT consumes at inference. See `docs/MANIFESTO.md` § Identity discipline.

## Standing rules — RELEVANT THIS RUN

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal).

**Codified universal during cycle 4 (binding for cycle 5+):**
- **Anti-cheat discipline (cycle 4 #24 binding):** substrate-driven capability touchpoints MUST record `memorization_signal` alongside grade. Honest framing: "memorization_signal == 0.0 verified across N surrogates" — or honest gap report.
- **`/docs` REPO_CONTROL exemption** (commits `e1ddbf6` + `5891da3`; universal `~/.claude/CLAUDE.md` § REPO_CONTROL upkeep also updated). New `docs/` files do NOT need REPO_CONTROL row co-landing. Only `src/` + `tests/` + `gpt-codex/` + `scripts/` + `ref/` + `sandbox/` + repo-root files need rows.
- **Predicate-strength discipline (cycle 4 advisor catch):** anti-cheat predicates SHOULD use independent identities (different from substrate's computation), not re-derivations. Asymmetry must be documented when present + closed where possible.

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
- NOT extending substrate to GR / quantum-gravity (out of cycle 5 scope; substrate Tier 3 candidate is conservative — vector calculus / large-angle / air-resistance).
- NOT closing without re-verifying `memorization_signal == 0.0` post-predicate-fix on cycle 4 baseline_physics_tier2 (M-PROJECTX-013 measure-don't-claim — the cycle 4 verdict must hold under the strengthened predicate).

## Anti-laziness gates (lain frustration-load-bearing — re-read before cycle close)

- *"all you have done so far is just minor work"* — cycle 4 shipped **anti-cheat mechanism operationalization** + physics PASS lift + 3 substrate primitives + capability touchpoint with measurable `mem_sig == 0.0`. Cycle 5 closes the predicate-strength asymmetry advisor caught + cycle-5+ deferred items.
- *"its more important to try to make it pass all the benchmark tests first"* — cycle 4 already lifted physics PASS 3→5; cycle 5 #04 per-criterion floor gates + #03 surrogate-author independence harden the PASS judgments under stronger anti-cheat.
- *"unless its super-human in every domain ... YOU ARE NOT DONE WORKING ON PROJECT-X"* — Terminus is FAR. Cycle 5 is one step.
- *"honest and honorable work ethics. If all tests pass, but the model falls apart in real tests, or it sees the answer in advance in some hidden way, the test passes are meaningless"* — cycle 5 #01 predicate-strength fix + #03 surrogate-author independence harden the operationalization.

## Done condition (cycle 5, mechanical)

- All 7 #00P13c5-XX TaskList rows = `completed`.
- pytest -q ≥ 256 (no regression; expect ≥ 270 with new tests for #02 Newton verifier).
- D3 harness reports 15 PASS / 0 FAIL maintained (no expected change from cycle 5 work).
- Maths PASS 5/0; memory 5/0; physics 5/0. ZERO regressions.
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-5.md`.
- THIS file rewritten as cycle 6 handoff.
- `git status -s` empty.
- Discord cycle 5 close post sent.
- Cycle 6 picked up immediately OR `-ni` proposal at cycle 5 close.

— Update this file at cycle 5 close: replace cycle 5 deliverables table with cycle 6 deliverables table; refine cycle 6 scope based on cycle 5 lessons; preserve the lain-quote + standing-rules + anti-laziness sections.
