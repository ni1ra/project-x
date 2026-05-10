#!/usr/bin/env bash
# Phase 7 cycle 4 — 40-cell subset grid run.
#
# 10 seeds × 1 task (long-range-copy) × 4 ablations = 40 cells.
# Uses ONLY existing CLI flags (no new code per advisor cycle 2).
#
# Cell config tuple (CONFIG_*) is set from cycle 4 Step 6's baseline-scan winner.
# If baseline didn't pick a band-passing tuple, falls back to the highest-util
# cell observed (documented as #00b reality, not failure).
#
# Resumability: skip if gpt-codex/runs/<run_id>/result.json already exists.
# Output: per cell — gpt-codex/runs/phase7_lrc_<ablation>_seed<N>/result.json.
#         Each contains util block, sample_generations, and assoc_acc.

set -euo pipefail

cd "$(dirname "$0")/.."

# Cell config tuple — locked cycle 4 (v2) to MATCH phase-4 adversarial probe EXACTLY.
# Phase-4 used ExperimentConfig defaults: dim=48, batch_size=8 (NOT 64!).
# But the WINNER config from phases 1-4 was d=128 d=2 seq=128 batch_size=8.
# Cycle 4 v1 ran with batch_size=64 → control hit 1.000 (training signal too strong).
# Cycle 4 v2: lock batch_size=8 to replicate phase-4's variance-flip operating point.
CONFIG_DIM="${CONFIG_DIM:-128}"
CONFIG_DEPTH="${CONFIG_DEPTH:-2}"
CONFIG_BATCH="${CONFIG_BATCH:-8}"   # CRITICAL FIX cycle 4 v2: was 64 → reverted to phase-4 default 8
CONFIG_SEQ="${CONFIG_SEQ:-128}"

# Match phase-4 exactly: 500 steps, eval_batches=200 (M-PROJECTX-004 floor obeyed).
STEPS=500
EVAL_BATCHES=200

SEEDS=(1337 2026 3001 4042 5050 6063 7074 8085 9096 10107)
ABLATIONS=("control" "candidate_sumpool" "candidate_sumpool_distill" "sanity_heavy8")

mkdir -p gpt-codex/runs

count=0
total=$(( ${#SEEDS[@]} * ${#ABLATIONS[@]} ))
echo "[grid] CONFIG d=$CONFIG_DIM h=$CONFIG_DEPTH b=$CONFIG_BATCH s=$CONFIG_SEQ steps=$STEPS eval=$EVAL_BATCHES"
echo "[grid] running $total cells (${#SEEDS[@]} seeds × ${#ABLATIONS[@]} ablations)"

for seed in "${SEEDS[@]}"; do
  for ablation in "${ABLATIONS[@]}"; do
    run_id="phase7_lrc_${ablation}_seed${seed}"
    out="gpt-codex/runs/${run_id}/result.json"
    count=$((count + 1))
    if [ -f "$out" ]; then
      echo "[$count/$total skip] $run_id (result.json exists)"
      continue
    fi
    # Build the per-ablation flag set
    case "$ablation" in
      control)
        # Vanilla control = full attention only (no candidate-specific flags).
        # The script always trains BOTH (control + candidate); for "control"
        # ablation we just don't engage the distillation path on the candidate
        # (already the default when selector-distill-weight=0).
        ABL_FLAGS="--block-pool sum --selector-distill-weight 0.0"
        ;;
      candidate_sumpool)
        ABL_FLAGS="--block-pool sum --selector-distill-weight 0.0"
        ;;
      candidate_sumpool_distill)
        ABL_FLAGS="--block-pool sum --selector-distill-weight 2.0"
        ;;
      sanity_heavy8)
        ABL_FLAGS="--block-pool sum --selector-distill-weight 2.0 --heavy-block 8"
        ;;
      *)
        echo "[error] unknown ablation: $ablation"; continue
        ;;
    esac
    echo "[$count/$total] $run_id (ablation=$ablation seed=$seed)..."
    # shellcheck disable=SC2086
    python3 -m src.project_x.experiments.compressed_memory \
      --mode full \
      --run-id "$run_id" \
      --device cuda \
      --amp bf16 \
      --seed "$seed" \
      --dim "$CONFIG_DIM" \
      --depth "$CONFIG_DEPTH" \
      --batch-size "$CONFIG_BATCH" \
      --seq-len "$CONFIG_SEQ" \
      --steps "$STEPS" \
      --eval-batches "$EVAL_BATCHES" \
      --assoc-loss-weight 10.0 \
      $ABL_FLAGS \
      || echo "[warn] $run_id failed; continuing"
  done
done

echo "[done] grid scan complete. results in gpt-codex/runs/phase7_lrc_*/result.json"
