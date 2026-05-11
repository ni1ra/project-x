# Cycle 13 Council — Angle 2: Variable-Resolution HDC

**Status:** council angle 2 of 5. Inputs the synthesis pass (#06).
**Date:** 2026-05-11.
**Length note:** honestly thinner than angles 1 / 3 / 5 per the cycle-10 synthesis precedent (asymmetric loading — some angles short because the underlying analysis is honestly short). lain framed the idea as *"optional, I'm just thinking out loud"* (msg `1503248974`); this note honors that framing.
**Advisor consult:** one pre-write round (geometry-mapping correction + F3-addressability refutation integrated).

---

## 1. The proposal (verbatim trigger)

lain Discord 2026-05-11 04:14 UTC, msg `1503248974`: *"Variable HDC resolution, like it can give higher detail to certain geometric positions where needed. This is just optional, I'm just thinking out loud."*

Architecturally: the current HDC substrate is uniform — D = 10000 bipolar dimensions, all dimensions semantically equivalent (random projections, no per-dim weighting). "Variable resolution" implies non-uniform discrimination — some hypervector regions carry more discriminative power than others, dynamically allocated per query.

## 2. Three architectural readings

| Option | Mechanism | Maps to "geometric"? |
|---|---|---|
| **A — per-region-D-varies** | Hypervector split into named regions (semantic / syntactic / intent / procedural per canonical-doc Layer 1); each region uses a different effective D. Implementation: extend `CharNgramHashEncoder.encode` to project different prompt-content into different D-regions per intent classification. | Partial — region boundaries are geometric but resolution within each region is uniform. |
| **B — hierarchical binding** | Primary 10k semantic HV + bound 1k "detail" HV at retrieval time, computed only for concepts flagged (frequency threshold or audit signal). HRR-style. | Misnamed — this is hierarchical *binding*, not hierarchical *geometry*. (Advisor catch — my pre-frame mis-mapped this to lain's quote.) |
| **C — hierarchical retrieval** | Cheap 10k-dim cosine to narrow to top-K candidates; expensive 100k-dim (or D-expanded) re-rank on the top-K only. | **Truer reading.** The high-resolution operation runs where the cheap-retrieval already located discriminative pressure — "higher detail where needed" maps to the K-shortlist. |

Option C is the most direct reading of lain's quote. Options A and B are valid HDC research directions but mis-mapped to the verbatim ask.

## 3. What the demo data adds (advisor refutation of my pre-frame)

My pre-advisor draft argued F3 (walks don't converge, avg_sim 0.18-0.35) was variable-res's load-bearing demo signal. Advisor refuted: F3 reflects **sparse** neighborhoods (the 22k-fragment corpus has non-uniform semantic clustering; nearest-neighbors at the prompt's location are honestly loose). Higher-resolution HDC helps discriminate **within dense neighborhoods**; it does not densify sparse ones. Variable-res does not address F3.

Mapping the 7 demo findings against variable-res leverage:

- **F1 retrieval works fine at 22k** — unrelated to resolution.
- **F2 bundle vs greedy strategy preference** — unrelated.
- **F3 sparse-neighborhood non-convergence** — NOT addressable by higher resolution; this is corpus-density not corpus-discrimination.
- **F4 lain_voice fragments retrieve appropriately** — unrelated.
- **F5 Collatz dispatcher mis-route** — unrelated; angle 5.
- **F6 trigger-gate narrow** — unrelated; angle 5.
- **F7 Whitman 5× on P1** — unrelated; corpus-domain-diversity (angle 3).

Net: variable-res HDC addresses **zero** of the 7 demo findings. Its case stands purely on the speculative-research-direction axis.

## 4. Load-bearing % verdict (honest)

- **Demo-rateable lift this cycle:** ~0%.
- **Terminus-risk-reduction:** ~5-10%. Canonical-doc Layer 1 does not depend on variable resolution; it would be additive architecture, not load-bearing for current cycles 14-N planning.
- **Research-direction value (the lain "thinking out loud" axis):** ~15-20%. lain raised it; HDC literature has precedent (Plate HRR, Eliasmith SPA hierarchical compositions); a future cycle exploring it would not be wasted.
- **Combined-axis honest midpoint:** **~5-8%** load-bearing.

This is the lowest-scoring of the 5 angles. Honest framing — the asymmetric-loading discipline of the cycle-10 synthesis precedent applies. Variable-res is included in the council because lain raised it; the analysis is short because the analysis is honestly short.

## 5. Implementation sketch if cycle-14+ pursues (~3-4 h)

Option C (the truer reading) is the candidate. Concrete sketch:

1. Existing retrieval path in `NaturalModeComposer._step` returns argmax over all candidate fragment hypervectors. Add a `top_k_shortlist` parameter (default disabled).
2. When enabled: compute the cheap 10k-dim cosines first → keep top-K (K = 20-50). Then re-encode the K shortlisted fragments at D = 100000 via a separate `CharNgramHashEncoder(D=100000)` instance. Re-rank by 100k-dim cosine. Emit the top-1.
3. Memory cost: 50 × 100000 bits = 1.25 MB per query at the re-rank step (negligible).
4. Compute cost: 50 × 100000-dim cosine ≈ 5M operations per query (negligible vs the 22k × 10000 = 220M ops of the cheap pass).
5. The 100k encoder must be deterministic (same seed) so re-runs produce identical re-ranks; cycle-13+ work would explore whether the 100k-encoder benefits from a learned-projection variant or stays at random projection.
6. Test surface: ~10 tests verifying (a) re-rank only fires when enabled; (b) re-rank preserves top-1 for queries where the cheap-pass top-1 already dominates; (c) re-rank can move a #3 cheap-pass candidate to #1 in cases where 100k-dim discrimination differs from 10k.

## 6. Honest counter-claims

1. **lain explicitly framed it as "optional, thinking out loud."** Not a directive. The council includes it for completeness, not because it has a high prior.
2. **Variable-res doesn't address any 2026-05-11 demo finding.** Its score is not zero only because the future architectural value is real, not because the cycle-13 case is.
3. **The "geometric positions" interpretation is contested.** Three architectural readings exist; option C is the closest direct match, but reasonable people could prefer A or B. The advisor flagged the mapping question as itself a judgment call.
4. **Even option C is HEAVIER than the cycle-13 budget naturally affords.** 3-4 h for a non-load-bearing research direction is a poor trade against angle 5's clear demo-lift (~2 h estimated) or angle 1's substrate-insurance (45-75 min).
5. **The 100k-dim re-rank is plausibly redundant with corpus expansion (angle 3).** If the corpus reaches 1M+ fragments per domain (canonical-doc Layer 6 spec), sparse-neighborhood F3 dissolves and the re-rank's marginal value drops.

---

*Single-number contribution to the 5-angle synthesis: **~5-8%** load-bearing on the combined axis. Asymmetrically thin per cycle-10 precedent. The synthesis pass should NOT pick angle 2 as cycle-13 #1; recommend deferring to cycle-15+ research-direction window.*
