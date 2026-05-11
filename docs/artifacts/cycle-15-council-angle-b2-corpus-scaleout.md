# Cycle 15 council angle B2 — A4 corpus Layer-6 scale-out, refined

**Status:** cycle-15 council surface B2 (refined from cycle-14 A4 angle note at commit `743128b`). Incorporates cycle-15 #01 demo findings (commit `c197bbd`) + thesis-compliance gate (commit `bb8f297`).
**Date:** 2026-05-11.
**Pairs with:** cycle-14 A4 angle note (predecessor), cycle-15 #01 capability demo, cycle-15 B4 thesis-compliance gate, cycle-15 B3-math predicate v1 (commit `afe6a64`).

---

## 1. The proposal (refined)

The cycle-14 A4 angle note proposed ~200k words of targeted public-domain ingest across 4 gap-shaped domains exposed by the cycle-14 demo's F4/F5 misroute findings. Cycle-15's #01 demo (5 fresh prompts) surfaced TWO additional gaps that refine A4's targeting:

- **F1 cycle-15 (formal `pendulum_period` parser bypassed on prose form):** physics-derivation prompts whose phrasing doesn't match formal-parser regexes route to natural-mode walks. With current corpus (Whitman / Plato / Aristotle / Shakespeare / Dickens / Austen / Aurelius / Tao Te Ching / Wordsworth / Yeats), there are essentially NO physics-derivation fragments. The walk emits whatever-the-cosine-finds — math vocabulary fragments from Aurelius or Aristotle, not physics-derivation worked examples.
- **F4 cycle-15 (P4 self-reflective persona routes to walk_poetry; no persona-walk domain):** persona substrate is hand-coded register archetypes (output-flavor), NOT a retrieval domain. Persona/self-reflection prompts get cosined into whatever domain their lexical features match.

Refined cycle-15 B2 scope (~200-250k words across 5 gap-shaped domains, NOT 4):

| Sub-set | Sources | Target words | Addresses cycle-14/15 finding |
|---|---|---|---|
| **Physics worked-examples** | Newton's *Principia* (PG#28233, English 1729 trans), Maxwell's *Treatise on Electricity & Magnetism* (PG#14725), Galileo's *Two New Sciences* (PG#28644), Helmholtz lectures (PG#27827) | ~80k | F1 cycle-15 (physics derivation gap); F1 cycle-14 (math-derivation gap by analogue) |
| **Math worked-examples + intuition** | Euclid *Elements* (PG#21076), Descartes *Geometry* (PG#26400), Euler's *Introduction to Analysis of the Infinite* (Vol I+II — partial PG availability), Felix Klein lectures (PG availability check) | ~50k | F1 cycle-14 (math-derivation hand-coded gap) |
| **Conversational + casual register** | Austen letters (PG #1342 epistolary segments isolated), Plato dialogue passages (PG#1497 with question-mark veto relaxed for dialogue-tagged sources), Boswell *Life of Johnson* (PG#1564) | ~50k | F5 cycle-14 (chat misroutes to poetry — no chat corpus) |
| **Humour + persona-aligned** | Twain pre-1928 (PG#76 *Tom Sawyer* + PG#74 *Huckleberry Finn* + PG#3173 *Roughing It*), Wodehouse pre-1928 (PG availability check), Jerome's *Three Men in a Boat* (PG#308) | ~30k | F4 cycle-14 (humour misroutes to math); F4 cycle-15 (persona-walk no domain) |
| **Epistemology-of-perception** | Berkeley's *Treatise* (PG#4723), Hume's *Enquiry* (PG#9662), Kant's *Critique of Pure Reason* (PG#4280 — partial), Locke's *Essay* (PG#10615) | ~40k | F3 cycle-14 (P3 retrieved generic Plato instead of perception-shaped) |

**Total target: ~250k words.** Pipeline already exists (`scripts/fetch_corpus.py` + `corpus/ingestion.py` from cycle-12 #00P13c12-01b). B2 implementation extends manifest + tunes `_is_acceptable_fragment` per-source filter (cycle-14 A4 spec preserved).

## 2. What cycle-15 #01 demo data adds vs cycle-14 A4 framing

Cycle-14 A4 was scoped against cycle-14 demo F4 + F5 (humour + chat misroutes). Cycle-15 #01 finds two ADDITIONAL gaps that A4's scope didn't anticipate:

- **F1 cycle-15 (physics derivation):** A4's "math worked-examples" sub-set conflated physics + math. Cycle-15 refines: physics-derivation needs its OWN sub-set (~80k from Newton/Maxwell/Galileo/Helmholtz), separable from math-derivation (~50k from Euclid/Descartes/Euler). Two distinct shapes; both needed.
- **F4 cycle-15 (persona retrieval domain):** A4's "humour" sub-set is mostly Twain comedic prose. Cycle-15 finds that persona-shape prompts (meta-self-reflection, "tell me what you think about X") also fail with no dedicated domain. Twain is partly the answer (persona consistency in narrator voice) + Wodehouse (consistent character voice). Cycle-15 B2 combines humour + persona into one sub-set because they share the corpus surface.

## 3. The strict-strict-thesis case

Per cycle-15 B4 thesis-compliance gate:

- **Test 1 — "Would lain call this hardcoding?"** PASS. Data is INPUT to the substrate, not structure inside it. The encoder consumes the new corpus uniformly through char-n-gram-hash → projection; no per-domain code path added.
- **Test 2 — LEARNING-MACHINERY-ONLY filter.** PASS. B2 doesn't introduce new authored substrate structure. The `_is_acceptable_fragment` per-source filter config exists (cycle-12) and gets tuned (not added).
- **Test 3 — Atom-shape substrate-wide.** PASS. The HebbianBank's `(prompt_atom, fragment_atom)` key set grows with new fragments uniformly. No per-domain partition on the substrate side.
- **Test 4 — Gate fires PER-ANGLE BEFORE commit.** PASS — this section is inline.

**Net gate verdict: PASS.** B2 is strict-strict-thesis-compatible. The thesis explicitly names *"good enough training data + smart enough model"* — B2 is the first half.

## 4. The discriminating question for the cycle-15 synthesis pass

| Scoring axis | B2 score | Plausible cycle-15 #1 under this axis |
|---|---|---|
| **Biggest CAPABILITY lift this cycle (rateable on cycle-15 demo or B3-math predicate)** | ~15% (more corpus alone doesn't shift the substrate; needs the bank + audit signal to consume it) | B1 (dispatcher fix) or B3 (predicates already shipped math; runs the predicate on existing substrate) |
| **Biggest STRICT-thesis-fraction shift (learned / hand-coded)** | ~10% (B2 is data-side; thesis-fraction lives on the model side per cycle-14 framing) | A1-style substrate work (already shipped cycle-14); cycle-15 doesn't have a new substrate-side angle that passes the thesis-compliance gate |
| **Biggest cycle-16-N infrastructure investment (data-side precondition)** | ~30-40% (B2 is precondition for cycle-16+ Hebbian-bank-shaped-by-rated-walks-on-on-topic-corpus; without B2 the bank stays empty of the gap domains) | B2 wins this axis |
| **Combined multi-ship** | ~20% (when bundled with cycle-15 B1 dispatcher fix; bank then has on-topic corpus to retrieve into post-fix) | B1 + B2 paired ship covers routing-side + data-side |

The cycle-14 A4 angle note's combined-multi-ship verdict was ~25%; cycle-15 B2 refines to ~20% standalone, ~25-30% bundled. Slight downward revision because cycle-14's #08c retrieval-blend + bank wire-up shipped — B2 now has machinery to consume new data, but the bank's actual filling depends on lain's rating activity (which is independent of B2's ingest).

## 5. Permeability asterisk (honest framing per cycle-14 synthesis §5 precedent)

**B2 alone produces ~0 measurable capability lift in cycle-15.** Adding 200-250k words to the corpus doesn't make the agent measurably smarter:
- The HebbianBank is empty cold-start; new fragments accumulate in the static encoder's hypervectors but the bank's reward-shaped blend doesn't activate.
- The natural-mode walks now have on-topic material to retrieve toward, BUT cycle-14 demo's F4/F5 misroutes happened at the DISPATCHER level (domain classifier picks wrong domain), not the retrieval level. B2 alone doesn't fix misrouting — it just makes the retrieval less embarrassing IF the routing is correct.
- The cycle-15 B3-math predicate's verdict on a post-B2 agent would likely match the post-cycle-14-close verdict: STRONG or PARTIAL on math worked-example prompts that hit formal parsers correctly (with or without B2 corpus); the corpus addition is upstream of the bank's behavior change.

B2 is **infrastructure investment** with cycle-16+ payoff. Cycle-15 council should treat it as such, not as a capability-lift ship.

## 6. Implementation sketch (sub-task split if cycle-15 council picks B2 as #1 or co-#1)

- **#08a fetch_corpus extension:** Add manifest entries for 4 new public-domain works per sub-set (~15-20 PG works total). ~1h Raphael-time + ~10 min download wall-clock.
- **#08b ingestion per-source filter config:** Tune `_is_acceptable_fragment` per source-tag — relax question-mark veto for dialogue-tagged Plato + epistolary fiction; keep veto for non-conversational sources. ~30 min Raphael-time + tests.
- **#08c corpus ingest run:** Process the new manifest into `data/corpus_raw/` + verified counts. ~20-40 min wall-clock for fetching + ~20 min for ingestion.
- **#08d natural-mode archetype extension:** Add archetypes for new domain tags (`physics_worked_example`, `math_worked_example`, `conversational`, `humour_persona`, `epistemology`). Cycle-13 #07e shipped the cosine-archetype matching infrastructure; B2 just registers more archetypes. ~30 min.
- **#08e regression verification:** Re-run cycle-15 #01 demo on post-B2 agent. Cold-start contract verification (HebbianBank still empty; routing should preserve cycle-15 #01 outputs unless new archetypes shift the cosine-archetype classifier's domain picks). ~30 min.
- **REPO_CONTROL row updates:** `fetch_corpus.py` extension + new `data/corpus_raw/*.txt` files tracked.
- **Atomic commits:** `feat(P13c15-NN-fetch-corpus-extend)` + `feat(P13c15-NN-ingestion-per-source-filter)` + `feat(P13c15-NN-corpus-ingest)` + `feat(P13c15-NN-natural-mode-archetypes)` + `docs(P13c15-NN-demo-rerun-post-b2)`.

**Estimated total cost: 3-5h Raphael-time + 20-40 min compute wall-clock.** Comparable to cycle-14 #08 implementation; smaller than B1 paired ship.

## 7. Honest counter-claims (M-PROJECTX-013)

1. **B2 alone produces near-zero capability lift this cycle.** Same honest framing as cycle-14 A1 had — substrate writability shipped without measured learning. B2 is the data-side analog: corpus shipped without consumed-by-the-bank learning. Both sides need EACH OTHER + audit cadence.
2. **Public-domain corpus has skews.** Pre-1928 English-language sources skew heavily white-Western-male-canon. Conversational corpus from epistolary fiction dominated by Austen / Dickens; humour by Twain / Wodehouse. Cycle-14 A4 already named this; cycle-15 B2 inherits the limitation. Source-diversity audit is cycle-16+ work (M-PROJECTX-corpus-source-bias is a candidate mistake-entry).
3. **The cycle-15 #01 demo F4 (persona-walk no domain) might not be fixed by B2 alone.** Adding humour/persona corpus gives the cosine-archetype classifier a target, BUT the cosine-archetype classifier's CONFIDENCE on persona-shape prompts depends on archetype-similarity quality — and a single Twain or Wodehouse archetype may not cleanly disambiguate "self-reflective persona" from "narrative_prose" or "poetry." Cycle-16+ may need to multi-archetype per domain (cycle-13 #07e's max-of-cosines pattern would extend naturally).
4. **Compute time non-trivial.** 200-250k words through `CharNgramHashEncoder.encode` is ~30-60 min wall-clock single-threaded. Cycle-13 WSL-crash-twice pattern means: ANY HDC-at-scale work routes through `encode_packed` + batched encoding. The encoder's transient float32 proj matrix is the OOM site; B2 ingest at the corpus scale doesn't exceed the existing 22k-corpus encoding (which works), so the risk is bounded.
5. **The cycle-15 council's pre-deliberation read** in the B4 thesis-compliance gate marked B2 as PASS. The synthesis pass should NOT treat B2 as the cycle-15 #1 implementation candidate on capability-lift grounds (~15% rank) — B2 wins the cycle-16-N infrastructure axis (~30-40%) but loses the capability axis to B1 (dispatcher fix; addresses cycle-15 #01 F1 + F3 directly).

## 8. Cycle-16+ spillover (if B2 not picked as cycle-15 #1 or co-#1)

If cycle-15 synthesis picks B1 standalone (closes #08e deferral + the 4-cycle-old latent BG-dispatcher bug):

- Cycle-15 ships routing-side fixes; capability on cycle-15 #01 demo's misroute findings improves WITHOUT B2.
- Cycle-16 ships B2 corpus + B3 sibling predicates (poetry / philosophy / chat) AFTER lain provides rubric input on the subjective-domain firewall.
- Cycle-17 ships A1 + Hebbian-bank-shaped-by-rated-walks IF audit rating cadence has accumulated meaningfully.

The B2 → B3-siblings → A1-bank-filled sequencing is the natural cycle-16+ arc.

## 9. Single-paragraph verdict (for cycle-15 synthesis citation)

B2 is the data-side strict-thesis lever (per `"good enough training data + smart enough model"`); refined cycle-15 scope is 200-250k words across 5 gap-shaped domains (physics worked-examples + math worked-examples + conversational + humour-persona + epistemology), addressing cycle-14 + cycle-15 demo findings F1 / F4 / F4 / F5 / F3 respectively. Thesis-compliance gate PASS (data is input, not structure). Capability-lift this cycle ~15% standalone (corpus alone doesn't move the substrate without rated walks on the new corpus); cycle-16-N infrastructure axis ~30-40% (precondition for the bank-shaped-by-on-topic-rated-walks path). Combined-multi-ship with B1 ~25-30%. Cost: 3-5h Raphael-time + ~30-60 min compute wall-clock. **Synthesis recommendation:** if cycle-15 picks B1 standalone (capability axis), B2 ships cycle-16; if synthesis authorizes a B1 + B2 paired ship, ~20% combined-bundle-bonus on the data-side-precondition framing.

---

*Single-line takeaway: cycle-15 B2 refines cycle-14 A4 with cycle-15 #01 findings (physics-derivation + persona-walk-no-domain). Data-side; thesis-compliance gate PASS; ~15% capability-this-cycle vs ~30-40% cycle-16-N infrastructure. Sequencing question for synthesis: data-first or machinery-first.*
