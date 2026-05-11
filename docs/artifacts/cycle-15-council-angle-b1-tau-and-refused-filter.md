# Cycle 15 council angle B1 — per-domain τ_satisfaction + BG-dispatcher refused-candidate filter (paired)

**Status:** cycle-15 council surface B1. Pairs cycle-14 #08e deferred-with-two-findings: the per-domain τ_satisfaction calibration + the latent 4-cycle-old BG-dispatcher refused-candidate-competition bug. Cycle-15 #01 demo (commit `c197bbd`) re-confirmed the bug's mechanism on a different domain (F3: P5 saturation via missing-archetype default to `hv_sim=1.0`).
**Date:** 2026-05-11.
**Pairs with:** cycle-14 synthesis verdict §7 #08e (commit `9b1f8fd`), cycle-14 #08e deferred-with-finding commit (`2f2e803`), cycle-15 #01 demo (`c197bbd`) F1+F3, cycle-15 B4 thesis-compliance gate (`bb8f297`).

---

## 1. The proposal (paired ship)

Cycle-14 #08e attempted to raise `_K_ROLLOUT_TAU` from 0.0 to 0.20 + immediately surfaced two findings: (a) avg-cosine is not a quality discriminator across cycle-13 + cycle-14 regimes (good cycle-13 framing walks ~0.17 sit in the same band as cycle-14 misroutes 0.19-0.20), and (b) a latent 4-cycle-old BG-dispatcher bug where refused natural-mode candidates compete at `combined_confidence ≈ 1.0` (no archetype for `_refused_*` problem_shape → `hv_sim_normalized` defaults to 1.0) and beat formal candidates.

Cycle-15 B1 proposes a **paired ship**:

### Half 1 — BG-dispatcher refused-candidate filter (bug fix, R1/R2-independent)

At `reasoning_agent.py:process()` line ~1117-1138 (the candidate-collection loop): exclude any AgentResponse with `confidence='refused'` from the `candidates` list BEFORE the combined-confidence sort. The refused branch is the explicit "I-don't-match" signal; emitting a competing candidate at hv_sim_normalized=1.0 default was a latent bug for 4 cycles (cycle-13 audit B5's τ=0.0 masked it; cycle-14 #08e's τ-raise surfaced it).

Generalize: candidates whose problem_shape has NO archetype in `_PARSER_ARCHETYPES` should EITHER (a) be excluded, OR (b) hv_sim_normalized default to 0.5 (neutral) rather than 1.0 (saturated). Cycle-15 #01 F3 (P5 saturation on `natural_mode_walk_narrative_prose` via missing-archetype default to 1.0) demonstrates this is a GENERAL pattern, not just for refused branches.

**Two failure shapes resolved:**
- Refused natural-mode candidates no longer beat legitimately-high-confidence formal candidates (cycle-14 #08e finding 2).
- Missing-archetype candidates no longer saturate combined_confidence at 1.0 regardless of actual prompt cosine (cycle-15 #01 F3 finding).

### Half 2 — Per-domain τ_satisfaction calibration (R2-dependent; defers if R1 picked)

If lain confirms R2 transition reading, cycle-15 ships per-domain `τ_satisfaction` calibration over the rated audit log (when accumulated). Per-domain replaces the failed global-τ attempt at cycle-14 #08e. Calibration via empirical sweep per domain: math walks typically score higher cosines (focused vocab); poetry/philosophy spread wider; chat (cycle-14 demo P5) currently has no domain. Per-domain τ values are scalars (calibration constants, parallel to learning_rate + decay).

If R1 (rip dispatcher entirely): per-domain τ becomes moot because the formal-vs-natural-mode dispatcher no longer exists; everything routes through bank-blended retrieval directly. Half 1 (refused-filter) still ships as the cleanup before retirement.

## 2. What cycle-14 #08e deferral surfaced (re-stated)

Two substantive findings cycle-14 #08e contributed despite being deferred:

- **F1 (cycle-14 #08e):** avg-cosine is not a quality discriminator. Collatz framing-walks (cycle-13 desired, ~0.17) and cycle-14 misroutes (P4/P5, 0.19-0.20) sit in the same cosine band. No global τ separates them.
- **F2 (cycle-14 #08e):** latent 4-cycle-old BG-dispatcher bug — refused candidates compete at `combined_confidence ≈ 1.0`. Cycle-15 #01 F3 (P5 saturation) is the SAME mechanism re-surfaced on a different domain (missing-archetype default).

B1's two halves close both. Half 1 (refused-filter, generalized) closes F2 + F3 generally. Half 2 (per-domain τ) closes F1 — by replacing the failed global-τ with calibration over the rated audit log + bank-blend that's now the quality discriminator.

## 3. What cycle-15 #01 demo data adds

Re-confirms the cycle-14 #08e F2 finding on a different domain (F3 P5 saturation). Strengthens the case for Half 1 generalizing beyond refused branches to any missing-archetype candidate.

Cycle-15 #01 F1 (formal `pendulum_period` parser bypassed on prose form) is RELATED but a DIFFERENT mechanism — that's a parser-prose-form-miss, not a refused-candidate-competition. B1 doesn't fix F1 directly; cycle-13 #07d (Collatz prose-form parser extension) is the analogue precedent for fixing F1 via parser-regex extension, NOT via B1.

## 4. The strict-strict-thesis case

Per cycle-15 B4 thesis-compliance gate:

- **Test 1 — "Would lain call this hardcoding?"** PASS for Half 1 (refused-candidate filter is plumbing — a missing-archetype-default check that doesn't add knowledge); BORDERLINE for Half 2 per-domain τ. Per-domain τ values are calibration scalars; lain may or may not call them "hardcoding." Mitigation: Half 2 sources τ values FROM rated audit data (not author-picked), making per-domain values learned-from-data; the "per-domain partition" itself is structural. Council should be explicit: is the partition "math vs poetry" hand-coded (FAIL) or "what the cosine-archetype classifier outputs at runtime as domain" (PASS — emergent)?
- **Test 2 — LEARNING-MACHINERY-ONLY filter.** Half 1 PASS (category 4 plumbing — missing-archetype-default-1.0 check). Half 2 PARTIAL — per-domain τ values are calibration constants (parallel to learning_rate; analogous to substrate-arithmetic tuning per cycle-14 synthesis §8 counter-claim #8). PASS with explicit framing.
- **Test 3 — Atom-shape substrate-wide.** Half 1 PASS (no new state). Half 2 PARTIAL — per-domain τ is `dict[domain, float]`, which IS per-domain partition. But "domain" here is the cosine-archetype classifier's OUTPUT (emergent at runtime, not authored hand-picked list); the partition is over classifier outputs, not over substrate atoms. PASS with caveat (cycle-14 reflect §"Architectural tensions" #2 explicitly named per-domain τ as cycle-15 path; the partition is borderline but defensible).
- **Test 4 — Gate fires PER-ANGLE BEFORE commit.** PASS — this section is inline.

**Net gate verdict: PASS (with explicit framing of Half 2's per-domain partition as classifier-output-partition, NOT hand-coded-domain-list).** Cycle-15 council should adjudicate the borderline framing at synthesis.

## 5. Load-bearing % verdict (axis-dependent)

| Scoring axis | B1 score | Plausible cycle-15 #1 |
|---|---|---|
| **Biggest CAPABILITY lift this cycle** | ~35% — closes cycle-14 #08e deferred-finding + cycle-15 #01 F3 directly; the refused-candidate filter is a real bug fix lain can SEE in cycle-15 demo re-run | B1 wins |
| **Biggest STRICT-thesis-fraction shift** | ~10-15% — Half 1 doesn't shift the fraction (plumbing); Half 2's per-domain τ depends on framing-of-domain-as-emergent-vs-hand-coded | A1-style work would win, but no new cycle-15 substrate-side angle that passes the thesis-compliance gate is on the surface |
| **Biggest cycle-16-N infrastructure investment** | ~25% — closes the calibration-debt; cycle-16+ work builds atop calibrated dispatcher | B2 (corpus) wins this axis |
| **Combined multi-ship** | ~30% — bundled with B2 corpus, ~40-45% combined (corpus + calibrated dispatcher together produce measurable cycle-15-demo-rerun lift) | B1 + B2 paired |

**Single number for synthesis: ~30-35% combined-axis.** Highest of the 5 cycle-15 angle proposals on the capability-this-cycle axis. The refused-candidate filter is the most-actionable bug fix the cycle-15 demo data identifies; per-domain τ closes cycle-14's deferred-with-findings.

## 6. Implementation sketch (sub-task split if cycle-15 council picks B1 as #1)

### Half 1 — refused-candidate filter (R1/R2-independent; 1-2h Raphael-time)

- `src/project_x/reasoning_agent.py:process()` modify: at line ~1117-1138 candidate-collection loop, add `if response.confidence == 'refused': continue` filter. Also: when looking up `archetype_hv = self._archetype_hvs.get(response.problem_shape)`, if `archetype_hv is None`, default `hv_sim_normalized = 0.5` (neutral) rather than 1.0 (saturated).
- Tests: 4-6 new tests covering (a) refused natural-mode + high-confidence formal → formal wins; (b) missing-archetype response + cosine-matched formal → formal wins; (c) cycle-13 audit B5 regression (existing tau=0.0 behavior preserved); (d) cycle-14 #08e demo-prompt regression (P4 humour, P5 chat with their cycle-14 walks).
- Cycle-14 demo re-run: cold-start should still match cycle-14 #08f Arm A; with Half 1 active, P4/P5 likely STILL route to walk_math / walk_poetry (the cosine-archetype classifier doesn't change; only the dispatcher's tiebreaker logic does). The refused-filter affects different prompts than cycle-14 demo's; cycle-15 #01 F3 (P5 saturation) DOES change — that's the visible improvement.
- Atomic commit: `feat(P13c15-NN-refused-candidate-filter)`.

### Half 2 — per-domain τ calibration (R2-dependent; 2-3h Raphael-time IF rated audit log has enough data)

- Requires accumulated rated audit data (at least ~50 ratings spread across domains). Cycle-15 capability-lift-IF-rating-cadence-meets-floor is contingent on lain rating activity.
- `src/project_x/reasoning_agent.py:1231` `_K_ROLLOUT_TAU: float = 0.0` → `_K_ROLLOUT_TAU: dict[str, float] = {'math': X, 'poetry': Y, 'philosophy': Z, 'narrative_prose': W, 'chat': V}`. Per-domain values calibrated by sweep over rated audit data (script that reads `data/audit_log/walks.jsonl`'s rated walks, groups by domain, finds the cosine-band that separates approve-rated from reject-rated walks).
- Calibration script: `scripts/cycle_15_tau_calibration.py` (new) — reads audit log, outputs per-domain τ values, plot per-domain cosine distribution.
- Tests: 3-4 new tests covering (a) per-domain τ dictionary lookup; (b) refusal triggered at correct per-domain threshold; (c) calibration script reproducibility.
- Atomic commits: `feat(P13c15-NN-per-domain-tau-storage)` + `feat(P13c15-NN-tau-calibration-script)`.

**Total Half 1 + Half 2: 3-5h Raphael-time + audit-data-dependence on Half 2.** If audit-data insufficient at cycle-15 time, Half 2 ships Half-2-PARTIAL with τ values set to identical 0.20 across domains (cycle-14 #08e's failed value) + Half 1's refused-filter makes the 0.20 floor actually behave correctly (refused-natural-mode no longer competes; formal candidates win on their merit).

## 7. Honest counter-claims (M-PROJECTX-013)

1. **Half 1 alone produces visible capability lift; Half 2 alone produces no lift without audit data.** Half 1 fixes a 4-cycle-old bug — cycle-15-demo-rerun on P4/P5 prompts (cycle-14 misroutes) should show formal candidates winning where they previously lost to refused-natural-mode. Visible. Half 2 ships substrate that CAN learn from rated walks but capability lift waits on rating cadence — same dependency as cycle-14 A1 substrate-writability ship.
2. **The "per-domain" framing of Half 2 is borderline under the strict-strict-thesis gate.** Per Test 1+3+caveat: if "domain" means the hand-coded domain list (`{math, poetry, philosophy, narrative_prose, lain_voice}`), it's per-tool partition (FAIL). If "domain" means the cosine-archetype classifier's runtime output (`_classify_natural_mode_domain` returns), it's classifier-output-partition (PASS). Council should be EXPLICIT — the cycle-14 mid-synthesis catch lesson is that "permissive gates admit hand-coded structure." Half 2's framing must clarify.
3. **The refused-filter generalization to missing-archetype-default-0.5 changes cycle-14 demo cold-start behavior on P5.** P5 currently routes to `natural_mode_walk_narrative_prose` at combined_confidence=1.0 (no archetype, defaults to 1.0). With Half 1's generalization, P5's combined_confidence drops to 0.5+... wait, let me check. Actually the hv_sim_normalized default to 0.5 would mean combined_confidence = α·1.0 + (1−α)·0.5 = 0.6·1.0 + 0.4·0.5 = 0.8 (assuming α=0.6 per existing dispatcher constants). So P5's combined_confidence drops from 1.0 to ~0.8 — still above τ_dispatch=0.3, still emits. The visible change: cycle-15 demo re-run shows P5 at combined_confidence 0.8 instead of 1.0. Not a behavioral change in routing.
4. **The 4-cycle-old bug is "latent" because the refused branch never fired at τ=0.0.** Half 1 ships even though the bug is currently masked. Justification: cycle-15 #01 F3 (P5 saturation via missing-archetype default to 1.0) demonstrates the GENERAL mechanism is currently active (not just on refused branches; on any missing-archetype). Half 1 fixes a currently-active failure, not just a latent one.
5. **Half 2's per-domain calibration requires audit rating cadence we don't have.** If lain doesn't rate cycle-13/14/15-demo walks (or new walks generated during cycle-15+), the rated audit log stays at ~0 rated entries, and the calibration sweep has no data. Half 2 ships per-domain STRUCTURE that supports calibration; ACTUAL calibration waits.

## 8. Cycle-16+ spillover (if B1 not picked as cycle-15 #1)

If cycle-15 synthesis picks B2 (corpus) instead:

- B1 Half 1 (refused-filter + missing-archetype-default-0.5) is small enough to bundle as cycle-15 #2 ship alongside B2. ~1-2h Raphael-time. Closes the 4-cycle-old bug regardless.
- B1 Half 2 (per-domain τ) defers to cycle-16+ when audit data accumulates.

If cycle-15 synthesis picks B3-implementation (per-domain emergence predicates) — assuming sibling predicates ship after lain provides rubric:

- B1 defers to cycle-16; the B3 predicate runs scored against the post-B1 agent would surface the latent bug's effects directly, justifying the cycle-16 B1 ship empirically.

## 9. Single-paragraph verdict (for cycle-15 synthesis citation)

B1 pairs the BG-dispatcher refused-candidate-filter (Half 1, R1/R2-independent bug fix; closes cycle-14 #08e finding 2 + generalizes to cycle-15 #01 F3 via missing-archetype default to 0.5 rather than 1.0) with per-domain τ_satisfaction calibration (Half 2, R2-dependent; closes cycle-14 #08e finding 1 by replacing failed global-τ with rated-audit-driven per-domain values). Half 1 produces visible cycle-15-demo-rerun capability lift on missing-archetype saturation cases; Half 2 ships calibration STRUCTURE awaiting accumulated audit data. Thesis-compliance gate PASS for Half 1; Half 2 BORDERLINE on per-domain partition framing (council must adjudicate "hand-coded domain list" vs "classifier-output partition"). Load-bearing axis: ~35% capability-this-cycle (highest of 5 cycle-15 angles), ~30% combined-multi-ship bundled with B2 corpus. Cost: 1-2h Half 1 + 2-3h Half 2 = 3-5h Raphael-time. **Synthesis recommendation:** B1 Half 1 ships cycle-15 #1 regardless of R1/R2 (it's a bug fix); Half 2 ships under R2 transition reading; under R1 (rip dispatcher), Half 2 becomes moot because the dispatcher's τ stops existing.

---

## Thesis-compliance gate (per cycle-15 B4 — commit `bb8f297`)

- **Test 1 — "Would lain call this hardcoding?"** Half 1: PASS (plumbing). Half 2: BORDERLINE (per-domain partition is borderline; mitigated by sourcing τ values from rated audit data, but the partition itself is structural).
- **Test 2 — LEARNING-MACHINERY-ONLY filter.** Half 1: PASS (category 4). Half 2: PARTIAL — per-domain τ values are calibration scalars (parallel to learning_rate; cycle-14 §8 counter-claim #8 precedent). PASS with explicit framing.
- **Test 3 — Atom-shape substrate-wide.** Half 1: PASS (no new state). Half 2: PARTIAL — `dict[domain, float]` IS partition, but "domain" is the classifier's runtime output, not authored list. PASS with caveat; council adjudicates.
- **Test 4 — Gate fires PER-ANGLE BEFORE commit.** PASS — inline.

**Net gate verdict: PASS (with explicit Half 2 framing required at synthesis).** B1 ships cycle-15 council deliberation; Half 1 ships regardless of R1/R2; Half 2's framing is the load-bearing council question.

---

*Single-line takeaway: B1 paired ship — refused-candidate filter (R1/R2-independent bug fix; closes cycle-14 #08e finding 2 + cycle-15 #01 F3) + per-domain τ calibration (R2-dependent; closes cycle-14 #08e finding 1). ~35% capability-this-cycle axis (highest of 5 angles); ~30% combined-bundle with B2. Cost 3-5h. Half 2's per-domain framing is the load-bearing thesis-compliance question for cycle-15 synthesis adjudication.*
