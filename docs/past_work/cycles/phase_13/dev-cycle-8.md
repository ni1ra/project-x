# Phase 13 — Cycle 8 reflection

**Theme:** Substrate-extension blitz closing the six cycle-7 agent-runtime FAIL gaps (4 maths + 2 physics) + lain mid-cycle directive — programmatic-unsolved-theorems pack at the unsolved-conjecture frontier (Collatz / Goldbach / twin primes / Mertens, honestly framed per M-PROJECTX-013) + parser-robustness 3-pattern fortification + bench-replay harness tolerance bug surfaced & fixed.
**Closed:** 2026-05-11
**Cycle horizon:** ~3 hours across two Claude Code instances (single `/clear`+paste handoff at mid-cycle via `/forge-prompt -ni`). 8 atomic commits + 1 handoff doc-sync.

## Deliverables ledger (per docs/DO_THIS_NEXT.md cycle 8 table)

| ID | Status | Commit |
|---|---|---|
| #00P13c8-01 residue-theorem substrate | DONE (pre-handoff) | `e310301` |
| #00P13c8-02 definite-integral substrate | DONE (pre-handoff) | `e6accba` |
| #00P13c8-03 ODE substrate | DONE (post-handoff) | `e1e309c` |
| #00P13c8-04 3x3 determinant | DONE | `3dd9550` |
| #00P13c8-05 physics extensions (projectile + Doppler) | DONE | `36f8afc` |
| #00P13c8-06 parser robustness | DONE | `147fbe0` |
| #00P13c8-07 CLAUDE.md trim | DEFERRED (lain-pending; awaits direction on what's load-bearing in older sections) | — |
| #00P13c8-08 bench-replay | DONE — surfaced + fixed harness tolerance bug | `afa40b7` |
| #00P13c8-09 cycle reflect | DONE (THIS commit) | — |
| #00P13c8-10 programmatic-unsolved-theorems | DONE (lain HIGH directive 2026-05-11) | `2207fdb` |

## What shipped (atomic per-deliverable commits)

### #03 — first-order linear ODE substrate (`e1e309c`)

`src/project_x/reasoning/ode.py` (NEW; 110 lines). Closed-form `first_order_linear_ode_exp_solution(k, y_0, x_target, x_0=0.0)` returning Lemma; y(x) = y_0·e^(k·(x-x_0)). 4-step Lemma chain mirroring cycle 8 #01/#02. Closes maths-011 agent-runtime gap.

Advisor catches (2026-05-11) absorbed pre-Write: `x_0=0.0` default param for future generalization; negative-y_0 test (sign-flip bug class); phantom "BEFORE quadratic" ordering constraint from corpse dropped (`dy/dx` and `x²=0` keywords don't overlap); verifier.py-ODE-deferred noted in REPO_CONTROL row; cycle-9 predicate-strength-uniformity-pass pinned in #09 description.

12 substrate tests + 6 dispatcher tests. REPO_CONTROL gap-fix co-landed (cycle 8 #01/#02 test rows that didn't ship with their substrate commits).

### #04 — 3x3 determinant substrate (`3dd9550`)

`src/project_x/reasoning/symbolic.py` extension; `determinant_3x3(matrix)` via Laplace cofactor expansion along row 0. 2-step Lemma chain (build_minors → cofactor_expansion_row_0); tautological cofactor-formula invariant. Closes maths-012. 10 substrate tests + 5 dispatcher tests.

### #05 — physics extensions (`36f8afc`)

Two new primitives: `projectile_horizontal_range(h, v_horizontal, g)` (closes physics-007 — cliff-launched horizontal projectile) + `relativistic_doppler_shift(wavelength_emit, beta, approaching=True)` (closes physics-012 — radial Doppler with sign-branch on direction). Projectile universal invariant R²·g/(2h) = v_horizontal² (algebraic identity); verified anti-cheat via `differential_capability_test` across solar-system gravities (Earth/Moon/Mars/Jupiter; memorization_signal == 0.0). Doppler uses tautological factor² = ratio invariant.

`__init__.py` retroactively re-exports ALL physics primitives (free_fall_time / pendulum_period / large_angle_pendulum_period / relativistic_momentum / projectile_horizontal_range / relativistic_doppler_shift + 6 INTRO constants). Closes cycle 4/5 re-export gap with the same retrofit pattern cycle 8 #03 applied to complex_analysis + calculus. 14 substrate tests + 6 dispatcher tests.

### #10 — programmatic-unsolved-theorems pack (`2207fdb`, lain mid-cycle directive 2026-05-11)

`src/project_x/reasoning/number_theory.py` (NEW; 4 primitives at the unsolved-conjecture frontier). `collatz_verify_range(N)` / `goldbach_verify_range(N)` / `twin_primes_in_range(N)` / `mertens_bound_verify(N)`. Shared helpers `_sieve_of_eratosthenes` (classical O(n log log n)) + `_smallest_prime_factor_sieve` (for Möbius via factor-counting).

**HONEST FRAMING (M-PROJECTX-013 binding) EVERYWHERE.** Every Lemma's claim states "verified for [1, N]", NEVER "theorem proved". INTRO prose + step justification + invariant_check all repeat the constraint. Mertens INTRO explicitly notes the bound was DISPROVED at large N (Odlyzko + te Riele 1985, lim sup |M(n)|/√n > 1.06); the substrate is small-N regression-test surface, NOT a conjecture-proof claim.

4 new ladder entries at `gpt-codex/benchmark/maths/ladder.jsonl` (maths-017 Collatz / 018 Goldbach / 019 twin primes / 020 Mertens) at difficulty_rank 1 (intro — programmatic). `audit_status` reads "auto-graded-green; empirical verification only — NOT a theorem proof per M-PROJECTX-013". `auto_grade.expected` = count of verified items at N=1000 (1000 / 499 / 35 / 1000). 29 substrate tests + 5 dispatcher tests.

### #06 — parser robustness (`147fbe0`)

3-pattern fortification of `src/project_x/reasoning_agent.py`: `_HEIGHT_PATTERN` accepts "meters"/"metres" full-word suffix (was failing `m\b` boundary on rephrased prompts); `_LENGTH_PATTERN` accepts "length X m" / "length of X m" alongside the original "L = X m" form (resolves "swinging pendulum of length 1 m" routing); `_QUADRATIC_PATTERN` accepts unicode `x²` (U+00B2) + unicode minus `−` (U+2212) alongside ASCII forms (LaTeX-typography prompts now parse). `_parse_signed_coefficient` normalizes unicode minus to ASCII inline.

7 regression tests including backward-compat regression guard across all three patterns. Intentionally narrow scope: the other 10 dispatchers (residue / integral / determinant / 2x2 eigenvalue / relativistic momentum / projectile / Doppler / 4 number-theory) haven't been stress-tested; cycle 10+ extends as failure prompts surface.

### #08 — bench-replay harness tolerance fix (`afa40b7`)

Surfaced during cycle-8 close bench-replay (the verification step IS the discovery): `_close_enough` used strict-`<` semantics → exact match at `tolerance=0` false-FAIL'd. Hit on the 4 cycle-8 #10 count-based entries (agent computed 1000, expected 1000, but `abs(0) < 0` = False). One-character fix: `<` → `<=` (closed-ball tolerance) on both branches of `_close_enough`. Off-by-one still fails (|1-0|=1 > 0); only exact match newly passes.

Audited: only the 4 cycle-8 #10 entries use `tolerance=0`. No existing entry depends on strict-< semantics for failure. All existing entries have `abs(diff)` STRICTLY less than tolerance (not equal), continue to PASS under `<=` unchanged.

## Headline metrics (HONEST DECOMPOSITION per advisor 2026-05-11 anti-conflation catch)

```
pytest -q:                       310 (cycle 7 close) → 429 (cycle 8 close)   [+119 tests]
bench-replay --agent-runtime:    31/6 → 41/0    [all FAILs cleared]
bench-replay frozen:             37/0 → 41/0    [+4 entries; both modes parity]
```

**Capability lift — split into two distinct axes:**

```
AXIS A — CYCLE-7 FAIL GAPS CLOSED on the original set (unconfounded across cycles):
  Cycle-7 baseline failing entries: 6
    - maths: residue (003) + integral (010) + ODE (011) + 3x3 det (012)
    - physics: projectile (007) + Doppler (012)
  Cycle-8 closed: 6 of 6 = 100%
  This is the pure capability lift — comparable across cycles, denominator fixed.

AXIS B — NEW BENCHMARK ENTRIES SHIPPED (denominator expansion):
  +4 new entries (maths-017 / 018 / 019 / 020)
  All 4 substrate-solved-BY-CONSTRUCTION (we wrote the substrate AND the auto_grade.actual).
  Honest framing in audit_status + raphael_response + Lemma renders: empirical
  verification over [1, N=1000] only, NEVER theorem proof. M-PROJECTX-013 binding.
  Capability touchpoint at unsolved frontier — NOT a research contribution.

COMBINED METRIC (read with caveats above):
  Substrate-solved at agent-runtime, post-cycle-8: 22 of 26 = 85%
    - 12 cycle-7-baseline substrate-solved (carried forward)
    - +10 cycle-8 substrate-extensions (6 closing FAIL gaps + 4 new entries)
    - 4 of 26 remaining are rubric-pending (need rubric-grade, not substrate-solve)
  The 85% partly reflects denominator expansion. Don't read as pure capability gain
  without the decomposition above.
```

## Architectural tensions surfaced

### Tension 1 — Predicate-strength uniformity gap (cycle 9 #1 priority per advisor)

Cycle 8 #01/#02/#03/#04 + #10 ship **tautological algebraic-identity invariants** (e.g., `factor² = ratio` for Doppler; `y(x_0) = y_0` IC preservation for ODE; `det = a·(ei-fh) - b·(di-fg) + c·(dh-eg)` inlined-vs-chained for determinant). These verify formula consistency within the closed-form path — they do not cross-check via independent computation.

Physics substrate (cycle 4 #00P13c4-02 + cycle 5 #00P13c5-01) ships **STRONG (algorithmically-independent) invariants**: free-fall's `v_f = √(2gh)` energy-conservation cross-check; pendulum's `T²·g/L = 4π²` dimensionless universal; relativistic_momentum's energy-momentum-relation route (cycle 5 #01 fix on asymmetry); large-angle pendulum's ratio-recursion form independent of explicit-coefficient sum.

This makes cycle 8's maths substrate consistency-checked but not capability-checked. Cycle 9 #1 priority: **predicate-strength uniformity pass** — retrofit independent-path verifiers across `reasoning/{symbolic,complex_analysis,calculus,ode,number_theory}` to match physics's STRONG-predicate standard. Per-primitive verifier candidates documented in DO_THIS_NEXT cycle 9 scope.

### Tension 2 — Capability-touchpoint-at-unsolved-frontier requires honest framing

#10's 4 primitives forced M-PROJECTX-013 binding to its hardest case: prompts about OPEN conjectures (Collatz, Goldbach, twin primes) or DISPROVED ones (Mertens). The substrate explicitly cannot prove anything; it verifies empirically over a finite range only.

Solution shipped in #10: every Lemma's claim states "verified for [1, N]", NEVER "theorem proved". INTRO prose + step justification + invariant_check all repeat the constraint. Mertens INTRO explicitly says "DISPROVED at large N". A grader/reader cannot mistake the verification result for a proof.

Cycle 10+ implication: as more capability-touchpoint entries land at the unsolved frontier (Riemann zeta zero verification, Erdős conjectures, etc.), the same framing pattern applies. The "PASS = empirical verification over [1, N], NEVER proof" formulation is the durable contract.

### Tension 3 — Parser robustness is incremental, not comprehensive

#06 fortified 3 dispatchers (free_fall + pendulum + quadratic) against specific rephrasings. The other 10 dispatchers (residue / integral / ODE / determinant / 2x2 eigenvalue / relativistic momentum / projectile / Doppler / 4 number-theory) haven't been stress-tested against rephrased prompts.

Cycle 10+ scope: comprehensive parser-robustness audit. Pattern is established (alternation in regex + regression test); execution is mechanical. Trigger: failure prompts in the wild OR a scheduled cycle pass.

### Tension 4 — Bench-replay harness has alignment debt with substrate evolution

#08 surfaced a tolerance-comparison semantic bug (strict-< failed exact-match at `tolerance=0`) only because cycle-8 #10 introduced count-based entries with that tolerance shape. The bug existed since cycle 7 #00P13c7-NEW (when `_close_enough` was authored) but was invisible until a tolerance-0 entry shipped.

Lesson: running the bench-replay at cycle close (#08 verification step) reveals alignment bugs the test suite cannot — `test_benchmark_harness.py` tests the harness against existing entries, not against new boundary cases.

Cycle 10+ scope: bench-replay-driven harness audit. Add boundary-case test cases to `test_benchmark_harness.py` (tolerance=0, tolerance > expected magnitude, relative-vs-absolute boundary). Plus consider whether the audit should distinguish "substrate raised exception" from "substrate returned wrong answer" as separate signals.

## Lain catches absorbed (4)

1. **TaskList trim discipline** (lain 2026-05-10 — *"trim better"*). Session-start: rebuilt TaskList to 11 lean rows (2 eternals + 8 cycle-8 actives + 1 carry-forward); split #03 only into 4 sub-tasks for visible momentum; split-on-demand discipline for #04/#05/#10 (kept TaskList lean while preserving momentum-visibility on the active room).
2. **Per-section skill variety** (lain 2026-05-10 standing order). Pillar pick at session start (`/run-loop` ATOMIC + per-section advisor / smart-commit / hand-off). Advisor consulted pre-Write at #03 design + cycle-reflect; skipped at #04/#05/#10 since pattern-mirror to #03.
3. **Listener accumulation pattern** (M-NAVI-021 logged this cycle). `pkill -f 'discord-wait-for-lain'` matches its own wrapper shell's argv when bundled with the launch command — the wrapper dies with SIGURG before reaching the bash invocation. New two-call pattern: separate Bash for kill; separate bg Bash with `exec bash discord-wait-for-lain.sh` to replace wrapper shell directly. MANIFESTO § Discord listener manual re-arm needs update at next universal-prompt trim.
4. **Mid-cycle directive — programmatic-unsolved-theorems pack** (lain Discord 2026-05-11). Absorbed as #00P13c8-10 immediately when surfaced; ladder entries + substrate + dispatchers + tests + REPO_CONTROL row + atomic commit all shipped same session. Honest M-PROJECTX-013 framing applied throughout.

## Cycle 9 scope (provisional; refined per cycle 8 lessons)

**Priority 1 (HIGH — advisor pinned 2026-05-11):** Predicate-strength uniformity pass. Retrofit independent-path verifiers across `reasoning/` primitives to match physics's STRONG-predicate standard. Capability-debt > grading-debt; pay the structural before the cosmetic.

Per-primitive verifier candidates:
- `symbolic.py` (quadratic, 2x2 eigenvalue, 3x3 determinant): Newton-method (cycle 4 #00P13c4-24 precedent extended) + Vieta cross-check + Sarrus rule
- `complex_analysis.py` (residue): numerical-integration (Simpson's rule on `[-100, 100]`) — algorithmically distinct from closed-form residue
- `calculus.py` (polynomial integral): Riemann sum / midpoint rule — algorithmically distinct from FTC
- `ode.py` (first-order linear): Taylor series for e^(kx) (manual factorial + power; truncated at N=10) — algorithmically distinct from math.exp
- `number_theory.py`: empirical-verification primitives are already independent-path by construction (iteration / sieve vs nothing else to compare against); document this in cycle 9 reflection rather than retrofit

**Priority 2 (lower — defer if Priority 1 takes the cycle):** Path B grader-flip on ~17 rubric-pending entries (poetry, philosophy, persona, conceptual physics, hard math). Cycles 6+7+8 deferred this; cycle 9 should execute IF time remains after predicate-strength uniformity.

**Carry-forwards (lain-pending; surface on Discord if needed):**
- CLAUDE.md trim resolution (62k current vs 41-47k hard range; awaits lain direction on what's load-bearing in older sections)
- Council audit tag mechanism (lain proposed 2026-05-10; awaits scope direction)

## Done condition (cycle 9, mechanical)

- All 6 #00P13c9-XX TaskList rows = `completed` (or explicitly deferred with rationale)
- pytest -q ≥ 460 (current 429; predicate-strength pass expected +30+ tests)
- bench-replay `--agent-runtime`: 41/0 maintained (no regressions; verifier additions are check-only)
- bench-replay frozen: 41/0 maintained
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-9.md`
- `docs/DO_THIS_NEXT.md` rewritten as cycle 10 handoff
- `git status -s` empty
- Discord cycle 9 close in 4-metric rubric
- Cycle 10 picked up immediately

— Cycle 8 reflection landed THIS commit.
