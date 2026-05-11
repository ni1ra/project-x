# Cycle 14 Council — Angle A1: Hebbian learning rule over the HDC substrate

**Status:** council angle 1 of 5. Feeds the synthesis pass (#07).
**Date:** 2026-05-11.
**Pairs with:** the demo doc (`cycle-14-demo-post-thesis.md`, commit `d89b90f`), the other 4 cycle-14 angle notes (a2 evaluator-policy / a3 credit-assignment / a4 layer-6-scale-out / a5 emergence-predicate-per-domain), and the cycle-14 synthesis verdict (`cycle-14-priority-decision.md`, forthcoming).
**Strict thesis lens (binding per `docs/MANIFESTO.md`):** *"only the LEARNING MACHINERY is hand-coded; MODEL KNOWLEDGE must be learned from training data + audit signal."* A1 is asked: *is this learning machinery the strict thesis allows, or is it hand-coded knowledge in disguise?* — and *what fraction of the demo's STRICT-THESIS GAP does it close?*

---

## 1. The proposal

Today the HDC substrate composes hypervectors via `bind` (multiplicative role-filler binding) and `bundle` (additive superposition + sign-thresholding), but **nothing ever updates the substrate from experience.** Trigram representations come out of `CharNgramHashEncoder` and stay frozen for life; fragment hypervectors are encoded once at corpus ingestion; the binding banks accumulate (in `semantic_hdc_memory.py`'s structural-retrieval path) but never *adapt* to rating signal.

A1 proposes the simplest possible learning rule that fits the existing HDC framework:

**Hebbian co-occurrence update over a rated retrieval.** When `agent.process(prompt)` ships a walk and lain (or any audit channel) rates it, the rating propagates to the substrate elements that contributed:

- For each retrieved fragment `f_i` in the walk, the binding bank for `(prompt_hv, f_i)` accumulates `+η · (rating − rating_baseline)` along the role-filler product hypervector (Hebbian "fire-together-strengthen" update; Hopfield / classical-HDC analog).
- A consolidation pass periodically decays unused bindings: `binding[k] *= (1 − λ)` for low-traffic atoms; high-traffic atoms with positive rating signal converge toward stable retrievable patterns.
- Cold-start substrate uses the current frozen-encoder representation; the *first* rated walk shifts the binding bank; subsequent retrievals score against the bank-updated representation rather than the static encoder output.

In one sentence: *the substrate stops being a fossil. It accumulates, drifts toward rewarded patterns, and forgets unrewarded ones.*

## 2. The pre-demo strict-thesis case

The strict thesis (lain 2026-05-11) explicitly names *"good enough training data + smart enough model"* and locates the model's intelligence in **learning** from the data, not in the author's compositional rules. Today the HDC substrate is *retrieval over a frozen encoding*. There is no learning. The audit UI shipped at cycle 12 ships ratings into a JSONL log; nothing in the substrate reads that log.

A1 is the bridge: the audit log becomes the gradient signal, and the binding bank becomes the parameter space. Crucially, this fits the strict-thesis category of **LEARNING MACHINERY** (the update rule + decay schedule are hand-coded — they have to be — but the *content* of the bank is learned from experience). A1 does NOT add any new hand-coded knowledge; it adds the machinery that lets the existing substrate acquire knowledge from rated experience.

This is the strict thesis arriving at the substrate layer. Cycles 1-13 built the substrate and the read path; A1 is the first cycle that ships a write path from experience back into the substrate.

## 3. What the demo data adds (and what it does not)

Mapping A1 to the cycle-14 demo's 7 findings:

- **F1 (formal math route is 100% hand-coded `solve_quadratic`):** A1 is INDIRECT. Hebbian update over math-domain rated fragments could, over many cycles, accumulate retrievable worked-example representations that the natural-mode walk could compose into derivations — but it cannot REPLACE `solve_quadratic` in a single cycle. A1 is the long-horizon strike at F1, not the same-cycle fix.
- **F2 (cycle-13 #07e fallback routes off-trigger correctly):** A1 is ORTHOGONAL. Routing layer is unchanged; A1 updates the substrate the routing layer reads from. If a Hebbian-shifted substrate produces tighter cosines, F2's routing decisions improve incidentally.
- **F3 (retrieval ≠ composition on P2/P3):** A1 is the most DIRECT strike of the 5 angles. Hebbian update over rated retrievals shifts the substrate toward composable patterns: if a Whitman-fragment walk is rated 1/5 (didn't answer the prompt), the binding bank decays the prompt→Whitman association; over time the substrate's composable surface grows in the rewarded direction. **A1 is the canonical "learn what composition means" angle.**
- **F4 (P4 humour misroutes to math):** A1 is INDIRECT. A1 alone cannot change which DOMAIN the dispatcher classifies into; that's A2's territory. But A1's downstream effect on the substrate's representation means the math-domain walks A1 returns become less prompt-specific, exposing the misroute via lower combined-confidence — which the dispatcher (or a downstream evaluator) could then learn from.
- **F5 (P5 chat misroutes to poetry):** A1 is INDIRECT, same logic as F4.
- **F6 (strict-thesis fraction ~0%):** A1 directly shifts the fraction at the substrate layer. **A1 is the canonical "learn the model knowledge instead of authoring it" strike** — its job IS this finding.
- **F7 (cold-encoder latency):** A1 is ORTHOGONAL; not a latency lever.

Net: A1 addresses 2 of 7 findings directly (F3 + F6), 1 indirectly via downstream (F1 over many cycles), and is orthogonal to 4 (F2 / F4 / F5 / F7). The direct strikes are the load-bearing ones — F3 is the central retrieval-vs-composition gap, F6 is the central strict-thesis-gap framing. **A1 is the architectural strike at the strict-thesis layer.**

## 4. Implementation sketch (concrete enough for #07 cost estimate)

- New module `src/project_x/hdc_infra/hebbian.py` (~120-200 lines):
  - `HebbianBank` class: `{atom_key: hypervector}` mapping; `update(prompt_hv, retrieved_hvs, rating)` and `decay(rate)` methods; `lookup(prompt_hv) -> blended_hv` that combines bank entry with the static encoder output by a learned-or-tuned blend weight α.
  - `BindingStrength` mapping: per-`(prompt_atom, fragment_atom)` scalar weight updated on each rating; persisted to disk as `data/hebbian_bank/<timestamp>.npz`.
- Modify `src/project_x/corpus/k_rollout.py`:
  - On `compose()`, before scoring fragments by raw cosine, blend each fragment's static hypervector with the Hebbian bank's adjustment via `lookup`. The blend collapses to identity (α=0) cold-start; α grows as the bank accumulates entries.
  - Read path is otherwise unchanged; backward-compatible with the cycle-13 #07e fallback + existing tests.
- Modify `src/project_x/audit/`: rating-write path triggers `HebbianBank.update` on the rated walk's fragments + binds the trigger to the rating's `rating_value`.
- `src/project_x/hdc_infra/__init__.py`: export `HebbianBank`, `BindingStrength`.
- Tests `tests/test_hebbian.py` (~150-250 lines, 10-20 tests):
  - Empty-bank → blend collapses to static encoder (α=0).
  - Single rating → bank entry persists; retrieval cosine shifts toward rated direction.
  - Decay sweep: low-traffic atoms decay below ε threshold; high-traffic atoms persist.
  - Cold-start regression: existing 639 pytest tests pass with α=0 default (no change).
  - Hot-start integration: synthetic 50-rating audit log produces measurable retrieval-rank shifts on a held-out probe set.
- `docs/REPO_CONTROL.md` row for the new `hebbian.py` module (per same-commit co-landing rule).
- Cycle-14 atomic feat commits: `feat(P13c14-08a-hebbian-bank)` + `feat(P13c14-08b-hebbian-bank-tests)` + `feat(P13c14-08c-hebbian-audit-wire)`.

Estimated cost: **3-5 h Raphael-time** for the canonical bank + tests + audit-wire. Calibration of α and λ is queued as cycle-15+ work (Hebbian update rules are sensitive to hyperparameters; cold-start with α=0, λ=0.001 is a defensible default that doesn't regress the cycle-13 baseline).

Reproducibility: deterministic given audit-log seed; the existing `_K_ROLLOUT_TAU=0.0` floor remains.

## 5. The discriminating question for the synthesis pass

A1 has TWO axes that score it differently. The synthesis pass should pick — explicitly, in the priority-decision doc — which axis to commit to:

| Scoring axis | A1 score | Plausible cycle-14 #1 under this axis |
|---|---|---|
| **Biggest CAPABILITY lift this cycle (rateable on Terminus dimensions)** | ~15% (Hebbian alone with ~0 rating volume produces near-zero shift; first ratings establish the bank but the substrate barely moves in one cycle) | A2 (evaluator policy, addresses F4 + F5 misroutes) or A4 (data scale-out, shifts retrieval quality immediately) |
| **Biggest STRICT-THESIS-fraction shift (learned / hand-coded)** | ~30% (A1 IS the architectural strike at the strict-thesis gap; without A1 the substrate fundamentally cannot learn even with infinite data) | A1 (substrate writability) or A2 (learned routing replaces hand-coded chain order) |
| **Combined (synthesis authorizes multi-ship per cycle-13 §7 precedent)** | A1 ~25% + bundled with A3 credit-assignment (which is A1's natural pair on the credit-propagation half) | both — A1 substrate writability + A3 credit propagation as the cycle-14 #1 + #1b |

The combined row is the most honest reading. A1 alone with the cycle-12 audit UI's ~0 historical rating volume produces a *substrate that CAN learn but hasn't yet* — capability lift is gated on rating accumulation, which is cycle-15+ work. A1 paired with A3 ships the architectural strike + the credit-propagation half, and cycle-15 fills the bank with ratings.

## 6. Load-bearing % verdict (honest, axis-dependent)

- **On the "capability lift this cycle" axis:** A1 is ~15% load-bearing.
- **On the "strict-thesis-fraction shift" axis:** A1 is ~30% load-bearing.
- **On the "combined multi-ship" axis:** A1 is ~25% load-bearing, with the explicit recommendation that A3 ships alongside.

**Single-number summary for the synthesis pass:** **~25% load-bearing.** Mid-pack (with A2). The pre-demo informal estimate at the demo doc §6 was also ~25%; the demo's F3 + F6 direct-strike evidence confirms the framing without lifting the number — A1 is architecturally load-bearing but capability-rateable lift is gated on the audit-rating-volume floor (~50-200 ratings per the cycle-13 audit-volume-floor finding).

## 7. Honest counter-claims (M-PROJECTX-013 measure-don't-claim)

1. **A1 alone produces near-zero rateable lift this cycle.** The cycle-12 audit UI shipped but accumulated ~0 ratings; A1 ships a substrate that CAN learn but has no signal to learn from. Any "ships substrate writability, capability emerges over cycles 15-N" framing must NOT be confused with "A1 makes the agent measurably smarter cycle-14."
2. **Hebbian update is the simplest possible learning rule, not the most powerful.** Backprop-style credit assignment over rated walks would be more efficient, but requires differentiable composition primitives the HDC substrate doesn't currently expose. A1 stays in HDC arithmetic (additive update, multiplicative decay); future cycles may layer a more expressive rule.
3. **The Hebbian update is sensitive to α and λ hyperparameters.** Cold-start α=0 / λ=0.001 is defensible but uncalibrated. Cycle-15+ work needs an empirical sweep on a held-out probe set; without calibration the bank may either over-learn (memorise rated fragments verbatim) or under-learn (decay too fast for the audit signal to persist).
4. **A1 cannot replace `solve_quadratic` in any reasonable cycle count.** Even with 10⁶ rated worked-example walks, the substrate accumulating "quadratic-form prompts predict roots-style outputs" does not derive the closed-form discriminant formula — that's a symbolic-reasoning capability the HDC substrate has no path to today. F1 (hand-coded math) is a long-horizon strike; A1 is one step on a multi-cycle path, not the path itself.
5. **The audit-volume floor is real.** Cycle-15+ needs ~50-200 ratings before A1's gradient is informative. The lain-rating UI is shipped; the rating rate is the bottleneck. If lain doesn't rate ~10 walks per cycle, A1's bank stays empty and the substrate stays static. **A1 implicitly imports a soft dependency on lain's rating activity.**

## 8. Cycle-15 spillover (if A1 not picked as cycle-14 #1)

If the synthesis picks a different angle as cycle-14 #1, A1 belongs in cycle-15 as the architectural follow-up:

- The cycle-14 #1 ships its primary work (likely A2 evaluator-policy per the demo's F4 + F5 misroute evidence + the corpse's "biggest leverage" directive).
- Cycle-15's first task: A1 substrate writability + A3 credit assignment as a bundled ship, leveraging whatever audit-rating volume has accumulated by then.
- The cycle-14 emergence predicate (A5, if picked) would have generated the falsifiability surface for measuring whether A1 + A3 actually shift capability cycle-over-cycle.

A1 is high-priority regardless of cycle-14 #1 choice; deferring it more than one cycle leaves the substrate non-writable indefinitely.

---

*Single-line takeaway: A1 makes the substrate writable. It does not, by itself, make the agent measurably smarter this cycle — capability emerges over cycles 15-N as the audit signal accumulates. The strict-thesis case is strong (~30% on the thesis-fraction axis); the capability-lift case is weak (~15%); the combined-axis verdict puts A1 at ~25%, with A3 as the natural ship-mate.*
