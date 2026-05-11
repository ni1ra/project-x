# Cycle 13 #06 — Priority Decision (Synthesis Pass)

**Status:** synthesis pass over the 5 council angles. Names cycle-13 #1 (winner) + cycle-13 #1b (bundle). Gates the cycle-13 #07 implementation.
**Date:** 2026-05-11.
**Pairs with:** demo doc (`cycle-13-demo-22k.md` commits `e4272ac` + `69dec02`), 5 angle notes (`cycle-13-council-angle-*.md` commits `6aaedad` / `fc2b51d` / `43ffaa4` / `800deed` / `c9e5401`), canonical architecture (`cycle-10-semantics-architecture.md`), cycle-12 close (`b352231`).
**Advisor consult:** one pre-write round (4 sharpenings integrated: axis-as-value-judgment, implementation-order flip, gate-permeability asterisk, a3 OUT-not-stretch).

---

## 1. The verdict

- **Cycle-13 #1 (substrate insurance, ships first):** Angle 1 — bitpack + emergence-at-scale.
- **Cycle-13 #1b (capability calibration, ships second):** Angle 5 — dispatcher + trigger-gate calibration.
- **Cycle-13 defers (cycle-14 front-of-queue):** Angle 3 — quality-curation filter pipeline.
- **Cycle-13 defers (cycle-15+ research window):** Angle 2 — variable-resolution HDC.
- **Cycle-13 defers (cycle-14+ pending rating-velocity data):** Angle 4 — bootstrap audit.

Total cycle-13 implementation budget: **~3-3.5 h Raphael-time** (45-75 min bitpack + 2-2.5 h dispatcher calibration). Comfortably inside the 5-8 h cycle budget, leaving headroom for the cycle-13 reflect ritual and any unexpected debug surface.

## 2. The 5-angle load-bearing % table

| Angle | Combined-axis % | Demo-anchor | Implementation cost | Cycle-13 disposition |
|---|---|---|---|---|
| a5 dispatcher + trigger calibration | **~30-35%** | F5 + F6 direct | ~2-2.5 h | **WINNER — #1b** |
| a1 bitpack + emergence-at-scale | **~25%** | none direct (substrate insurance) | ~45-75 min + ~60-90 min emergence run | **BUNDLE — #1 (ships first)** |
| a3 quality-curation filter + scale push | ~22% | F7 direct + F3 partial | ~2-3 h filter; multi-cycle scale | **DEFER — cycle 14 front-of-queue** |
| a4 bootstrap-audit consolidation | ~11% | F4 corroborates | ~2-3 h | **DEFER — cycle 14+ pending rating velocity** |
| a2 variable-resolution HDC | ~6% | zero | ~3-4 h | **DEFER — cycle 15+ research window** |

Sum: ~96% (asymmetric loading honored per cycle-10 precedent; angles get honest scores, not forced 25/25/25/12.5/12.5 splits).

## 3. Why combined-axis scoring (value judgment, stated explicitly)

The synthesis commits to **combined-axis** scoring (mid-point of demo-rateable lift + Terminus-risk reduction) rather than picking either axis alone.

This is a **value judgment**, not a mechanical derivation. The case:

- Under **demo-rateable-only** axis: a5 wins (~30%), a1 drops to ~15-20% (no demo lift), a3 ~10-15%. Cycle-13 #1 = a5 alone; a1 defers to cycle-14.
- Under **Terminus-risk-only** axis: a1 wins (~35-45% per angle-1 §5), a3 ~25-30%, a5 ~15-20%. Cycle-13 #1 = a1 alone; a5 defers.
- Under **combined** axis: a5 (~32%) > a1 (~25%) > a3 (~22%) > a4 (~11%) > a2 (~6%). Top two are bundlable under the multi-ship refinement.

**Why combined wins as the synthesis rule:** cycle-13's 5-8 h budget affords multi-ship of the top-2 ranked angles. Combined-axis picks the demo-rateable winner (a5) with substrate insurance (a1) bundled in — structurally cheaper than committing to one axis alone and forcing a false choice. Future-Raphael reading this doc can reconstruct the rule: the synthesis weighed *"both axes matter; combined-axis honors both without forcing a false single-axis pick when budget allows bundling."*

If cycle-13's budget had been tight (~2 h only), the synthesis would have been forced to pick one axis and one winner. The budget permits the better outcome.

## 4. Implementation order: a1 first, a5 second (advisor sharpening)

The naive ordering "winner first, bundle second" would ship a5 (cycle-13 #1) before a1 (#1b). The synthesis **inverts this** for variance-management reasons:

- **a1 is low-variance.** Bitpack is pure mathematical equivalence — `pack_bipolar` / `unpack_bipolar` / `cosine_packed` per the design doc spec (`e9b64cc`). The empirical-equivalence test (`abs(cosine_bipolar(a, b) - cosine_packed(pack(a), pack(b))) < 1e-9`) either passes or fails deterministically; debug surface is bounded.
- **a5 is higher-variance.** Archetype curation is judgment-call (per a5 §5 counter-claim #2: "false-positive rate vs false-negative rate trade-off if τ_natural_dispatch is wrong"); the existing-prompt regression sweep is mandatory because the trigger-gate change touches every prompt that ever invoked natural mode. If a5 ships first and breaks dispatcher routing on cycle-11-12 prompts, the debugging eats time that should be writing bitpack.

**Land the low-variance ship first.** Bitpack lands clean. Dispatcher calibration then ships against a stable substrate; if dispatcher regressions surface, the bitpack work is already committed and won't be touched while a5 stabilizes. **Implementation order: a1 → a5.** The "winner" framing labels which angle the cycle is FOR; the implementation order labels which angle ships FIRST to manage variance.

## 5. What a5's "3/5 demo prompts change behavior" actually means (gate-permeability asterisk)

The Discord midpoint update and the angle-5 note framed a5's load-bearing in terms of "3/5 demo prompts behave differently after the fix." This is mathematically true but rhetorically heavier than the underlying mechanism. **Stated cleanly:**

- a5 fixes **GATE PERMEABILITY** — which prompts can route through the dispatcher at all. P3 routes to formal substrate (instead of natural-mode); P4 + P5 route to natural-mode (instead of refusal).
- a5 does **NOT lift CAPABILITY DEPTH** — the quality of the emitted walks for prompts already routing through natural-mode is unchanged. The substrate (22k corpus + K-rollout + cosine retrieval) is identical post-fix.

P4 and P5 will emit walks of EQUIVALENT quality to P1 + P2 (~5 Whitman fragments or ~5 Plato+Emerson fragments at avg_sim 0.18-0.35). Their walks will not be "answers" any more than P1 or P2 were "poetry" or "philosophy" — they will be surface-similar corpus retrievals with cited provenance. The qualitative reading: **turning refusals into walks of equivalent quality to existing walks is gate permeability, not capability depth.**

The 32% load-bearing on the combined axis is honest. But the read shouldn't be "cycle-13 produces poetry / philosophy." The read should be: "cycle-13 fixes the dispatcher and gate so the substrate's existing capability (loose corpus retrieval with honest provenance) is reachable by a wider class of prompts." Capability depth is cycle-14+ work (angle 3 corpus scaling + angle 1 emergence-at-scale + future cycles' generation-not-just-retrieval architecture).

## 6. Why a3 defers OUT (not "stretch")

A3 (quality-curation filter pipeline) is the third-highest scoring angle (~22%). Initial verdict drafts hedged it as "cycle-13 #1c stretch if budget permits." Advisor sharpening: commit IN or OUT cleanly; "stretch" breaks the atomic-commit-at-cycle-level discipline.

**Commit: OUT.** Reasoning:

- a5 alone hits the high-variance ceiling (archetype curation + regression sweep). Bundling a3's filter pipeline (5-stage filter — semantic dedup + register classifier + length normalizer + diversity quota + register-clarity predicate; each stage has tuning judgment-calls) adds a SECOND judgment-call surface to the same cycle.
- Cycle-13 a1 + a5 ships clean at ~3-3.5 h, leaves ~2-4 h of budget for cycle-13 reflect + any unexpected debug surface + Discord cycle-close. Comfortable.
- a3 cycle-13-scope (filter pipeline + 10-15 new works) was already mostly slow-burn — full Layer-6 scaling is multi-cycle anyway. Front-of-queue cycle-14 means a3 ships within ~5 days.

**Result:** cycle-13 ships TWO atomic implementation commits (a1 + a5) plus the cycle-13 reflect close commit. Three judgment-call-heavy deliverables compounding in one cycle is the trap; defer a3 cleanly.

## 7. Cycle-13 #07 implementation contract (handoff to next task)

The synthesis hands #07 a concrete contract. Sharpen-todos at the #08→#07 boundary will split #09 into sub-tasks; this section is the source of truth.

### #07 ship-shape

| Order | Sub-task | Scope | Cost | Atomic commit |
|---|---|---|---|---|
| 1 | **#07a bitpack module** | `src/project_x/hdc_infra/__init__.py` + `bitpack.py` (~120-200 lines): `pack_bipolar` / `unpack_bipolar` / `cosine_packed`. Constraint D % 32 == 0 → bump default D from 10000 to 10240 OR 9984; pick one in implementation. | 30-45 min | `feat(P13c13-07a-bitpack-module)` |
| 2 | **#07b bitpack tests** | `tests/test_bitpack.py` (~150 lines, 12-20 tests): empirical-equivalence `< 1e-9` at D=10240; edge cases at D=32/64/96/128; pad convention; antipodal + all-ones trivials; D-not-divisible-by-32 raises ValueError. | 20-30 min | `feat(P13c13-07b-bitpack-tests)` |
| 3 | **#07c encoder shim** | `src/project_x/experiments/encoder.py` gains `encode_packed` method (~20 lines); REPO_CONTROL.md row for new `hdc_infra/` package co-landed in commit. | 10-15 min | `feat(P13c13-07c-encoder-shim)` (or bundle into #07a if small) |
| 4 | **#07d dispatcher Part A** | `src/project_x/reasoning_agent.py`: formal-parser priority boost (1.2x combined-confidence when both formal + natural-mode match) + tighten natural-mode "math" trigger to require longer phrase match. Tests covering F5 fix (P3 routes to formal). | 45-60 min | `feat(P13c13-07d-dispatcher-formal-boost)` |
| 5 | **#07e trigger archetypes Part B** | `src/project_x/reasoning_agent.py`: `_NATURAL_MODE_ARCHETYPES` table (mirrors `_PARSER_ARCHETYPES` shape; ~2-4 archetypes per natural-mode domain); replace `_classify_natural_mode_domain` with cosine-to-archetype-centroid; τ_natural_dispatch=0.25 (empirical, will tune cycles 14-15). Tests covering F6 fix (P4 + P5 route correctly) + regression on cycle-11-12 natural-mode prompts. | 60-90 min | `feat(P13c13-07e-trigger-archetypes)` |
| 6 | **#07f emergence-at-scale RUN** | Run `run_primitive_emergence` with `packed=True` on the 22k-fragment corpus's ~80k unique trigrams (per `cycle-13-bitpack-design.md` §3.3). Document empirical result: structural shells vs frequency rankings. Outputs `docs/artifacts/cycle-13-primitive-emergence-at-scale.md`. | 60-90 min (compute time may dominate) | `docs(P13c13-07f-emergence-at-scale)` |

Total: ~4-5 h Raphael-time including the emergence run. The 3-3.5 h estimate covered a1+a5 implementation; the emergence run adds 60-90 min and is the empirical test the cycle-13 #1 PREREQUISITE existed for. If the emergence run blows budget (k-means at 80k trigrams may be slow even packed), document the run-state + continue past cycle close.

### Mechanical proof gates

- pytest passes at the new baseline (current 596; expect +20-40 with bitpack + dispatcher tests).
- bench-replay --agent-runtime stays 48/0 (no regressions).
- bench-replay frozen stays 46/0 (parity).
- Demo prompts 1-5 re-run post-#07: P3 routes formal (verification computed for [1, 10000]); P4 + P5 emit philosophy / poetry walks; P1 + P2 unchanged behavior.
- `git status -s` clean post each atomic commit.
- REPO_CONTROL.md row for `src/project_x/hdc_infra/` package co-lands with the package commit.

## 8. Honest counter-claims

1. **The verdict's structural honesty depends on the demo being representative.** Five prompts is too few to generalize the 5-angle scoring. Angle-5's score might be 2-of-20 or 4-of-50 on a larger demo set. Cycle-13 reflect (#08) should propose a 15-20-prompt demo set for cycle-14 to test against.
2. **a1 + a5 combined is still incremental.** The Terminus needs super-human capability across math + poetry + philosophy + physics + persona + always-on + sandbox. Cycle-13 a1+a5 ships dispatcher calibration + substrate insurance + Layer-5 empirical validation. Net move toward Terminus is real but small — this is the cycle-1-of-N reality.
3. **The "land a1 first to manage variance" argument assumes a5 has the higher variance.** If bitpack's per-bit-majority-vote centroid update has a subtle bug (the design doc §3.3 acknowledges it as "the load-bearing care-point"), bitpack debugging eats the variance budget too. Both have variance; a5 has MORE.
4. **Deferring a3 to cycle 14 assumes cycle 14 exists and runs.** A multi-cycle plan is a commitment that can break (lain reprioritizes; rate limits; physics failures). a3's filter pipeline could die deferred forever. Mitigation: cycle-13 reflect (#08) explicitly carries a3 to cycle-14 scope with the verdict cited.
5. **The combined-axis pick is a SOFT win for a5.** On Terminus-only axis a1 wins. The synthesis's choice of combined-axis is defensible but not forced; a different value-call (more Terminus-weighted) would invert the order. Honest framing: a5 wins by ~7 percentage points on combined-axis (32 vs 25); not a blowout.
6. **The emergence-at-scale RUN (#07f) is the cycle-12 deferred work.** Including it in cycle-13 closes a deferral; if the run reveals frequency rankings instead of structural shells, the canonical-doc Layer 5 claim takes a hit and cycle-14+ planning shifts. The cycle-13 reflect (#08) must own this potential outcome.

---

## 9. The single-paragraph verdict (for cycle-13 reflect citation)

The 5-angle council, informed by the demo data, scores Angle 5 (dispatcher + trigger calibration, ~32%) as cycle-13 #1's capability winner and Angle 1 (bitpack + emergence-at-scale, ~25%) as its substrate-insurance bundle. The synthesis commits to combined-axis scoring as an explicit value judgment (cycle-13's budget affords multi-ship; combined-axis avoids forcing a false single-axis pick). Implementation order inverts the winner-first naive order: low-variance Angle 1 lands first, higher-variance Angle 5 ships against the stabilized substrate. Angle 3's quality-curation defers cleanly OUT to cycle-14 front-of-queue; Angles 2 and 4 defer to cycle-15+. Angle 5's lift is honest gate-permeability (which prompts can route) not capability depth (the quality of routed walks). The cycle-13 #07 implementation contract (§7) hands six sub-tasks totaling ~4-5 h Raphael-time including the cycle-12-deferred emergence-at-scale RUN.
