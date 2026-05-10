# Dev Cycle 2 — Phase 8 — Execute-Raphael — HDC Substrate

**Date:** 2026-05-09
**Cycle:** 2 of 9 (Execute-Raphael)
**Window:** ~09:00 → ~09:30 CEST (~30 min — over the 20-min target due to advisor-driven plan correction mid-cycle, but green output)
**Persona:** Raphael

## What shipped

1. **advisor() consulted pre-Write** per universal CLAUDE.md standing order. Caught two real plan bugs:
   - Original T1 pass-line (`bit_accuracy ≥ 0.95 at N=1000, D=10000`) was mechanically unreachable per Plate-1995 capacity bound. Reframed as `item_recall_after_cleanup ≥ 0.95 at N=200` (within capacity) — kept the bit_accuracy as reported metric, not the gate.
   - Architecture sketch in plan used `M += outer(k, v)` (D×D = 800MB at D=10000), but my mental code had already corrected to direct binding `M += bind(k, v)` (D-dim accumulator). Plan and code reconciled.
2. **A_TO_Z_PLAN.md edited** — capacity-aware acceptance criteria (T1, T3 within-capacity; T4 explicitly maps the cliff; EXCEPTIONAL pushes D up for ≥1000 items). Kill criterion conditioned on within-capacity recall, not absolute. Architecture sketch corrected.
3. **`src/project_x/experiments/hdc_substrate.py` written** — 6 primitives (bind, unbind, superpose, write, read, cleanup) + 4 unit tests + CLI. Standard bipolar HDC per Plate-1995 / Kanerva-2009. Direct-binding write (D-dim accumulator).
4. **Self-test 4/4 GREEN** at D=10000, seed=1337, in 0.0s wall:
   - test_bind_self_inverse: bit_accuracy=1.0000 ✓
   - test_superpose_capacity_2_items: max_bit_accuracy=1.0000 ✓
   - test_write_read_single_item: bit_accuracy=1.0000 ✓
   - test_random_baseline_below_passline: bit_accuracy=0.5009 (~0.50 expected) ✓
5. **`src/project_x/experiments/hdc_capacity.py` written** — T1 + T4 implementations. CLI `T1` and `T4` subcommands. Saves result.json per cell.
6. **T1 GREEN at (D=10000, N=200, seed=1337):**
   - bit_accuracy_mean = 0.5282 (matches Plate prediction 1 - Φ(-1/√199) ≈ 0.528 to 4 decimals)
   - **item_recall_after_cleanup = 1.0000** ← THE PASS-LINE METRIC
   - Plate capacity at M=N=200: 256.2 → we are at N=200, comfortably within capacity
   - Wall: 0.196 sec
7. **T4 capacity sweep launched in background** — D=10000, N ∈ {50, 100, 200, 500, 1000, 2000} × 3 seeds = 18 cells. Monitor armed for completion.

## Surprises

- The substrate is FAST. 0 sec wall for self-test, 0.2 sec for N=200 cell. NumPy vectorization at D=10000 is essentially free.
- T1 item_recall went straight to 1.0 at the calibrated within-capacity N=200. The advisor correction was load-bearing — without it, I'd have run at N=1000 and seen ~50% recall, triggered the kill criterion, and abandoned HDC for the wrong reason.
- The math (Plate-1995 bit-accuracy prediction 0.528) matches empirical bit_accuracy_mean (0.5282) to 4 decimals. This is theoretical confirmation in the data.

## What I'd do differently

- I should have done a back-of-envelope capacity calculation BEFORE writing the plan in cycle 1, not relied on the advisor to catch it. The advisor's sharpness saved me, but cycle 0 should have been more careful.
- Cycle 2 over-ran the 20-min target because of the mid-cycle advisor correction. That was the right call (capacity-aware targets are correct), but it means cycle 3 has less buffer.

## Cycle 3 mission (handoff)

Cycle 3 = T2 compositional binding + T3 continual learning. Both within-capacity at D=10000, N ≤ 200. Pass lines: T2 ≥ 0.80 compositional accuracy, T3 ≥ 0.90 first-100 retention at t=200. After T4 capacity sweep completes, also include the cliff-mapping plot in Discord.

## Updated PHASE CHANGELOG fields

- `cycle_position_in_phase`: 2 → 3
- `extension_log` += "2026-05-09 cycle 2 close: substrate shipped 4/4 green; T1 PASS at item_recall=1.0 N=200 D=10000; T4 sweep launched bg. advisor() caught two plan bugs (capacity targets + outer-vs-bind); plan reconciled."

---

*Cycle 2 closes. Cycle 3 fires T2 compositional + T3 continual.*
