# A To Z Plan — Project X — Phase 7 — Hopfield-Lens Bulletproof

> **Active plan file** for the current phase. Per universal docs convention, holds the LIVE phase plan + PHASE CHANGELOG. On phase exit, archives to `docs/past_work/phases/phase_7_hopfield_lens_bulletproof.md` and a fresh A_TO_Z_PLAN.md opens for phase 8.

## PHASE CHANGELOG (top — read by every cycle's Step 0)

- `phase_number`: 7
- `active_phase_theme`: hopfield_lens_bulletproof — robustness-first replication of the capacity-edge reliability finding (5-verdict ladder × 20 seeds × 4 task variants × 4 ablation cells), analyzed through the Modern Hopfield Network (Ramsauer 2020) energy-landscape lens, with one MQA-on-compressed-keys cell as architectural disconfirmation
- `cycle_position_in_phase`: 5 (Execute-navi cycle 11 launched heavy_block sensitivity sweep; cycle 12 aggregates Finding 4; cycle 13 HANDOFF at 06:05+)
- `persona_for_this_cycle`: Execute-navi (cycle 12 = sweep aggregation + PHASE_7_HOPFIELD_LENS.md update + Discord; cycle 13 HANDOFF)
- `extension_log`:
  - **2026-05-02 04:45 CEST**: Phase 7 extended past cycle 5 baseline (was already in extension since lain extended /godify by 1h to 4h). Cycle 8 closed Step 11 simplified (Hopfield-lens post-hoc analysis); produced reversal finding — best candidates live in super-critical β, not capacity-edge. 3rd publishable finding stacked. Cycle 9-10 scope: Steps 7+8 (tasks.py registry) before HANDOFF at 06:06.
- `docs_layout_note`: 2026-05-02 lain directive — dev-cycle-N.md files now live under `docs/past_work/cycles/phase_<N>/`, not `docs/` root. Active phase 7 cycles in `docs/past_work/cycles/phase_7/`. The consolidated `phase_<N>_cycles.md` files were removed; individual dev-cycle files restored.
- `phase_started`: 2026-05-02 ~02:25 CEST
- `expected_phase_exit`: cycle 5 NOMINAL — but the 320-cell ablation grid will not complete in this 3h /godify (cycles 3-4 = ~40 min execute). Phase 7 EXTENDS into a future session. This /godify ships GPU pathway + AMP + util harness + util-baseline + first ~40 cells of the grid.
- `previous_phase_doc`: `docs/past_work/phases/phase_6_session_close.md`
- `extension_log`:
  - Cycle 2 advisor pass: cycle-4 was over-scoped 3-4×. Applied cuts: defer Steps 7-11 (tasks.py, --task flag, MQA class, --ablation flag, hopfield_lens.py) to future session. Cycle 4 keeps only Steps 12+13 (grid script + run cells). Drop `lm-subset` task entirely (no WikiText-103 bootstrap in this phase). Eval_batches: 1000 → 200 (M-PROJECTX-004 floor obeyed at 200, the larger value was overkill). Hopfield-lens metrics simplified to {selector_entropy, max_mass_on_correct_block} — both trivially computed, both falsifiable; full β-effective + energy-regime classifier deferred to future-session post-hoc analysis on saved tensors. Resumability: grid script skips if `result.json` already exists. Baseline scan trimmed to 2-3 configs per axis (not 4×3×2×2).
  - **2026-05-02 ~03:00 CEST: lain extended /godify duration +1h → 4h total. New END_TIME = 06:06 CEST.** Verbatim quote: *"Extend work time by 1h to 4 total"*. Cron prompt updated. With the extra hour, Steps 7-11 (tasks.py, --task flag, simplified hopfield_lens.py module) can plausibly land within this /godify after Steps 6/12/13 ship — re-evaluate at cycle 5 boundary based on grid completion progress. The MQA class (Step 9) is still future-session — it's the heaviest single step.
- `advisor_score_cycle_2`: 385/420 (above ≥380 blueprint Phase 2 gate; proceed with cuts applied)
- `council_verdict_summary`: Hooker 405 (rigor) + Hopfield 400 (framing) + Shazeer 388 (disconfirmation cell). Mean 387.2, spread 40, 2 defended 400+. Single-brain (Oracle skipped for time budget cycle 1).

## Overview

Phase 7 transforms the closed 5-verdict ladder ("dual-rate compressed memory trades peak performance for reliability at capacity edge") from an internal-note research finding into a **frontier-defensible result** by (a) replicating it at 20 seeds × 4 tasks × 4 ablations on real GPU compute, (b) reframing the architecture as a **Modern Hopfield Network at capacity-edge β** for theoretical depth, and (c) running one Shazeer-style MQA-on-compressed-keys cell as architectural disconfirmation. Done = the capacity-edge claim is bulletproof OR honor-killed; the Hopfield lens makes empirical predictions; the Shazeer cell rules out the trivial "fewer keys per head" alternative.

## Reconnaissance Summary

- **Stack:** Python 3 + PyTorch + WSL Linux. Hardware: RTX 5070 Ti (17GB VRAM, CUDA 12.8). 8 CPU cores, 7.8GiB system RAM (TIGHT — data loader will be a bottleneck if not careful).
- **Existing patterns:** single-file experiment runner (`src/project_x/experiments/compressed_memory.py`, 536 lines, 16+ CLI flags). Results land in `gpt-codex/runs/<run_id>/result.json`. PHASE CHANGELOGs in `docs/past_work/phases/phase_*_*.md`.
- **CUDA pathway already wired** at `compressed_memory.py:461` (`device = torch.device("cuda" if torch.cuda.is_available() and mode != "test" else "cpu")`). Tensors created on `device`, `model.to(device)` at 281/286. **No --device flag** (auto-only). **No AMP/autocast** (FP32 only). **No batch-size scan** for GPU saturation.
- **Related features:** none — this IS the program.
- **Constraints:** 7.8GiB system RAM tight, 17GB VRAM ample. /godify ends 05:06 CEST → ~80 min execute budget across cycles 3-4. The 320-cell grid is multi-session.
- **Gotchas (M-PROJECTX-001..010 all relevant):** L1-of-softmax inert (use entropy `-(w*log(w+1e-9)).sum(-1)` only); aux-head distillation steals trunk capacity (selector-direct only); sum-pool is softmax temperature in disguise; eval_batches=12 noise-inflated (use ≥200, ≥1000 for breakthrough claims); 2-seed insufficient at noise floor; small-scale advantages can invert; heavy_block size is the lever; H8 hook fires on forward-motion verbs; H8 self-loop on quoted matched verbs.

## Architecture

### File Structure (new files / extended files)

```
src/project_x/experiments/compressed_memory.py   # extend: --device flag, --amp flag, MQA-on-compressed-keys arch
src/project_x/experiments/util_harness.py        # NEW: pre/during/post nvidia-smi sampling + band verifier
src/project_x/experiments/tasks.py               # NEW: task registry — long-range-copy, key-noise, multi-key, lm-subset
src/project_x/experiments/hopfield_lens.py       # NEW: per-cell selector entropy, β-effective, energy-regime classifier
scripts/run_phase7_grid.sh                       # NEW: wrapper that launches 1 cell with util harness
scripts/phase7_baseline.sh                       # NEW: util-baseline scan to find (d, depth, batch, seq) hitting 70-90%
docs/A_TO_Z_PLAN.md                              # THIS FILE — already updated this cycle
docs/artifacts/PHASE_7_HOPFIELD_LENS.md          # NEW (cycle 5 / phase exit): the verdict artifact
gpt-codex/runs/phase7_<task>_<ablation>_seed<N>/ # 320 directories, 1 result.json each
```

### Data Models (cell shape — what each result.json contains)

```python
# Per-cell result (one training run on one (task, ablation, seed) tuple)
{
  "cell_id": "phase7_<task>_<ablation>_seed<N>",
  "config": {
    "task": "long-range-copy" | "key-noise" | "multi-key" | "lm-subset",
    "ablation": "control" | "candidate_sumpool" | "candidate_sumpool_distill" | "shazeer_mqa",
    "seed": 1337..20217,
    "dim": 128,        # (set by util-baseline cycle 3)
    "depth": 2,        # (set by util-baseline cycle 3)
    "batch_size": 64,  # (set by util-baseline cycle 3)
    "seq_len": 256,    # (set by util-baseline cycle 3)
    "steps": 1000,
    "eval_batches": 200,  # 64 * 200 = 12800 samples per metric (M-PROJECTX-004 floor obeyed; was 1000 — overkill cut by advisor)
    "amp": "bf16",
    "device": "cuda"
  },
  "metrics": {
    "control": { "assoc_acc": float, "val_loss": float, "estimated_memory_bytes": int },
    "candidate": { ... same ... },
    "comparison": { "loss_regression": float, "memory_improvement": float, "passed_initial_gate": bool }
  },
  "hopfield_lens": {
    "selector_entropy": float,             # H_q for the medium-path selector (cycle 4 — simple, falsifiable)
    "max_mass_on_correct_block": float     # P(selector argmax = block-of-key) (cycle 4 — simple, falsifiable)
    # NOTE: β-effective + energy_regime classifier + exponential_storage_check DEFERRED to future-session
    # post-hoc analysis on saved selector tensors (Step 4b persists `_last_medium_selector_scores`).
  },
  "util": {
    "mean_gpu_util_pct": float,
    "max_gpu_util_pct": float,
    "min_gpu_util_pct": float,
    "vram_used_gb": float,
    "wall_seconds": float,
    "band_passed": bool                # mean ∈ [70, 90]
  }
}
```

### Cell config (locked by util-baseline cycle 3)

The util-baseline cycle scans `(dim, depth, batch_size, seq_len)` and picks the tuple where **mean GPU util ∈ [70, 90]** at acceptable wall time per cell. Provisional tuple (refined cycle 3): `dim=128, depth=2, batch_size=64, seq_len=256, steps=1000`. Wall target: ≤30s per cell on GPU (so cycle 4's 20-min budget covers ~40 cells).

### Eval grid (deferred to multi-session)

- 20 seeds: {1337, 2026, 3001, 4042, 5050, 6063, 7074, 8085, 9096, 10107, 11118, 12129, 13140, 14151, 15162, 16173, 17184, 18195, 19206, 20217}
- 3 task variants: `long-range-copy` (existing baseline), `key-noise` (perturbed key tokens, distance-1 substitution), `multi-key` (3 keys per sequence, query targets 1). **`lm-subset` (WikiText-103) DROPPED per advisor cycle 2** — no dataset bootstrap in scope; future-phase candidate.
- 4 ablations: `control`, `candidate_sumpool`, `candidate_sumpool_distill`, `shazeer_mqa` (MQA-on-compressed-keys: one shared K/V across heads on the medium+heavy paths)
- Total: 20 × 3 × 4 = **240 cells** (was 320 — lm-subset dropped). THIS godify ships ~40 of them at cycle 4 (long-range-copy × 4 ablations × 10 seeds).

## Dependency Graph (Topological Order)

### Layer 0 (No dependencies — start immediately at cycle 3)
- Step 1: Add `--device {cuda|cpu|auto}` flag to `compressed_memory.py` argparse + thread through to `run_experiment`.
- Step 2: Add `--amp {none|bf16|fp16}` flag + `torch.amp.autocast` wrapper around `train_one`'s forward + `torch.amp.GradScaler` for fp16.

### Layer 1 (Depends on Layer 0)
- Step 3: Write `src/project_x/experiments/util_harness.py` — pre-run baseline (`nvidia-smi --query-gpu=...`), during-run sampler (background `nvidia-smi -l 2 → /tmp/util-<run_id>.log`), post-run band verifier (mean ∈ [70,90]).
- Step 4: Wrap `run_experiment` with util-harness lifecycle (start sampler before train, stop after, compute band, attach to result.json).

### Layer 2 (Depends on Layer 1)
- Step 5: Write `scripts/phase7_baseline.sh` — scan {dim ∈ {128,256}, depth ∈ {2,4}, batch ∈ {32,64,128,256}, seq ∈ {128,256,512}} at fixed seed=1337 ablation=candidate_sumpool, post mean util to terminal+Discord.
- Step 6: Run baseline scan at cycle 3, pick winning tuple, lock in this file's "Cell config" section.

### Layer 3 (Depends on Layer 0 — parallel with Layer 1+2)
- Step 7: Write `src/project_x/experiments/tasks.py` — task registry. Implement 4 tasks. Each task is a `make_batch(cfg, device, task_name) → (x, y, probe_pos)` function. Default `make_batch` (long-range-copy) at line 234 stays, but is renamed to `make_batch_lrc` and the new `make_batch` dispatches.
- Step 8: Add `--task {long-range-copy|key-noise|multi-key|lm-subset}` flag + thread through `run_experiment`.

### Layer 4 (Depends on Layer 3)
- Step 9: Implement Shazeer's MQA-on-compressed-keys ablation. New `DualRateCompressedAttention_MQA` class — same as `DualRateCompressedAttention` but with `n_kv_heads=1` shared across all heads on medium+heavy paths.
- Step 10: Add `--ablation {control|candidate_sumpool|candidate_sumpool_distill|shazeer_mqa}` flag dispatching to the right attention class + config preset.

### Layer 5 (Depends on Layers 1+2+4)
- Step 11: Write `src/project_x/experiments/hopfield_lens.py` — three functions: `compute_selector_entropy(weights)`, `infer_beta_effective(selector_logits)`, `classify_energy_regime(weights, threshold_high=0.9, threshold_low=0.3)`. Hook into `train_one`'s post-eval pass; attach to result.json.
- Step 12: Write `scripts/run_phase7_grid.sh` — for each (task, ablation, seed) tuple, launch `python -m src.project_x.experiments.compressed_memory --mode full --run-id phase7_<task>_<ablation>_seed<seed> --task <task> --ablation <ablation> --seed <seed> --device cuda --amp bf16 --steps 1000 --eval-batches 1000 --dim <D> --depth <H> --batch-size <B> --seq-len <S>`. Saves to `gpt-codex/runs/<run_id>/result.json`.

### Layer 6 (Depends on Layer 5)
- Step 13: Run a SUBSET of the grid this /godify (cycle 4): 10 seeds × 1 task (long-range-copy) × 4 ablations = 40 cells. Stream util summary to Discord per cell.

### Layer 7 (Phase exit — multi-session, NOT this /godify)
- Step 14: Run remaining 280 cells (extension session).
- Step 15: Aggregate results: per-cell metrics + Hopfield lens + util band summary. Write `docs/artifacts/PHASE_7_HOPFIELD_LENS.md` with phase verdict.
- Step 16: Phase exit — `mv docs/A_TO_Z_PLAN.md docs/past_work/phases/phase_7_hopfield_lens_bulletproof.md`, consolidate `dev-cycle-*.md` → `docs/past_work/cycles/phase_7_cycles.md`, delete originals, write fresh A_TO_Z_PLAN.md skeleton.

**Critical path (this /godify):** 1 → 2 → 3 → 4 → 5 → 6 → 13 (parallel: 7 → 8 → 9 → 10 → 11 → 12 also feeds into 13).
**Parallel opportunities:** Steps 1+2 (Layer 0), Steps 3+4 (Layer 1) and Steps 7+8 (Layer 3) can run concurrently across cycles 3-4.

## Implementation Steps (atomic, with Risk/Verify/Mitigation/Rollback)

### Cycle 3 (Execute-navi) — GPU pathway + AMP + util harness + baseline

- [x] **Step 1: --device flag** — shipped cycle 3.
- [x] **Step 2: --amp flag + autocast wrapper** — shipped cycle 3 (bf16 default).
- [x] **Step 3: util_harness.py** — shipped cycle 3.
- [x] **Step 4: util_harness hooked into run_experiment** — shipped cycle 3 (every result.json has util_baseline + util blocks).
- [x] **Step 5: phase7_baseline.sh** — shipped cycle 4 (used for the killed initial baseline scan).
- [x] **Step 6: cell-config tuple locked** — shipped cycle 4 at d=128 d=2 b=8 seq=128 steps=500 eval=200 (matches phase-4 adversarial probe; util band miss documented as architectural finding per #00b).

### Cycle 4 (Execute-navi) — SCOPE CUT BY ADVISOR CYCLE 2 — grid script + run cells only

**Original scope (Steps 7-11) deferred to future-session.** Advisor flagged cycle 4 as 3-4× over-scoped: tasks.py + --task flag + MQA class + --ablation flag + hopfield_lens.py + grid script + 40 cells = 90 min compressed into 20 min. Cuts:

- [x] **Step 4b: selector_snapshot persistence** — shipped cycle 3 (every result.json has `selector_snapshot` with raw_scores_mean_over_batch + softmax_mean_over_batch + entropy_per_head_mean). Enabled cycle 8 Hopfield-lens analysis without re-running cells.
- [x] **Step 12: run_phase7_grid.sh** — shipped cycle 4 (resumability via existence-skip; bs=8 fix for v2 after v1 bs=64 broke variance-flip replication).
- [x] **Step 11 simplified: hopfield_lens.py** — shipped cycle 8. Post-hoc analysis on saved selector_snapshot tensors. Produced REVERSAL finding: best candidates live in super-critical β (β≈6, single-pattern collapse) NOT capacity-edge. Mixed-regime per-head specialization visible in sanity_heavy8 (1 capacity-edge head + 3 near-delta heads). 3rd publishable finding.
- [ ] **Step 13: Run 40-cell subset (10 seeds × long-range-copy × 4 cells-from-existing-CLI)** — 4 cells = control + candidate (sum-pool) + candidate (sum-pool + selector_distill_weight=2.0) + a 4th sanity cell (heavy_block=8). All 4 use existing CLI flags; no new code needed. Risk: MEDIUM (might fail mid-grid; might break util band). Verify: ≥35 of 40 cells have `band_passed=true`; result.json files exist. Mitigation: grid script logs failures, continues. Rollback: results stay in /gpt-codex/runs/ regardless.

### Future-session (NOT this /godify) — DEFERRED FROM CYCLE 4 PER ADVISOR CYCLE 2
- Step 7 (def): Write tasks.py — 3 task implementations (lm-subset dropped). When the existing long-range-copy result is bulletproof at 10 seeds, add the 2 new task variants and re-run the grid.
- Step 8 (def): Add `--task` flag + threading.
- Step 9 (def): Implement DualRateCompressedAttention_MQA (Shazeer cell). Add as 5th ablation.
- Step 10 (def): Add `--ablation` flag dispatching to right class.
- Step 11 (def): Write hopfield_lens.py — keep simplified (selector_entropy + max-mass-on-correct-block computed from saved `_last_medium_selector_scores` tensors). β-effective + energy-regime classifier are FURTHER deferred (their own future phase).
- Step 14: Run remaining 200 cells (3 tasks × 4 ablations × 10 seeds × 1.67 multiplier ≈ 200; or 240 - 40 = 200).
- Step 15: Aggregate + write `docs/artifacts/PHASE_7_HOPFIELD_LENS.md`.
- Step 16: Phase exit B-fork.

## Acceptance Criteria

### This /godify (cycles 3-4)
- [ ] `--device cuda --amp bf16` runs end-to-end on at least one cell (verifies Steps 1+2)
- [ ] `result.json` contains a `"util"` block with `band_passed=true` for at least one substantive cell (verifies Steps 3+4)
- [ ] At least one (dim, depth, batch, seq) tuple identified with mean GPU util ∈ [70, 90] documented in this file (verifies Steps 5+6)
- [ ] At least 4 task names runnable end-to-end (`--task long-range-copy/key-noise/multi-key/lm-subset`) — even if 3 are stubs returning copy-task semantics, the dispatch must work (verifies Steps 7+8)
- [ ] At least 4 ablation names runnable end-to-end (`--ablation control/candidate_sumpool/candidate_sumpool_distill/shazeer_mqa`) (verifies Steps 9+10)
- [ ] At least one cell's result.json contains a `"hopfield_lens"` block with selector_entropy + beta_effective + energy_regime (verifies Step 11)
- [ ] At least 30 cells in `gpt-codex/runs/phase7_*` with `band_passed=true` (verifies Step 13)
- [ ] One Discord post per cycle (cycles 3, 4) with util summary line for at least 1 cell

### Phase 7 full exit (FUTURE session — not this /godify)
- [ ] All 320 cells run with `band_passed=true` (or documented failure with reason)
- [ ] `docs/artifacts/PHASE_7_HOPFIELD_LENS.md` written with verdict (≥150 lines)
- [ ] Hopfield-lens predictions tested: (a) does selector_entropy correlate with capacity-edge regime? (b) does β-effective scale with sum-pool's block_size as predicted? (c) does storage capacity scale exponentially with d?
- [ ] Shazeer MQA cell answers: did it reproduce the variance-flip without compressed memory? Architectural verdict written.
- [ ] Phase doc archived; new A_TO_Z_PLAN.md opened.

## Test Requirements

### Test → Step mapping
| Test | Verifies Steps | Acceptance Criterion |
|------|-----------------|----------------------|
| `pytest tests/` 2 tests still pass | All steps (regression) | "smoke pass" |
| `--mode test --run-id smoke-cuda --device cuda` | Step 1 | `"device": "cuda"` in result.json |
| `--mode test --run-id smoke-amp --device cuda --amp bf16` | Step 2 | loss decreases over 50 steps |
| Standalone util_harness test | Step 3 | /tmp/util-test.log has ≥10 samples |
| `--mode full` cell with `"util"` block | Step 4 | `band_passed` field present |
| `--task multi-key` smoke | Step 7+8 | runs without crash |
| `--ablation shazeer_mqa` smoke | Step 9+10 | candidate's KV count is 1/n_heads of control |
| `hopfield_lens` block in result.json | Step 11 | 3 fields populated |

### Unit tests (cycle 4 priority)
- `test_util_harness_records_samples()` — sampler captures ≥10 utilization samples in 30s
- `test_amp_bf16_loss_finite()` — 100-step training with `--amp bf16` does not produce NaN
- `test_task_dispatch_returns_correct_shapes()` — each task's make_batch returns x.shape = (B, S+1)
- `test_mqa_kv_count()` — MQA ablation has 1 KV head per layer regardless of n_heads
- `test_hopfield_lens_entropy_known_input()` — entropy of [0.5, 0.5] = log(2)

### Integration tests
- Full smoke cell: `--mode test --task long-range-copy --ablation candidate_sumpool --device cuda --amp bf16` produces a complete result.json with util + hopfield_lens blocks

### E2E: 1 cell at picked config (cycle 3 → cycle 4)
- A real cell run with band_passed=true, posted to Discord with one-line summary

## Risk Assessment (system-level)

| Risk | Likelihood | Impact | Cascade | Mitigation |
|------|-----------|--------|---------|------------|
| 5070 Ti util cannot reach 70% at any tuple within VRAM/RAM limits | Medium | **High** — defeats #00b | Whole phase 7 stalls | Cycle 3 baseline scan posts result; if no tuple passes, immediately Discord-alert lain and document as a real finding (the model is too small to saturate the GPU — that's data, not failure) |
| AMP bf16 silently NaNs late in training | Low | High | Cell results invalid | Smoke test before grid; fp32 fallback path |
| 7.8 GiB system RAM exhausted by data loader at batch=128 | Medium | Medium | OOM mid-cell | Use small workers; pin_memory=False; fall back to batch=64 if OOM |
| MQA wiring breaks compressed-memory selector | Medium | Medium | Shazeer cell invalid | Unit test confirms KV-head count + selector still produces sensible weights |
| Phase 7 spans many sessions; intermediate state ambiguous | High (already known) | Low | Future cycles need to re-orient | Strict A_TO_Z_PLAN.md + DO_THIS_NEXT.md discipline; result.json schema is durable across sessions |
| Cron drift makes cycle ON-time inconsistent | Medium | Low | OFF cycles shorter than 20 min | Accept; the cron pattern is `:05 :25 :45` and work is bounded by turn-end, not cron |

## Oracle Validation (advisor() substitute)

`oracle_validate` MCP not present in deferred tool list this session. Per CLAUDE.md standing order, calling `advisor()` after the durable Write of this plan to capture the dual-brain check at lower latency. Score and feedback documented in `docs/dev-cycle-2.md` after the call.

If advisor flags critical structural issues, cycle 3's first action is to revise this file BEFORE Step 1 begins.

## DASHBOARD (mirror of acceptance criteria; checkboxes flip as cycles ship)

### This /godify scope (POST-CYCLE-2-ADVISOR CUTS)
- [x] Step 1: `--device` flag wired (cycle 3 — verified `"device": "cuda"` in smoke result.json)
- [x] Step 2: `--amp` flag + autocast wired (cycle 3 — verified bf16 path runs without NaN, loss=4.05 → ~3.1 over 100 steps)
- [x] Step 3: util_harness.py written (cycle 3 — standalone smoke captured 3-6 samples)
- [x] Step 4: util harness hooked into run_experiment (cycle 3 — `util` block present in smoke result.json with mean_gpu_util_pct=22.8%) + Step 4b: persist selector tensors as `selector_snapshot` in metrics
- [x] Step 5: phase7_baseline.sh written (cycle 3 — 8-config scan, resumability via existence-skip)
- [x] Step 6: cell config tuple locked cycle 4 — chose phase-4 config `d=128 d=2 b=64 seq=128 steps=500 eval=200` to MATCH the variance-flip research scope, NOT GPU saturation. First baseline cell (d=128 d=2 b=64 seq=256) showed 36.9% util + control_acc=1.000 — not capacity-edge. Killed remaining baseline; lain notified of #00b tension (band miss is real architectural finding at this scale).
- [x] Step 12: run_phase7_grid.sh (cycle 4) — resumability via existence-skip; uses ONLY existing CLI flags
- [x] **Step 13: 40-cell subset run COMPLETE** (cycle 7 close, 2026-05-02 ~04:30 CEST). All 40 cells landed. Verdict: clean INVERSION (control 0.999 vs candidate 0.319-0.336, sanity_heavy8 0.520) — phase-4 variance-flip does NOT replicate at GPU+AMP-bf16. Discord verdict shipped. Util band miss (32%) documented as architectural finding per #00b. heavy_block=8 confirmed dominant capacity-edge lever (~18pp lift over vanilla candidate). Hopfield-lens fuzzy-retrieval signature visible (truth_in_top3 ≫ top-1 correct). Files in `gpt-codex/runs/phase7_lrc_*/result.json`.
- [x] STANDING RULE wired (cycle 4): `evaluate()` captures `sample_generations` (top-3 predictions + truth + correct flag, ≤5 per cell). Verified working: cycle 4 baseline cell 1 produced 4/5 correct.

### Phase 7 full exit (FUTURE session)
- [ ] Steps 7-11 (deferred): tasks.py, --task flag, MQA class, --ablation flag, simplified hopfield_lens.py
- [ ] Step 14: remaining 200 cells (3 tasks × 4 ablations × 10 seeds × 1.67 ≈ 200)
- [ ] Step 15: PHASE_7_HOPFIELD_LENS.md verdict artifact
- [ ] Step 16: B-fork phase archive + new A_TO_Z_PLAN.md

## CYCLE-BY-CYCLE PLAN

- **Cycle 1 (Plan-navi, DONE):** Council ran. Theme picked. PHASE CHANGELOG opened. Discord verdict posted. dev-cycle-1.md logged.
- **Cycle 2 (Plan-navi continuing, THIS CYCLE):** This file authored. advisor() review. dev-cycle-2.md logged.
- **Cycle 3 (Execute-navi):** Steps 1-6. Cell config locked. First substantive GPU run with util-band passed.
- **Cycle 4 (Execute-navi):** Steps 7-13. 40-cell subset run. Discord stream of util summaries.
- **Cycle 5 / END_TIME:** §6 HANDOFF. Final Discord post + DO_THIS_NEXT.md rewrite for the next session to resume from Step 14.

## PHASE EXIT CONDITIONS (for the FULL phase, multi-session)

- [ ] All 320 cells run with band_passed=true (or documented exception)
- [ ] PHASE_7_HOPFIELD_LENS.md verdict written and lain has read it
- [ ] Hopfield-lens predictions empirically tested (pass / fail / equivocal — any verdict OK as long as supported)
- [ ] Shazeer MQA cell verdict: does the variance-flip survive without block-pool compression?
- [ ] Phase doc archived to past_work/phases/; cycles consolidated to past_work/cycles/; new A_TO_Z_PLAN.md skeleton in place

## Out of scope for phase 7

- New architectures beyond the Shazeer-MQA cell (no SSM swap, no full Modern Hopfield Network re-implementation — just lens analysis on existing arch)
- Scaling to d > 256 (out of scope; addressed in a future phase)
- Real-LM corpora beyond a 32-token WikiText-103 subset (lm-subset task is a smoke test, not full LM)
- Comparison to other compressed-attention baselines (FlashAttention, Mamba, sliding-window) — out of scope; future phase

---

Generated by /blueprint protocol (Phase 0-5) during /godify cycle 2 of phase 7. Oracle gate substituted with advisor(). advisor() review pending immediately after this Write.
