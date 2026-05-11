# Cycle 13 Council — Angle 1: Bitpack + Emergence-at-Scale

**Status:** council angle 1 of 5. Inputs the synthesis pass (#06).
**Date:** 2026-05-11.
**Pairs with:** the demo doc (`cycle-13-demo-22k.md` commits `e4272ac` + `69dec02`), the existing bitpack design (`cycle-13-bitpack-design.md` commit `e9b64cc`), and the other 4 angle notes.
**Advisor consult:** 2 pre-write rounds (sequencing-isn't-winner-takes-all + substrate-axis-undersold catches integrated).

---

## 1. The proposal

Bitpack ships as cycle-13 #1 per the cycle-12 close handoff: pack 32 bipolar ±1 bits into one uint32 (≈8× compression vs int8 bipolar; ≈32× vs int32/float32), cosine-via-popcount on the packed representation, k-means on packed centroids via per-bit majority vote. Emergence-at-scale then re-runs the cycle-12 deferred #06 k-means on the ~22k-fragment Tier-2 corpus (~50k-200k unique trigrams) using the packed infra. Design + implementation surface fully specified at `docs/artifacts/cycle-13-bitpack-design.md`; estimated 45-75 min Raphael-time per the design's honest revised budget (cycle-12 close's 28-min estimate was 2× optimistic per advisor).

## 2. The cycle-12-close case (pre-demo)

The cycle-12 WSL crash on the 22k-corpus k-means was NOT a one-off bug — it's the canonical-doc HDC-infrastructure-optimization roadmap arriving on schedule. 10⁸ associations was always projected to degrade non-linearly; cycle-12's empirical RAM hit (500MB-2GB for 80k×D=10000 bipolar int8 hypervectors + k-means inner-loop allocations exceeding the 7.8 GB WSL ceiling) is the predicted bottleneck materializing. Packed footprint at the same scale: 96-239 MB, comfortably under the ceiling with room for OS + Python + parallel work. Cycle-12 close framed bitpack as PREREQUISITE for re-attempting emergence-at-scale, not optional.

This is true regardless of demo data. The cycle-11 #06 primitive-emergence MVP at ~3k trigrams produced clean structural shells (e.g. primitive #10 "X is Y" copula `{'it is a' / '2 is a' / 'this is my' / 'he is a'}` — canonical-doc's first example pattern, NOT frequency ranking). Whether this survives at production scale (~80k trigrams, 25× the MVP) is the empirical test the canonical-doc Layer 5 claim rests on. Bitpack unblocks that test.

## 3. What the demo data adds (and what it does not)

The demo (cycle-13 #01) ran 5 prompts against the 22k corpus and surfaced 7 findings. Mapping bitpack's leverage against each:

- **F1 retrieval works fine at 22k.** Bitpack is NOT in the retrieval path — it's a k-means infra change. Retrieval substrate is untouched. Bitpack does not address F1; F1 does not undermine bitpack.
- **F3 walks don't converge (avg_sim 0.18-0.35).** Bitpack does not affect per-step similarity (it's the same cosine arithmetic on the same vectors, just packed). Bitpack is orthogonal to F3.
- **F5 Collatz routed to natural-mode (0.86 confidence) instead of formal substrate.** Bitpack is unrelated; this is BG-dispatcher confidence-formula calibration.
- **F6 narrow keyword-trigger gate refused P4 + P5.** Bitpack is unrelated; this is parser-archetype gate work (angle 5).
- **F7 Whitman 5× on P1.** Bitpack is unrelated; this is corpus-domain-diversity (angle 3).

Net: bitpack addresses ZERO of the 5 demo findings that produced rateable outputs. Its case stands on the cycle-12-close substrate-axis argument, not on demo-rateable lift.

## 4. Advisor refinements

Two pre-write advisor catches reshaped the angle's load-bearing %.

**Refinement (a) — sequencing is NOT winner-takes-all.** Cycle-13's total Raphael-time budget is 5-8 h. Bitpack alone is 45-75 min per design doc. Even if angle 5 (dispatcher + trigger calibration) takes the cycle-13 #1 implementation slot, bitpack can plausibly ship as a parallel deliverable in the same cycle if the synthesis pass authorizes a multi-ship. The original cycle-12 close handoff treated the priorities as a serial 10-deliverable list; that was pre-demo framing. The synthesis is free to bundle.

**Refinement (b) — the substrate-axis case was undersold in my pre-advisor draft.** "Indirect, unblocks an experiment, no demo-rateable lift" is true but incomplete. The Terminus (MANIFESTO § Terminus) names super-human capability across math + poetry + philosophy + physics + perfect memory + persona + always-on + sandboxed action-taking — and the canonical-doc Layer 5 claim (primitive emergence at scale produces structural shells, not frequency rankings) is load-bearing for that target. If 80k trigrams produces frequency rankings instead of "X is Y" shells, that's a pivot signal that reshapes cycles 14-N architectural direction. Bitpack is cheap insurance against architectural overcommitment — not just RAM plumbing.

## 5. The discriminating question for the synthesis pass

The two axes score angle 1 differently. The synthesis pass should pick — explicitly, in the priority-decision doc — which axis to commit to before naming the cycle-13 #1 winner. Otherwise the synthesis silently chooses and the cycle never learns which scoring rule it followed.

| Scoring axis | Angle 1 (bitpack) score | Plausible cycle-13 #1 winner under this axis |
|---|---|---|
| Biggest demo-rateable lift THIS cycle | ~15-20% (no lift on P1-P5; substrate-only) | likely angle 5 (F5/F6 fix unlocks P4/P5 rateable answers from existing 22k) |
| Biggest move against the Terminus (substrate insurance) | ~35-45% (Layer-5 validation is cheap; failure mode is reframing cycles 14-N) | bitpack OR angle 3 quality-curation (if scaling to 1M+ fragments needs both bitpack AND curation pipeline) |
| Combined (synthesis authorizes multi-ship per refinement-a) | bitpack ~25-30% + parallel-ship | both — angle 5 as cycle-13 #1 demo-lift + bitpack as cycle-13 #1b substrate insurance |

The combined row is the most honest reading. The cycle-12 close framed cycle 13 as 10 sequenced deliverables totaling 10-16 h; that doesn't actually fit the 5-8 h budget cycle-13 was scoped for. Picking ONE cycle-13 #1 with the implicit "everything else slips to cycle 14" was always a forced choice; the synthesis is free to authorize bundling.

## 6. Load-bearing % verdict (honest, axis-dependent)

- **On the "demo-rateable lift this cycle" axis:** angle 1 is ~15-20% load-bearing.
- **On the "Terminus-risk-reduction" axis:** angle 1 is ~35-45% load-bearing.
- **On the combined-multi-ship axis:** angle 1 is ~25-30% load-bearing, with the explicit synthesis recommendation that it ships AS WELL AS the demo-rateable winner if the budget permits.

**Single-number summary for the synthesis pass:** **~25%** load-bearing. Mid-pack of the 5 angles, with the explicit caveat that this score depends on the synthesis pass picking the COMBINED-axis scoring rule. If the synthesis commits to "demo-rateable lift" axis only, angle 1 drops to ~15%; if it commits to "Terminus-risk" axis only, angle 1 rises to ~40%. The 25% is the combined-axis midpoint.

## 7. Implementation (recap — design is fully specified)

Per `cycle-13-bitpack-design.md`:
- `src/project_x/hdc_infra/bitpack.py` (~120-200 lines): `pack_bipolar` / `unpack_bipolar` / `cosine_packed`.
- `src/project_x/experiments/encoder.py` (~20 lines): `encode_packed` sibling method on `CharNgramHashEncoder`.
- `src/project_x/corpus/primitive_emergence.py`: `_kmeans_cosine_packed` (per-bit-majority-vote centroid update; the load-bearing care-point).
- `tests/test_bitpack.py` (~150 lines, 12-20 tests): empirical-equivalence test `abs(cosine_bipolar(a, b) - cosine_packed(pack(a), pack(b)))` < 1e-9 at D=10000; edge cases at D=32/64/96/128; pad-and-zero convention; antipodal + all-ones trivials.
- D=10000 constraint: bitpack requires D % 32 == 0; design doc recommends bumping to D=10240 (320 × 32) or D=9984 (312 × 32). Cycle-13 instance picks one.
- REPO_CONTROL.md row for the new `hdc_infra/` package (per same-commit co-landing rule).
- Atomic commit `feat(P13c13-07-bitpack)` if angle 1 wins.

Emergence-at-scale (#03 of the original 10-deliverable cycle-12-close list) then re-runs `run_primitive_emergence` on the 22k-fragment corpus's ~80k unique trigrams using `packed=True`. Document empirical result: do the discovered primitives represent structural shells consistent with the MVP, or frequency rankings? Either answer informs cycle-14+.

## 8. Honest counter-claims

1. **Bitpack at 45-75 min is a small ship.** It does not, by itself, lift any demo-rateable metric. If the cycle-13 budget is genuinely tight and the synthesis forces a single ship, angle 5's demo-lift may win on capability-axis.
2. **The "Layer-5-validation" framing rests on a thin MVP.** Cycle-11 #06 at 3k trigrams produced "X is Y" shells in ONE k-means run; n=1, no replicates. Calling this "the empirical test" is overcommitting on a single observation. The emergence-at-scale test is interpretive — what counts as a "structural shell" vs "frequency ranking" needs an explicit predicate the design doc does not yet specify.
3. **Cosine-via-popcount equivalence is mathematically exact** for binary inputs but has ordering-sensitive float behavior near-orthogonal pairs (design doc §9.3). The `<1e-9` test threshold absorbs this; tighter thresholds would be brittle.
4. **Bitpack does not solve the dispatcher question.** If F5 (Collatz routed wrong) reflects a deeper calibration issue, bitpack lands and the dispatcher is still wrong on the next cycle. Angle 5 IS the dispatcher question.
5. **The advisor's "cheap insurance against architectural overcommitment" framing is itself a value claim.** Whether Layer-5 collapse would actually be cheap to recover from depends on how many cycles 14-N have been built on the assumption. The recovery cost is unknown.

## 9. Discriminating ask if synthesis picks angle 1 alone

If the synthesis pass picks angle 1 (bitpack) as cycle-13 #1 and DOES NOT authorize parallel ship with another angle, the implementation must include the emergence-at-scale RUN itself (not just the bitpack infra) within cycle 13. Otherwise the cycle delivers infra without the empirical test the infra exists to enable — substrate without the experiment is the cycle-12 deferral repeated. Estimated total: 45-75 min bitpack + 60-90 min emergence-at-scale + result-documentation = 2-3 h. That fits the cycle-13 budget; the synthesis should require it.

---

*Single-number contribution to the 5-angle synthesis: **~25%** load-bearing on the combined-axis midpoint, with the explicit synthesis recommendation that the cycle authorize parallel ship of bitpack alongside the cycle-13 #1 capability winner (likely angle 5 on the demo-rateable axis).*
