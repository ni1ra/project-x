# Cycle 10 Semantics Architecture — Angle 3 (Intrinsic Curiosity)

**Status:** research note, not canonical. Feeds the #05e synthesis pass that overwrites the DRAFT.
**Date:** 2026-05-11.

---

## 1. Lain quote (verbatim source anchor)

> *"Humans also have an image curiosity, to WANT to understand the environment better, which is an instinct to keep ones kind to continue. Therefore we have natural curiosity..."*

— Msg `1503217035`, 2026-05-11 02:07 UTC.

> *"If a simulated (expected) result differs from the actual result (next item in a sequence) it should be surprised, it should want to understand concepts. That diff can be a training signal, maybe if it spends more resources on areas or spaces or high uncertainty and surprise, it should want to get to the bottom of it, maybe?"*

— Msg `1503219992`, 2026-05-11 02:19 UTC.

> *"So if you release it on the whole bench suite, it will WANT to solve it all, it tries different paths until it finally feels satisfied with itself. It must try to reduce uncertainty, but be honest when it doesn't know. Must be able to articulate itself fluently in at least English, in native language. Maybe the WANTing can be a hormone we control? Or that switches off when the queued given tasks are complete?"*

— Msg `1503219362`, 2026-05-11 02:17 UTC.

## 2. Advisor verdict (2-3 sentences)

This is the strongest concrete-mechanism angle of the four. The key insight is that **HDC obviates Pathak 2017's hardest engineering problem** — the inverse-model that learns a feature space — because HDC hypervectors *are* the feature space by construction, with cosine distance as the built-in similarity metric. The curiosity signal collapses to `1 - cos(predicted_hv, actual_hv)` with no learned-representation overhead, and lain's "WANTing as a controllable hormone" maps cleanly onto the v2 hormone-modulation architecture: `H_curiosity` is one register among many, raising retrieval thresholds when active and returning to baseline when queued tasks complete.

Net call: **~60-70% load-bearing.** The strongest angle of the four; the note is honestly longer than evolutionary's because there is more concrete mechanism to write down.

## 3. Literature integration — paper by paper

### Pathak et al. 2017 — *Curiosity-driven Exploration by Self-supervised Prediction* (ICML)

- **Core mechanism (forward model):** train a forward model to predict `phi(state_{t+1})` from `phi(state_t), action_t`; prediction error in feature space is the intrinsic reward signal.
- **The harder mechanism (inverse model):** learn `phi(·)` itself by training an inverse model to predict `action_t` from `(state_t, state_{t+1})`. This is what gives feature space the property of *encoding only action-relevant variance* — filtering out the "noisy TV problem" where an agent gets stuck staring at random pixels.
- **HDC translation candidate:** **The forward-model part maps directly.** The inverse-model part is *unnecessary*.
- **Why the inverse model is unnecessary in HDC:** hypervectors *are* the feature space, by construction. Cosine similarity is the built-in metric. Semantically-related concepts have high cosine similarity by the substrate's algebraic properties; unrelated noise has low similarity by random-projection orthogonality. There's no feature space to learn — the substrate ships it.
- **Verdict: load-bearing.** This is the strongest single mechanism in the angle. The HDC implementation is conceptually simpler than Pathak's because the hardest piece is solved by substrate choice.

### Burda et al. 2019 — *Exploration by Random Network Distillation* (ICLR)

- **Core mechanism:** A randomly-initialized target network produces fixed targets. A learnable predictor network is trained to match the target. Predictor's residual error on a state is the novelty signal: high error = unseen state.
- **Why RND works:** the predictor cannot perfectly match the target on novel inputs because it hasn't seen them yet; gradient updates close the gap on visited states, leaving residuals on unvisited ones.
- **HDC translation candidate:** Random hypervector projections as the "target," some HDC operation as the "predictor."
- **Why it doesn't transfer:** HDC random projections are *nearly-orthogonal by construction* across the substrate. There is no learning loop where a "predictor" closes a gap to a "target." The RND mechanism requires a learnable predictor whose residuals carry the novelty signal; HDC has no such layer. Forcing an analogue would either collapse to "everything is novel because random vectors are random" (no signal) or duplicate the substrate's similarity metric (rebranding).
- **Verdict: decoration.** Don't oversell RND in the synthesis. Pathak ICM is the load-bearing piece; RND is a citation, not a mechanism.

## 4. HDC translation (concrete mechanisms where they exist)

### 4a. Prediction-error-cosine-distance as the curiosity signal

```
At each step in a sequence-processing loop:
  1. Maintain an "expected next" hypervector hv_pred (from the agent's current
     working hypothesis about what should come next).
  2. When the actual-next-step lands, compute hv_actual.
  3. curiosity_signal = 1 - cos(hv_pred, hv_actual)
  4. If curiosity_signal > tau_surprise → flag this step as surprising.
     Allocate additional compute to concepts touched at this step.
```

- No learned feature-space, no inverse model, no extra network. The substrate provides everything.
- `tau_surprise` is the satisfaction threshold from lain's spec — empirical tuning loop, not closed-form. See section 5.

### 4b. H_curiosity hormone integration with v2 architecture

The DRAFT v2's hormone-modulation pattern applies a hormone vector to retrieval thresholds across subspaces. `H_curiosity` plugs in as one register:

```
H_curiosity active (high curiosity_signal detected, OR explicit WANTing):
  - Raise retrieval thresholds (more selective candidate bindings)
  - Permit more iterative rollouts (K-rollout, see 4c)
  - Allocate more compute per query
  - Bias retrieval toward concepts adjacent to surprising steps

H_curiosity inactive:
  - Return to baseline thresholds
  - Single-rollout per query
  - Standard compute budget
```

Activation logic: **`H_curiosity = active iff (recent curiosity_signal > tau_surprise) AND (queued_tasks non-empty)`** — matches lain's two specs (surprise triggers it; queued-task-completion ends it).

### 4c. Try-until-satisfied K-rollout loop

```
For a benchmark prompt with H_curiosity active:
  for k in 1..K_max:
    rollout_k = full HDC composition chain (different primitive choices)
    per_step_error_k = max curiosity_signal across the rollout's sequence
    if per_step_error_k < tau_satisfaction:
      emit rollout_k as the answer
      break
  else:  # all K_max rollouts failed to satisfy
    emit HONEST REFUSAL: "I tried K_max paths, none converged below threshold,
                          the genuine answer is I don't know yet."
```

- Preserves M-PROJECTX-013 cleanly: the agent does not overclaim. The curiosity drives EXPLORATION not OVERCLAIM.
- Compatible with v2's dual-mode composition (formal Lemma chain vs natural HDC walk): the K rollouts can be a mix of modes, with hormone state biasing which mode the next rollout takes.

### 4d. The "noisy TV" check (cross-ref)

Pathak's classic failure case: an agent encountering a TV showing static gets stuck because the static is unpredictable. Pathak's inverse model fixed this by making the feature space action-relevance-only.

HDC version of the check: if curiosity_signal stays high across many steps but no binding-quality improvement results (audit-loop score doesn't improve), then the "surprise" is uninformative noise, not signal. Mechanism: track a moving-average of `(curiosity_signal_t, audit_score_delta_t)`. If high curiosity correlates with zero audit-score-delta over a window → suppress further compute on that region. The substrate's compositional structure means this is a measurable signal, not just an architectural worry.

## 5. Load-bearing vs decoration verdict (single sentence + percentage)

**~60-70% load-bearing** — the Pathak-ICM forward-model mechanism plus the H_curiosity hormone integration plus the K-rollout-with-honest-refusal loop are three concrete pieces that compose into a coherent intrinsic-motivation layer; RND is decoration; the satisfaction-threshold calibration is an empirical tuning loop (open problem, not a solved primitive) that the cycle-11+ work will need to converge on. **The mechanism is real; the calibration is the honest open question.**

## 6. Decision points for #05e synthesis (numbered for copy-paste)

1. **Primary curiosity signal: `1 - cos(hv_predicted, hv_actual)`.** No learned feature space; no inverse model; no extra network. HDC substrate provides everything Pathak's hardest engineering work would have needed. State this as a LOAD-BEARING SIMPLIFICATION over Pathak's full ICM in the synthesis doc.

2. **`H_curiosity` is one of the hormones in v2's hormone-modulation architecture.** Active when (recent curiosity_signal > tau_surprise) AND (queued_tasks non-empty). Modulates retrieval thresholds + iterative-rollout permission + compute allocation. Inactive otherwise.

3. **Hormone deactivates on queued-task completion** — preserves resource budget against perpetual exploration. This is lain's "switches off when the queued given tasks are complete" spec.

4. **Try-until-satisfied = K-rollout with per-step-error tracking.** Emit the first rollout whose per-step max-curiosity-signal falls below `tau_satisfaction`. If all K fail → **HONEST REFUSAL** ("I tried K paths, none converged, I don't know yet"). M-PROJECTX-013 preserved.

5. **Reject RND-style mechanism.** HDC random projections are orthogonal by construction; no learnable predictor closes a gap to a target. Cite RND as a literature reference, not a mechanism.

6. **The "noisy TV" check has an HDC analogue.** Moving-average of `(curiosity_signal, audit_score_delta)` over a window; high-signal + zero-delta → suppress further compute on the region. Pathak needed an inverse model to filter noise; HDC needs this windowed correlation check.

7. **Open question (NOT a solved primitive): `tau_surprise` and `tau_satisfaction` calibration.** Empirical tuning loop in cycle-11+. State this honestly as a cycle-11 deliverable, not as a closed-form pre-derivation.

8. **English-fluency floor belongs elsewhere.** Lain's "must articulate fluently in at least English" is a quality bar on the output-surface-assembly path, not the curiosity mechanism. Synthesis pass should place this in the corpus-shape / surface-assembly section, not the curiosity section. `[cross-ref: corpus-shape decision in synthesis]`

9. **Cross-link to angle 2 (evolutionary) maintenance pass.** The K-rollout loop produces variant compositions; the ES-style perturb-audit-reweight pass from angle 2 could refine the bindings touched by surprising rollouts. This is one architectural piece viewed from two lenses, not two separate mechanisms — synthesis should merge.

10. **Cross-link to angle 1 (brain subsystems, scheduled last).** Hippocampal replay is the natural neurobiological substrate for the consolidation pass that angle 2 identified and that the K-rollout's surprising-region tracking would feed. Three angles describe the same architectural piece (consolidation / replay / refinement); synthesis must merge them into ONE decision point, not triple-count.

---

## Sources

- Pathak, D. et al. *Curiosity-driven Exploration by Self-supervised Prediction*. ICML 2017 (arXiv:1705.05363).
- Burda, Y. et al. *Exploration by Random Network Distillation*. ICLR 2019 (arXiv:1810.12894).
- Advisor consult, cycle 10 #05b turn (auto-forwarded transcript).
- Lain Discord msgs `1503217035` + `1503219362` + `1503219992`, 2026-05-11 02:07–02:19 UTC.
- DRAFT: `docs/artifacts/cycle-10-semantics-architecture.md` (status: DRAFT-PRELIMINARY).
- Research plan: `docs/artifacts/cycle-10-semantics-research-plan.md`, § Angle 3.
- Cross-references to angle-2 evolutionary note: `docs/artifacts/cycle-10-semantics-angle-evolutionary.md` (commit `4133eaa`).
