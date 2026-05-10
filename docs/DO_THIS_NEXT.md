# Do This Next — Project X — Phase 13 cycle 9 (PREDICATE-STRENGTH UNIFORMITY PASS — retrofit independent-path verifiers across `reasoning/` primitives to match physics's STRONG-predicate standard; advisor cycle-8 #03a pinned)

**Updated:** 2026-05-11 (cycle 8 closed at THIS commit; cycle 9 handoff)
**Mode:** NORMAL (not godify-app)
**Status:** Cycle 8 CLOSED at THIS commit. Cycle 9 STARTING.

**Cycle 8 closing metrics:** pytest 429 (was 310; +119 cycle 8 tests). Bench-replay `--agent-runtime` 41/0 + frozen 41/0 (both modes parity). All 6 cycle-7-baseline FAIL gaps closed (4 maths + 2 physics; pure capability lift on the original set = 100%). +4 new entries shipped at unsolved-conjecture frontier (maths-017..020; honest M-PROJECTX-013 framing). Substrate-solved at agent-runtime: 22 of 26 = 85% (decomposed: 12 cycle-7-carry + 10 cycle-8-shipped; 4 rubric-pending remaining).

## Cycle 8 shipped (8 commits + handoff doc-sync)

| Commit | Deliverable | Result |
|---|---|---|
| `4f8d182` | doc-sync pre-`-ni`-handoff (cycle 7 close) | Cycle 8 #01+#02 ledger landed + lain mid-cycle #10 directive captured |
| `e310301` | #01 residue-theorem substrate | maths-003 agent-runtime closed |
| `e6accba` | #02 definite-integral substrate | maths-010 closed |
| `e1e309c` | #03 ODE substrate | maths-011 closed |
| `3dd9550` | #04 3x3 determinant substrate | maths-012 closed |
| `36f8afc` | #05 physics extensions (projectile + Doppler) | physics-007 + physics-012 closed |
| `2207fdb` | #10 programmatic-unsolved-theorems pack | +4 ladder entries (maths-017..020); lain mid-cycle directive 2026-05-11 |
| `147fbe0` | #06 parser robustness extensions | rephrased prompts route correctly (meters/metres + length-of phrasing + unicode minus + x²) |
| `afa40b7` | #08 bench-replay harness tolerance fix | 41/0 agent-runtime + frozen parity |
| THIS commit | #09 cycle reflect | dev-cycle-8.md + this rewrite + A_TO_Z changelog |

**Cycle 8 carry-forwards (still lain-pending; surface on Discord if needed):**
- #07 CLAUDE.md trim resolution: 62k current; lain's 41-47k hard range needs 15k+ more from older sections (RAPHAEL OPERATING MODES / SIX VOWS / UNIVERSAL vs PROJECT-SPECIFIC / PHASE 0); awaits lain direction on what's load-bearing
- #11 (cycle 7 #04) council audit tag: awaits lain direction on mechanism shape

## Phase 13 cycle 9 deliverables (predicate-strength uniformity pass + bench-replay + reflect)

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c9-01-symbolic-strong-predicate** | HIGH | `src/project_x/reasoning/symbolic.py` + `src/project_x/reasoning/verifier.py` extensions + tests | Newton-method divergent verifier for quadratic (cycle 4 #00P13c4-24 precedent extended) + Vieta cross-check for 2x2 eigenvalues + Sarrus rule for 3x3 determinant. Each algorithmically-independent of the primary closed-form. Wire into `verifier.py` supported-operation set. |
| **#00P13c9-02-complex_analysis-strong-predicate** | HIGH | `src/project_x/reasoning/complex_analysis.py` extension + tests | Numerical-integration cross-check on a finite interval for residue-theorem real-line integral (Simpson's rule on `[-R, R]` for R = 100 or similar); algorithmically distinct from closed-form residue computation. Verify convergence to π/√(a·c) as R grows. |
| **#00P13c9-03-calculus-strong-predicate** | HIGH | `src/project_x/reasoning/calculus.py` extension + tests | Riemann sum / midpoint rule cross-check for polynomial definite integral; algorithmically distinct from FTC closed-form. Tolerance scales with N (number of subintervals). |
| **#00P13c9-04-ode-strong-predicate** | HIGH | `src/project_x/reasoning/ode.py` extension + tests | Taylor series expansion `e^(k·x) = Σ_{n=0}^{N} (k·x)^n / n!` truncated at N=20; manual factorial + power; algorithmically distinct from math.exp. Tolerance scales with truncation error bound. |
| **#00P13c9-05-bench-replay** | MED | `python3 gpt-codex/benchmark/run_audit.py --agent-runtime` | Target: 41/0 maintained on `--agent-runtime` (no regressions from verifier additions; verifiers are check-only); +30+ tests on predicate-strength uniformity invariants. |
| **#00P13c9-06-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-9.md` + DO_THIS_NEXT cycle-10 handoff + A_TO_Z changelog | advisor() pre-commit. Discord cycle-9 close in 4-metric rubric. |

## Recommended cycle 9 order

1. **#01 symbolic primitives** — verifier.py already has Newton-method scaffolding from cycle 4 #00P13c4-24; extension to 2x2 eigenvalue Vieta + 3x3 Sarrus is mechanical. Most heavily-used substrate; highest-value retrofit.
2. **#02 complex_analysis** — residue substrate is small (one primitive); Simpson's rule fits in ~40 lines. Watch convergence (residue formula is exact; numerical converges as 1/R²).
3. **#03 calculus** — polynomial integral substrate is mechanical; Riemann sum mirrors structure of antiderivative computation but iterates over subintervals.
4. **#04 ode** — Taylor series is conceptually simple but care needed on truncation tolerance (factorial growth is fast; ~20 terms suffice for |k·x| < 5).
5. **#05 bench-replay** — verify no regressions (verifiers don't change the AGENT's primary path).
6. **#06 cycle reflect** — close cycle 9 + DO_THIS_NEXT rewrite for cycle 10.

## #1 priority — exact next-action

1. Re-read `src/project_x/reasoning/verifier.py` lines 50-150 to refresh memory of cycle 4 #00P13c4-24 `_quadratic_newton_verification_script` + `verify_quadratic_via_newton` pattern (sandbox-bound divergent verifier).
2. Design Vieta-based 2x2 eigenvalue cross-check: given matrix `[[a,b],[c,d]]` with computed eigenvalues `[λ₁, λ₂]`, verify `λ₁ + λ₂ ≈ tr(A) = a + d` AND `λ₁·λ₂ ≈ det(A) = a·d - b·c`. Algebraically independent of `solve_quadratic`'s discriminant-formula path through the characteristic polynomial. Already implemented in `expand_characteristic_polynomial_2x2`'s invariant_checks (cycle 3 #02 added Vieta invariants); cycle 9 #01 lifts this to a STANDALONE verifier callable from verifier.py.
3. Design Sarrus-rule 3x3 determinant cross-check: `det = aei + bfg + cdh - ceg - bdi - afh` (direct sum-of-permutations formula). Algebraically distinct from cofactor expansion's three-minor sum (different operations, different intermediate values).
4. Build `verify_*_via_*` functions in `verifier.py` + integrate into `_close_enough` supported-operation mapping.
5. Tests verifying each primitive's primary path + secondary verifier AGREE on canonical inputs (and disagree on hardcoded-counterexample inputs — anti-cheat regression).
6. Atomic commit `feat(P13c9-01)` + REPO_CONTROL row + push.

## Identity disambiguation (CRITICAL — lain 2026-05-10 binding)

Claude Code Raphael (BUILDER, this Claude Code instance) ≠ Project X Raphael (AGENT, in `src/project_x/`). Cycle 9 BUILDER work: extend `verifier.py` substrate (independent computation paths) and audit the primary closed-form path. AGENT consumes the new verifiers at runtime (via bench-replay `--agent-runtime` which calls substrate primitives + their verifiers).

## Standing rules — RELEVANT THIS RUN

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal).

**Codified universal during cycle 8 (lain mid-cycle absorbed; binding cycle 9+):**
- Parser-robustness pattern (lain 2026-05-11 indirectly via #06): alternation in regex + regression test per rephrasing; apply to remaining 10 dispatchers as failure prompts surface
- Bench-replay tolerance semantics (cycle 8 #08): `<=` (closed-ball); exact-match at `tolerance=0` PASSes
- M-PROJECTX-013 honest framing for capability-touchpoint entries (cycle 8 #10 binding): "PASS = empirical verification over [1, N], NEVER theorem proved" — INTRO + step + invariant_check all carry the constraint explicitly
- TaskList trim + split-on-demand discipline (lain 2026-05-11 internalized): split only the immediate-next room into sub-tasks; keep future-room rows lean

**Persistent (unchanged):**
- NO pretrained transformer derivatives at any layer (binding to AGENT inference; regex parsers only)
- Comment-ratio rule (WHY-comments + pure-signal explanations + complex code justified)
- Atomic per-deliverable commits; never `git add -A`
- REPO_CONTROL row co-landing in SAME commit as new files (docs/ exempt per lain 2026-05-10 standing exemption)
- M-PROJECTX-013 measure-don't-claim; M-PROJECTX-014 split-grading firewall

## What this cycle is NOT

- NOT shipping Path B grader-flip (deferred per advisor cycle-8 verdict: capability-debt > grading-debt; predicate-strength uniformity wins the slot)
- NOT a comprehensive parser-robustness audit (cycle 8 #06 fortified 3 dispatchers; the other 10 are cycle 10+ scope unless failure prompts surface)
- NOT extending to n×n determinant (3×3 sufficient for current ladder; cycle 10+ if needed)
- NOT touching lain-pending items (#07 CLAUDE.md trim, #11 council audit tag) without lain direction — surface on Discord if cycle 9 close approaches without lain input

## Anti-laziness gates

- *"honest and honorable work ethics"* — cycle 9 ships REAL capability rigor (independent-path verifiers; algorithmically-distinct cross-checks), not cosmetic PASS-count progress.
- *"make the agent actually solve the problems"* — cycle 9's verifiers don't change the AGENT's surface (the dispatchers still call the primary path); they audit the primary path for correctness. This is structural rigor, not capability bait-and-switch.
- *"unless its super-human in every domain ... YOU ARE NOT DONE"* — Terminus is FAR; cycle 9 is one more rung of substrate rigor before scaling.

## Done condition (cycle 9, mechanical)

- All 6 #00P13c9-XX TaskList rows = `completed` (or explicitly deferred with rationale)
- pytest -q ≥ 460 (current 429; expect +30+ tests across 4 primitives' verifiers)
- D3 harness `--agent-runtime`: 41/0 maintained (no regressions)
- Frozen mode: 41/0 maintained
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-9.md`
- THIS file rewritten as cycle 10 handoff
- `git status -s` empty
- Discord cycle 9 close in 4-metric rubric (denominator+% + Hassabis-tier impression + plain-English achievement + counter-claim guard)
- Cycle 10 picked up immediately

— Update this file at cycle 9 close: replace cycle 9 deliverables table with cycle 10 deliverables table; refine cycle 10 scope based on cycle 9 lessons.
