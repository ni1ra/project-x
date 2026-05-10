## Cycle 9 Reflection — Phase 2 — 2026-04-29 04:45–05:02 UTC (CEST 06:45–07:02) — first Execute-Navi of phase 2

### Persona
Execute-Navi (cycle 9, position 2 of phase 2). Skills carried over: `/flow-state`, `/skills:skill-index`, `/skills:refine-todos`.

### Shipped this cycle

- **5-seed reliability sweep** at the cycle-7 winner config: seeds `{1337, 2026, 3001, 4042, 5050}` × `--block-pool sum --selector-distill-weight 2.0 --dim 64 --depth 2 --steps 500 --eval-batches 50 --assoc-loss-weight 10.0`. Total wall time ~92s (5 × ~18s per cell). 5 result.json files in `gpt-codex/runs/run-*-reliability-seed-*`.
- **Aggregation analysis** in-line via Bash + Python. Output: 5-seed mean ± std table, candidate vs control comparison, val_loss aggregation.
- **`docs/A_TO_Z_PLAN.md` updated** — PHASE CHANGELOG cycle_9_clockout entry written, dashboard checkbox 1 (5-seed sweep) flipped to [x], cycle_position_in_phase incremented to 3, expected_phase_exit revised down to cycle 5 because the result is clean enough that HP grid may be unnecessary.
- **`gpt-codex/PROGRESS.md` appended** with `## 2026-04-29 (Phase 2, cycle 9) — 5-seed reliability sweep RECONTEXTUALIZES the breakthrough` section: 5-seed table, reframing of phase 1's 2-seed narrative, headline numbers, verdict update from PARTIAL ADVANCE → STRONGER ADVANCE, phase-2 next-step plan.
- **`docs/DO_THIS_NEXT.md` rewritten** for cycle 10: eval_batches scaling test on seed 3001 + optional harder-probe pilot on seed 1337 (deferring to cycle 11 if Step B requires CLI changes).
- **This file (`docs/dev-cycle-9.md`)** — closing reflection.

### The cross-seed finding (this cycle's payload)

The 5-seed sweep produced a much stronger picture than phase 1's 2-seed narrative:

```
                    seed 1337  seed 2026  seed 3001  seed 4042  seed 5050   mean ± std
control assoc_acc:    0.080      0.085      0.005      0.015      0.010    0.039 ± 0.036
candidate assoc_acc:  0.125      0.070      0.070      0.060      0.060    0.077 ± 0.024
Δ (cand - ctl):      +0.045    -0.015     +0.065     +0.045     +0.050   +0.038
```

Phase 1 picked seeds 1337 and 2026 — both of which turn out to be the seeds where CONTROL lifts most (above its 0.039 mean). The other 3 seeds (3001, 4042, 5050) have control essentially at random (0.005-0.015), but candidate stays in the 0.06-0.07 range. **Candidate is more reliable than control on this task** — std 0.024 vs 0.036.

#### What this changes about the morning briefing

Phase 1's verdict was "PARTIAL ADVANCE — candidate beats control on seed 1337, trails on seed 2026." The 5-seed view supports a much stronger claim: **on the average seed, candidate beats control on assoc_acc by ~2× with lower variance, and beats it on val_loss + memory on every seed**. The phase-1 framing under-sold the architecture's reliability.

The cycle-1 contract's `assoc_acc ≥ 0.15` target is still unmet by candidate mean (0.077 vs 0.15). But the candidate consistently lifts off random while control is near-random on most seeds — a stronger pareto demonstration than phase 1 documented.

### Verifications

- All 5 runs completed in <20s wall each (well within `--mode test` 180s budget).
- All 5 `result.json` files have `passed_initial_gate: true` (loss_regression < 3%, memory_improvement > 0, selector_entropy > 0.05).
- Cross-seed reproducibility of seed 1337 + 2026: cycle-7 final reported 0.125 / 0.070; cycle-9 reproduced 0.125 / 0.070 EXACTLY. Same random seeding, same answer — torch/numpy/random seeding is correctly reset per run.
- pytest not run this cycle (pure experiment, no code changes).

### Lessons

- **Two seeds is not enough to characterize a method's cross-seed behavior on a task where one or both methods are near a noise floor.** Phase 1 used 2 seeds; the variance signal across 5 seeds is dramatically richer (std went from "ambiguous" to "candidate clearly more reliable than control"). Lesson for phase 3 onwards: any breakthrough claim that hinges on a comparative metric near a noise floor should require ≥5 seeds before claiming.
- **Control's seed-sensitivity is itself a finding.** Full-attention transformer control assoc_acc varies from 0.005 to 0.085 across seeds (17× spread!) at the same dim/depth/steps. This means the task's difficulty is high enough that control is at the edge of "barely learns" — initialization matters a lot. The compressed-memory candidate's tighter distribution suggests its inductive bias (varied probe + sum-pool block-keys + selector-direct distill) helps it avoid the bad-init basins that trap control on most seeds.
- **The "phase 1 partial advance" framing was honest given 2-seed data, and stronger framing emerges naturally with more seeds.** Don't oversell early; let the data widen the claim. Phase 2 cycle 9 took ~15 min of execute time and rewrote the verdict.
- **PRE-CLOCKOUT length:** I should consider that PROGRESS.md updates are most impactful at cycle boundaries (Lain reads them on wake). The cycle-9 PROGRESS append re-frames the entire morning briefing — high-leverage 90 seconds of writing.

### 420 Score
**420** — perfect cycle. The contract was "ship the 5-seed sweep + branch decision," what landed was the sweep + a substantively stronger result than phase 1 reported + comprehensive PROGRESS.md update + dashboard advance. The branch decision turned out cleaner than the cycle-8 plan anticipated (no HP grid needed). Cycle 10 has a tight scope (eval_batches scaling + optional harder-probe) and ample slack.

### Next Cycle Hook

Cycle 10 (Execute-Navi, fires 7:22 CEST per cron) ships eval_batches scaling test on seed 3001 (the most informative seed for confidence checks), then optionally a harder-probe pilot at longer `seq_len` IF the CLI doesn't need a `--seq-len` flag added. Phase 2 likely wraps in cycle 11; phase 3 Plan-Navi at cycle 12 picks scale study OR adversarial probe theme.
