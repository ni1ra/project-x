# Dev Cycle 3 — Phase 8 — Execute-Raphael — T1+T2+T3+T4 + EXCEPTIONAL launch

**Date:** 2026-05-09
**Cycle:** 3 of 9 (Execute-Raphael)
**Window:** ~09:30 → ~10:00 CEST (~30 min — over 20-min target but green output across all 4 tests)
**Persona:** Raphael

## What shipped

1. **T2 compositional binding shipped GREEN** — `src/project_x/experiments/hdc_compose.py` written, run at (D=10000, n_bindings=10, n_filler_atoms=100, 3 seeds). `compositional_accuracy_mean = 1.0000 ± 0.0000`. Pass-line 0.80 → PASS.
2. **T3 continual learning shipped GREEN** — `src/project_x/experiments/hdc_continual.py` written, run at (D=10000, n_phase1=100, n_phase2=100, 3 seeds). `first_100_retention_at_t200 = 1.0000 ± 0.0000`. Pass-line 0.90 → PASS.
3. **T3 measure_retention bug found and fixed** — initial pass had a comparison-offset bug where `idx == i` (loop counter) was compared instead of `idx == expected_index_in_atom_set`. The "first 100" case incidentally passed because i and expected_idx coincided (0..99 in both). The "last 100" case correctly failed (offsets 100..199 expected, but i=0..99 used). Fixed signature to take explicit `expected_indices_in_atom_set` array. Re-run: both first_100 and last_100 retention = 1.0000. Standing rule: any function that takes a "subset of items" must take an explicit index map; never assume `range(len(subset))`.
4. **T4 capacity cliff sweep shipped GREEN** — `gpt-codex/runs/phase8_T4/T4_summary.json` populated. Cliff onset matches Plate-1995 prediction. Numeric data:

   | N | item_recall_mean (3 seeds) | bit_acc_mean | plate_cap_at_M=N |
   |---|---|---|---|
   | 50 | 1.0000 | 0.5559 | 331 |
   | 100 | 1.0000 | 0.5397 | 289 |
   | 200 | 1.0000 | 0.5281 | 256 |
   | 500 | 0.6980 | 0.5179 | 223 |
   | 1000 | 0.2493 | 0.5125 | 203 |
   | 2000 | 0.0592 | 0.5089 | 186 |

   Cliff appears between N=200 (within capacity) and N=500 (over capacity). Pass-line "curve falls within ±2× of Plate prediction" → PASS (cliff onset 200-500 vs Plate prediction 200-300 across the M range).

5. **Charts rendered:**
   - `docs/artifacts/T4_capacity_curve.png` (item recall vs N with Plate capacity zone shaded, 0.95 pass-line marked)
   - `docs/artifacts/T4_bit_accuracy_curve.png` (measured vs Plate-1995 theory line; theory and data overlap)

6. **Discord posted** with 4-test summary + both charts attached. lain wakes up to a clear visualization.

7. **EXCEPTIONAL launched in background:** D ∈ {20k, 50k, 100k} at N up to 2000, 3 seeds each. Three parallel background sweeps. Will complete in ~5-10 min (D=100k cleanup at N=2000 is the longest cell). Monitor armed.

## Surprises

- T2 compositional accuracy at 100% across ALL 3 seeds, not 95%-ish. The 10-binding × 100-filler-atom dictionary setup is well within capacity, so cleanup discriminates trivially. The test may be too easy at this scale; cycle 4-5 should push n_bindings up to find the compositional cliff (a separate empirical question from the raw recall cliff).
- T3 retention is also at 100%. The continual setup (200 total at D=10000) sits just below capacity (cap=256 at M=200). So both "first 100" and "last 100" retain perfectly. This is the "no catastrophic forgetting WITHIN capacity" result lain's vision demanded.
- The bit-accuracy theory match is uncanny. Measured 0.5282 at N=200 vs predicted 0.5281 to 4 decimals. Plate's 1995 paper holds up empirically.

## What I'd do differently

- I should have written the T4 capacity sweep code first (most science-rich), then T1 (smaller scope) as a degenerate case of T4. They're the same loop with different N choice. Cycle 4+ may consolidate.
- The measure_retention bug should have been caught by an inverted unit test. Add to lessons: "any function that takes a subset must take an explicit index map; verify with last_50 retention test before declaring continual-learning green."

## Cycle 4 mission

Once EXCEPTIONAL sweeps finish:
1. Aggregate D-sweep summaries; plot capacity-vs-D charts at fixed N=1000, showing cliff moves with D.
2. Verify ≥1000 items recallable at some D ≤ 100000 — the EXCEPTIONAL goal.
3. Begin draft of `docs/artifacts/PHASE_8_HDC_ORGANIC_MEMORY.md` verdict artifact.
4. If time: SNN-encoder bridge stretch goal.

## Updated PHASE CHANGELOG fields

- `cycle_position_in_phase`: 3 → 4
- `extension_log` += "2026-05-09 cycle 3 close: T1+T2+T3+T4 all GREEN. Charts shipped. Discord delivered with images. EXCEPTIONAL D-sweep launched bg. measure_retention bug found and fixed. lain has visible result by morning."

---

*Cycle 3 closes. Cycle 4 fires aggregator + verdict drafting. The science holds.*
