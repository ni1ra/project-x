# Cycle 13 Council — Angle 3: Quality-First Corpus + Automated Curation

**Status:** council angle 3 of 5. Inputs the synthesis pass (#06).
**Date:** 2026-05-11.
**Pairs with:** the demo doc (`cycle-13-demo-22k.md`), canonical-doc Layer 6 (corpus shape spec; 1-10M words per domain), cycle-12 #01b Tier-2 ingestion pipeline (`4efa69e`), cycle-12 #01c domain-tag expansion (`21a191a`).
**Advisor consult:** none pre-write; framing is anchored by lain's verbatim cluster + demo's F7 signal. Will call mid-write if a judgment-call surfaces.

---

## 1. The premise (verbatim trigger)

lain Discord cluster 2026-05-11 03:54-04:14 UTC, msgs `1503244000` / `1503247136` / `1503247496`:

- *"You are underestimating how much and how good data you need."*
- *"Dataset must be very well curated and high quality, low noise. But rich and broad. You can download from the web too man."*

This is a directive about the **data axis**, not architecture. The hypothesis: the substrate isn't algorithm-bottlenecked — it's data-bottlenecked. The cycle-12 expansion (88× — ~250 → 22k fragments) was real progress but is still **2-3 orders of magnitude below** the canonical-doc Layer 6 target (1-10M words per domain).

## 2. What the demo data adds

Two of the seven demo findings map directly to this angle:

- **F7 Whitman 5× on P1.** The poetry-tagged subset is dominated by Whitman volume (the ingested `leaves_of_grass.txt` is large; the other poetry sources are small). When P1 asks for "a poem on the impermanence of stone," the 5 nearest-neighbors all land in the same author. Per-source diversity is a curation parameter the cycle-12 pipeline did not enforce.
- **F3 walks don't converge (avg_sim 0.18-0.35).** Partially maps — if the prompt's semantic neighborhood is sparse because the corpus is thin per domain, denser/higher-quality per-domain content would raise avg_sim. (The advisor refutation in angle 2 specifically: F3 reflects sparse neighborhoods. Densifying the relevant domain IS angle 3's lever, not angle 2's.)

F1, F2, F4, F5, F6 are unrelated to curation; they're substrate / dispatcher / register findings.

Two-of-seven direct mapping is the second-highest demo coverage among the 5 angles (angle 5 has direct mapping on F5+F6; angle 1 has zero direct; angle 4 has none directly on the rateable prompts, only on the audit-loop's bootstrap). Angle 3's score is anchored in the demo evidence, not speculative.

## 3. Concrete implementation sketch

The cycle-12 #01b ingestion pipeline (`src/project_x/corpus/ingestion.py`) currently does: fetcher → sentence-splitter → provenance-tagger → v2 noise-reduction filters. The cycle-13 #1 winner (if angle 3 lands) extends this with an **automated curation filter pipeline** plus a **scale push**:

### Curation filter additions

1. **Semantic dedup** — cosine threshold (≥0.95 cosine to existing fragment in any encoding pass = duplicate). Removes near-identical Bible quotes, classical-philosophy passages reprinted across multiple Project Gutenberg volumes, etc. Catches the ~5-10% redundancy in the cycle-12 corpus.
2. **Register classifier gate** — uses the existing `_classify_intent_register` (from `src/project_x/reasoning_agent.py:773`) to tag each fragment by intended register (poetry / philosophy-formal / philosophy-casual / argumentative / narrative). Audit signal: under-represented registers get prioritized in subsequent ingestion.
3. **Length normalizer** — fragments longer than ~250 characters get chunked into 1-3-sentence sub-fragments at sentence boundaries; fragments shorter than ~30 characters discarded as low-information. Cycle-12 fragments span 20-2000 characters; the long tail pulls bundle-strategy walks toward verbose-author dominance (F7 evidence).
4. **Per-source diversity quota** — cap any single source/work to N=20% of any per-domain bucket. Whitman alone currently exceeds this in the poetry bucket; the quota would force ingestion of more poets (Dickinson, Browning, Yeats, public-domain Frost subset) to maintain the per-domain target without single-author dominance.
5. **Quality predicate** — heuristic from the registers' cosine spread: a fragment whose register-classifier confidence is sharply peaked (top-1 cosine > 0.4 and top-2 < 0.2) is "register-clear"; ambiguous fragments (top-1 - top-2 < 0.1) get a lower-priority tag. The clean-fraction shapes corpus utility.

### Scale push

- Project Gutenberg has ~70,000 works in the public domain; the cycle-12 ingestion picked 22. Cycle 13 (if angle 3 wins) targets +50-100 works across underrepresented domains. Per-batch atomic commits via the existing pipeline; ~3-5 h Raphael-time per batch × multiple batches.
- Domains to expand: math (Hardy & Wright, Euler's Elements of Algebra, Hilbert's Foundations of Geometry — public domain), physics (Maxwell, Boltzmann — public domain), biology (Darwin Voyage of the Beagle in addition to Origin), Eastern philosophy (Mencius, Zhuangzi), modern poetry (Dickinson, Tagore, Yeats's pre-1928 work).
- Realistic cycle-13-scope: filter pipeline (2-3 h) + first batch of 10-15 new works (1-2 h) + atomic per-work commits. Stretch: 50+ works in cycle 13; honestly, this slips to multi-cycle.

## 4. Load-bearing % verdict

- **Demo-rateable lift this cycle:** ~10-15%. F7 fix is real and direct; F3 partial fix depends on which prompts are tested.
- **Terminus-risk-reduction:** ~25-30%. Canonical-doc Layer 6 explicitly names 1-10M words/domain — that's the spec. Current 22k fragments / ~50k words is 2-3 OoM short across the entire corpus, not just one domain. If the Terminus is "super-human everywhere" and the corpus IS the model (per canonical-doc Layer 6 framing — "HDC at 10⁸ associations… tens of millions of fragments… memory IS the model"), corpus depth is load-bearing for Terminus achievement.
- **Combined-axis honest midpoint:** **~20-25%** load-bearing.

This is the second-highest scoring of the 5 angles after angle 5 (likely 30-40%). Anchored in demo evidence + lain's verbatim cluster.

## 5. Synthesis-tension flag

If the synthesis pass picks angle 3 alone as cycle-13 #1, the ship shape is: filter pipeline + 10-15 new works + tests on the filter. Demo-rateable lift is delayed to cycle 14-15 when accumulated corpus depth changes walk quality measurably. Honest framing — angle 3's lift is **slow-burn**, not first-cycle. Compare with angle 5 (F5/F6 fix = same-cycle demo-rateable improvement on P4/P5).

If the synthesis pass authorizes **multi-ship** (per angle 1's refinement (a)), angle 3's filter pipeline can ship alongside angle 5's dispatcher fix — they're orthogonal code surfaces. The "first batch of new works" element of angle 3 can defer to cycle 14 without losing the architectural lever (the pipeline is the structural piece).

## 6. Honest counter-claims

1. **Quality vs quantity is a real trade.** Cycle 12 hit 22k fragments; 100k-1M target needs ingestion bandwidth that's bottlenecked by Project Gutenberg's public-domain catalog + the curation filter's reject rate. If the filter rejects 60-80% of incoming fragments, reaching 1M-per-domain takes 50× more raw input. Honest estimate: cycle-13 ships the FILTER + ~+5-10k fragments, not 1M.
2. **"NO GPT-generated text" constraint binds.** The thesis-compliance rule (lain 2026-05-09) forbids LLM-distilled corpus. This caps the realistic upper bound on synthetic augmentation; the corpus growth path is genuinely book-by-book Project Gutenberg ingestion.
3. **F3 fix is downstream of corpus density.** Even with 10× the corpus, sparse-neighborhood walks won't tightly converge unless the corpus DENSITY at the prompt's semantic location is high. Per-domain expansion only helps if the prompt's intent is well-covered in the expanded domain.
4. **Curation filter complexity could backfire.** A 5-stage filter pipeline (dedup + register + length + diversity + quality) adds review surface. If the filter's tuning is wrong, the corpus quality drops not rises. Recommend cycle-13 ships the filter with PERMISSIVE thresholds + audit the rejected-fraction; calibrate tightness across cycles 14-15.
5. **F7 alone doesn't justify cycle-13 #1 priority.** A single demo finding showing Whitman dominance on one prompt doesn't prove the corpus is broken. The Layer-6-spec gap IS the load-bearing case; F7 is corroboration not the case.

---

*Single-number contribution to the 5-angle synthesis: **~20-25%** load-bearing on the combined axis. Second-highest scoring angle after the expected angle-5 result. Synthesis-pass recommendation: bundle the filter-pipeline ship with the cycle-13 #1 capability winner (angle 5) under the multi-ship authorization; defer the full corpus scale-push to cycles 14-N.*
