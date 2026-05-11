# Cycle 10 — Semantics / Text-Generation Architecture

**Brainstorm requested:** lain 2026-05-11 (mid-NotebookLM-listen of `docs/paper.md`).

**Quote:** *"Use the council skill and brainstorm elegant ways to do this. I'd assume utilizing the hyperdimensional space in some way would be the way. Like something that would make you go 'aaaaah of course!'"* + *"How are we supposed to do poetry, physics, astrophysics, everyday convo, have it take actions on my PC like you can etc. you need to find a smart solution here."*

**The gap (real, not polish):** The current architecture has **zero free-form text generation**. All "natural language" output the agent produces today is either:
- (a) BUILDER-authored frozen `raphael_response` text in benchmark entries (not generated; hand-written).
- (b) `Lemma.render()` — structured proof-shape: `Notice. Step 1 — discriminant: D = 256. Step 2 — sqrt: ...`. This is template-rendered, not generated.

Neither writes a haiku. Neither answers an open philosophy question in natural prose. Neither chats. Neither takes agentic actions on a user's machine. The paper's Chapter 9 baseline-grades of 1.2-1.3 / 5 on poetry/philosophy are a SYMPTOM; the root cause is we never built generation machinery.

**Constraint set (binding):**
- NO pretrained transformer at any load-bearing layer (organic-thesis, lain 2026-05-09).
- The architecture must compose with HDC memory + fact-graph + Lemma substrate already shipped.
- Honest framing per M-PROJECTX-013 + M-PROJECTX-014: every output is auditable; honest refusal when out of scope.
- Goal: one unified architecture spans poetry, physics-natural-language, everyday conversation, agentic action-taking.

---

## Five candidate architectures

Advisor-pre-loaded; analyzed for fit against the constraints. Ranked by elegance + likelihood of an "aaaah of course" reaction from a senior architect who's read the paper.

### Candidate 1 — Binding-based composition

**Mechanism:** Generate by superposing role-filler bindings (subject ⊗ noun + verb ⊗ action + …) into a single hypervector, then unbind into surface form via a decoder over a learned-but-organic codebook of phrase-vectors.

**Native HDC use:** maximum. Binding (⊗) and superposition (+) are the canonical HDC operations.

**What it CAN do:** generate compositionally — express novel role-filler combinations. Strong for "fill-in-the-blank" patterns.

**What it CAN'T do:** stand alone. "Unbind to surface" produces a vector, not text. Still needs a vector → text mapping, which is exactly what candidate 3 solves. So this isn't a complete architecture; it's a sub-mechanism within others.

**Verdict:** half-architecture. Use as a building block, not a standalone path.

### Candidate 2 — Cleanup-memory-as-generator (Markov + HDC indexing)

**Mechanism:** Bundle context vectors → query the HDC accumulator for nearest stored n-grams or phrases → stitch via overlap into output text.

**Native HDC use:** as indexing infrastructure for an n-gram model. The HDC similarity replaces a hash table.

**What it CAN do:** produce locally fluent text matching the training corpus's style. Easy to train (just write text into the HDC accumulator with token-window context).

**What it CAN'T do:** generalize beyond the corpus. Requires a training corpus — and "trained on what?" is the question. If we train on the open Web, we approximate a transformer's outputs via Markov chains; this defeats the thesis-spirit even if technically not a transformer. If we train on lain's writing, we ape his style without him present. Cleanup-memory is also brittle on n-gram boundaries (the stitching produces non-grammatical seams).

**Verdict:** technically tractable, aesthetically wrong. Doesn't generalize to physics, agentic action. Not the "of course." Markov chains are the 1948 path, not the 2026 one.

### Candidate 3 — Inverse-encoder

**Mechanism:** The cycle-9 encoder maps text → hypervector via character-n-gram hashing + Hebbian co-occurrence. Train (or hand-design) an INVERSE mapping vector → text. The hashing direction is many-to-one (multiple texts map to nearby vectors); the inverse is therefore probabilistic and requires search/scoring.

**Native HDC use:** moderate. The encoder is HDC; the inverse traverses the same space.

**What it CAN do:** in principle, decode any vector that lies near a known concept back into text. Re-uses infrastructure we already shipped.

**What it CAN'T do:** be deterministic. Inversion is lossy by construction — n-gram hashing collides on purpose (that's what makes it work as a similarity metric). The inverse needs a scoring function ("which of the candidates that decode to this vector is most plausible?") and that scoring function tends to want a language model, which we can't use. Could fall back to corpus-search-by-similarity, which collapses back into candidate 2.

**Verdict:** elegant in theory, intractable without a corpus or a scorer. The "of course" reaction would shift to "of course we can't actually invert it without bringing back the thing we're avoiding."

### Candidate 4 — Concept-graph-walking + template-fill

**Mechanism:** The fact-graph stores (subject, relation, object) triples + HDC-bound concept vectors. Generation traverses the graph along discourse-coherent paths (informed by HDC similarity to the current context), filling template slots with the visited concepts.

**Native HDC use:** moderate-high. HDC for similarity-driven traversal; binding for slot-filling.

**What it CAN do:** produce grounded, citable text. Every claim traces back to a fact-graph triple. Honest-refusal is trivial — if the path runs out, the system stops generating mid-stream and emits a documented refusal.

**What it CAN'T do:** generate fluently. Templates are templates; the seams show. Poetry needs more than slot-filling. Conversation needs improvised acknowledgement, not pre-templated. Action-taking needs imperative templates (`call_tool(name, params)`) which work but feel mechanical.

**Verdict:** good for QA-style explanation (physics, philosophy at the textbook level). Bad for poetry, conversation, action-taking specifically. Doesn't generalize across all four use cases lain named.

### Candidate 5 — Composition-of-substrate-primitives (the "aaaah of course" path)

**Mechanism:** Treat text generation as a `Lemma` chain where each step emits a domain-typed output via a primitive (e.g., `state_premise(x)`, `name_invariant(x, y)`, `close_with_affirmative(x)` for math; `emit_couplet(theme, meter)`, `emit_image(sense, domain)` for poetry; `emit_tool_call(intent, params)` for action). The `Lemma.render()` we already use IS the text generator; we've just only built mathematical primitives so far. Adding non-mathematical primitives — each one a hand-rolled template generator with HDC-typed slots — extends the same architecture to all four target domains.

**Native HDC use:** moderate. HDC drives **slot-filling** (each primitive's slots are typed by HDC concept similarity; the slot for "image associated with grief" returns whichever hypervector is closest to the grief-concept's stored neighbors) and **planning** (which primitive comes next is selected by HDC-similarity-between-context-and-primitive-purpose).

**What it CAN do across the four use cases:**
- **Poetry:** primitives like `emit_image_via_sense(theme, sense)`, `emit_caesura()`, `emit_volta(stance_before, stance_after)`. The composer picks primitives that produce a 5-7-5 haiku, an English sonnet's 14-line structure with volta at line 9, a villanelle's 19-line repetition pattern. Slot-filling uses HDC similarity for "image associated with theme."
- **Physics-natural-language:** primitives like `state_law(formula)`, `emit_analogy(known_domain, target)`, `name_regime(condition)`, `name_limiting_case(parameter)`. Compose into an explanation that walks from the law → analogy → regime → boundary.
- **Everyday conversation:** primitives like `emit_acknowledgement(sentiment)`, `emit_followup_question(topic, granularity)`, `emit_clarification_request(ambiguity)`, `emit_brief_opinion(topic, stance)`. Composer is driven by conversation state.
- **Agentic action-taking:** primitives like `emit_intent(verb, object)`, `emit_tool_call(tool_name, params)`, `emit_outcome_observation(result)`, `emit_followup_intent(if_clause)`. The composer is the plan; tool_call primitives invoke the sandbox layer cycle 1 already shipped.

**What it CAN'T do:** produce GPT-fluency. Templates are templates; the prose will read structured, not improvised. Voice gravitates toward Raphael's declarative-analytical register (which is fine — that IS the agent's identity). Poetry will be more structured than free-form; haiku and sonnet shapes will land cleaner than 12-line free verse. Cannot improvise truly novel phrases — only compose from primitive vocabulary.

**Native HDC role:** slot-filling + planning. HDC's binding/similarity become the runtime mechanism for "which content goes in this slot" and "which primitive comes next."

**Verdict:** the "aaaah of course" candidate. **We already have text generation.** It's `Lemma.render()`. We've built only mathematical primitives. Add primitives across the other domains and the same architecture handles them. No new architecture class. The existing dispatcher pattern (regex → primitive) extends naturally — natural-language prompts route to a planner that selects primitives + composes them via Lemma chain → renders.

The elegance: **the Lemma is the unit of cognition**, and Lemma rendering IS already text generation. We just don't see it that way because cycle 2-9 only added math primitives. The constraint set + the unified-architecture goal + the HDC-native slot/plan mechanism + the M-PROJECTX-013 honest-refusal pattern all fall out of extending what already exists.

---

## Recommendation: candidate 5

**Why it wins on aesthetic ("aaaah of course"):**

The realization isn't "build something new." It's "what you already built IS the generator; you've just been narrow about the primitive library." That's the elegant reframing. Lain's "I'd assume HDC would be the way" intuition is satisfied: HDC does slot-filling and planning, not surface generation per se — and that's the right division of labor.

**Why it wins on engineering:**

- No new substrate class. Lemma + DerivationStep + render() already exist.
- Continuous with the dispatcher pattern. Add a "natural-language planner" branch that, given a free-form prompt, identifies the target domain (poetry / physics / chat / action) and dispatches to a composer that picks primitives for that domain.
- Honest-refusal is native. No primitive fits → refusal with reason (same shape as Pell refusing on indefinite-non-Pell forms).
- Predicate-strength uniformity extends: each new primitive ships with its own algorithmically-independent verifier (or honest scope-boundary doc) per cycle 10 #1's discipline.

**Why it loses (the honest counter-claim):**

- Output WILL read structured, not fluent. Raphael's voice is declarative-analytical by design — that fits chat + physics + actions naturally, but poetry will be more "primitive-composed" than "natural-flowing." Free verse will feel templated.
- The primitive library has to be HAND-BUILT for each domain. Poetry alone needs maybe 20-30 primitives (image, sense, meter, caesura, volta, ...); building them is real work over multiple cycles.
- A truly novel image or phrase ("the cherry blossoms scattered like ink across the pond") can only be assembled from primitive vocabulary — never coined from nothing.

**Honest scope, lain-facing:** this architecture is good for "competent" text across all four domains, not for "human-frontier-creative" text. A frontier-level haiku written by a published poet would still beat what this produces. But (a) competent-and-honest beats fluent-and-confabulating, which is the wider thesis, and (b) the SUBSTRATE doesn't need to be human-frontier to be the architecturally-correct path; the human-frontier sits on top of the substrate via cycle-11+ primitive expansion.

---

## Smallest shippable primitive — demo proposal

Pick ONE domain and ship the smallest primitive that demonstrates the architectural pattern is real and composable.

**Recommendation: `compose_haiku(theme: str) → Lemma`**. Why:
1. Poetry is the most contested domain (lain explicitly noted 1.2/5 baseline). Demonstrating non-trivial improvement here matters most.
2. Haiku has STRUCTURE — 5-7-5 syllable count, seasonal reference, juxtaposition — so it's not arbitrary free-form; the primitives can be small and the structural constraints provide a verifiable rubric.
3. The HDC slot-filling is exercised cleanly: pick a SENSE primitive (sight / sound / touch) based on theme; pick an IMAGE associated with that sense in the HDC concept space; pick a CONTRAST image that creates the juxtaposition.

**Primitive sub-decomposition** (each a stand-alone function returning a typed slot value):

- `_pick_sense_for_theme(theme: str) -> Sense` — HDC similarity to themed sense-concepts; deterministic given encoder + memory.
- `_pick_image_for_sense_and_theme(sense, theme) -> Image` — HDC search in the concept-graph for image-typed vectors near (sense ⊗ theme).
- `_pick_contrast_image(image: Image) -> Image` — image with HIGH semantic distance to the seed image (still in concept space).
- `_format_5_7_5(image_a, image_b) -> str` — surface-form rendering with syllable-counted line breaks. Templates per image-typed slot.
- `compose_haiku(theme: str) -> Lemma` — composes the above as a 4-step Lemma chain; renders as Raphael-voice with the haiku as `actual_value` and the structural choices as `derivation_steps`.

**Ladder entry candidate:** `poetry-008` (after the existing poetry-001..007): "Write a haiku on the theme of loss using internal seasonal reference. Honor 5-7-5 syllabification." Auto-graded portion: syllable count exactly 5/7/5; theme-image semantic similarity above a threshold; seasonal reference word from a curated list. Rubric portion: aesthetic quality (split-grading firewall per M-PROJECTX-014 — lain or external grader, not the agent).

**Implementation cost estimate (cycle 11 #1 candidate):** ~90 min Raphael-time. New file `src/project_x/composition/poetry.py` + helper-primitive imports from existing reasoning substrate + 8-10 tests + REPO_CONTROL row + ladder entry.

---

## Discriminating use cases — what each candidate handles

| Use case | C1 binding | C2 cleanup-mem | C3 inverse-enc | C4 graph-walk | **C5 prim-compose** |
|---|---|---|---|---|---|
| Poetry (haiku, sonnet, free verse) | partial | weak | poor | weak | **good for structured forms; honest about free-verse limits** |
| Physics-natural-language explanation | weak | poor | poor | strong | **strong (extends existing math substrate naturally)** |
| Everyday conversation | weak | medium | weak | weak | **good (small primitives compose; Raphael-voice fits)** |
| Agentic action-taking | weak | poor | weak | medium | **strong (tool_call primitives compose into action plans)** |
| Honest refusal native | yes | no | no | yes | **yes (same shape as math refusal)** |
| Verifiable composition | yes | no | no | partial | **yes (Lemma chain + invariant checks)** |
| Requires training corpus | no | YES | maybe | no | **no** |
| Cycle-10-#1 verifier discipline applies | no | no | no | partial | **yes (each primitive ships with its own STRONG verifier)** |

C5 is the only candidate that's "good or strong" across all four use cases without requiring a training corpus and without breaking the predicate-strength uniformity discipline cycle 10 #1 just established.

---

## Cycle-11+ implementation roadmap

If lain greenlights C5:

1. **Cycle 11 #1** — smallest shippable: `compose_haiku(theme)` per above; demonstrates the pattern end-to-end with the existing HDC infrastructure.
2. **Cycle 11 #2** — physics-natural-language: extend math substrate's Lemma rendering with `emit_analogy(known, target)` + `emit_intuition(law, regime)`. Apply to existing physics ladder entries (physics-004 / 005 / 015 — rubric-graded conceptual ones).
3. **Cycle 11 #3** — conversation: `emit_acknowledgement` + `emit_followup` + a Discord-shaped chat-daemon stub that uses HDC memory for context-tracking. Start with single-turn responses.
4. **Cycle 11 #4** — action-taking: `emit_tool_call` primitives + integration with cycle 1's sandbox layer. Single-tool demo (`run_python` on a fixed prompt template).
5. **Cycle 12 #1** — natural-language planner: regex + HDC-similarity-based prompt classifier that routes free-form prompts to the right composer (poetry / physics / chat / action). Free-form input becomes the dispatcher's new branch.

Each step is independently atomic, ships with its own STRONG verifier per cycle 10 #1's discipline, and slots into the existing benchmark + bench-replay infrastructure.

---

## Open questions for lain

1. **Is C5 the right call?** Or does the "aaaah of course" you were looking for go differently?
2. **Which domain ships first?** I recommend poetry-haiku (smallest, most contested, most demonstrative). Alternative: action-taking (most directly useful for "take actions on my PC").
3. **HDC memory training corpus.** For slot-filling to work, the HDC concept space needs DENSE-ENOUGH coverage of theme-image associations. Currently the memory is sparse (test fixtures + a few canonical examples). Question: do we train it on a curated small corpus (lain-selected; not the open Web) or rely on hand-seeded concept associations per domain? Bias: hand-seeded is more honest; corpus introduces the same provenance question as a transformer would.
4. **Voice consistency.** Raphael's declarative-analytical voice fits chat/physics/action natively. For poetry, do we maintain the voice (which makes haiku read more aphoristic than lyric) or relax it for the poetic domain? I lean toward maintain — voice consistency IS Raphael's identity.

---

## Sources

- Pentti Kanerva, *Hyperdimensional Computing* (2009) — binding + superposition + cleanup memory fundamentals.
- The existing `docs/paper.md` Chapters 3-4 — HDC + reasoning substrate as already shipped.
- The cycle 10 #1 predicate-strength uniformity pass — establishes the rigor pattern each new primitive must honor.
- This brainstorm benefited from advisor pre-loading the 5 candidate architectures with the hypothesis #5 nudge toward the Lemma-render-already-IS-text-gen reframing. The synthesis + ranking + counter-claims are this document.

— Design ready for lain greenlight or pushback. Implementation pickup is a cycle-11 candidate; ~90 min Raphael-time for the smallest-shippable haiku primitive demo per the proposal above.
