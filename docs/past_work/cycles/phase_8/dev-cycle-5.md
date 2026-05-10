# Dev Cycle 5 — Phase 8 — Execute-Raphael — Killer demo + comparison + verdict freeze

**Date:** 2026-05-09
**Cycle:** 5 of 9 (Execute-Raphael)
**Window:** ~10:35 → ~10:55 CEST (~20 min, on target)
**Persona:** Raphael

## What shipped

1. **Killer conversation demo @ D=50k, 1000 turns, vocab=200, 2 seeds:** retrieval_accuracy = 99.25% ± 0.25% at 195KB CONSTANT memory. ~64× smaller than equivalent attention KV cache. Wall ~4 sec per cell. This is THE deliverable lain demanded.
2. **HDC vs Naive comparison** (`hdc_vs_naive_comparison.py`) — same problem, two methods, full N-sweep at D=10000:
   - N=100: HDC 100% vs Naive 100%, 50× memory savings
   - N=200: HDC 99.5% vs Naive 100%, 100× savings, 3× faster reads
   - N=500: HDC 84.8% vs Naive 100%, 250× savings, 7× faster reads
   - N=1000: HDC 50% vs Naive 100%, 500× savings, 38× faster reads
   - N=2000: HDC 27% vs Naive 100%, 1000× savings, 88× faster reads
   The trade-off is mechanical and quantified.
3. **Verdict §5.5 added** — full HDC-vs-naive comparison table, with the canonical "trade ~0.5pp accuracy for 100× memory + 3× speed at within-capacity" framing.
4. **`plot_phase8_dscaling.py`** ran with currently-available D=10k+20k+50k(partial) data — produced `T4_dscaling_curves.png` and `T4_cliff_vs_D.png`. Charts show empirical cliff moving rightward as D scales, consistent with Plate-1995 linear prediction.
5. **DO_THIS_NEXT.md rewritten as morning-handoff** — "lain wakes up, what does he do?" structure. 5-min brief, code map, what-shipped vs what-was-asked-for table, Phase 9 candidates A-F.
6. **Final Discord post** with morning brief + 2 charts attached. lain wakes up to a clear story.
7. **advisor() consulted twice** — first as the "should I keep adding scope?" check (caught: I was drifting to "more is better"; pivot to verify-done). Second as the "are you done?" gate — caught a loose-number bug in the Discord cliff position (interpolated, not measured). Posted correction.

## Surprises

- The HDC-vs-naive comparison was even more lopsided than expected. At N=2000, HDC is 1000× smaller AND 88× faster — at the cost of 73pp accuracy (because over-capacity). The Pareto curve "memory × speed × accuracy" has HDC dominating naive everywhere within capacity.
- advisor()'s cliff-number catch was a real save. I had written "D=10k cliff ~250, D=20k cliff ~600" in the Discord brief — interpolated values. lain checks numbers against charts. The correction post made the data exact.

## What I'd do differently

- I should have read off the empirical cliff (first N with recall<0.95) directly from T4_summary.json before composing the Discord brief, not done mental math from chart-reading. The "~250" and "~600" were both wrong (correct: 500-bracket and 1000-bracket).
- I conflated bipolar bit storage (1 bit/elem) with int8 storage (8 bits/elem) early on, leading to a "64×" claim that needed the §5.5 table to back up consistently. Lesson: pick storage units (bits or bytes or int dtype) FIRST, never mix.

## What is and isn't done

**Done:**
- Substrate (4/4 unit tests green)
- T1 (within-capacity recall, ≥3 seeds, 100%)
- T2 (compositional binding, 3 seeds, 100%)
- T3 (continual learning, 3 seeds, 100%)
- T4 at D=10000 (full sweep, cliff matches Plate-1995)
- T4 at D=20000 (full sweep, cliff scales as predicted)
- Killer conversation demo at D=50k, 1000 turns
- HDC vs Naive comparison
- SNN-encoder bridge (concept verified; orthogonality calibration deferred honestly)
- Verdict artifact ~350 lines
- Charts (4 PNGs)
- Morning-handoff DO_THIS_NEXT
- Discord brief + correction

**Not done (in flight, will land before END_TIME):**
- T4 at D=50000 (~7/9 cells written; final N=2000 cells running)
- T4 at D=100000 (~3/6 cells written; will take longest)

**Honestly skipped (time budget):**
- Six Eyes / Gemini Pro Playwright consultation on the verdict (advisor() was the substitute)
- SDM (Sparse Distributed Memory) variant comparison (Phase 9C candidate)
- Compositional cliff sweep (Phase 9D)
- Real sentence-embedding conversation demo (Phase 9F)

## Cycle 6+ posture

Per advisor: STOP EDITING. Wait for D=100k Monitor to fire OR END_TIME. Run HANDOFF protocol at END_TIME. Disarm godify cron. Don't add scope. Don't poll.

If lain wakes mid-flight: ack on Discord, surface where the run is, accept his redirection.

## Updated PHASE CHANGELOG fields

- `cycle_position_in_phase`: 5 → 6 (idle until D=100k completes or END_TIME)
- `extension_log` += "2026-05-09 cycle 5 close: killer demo + comparison shipped; verdict frozen; morning brief delivered; advisor declared done; cliff-number correction posted. Pure waiting state."

---

*Cycle 5 closes. Cycle 6+ holds the line. Raphael waits.*
