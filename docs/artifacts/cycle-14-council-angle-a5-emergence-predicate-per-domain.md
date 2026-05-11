# Cycle 14 Council — Angle A5: Emergence-validation predicate per-domain

**Status:** council angle 5 of 5 — final cycle-14 council artifact. Feeds the synthesis pass (#07).
**Date:** 2026-05-11.
**Pairs with:** the demo doc (`cycle-14-demo-post-thesis.md`, commit `d89b90f`), A1/A2/A3/A4 angle notes (commits `a0babad` / `d40572d` / `b691961` / `743128b`), the cycle-13 predicate template (`docs/artifacts/cycle-13-primitive-emergence-at-scale.md` §§1-6 at hash `0b89101`), the cycle-13 result (the same doc §7 at hash `b673993` — 0/20 STRUCTURAL → NOT VALIDATED), and the cycle-14 synthesis verdict.
**Strict thesis lens:** A5 IS the measurement layer — it does not advance the strict-thesis fraction itself, but without it, every cycle re-litigates "did learning happen this cycle?" by post-hoc story-fitting. Cycle-13 demonstrated the predicate's value: 0/20 STRUCTURAL is a clean, falsifiable verdict against the canonical-doc Layer 5 claim, not a fuzzy "kinda emerged."

---

## 1. The proposal

The cycle-13 #07f-pre predicate (committed at hash `0b89101` BEFORE the emergence run) was a single-domain test: do k-means clusters on trigrams from the 22k Tier-2 corpus produce structural shells ("X is Y") at the ≥40% intra-cluster threshold + ≥30% structural-cluster threshold? The cycle-13 result at hash `b673993` was **0/20 STRUCTURAL** — clean, dispositive, NOT VALIDATED.

A5 generalizes this template to **per-domain capability metrics.** Each domain on the Terminus list (math / poetry / philosophy / physics / persona+humour / memory / always-on-chat) gets a pre-registered predicate that scores *"did the learned model acquire capability X this cycle?"* in a falsifiable way.

**Cycle-14 deliverable: 4-5 per-domain predicate templates, each ~150-250 lines of pre-registered scoring rules + falsifiability bands + the methodology + the shell-or-equivalent enumeration.** Each template ships as a separate doc under `docs/artifacts/cycle-14-predicate-<domain>.md`, mirroring the cycle-13 `cycle-13-primitive-emergence-at-scale.md` structure.

**Domain templates the cycle-14 demo's findings argue for:**

1. **Math predicate** — does the agent's math output on N held-out worked-example prompts (random sample from a generated math test set) match the closed-form answer? Falsifiability: per-prompt {correct numerically / partially correct / refused / confidently wrong}. Verdict bands: ≥80% correct = STRONG learning evidence; 30-80% = PARTIAL; <30% = NOT VALIDATED. Test set: 100 quadratic + ODE + integration prompts auto-generated from a parameter grid; held-out from the substrate's exposure during the rating UI.
2. **Poetry predicate** — does the agent generate (vs retrieve) on N poetry prompts? Falsifiability: for each emitted text, compute "novel-character-fraction" = `1 − max_overlap_with_corpus_fragments` (the fraction of output not directly traceable to a single corpus fragment). Verdict bands: ≥40% novel-character on average = STRONG generation evidence; 15-40% = PARTIAL; <15% = NOT VALIDATED (retrieval, not composition).
3. **Philosophy predicate** — does the agent argue (vs cite)? Falsifiability: for each emitted text on philosophy prompts, count the number of distinct positions argued + the presence of "X says Y because Z" structural markers vs the count of unattributed citations. Verdict bands: ≥2 positions/output + ≥1 reasoning chain = STRONG; 1 position + citation = PARTIAL; 0 positions = NOT VALIDATED (citation, not argument).
4. **Persona + humour predicate** — does the agent respond in-register on persona-shaped prompts + does it elicit a humour-signal on humour-shaped prompts? Subjective domain (M-PROJECTX-014 firewall applies — auto-grading impossible). Falsifiability deferred to external GPT/lain audit per the firewall; the predicate's job is to define the *rubric* (target register markers + humour-target signals) so the audit can be replayed cycle-over-cycle against a stable yardstick.
5. **Always-on chattability predicate** — does the agent respond appropriately to casual chat (greeting, follow-up question, topic-shift) vs misroute to math/poetry/philosophy? Falsifiability: 20 chat-shaped prompts; per-prompt {chat-domain-recognized / refused-honestly / misrouted}. Verdict bands: ≥80% chat-recognized = STRONG; 30-80% = PARTIAL; <30% = NOT VALIDATED.

In one sentence: *cycle-14 ships 4-5 per-domain predicates BEFORE the implementation cycle that builds the learning machinery, so the cycle-15+ machinery is measured against a yardstick that can't be retro-fit to the result.*

## 2. The pre-demo strict-thesis case

The strict thesis is a claim about HOW the model gets capable (learning from data + audit). A5 is the *measurement* that distinguishes "learning happened" from "we're telling ourselves a story." Cycle-13 demonstrated the cost of NOT having a predicate: cycles 11-12's "primitive emergence" framing produced shells in a 3k-trigram MVP and was carried as "the architecture works" through 5 cycles. Cycle-13's pre-registered predicate revealed the framing didn't survive scale-up: 0/20 STRUCTURAL at 10k trigrams = NOT VALIDATED.

A5 generalizes this discipline. Each cycle that ships A1/A2/A3/A4 implementation produces a deliverable that A5's predicates SCORE. Without A5, cycle-N+1 says "the substrate is composing now"; with A5, cycle-N+1 says "the poetry predicate scored 0.23 novel-character on the held-out test set vs 0.18 at cycle-N — PARTIAL learning evidence."

Strict-thesis fit: A5 IS LEARNING MACHINERY (predicate construction + scoring algorithm + falsifiability bands are hand-coded; the predicate's verdict on each cycle's deliverable is MEASURED, not learned). A5 adds no new MODEL KNOWLEDGE. It adds the measurement scaffolding without which the strict-thesis fraction "% learned / % hand-coded" is unmeasurable.

## 3. What the demo data adds (and what it does not)

Mapping A5 to the cycle-14 demo's 7 findings:

- **F1 (math hand-coded):** A5 DIRECT — the math predicate IS the measurement that would tell us, cycle-over-cycle, whether the strict-thesis-fraction shifts on math. Without it, "the agent learned to solve quadratics" is unverifiable.
- **F2 (cosine-archetype routes correctly):** A5 INDIRECT — chat predicate (5th) is the inverse measurement (did routing fail to recognize chat-shape?). F2's routing-success is what A5's chat predicate measures BY ITS ABSENCE.
- **F3 (retrieval ≠ composition):** A5 DIRECT — the poetry predicate's novel-character-fraction IS the cycle-over-cycle measurement of whether composition is emerging. P2/P3's retrieval-not-composition outcome would score ~0% novel on cycle-13; cycle-15+ implementation of A1 with sufficient ratings would shift this fraction if learning happened.
- **F4 (P4 humour misroutes):** A5 DIRECT — persona+humour predicate measures whether humour-shaped prompts elicit humour-shaped responses (vs misroutes to math). External audit per M-PROJECTX-014 firewall.
- **F5 (P5 chat misroutes):** A5 DIRECT — chat predicate (5th) directly measures the F5 failure mode.
- **F6 (strict-thesis fraction ~0%):** A5 is the ONLY angle that gives the "% learned vs % hand-coded" claim a falsifiable measurement. Without A5, the strict-thesis-fraction is a feeling, not a number.
- **F7 (cold-encoder latency):** A5 is ORTHOGONAL.

Net: A5 directly addresses 4 of 7 findings (F1, F3, F4, F5, F6) — by *measuring* them rather than *fixing* them. **A5 is the meta-angle**: it doesn't strike capability gaps; it scores whether the other angles' strikes landed. Its load-bearing-% comes from "cycles 15-N waste budget if they can't measure what they built." Cycle-13's 0/20 STRUCTURAL outcome is the canonical example of A5's value: a clean falsifiable verdict that prevented Layer 5 framing from staying inflated through cycles 14-N.

## 4. Implementation sketch (concrete enough for #07 cost estimate)

Per-domain predicate ships as a SEPARATE doc + SEPARATE scoring script. Cycle-14 v0 ships 4 domains (math + poetry + philosophy + chat); persona+humour predicate defers to cycle-15 (external-audit firewall requires more rubric work).

Per domain:
- New doc `docs/artifacts/cycle-14-predicate-<domain>.md` (~150-250 lines): the predicate text + falsifiability bands + the methodology + the test set spec.
- New script `scripts/cycle_14_predicate_<domain>.py` (~100-200 lines): generates the held-out test set deterministically (seed=42 per cycle-13 pattern); runs `ReasoningAgent.process()` on each prompt; scores per the predicate; emits the result block paste-ready for the doc.
- Test set: 20-100 prompts per domain (math = 100 auto-generated parameter-grid; poetry = 30 hand-curated diverse-target prompts; philosophy = 30 hand-curated diverse-frame prompts; chat = 20 chat-shaped utterances).
- Pre-registration commit hash: each predicate commits §§1-N at hash `H` BEFORE the cycle-N+1 implementation runs it; result block at §N+1 commits separately. Git history is the audit trail (per cycle-13 precedent).
- Tests `tests/test_predicates.py` (~150-200 lines, 8-12 tests):
  - Each per-domain scoring function is deterministic.
  - Each test set generator is seed-deterministic.
  - Each verdict-band threshold is documented + asserted.
  - Cycle-13 predicate template structural compatibility regression (the cycle-13 template at `0b89101` continues to score correctly).
- `docs/REPO_CONTROL.md` rows for 4 new docs + 4 new scripts.
- Cycle-14 atomic commits: `docs(P13c14-08-predicate-math)` + `docs(P13c14-08-predicate-poetry)` + `docs(P13c14-08-predicate-philosophy)` + `docs(P13c14-08-predicate-chat)` (4 atomic commits if A5 is cycle-14 #1).

Estimated cost: **~2 h Raphael-time per domain template = 6-8 h for 4 domains** (cycle-14 v0 scope). Persona+humour predicate deferred to cycle-15+. The full 5-domain pre-registration set is multi-cycle work, and A5's cycle-14 scope is realistically the first 3-4 domains.

Reproducibility: deterministic given seed; test sets re-generatable from the script.

## 5. The discriminating question for the synthesis pass

A5's score depends on **whether the synthesis values measurement infrastructure as cycle-14 #1 candidate.**

| Scoring axis | A5 score | Interpretation |
|---|---|---|
| **Biggest CAPABILITY lift this cycle** | ~5% (zero capability advancement — predicates SCORE capability, they don't BUILD it) | A1 / A2 / A4 win this axis decisively |
| **Biggest STRICT-THESIS-fraction shift** | ~10% (the strict-thesis fraction is unmeasurable WITHOUT A5; A5 makes it measurable but doesn't shift the number) | A2 wins this axis |
| **Biggest cycle-15-N infrastructure investment** | ~30-40% (cycles 15-N will use A5's predicates to grade their own deliverables; without A5, cycle-15+ deliverables are vibes-graded — same trap cycles 11-12 fell into before cycle-13's pre-registered predicate exposed Layer 5 NOT VALIDATED) | A5 is uniquely strong on this axis |
| **Combined multi-ship** | ~10-15% (bundled with a capability-axis angle; A5 doesn't compete for the cycle-14 #1 slot; it sits alongside) | Bundle A5 with whatever else ships |

The cycle-14 budget question: **is the cycle-14 #1 capability-shipping (A1/A2/A3 bundle, or A4) or infrastructure-shipping (A5)?** Two defensible reads:

- *Capability-first:* cycle-13 closed clean, audit shipped, demo measured the gaps. Cycle-14 should ship one of the model-side angles (most likely A2 or A2+A1) to actually MOVE the agent's capability cycle-over-cycle. A5 ships in cycle-15 as the measurement scaffolding for whatever capability cycle-14 produced.
- *Measurement-first:* cycle-13 demonstrated the cost of post-hoc framing on the Layer 5 claim. Cycle-14 #1 = ship A5 predicates BEFORE any A1/A2/A3 work, so cycle-15+ capability shipping has a yardstick to be graded against from the start. The strict-thesis-fraction becomes measurable.

The capability-first read aligns with lain's "biggest leverage work should be done first" directive (Discord msg 1503368472, cycle-14 trigger). The measurement-first read aligns with M-PROJECTX-013 (measure-don't-claim) and cycle-13's audit-of-self lesson.

## 6. Load-bearing % verdict (honest, axis-dependent)

- **On the "capability lift this cycle" axis:** A5 is ~5% load-bearing — lowest of the 5 angles.
- **On the "strict-thesis-fraction shift" axis:** A5 is ~10% load-bearing — makes the fraction measurable, doesn't shift it.
- **On the "cycle-15-N infrastructure investment" axis:** A5 is ~30-40% load-bearing — highest of the 5 angles on this axis.
- **On the "combined multi-ship" axis:** A5 is ~10-15% load-bearing when bundled.

**Single-number summary for the synthesis pass:** **~10-15% load-bearing**, lowest of the 5 angles on capability terms, but **uniquely strong on cycle-15-N infrastructure** — the synthesis should explicitly state whether infrastructure framing is in scope. The pre-demo informal estimate at the demo doc §6 was ~10%; the F1/F3/F4/F5/F6 measurement-coverage evidence keeps the number stable.

## 7. Honest counter-claims (M-PROJECTX-013 + M-PROJECTX-014)

1. **A5 is not a capability lift.** The predicate ships, the cycle-13 audit-pattern says "0/20 STRUCTURAL, NOT VALIDATED" or similar — cycle-14 ends with a measurement of what's broken, not a fix. lain's cycle-14 trigger said *"try moving the needle even further"*; A5 measures the needle, doesn't move it. The synthesis must surface this honestly.
2. **Predicate design has bias risk (M-PROJECTX-014).** The agent that designs the system can't write the rubric without bias. The cycle-13 predicate at `0b89101` was internally designed and externally untested before the run; the verdict (0/20) was honest, but the predicate's THRESHOLDS could have been chosen differently to produce a different verdict. Cycle-14 predicates should be peer-reviewed (lain + advisor) before pre-registration.
3. **Subjective-domain predicates depend on the external-audit firewall.** Persona+humour predicate IS the M-PROJECTX-014 case — auto-grading is structurally infeasible. The predicate's job is to define the RUBRIC; the GRADE comes from external audit. Without lain's audit cadence, the predicate measures nothing.
4. **Per-domain predicates are individually small; the value is in the set.** Math predicate alone gives us math-progress visibility but not strict-thesis-fraction visibility; the latter requires summing across all 5 domains. Cycle-14 v0 ships 3-4 predicates; the full set is multi-cycle.
5. **A5's value depends on running the predicate every cycle.** Cycle-13 ran its predicate ONCE; cycles 14-N would need to re-run it to measure drift. The cycle-14 implementation should include a "predicate replay harness" (similar to `gpt-codex/benchmark/run_audit.py` for auto-graded benchmarks) so cycles 15-N can flag with `--predicates` and get a verdict matrix automatically.
6. **The "% novel-character" metric for poetry has limits.** A truly composed line might overlap heavily with corpus diction (canonical metaphors, common imagery) without being retrieval; conversely, a retrieval that surfaces an unusual corpus fragment can have low max-overlap. Cycle-15+ work would refine the novelty metric to handle these edge cases. The cycle-14 v0 threshold (40% novel = STRONG) is a defensible first pass per cycle-13's "honest framing of where we actually are."
7. **A5 does not solve the cold-start audit-volume floor.** If cycle-15+ implements A1+A2+A3 with ~0 historical ratings, the cycle-15 predicate run will score the cold-start machinery (likely NOT VALIDATED), and the verdict will be "machinery shipped but the bank is empty." This is the right outcome — honest measurement is the point — but it doesn't FIX the audit-volume floor; it documents it.

## 8. Cycle-15 spillover (if A5 not picked this cycle)

If the synthesis defers A5:

- Cycle-14 ships capability work without predicates. Cycle-15's first task is A5 retrospective — design the predicates AFTER cycle-14's deliverable lands. The bias risk is HIGHER than pre-registration: predicate thresholds may be chosen to favorably grade cycle-14's outcome.
- Cycle-14 demo (this artifact) doubles as the "no-formal-predicate" cycle-14 measurement — 7 findings, counter-claims, honest framing, but not a falsifiable test.
- Risk: cycle-15's A5 work has to either (a) retro-fit predicates to cycle-14's deliverable (bias-risk) or (b) design predicates afresh and *also* re-run them against cycle-14's deliverable (more cycle-15 work).

The cleanest sequencing is: **predicates pre-register THIS cycle (cycle-14), implementation lands NEXT cycle (cycle-15), result block commits at cycle-15 close.** Mirrors cycle-13 #07f's pre-register-then-run pattern.

---

*Single-line takeaway: A5 measures, doesn't move. ~5-15% load-bearing on capability terms, ~30-40% on cycle-15-N infrastructure terms. The synthesis must explicitly choose whether cycle-14 #1 is capability-shipping or measurement-shipping — both reads are defensible; lain's "biggest leverage" directive tilts capability, M-PROJECTX-013 tilts measurement.*
