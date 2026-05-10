#!/usr/bin/env bash
# Phase 7 cycle 3 — util-baseline scan.
#
# Scans 8 (dim, depth, batch, seq) configs at fixed seed=1337 with the candidate
# sum-pool architecture, AMP bf16 on cuda. Goal: find a tuple where mean GPU
# util ∈ [70, 90] (lain #00b) AND VRAM ≤ 14 GB AND wall ≤ 30s. The winning
# tuple becomes the locked cell-config for the 240-cell ablation grid.
#
# Output: gpt-codex/runs/baseline_<dim>_<depth>_<batch>_<seq>/result.json
# Each result.json contains the "util" block with band_passed + mean_gpu_util_pct.
#
# Resumability: skip if result.json already exists.

set -euo pipefail

cd "$(dirname "$0")/.."

DIMS=(128 256)
DEPTHS=(2 4)
BATCHES=(64 128)
SEQ=256
STEPS=500    # baseline scan uses fewer steps; full grid uses 1000
EVAL_BATCHES=50  # baseline only — diagnostic, not breakthrough-claim

mkdir -p gpt-codex/runs

count=0
for dim in "${DIMS[@]}"; do
  for depth in "${DEPTHS[@]}"; do
    for batch in "${BATCHES[@]}"; do
      run_id="baseline_d${dim}_h${depth}_b${batch}_s${SEQ}"
      out="gpt-codex/runs/${run_id}/result.json"
      if [ -f "$out" ]; then
        echo "[skip] $run_id (result.json exists)"
        continue
      fi
      count=$((count + 1))
      echo "[$count/8] running $run_id (dim=$dim depth=$depth batch=$batch seq=$SEQ)..."
      python3 -m src.project_x.experiments.compressed_memory \
        --mode full \
        --run-id "$run_id" \
        --device cuda \
        --amp bf16 \
        --seed 1337 \
        --dim "$dim" \
        --depth "$depth" \
        --batch-size "$batch" \
        --seq-len "$SEQ" \
        --steps "$STEPS" \
        --eval-batches "$EVAL_BATCHES" \
        --block-pool sum \
        --selector-distill-weight 2.0 \
        --assoc-loss-weight 10.0 \
        || echo "[warn] $run_id failed (likely OOM); continuing"
    done
  done
done

echo "[done] baseline scan complete. results in gpt-codex/runs/baseline_*/result.json"
echo "[next] inspect util.mean_gpu_util_pct + band_passed across the 8 cells; pick the tuple with band_passed=true and lowest wall_seconds for the 240-cell grid."
