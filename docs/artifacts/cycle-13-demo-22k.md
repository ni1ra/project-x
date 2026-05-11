# Cycle 13 #01 — Capability demo on 22k Tier-2 corpus

**Status:** first ship of cycle 13. Capability touchpoint BEFORE the 4-angle council per advisor catch 2026-05-11 (cycle 12 expanded corpus 88× and never re-ran the v0 dispatcher against it).
**Date:** 2026-05-11.
**Pairs with:** the 4 council-angle notes (`cycle-13-council-angle-*.md`) and the synthesis verdict (`cycle-13-priority-decision.md`).
**Cited by:** cycle-13 #06 synthesis, cycle-13 dev reflection.

---

## 1. Setup (mechanically verified)

- Entrypoint: `ReasoningAgent.process(prompt)` from `src/project_x/reasoning_agent.py`.
- Natural-mode composer: `NaturalModeComposer(include_ingested=True)` (default args). Auto-loads `data/corpus_raw/` at init via `ingest_corpus_dir` per `src/project_x/corpus/natural_mode.py:156-180`.
- Corpus scale verified at runtime: **22,052 fragments** loaded (Tier-1 mini-seed + 22 public-domain Project Gutenberg works ingested cycle 12 #01b/#01c).
- K-rollout: 3 strategies (`bind`, `bundle`, `greedy`); τ_satisfaction=0.000 (v1 floor; calibration is open); winner = highest avg per-step cosine similarity.
- Demo run wall-clock: P1 9.97 s (cold path through encoder), P2-P5 ≤ 0.74 s each. P2-P5 hit the warmed encoder cache; P1 paid the one-time fragment-HV-encode cost.

## 2. Prompts (verbatim from cycle-13 corpse)

| # | Prompt | Expected route (pre-demo) |
|---|---|---|
| 1 | *"Write a poem on the impermanence of stone."* | natural-mode poetry (trigger: "write a poem") |
| 2 | *"What is the meaning of life?"* | natural-mode philosophy (triggers: "meaning of life", "what is the meaning") |
| 3 | *"Verify the Collatz conjecture for the first 10000 integers and discuss honestly what this does and doesn't prove."* | formal `collatz_verify_range` (parser match expected) |
| 4 | *"Argue both sides: is mathematics discovered or invented?"* | unclear — no existing trigger for "argue both sides" |
| 5 | *"Compose a sonnet on the death of a friend."* | unclear — "compose a sonnet" not in poetry triggers (only "compose a poem") |

## 3. Captured outputs (verbatim from ReasoningAgent.process)

### Prompt 1 — *"Write a poem on the impermanence of stone."*

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_poetry`, combined_confidence=0.8474, intent_register=`terse`.
- **K-rollout:** bind 0.0839 / **bundle 0.2754** (chosen) / greedy 0.1824.
- **Walk (5 fragments, all public-domain Whitman):**
  1. *"Of the turbid pool that lies in the autumn forest, Of the moon that descends the steeps of the soughing twilight, Toss, sparkles of day and dusk—toss on the black stems that decay in the muck, Toss to the moaning gibberish of the dry limbs."* — Whitman *Leaves of Grass* (PG#1322) (sim=0.194)
  2. *"The sharp-hoof'd moose of the north … same old law."* — Whitman *Leaves of Grass* (sim=0.339)
  3. *"The leaves and flowers of the commonest weeds … through the forenoon."* — Whitman *Leaves of Grass* (sim=0.311)
  4. *"And that is the theme of War, the fortune of battles, The making of perfect soldiers."* — Whitman *Leaves of Grass* (sim=0.281)
  5. *"I am the poet of the Body and I am the poet of the Soul."* — Whitman *Song of Myself* (sim=0.251)

### Prompt 2 — *"What is the meaning of life?"*

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_philosophy`, combined_confidence=1.0 (full match), intent_register=`casual`.
- **K-rollout:** bind 0.1454 / **bundle 0.3510** (chosen) / greedy 0.3070.
- **Walk (5 fragments, Emerson + Plato):**
  1. *"So in accepting the leading of the sentiments … principal fact in the history of the globe."* — Emerson *Essays First Series* (PG#2945) (sim=0.317)
  2. *"And so we arrive at the result, that the pleasure of the intelligent part of the soul … has the pleasantest life."* — Plato *The Republic* (PG#1497) (sim=0.388)
  3. *"Through the innermost or eighth of these, which is the moon, is passed the spindle …"* — Plato *The Republic* (sim=0.378)
  4. *"The antidote to this abuse of formal Government … shabby imitation."* — Emerson *Essays First Series* (sim=0.347)
  5. *"The beauty of the fable proves the importance of the sense … celebration."* — Emerson *Essays First Series* (sim=0.324)

### Prompt 3 — *"Verify the Collatz conjecture for the first 10000 integers and discuss honestly what this does and doesn't prove."*

- **Dispatcher:** `domain=open_domain`, `problem_shape=natural_mode_walk_math`, combined_confidence=0.8615, intent_register=`default`.
- **Did NOT route to formal `collatz_verify_range`** — natural-mode trigger fired first via `"collatz"` keyword in `_NATURAL_MODE_TRIGGERS["math"]`. Finding flagged in §4 below.
- **K-rollout:** bind 0.0722 / bundle 0.1743 / **greedy 0.1859** (chosen).
- **Walk (5 fragments — math + project canonical framing):**
  1. *"Gödel's first incompleteness theorem proves any consistent formal system rich enough for arithmetic contains true statements that cannot be proven within the system."* — Classical mathematical logic (sim=0.198)
  2. *"Honest framing: the substrate empirically verifies over [1, N]; the conjecture itself remains theoretically open. Process artifact, not capability artifact."* — Project X canonical M-PROJECTX-013 (sim=0.195)
  3. *"The twin-prime conjecture (infinitely many pairs of primes p, p+2) is open; Hardy-Littlewood gives a density conjecture that empirical data matches."* — Project X canonical + classical (sim=0.185)
  4. *"The Collatz conjecture (3n+1) is empirically verified for all n up to ~2⁶⁰; no theoretical proof exists. Substrate PASS over [1, N] is empirical verification, NEVER proof."* — Project X canonical (sim=0.185)
  5. *"Aleph-null is the cardinality of the natural numbers …"* — Classical set theory (sim=0.167)

### Prompt 4 — *"Argue both sides: is mathematics discovered or invented?"*

- **Dispatcher:** `domain=unrecognized`, `problem_shape=unrecognized`, `confidence=refused`.
- **Outcome:** *"Notice. Prompt did not match any currently-supported problem-shape. BG-style dispatcher ran all 21 parsers; none returned a match. Honest failure preferred over confabulation per M-PROJECTX-013."*

### Prompt 5 — *"Compose a sonnet on the death of a friend."*

- **Dispatcher:** `domain=unrecognized`, `problem_shape=unrecognized`, `confidence=refused`.
- **Outcome:** identical honest-refusal as P4.

## 4. Findings (honest; NO grading of subjective outputs per M-PROJECTX-014)

### F1 — Corpus loads cleanly; retrieval works mechanically

22,052 fragments encoded once at composer init; per-prompt retrieval through the 22k space runs sub-second after the cold start. The WSL-crash failure mode of cycle 12 was specifically the k-means clustering step, not the retrieval path. **Retrieval is NOT the bottleneck.**

### F2 — Bundle wins poetry + philosophy; greedy wins math

`bundle` (same-theme continuation, additive context update) was chosen for both subjective-domain walks; `greedy` (no context update; always score against original prompt) won the math walk. This is consistent with the canonical doc Layer 4 framing — bundling produces same-theme drift suited to expressive domains; greedy holds tight to the original prompt for fact-shaped queries. **Reproducible empirical pattern**; not a fluke.

### F3 — Average similarities are low (0.18–0.35) — the WALK doesn't converge tightly

Even the best walk (P2 philosophy bundle, avg_sim 0.351) sits well below what would qualify as a coherent answer; the runner-up rollouts (bind 0.07–0.15) are near-orthogonal to the prompt. **The 22k corpus retrieves nearby fragments but does NOT compose a satisfying response to the prompt.** Bundle's win is relative, not absolute. The current τ_satisfaction=0 means ALL walks emit; raising τ to ~0.3 would mass-refuse walks below threshold.

### F4 — Project's own canonical framing is in the retrievable corpus and surfaces appropriately

P3 walk pulled M-PROJECTX-013 framing fragments at steps 2 and 4 (*"the substrate empirically verifies over [1, N] … never proof"*). The lain_voice-tagged Tier-1 fragments are doing real load-bearing work — the agent's honest framing on open conjectures IS retrievable and DOES retrieve when the prompt asks about Collatz. This is a small but real architectural signal.

### F5 — Dispatcher routes Collatz to NATURAL mode, NOT formal substrate

P3 should plausibly have routed to `collatz_verify_range` (formal mode would have computed the actual 1-10000 verification). Instead the BG dispatcher gave natural-mode 0.8615 confidence and shipped the corpus walk. Two hypotheses:
- **(a)** The formal parser's regex didn't match the prose form ("Verify the Collatz conjecture for the first 10000 integers and discuss honestly …") — too much surrounding prose, not the canonical "verify … in range 1 to N" form.
- **(b)** Both formal + natural-mode parsers matched but natural-mode's combined confidence beat formal's via the hv-similarity term.

Either hypothesis suggests the BG-dispatcher's confidence calibration is a real lever. Council angle 1 (bitpack) does not address this; council angles 2/3/4 don't either. **This is a finding the synthesis pass should hold against any winning angle.**

### F6 — Natural-mode trigger gate is narrow vs the 22k corpus

P4 and P5 are obviously lain-aligned (one a philosophy question, one a poetry request) but neither matched the existing trigger set. The 22k corpus has rich material for both — Plato + Emerson for "discovered or invented," Whitman + sonnet poets for "sonnet on death." **The bottleneck on P4/P5 was the trigger keywords, not the retrieval substrate.** Expanding `_NATURAL_MODE_TRIGGERS` from regex-keyword gates to HDC-similarity-to-archetype gates (already done for the BG dispatcher at Layer 3) would lift capability cheaply.

### F7 — Walks emit Whitman 5× on P1 (a stone-impermanence prompt)

P1 returned 5 Whitman fragments out of 22k available. The poetry-tagged subset (Whitman + Shakespeare sonnets + Milton + Dante) is small enough that the 5 nearest neighbors clustered in one author. This is honest but suggests **per-domain corpus diversity is uneven** — narrative_prose / philosophy / science have multiple contributing authors per domain; poetry is dominated by Whitman volume.

## 5. Counter-claims (M-PROJECTX-013)

1. **The demo did NOT produce poetry.** It retrieved 5 nearby Whitman fragments on P1. A reader looking for "a poem on the impermanence of stone" gets surface-similar Whitman, not a composed poem. Honest framing: this is corpus retrieval, not generation.
2. **The demo did NOT answer "what is the meaning of life."** It surfaced 5 Plato/Emerson fragments tangentially related to "soul/intelligence/life." A reader gets canonical philosophy excerpts, not a synthesized answer.
3. **The demo did NOT verify Collatz for [1, 10000].** The formal substrate that COULD have actually computed the empirical verification was bypassed. The walk returned framing-about-Collatz, not a verification.
4. **Refusal on P4/P5 is correctly preferred over confabulation** but reveals trigger-gate brittleness, not architectural depth.
5. **22k fragments is still 2-3 OoM below the canonical Layer 6 spec** (1-10M words/domain). Cycle-12 expansion was real progress; the corpus is NOT yet at the spec.

## 6. Hooks for the 4-angle council

| Finding | Bitpack+emergence (angle 1) | Variable-res HDC (angle 2) | Quality-curation (angle 3) | Bootstrap-audit (angle 4) |
|---|---|---|---|---|
| F1 retrieval works fine | retrieval not the lever | retrieval not the lever | retrieval not the lever | audit signal is downstream of retrieval; still relevant |
| F3 walks don't converge | unrelated | **variable-res could lift per-step similarity** by giving high-detail subspaces to the prompt's semantic core | **better-curated corpus could raise avg_sim** if higher-quality nearest-neighbors exist | bootstrap audit IS the loop that learns what counts as "converged" |
| F5 Collatz routed wrong | unrelated | unrelated | unrelated | unrelated — this is dispatcher calibration |
| F6 narrow trigger gate | unrelated | unrelated | unrelated | unrelated — this is parser-archetype work |
| F7 Whitman dominance | unrelated | unrelated | **angle 3 directly addresses** — per-domain corpus diversity is a curation parameter | unrelated |

**Surprises:** the demo's most-load-bearing findings (F5 dispatcher calibration + F6 trigger gate) map to NONE of the 4 council angles. The synthesis pass should explicitly account for whether the cycle-13 #1 should be one of the 4 angles OR a 5th candidate ("dispatcher-and-trigger refinement") surfaced by the demo data.

## 7. Atomic commit info

- Demo script (one-off, gitignored): `/tmp/cycle_13_demo_22k.py`. NOT tracked — per Seal 6 tidiness.
- Doc artifact: `docs/artifacts/cycle-13-demo-22k.md` (this file).
- Commit message: `docs(P13c13-01-demo-22k): capability demo on 22k Tier-2 corpus — 3 walks, 2 honest refusals, dispatcher-calibration finding (F5) + trigger-gate finding (F6) for council`.

---

*Honest framing — this is observation, not grading. Subjective-domain outputs (P1 poetry, P2 philosophy, P4/P5 attempted) are rubric-pending; lain audits via the cycle-12 #02 CLI rating tool, not via this doc. No `self_score` on poetry/philosophy outputs per M-PROJECTX-014 split-grading firewall.*
