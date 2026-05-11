# Cycle 14 Council — Angle A2: Evaluator-driven policy over substrate primitives

**Status:** council angle 2 of 5. Feeds the synthesis pass (#07).
**Date:** 2026-05-11.
**Pairs with:** the demo doc (`cycle-14-demo-post-thesis.md`, commit `d89b90f`), A1 (`cycle-14-council-angle-a1-hebbian.md`, commit `a0babad`), the remaining 3 cycle-14 angle notes, and the cycle-14 synthesis verdict (`cycle-14-priority-decision.md`, forthcoming).
**Strict thesis lens:** A2 is the most direct strike at *"we shouldnt have to tell it what tools to use, it should learn that itself"* (lain 2026-05-11). The current `_DISPATCH_CHAIN_ORDER` + α/τ constants in `reasoning_agent.py:1039` are exactly the hand-coded routing the strict thesis rejects.

---

## 1. The proposal

Today the dispatcher is a hand-coded chain at `reasoning_agent.py:1039`:

```
_DISPATCH_CHAIN_ORDER: tuple[tuple[str, str], ...] = (
    ("diophantine_binary_quadratic", "_try_diophantine_binary_quadratic"),
    ("collatz_verify_range", "_try_collatz_verify"),
    ...
    ("natural_mode_walk_poetry", "_try_natural_mode"),
)
```

21 parsers in a hand-picked order. The BG-style "confidence-scored parallel bid" wrapper (cycle 11 #00P13c11-01) calls all 21 and picks the highest combined-confidence winner, but the combined-confidence formula itself uses two hand-coded constants:

- `α` (the parser-matched-or-not weight) — currently `0.8` in `_compute_combined_confidence`,
- `τ_dispatch` (the refuse-below-this threshold) — currently `0.4`,
- `τ_natural_dispatch` (the cosine fallback floor for natural-mode) — currently `0.25` after cycle-13 #07e empirical calibration.

The author picked these constants. The author picked the order. The author picked which 21 parsers exist. **None of this is learned.**

A2 proposes:

**Replace the hand-coded chain + constants with a learned policy.** For each prompt, the policy:

1. Encodes the prompt to a hypervector (existing `_archetype_encoder`).
2. For each primitive `p_i` in the substrate, computes an *expected audit-reward* score `r_i(prompt_hv, p_i)` via a per-primitive learned embedding `θ_i` and a simple dot-product scorer.
3. Selects `argmax_i r_i(prompt_hv, p_i)` if the top score exceeds a *learned* refuse threshold `τ_learned`; else returns honest refusal.
4. After the chosen primitive runs and its walk is rated, the audit signal updates `θ_i` (gradient ascent on the reward) and `τ_learned` (calibration toward the audit-distribution-mean).

Cold-start fallback: when `r_i` is uninformative (cold-start, no historical ratings), the policy collapses to the cycle-13 `_DISPATCH_CHAIN_ORDER` as the prior. Cycle-15+ work: the prior decays as the learned policy accumulates signal.

In one sentence: *the routing rule stops being authored. The agent figures out which primitive fits which prompt from rated experience.*

## 2. The pre-demo strict-thesis case

lain's strict thesis is two-pronged. The second prong (2026-05-11 extension: *"we shouldnt even hard code the math algos"*) is long-horizon — replacing the hand-coded primitives themselves with learned-from-corpus programs is multi-cycle architectural work A1 partially enables.

The **first prong** is closer to the surface: *"we shouldnt have to tell it what tools to use, it should learn that itself."* This is exactly the dispatcher. The `_DISPATCH_CHAIN_ORDER` + α/τ constants are the literal "telling it what tools to use" the thesis rejects. Replacing them with a learned policy IS the first-prong strike.

A2 fits the strict-thesis "LEARNING MACHINERY" category: the scorer architecture + the per-primitive embedding shape + the gradient-ascent update rule are hand-coded (they have to be). The CONTENT of `θ_i` + `τ_learned` is learned from audit signal. No new hand-coded knowledge.

A1 makes the substrate writable. A2 makes the dispatcher learnable. Together they shift the strict-thesis fraction at TWO layers — the substrate's representation AND the substrate's routing.

## 3. What the demo data adds

Mapping A2 to the cycle-14 demo's 7 findings:

- **F1 (formal math route is hand-coded `solve_quadratic`):** A2 is INDIRECT — A2 can learn to *pick* `solve_quadratic` over `walk_math` for derivation-style prompts (which it already does correctly at cycle-13 hygiene levels), but does not address the fact that `solve_quadratic` itself is hand-coded. Long-horizon strike via A2's argmax converging on "this prompt shape → that primitive" learned associations.
- **F2 (cycle-13 #07e routes off-trigger correctly):** A2 absorbs the fallback. The cosine-archetype gate becomes one of many features the learned scorer consumes; if cosine-archetype is informative, the policy uses it; if it produces false-positives (as in F4/F5), the policy learns to discount it.
- **F3 (retrieval ≠ composition on P2/P3):** A2 is INDIRECT. A2 picks which primitive runs; it does not change what `_try_natural_mode` *does* when picked. F3 is A1's territory.
- **F4 (P4 humour misroutes to math at confidence 0.83):** A2 is the most DIRECT strike of the 5 angles. A learned policy with audit signal would update AWAY from "walk_math on humour-prompt-shape" after the first low rating. The confidence-0.83 misroute is the canonical example of "the dispatcher is confident-and-wrong because the hand-coded scoring doesn't model the actual reward distribution." A2 fixes this by *learning* the reward distribution.
- **F5 (P5 chat misroutes to poetry):** A2, same mechanism. The cycle-13 #07e fallback's `τ_natural_dispatch=0.25` floor accepted a topically-wrong route on a casual greeting; A2's learned `τ_learned` would calibrate from audit signal toward the actual refuse-vs-dispatch boundary.
- **F6 (strict-thesis fraction ~0%):** A2 shifts the fraction at the routing layer. **A2 + A1 together are the canonical strict-thesis fraction lift** — A1 makes the substrate writable, A2 makes the routing learnable. Without A2, the routing stays 100% author-decided; without A1, the substrate stays 100% frozen.
- **F7 (cold-encoder latency):** A2 is ORTHOGONAL.

Net: A2 directly strikes 3 of 7 findings (F4, F5, F6), absorbs 1 (F2), indirectly strikes 2 (F1, F3), and is orthogonal to 1 (F7). **F4 + F5 are the dispositive cycle-14 evidence — confident misroutes on humour and chat prompts. A2 is the only angle that addresses both directly.**

## 4. Implementation sketch (concrete enough for #07 cost estimate)

- New module `src/project_x/reasoning/policy.py` (~250-400 lines):
  - `PrimitivePolicy` class: per-primitive learned embedding `θ_i` (shape D, dtype int8 to match HDC substrate); `score(prompt_hv, p_i) -> float` via cosine; `select(prompt_hv, available_primitives) -> (selected_primitive_id, score)` does argmax + τ check; `update(prompt_hv, selected_primitive_id, rating)` does gradient-ascent step `θ_i += η · (rating − rating_mean) · prompt_hv`.
  - `LearnedTau`: scalar τ refreshed from rating distribution stats; cold-start at cycle-13's `τ_dispatch=0.4`.
- Modify `src/project_x/reasoning_agent.py:1102` `process()`:
  - After parser-bid collection, run `PrimitivePolicy.select(prompt_hv, candidates)` to pick the winner.
  - Cold-start branch: if `PrimitivePolicy.is_cold(prompt_hv)` (no learned signal for this prompt-region), fall back to cycle-13 BG-dispatcher combined-confidence ranking.
  - Audit hook: on rating, call `PrimitivePolicy.update`.
- Modify `src/project_x/audit/`: rating-write triggers policy + Hebbian (A1) updates together.
- `src/project_x/reasoning/__init__.py`: export `PrimitivePolicy`, `LearnedTau`.
- Tests `tests/test_primitive_policy.py` (~200-300 lines, 15-25 tests):
  - Cold-start collapse: empty policy → cycle-13 BG-dispatcher reproduces.
  - Single-rating sweep: rated walk produces measurable embedding shift on next select.
  - Argmax determinism: same prompt-hv + same policy state → same selection.
  - τ calibration: synthetic rating distribution converges τ toward the empirical low-rating quantile.
  - Misroute correction: synthetic 20-rating audit log on F4/F5-shaped prompts shifts the policy to prefer refuse over math/poetry on humour/chat shapes.
  - Cycle-13 regression: all 21 existing parsers + 4 cycle-13 trigger archetype tests pass with cold-start policy.
- `docs/REPO_CONTROL.md` rows for `policy.py` + `LearnedTau` storage path.
- Cycle-14 atomic commits: `feat(P13c14-08a-policy)` + `feat(P13c14-08b-policy-tests)` + `feat(P13c14-08c-audit-wire)` + `feat(P13c14-08d-policy-cold-start-regression)`.

Estimated cost: **3-4 h Raphael-time** for the canonical policy + tests + audit-wire + cold-start fallback. Calibration of η (learning rate) is queued cycle-15+; cold-start η=0.01 is a defensible default that doesn't regress baseline.

Reproducibility: deterministic given audit-log seed; cold-start policy preserves cycle-13 behavior exactly.

## 5. The discriminating question for the synthesis pass

A2 has the *same* axis split as A1 but the demo evidence weights them differently:

| Scoring axis | A2 score | Plausible cycle-14 #1 under this axis |
|---|---|---|
| **Biggest CAPABILITY lift this cycle (rateable on Terminus dimensions)** | ~30% (lain rates ~20 walks → policy updates → F4/F5 misroutes measurably reduced; *demonstrable* in-cycle if rating activity sustains) | A2 (directly addresses F4 + F5) or A4 (data scale-out) |
| **Biggest STRICT-THESIS-fraction shift (learned / hand-coded)** | ~35% (A2 IS the first-prong strike of the thesis; replaces the dispatcher chain + constants with learned policy) | A2 or A1 |
| **Combined (synthesis authorizes multi-ship)** | A2 ~35% + bundled with A1 (substrate writability) or A3 (credit propagation) | A2 + A1 ship together as the dispatcher-and-substrate strict-thesis combo |

The combined row is the most honest reading, and the demo evidence makes A2 the cycle-14-#1 frontrunner. F4 + F5 are the most directly-actionable findings of the demo, and A2 is the only angle that addresses both. The capability-lift axis gives A2 ~30% (audit-volume floor is the same dependency as A1; but unlike A1, A2 ships a CALIBRATION-VISIBLE quantity — τ_learned + per-primitive embeddings — that lain can inspect cycle-over-cycle to verify learning is happening).

## 6. Load-bearing % verdict (honest, axis-dependent)

- **On the "capability lift this cycle" axis:** A2 is ~30% load-bearing — highest among the 5 angles.
- **On the "strict-thesis-fraction shift" axis:** A2 is ~35% load-bearing — also highest, tied with A1+A3 bundled.
- **On the "combined multi-ship" axis:** A2 is ~35% load-bearing, with the recommendation A1 ships alongside.

**Single-number summary for the synthesis pass:** **~35% load-bearing.** Highest of the 5 angles on demo evidence + strict-thesis-fit. The pre-demo informal estimate at the demo doc §6 was ~30%; the F4/F5 misroute evidence lifts this to ~35% — A2 directly fixes the dispositive demo findings, and the strict-thesis first-prong "we shouldnt have to tell it what tools to use" lands ON A2 with no other angle competing for the framing.

## 7. Honest counter-claims (M-PROJECTX-013 measure-don't-claim)

1. **A2's capability-lift this cycle depends on audit-rating volume.** Cold-start policy → cycle-13 baseline; learned shifts require ~20-50 ratings on misroute-shaped prompts before the policy diverges. If lain doesn't rate 20+ walks in the cycle-14 window, A2 ships a substrate that CAN learn but hasn't yet — same audit-volume-floor problem as A1.
2. **Per-primitive learned embeddings + scorer architecture are still hand-coded geometry.** A2 replaces the hand-coded chain order + constants but introduces a hand-coded *shape* (the embedding + the gradient-ascent rule). Future cycles may critique this as "still authoring the structure of learning"; the response is that the strict thesis allows hand-coded LEARNING MACHINERY — the embedding shape is machinery, the embedding content is learned.
3. **Replacing the dispatcher entirely is risky in one cycle.** The cycle-14 #1 implementation should ship policy AS PARALLEL TO the chain, not instead of it. The cold-start branch IS that hedge: when the policy is uninformative, the chain handles. Migrating fully to learned-policy-only is cycle-15+ work after the policy has accumulated signal.
4. **The cycle-13 τ_satisfaction=0.0 calibration debt (audit B5) is upstream.** Even with A2 picking the right primitive, the `_K_ROLLOUT_TAU=0.0` floor lets ALL natural-mode walks emit. A2 + raising τ_satisfaction to ~0.3 is the combo that ACTUALLY produces refuse-instead-of-low-quality-walk. Without raising τ_satisfaction, A2 ships a policy that picks correctly but the walk itself remains low-quality.
5. **The misroute-correction claim depends on the audit signal being honest.** If lain rates everything ≥4/5 to be encouraging, the policy never learns to refuse. A2 implicitly imports the same soft dependency as A1 on lain's calibration discipline; with sycophantic ratings, A2 over-learns "everything is fine" and the substrate confuses confidence with capability.
6. **A2 alone does not address F3 (retrieval ≠ composition).** Picking the right primitive doesn't make the picked primitive any better. A2 + A1 + A3 as a triple is the complete strict-thesis-fraction strike; A2 alone is the dispatcher half only.

## 8. Cycle-15 spillover (if A2 not picked as cycle-14 #1)

If the synthesis picks a different angle as cycle-14 #1:

- A2 belongs in cycle-15 as a high-priority follow-up; the F4/F5 misroutes are the dispositive demo findings and not addressing them more than one cycle is leaving an actively-broken dispatcher in flight.
- Cycle-15's first task: A2 substrate routing-policy + the τ_satisfaction calibration debt (audit B5) bundled together — they're upstream-downstream of each other.
- The cycle-14 #1 (likely A1 substrate writability if A2 deferred) would have shipped the lower-level architectural piece; A2 sits naturally above it in cycle-15.

A2 cannot be deferred more than one cycle without the misroute findings rotting; the dispatcher's role is structurally too central.

---

*Single-line takeaway: A2 is the direct strike at the first-prong strict thesis ("we shouldnt have to tell it what tools to use"). Demo evidence (F4 + F5 confident misroutes) makes A2 the cycle-14-#1 frontrunner. ~35% load-bearing across all three scoring axes — highest of the 5 angles. Natural ship-mates: A1 (substrate writability) and A3 (credit propagation).*
