# Cycle 14 Council — Angle A3: Credit assignment loop over composed answers

**Status:** council angle 3 of 5. Feeds the synthesis pass (#07).
**Date:** 2026-05-11.
**Pairs with:** the demo doc (`cycle-14-demo-post-thesis.md`, commit `d89b90f`), A1 (`a0babad`), A2 (`d40572d`), the remaining 2 cycle-14 angle notes, and the cycle-14 synthesis verdict.
**Strict thesis lens:** A3 is the plumbing that turns a scalar rating into a *structured* gradient signal — without A3, A1 and A2 receive only "good walk / bad walk" instead of "the third fragment was load-bearing; the dispatcher choice was right; the K-rollout strategy was wrong." A3 is hand-coded LEARNING MACHINERY by every reasonable reading; it adds the credit-propagation algorithm but no new knowledge.

---

## 1. The proposal

Today the audit UI (cycle 12) writes a single rating `r ∈ [1..5]` per rated walk to `audit/ratings.jsonl`. A1's HebbianBank consumes the rating as scalar against the prompt-hv↔fragment-hv pairs; A2's PrimitivePolicy consumes it as scalar against the prompt-hv↔primitive-id pair. Both compress the rating's structure to scalar.

A walk has structure:

- A primitive choice (`_try_natural_mode` vs `_try_quadratic` vs ...).
- A K-rollout strategy choice (bind / bundle / greedy).
- A walk path (5 fragments retrieved in a specific order, each at a specific cosine to the bundled-context-at-step-k).
- Each fragment's similarity score at the moment it was retrieved.

If the rating reflects "this walk was good," then *some* of those structural decisions were right. If "this walk was bad," some were wrong. **Today the substrate cannot tell which.** A scalar rating distributed uniformly across 4 structural decisions × 5 fragments = a noisy gradient where signal-to-noise is 1/20 in the worst case.

A3 proposes:

**A credit-assignment rule that distributes the scalar rating non-uniformly over the structural decisions a walk made, proportional to each decision's *marginal contribution* to the walk's coherence.**

Concretely:

1. **Fragment-level credit:** each retrieved fragment's contribution = its per-step similarity score normalized by the walk's total similarity. High-similarity fragments get more credit (positive for `r ≥ 4`, negative for `r ≤ 2`).
2. **Strategy-level credit:** the chosen K-rollout strategy (e.g. `greedy`) gets credit = `(its_avg_similarity − second_place_strategy_avg_similarity) / max_avg_similarity`. If `greedy` won by a wide margin, it gets most credit; if it barely won, credit is split with the runners-up.
3. **Primitive-level credit:** the dispatched primitive gets credit proportional to `(combined_confidence − refuse_threshold)`. Confident-and-right walks reinforce the primitive choice strongly; barely-clearing walks reinforce weakly.
4. **Walk-path credit:** ordered fragments contribute differently — step 1's choice constrains steps 2-5; A3 weights early-step fragments more heavily on the principle that "the first fragment sets the trajectory."

Each piece of credit then flows to:

- A1's HebbianBank — fragment-level credit updates the prompt-hv↔fragment-hv binding strength.
- A2's PrimitivePolicy — primitive-level credit updates the per-primitive embedding `θ_i`.
- A new `StrategyPolicy` (small enough to fit alongside A3): strategy-level credit updates per-strategy preference weights.

In one sentence: *a rating stops being a scalar on the whole walk and becomes a structured update on the four decisions the walk actually made.*

## 2. The pre-demo strict-thesis case

A3 is the credit-assignment half of any learning loop. Backprop in transformer training is credit-assignment over a computation graph; A3 is credit-assignment over a hand-coded HDC composition graph (primitive→strategy→fragment-walk→render). The graph is simple enough that hand-coded credit-propagation rules suffice; no auto-diff machinery needed.

Strict-thesis fit: A3 is LEARNING MACHINERY (the credit-propagation algorithm + the per-decision weighting heuristics are hand-coded), and produces no new MODEL KNOWLEDGE — the rating becomes a structured gradient over A1's and A2's parameter spaces. A3 has no parameters of its own except (optionally) the per-decision weighting heuristics' coefficients.

A1 + A2 alone work, but with a noisy scalar-rating signal. A3 sharpens that signal by factoring it through the walk's actual structural decisions. The synthesis pass should treat A3 as A1+A2's amplifier, not as a competing direction.

## 3. What the demo data adds

Mapping A3 to the cycle-14 demo's 7 findings:

- **F1 (formal math route is hand-coded):** A3 is ORTHOGONAL — formal routes (`solve_quadratic`) emit a Lemma render, not a multi-fragment walk; nothing to do credit assignment over.
- **F2 (cycle-13 #07e routes off-trigger correctly):** A3 is INDIRECT — A3 amplifies A2's policy update; the cosine-archetype feature's contribution to combined-confidence becomes a credit-assigned signal A2 learns to weight.
- **F3 (retrieval ≠ composition on P2/P3):** A3 is the DIRECT amplifier of A1's strike at F3. A1 alone updates substrate atomically per rating; A1 + A3 updates each FRAGMENT's contribution non-uniformly, so the substrate learns "Whitman-`give-me-eyes` was the dominant retrieval for prompt 'river that forgets sea' and got rated 2/5, decay HIGH" rather than "the whole walk got rated 2/5, decay UNIFORM."
- **F4 (P4 humour misroutes to math):** A3 is INDIRECT — credit-assignment over A2's primitive choice means the math-walk's rating directly updates the policy's `θ_math`, not just a generic "walk had bad rating" signal.
- **F5 (P5 chat misroutes to poetry):** A3, same as F4.
- **F6 (strict-thesis fraction ~0%):** A3 indirectly shifts the fraction by amplifying A1 + A2.
- **F7 (cold-encoder latency):** A3 is ORTHOGONAL.

Net: A3 directly amplifies A1's F3 strike (the central retrieval-vs-composition gap); indirectly amplifies A2's F4 + F5 strikes; orthogonal to F1, F7; absorbed by A2 for F2. **A3's load-bearing % depends entirely on whether A1 or A2 ships alongside it.** A3 in isolation produces ~0 cycle-14 capability lift; A3 with A1+A2 IS the complete strict-thesis-fraction strike.

## 4. Implementation sketch

- New module `src/project_x/reasoning/credit.py` (~150-250 lines):
  - `CreditAssignment` class: `propagate(walk_metadata: WalkMetadata, rating: int) -> CreditBundle` where `WalkMetadata` carries (primitive_id, strategy, fragments, per_step_sims, combined_confidence, refuse_threshold) and `CreditBundle` carries `(fragment_credits: dict[str, float], primitive_credit: float, strategy_credit: dict[str, float])`.
  - Per-decision weighting heuristics: cycle-14 v0 ships with hand-tuned coefficients (e.g. fragment_step_decay = 0.8, strategy_margin_weight = 1.0); cycle-15+ calibration sweeps.
- Modify `src/project_x/audit/`: rating-write triggers `CreditAssignment.propagate`, then routes the bundle to A1's HebbianBank.update + A2's PrimitivePolicy.update.
- Modify `src/project_x/corpus/k_rollout.py`: `KRolloutResult` carries `WalkMetadata` on every emit (already mostly present in `parsed_inputs`; A3 just needs to formalize the schema).
- New `StrategyPolicy` (small — ~50 lines): three scalars `weight_bind / weight_bundle / weight_greedy`; updated from strategy-level credit; modifies K-rollout's strategy-selection weighting from "highest avg_similarity wins" to "highest (avg_similarity × strategy_weight) wins."
- Tests `tests/test_credit_assignment.py` (~200 lines, 12-18 tests):
  - Empty walk-metadata → empty bundle.
  - Single-fragment walk → all credit on that fragment.
  - 5-fragment walk + uniform similarities → uniform credit.
  - 5-fragment walk + skewed similarities → skewed credit per step-decay heuristic.
  - Strategy-level credit: 3-strategy K-rollout where chosen strategy wins by margin → most credit; wins by ε → split credit.
  - Cycle-13 regression: existing tests pass with A3 disabled (cold-start coefficient = 0 collapses to uniform).
- `docs/REPO_CONTROL.md` rows for `credit.py` and the StrategyPolicy.
- Cycle-14 atomic commits: `feat(P13c14-08-credit-assignment)` (or numbered as #08c if A2 + A1 also ship under #08).

Estimated cost: **2-3 h Raphael-time** — A3 is genuinely small; most of the work is integration with A1's HebbianBank and A2's PrimitivePolicy update paths. Calibration of the per-decision weighting coefficients is queued cycle-15+ as a hyperparameter sweep over a held-out audit log.

## 5. The discriminating question for the synthesis pass

A3's score depends on whether A1 / A2 also ship:

| Scoring axis | A3 score (solo) | A3 score (bundled with A1+A2) | Plausible cycle-14 #1 |
|---|---|---|---|
| **Biggest CAPABILITY lift this cycle** | ~5% (no parameters of its own; relies on A1/A2 existing) | ~25% (amplifier of A1 + A2 strikes) | A2 + A1 + A3 as the triple |
| **Biggest STRICT-THESIS-fraction shift** | ~10% (provides structure to the rating signal; doesn't add new substrate writability or learned routing) | ~25% (essential for A1+A2 to receive structured signal) | A2 + A1 + A3 triple |
| **Combined multi-ship** | ~20% (when bundled with at least one of A1/A2) | ~25-30% | A2 + A1 + A3 triple as the complete dispatcher+substrate+credit-flow combo |

The cycle-14 budget question is whether all three ship in one cycle. A1 alone is 3-5 h, A2 alone is 3-4 h, A3 alone is 2-3 h. Combined: 8-12 h Raphael-time, plus integration testing. That's plausibly 1.5-2 cycles of work — meaning the synthesis pass might split A2 + A3 into cycle-14 (the dispatcher half) and A1 into cycle-15 (the substrate half), or vice versa.

**The discriminating question for the synthesis pass: which two of {A1, A2, A3} ship this cycle?**

A1 + A3 ships substrate writability + structured credit propagation; A2 ships in cycle-15. Risk: dispatcher remains hand-coded for another cycle, F4/F5 misroutes persist.

A2 + A3 ships learned routing + structured credit propagation; A1 ships in cycle-15. Risk: substrate remains frozen for another cycle; A2 is updating policy parameters that read from a frozen encoder.

A1 + A2 ships substrate writability + learned routing without A3; A3 ships in cycle-15. Risk: credit signal is scalar-uniform; A1 and A2 both update with high-variance gradients; the audit-volume floor effectively doubles.

The synthesis pass picks one of these triangles. A3's role is to be the "yes, bundle me with whatever else ships" angle — A3 alone produces ~5% lift, A3 bundled produces +5-10% on top of whatever it's bundled with.

## 6. Load-bearing % verdict (honest, axis-dependent + bundle-dependent)

- **On the "capability lift this cycle" axis, solo:** A3 is ~5% load-bearing.
- **On the "capability lift this cycle" axis, bundled with A1+A2:** A3 is ~25% load-bearing.
- **On the "strict-thesis-fraction shift" axis, solo:** A3 is ~10% load-bearing.
- **On the "strict-thesis-fraction shift" axis, bundled:** A3 is ~25% load-bearing.
- **On the "combined multi-ship" axis:** A3 is ~25% load-bearing, with the explicit recommendation that A3 ships ALONGSIDE A1 OR A2 (and ideally both).

**Single-number summary for the synthesis pass:** **~20% load-bearing as the "amplifier" angle.** Pre-demo informal estimate at the demo doc §6 was also ~20%; the F3-direct-amplification evidence + A3's clear "bundle me" structural role keeps the number stable. A3 is genuinely *low priority alone* and *medium priority bundled* — the synthesis should treat it as an automatic add-on when A1 or A2 ships.

## 7. Honest counter-claims (M-PROJECTX-013 measure-don't-claim)

1. **A3 solo produces almost no capability lift.** A3 distributes a scalar rating into a structured bundle, but if nothing else consumes the bundle, the structure is wasted bytes. A3's value is conditional on A1 or A2 (or both) shipping in the same cycle.
2. **Per-decision weighting heuristics are themselves hand-coded.** Step-decay coefficient = 0.8, strategy-margin-weight = 1.0 are author-picked. Future cycles may critique this as "still authoring the structure of learning"; same response as A2 — the strict thesis allows hand-coded LEARNING MACHINERY.
3. **The walk's structural decisions are not all causally independent.** The primitive choice constrains the strategy choice (formal routes don't have a strategy); the strategy choice constrains the fragment-walk path. A3's heuristic credit-distribution treats them as factored when they're actually conditional. Future cycles may want a more principled causal-graph-aware credit rule; cycle-14 v0 ships the factored approximation.
4. **A3 cannot fix sycophantic ratings.** Same dependency as A1/A2 on lain's calibration discipline. Even structured credit over a `r=5,5,5,5,5` rating series teaches the substrate nothing.
5. **The strategy-policy is a parameter A3 introduces.** Technically A3 adds 3 scalars (weight_bind, weight_bundle, weight_greedy) and updates them from strategy-level credit — that IS new substrate state. Defensible per "small enough that the hand-coded scaffolding (3 scalars) is justified," but could be challenged as "A3 is also adding a learned routing rule like A2." The boundary between A3-credit-routing-to-A2 and A3-having-its-own-mini-policy is thin; the synthesis pass should be explicit about whether StrategyPolicy lives inside A3 or is split out.

## 8. Cycle-15 spillover (if A3 not picked this cycle)

A3 is the natural add-on for whichever of A1 / A2 ships in cycle-14:

- If cycle-14 ships A2 alone (no A3): the policy receives scalar-only rating signal; cycle-15 task A3 amplifies the policy's learning rate retroactively.
- If cycle-14 ships A1 alone (no A3): the HebbianBank receives scalar-only rating signal; same retroactive cycle-15 amplification.
- If cycle-14 ships A2+A3 or A1+A3: one of A1/A2 ships in cycle-15 plus integration work to flow A3's existing credit bundle to the new component.

A3 has the lowest urgency of A1/A2/A3 — it amplifies but doesn't STRIKE the strict-thesis gap on its own. Deferring A3 a cycle is the most acceptable of the three deferrals.

---

*Single-line takeaway: A3 turns a scalar rating into a structured gradient over the walk's actual structural decisions. ~5% lift solo, ~25% lift bundled with A1 or A2. The "yes, bundle me" angle — synthesis pass should treat A3 as an automatic add-on when A1 or A2 ships. The discriminating question is which two of {A1, A2, A3} fit in cycle-14's budget.*
