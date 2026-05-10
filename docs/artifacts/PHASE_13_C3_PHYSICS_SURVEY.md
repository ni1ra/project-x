# Phase 13 Cycle 3 — Physics Ladder Survey (#00P13c3-03)

**Authored:** 2026-05-10 by Claude Code Raphael (the BUILDER)
**Source:** `gpt-codex/benchmark/physics/ladder.jsonl` (6 entries) + `gpt-codex/benchmark/physics/rubric.md`
**Purpose:** classify physics ladder by verification path; identify cycle 4 scope-fit candidates per the cycle 3 cycle reflection sequencing (substrate Tier 2 expansion vs Path B grader-flip vs both).

---

## 1. Ladder breakdown

| Rank | ID | Difficulty | Prompt shape | Verification path | Current status |
|---|---|---|---|---|---|
| 1 | `physics-001` | intro | Free-fall kinematics (`t = √(2h/g)` for h=80m, g=9.8) | `numerical_close` | **AUTO-GRADED-GREEN** |
| 2 | `physics-002` | easy | Simple pendulum period (`T = 2π√(L/g)`) | `numerical_close` | **AUTO-GRADED-GREEN** |
| 3 | `physics-003` | medium | Relativistic momentum (`p = γmv`, γ = 1/√(1-v²/c²)) at v=0.9c | `numerical_close` | **AUTO-GRADED-GREEN** |
| 4 | `physics-004` | hard | Einstein field equations conceptual (proof-shape) | rubric-pending (proof-shape) | UNGRADED |
| 5 | `physics-005` | frontier | LQG vs string theory comparison (proof-shape) | rubric-pending (proof-shape) | UNGRADED |
| 6 | `physics-006` | unsolved | Cosmological constant problem | `ungradeable; unsolved tier` | UNGRADEABLE |

**Current physics PASS count:** 3/0 (ranks 1-3 auto-green via cycle 2 D5 + cycle 3 D5 confirmation). Ranks 4-5 rubric-pending; rank 6 ungradeable. **Identical structure to maths ladder.**

## 2. Cycle 4 scope-fit verdict — TWO COMPLEMENTARY PATHS

### Path A — substrate extension to closed-form physics (Tier 2 candidate)

All 3 closed-form physics entries (ranks 1-3) reduce to **arithmetic + sqrt + simple algebra** — primitives the cycle 3 substrate already has via `solve_quadratic`'s `math.sqrt` foundation.

Required substrate primitives (each builds on cycle 3 substrate):
- **`free_fall_time(h, g)`** — closed-form `t = √(2h/g)`. Reuses `math.sqrt` directly. 1-step Lemma chain.
- **`pendulum_period(L, g)`** — closed-form `T = 2π√(L/g)`. Reuses `math.sqrt` + `math.pi`. 1-step Lemma chain.
- **`relativistic_momentum(m, v, c)`** — closed-form `p = m·v/√(1-v²/c²)`. Reuses `math.sqrt`. 2-step Lemma chain (compute γ first, then p = γmv).

Each primitive composes prior primitives (organic-thesis composition discipline preserved). Each lemma carries an `add_introduction` (math-WHY: kinematic-equation derivation from constant-acceleration; pendulum from small-angle SHM; relativistic momentum from Lorentz factor) + `add_invariant_check` where physically meaningful (e.g. relativistic momentum reduces to mv in v << c limit).

**Cycle 4 effort estimate:** small. ~3 primitives + ~10-15 tests + 3 baseline candidates + advisor + commit. Roughly 1 hour of cycle 4 work. **Outcome: substrate works on physics rank 1-3, but PASS count stays 3/0** (those are already auto-green) — same QUALITY-vs-COUNT gap as cycle 2 maths Path A.

### Path B — grader-flip on physics-004 + physics-005 (cycle 3 Path B repeat)

Same shape as cycle 3 #00P13c3-01 Path B on maths-004/005. Apply cycle 1 grader-min to the hand-crafted `raphael_response` for physics-004 (Einstein field equations) + physics-005 (LQG vs string theory). Builder grades against rubric proof-shape dimensions.

**Cycle 4 effort estimate:** small. Read raphael_response, grade, write JSONL, ladder schema flip + bench-replay. ~30-60 min. **Outcome: physics PASS 3/0 → 4/0 or 5/0 directly.** Visible PASS-count progress.

### Cycle 4 recommended sequencing

**Both paths combine cleanly in one cycle** — Path B (#00P13c4-01) ships visible PASS lift fast; Path A (#00P13c4-02) ships substrate quality on physics. Mirror of cycle 3 sequencing (Path B first for visibility, substrate work second for capability deepening).

Or: cycle 4 ships Path B + cycle 5 ships substrate Tier 2 (deeper substrate primitives — complex numbers, Newton's method for higher-degree polys, contour integration for maths-003 residue). lain-decided at cycle 3 close.

## 3. Anti-thesis-violation check

- All 3 closed-form physics primitives use Python stdlib `math` module (sqrt + pi) — calculator, not symbolic-AI. Compliant.
- NO numerical-physics-libraries (numpy.physics, scipy.constants — neither needed for cycle 4 minimum-viable scope).
- Pendulum small-angle approximation is mathematical assumption, not library reach.
- Relativistic momentum closed-form is non-quantum classical-relativistic; no physics-engine wrapper.

## 4. Out-of-scope for cycle 4 substrate

- **physics-004** (Einstein field equations): tensor calculus + Riemannian geometry + stress-energy tensor — beyond closed-form arithmetic substrate. Path B (grader-flip on existing raphael_response) is the cycle 4 path; substrate-driven attempt is cycle 6+.
- **physics-005** (LQG vs string theory): comparative quantum gravity exposition — proof-shape only; substrate has no path. Path B only.
- **physics-006** (cosmological constant): ungradeable per design.

## 5. Cycle 4 deliverable hand-off (provisional, refined at cycle 3 D6 reflection)

Provisional cycle 4 #00P13c4-XX scope (folds into DO_THIS_NEXT.md rewrite at #00P13c3-06):
- **#00P13c4-01-pathB-physics-rank-4-5-grader-flip** [HIGH] — visible PASS lift (3 → 4 or 5)
- **#00P13c4-02-substrate-physics-tier2-extensions** [MED] — `free_fall_time` + `pendulum_period` + `relativistic_momentum` primitives + tests + substrate-vs-substrate physics baseline
- **#00P13c4-03-cycle3-deferred-substrate-driven-attempt** [HIGH] — the deferred cycle 3 #00P13c3-04 (was deferred per advisor pacing flag); now executable on cycle 4's chosen domain (physics rank 1-3 substrate-driven attempt)
- **#00P13c4-04-bench-replay** + **#00P13c4-05-cycle-reflect** — standard tail

Note cycle 3 deferred #00P13c3-04 carries forward as cycle 4 #03 — explicit rationale per advisor pacing flag (cycle 3 closed cleanly with #01-#02 + #03 + #05-#06; #04 heavier new-domain attempt absorbs into cycle 4).

---

*— survey artifact landed for #00P13c3-03 at cycle 3 D3. Quick recon; substantive scope-fit verdict for cycle 4 path-selection.*
