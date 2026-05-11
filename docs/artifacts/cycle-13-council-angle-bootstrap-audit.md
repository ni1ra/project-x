# Cycle 13 Council — Angle 4: Consolidation Pass with Bootstrap Audit

**Status:** council angle 4 of 5. Inputs the synthesis pass (#06).
**Date:** 2026-05-11.
**Pairs with:** canonical-doc Layer 7 (consolidation pass spec), cycle-12 #02 audit UI v1 (`ae5dffc` — JSONL log + CLI rating tool + composer hook), demo doc (`cycle-13-demo-22k.md`).
**Advisor consult:** none pre-write per the natural-decay process note.

---

## 1. The premise

Canonical-doc Layer 7 specifies a surprise-biased perturb-audit-reweight consolidation pass: offline / overnight, pull bindings touched by surprising-recent rollouts ∪ bindings with recent audit revision, perturb each (1% bit-flip), score perturbations on retrieval-quality against audit-loop queries, replace or blend toward the higher-scoring perturbation. The mechanism merges four research angles (hippocampal selection + ES update + K-rollout candidate-surfacing + multi-temporal-Raphael temporal placement).

Cycle-12 #03 consolidation pass was **deferred** because the mechanism needs real audit signal — without ~50+ accumulated lain ratings, the "score by audit-loop queries" step has no data and the perturb-audit-reweight loop is tautological (noise injection).

**Bootstrap audit** asks: can we substitute a heuristic/simulated audit signal for real lain ratings, to fire Layer 7 NOW instead of waiting for rating accumulation?

Two candidate proxy rewards:

1. **Similarity-to-lain-voice-centroid.** Centroid hypervector of all `voice=lain`-tagged Tier-1 fragments (mini-seed + MANIFESTO + paper.md + Discord). Score each generated walk on cosine similarity from emitted-fragment-bundle to lain-centroid. High = "sounds like lain"; low = drifts away from lain's tone.
2. **Agreement-with-canonical-doc.** Cosine similarity to the centroid of the canonical-doc-rule fragments (M-PROJECTX-013 framing, honest-refusal patterns, organic-thesis statements). Score each walk on whether it respects architectural rules.

The consolidation pass then uses the proxy reward instead of real-rating retrieval-quality.

## 2. What the demo data adds

- **F4 lain_voice fragments retrieve appropriately on P3 (Collatz walk).** The math walk pulled M-PROJECTX-013 framing at step 2 (*"the substrate empirically verifies over [1, N]; the conjecture itself remains theoretically open. Process artifact, not capability artifact"*) and Collatz canonical framing at step 4. This is positive evidence that **the lain-voice corpus is rich enough to serve as a proxy reward**: lain-voice fragments are retrievable AND retrieve appropriately for context-relevant prompts.
- None of F1, F2, F3, F5, F6, F7 directly bear on Layer 7. Consolidation is an offline pass; demo data is a single-shot retrieval snapshot.

Demo coverage: 1 finding (F4) corroborates the bootstrap-audit feasibility premise. No findings refute. Lower coverage than angles 3 + 5; higher than angles 1 + 2.

## 3. Concrete implementation sketch (~2 h Raphael-time if angle 4 wins)

### Proxy reward functions

```python
def proxy_reward_lain_voice(walk_hv: np.ndarray, lain_centroid_hv: np.ndarray) -> float:
    """Cosine similarity from a walk's bundled fragment hypervector to the
    lain-voice centroid. Range [-1, 1]; positive = aligned with lain's voice."""
    return cosine_bipolar(walk_hv, lain_centroid_hv)

def proxy_reward_canonical(walk_hv: np.ndarray, canon_centroid_hv: np.ndarray) -> float:
    """Cosine similarity to the canonical-doc-rule centroid (M-PROJECTX-013 + organic-
    thesis + honest-refusal fragments). Range [-1, 1]; positive = walk respects
    canonical architectural rules."""
    return cosine_bipolar(walk_hv, canon_centroid_hv)
```

### Centroid construction

- Filter cycle-12 corpus for `voice=lain` tag (mini-seed `LAIN_VOICE_FRAGMENTS` + ~50 cycle-1-thru-12 added lain_voice entries). Encode each via `CharNgramHashEncoder.encode`. Bundle via `np.sign(np.sum(hvs, axis=0))` to get the centroid. ~50-150 lain_voice fragments → centroid is well-defined.
- Filter for canonical-doc-rule fragments (M-PROJECTX-013, M-PROJECTX-014, organic-thesis quotes). Same centroid construction. Smaller set (~20-40 fragments) but topically tight.

### Consolidation pass with proxy reward

1. Pull candidate bindings (start with K=20 most-recently-rotated bindings; tune over cycles).
2. For each binding: generate K=5 perturbations (1% bit-flip).
3. For each perturbation: replay the most-recent demo prompt(s) under the perturbed substrate; bundle the emitted walks; score under both proxy rewards.
4. Combined score = `0.6 * proxy_lain_voice + 0.4 * proxy_canonical`. (Weights are guesses; calibrate over cycles.)
5. Replace each binding's centroid with the highest-scoring perturbation IF that score exceeds the pre-perturbation score by margin > 0.02 (avoid noise-driven replacement).
6. Log every replacement to a "consolidation audit JSONL" — lets cycle-N+1 see what bindings shifted and roll back if a quality regression appears.

### Test surface

- 8-12 tests verifying (a) centroid construction is deterministic; (b) proxy reward range; (c) perturbation produces measurably-different walks; (d) replacement-margin guard prevents noise-driven replacement; (e) rollback path exists.

## 4. Load-bearing % verdict

- **Demo-rateable lift this cycle:** ~5-10%. Consolidation is an offline pass; the demo's same 5 prompts re-run AFTER consolidation might show measurable walk-quality shift, but the lift is bounded by how much the proxy reward correlates with actual capability improvement.
- **Terminus-risk-reduction:** ~15-20%. Layer 7 IS load-bearing for the Terminus (canonical-doc explicitly cites the consolidation pass as the offline maintenance loop that closes the audit feedback). Bootstrap audit unblocks Layer 7 firing NOW vs waiting for accumulated ratings. BUT: real-rating accumulation may not be slow — the cycle-12 #02 CLI tool ships ratings every time lain uses it. If accumulation is fast, bootstrap audit is bridge architecture that becomes obsolete in 2-3 cycles.
- **Bootstrap-tautology risk discount:** -5-10%. If the proxy reward correlates poorly with actual lain judgment, the consolidation pass drifts in a wrong direction. Without real ratings to calibrate against, this risk is genuine.
- **Combined-axis honest midpoint:** **~10-12%** load-bearing.

Third-lowest of the 5 angles (after angle 2 ~5-8% and angle 1 ~25%).

## 5. Synthesis-tension flag

The synthesis pass should hold this question explicitly: **how fast does real-rating accumulation actually go**? If lain rates 1-2 walks per Discord session, 50 ratings accumulate in 4-5 weeks of normal usage; bootstrap audit's value window is narrow. If real-rating accumulation requires multi-cycle focused effort (rating 50 walks in one session is taxing), bootstrap audit's value window is wider.

The honest cycle-13 framing: bootstrap audit is **insurance against rating-accumulation slowness**, not against architectural failure. The synthesis can reasonably defer it pending data on rating velocity (cycle-13 to cycle-15).

## 6. Honest counter-claims

1. **Proxy reward bias.** The lain-voice centroid is built from cycle 1-12 lain_voice fragments. If lain's voice evolves (cycle-N onward) and the centroid is fixed, the proxy rewards walks that sound like cycle-12-lain not current-lain. Drift-correction would need re-centering the centroid each cycle, adding maintenance.
2. **The canonical-doc agreement proxy is REFLEXIVE.** It scores walks against the architectural rules the architecture itself is built on. Consolidation toward higher canonical-doc agreement may produce walks that sound architecturally-coherent but are actually less useful as answers to user prompts. Calibration risk.
3. **The cycle-12 #02 CLI tool was just shipped.** No data on rating accumulation rate. The premise that bootstrap audit is needed rests on a guess about how fast real ratings will accumulate; this guess may be wrong in either direction.
4. **Layer 7 is itself unvalidated empirically.** Even with REAL ratings, the canonical-doc Layer 7 mechanism (perturb-audit-reweight) has not been tested. Bootstrap audit unblocks a mechanism whose first-principles soundness is well-argued but whose empirical behavior is unknown.
5. **The 0.6 lain-voice / 0.4 canonical weight split is arbitrary.** Across cycles the optimal weight depends on which proxy turns out to correlate better with actual lain judgment; calibration is multi-cycle.
6. **Cycle-13 ship at ~2 h** is honest only if centroid construction + proxy functions + perturbation loop + tests are all small. Realistic risk: the test surface expands when subtle correctness checks (margin guard, rollback) get fleshed out; could grow to 3-4 h.

---

*Single-number contribution to the 5-angle synthesis: **~10-12%** load-bearing on the combined axis. Third-lowest of the 5 angles. Synthesis-pass recommendation: defer to cycle-14+ unless rating-velocity data from cycles 13-15 shows real accumulation is genuinely slow; the value window is narrow and tautology risk is real.*
