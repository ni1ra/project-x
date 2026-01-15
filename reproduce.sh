#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${ROOT}/.venv/bin/python"

if [[ ! -x "${PY}" ]]; then
  echo "ERROR: venv python not found at ${PY}" >&2
  exit 2
fi

CHECKPOINT="${1:-results/checkpoint_multitask_ccb_final_50331648.pt}"

export PYTHONPATH="${ROOT}"

echo "== Environment =="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi -L
else
  echo "nvidia-smi not found; continuing"
fi
${PY} --version
${PY} -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'cuda_version', torch.version.cuda)"

echo
echo "== Tests =="
${PY} -m pytest tests/ -q

echo
echo "== Gates =="
echo "Checkpoint: ${CHECKPOINT}"

${PY} scripts/check_k_eff.py --checkpoint "${CHECKPOINT}" --min 2 --max 6 --window 5
${PY} scripts/compute_cbr_bimodality.py --checkpoint "${CHECKPOINT}" --no-save
${PY} scripts/eval_doerr.py --checkpoint "${CHECKPOINT}"
${PY} scripts/eval_od_ndt.py --checkpoint "${CHECKPOINT}" --sleep-consolidation --sleep-steps 50 --sleep-lr 1e-3 --no-save

echo
echo "ALL GATES: PASS"
