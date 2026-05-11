# Cycle 14 Council — Angle A4: Training-data Layer-6 scale-out

**Status:** council angle 4 of 5. Feeds the synthesis pass (#07).
**Date:** 2026-05-11.
**Pairs with:** the demo doc (`cycle-14-demo-post-thesis.md`, commit `d89b90f`), A1/A2/A3 angle notes (commits `a0babad` / `d40572d` / `b691961`), the remaining 1 cycle-14 angle note (A5 emergence predicate), and the cycle-14 synthesis verdict.
**Strict thesis lens:** A4 IS the data half of lain's *"good enough training data + smart enough model"* (2026-05-11 binding). The canonical doc Layer 6 spec names 1M-10M words per domain; today's Tier-2 corpus is 22k fragments (~5.5MB on disk). A4 is the cycle-14 scale-out + targeted gap-fill.

---

## 1. The proposal

The cycle-13 demo found the agent retrieving *Whitman* on a "river that forgets the sea" prompt, *Cantor's diagonal argument* on a humour prompt, and *Shakespeare* on a casual greeting. The substrate retrieved what it had. The corpus is what it had access to.

The canonical doc § Layer 6 names the corpus target: **1M-10M words per domain.** Today's Tier-2 corpus is 22,052 fragments across ~12 domain-tagged sources (Whitman, Plato, Emerson, Aristotle, Shakespeare, Wordsworth, Yeats, Austen, Carroll, Dickens, Shelley, Aurelius, Tao Te Ching, etc.) — ~5.5 MB on disk. Per-domain density (rough estimates from `data/corpus_raw/` line-counts): poetry ~700k words, philosophy ~400k words, narrative_prose ~600k words, math+physics fragments ~3k words (project-authored canonical lain_voice + classical math/physics one-liners — by far the thinnest domain).

A4 proposes:

**Cycle-14 scale-out targets, ordered by demo evidence:**

1. **Math + physics worked-examples corpus.** ~100k words public-domain (early calculus texts, classical mechanics derivations, Project Gutenberg's mathematical-and-physical-papers series). Closes the gap most directly relevant to F1 (the strict-thesis ask "learn the math algos from worked examples"). Sources: Euclid (PG#21076, plane geometry), Descartes (PG#26400, geometry), Newton *Principia* (PG#28233, English translation 1729), Maxwell *Treatise on Electricity & Magnetism* (PG#14725), Galileo *Two New Sciences* (PG#28644).
2. **Conversational + casual register corpus.** ~50k words public-domain (epistolary fiction, transcribed-dialogue passages from Plato that DO exist but are filtered out by cycle-13 `_is_acceptable_fragment` question-mark veto, Austen and Dickens chapter-openings that read as casual scene-setting). Closes F5 (P5 chat misroutes to poetry — no chat corpus exists). May require relaxing the question-mark veto for explicitly conversational sources.
3. **Humour + persona-aligned corpus.** ~30k words public-domain (Twain's short pieces, Wodehouse pre-1928, Jerome's *Three Men in a Boat* PG#308). Closes F4 (P4 humour misroutes to math — no humour corpus exists).
4. **Targeted philosophy gap-fill.** ~20k words on epistemology-of-perception specifically (Berkeley's *Treatise* PG#4723, Hume's *Enquiry* PG#9662, Kant's *Critique of Pure Reason* PG#4280) — addresses F3 (P3 retrieved generic Plato instead of epistemology-shaped fragments).

**Total cycle-14 ingest target: ~200k words across 4 gap-shaped domains.** Pipeline already exists (`scripts/fetch_corpus.py` + `corpus/ingestion.py` from cycle 12 #00P13c12-01b); A4 extends the manifest + tunes `_is_acceptable_fragment` for conversational/dialogue sources.

In one sentence: *the canonical doc says 1M-10M words per domain; today's corpus is thin on the four domains the demo exposed as failure modes. A4 fixes the data-shaped failure modes with targeted ingest.*

## 2. The pre-demo strict-thesis case

The strict thesis is two-sided: *"good enough training data + smart enough model."* A1+A2+A3 are the model-side strikes; A4 is the data-side strike. **Neither side alone closes the strict-thesis gap.**

Concretely:
- If A1/A2/A3 ship without A4, the learning machinery learns from a thin, gap-shaped corpus. The substrate Hebbian-updates toward more Whitman; the policy learns "humour prompts have no good route, pick math by default"; the credit propagator distributes blame over fragments the corpus didn't have to begin with.
- If A4 ships without A1/A2/A3, the corpus grows but no machinery consumes it. Retrieval gets *slightly* better as more on-topic fragments exist, but no composition emerges and no routing improves.

The cycle-13 audit (E1, E3) named this exact split: *"discipline + calibration ships; the Terminus needs generation + learning."* Generation needs data; learning needs both data AND machinery. A4 is the data half, alone insufficient but necessary.

## 3. What the demo data adds (and what it does not)

A4's mapping to the cycle-14 demo's 7 findings is the cleanest of the 5 angles — A4 is genuinely a DATA fix:

- **F1 (math hand-coded):** A4 INDIRECT — math worked-example corpus is necessary precondition for A1+A2+A3 to eventually learn algebra-like programs; without it, even infinite ratings can't teach the substrate "completing the square" because the substrate has nothing to retrieve from.
- **F2 (cosine-archetype fallback works):** A4 INDIRECT — more domain-shaped corpus means tighter archetype clusters; routing decisions improve incidentally as the corpus densifies.
- **F3 (retrieval ≠ composition on P2/P3):** A4 PARTIAL — more on-topic corpus means retrieval is closer to the prompt; the P3 epistemology gap-fill would surface Berkeley/Hume/Kant fragments instead of generic Plato. Composition is still A1's territory; A4 makes retrieval-without-composition a higher-quality failure mode.
- **F4 (P4 humour misroutes to math):** A4 DIRECT — there's no humour corpus. P4 was forced to retrieve from math fragments because that's where the cosine led. With humour corpus ingest, the natural-mode classifier's archetype set grows; either the humour-archetype absorbs P4 (best case) or the misroute persists but routes to a richer-than-math corpus.
- **F5 (P5 chat misroutes to poetry):** A4 DIRECT — same as F4 for chat. The cycle-13 `_is_acceptable_fragment` filter explicitly rejects question-marks and dialogue markers, which is exactly the conversational shape P5 needs. A4 + filter-relaxation creates a chat-corpus retrieval target.
- **F6 (strict-thesis fraction ~0%):** A4 INDIRECT — A4 doesn't add learning machinery; the fraction stays at 0% on the model-side. A4 is the data-side strict-thesis lever; its absence guarantees A1+A2+A3 can't move the needle.
- **F7 (cold-encoder latency):** A4 makes it WORSE — more fragments = longer encoder-encode at composer init. Cycle-14 work on batched encoding (queued for whichever angle wins) is more important if A4 ships. Trade-off explicit.

Net: A4 directly strikes 2 of 7 findings (F4, F5), partially strikes 1 (F3), and is a precondition for A1+A2+A3's long-horizon F1 + F6 strikes. **F4 + F5 are uniquely addressed by A4 — A2 fixes routing but cannot route to a humour-corpus or chat-corpus that doesn't exist.** This is A4's load-bearing claim.

## 4. Implementation sketch (concrete enough for #07 cost estimate)

- Extend `scripts/fetch_corpus.py`:
  - New manifest entries for math (Euclid, Descartes, Newton, Maxwell, Galileo), conversational (epistolary fiction), humour (Twain, Jerome), philosophy gap-fill (Berkeley, Hume, Kant).
  - Total ~15 new PG works at ~5-15 MB each; total ~100-150 MB on disk before ingestion (raw txt files).
- Tune `src/project_x/corpus/ingestion.py`:
  - Relax the question-mark veto for conversational-tagged sources via `INGESTION_MANIFEST` per-source filter config. Today's filter is one-size-fits-all; A4 makes it per-source.
  - Add 4 new domain tags: `math_worked_example`, `conversational`, `humour`, `epistemology`.
  - Cycle-12 v2 noise-reduction filter holds for non-conversational sources unchanged.
- Run `scripts/fetch_corpus.py --force` to ingest the new manifest entries.
- Re-encode at composer init: the existing `NaturalModeComposer(include_ingested=True)` path picks up the new corpus automatically; no code change needed there.
- Update `src/project_x/corpus/natural_mode.py` `_NATURAL_MODE_ARCHETYPES`: add archetype prompts for the 4 new domain tags (cycle-13 #07e already shipped the cosine-archetype matching infrastructure; A4 just adds archetypes).
- Tests `tests/test_corpus_scaleout.py` (~80-120 lines, 8-12 tests):
  - Per-source filter config respected (conversational source's question-marks survive; non-conversational source's question-marks filtered).
  - New domain tags present in retrieval results when archetype-cosine triggers them.
  - Cycle-13 regression: cycle-13 demo P1-P5 + cycle-14 demo P1-P3 routing decisions preserved (A4 should ADD routing options, not change existing ones).
  - Cycle-14 demo P4 + P5 re-run: with A4 corpus, do they route to humour / conversational domains instead of misrouting?
- `docs/REPO_CONTROL.md` row updates for `fetch_corpus.py` (new manifest entries) + `ingestion.py` (per-source filter config) + `data/corpus_raw/*.txt` (new public-domain works tracked in git).
- Cycle-14 atomic commits: `feat(P13c14-08a-corpus-manifest-extend)` + `feat(P13c14-08b-ingestion-per-source-filter)` + `feat(P13c14-08c-corpus-ingest)` + `feat(P13c14-08d-natural-mode-archetypes-extend)`.

Estimated cost: **2-4 h Raphael-time** + compute time for ingestion (~20-40 min wall-clock for 200k words through char-n-gram-hash + projection). Compute time may dominate Raphael-time on a single-threaded encoder; cycle-14 work on batched encoding (queued from corpse) would help.

## 5. The discriminating question for the synthesis pass

A4 has a unique axis: **does it ship as scaffold for A1+A2+A3, or as a standalone capability-lift?**

| Scoring axis | A4 score | Interpretation |
|---|---|---|
| **A4 ships alone (no A1/A2/A3 cycle-14)** | ~15% load-bearing | Corpus densifies; F4/F5 routing improves via archetype expansion; no learning happens but retrieval-quality lifts measurably |
| **A4 ships bundled with A1+A2+A3** | ~25% load-bearing | A4 is the data precondition; the model-side angles consume the new corpus and produce richer Hebbian updates / policy gradients / credit signals |
| **A1+A2+A3 ship without A4** | A4's absence is "data debt" — the model-side learns over a gap-shaped corpus | Cycle-15 + would be expected to ship A4 then; defensible but costly |

The cycle-13 audit E3 + lain's strict-thesis quote frame the model-side as load-bearing; A4 is sequentially earlier. A defensible reading is *"ship A4 first (cycle-14), A1+A2+A3 second (cycle-15) once the corpus is rich enough that the model-side has signal to learn from."* The opposing reading is *"ship A1+A2+A3 first to get the machinery online, then scale corpus as the machinery starts producing rateable walks lain can engage with."*

**The discriminating question for the synthesis pass: data-first or machinery-first?**

The demo evidence partially answers: P4 + P5 misroute because the cosine fallback has no humour / chat archetypes to dispatch to — that's a DATA gap, not a machinery gap. So at least the routing-side of P4/P5 fixes are A4-shaped. A2's policy update over post-A4-corpus would converge faster than A2 over pre-A4-corpus.

## 6. Load-bearing % verdict (honest, ship-context-dependent)

- **Standalone:** A4 is ~15% load-bearing — directly addresses F4 + F5 routing-side gaps, indirectly improves F3 retrieval quality.
- **Bundled with A1+A2+A3:** A4 is ~25% load-bearing as data precondition for the model-side strikes.
- **Deferred to cycle-15:** "data debt" framing; defensible if synthesis judges machinery-first sequencing.

**Single-number summary for the synthesis pass:** **~15-20% load-bearing**, lowest of the 5 angles on capability-lift alone, but **highest of the 5 on data-precondition framing** for cycles 15+. The pre-demo informal estimate at the demo doc §6 was ~15%; the F4 + F5 routing-side connection lifts this to ~15-20%. A4's role in synthesis is more sequential ("first, then machinery") than competitive ("instead of machinery").

## 7. Honest counter-claims (M-PROJECTX-013 measure-don't-claim)

1. **A4 alone does not advance the strict-thesis fraction.** More data ≠ more learning. The fraction stays at 0% on the model side regardless of corpus size. The strict-thesis quote is *"good enough training data AND smart enough model"* — A4 is half.
2. **The "more data fixes routing" claim depends on cosine-archetype matching being informative.** If the humour-corpus archetype clusters too closely to the math-corpus archetype (some overlap is likely — both have abstract/technical register), A4 doesn't disambiguate P4. The cycle-13 #07e fallback's TAU floor may need re-calibration alongside A4.
3. **Compute time may dominate Raphael-time.** 200k words through `CharNgramHashEncoder.encode` is ~20-40 min wall-clock on a single thread — not free. The WSL crashes from cycle 12-13 show what happens when corpus + machinery hit memory limits; A4 alone won't crash WSL (corpus is bounded; the dangerous expansion is at the trigram-extraction level in `discover_primitives`) but cycle-15+ work building on A4 needs the batched-encoder fix.
4. **Public-domain corpus has biases.** Pre-1928 English-language works skew heavily white-Western-male-canon. The conversational corpus from epistolary fiction is dominated by Austen / Dickens; the humour corpus is dominated by Twain. Cycle-14 v0 ships the corpus that exists; future cycles need source-diversity audits. M-PROJECTX-corpus-source-bias is a candidate mistake-entry.
5. **Filter relaxation introduces a regression risk.** Today's `_is_acceptable_fragment` rejects question-marks because cycle-12's first ingestion let Socratic-dialogue questions dominate ("What is the meaning of this?" outranked Aurelius aphorisms 100x). Per-source filter config + conversational-tag exemption is defensible, but the cycle-14 implementation must test the regression boundary carefully.
6. **A4 cannot fix F1 in cycle-14.** Math worked-examples ingested at 100k words means the agent has a math-corpus to retrieve from — but retrieval ≠ composition. Without A1+A2+A3, the agent still won't LEARN to derive quadratic roots from worked examples. A4 unlocks the data; A1+A2+A3 are what consume it. Both are needed.

## 8. Cycle-15 spillover (if A4 not picked this cycle)

If the synthesis defers A4:

- A1+A2+A3 train on the cycle-13 thin-corpus. The learning machinery is online but produces narrow updates (Whitman-heavy retrievals get rated, Whitman-heavy substrate accumulates). Cycle-15 ships A4 once the machinery is mature enough to consume new data productively.
- The F4 + F5 misroutes persist for cycle-14. A2's policy update can shift away from "walk_math on humour prompts" but the alternative routes are also wrong-domain — there's nowhere right to route to.
- Cycle-15+ A4 ingest then triggers a re-run of the cycle-14 demo prompts to validate the F4/F5 fix lands as expected.

Deferring A4 a cycle is defensible (machinery-first sequencing has a real argument), but deferring it more than one cycle leaves the demo's data-shaped failure modes unaddressed indefinitely.

---

*Single-line takeaway: A4 is the data half of "good enough training data + smart enough model." Standalone ~15-20% load-bearing; bundled with A1+A2+A3 ~25% as data precondition; deferred a cycle ~"data debt." Uniquely addresses F4 + F5 routing-side via archetype expansion; cannot move the strict-thesis fraction without model-side machinery.*
