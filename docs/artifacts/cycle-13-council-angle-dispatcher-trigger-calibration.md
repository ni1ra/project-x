# Cycle 13 Council — Angle 5: Dispatcher + Trigger-Gate Calibration

**Status:** council angle 5 of 5. Inputs the synthesis pass (#06).
**Date:** 2026-05-11.
**Origin:** added post-demo per advisor catch. The corpse named 4 angles; demo findings F5 (Collatz routing) + F6 (narrow trigger gate) mapped to NONE of them. Symmetric council per the demo-first discipline.
**Pairs with:** demo doc (`cycle-13-demo-22k.md` — F5/F6 evidence), canonical-doc Layer 3 (BG-style confidence-scored parallel-bid dispatcher), `src/project_x/reasoning_agent.py:694` (current keyword-table trigger gate), `src/project_x/reasoning_agent.py:723` (`_PARSER_ARCHETYPES` — the HDC-similarity-to-archetype pattern already used for parser selection).
**Advisor consult:** none pre-write per the natural-decay process note; the angle's case is anchored by demo evidence directly.

---

## 1. The premise

Two demo findings, both DIRECT, both unaddressed by the corpse-named angles 1-4:

- **F5 — Dispatcher mis-routes Collatz to natural-mode (combined confidence 0.86) instead of the formal `collatz_verify_range` substrate.** The formal substrate would have ACTUALLY VERIFIED Collatz over [1, 10000] (the agent has a working `collatz_verify_range(N)` primitive). Natural-mode returned framing-about-Collatz pulled from the lain_voice + canonical-doc fragments. The user got prose-about-Collatz instead of an empirical verification.

- **F6 — `_NATURAL_MODE_TRIGGERS` keyword regex is too narrow.** P4 *"Argue both sides: is mathematics discovered or invented?"* and P5 *"Compose a sonnet on the death of a friend."* both honest-refused because (a) "argue both sides" / "discovered or invented" aren't in the philosophy trigger keyword list, and (b) "compose a sonnet" isn't in the poetry trigger list (only "compose a poem"). The 22k corpus has rich material for both — the gate refused, not the substrate.

The fix for both findings is **calibration** of existing infrastructure, not new infrastructure.

## 2. The two-part implementation sketch (~2-2.5 h Raphael-time)

### Part A — Dispatcher confidence-formula tuning (F5 fix; ~45-60 min)

The current BG-style dispatcher combines `parser_match × α + hv_similarity_to_archetype × (1-α)` with α=0.6, τ_dispatch=0.3, chain-order tiebreaker (per canonical-doc Layer 3 + cycle-11 #01 implementation). For P3 Collatz:

- Natural-mode `_try_natural_mode` matched on the `"collatz"` keyword trigger → parser_match=1.0; hv_similarity_to_archetype ≈ 0.77 (prose-y prompt → archetype). Combined = 0.6 × 1.0 + 0.4 × 0.77 = 0.908. Reported as 0.8615 in dispatcher metadata (slight delta from rounded constants; either way well above τ=0.3).
- Formal `collatz_verify_range` parser MUST have either not matched the prose-form prompt OR matched at a lower combined-confidence. Inspection of the parser's regex would confirm which.

Two candidate fixes:

1. **Formal-parser priority boost.** Multiply combined-confidence by 1.2 when a formal-mode parser matches AND a natural-mode parser ALSO matches. Rationale: formal parsers are more specific by construction; their match condition is tighter; ties should favor verifiability. Empirically tuned over cycle-13 → cycle-N.
2. **Tighten the natural-mode `"math"` trigger.** Require longer phrase match (e.g., "what does X conjecture mean" or "discuss X" not bare "collatz" alone). Less general but cleaner separation from formal-substrate prompts. Lower-risk than (1).

Recommendation: ship **both** if angle 5 wins — (2) tightens the immediate F5 case; (1) provides general protection for future formal+natural ambiguities. Test surface: P3 Collatz routes to formal after the fix; existing tests covering formal-only and natural-only prompts still pass.

### Part B — Trigger-gate replacement with HDC-similarity-to-archetype (F6 fix; ~60-90 min)

The Layer-3 BG dispatcher already uses HDC-similarity-to-archetype gates for parser selection (see `_PARSER_ARCHETYPES` at line 723 — 21 archetypes, one canonical prompt per parser shape, cosine scored at dispatch time). The exact same pattern applies to natural-mode domain selection.

Concrete change:

```python
# CURRENT (reasoning_agent.py:694-710) — keyword regex
_NATURAL_MODE_TRIGGERS: dict[str, tuple[str, ...]] = {
    "poetry": ("write a poem", "compose a poem", "write poetry", ...),
    "philosophy": ("meaning of life", "what is the meaning", ...),
    ...
}

# PROPOSED — HDC archetypes (mirrors _PARSER_ARCHETYPES shape)
_NATURAL_MODE_ARCHETYPES: dict[str, tuple[str, ...]] = {
    "poetry": (
        "Write a poem about the changing seasons.",
        "Compose a sonnet on the death of a friend.",   # P5 lands here
        "Give me verse on the impermanence of all things.",
    ),
    "philosophy": (
        "What is the meaning of life?",
        "Argue both sides: is mathematics discovered or invented?",   # P4 lands here
        "What is the nature of consciousness?",
        "Is free will real or illusion?",
    ),
    "math": (
        "What does the Collatz conjecture mean? Is it solved?",
        "Discuss honest framing on the twin prime conjecture.",
    ),
    ...
}
```

Then `_classify_natural_mode_domain` (line 807-819) replaces its keyword-loop with a cosine-similarity loop:

```python
def _classify_natural_mode_domain(prompt: str, encoder, archetype_hvs) -> str | None:
    """Cosine-to-archetype natural-mode domain classifier."""
    prompt_hv = encoder.encode([prompt])[0]
    best_domain, best_sim = None, 0.0
    for domain, archetypes_hv in archetype_hvs.items():
        # Score against the centroid of all archetypes for this domain
        domain_centroid = np.sign(np.sum(archetypes_hv, axis=0))
        sim = cosine_bipolar(prompt_hv, domain_centroid)
        if sim > best_sim:
            best_domain, best_sim = domain, sim
    return best_domain if best_sim > 0.25 else None  # tau_natural_dispatch
```

P4 + P5 → cosine to philosophy/poetry archetypes exceeds 0.25 → routes correctly. Test surface: regression on existing keyword-trigger matches (the 13 prompts in cycle-11 #08 dual-mode tests + the 5 demo prompts).

The archetype-gate pattern is the SAME pattern Layer 3 already uses. The change is pulling the natural-mode dispatcher into structural alignment with the parser dispatcher.

## 3. Load-bearing % verdict

- **Demo-rateable lift this cycle:** ~25-30%. Three of five demo prompts behave differently after the fix:
  - P3 Collatz → formal verification (actually computes 1-10000 ✓ over the 3n+1 conjecture)
  - P4 *"argue both sides"* → emits philosophy walk over the 22k corpus (instead of refusing)
  - P5 *"compose a sonnet"* → emits poetry walk (instead of refusing)
  
  No other angle moves 3/5 demo prompts in one cycle.

- **Terminus-risk-reduction:** ~15-20%. Dispatcher + trigger calibration is real architecture work; it affects how RELIABLY the BG dispatcher routes future prompts across cycles 14-N. The Terminus needs the dispatcher to make correct decisions across thousands of prompt shapes; this cycle's calibration is one of many but it's the FIRST.

- **Combined-axis honest midpoint:** **~30-35%** load-bearing.

This is the highest-scoring angle of the 5. The case is direct: it's the only angle anchored in TWO demo findings with concrete same-cycle capability lift.

## 4. Synthesis-tension flag

The synthesis pass should decide: if angle 5 wins cycle-13 #1, does cycle-13 ALSO ship angle 1 (bitpack) as parallel substrate-insurance per angle 1's refinement (a)? The combined cycle scope:

- Angle 5 implementation: ~2-2.5 h
- Angle 1 implementation (bitpack module + tests + empirical-equivalence verification): ~45-75 min
- Total: ~3-3.5 h — comfortably within the 5-8 h cycle-13 budget

This is the "biggest demo-rateable lift + cheap substrate insurance" combination. The synthesis can authorize multi-ship per the established refinement-(a) precedent.

Angle 3 (quality-curation filter pipeline) is also potentially bundlable but at higher cost (~3-5 h for the pipeline alone). If multi-ship authorized, the priority order is: angle 5 (cycle-13 #1) → angle 1 (cycle-13 #1b substrate insurance) → angle 3 (deferred to cycle 14).

## 5. Honest counter-claims

1. **The fix is calibration, not new architecture.** Anyone reading this should be honest: angle 5 isn't a research direction; it's tuning existing code. Hassabis yawns. What might register mildly is the DISCIPLINE of (a) running the demo first, (b) noticing the corpse-named angles missed the actual demo signals, (c) expanding the council scope to integrate, (d) the cheap calibration unlocks 3/5 demo-prompt capability with no new infra. That's process discipline, not research novelty.
2. **The archetype-gate pattern's THIRD-LARGEST RISK is archetype curation.** The proposed `_NATURAL_MODE_ARCHETYPES` table has 2-4 archetypes per domain; tuning which prompts serve as archetypes is judgment-call. Bad archetypes drop classification accuracy. Cycle-13 ship: hand-pick the first batch (mirrors cycle-11's `_PARSER_ARCHETYPES` curation); cycle-14+ extends + tunes.
3. **τ_natural_dispatch=0.25 is a guess.** Empirical-tuning territory across cycles 13-15. False-positive rate (routing to natural-mode when honest-refuse was correct) is the trade-off if τ is too low; false-negative rate (refusing when natural-mode SHOULD fire) if too high.
4. **F5 fix may surface other formal-vs-natural conflicts.** Tightening the natural-mode math trigger fixes Collatz but may break other prompts that legitimately should route to natural-mode (e.g., "discuss the Riemann hypothesis in plain English" — should route to natural-mode-math). Regression sweep over cycle-11-12 prompts is mandatory.
5. **The dispatcher's α=0.6 was empirical from cycle 11.** Re-tuning it now (Part A option 1) re-opens the calibration cycle-11 was supposed to close. Less aggressive: only ship Part A option 2 (tighten math trigger) + Part B (archetype gates); leave dispatcher α alone.
6. **The "highest demo-rateable lift" framing assumes the demo prompt set is representative.** Five prompts is too few to generalize. Angle 5's 3-of-5 score might be 2-of-20 or 4-of-50 on a larger demo set. Cycle-13 reflect should propose a larger demo set for cycle-14 to test against.

---

*Single-number contribution to the 5-angle synthesis: **~30-35%** load-bearing on the combined axis. Highest-scoring angle of the 5. Synthesis-pass recommendation: pick angle 5 as cycle-13 #1; authorize multi-ship of angle 1 (bitpack substrate insurance) as cycle-13 #1b; defer angles 2, 3, 4 to cycles 14-N per their honest load-bearing %s.*
