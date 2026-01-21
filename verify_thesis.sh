#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${ROOT}/.venv/bin/python"

if [[ ! -x "${PY}" ]]; then
  echo "ERROR: venv python not found at ${PY}" >&2
  exit 2
fi

export PYTHONPATH="${ROOT}"
cd "${ROOT}"

MAIN_CKPT="${1:-}"
ABLATION_A_CKPT="${2:-}"
ABLATION_B_CKPT="${3:-}"

if [[ -z "${MAIN_CKPT}" || -z "${ABLATION_A_CKPT}" ]]; then
  cat >&2 <<'USAGE'
Usage:
  bash verify_thesis.sh <MAIN_CHECKPOINT> <ABLATION_A_CHECKPOINT> [ABLATION_B_CHECKPOINT]

Purpose:
  BLUEPRINT.md Section 6 requires ablation controls to support the causal claim
  that RPJ pressure drives emergence. This script checks that:

  1) The main model PASSES the standard reproduce gates.
  2) Ablation A (lambda_E=0; no RPJ selection pressure) does NOT also pass.
  3) Optionally, Ablation B (K_max=0; no global scalars) does NOT also pass.

Notes:
  - This script does not train ablations; it evaluates provided checkpoints.
  - Create ablation checkpoints via `scripts/train_multitask_ccb.py` with:
      Ablation A: `--lambda-e 0.0`
      Ablation B: `--k-max 0`
USAGE
  exit 2
fi

echo "== Thesis Verification =="
echo "Main:      ${MAIN_CKPT}"
echo "AblationA: ${ABLATION_A_CKPT} (expected to FAIL at least one gate)"
if [[ -n "${ABLATION_B_CKPT}" ]]; then
  echo "AblationB: ${ABLATION_B_CKPT} (expected to FAIL at least one gate)"
fi

echo
echo "== Main Model (must PASS) =="
bash reproduce.sh "${MAIN_CKPT}"

run_gates_allow_fail() {
  local ckpt="$1"
  local name="$2"
  local failures=0

  echo
  echo "== ${name} Gates (should NOT all pass) =="
  echo "Checkpoint: ${ckpt}"

  if ${PY} scripts/check_k_eff.py --checkpoint "${ckpt}" --min 2 --max 6 --window 5; then
    echo "[${name}] K_eff: PASS"
  else
    echo "[${name}] K_eff: FAIL"
    failures=$((failures + 1))
  fi

  if ${PY} scripts/compute_cbr_bimodality.py --checkpoint "${ckpt}" --no-save; then
    echo "[${name}] CBR_B: PASS"
  else
    echo "[${name}] CBR_B: FAIL"
    failures=$((failures + 1))
  fi

  if ${PY} scripts/eval_doerr.py --checkpoint "${ckpt}" --doerr-max 0.25 --discrimination-min 0.80; then
    echo "[${name}] DoErr/discrimination: PASS"
  else
    echo "[${name}] DoErr/discrimination: FAIL"
    failures=$((failures + 1))
  fi

  if ${PY} scripts/eval_od_ndt.py --checkpoint "${ckpt}" --num-train-tasks 100 --num-test-tasks 100 --sr-novel-min 0.60 --transfer-min 0.80 --sleep-consolidation --sleep-steps 50 --sleep-lr 1e-3 --no-save; then
    echo "[${name}] OD-NDT: PASS"
  else
    echo "[${name}] OD-NDT: FAIL"
    failures=$((failures + 1))
  fi

  if [[ "${failures}" -eq 0 ]]; then
    echo
    echo "ERROR: ${name} unexpectedly passed ALL gates (thesis falsification)."
    return 1
  fi

  echo
  echo "OK: ${name} failed ${failures} gate(s) (counterfactual supported)."
  return 0
}

run_gates_allow_fail "${ABLATION_A_CKPT}" "Ablation A (no RPJ; lambda_E=0)"

if [[ -n "${ABLATION_B_CKPT}" ]]; then
  run_gates_allow_fail "${ABLATION_B_CKPT}" "Ablation B (no global scalars; K_max=0)"
fi

echo
echo "THESIS CHECK: PASS (main passes, ablation(s) do not)"
