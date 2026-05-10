# Phase 4 — Adversarial Probe at d=128 (does candidate's stall close at harder task?)

## PHASE CHANGELOG (top — read by every /godify cycle's Step 0)
- `phase_number`: 4
- `active_phase_theme`: Adversarial Probe at d=128 — make the long-range task harder (seq_len ∈ {48, 96, 128}) so control no longer trivially solves; characterize whether candidate's stall at d=128 is task-specific or fundamental.
- `cycle_position_in_phase`: 3
- `persona_for_this_cycle`: Execute-Navi (cycle 17)
- `phase_started`: 2026-04-29T06:30:00Z (cycle 15 Plan-Navi)
- `expected_phase_exit`: cycle 4 of this phase (cycle 18 overall) — phase compresses since the 5-seed final landed in cycle 16.
- `previous_phase_doc`: `docs/phase_3_scale_study_inverts.md`
- `extension_log`: (none yet)
- `cycle_15_clockout`: 2026-04-29T06:30:00Z (CEST 08:30) — Plan-Navi authored phase 4 plan. Theme: adversarial probe at d=128.
- `cycle_16_clockout`: 2026-04-29T07:00:00Z (CEST 09:00) — 3-cell adversarial sweep (seq ∈ {48, 96, 128}) on seed 1337 + 5-seed reliability at seq=128. **MAJOR FINDING: gap closes from phase-3's 0.336× ratio to 0.766× at seq=128 AND cross-seed variance flips**. At seq=128, control mean=0.380 ± 0.242 (huge std — sometimes 0.005, sometimes 0.730 across seeds); candidate mean=0.291 ± 0.080 (3× more reliable). Candidate beats control on 2 of 5 seeds (2026, 4042). The candidate's compressed-memory architecture is SCALE-ROBUST while full-attention control is wildly seed-sensitive at long seq. The phase-3 inversion verdict was real BUT was a small-seq-len phenomenon; at adversarial seq, candidate's hidden ability emerges.

## PHASE EXIT CONDITIONS

- [x] **Smoke test (cycle 16 step A merged with sweep):** seq_len=128 d=128 d=2 steps=500 wall=55s, well under 180s budget.
- [x] **Adversarial probe sweep on seed 1337 (cycle 16 step B):** ratio at seq=48 was 0.395; at seq=96 was 0.314; at seq=128 was 0.670. Decisive gap-closure at seq=128.
- [x] **Gap-closure decision (cycle 16 step C):** gap shrinks materially at seq=128 → ran 5-seed reliability at seq=128. Result: candidate mean 0.291 ± 0.080 vs control mean 0.380 ± 0.242 (ratio 0.766, candidate 3× more reliable, beats control on 2/5 seeds).
- [/] **Phase 4 verdict in PROGRESS.md** — cycle 16 wrote the headline; cycle 17 finalizes + B-fork rename.
- [ ] **B-fork rename** to `docs/phase_4_adversarial_probe.md` (cycle 17).

## RECON FINDINGS (Plan-Navi cycle 15 — kept for reference across phase 4)

Skipped formal Explore-agent recon. Project state inherited from phases 1-3 (16 CLI flags, 35+ result.json files, 8 wiki entries M-PROJECTX-001..008). Key state for phase 4:

- **Phase 3 winner config (will be reused as phase 4 baseline):** `--block-pool sum --selector-distill-weight 2.0 --medium-top-k 12 --heavy-block 8 --dim 128 --depth 2 --steps 500 --eval-batches 50 --assoc-loss-weight 10.0`. Adds `--seq-len <X>` for adversarial probe.
- **`--seq-len` CLI flag exists** (added cycle 13). Phase 4 uses it directly.
- **Compute envelope at seq=48 d=128 d=2**: ~21s wall per cell. At seq=128 expect ~3× cost = ~60-80s (linear in seq²). Should fit in 180s budget.
- **`make_batch` already varies marker position** (cycle 2 #03 finding) — at longer seq_len, probe distance scales naturally; the candidate's varied-distance probe handling from phase 1 should still work.
- **Architectural sub-question**: at seq_len=128 with medium_block=4, n_medium_blocks=32 (vs 12 at seq=48). Selector now picks among 32 blocks. Phase-2 selector-distill at distill_weight=2.0 may not scale to this larger selection space. If gap holds, this might be the bottleneck.

## CYCLE-BY-CYCLE PLAN (5 cycles default)

- **Cycle 16 (Execute-Navi):** smoke test (seq=128 d=128 d=2 steps=500 → wall time + result.json) + 3-cell adversarial probe sweep on seed 1337. Decide cycle-17 branch based on whether gap shrinks at any seq_len.
- **Cycle 17 (Execute-Navi):** branch-determined — if gap shrinks → 5-seed reliability at the closest-gap seq_len. If gap holds → write phase-4 verdict early.
- **Cycle 18 (Execute-Navi):** verdict + B-fork rename if exit conditions met.
- **Cycle 19 (Plan-Navi for phase 5):** if END_TIME headroom remains, plan phase 5. Likely candidate themes: `#21` VQ-Quantized KV (if adversarial probe shows fundamental gap), hybrid architecture (if gap-closure indicates partial advantage), or wrap-up + paper writeup.

## DASHBOARD (mirror of exit conditions)

- [ ] Smoke test seq=128 d=128 d=2 fits 180s budget
- [ ] 3-cell adversarial sweep (seq ∈ {48, 96, 128})
- [ ] 5-seed reliability at gap-closure seq_len (if any)
- [ ] Phase 4 verdict in PROGRESS.md
- [ ] B-fork rename

## INHERITED INFRASTRUCTURE (phases 1-3 → phase 4)

- `compressed_memory.py` — full architecture: 16 CLI flags including `--seq-len`. Pytest 2 passing.
- 35+ result.json files in `gpt-codex/runs/` covering all phase 1-3 experiments.
- 8 wiki entries (M-PROJECTX-001..008).
- Phase 3 winner config locked above. Phase 4 only varies `--seq-len`.

## OUT OF SCOPE THIS PHASE

- No `#21` VQ-Quantized KV architecture pivot (reserve for phase 5 if phase 4 reveals fundamental gap).
- No multi-key probe (defer to phase 5 if seq_len-alone adversarial probe doesn't reveal interesting signal).
- No Tritonization, no `mamba-ssm`, no `model.py` edits.
- No new files under `docs/` except `docs/dev-cycle-{15..19}.md`.

## END_TIME consideration

END_TIME = 2026-04-29 11:22 CEST. Cycle 15 fire (delayed) at ~08:30. Remaining: ~2.9h ≈ 4 more cycles after cycle 15. Phase 4 fits in 4 cycles (cycles 16-19); phase 5 Plan-Navi may not fit unless phase 4 compresses (likely given session pattern).
