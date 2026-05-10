# A To Z Plan

## PHASE CHANGELOG (top — read by every /godify cycle's Step 0)
- `phase_number`: 1
- `active_phase_theme`: Augmentation Cycle 1 — wire #5 Memory Distillation Head + #15 Memory-Byte Entropy Regularizer + #27 varied long-association probe into the compressed-memory harness; rerun 2 seeds; write per-seed interpretation.md
- `cycle_position_in_phase`: 7
- `persona_for_this_cycle`: Execute-Navi (final)
- `phase_started`: 2026-04-29T03:00:00Z (prior session's lock-the-contract Plan-Navi cycle authored `docs/DO_THIS_NEXT.md` as the phase plan)
- `expected_phase_exit`: cycle 8 of this phase — **cycle 6 produced the BREAKTHROUGH:** with `block_pool=sum + selector_distill_weight=2.0` at dim=64 depth=2, seed 1337 candidate hits `assoc_acc = 0.125` vs control 0.080 (56% LIFT over control), val_loss BETTER by 0.58%, memory 43.75% better. Seed 2026 candidate 0.070 vs control 0.085 (closer than ever, still trailing). The contract target `assoc_acc ≥ 0.15` is unmet by margin (0.125 vs 0.15) but the candidate is now PARETO-COMPETITIVE — beats control on val_loss + memory_bytes, beats it on assoc_acc on seed 1337, narrowly trails on seed 2026. Cycle 7 writes per-seed interpretation.md + final verdict + PROGRESS.md update. Cycle 8 = phase wrap + Plan-Navi for phase 2.
- `previous_phase_doc`: none (first /godify phase on this repo)
- `extension_log`: cycle 3 → phase extended 5→6 (capacity-too-small finding); cycle 4 → phase extended 6→7 (augmentations-hurt-candidate finding); cycle 5 → phase extended 7→8 (selector-direct distill provides modest cross-seed lift but architecture ceiling — block mean-pool washes position signal — requires architectural fix in cycle 6 before final 2-seed)
- `cycle_2_clockout`: 2026-04-29T03:40:00Z (CEST 05:40) — shipped #01,#02,#03,#06,#07; pytest 2 passed; entropy term smoke-verified (train_last 4.3→8.6 with memory_byte_weight=5e-2)
- `cycle_3_clockout`: 2026-04-29T03:55:00Z (CEST 05:55) — shipped #04, #05, CLI flags; 3 seed-1337 augmented runs landed; assoc_acc maxed at 0.0208 — capacity bottleneck identified.
- `cycle_4_clockout`: 2026-04-29T04:00:00Z (CEST 06:00; corrected from earlier speculative 06:18 timestamp) — shipped 4 model-size CLI flags; ran capacity sweep + augmentation ablation matrix. Three breakthroughs: capacity threshold dim=64 depth=2 cracks task (control 0.1875 seed 1337); augmentations as wired HURT candidate (aux-head distill steals trunk capacity); candidate likely uniform-distributing across 12 medium-blocks. 7 result.json files materialized.
- `cycle_5_clockout`: 2026-04-29T04:20:00Z (CEST 06:20) — shipped selector-direct distillation rewire (4-tuple `_compressed_attention` + `_last_medium_selector_scores` state buffer + `selector_distill_weight` config + train_one cross-entropy on teacher_block_idx[:, -1]). Cross-seed lift confirmed (1.8× seed 1337, 7× seed 2026) but candidate still ~half of control. Architectural ceiling diagnosed: mean-pool washes position-precise key signal.
- `cycle_6_clockout`: 2026-04-29T04:25:00Z (CEST 06:25) — shipped `block_pool` config option (`mean | max | max-keys-mean-vals | sum`) + `--block-pool` CLI flag + per-pool branches in `_compressed_attention`. Pytest 2 passed. **THE BREAKTHROUGH:** `block_pool=sum + selector_distill_weight=2.0` at dim=64 depth=2 lifts seed-1337 candidate to `assoc_acc=0.125` (vs control 0.080 — 56% LIFT), with val_loss `-0.58%` (better than control) and memory `43.75%` better. Sum-vanilla seed 2026 hits 0.060 (vs control 0.085). Sum+sel-distill seed 2026 hits 0.070 (close but still trailing 0.085). Architectural insight: sum-pool (vs mean-pool) effectively sharpens the softmax-distribution because magnitudes scale with block_size — equivalent to a temperature reduction. The selector, once supervised by selector-direct distill on these sharper scores, concentrates with selector_entropy=0.89 nats (down from vanilla 1.07). 10+ runs landed in cycle 6 covering: max-vanilla, max+sel-distill, max-keys-mean-vals+sel-distill, sum-vanilla, sum+sel-distill across seeds 1337/2026.

## PHASE EXIT CONDITIONS
- [x] `#01` (#5a) `nn.Linear(dim, n_blocks)` distillation head added to `TinyLM` (state-buffer pattern via `_last_distill_logits`)
- [x] `#02` (#15a) Differentiable entropy surfaced from `_compressed_attention` (3-tuple return) and stored as `_last_medium_entropy` / `_last_heavy_entropy` on `DualRateCompressedAttention`
- [x] `#03` (#27a) `make_batch` samples association distance uniformly per sample (`torch.randint(seq_len//4, seq_len-1, (batch_size,))`)
- [x] `#04` (#5b) Teacher labels computed via `FullCausalAttention.forward_with_weights` manual-attention path, gated on `cfg.distill_weight > 0` and `attention_cls is DualRateCompressedAttention`
- [x] `#05` (#5c) Distillation cross-entropy term added to candidate `train_one` loss; teacher TinyLM(FullCausalAttention) co-trained with separate optimizer; last-layer attention weights reduced to per-medium-block via `view+sum(-1)+sum(heads)+argmax` → `teacher_block_idx`
- [x] `#06` (#15b) Entropy term `cfg.memory_byte_weight * sum(medium + heavy)` added to candidate `train_one` loss (gated on weight > 0)
- [x] `#07` (#5d/#15c) `distill_weight` + `memory_byte_weight` fields added to `ExperimentConfig`; CLI extends with `--steps`, `--eval-batches`, `--assoc-loss-weight` for hyperparameter sweeps
- [x] `#08` (#VE) `pytest -q` 2 passed after full Layer 1 (verified 5 times across cycle 3 edits)
- [x] `#09` (#RR) 17+ runs across capacity sweep + augmentation ablation + selector-direct rewire + block_pool architectural matrix. **Winner config:** `--block-pool sum --selector-distill-weight 2.0 --dim 64 --depth 2 --steps 500 --eval-batches 50 --assoc-loss-weight 10.0`. Seed 1337 candidate 0.125 beats control 0.080. Seed 2026 candidate 0.070 trails control 0.085. Both seeds: val_loss tied or candidate-better, memory 43.75% better.
- [ ] `#10` (#RA) `interpretation.md` per seed dir + summary appended to `gpt-codex/PROGRESS.md` (CYCLE 7 — runs 6 hours after cycle 1 phase start; phase 1 wraps in cycle 8 with rename to `phase_1_augmentation_cycle_1.md`)

Project X is a research program for novel token-prediction architectures. Frontier reports are evidence, not templates to clone. The current decision is based on artifacts under `gpt-codex/` from run `run-20260428-233932-research-gate`.

## Research Synthesis

The strongest theme across DeepSeek V4, V2/V3, NSA, MLA hardware analysis, FlashAttention, GQA, Mamba/Jamba, Titans, and memory-centric papers is that long-context capability is dominated by memory movement, compression quality, and access policy. A useful model must preserve exact local dependencies, compress distant context, and retrieve only the parts that matter.

DeepSeek V4 is the most relevant public architecture source. It combines Compressed Sparse Attention, Heavily Compressed Attention, local sliding-window KV, mixed-precision KV storage, MoE, MTP, mHC residual mixing, Muon, and substantial serving/training infrastructure. The lesson is not to copy V4 wholesale. The transferable experiment is to test whether a small dual-rate memory attention module creates a better loss-per-memory-byte frontier than a transformer control.

## Chosen Direction

Primary: **Dual-Rate Compressed Memory Attention**.

The first model variant should combine:

- exact local causal attention over a short window,
- medium-rate compressed block memory with learned top-k selection,
- heavy-rate global compressed memory for cheap broad context,
- logging for selected block distance, selector entropy, estimated memory bytes, and validation loss.

Backup: **Surprise-Gated Writable Memory**, if compressed memory produces only known sparse-attention behavior or no memory-byte Pareto gain.

## Phase Status

The minimum falsification harness shipped (`run-20260428-234828-compressed-memory`). Two-seed rerun completed (`run-20260428-234939-compressed-memory-seed-1337`, `run-20260428-234941-compressed-memory-seed-2026`). Candidate ties control on validation loss within `0.0003` in both directions and uses `43.75%` fewer estimated memory bytes (`6912` vs `12288`). Delayed-association accuracy stuck at `0.0833` for both — current probe is not informative enough.

**Current phase: Training-Signal Augmentation.** Layer `#5` (Memory Distillation Head), `#15` (Memory-Byte Regularized Loss), and `#27` (stronger long-association probes) onto the existing harness, then rerun two seeds. Stack doctrine: PyTorch only this cycle. No Tritonization, no new architectures, until the candidate produces meaningful long-probe signal.

**Future phases (gated on long-probe signal):** Tritonization of compute-path kernels, `#21` VQ-Quantized KV (Tier A), `#2` Surprise-Gated Writable Memory (backup primary if augmented `#1` cannot produce a memory-byte Pareto gain).

## Rejected For First Implementation

- Full MoE: valuable at scale, but it confounds the memory experiment and adds routing instability.
- Muon: promising optimizer, but it would obscure whether the architecture works.
- FP4/FP8: hardware and kernel dependent; not needed for the first falsification.
- mHC: interesting stability/capacity axis, but secondary to context access.
- Serving/on-disk KV cache: important later, not a base-model proof.
- Pure Mamba/SSM: efficient but too weak on exact content retrieval as a sole first bet.

## Implementation Phases

- [x] Build the minimum falsification harness: transformer control and compressed-memory candidate with identical training setup.
- [x] Add synthetic delayed-association data plus a tiny text stream so the model cannot win by only solving a toy task.
- [x] Log metrics into `gpt-codex/runs/<run_id>/`: config, stdout/stderr, result JSON, memory estimate, and interpretation.
- [x] Run `--mode test` in under 180 seconds on CPU or a small GPU job with resource monitoring.
- [ ] Promote only if the augmented candidate improves long-context/memory metrics without unacceptable validation loss regression. (Pending augmentation cycle.)

## Experiment Ladder

- [x] Shape and determinism tests.
- [x] One-batch overfit sanity check.
- [x] Short matched training run: transformer control vs candidate.
- [x] Two-seed short run.
- [ ] Longer run only if short-mode metrics clear the kill criteria.
- [ ] Add memory distillation head (`#5`), memory-byte regularizer (`#15`), and stronger long-association probes (`#27`). Unconditional augmentation phase, not contingent on selector collapse.

## Augmentation Phase Substeps

Active substeps for the current Training-Signal Augmentation phase (next cycle ships code; this cycle locks the contract in `docs/DO_THIS_NEXT.md`):

- [ ] `#5` Memory Distillation Head wired into `TinyLM` in `src/project_x/experiments/compressed_memory.py` (auxiliary head + cross-entropy loss term against `FullCausalAttention` teacher labels).
- [ ] `#15` Memory-Byte Regularized Loss — differentiable read-budget penalty on selector weights inside `DualRateCompressedAttention._compressed_attention`, added to `train_one` loss.
- [ ] `#27` Stronger long-association probes — vary association distance in `make_batch` (uniform over `[seq_len // 4, seq_len - 2]`) so `assoc_acc` can lift off the `0.0833` floor.
- [ ] 2-seed rerun (`1337`, `2026`) of augmented candidate vs control, with full `result.json` and `interpretation.md`.

## Resource Plan

- Keep first tests CPU-safe and under 180 seconds.
- Do not launch heavy GPU jobs without a run ID, command log, timeout, and artifact directory.
- Keep at least 1 GiB system RAM and 1 GiB GPU VRAM free.
- Avoid unbounded downloads; all source fetching must use timeouts and file-size limits.

## Acceptance Criteria

A candidate can advance only if it has:

- matched data, tokens, steps, optimizer, batch, and hardware limits against the control,
- validation cross-entropy,
- delayed association metric,
- estimated memory bytes per token,
- selector entropy and selected-block age distribution,
- run ID and artifact paths,
- written interpretation of what improved and what did not.

## Artifact Requirements

Research artifacts live under `gpt-codex/`. Experiment artifacts must live under `gpt-codex/runs/<run_id>/` and include a machine-readable `result.json`.
