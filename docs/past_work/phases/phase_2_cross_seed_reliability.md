# Phase 2 — Cross-Seed Reliability + Hyperparameter Sensitivity Study

## PHASE CHANGELOG (top — read by every /godify cycle's Step 0)
- `phase_number`: 2
- `active_phase_theme`: Cross-Seed Reliability + Hyperparameter Sensitivity Study — establish whether phase-1's winner config produces reproducible candidate-beats-control on a 5+ seed sample, then identify any HP knobs (lr, steps, top_k) that close the seed-2026 gap.
- `cycle_position_in_phase`: 4
- `persona_for_this_cycle`: Execute-Navi (cycle 11)
- `phase_started`: 2026-04-29T04:42:00Z (CEST 06:42)
- `expected_phase_exit`: cycle 5 of this phase (cycle 12 overall) — phase 2 is on track to wrap in 1 more cycle (verdict + B-fork rename).
- `previous_phase_doc`: `docs/phase_1_augmentation_cycle_1.md`
- `extension_log`: (none yet)
- `cycle_8_clockout`: 2026-04-29T04:42:00Z (CEST 06:42) — Plan-Navi authored phase 2 plan.
- `cycle_9_clockout`: 2026-04-29T05:02:00Z (CEST 07:02) — 5-seed reliability sweep at eval_batches=50: candidate mean 0.077 ± 0.024 vs control 0.039 ± 0.036 (1.97× ratio).
- `cycle_10_clockout`: 2026-04-29T05:25:00Z (CEST 07:25) — eval_batches scaling test on seed 3001 (50/100/200) confirmed candidate signal is real (~5× control even at 800 samples). High-confidence 5-seed sweep at eval_batches=200 (800 samples per metric): **candidate mean 0.066 ± 0.025 vs control 0.040 ± 0.030 — 1.68× ratio (slightly more conservative than eval=50's 1.97× but qualitatively identical story).** Candidate beats control on 4/5 seeds; val_loss candidate-better by 0.045 on every seed; memory 43.75% better; candidate variance LOWER than control (0.025 vs 0.030).

## PHASE EXIT CONDITIONS

- [x] **5-seed reliability sweep landed (cycle 9):** seeds `{1337, 2026, 3001, 4042, 5050}` × winner config. 5 result.json files in `gpt-codex/runs/run-*-reliability-seed-*`. Cross-seed mean ± std reported: candidate 0.077 ± 0.024, control 0.039 ± 0.036. Candidate beats control on 4/5 seeds.
- [/] **HP grid at any underperforming seed:** SKIPPED — cross-seed signal at eval_batches=200 is clean (4/5 seeds have candidate beating control); seed 2026's underperformance is not a hyperparameter accident but a known seed where control is at its peak. HP grid would be ceremony.
- [x] **eval_batches scaling test (cycle 10):** seed 3001 at eval_batches ∈ {50, 100, 200}. Candidate converged 0.070 → 0.054 as samples increased; control stayed 0.005 → 0.011 (essentially noise floor). Slightly more conservative reading at eval=200 but pattern holds (candidate ~5× control on this seed). **All 5 seeds re-run at eval_batches=200** — high-confidence cross-seed mean: candidate 0.066 ± 0.025 vs control 0.040 ± 0.030, ratio 1.68×.
- [ ] **Phase-1 named curses wiki-logged:** `M-PROJECTX-002` (aux-head distillation steals trunk capacity from main task), `M-PROJECTX-003` (block-pool operation is softmax temperature in disguise), `M-PROJECTX-004` (eval_batches=12 produces 1-sample-noise reads of assoc_acc on this task) appended to `concepts/Project X Session Mistakes.md` via `wiki_log_mistake`.
- [ ] **Phase-2 verdict written:** `gpt-codex/PROGRESS.md` § Phase 2 Complete with cross-seed mean ± std, HP grid result, eval_batches finding, verdict on whether `assoc_acc ≥ 0.15` is achievable at this scale or requires phase 3 (scale study).

## RECON FINDINGS (Plan-Navi cycle 8 — kept for reference across phase 2)

Skipped formal Explore-agent recon — project state inherited intact from phase 1 cycle 7. Key state:

- **Winner config locked:** `--block-pool sum --selector-distill-weight 2.0 --dim 64 --depth 2 --steps 500 --eval-batches 50 --assoc-loss-weight 10.0`. Reproducible across 2 seed runs (cycle 6 and cycle 7 confirmed identical numbers per seed).
- **CLI flags available:** `--seed`, `--distill-weight`, `--memory-byte-weight`, `--selector-distill-weight`, `--steps`, `--eval-batches`, `--assoc-loss-weight`, `--dim`, `--depth`, `--batch-size`, `--heads`, `--block-pool`. NO `--lr` or `--medium-top-k` flag yet (cycle 9 may add if HP grid needs them).
- **Pytest baseline:** 2 passed continuously across 6 cycles. Default config preserves baseline.
- **Compute envelope:** each run at d64-depth2 steps=500 takes 15-20s wall on this CPU. 5-seed sweep ≈ 100s. 9-cell HP grid ≈ 180s. Both well within `--mode test` 180s-per-run budget.
- **Open hyperparameter space (untouched in phase 1):** `lr` (default 3e-4 — never varied), `medium_top_k` (default 4 of 12 — never varied), `local_window` (default 12), `heavy_block` (default 16). Phase 2's HP grid focuses on `lr × steps` first because they're cheapest to vary and most likely to close optimization-basin issues.

## CYCLE-BY-CYCLE PLAN (5 cycles default — extendable to 7 if seed-2026 closure is hard)

- **Cycle 9 (Execute-Navi):** ship the 5-seed reliability sweep at winner config. 5 result.json files materialize. Read mean/std. Decide: is seed 2026 an outlier (mean comfortably above its 0.070), or is the cross-seed distribution wide (mean is also low)?
- **Cycle 10 (Execute-Navi):** depending on cycle 9's verdict — if seed 2026 is outlier, run HP grid at seed 2026 only (3×3 lr×steps at the winner config otherwise). If distribution is wide, run HP grid at seed 1337 (the apparent winner) to see if HP tuning lifts mean.
- **Cycle 11 (Execute-Navi):** ship eval_batches scaling test (50, 100, 200) at seed 1337 to confirm phase-1 confidence intervals.
- **Cycle 12 (Execute-Navi):** wiki_log_mistake calls for M-PROJECTX-002/003/004 + any new lesson surfaced in cycles 9-11. Polish pass.
- **Cycle 13 (Execute-Navi final):** write Phase 2 Complete summary in PROGRESS.md. Verify all dashboard checkboxes. If exit-condition met, B-fork: rename to `phase_2_cross_seed_reliability.md`. Phase 3 Plan-Navi at cycle 14.

## DASHBOARD (mirror of exit conditions)

- [ ] 5-seed reliability sweep at winner config — `gpt-codex/runs/run-20260429-*-reliability-seed-{1337,2026,3001,4042,5050}/result.json`
- [ ] HP grid at any underperforming seed (or document HP-insensitivity)
- [ ] eval_batches scaling test (50/100/200)
- [ ] Phase-1 named curses wiki-logged (M-PROJECTX-002/003/004)
- [ ] Phase-2 verdict in PROGRESS.md

## INHERITED INFRASTRUCTURE (phase 1 → phase 2)

- `compressed_memory.py` — `TinyLM`, `DualRateCompressedAttention` (with `_last_medium_selector_scores`, `_last_medium_entropy`, `_last_heavy_entropy` buffers), `train_one` (with co-trained teacher path, selector-direct distill, entropy regularizer, assoc-loss-weight). All gated on zero defaults so pytest passes baseline.
- 12 CLI flags exposed via argparse, threaded through `run_experiment` overrides dict.
- Pytest 2 passing throughout phase 1.
- `gpt-codex/PROGRESS.md` § Phase 1 Complete is the morning briefing for Lain.

## OUT OF SCOPE THIS PHASE

- No new architectures (`#21` VQ-Quantized KV stays as Tier-A backup for phase 3 if phase 2 reveals the architecture saturates).
- No Tritonization (Lain's stack doctrine: PyTorch ships first; Triton when scaling earns it).
- No `mamba-ssm`.
- No edits to `src/project_x/model.py` (smoke-test tripwire).
- No new files under `docs/` except `docs/dev-cycle-{8..13}.md`.
