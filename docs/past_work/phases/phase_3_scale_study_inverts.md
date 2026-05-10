# Phase 3 — Scale Study (does the candidate's 1.68× advantage hold or compound at dim=128 depth=4?)

## PHASE CHANGELOG (top — read by every /godify cycle's Step 0)
- `phase_number`: 3
- `active_phase_theme`: Scale Study — at `dim=128, depth=4, seq_len ∈ {48, 96, 128}`, does the candidate's phase-2 1.68× control assoc_acc advantage hold, compound (e.g., 2-3×), or saturate (collapse to 1×)? Memory_improvement should be architecturally fixed at 43.75% regardless of scale; val_loss is the secondary axis.
- `cycle_position_in_phase`: 3
- `persona_for_this_cycle`: Execute-Navi (cycle 14)
- `phase_started`: 2026-04-29T05:25:00Z (cycle 12 Plan-Navi)
- `expected_phase_exit`: cycle 5 of this phase (cycle 16 overall) — phase 3 may compress because the scale-study verdict is clear-cut after 1 cycle of data.
- `previous_phase_doc`: `docs/phase_2_cross_seed_reliability.md`
- `extension_log`: (none yet)
- `cycle_12_clockout`: 2026-04-29T05:30:00Z (CEST 07:30) — Plan-Navi authored phase 3 plan. Theme: scale study.
- `cycle_13_clockout`: 2026-04-29T05:50:00Z (CEST 07:50) — Step A `--seq-len` CLI flag pre-completed in heartbeat #10's H8-honoring tool calls. Step B smoke test + Step C 4-cell scale sweep landed. **DEFINITIVE FINDING: candidate's 1.68× phase-2 advantage INVERTS at scale.** At d=128 d=2, control assoc_acc = 1.000 (fully solves long-range copy); candidate = 0.275 (saturates). At d=128 d=4, control = 1.000, candidate = 0.330. Memory improvement holds at 43.75% architecturally. **Phase 2's win was small-scale-only**: control was undertrained at d=64 d=2 (assoc_acc 0.08 — barely above random for a learnable task). At d=128, control has the capacity to fully solve long-range copy; the compressed-memory architecture trades capacity for memory and cannot scale into solving the task.

## PHASE EXIT CONDITIONS

- [x] **`--seq-len` CLI flag added** (heartbeat #10 H8-honoring tool calls). Pytest 2 passed.
- [x] **Scale smoke test (cycle 13)** — d=128 depth=4 steps=200 fits in 21s wall (well under 180s budget). Per-step cost at full d=128 d=4 = ~36s.
- [x] **Scale sweep on seed 1337** — 4 cells at steps=500 landed. **VERDICT: candidate's 1.68× advantage INVERTS at scale.** Control hits assoc_acc=1.000 at d=128 (both d=2 and d=4); candidate stalls at 0.275-0.330. Phase-2 framing of "candidate beats control" was a small-scale phenomenon; control was capacity-bottlenecked at d=64 d=2.
- [ ] **5-seed reliability re-run at scale-best config** (eval_batches=200, 800 samples per metric) — produces the high-confidence cross-seed numbers for phase 3 verdict.
- [ ] **Phase 3 verdict in `gpt-codex/PROGRESS.md`** — does the candidate's 1.68× advantage hold/compound/saturate at scale? B-fork rename `A_TO_Z_PLAN.md` → `docs/phase_3_scale_study.md` if exit conditions met.

## RECON FINDINGS (Plan-Navi cycle 12 — kept for reference across phase 3)

Skipped formal Explore-agent recon. Project state inherited intact from phase 1+2 (full architecture + 12 CLI flags + 5 wiki entries + 30+ result.json experiment files). Key state for phase 3:

- **Winner config (phase 2):** `--block-pool sum --selector-distill-weight 2.0 --dim 64 --depth 2 --steps 500 --eval-batches 50 --assoc-loss-weight 10.0`. Phase 3 builds on this — only varies `--dim`, `--depth`, and (NEW) `--seq-len`.
- **CLI flags available:** 12 flags: `--seed`, `--distill-weight`, `--memory-byte-weight`, `--selector-distill-weight`, `--steps`, `--eval-batches`, `--assoc-loss-weight`, `--dim`, `--depth`, `--batch-size`, `--heads`, `--block-pool`. **Missing for phase 3: `--seq-len`** — must be added in cycle 13.
- **Compute envelope at d=64 depth=2:** ~19s wall per cell at steps=500. d=128 depth=4 expected at 4-8× cost = 60-150s — close to 180s budget but should fit.
- **Memory_improvement formula:** `(local + medium + heavy) / full_attention`. Local = local_window × dim × 2 (k+v). Medium = ceil(seq_len/medium_block) × dim × 2. Heavy = ceil(seq_len/heavy_block) × dim × 2. Full = seq_len × dim × 2. At seq_len=48, dim=64: full = 6144, candidate = 12+12+3 blocks × 64 × 2 = 27 × 64 × 2 = 3456. Wait that doesn't match — actual reported numbers are 12288 vs 6912. Need to verify formula at higher seq_len.
- **Phase-2 5-seed mean:** candidate 0.066 ± 0.025 vs control 0.040 ± 0.030 (1.68× ratio at eval=200). Cross-seed variance ≈ 0.025-0.030 — phase-3 effects must exceed this to be statistically meaningful.

## CYCLE-BY-CYCLE PLAN (5 cycles default)

- **Cycle 13 (Execute-Navi):** add `--seq-len` CLI flag + run scale smoke test (d=128 depth=4 at steps=200) + run 4-cell scale sweep on seed 1337. Find best-scaling config.
- **Cycle 14 (Execute-Navi):** 5-seed reliability re-run at the cycle-13-best scale config (eval_batches=200). Produce high-confidence cross-seed numbers.
- **Cycle 15 (Execute-Navi):** orthogonal axis — seq_len scaling at the best dim/depth, e.g., seq_len ∈ {48, 96, 128} on seed 1337 to see if the candidate's advantage persists or compounds at longer sequences.
- **Cycle 16 (Execute-Navi final):** write phase 3 verdict in PROGRESS.md + B-fork rename to `phase_3_scale_study.md` + fresh A_TO_Z_PLAN placeholder for phase 4 Plan-Navi at cycle 17.

## DASHBOARD (mirror of exit conditions)

- [ ] `--seq-len` CLI flag added (cycle 13 Step A)
- [ ] Scale smoke test (d=128 depth=4) within 180s budget verified (cycle 13 Step B)
- [ ] 4-cell scale sweep on seed 1337 (cycle 13 Step C)
- [ ] 5-seed reliability re-run at cycle-13-best config (cycle 14)
- [ ] Phase 3 verdict in PROGRESS.md (cycle 15-16)

## INHERITED INFRASTRUCTURE (phases 1+2 → phase 3)

- `compressed_memory.py` — full architecture: TinyLM with distill aux head, DualRateCompressedAttention with selector_scores + entropy buffers, train_one with co-trained teacher path + selector-direct distill + entropy regularizer + assoc_loss_weight. Pytest 2 passing.
- 12 CLI flags exposed (see RECON above).
- 30+ result.json files in `gpt-codex/runs/` covering all phase 1+2 experiments.
- 5 wiki entries (M-PROJECTX-001 through 005) capture phase 1+2 lessons. Phase 3 may add M-PROJECTX-006+ for scale-study findings.
- Winner config from phase 2: `--block-pool sum --selector-distill-weight 2.0 --dim 64 --depth 2 --steps 500 --eval-batches 50 --assoc-loss-weight 10.0`.

## OUT OF SCOPE THIS PHASE

- No new architectures (`#21` VQ-Quantized KV stays as Tier-A backup for phase 4 if scale study reveals saturation).
- No Tritonization (Lain's stack doctrine: PyTorch ships first; Triton when scaling earns it). Phase 3 is the moment scaling earns it ONLY IF assoc_acc compounds materially at scale.
- No `mamba-ssm`.
- No edits to `src/project_x/model.py` (smoke-test tripwire).
- No new files under `docs/` except `docs/dev-cycle-{12..16}.md`.
- No HP grid (already documented as phase-2-skip-with-rationale; the cross-seed signal is clean enough to proceed with scale).
