#!/bin/bash
# Phase 7 heavy_block sensitivity sweep — Future Work item 5 from PHASE_7_HOPFIELD_LENS.md
# 3 heavy_block values × 3 seeds = 9 cells, candidate_sumpool config.
# Skips heavy_block=8 (10-seed data already exists from main grid).
# Wall budget: 9 × ~110s = ~16-17 min.

set -u

HEAVY_BLOCKS="4 16 32"
SEEDS="1337 2026 3001"

cd "$(dirname "$0")/.."

for hb in $HEAVY_BLOCKS; do
  for seed in $SEEDS; do
    run_id="phase7_hbsweep_hb${hb}_seed${seed}"
    if [ -f "gpt-codex/runs/${run_id}/result.json" ]; then
      echo "[skip] ${run_id} already exists"
      continue
    fi
    echo "=== ${run_id} ===" >&2
    python3 -m src.project_x.experiments.compressed_memory \
      --mode full --run-id "${run_id}" \
      --device cuda --amp bf16 --seed "${seed}" \
      --dim 128 --depth 2 --batch-size 8 --seq-len 128 \
      --steps 500 --eval-batches 200 --assoc-loss-weight 10.0 \
      --block-pool sum --selector-distill-weight 0.0 \
      --heavy-block "${hb}" > "/tmp/hbsweep_${run_id}.out" 2>&1
    if [ $? -eq 0 ]; then
      echo "[ok] ${run_id}" >&2
    else
      echo "[FAIL] ${run_id} — see /tmp/hbsweep_${run_id}.out" >&2
    fi
  done
done

echo "=== HBSWEEP_COMPLETE ===" >&2
