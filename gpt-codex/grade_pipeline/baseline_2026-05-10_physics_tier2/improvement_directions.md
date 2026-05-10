# Improvement Directions — physics_tier2 substrate-driven attempt baseline

> Cycle 4 #00P13c4-03 — substrate-driven physics-001/002/003 capability touchpoint, anti-cheat-verified (memorization_signal == 0.0 across N=5 surrogates per primitive, advisor-vetted 2026-05-10).
>
> **Honest framing.** This baseline is a **capability touchpoint**, not a claimed capability and not a ladder rubric flip. physics-001/002/003 are already auto-graded-green via numerical_close in `gpt-codex/benchmark/physics/ladder.jsonl`; this baseline documents *how* the cycle 4 #02 substrate (`src/project_x/reasoning/physics.py`) answers them under cycle 4 #24 anti-cheat verification (`src/project_x/anti_cheat.py`). No ladder.jsonl entries are flipped.

---

## Per-prompt directions

### physics-001 (free_fall_time, intro)

**Current state.** Substrate `free_fall_time(80, 9.81)` returns `t = 4.038550218769218 s` against ladder expected `4.04` (relative error `3.6e-4`, far inside tolerance `0.05`). Anti-cheat probe verified across 5 surrogates (Earth/Moon/Mars/Jupiter gravities + varied heights), `memorization_signal == 0.0`. Predicate is independent (reconstructs `h = ½·g·t²` from output, compares to input — different identity than substrate's `t = √(2h/g)`).

**Cycle 5+ paths to capability strengthening (not "to 5/5" — already passing):**

1. **Surrogate-author independence.** Current surrogates are builder-authored (rule-based parameter substitution). Cycle 5+ candidate: lain-authored / textbook-derived surrogate set (e.g., a problem from Marion & Thornton or Halliday & Resnick that the substrate has never seen as a parameter combo). Strengthens anti-cheat by closing surrogate-author bias.
2. **Air-resistance regime.** Current substrate is no-air-resistance only. Cycle 5+ extension: add `free_fall_with_drag(h, g, drag_coeff, mass)` returning a Lemma with the linear-drag terminal-velocity solution. Forces the substrate beyond pure-kinematic-identity into ODE territory.
3. **Energy-conservation invariant** is already the post-derivation check (verified). Could strengthen by adding momentum-impulse cross-check `m·v_f = ∫F dt = m·g·t` as a SECOND independent invariant.

### physics-002 (pendulum_period, easy)

**Current state.** Substrate `pendulum_period(1.0, 9.81)` returns `T = 2.0064092925890407 s` against ladder expected `2.007` (relative error `1.2e-4`). Anti-cheat probe verified across 5 surrogates (varying L + g across surface gravities), `memorization_signal == 0.0`. Predicate is independent (universal dimensionless `T²·g/L = 4π²` — substrate-independent identity).

**Cycle 5+ paths to capability strengthening:**

1. **Large-angle correction.** Substrate is small-angle linearization only. Cycle 5+ extension: add `pendulum_period_large_angle(L, g, theta_0)` using the elliptic-integral expansion `T = T_0 · (1 + (1/16)·sin²(θ₀/2) + (11/3072)·sin⁴(θ₀/2) + …)`. Forces the substrate beyond linear-ODE into perturbation theory.
2. **Damped pendulum.** Add `damped_pendulum_period(L, g, drag)` for the underdamped regime. Brings second-order ODE with non-conservative force into scope.
3. **Surrogate-author independence** (same as physics-001): textbook-derived surrogate set vs builder rule-based.

### physics-003 (relativistic_momentum, medium)

**Current state.** Substrate `relativistic_momentum(9.11e-31, 0.9·3e8, 3e8)` returns `p ≈ 5.6385e-22 kg·m/s` against ladder expected `5.64e-22` (relative error `~3e-4`). Anti-cheat probe verified across 5 surrogates (electron/proton mass scales × velocities 0.1c-0.99c), `memorization_signal == 0.0`.

**Predicate-strength asymmetry (advisor catch 2026-05-10).** Unlike physics-001/002, the predicate (`_relativistic_momentum_predicate`) re-computes `γ·m·v` and compares to substrate output — **same formula as substrate**. This still discriminates memorization-vs-computation (a hardcoded canonical fails on surrogate γmv values), but does NOT discriminate first-principles-derivation vs library-import. The library-import gap is closed at the file level by `test_physics_substrate_thesis_compliant` (source-grep for sympy/numpy/scipy/torch/transformers), but the predicate alone is weaker than physics-001/002.

**Cycle 5+ paths (priority on closing the predicate-strength asymmetry):**

1. **Replace predicate with energy-momentum relation.** Use `E² = (p·c)² + (m·c²)²` as the independent identity. Substrate's `p = γ·m·v` doesn't directly yield E; so verifying `(p·c)² + (m·c²)² ≈ (γ·m·c²)²` — using the substrate's `p` and an independently-computed `E = γ·m·c²` — closes the asymmetry. Or alternatively use `4-velocity invariant u_μu^μ = -c²` which encodes γ implicitly through the time-component but doesn't re-use γmv form.
2. **Add SR invariant decomposition** as a SECOND independent check: spacetime-interval `s² = (c·t)² - x²` invariance under boosts. Forces the substrate to engage with the geometry, not just the algebra.
3. **General-relativistic limit.** Cycle 5+ stretch: add `four_momentum_in_curved_spacetime` requiring metric-tensor input. Brings GR derivation into scope (currently flat-space-only).

---

## Architecture-level directions (cross-prompt)

### Surrogate-author independence (CYCLE 5+ PRIORITY)

The single biggest anti-cheat strengthening. Currently `AntiCheatProbe.surrogate_author == "builder (rule-based)"` documents the gap. Cycle 5+ candidates:

- **lain-authored surrogates.** lain provides 3-5 problems per primitive that the builder has never solved. Substrate runs them; predicate verifies. If `memorization_signal == 0.0` against a surrogate set the BUILDER never saw, the anti-cheat verdict is materially stronger.
- **Textbook-derived surrogates.** Pull from Halliday/Resnick/Marion-Thornton/Griffiths. Citation-traceable, lain-verifiable.
- **Adversarial surrogates.** Builder writes a "fake substrate" (hardcodes one canonical answer) and verifies the probe catches it via memorization_signal == 1.0. Already done for physics-001 (test_fake_overfit_free_fall_caught_by_probe). Cycle 5+: extend to physics-002/003 + maths primitives.

### Predicate-strength audit (CYCLE 5+ — NEW after advisor catch)

Per-primitive review of predicate independence. Mark each `STRONG` (independent identity) / `WEAK` (re-derives substrate formula). Replace WEAK predicates with STRONG ones where possible:

| Primitive | Current Predicate | Independence | Cycle 5+ Replacement |
|---|---|---|---|
| `free_fall_time` | `h = ½·g·t²` | STRONG (different identity) | — |
| `pendulum_period` | `T²·g/L = 4π²` | STRONG (universal invariant) | — |
| `relativistic_momentum` | re-computes γ·m·v | WEAK (same formula) | `E² = (p·c)² + (m·c²)²` |
| `solve_quadratic` | `a·r² + b·r + c ≈ 0` | STRONG (root-substitution) | — |
| `expand_characteristic_polynomial_2x2` | Vieta's `λ₁ + λ₂ = trace; λ₁·λ₂ = det` | STRONG (eigenvalue-of-matrix identity) | — |

Pattern: predicates that re-implement the substrate's computation are weaker; predicates that test a property the answer must satisfy (independent of how it was computed) are stronger.

### Per-criterion floor gates (CYCLE 5+ deferred from cycle 4)

Path B physics rubric grades use aggregate-only thresholds (4.0/5 weighted). A hypothetical uniformly-mediocre 4.01 still PASSES. Cycle 5+ when programmatic-rubric criteria (PHASE_13_ANTICHEAT_AUDIT.md Candidate B) ship: per-dimension floor gates (e.g., correctness ≥ 4.0 AND completeness ≥ 4.0 AND voice ≥ 4.0 individually).

### Substrate Tier 3 — extending the ladder

Cycle 4 #02 shipped 3 Tier 2 primitives (intro/easy/medium difficulty). Cycle 5+ Tier 3 candidates:

- **physics-004-equivalent:** `einstein_field_equations_decomposition` (G_μν symbolic derivation from Riemann tensor). Needs symbolic-tensor primitives — significant scope.
- **physics-005-equivalent:** quantum-gravity comparative (LQG vs ST) is qualitative — substrate role is bounded; this is rubric-grading territory not closed-form territory.
- **Bridge-to-symbolic:** extend `src/project_x/reasoning/symbolic.py` with vector calculus (gradient/divergence/curl on scalar/vector fields) — preconditions for Maxwell's equations or Navier-Stokes.

---

## Acceptance test for cycle 5 entry

Before cycle 5 closes:

- [ ] Replace physics-003's `_relativistic_momentum_predicate` with energy-momentum-relation predicate (cycle 5 #1 candidate).
- [ ] Run probe with new predicate; verify `memorization_signal == 0.0` still holds.
- [ ] At least one surrogate set (per primitive) with `surrogate_author != "builder (rule-based)"` (lain-authored OR textbook-derived).
- [ ] Per-criterion floor gates active in Path B physics rubric grading (Candidate B from PHASE_13_ANTICHEAT_AUDIT.md).
- [ ] Substrate Tier 3 — at least one primitive shipped (vector-calculus or large-angle pendulum or air-resistance free-fall).

Each ticked item materially strengthens the anti-cheat surface.
