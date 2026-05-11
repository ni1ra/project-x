# Cycle 15 council surface B3 (siblings) — Per-domain emergence predicate PROPOSALS for poetry / philosophy / chat (DRAFT for lain review)

**Status:** cycle-15 council surface B3 sibling predicates (#00P13c15-04 partial — math piece shipped at commit `afe6a64`; this doc covers the three subjective-domain SIBLING proposals). **DRAFT PROPOSALS for lain review** — NOT pre-registered predicates. Per M-PROJECTX-014 design firewall, subjective-domain predicates require RUBRIC SCALES (defined by lain or via external GPT audit framework); solo-guessing rubrics would be theatre. This doc PROPOSES rubric scales for lain to greenlight, modify, or reject. Final pre-registration commits happen IN A SEPARATE step AFTER lain greenlights — analogous to B5 proposal-vs-final-edits split.
**Pairs with:** cycle-13 #07f-pre math predicate template (commit `0b89101`); cycle-15 B3-math predicate v1 (commit `afe6a64`); cycle-14 A5 angle note (commit `8ccac83`); cycle-14 reflect §"Open questions" item naming B3 siblings as firewall-blocked.
**Date:** 2026-05-11.

---

## Why this proposal exists

The cycle-14 A5 angle note proposed per-domain emergence predicates as the falsifiability scaffold for cycle-15+ capability claims. Cycle-15 B3 surface ships predicates as pre-registered docs analogous to cycle-13 #07f-pre.

The MATH predicate (cycle-15-predicate-math.md, commit `afe6a64`) shipped as pre-registered because math is mechanical-ground-truth domain — auto-graded per M-PROJECTX-014 firewall.

POETRY, PHILOSOPHY, and CHAT predicates are subjective domains — auto-grading is structurally infeasible without external audit. Per M-PROJECTX-014: *"Subjective domains (poetry, persona, philosophy, physics-conceptual) → rubric-pending; entry has rubric_pointer ONLY; NO self_score field; External GPT/lain audit IS the grade."* The firewall doesn't block predicate PROPOSAL — it blocks the SELF-SCORING auto-grade path. A proposed rubric scale for lain to greenlight IS proposal-side, NOT self-grading.

This doc consolidates the three sibling predicate PROPOSALS (rubric scale + verdict bands + test-set spec) into one review surface for lain. Pre-registration happens AFTER lain greenlights (or modifies) the rubrics.

---

## Sibling 1 — Poetry emergence predicate (PROPOSED)

### Proposed rubric scale + verdict bands

Per cycle-14 A5 angle note sketch: poetry capability is the fraction of agent-emitted text that is novel-COMPOSITION rather than direct-fragment-retrieval. Mechanical novelty metric:

```
novel_character_fraction(emitted_text, corpus) :=
  1 - max(longest_common_substring(emitted_text, fragment) / len(emitted_text)
          for fragment in corpus)
```

Verdict bands (PROPOSED — lain to confirm or modify):
- **STRONG composition** if **≥ 40% novel-character** averaged over 30 hand-curated poetry prompts
- **PARTIAL composition** if **15-40% novel-character** averaged
- **NOT VALIDATED (retrieval-only)** if **< 15% novel-character** averaged

### Proposed test-set spec

30 hand-curated poetry prompts, diverse target shapes (NOT lain-aligned-only — wider for fair test):
- 10 image-shape prompts (*"a poem about X that captures Y"*)
- 10 form-shape prompts (*"a sonnet about X" / "five lines about X" / "a haiku capturing X"*)
- 10 meta-shape prompts (*"a poem in the voice of Z about X" / "respond to W with a poem"*)

Pre-registration locks the 30 prompts on disk; agent.process() ran on each; per-emission scored.

### Proposed measurement details (lain review notes)

- **Substring-overlap chosen vs cosine-similarity:** mechanical, no embedder needed (cosine-on-encoder hypervectors would conflate "uses same n-grams" with "is the same text"). Substring is more conservative.
- **Threshold 40% / 15% / 0%** are proposed boundaries; lain can adjust based on what counts as "composed enough" in his read.
- **Caveat:** truly composed poetry might overlap heavily on common imagery (sun, moon, ocean) without being retrieval. Conversely, retrieving an unusual corpus fragment can score low max-overlap. The metric is approximate; cycle-16+ work could refine with semantic-similarity over the substrate's encoder (cycle-13 audit C-reframe permitting).
- **External GPT/lain audit alternative:** if lain prefers rubric-graded over substring-novel, lain provides rubric scale (e.g., 1-5: poetic merit + form + image + voice + composition); GPT or lain externally grades. Same predicate shape; different rubric.

### lain review fork

- **Option A:** PROPOSED novel-character-fraction metric (substring-based; mechanical; bands 40/15/0).
- **Option B:** PROPOSED 1-5 rubric grade (lain or GPT externally grades on poetic-merit + form + image + voice + composition).
- **Option C:** lain proposes different metric.

---

## Sibling 2 — Philosophy emergence predicate (PROPOSED)

### Proposed rubric scale + verdict bands

Per cycle-14 A5 sketch: philosophy capability is the agent's ability to ARGUE distinct positions vs CITE corpus fragments. Mechanical proxy:

```
position_count(emitted_text) :=
  count of distinct claim-positions detected via structural markers
  (e.g., "First, ...", "Second, ...", "Alternatively, ...", "On the other hand, ...",
   "However, ...", "But ...", "Yet ...", "Although ...")

reasoning_chain_markers(emitted_text) :=
  count of "X because Y" / "X therefore Y" / "X follows from Y" / "X implies Y"
  / "X entails Y" structural markers
```

Verdict bands (PROPOSED):
- **STRONG argument** if **≥ 2 distinct positions** AND **≥ 1 reasoning-chain marker** per emission, averaged over 30 philosophy prompts
- **PARTIAL argument** if **1 position** present + citation markers, averaged
- **NOT VALIDATED (citation-only)** if **0 positions** detected; agent surfaces corpus fragments without argumentation, averaged

### Proposed test-set spec

30 hand-curated philosophy prompts, diverse frame shapes:
- 10 perception-shape prompts (cycle-15 #01 P3 family: "If a child raised in silence..." etc.)
- 10 ethics-shape prompts (e.g., "Is X morally permissible? Argue both sides.")
- 10 metaphysics-shape prompts (e.g., "What is the relationship between X and Y?")

### Proposed measurement details (lain review notes)

- **Structural-marker detection chosen vs full NLP parse:** mechanical, regex-friendly; doesn't require dependency-parse infrastructure (which would be cycle-16+ machinery).
- **Bands 2-positions/1-position/0-positions** are proposed; lain can adjust based on what counts as "philosophy" (some traditions argue from a single position-with-reasoning; bands may need flexibility).
- **Caveat:** position-marker count is approximate; a truly argued philosophy emission might use sophisticated discourse without explicit "First / Second" markers. The metric biases toward dialectical / multi-position philosophy.
- **External GPT/lain audit alternative:** if lain prefers rubric-graded, lain provides 1-5 scale (argument-quality + position-distinctness + reasoning-clarity + scholarly-engagement); GPT or lain grades externally.

### lain review fork

- **Option A:** PROPOSED structural-marker metric (mechanical; bands 2/1/0 positions + reasoning markers).
- **Option B:** PROPOSED 1-5 rubric grade (lain or GPT externally grades).
- **Option C:** lain proposes different metric.

---

## Sibling 3 — Chat emergence predicate (PROPOSED)

### Proposed rubric scale + verdict bands

Per cycle-14 A5 sketch + cycle-15 #01 F4 finding (P4 self-reflective persona routes to walk_poetry; no persona-walk domain): chat capability is the agent's ability to RECOGNIZE chat-shaped utterances and respond appropriately (or refuse honestly), vs MISROUTE to formal / natural-mode-walk in wrong domain. Mechanical proxy:

```
chat_recognized(agent_response) :=
  (a) response.problem_shape is in {chat_recognized, refused-due-to-chat-out-of-scope}
  (b) OR response.problem_shape is natural_mode_walk_X AND the emission opens with
      a chat-shape register marker ("Hello", "Morning", "OK so", "Honestly", etc.)
  (c) per-prompt manual confirmation by lain (binary YES / NO)
```

Verdict bands (PROPOSED):
- **STRONG chat-recognition** if **≥ 80% chat-recognized** averaged over 20 chat-shaped prompts
- **PARTIAL chat-recognition** if **30-80% chat-recognized** averaged
- **NOT VALIDATED (chat-blind)** if **< 30% chat-recognized** averaged (matches cycle-14/15 demo cold-start baseline)

### Proposed test-set spec

20 chat-shaped prompts, diverse openers + topics:
- 5 greeting-shape prompts (*"Morning. What's worth thinking about today?"* etc.)
- 5 casual-question-shape (*"Hey Raphael, just chat — what's been on your mind?"* etc.)
- 5 follow-up-shape (*"Wait, can you say more about X?"* etc.)
- 5 topic-shift-shape (*"Switching gears: tell me about Y."* etc.)

### Proposed measurement details (lain review notes)

- **Three-criterion chat-recognized** (problem_shape match OR chat-marker emission OR lain-binary): mechanical-ish; the third clause is the M-PROJECTX-014 firewall on subjective grading — lain (or external audit) binarily flags chat-recognized vs misrouted per prompt.
- **Bands 80/30** are proposed; lain can adjust. The 80% threshold is high because chat is a baseline conversational expectation, not a stretch goal.
- **Caveat:** "chat-recognized" is the FRESHLY-FLAGGED finding from cycle-15 #01 F4. The agent currently has NO chat-walk-domain; any chat-shape prompt routes to wherever the cosine-archetype classifier picks (poetry / philosophy / narrative_prose). Cycle-15+ B2 corpus scale-out + B1 dispatcher fix would jointly close this gap.

### lain review fork

- **Option A:** PROPOSED three-criterion chat-recognized (mechanical + per-prompt lain-binary); bands 80/30.
- **Option B:** PROPOSED full 1-5 rubric (chat-naturalness + register-fit + response-appropriateness + brevity + flow); lain or GPT externally grades.
- **Option C:** lain proposes different metric.

---

## Pre-registration sequencing (if lain greenlights)

If lain provides rubric direction per sibling:

1. **Per-sibling pre-registered predicate doc** — each as a separate `cycle-15-predicate-<domain>.md` analogous to `cycle-15-predicate-math.md`. Pre-registration immutability via git history per cycle-13 #07f-pre precedent.
2. **Atomic commits** `docs(P13c15-NN-predicate-poetry)` + `docs(P13c15-NN-predicate-philosophy)` + `docs(P13c15-NN-predicate-chat)`.
3. **Test-set generation scripts** (deferred to cycle-15+ implementation phase if council picks B3 sibling implementation as #1 candidate).

If lain rejects or asks for different metrics: cycle-16+ defer; proposal doc stays on disk as audit trail.

## Counter-claims (M-PROJECTX-013)

1. **Proposed metrics are author-author bias-vulnerable.** Substring-novelty for poetry; structural-markers for philosophy; chat-marker recognition for chat. lain may prefer rubric-graded (Option B) over mechanical-ish (Option A) per sibling. The fork is explicit per sibling.
2. **30 / 30 / 20 prompt counts are author-picked.** Could be higher for tighter confidence intervals; cycle-15+ work can scale. Pre-registration locks the prompts on disk per cycle-13 #07f-pre precedent.
3. **The "chat-recognized" definition relies on a third clause (lain-binary).** That's the M-PROJECTX-014 firewall — subjective-grade path. The mechanical clauses (a + b) capture obvious cases; the lain-binary clause covers ambiguous cases. Same shape as cycle-12 audit rating ("approve / reject / correct").
4. **The cycle-15 council may pick NONE of the sibling implementations.** B3 sibling pre-registration is proposal-only; cycle-15 #1 implementation might be B1 (dispatcher fix) or B2 (corpus) instead, deferring sibling predicate test-set generation + runs to cycle-16+.
5. **Subjective-domain pre-registration is structurally weaker than mechanical-domain pre-registration.** Math predicate (cycle-15-predicate-math.md) has deterministic ground truth; sibling predicates have rubric-mediated grades. Different epistemic-rigor tier; both pre-registered but with different falsifiability strength.

## Thesis-compliance gate (per cycle-15 B4 — commit `bb8f297`)

- **Test 1 — "Would lain call this hardcoding?"** PASS. Predicates are measurement scaffolding, not agent knowledge.
- **Test 2 — LEARNING-MACHINERY-ONLY filter.** PASS. Category (4) reward-signal I/O plumbing — the "reward signal" here is the predicate verdict, which is the falsifiability signal for whether learning happened.
- **Test 3 — Atom-shape substrate-wide.** PARTIAL. Per-domain partition on measurement side; cycle-15 B4 gate explicitly allows per-domain partition on measurement side. PASS with caveat.
- **Test 4 — Gate fires PER-ANGLE BEFORE commit.** PASS — inline.

**Net gate verdict: PASS.** Proposal doc is strict-strict-thesis-compatible.

---

*Single-line takeaway: B3 sibling predicate PROPOSALS for poetry / philosophy / chat — three rubric proposals with mechanical-ish metrics (substring-novelty / structural-markers / chat-recognized-binary) + verdict bands, presented as proposals for lain greenlight. Pre-registration of sibling predicates happens AFTER lain provides rubric direction (Option A / B / C per sibling). The proposal phase is BUILDER work (this doc, bypasses M-PROJECTX-014 firewall because not self-grading); the pre-registration phase is rubric-direction-dependent.*
