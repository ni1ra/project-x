#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BIN="build/organic_v0"
WRAPPER="scripts/run_organic_wrapper.py"
TIMEOUT="${TIMEOUT:-180s}"
WRAPPER_TIMEOUT_SECONDS="${WRAPPER_TIMEOUT_SECONDS:-180}"
ARTIFACT_DIR="run/artifacts/organic-v0"
RUN_ROOT="$(mktemp -d /tmp/cycle10_wrapper.XXXXXX)"

make -s "$BIN"
mkdir -p "$ARTIFACT_DIR"

run_cmd() {
  local name="$1"
  shift
  printf '[cycle10-wrapper] %s\n' "$name" >&2
  timeout "$TIMEOUT" "$@"
}

run_wrapper_allow_fail() {
  local name="$1"
  shift
  printf '[cycle10-wrapper] %s\n' "$name" >&2
  timeout "$TIMEOUT" "$@"
}

CLEAN_ROOT="$RUN_ROOT/clean"
mkdir -p "$CLEAN_ROOT"
run_cmd clean_wrapper_run "$WRAPPER" \
  --binary "$BIN" \
  --run-id cycle10-clean-run \
  --timeout-seconds "$WRAPPER_TIMEOUT_SECONDS" \
  --allowed-write-root "$ROOT" \
  --allowed-write-root "$CLEAN_ROOT" \
  --manifest-out "$ARTIFACT_DIR/cycle10_wrapper_manifest_clean_run.json" \
  -- \
  --phase daemon-lite \
  --mode test \
  --run-id cycle10-clean-run \
  --daemon-run-seconds 1 \
  --daemon-tick-sleep-ms 0 \
  --policy-tmp-root "$CLEAN_ROOT" \
  --event-log "$CLEAN_ROOT/log.jsonl" \
  --out "$CLEAN_ROOT/clean.json"

TRUNCATE_ROOT="$RUN_ROOT/truncate"
mkdir -p "$TRUNCATE_ROOT"
M1="$TRUNCATE_ROOT/M1.json"
M2="$TRUNCATE_ROOT/M2.json"
TRUNCATE_LOG="$TRUNCATE_ROOT/log.jsonl"

run_cmd truncate_baseline "$WRAPPER" \
  --binary "$BIN" \
  --run-id cycle10-truncate-baseline \
  --timeout-seconds "$WRAPPER_TIMEOUT_SECONDS" \
  --allowed-write-root "$ROOT" \
  --allowed-write-root "$TRUNCATE_ROOT" \
  --manifest-out "$M1" \
  -- \
  --phase daemon-lite \
  --mode test \
  --run-id cycle10-truncate-baseline \
  --daemon-run-seconds 1 \
  --daemon-tick-sleep-ms 0 \
  --policy-tmp-root "$TRUNCATE_ROOT" \
  --event-log "$TRUNCATE_LOG" \
  --out "$TRUNCATE_ROOT/baseline.json"

: > "$TRUNCATE_LOG"
set +e
run_wrapper_allow_fail truncate_restart "$WRAPPER" \
  --binary "$BIN" \
  --run-id cycle10-truncate-restart \
  --timeout-seconds "$WRAPPER_TIMEOUT_SECONDS" \
  --allowed-write-root "$ROOT" \
  --allowed-write-root "$TRUNCATE_ROOT" \
  --manifest-out "$M2" \
  --prior-manifest "$M1" \
  -- \
  --phase daemon-lite \
  --mode test \
  --run-id cycle10-truncate-restart \
  --daemon-run-seconds 1 \
  --daemon-tick-sleep-ms 0 \
  --policy-tmp-root "$TRUNCATE_ROOT" \
  --event-log "$TRUNCATE_LOG" \
  --out "$TRUNCATE_ROOT/restart.json"
TRUNCATE_WRAPPER_RC=$?
set -e

: > "$TRUNCATE_LOG"
set +e
run_cmd truncate_native_alone_control "$BIN" \
  --phase daemon-lite \
  --mode test \
  --run-id cycle10-truncate-native-alone \
  --daemon-run-seconds 1 \
  --daemon-tick-sleep-ms 0 \
  --policy-tmp-root "$TRUNCATE_ROOT" \
  --event-log "$TRUNCATE_LOG" \
  --out "$TRUNCATE_ROOT/native-alone.json"
NATIVE_ALONE_RC=$?
set -e

M1="$M1" M2="$M2" RUN_ROOT="$RUN_ROOT" TRUNCATE_ROOT="$TRUNCATE_ROOT" \
TRUNCATE_WRAPPER_RC="$TRUNCATE_WRAPPER_RC" NATIVE_ALONE_RC="$NATIVE_ALONE_RC" \
ARTIFACT="$ARTIFACT_DIR/cycle10_wrapper_truncate_test.json" python3 - <<'PY'
import json
import os
from pathlib import Path
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load(path):
    return json.loads(Path(path).read_text())


def event_log_count(path):
    p = Path(path)
    if not p.exists():
        return 0
    return sum(1 for line in p.read_text().splitlines() if line.strip())


m1 = load(os.environ["M1"])
m2 = load(os.environ["M2"])
truncate_root = Path(os.environ["TRUNCATE_ROOT"])
native_artifact = truncate_root / "native-alone.json"
native_log = truncate_root / "log.jsonl"
wrapper_rc = int(os.environ["TRUNCATE_WRAPPER_RC"])
native_rc = int(os.environ["NATIVE_ALONE_RC"])
checks = [
    {
        "name": "baseline_manifest_nonzero_rows",
        "passed": m1.get("event_log_row_count", 0) > 0,
        "actual": m1.get("event_log_row_count"),
        "expected": ">0",
    },
    {
        "name": "restart_binary_itself_exited_zero",
        "passed": m2.get("exit_code") == 0,
        "actual": m2.get("exit_code"),
        "expected": 0,
    },
    {
        "name": "wrapper_denied_restart_against_prior_anchor",
        "passed": bool(m2.get("wrapper_denial")),
        "actual": m2.get("wrapper_denial"),
        "expected": True,
    },
    {
        "name": "wrapper_exit_nonzero_on_anchor_mismatch",
        "passed": wrapper_rc != 0,
        "actual": wrapper_rc,
        "expected": "nonzero",
    },
    {
        "name": "native_alone_control_exited_zero",
        "passed": native_rc == 0,
        "actual": native_rc,
        "expected": 0,
    },
    {
        "name": "native_alone_control_wrote_event_log",
        "passed": event_log_count(native_log) > 0,
        "actual": event_log_count(native_log),
        "expected": ">0",
    },
]
failed = [check for check in checks if not check["passed"]]
result = {
    "schema": "project_x.cycle10_wrapper_truncate_test.v0",
    "run_id": "cycle10-wrapper-truncate-test",
    "timestamp_utc": utc_now(),
    "test_root": str(Path(os.environ["RUN_ROOT"]).resolve()),
    "baseline_manifest_path": str(Path(os.environ["M1"]).resolve()),
    "restart_manifest_path": str(Path(os.environ["M2"]).resolve()),
    "baseline_manifest": m1,
    "restart_manifest": m2,
    "comparison_verdict": {
        "wrapper_truncate_detect_verdict": m2.get("wrapper_truncate_detect_verdict"),
        "wrapper_truncate_detect_details": m2.get("wrapper_truncate_detect_details"),
        "wrapper_denial": m2.get("wrapper_denial"),
        "wrapper_denial_reason": m2.get("wrapper_denial_reason"),
        "wrapper_exit_code": wrapper_rc,
        "binary_exit_code_inside_wrapper": m2.get("exit_code"),
    },
    "native_alone_control": {
        "command": [
            "build/organic_v0",
            "--phase", "daemon-lite",
            "--mode", "test",
            "--run-id", "cycle10-truncate-native-alone",
            "--daemon-run-seconds", "1",
            "--daemon-tick-sleep-ms", "0",
            "--policy-tmp-root", str(truncate_root.resolve()),
            "--event-log", str(native_log.resolve()),
            "--out", str(native_artifact.resolve()),
        ],
        "exit_code": native_rc,
        "artifact_path": str(native_artifact.resolve()),
        "event_log_path": str(native_log.resolve()),
        "event_log_row_count": event_log_count(native_log),
        "interpretation": (
            "Native daemon-lite can start on a zero-length log and write an internally "
            "clean v2 chain. The wrapper rejects the same truncate/restart shape only "
            "because it compares against the prior external manifest."
        ),
    },
    "checks": checks,
    "failed_checks": failed,
    "all_required_checks_passed": not failed,
    "negative_space": {
        "not_sandboxed": True,
        "not_secure": True,
        "not_alignment_solution": True,
        "not_tool_use_safety": True,
        "not_full_resource_limit": True,
        "not_supply_chain_safety": True,
        "anchor_only": True,
    },
    "honest_interpretation": (
        "Cycle 10 closes the current short-runtime external anchor gap by binding a "
        "prior manifest's event-log row count and final event_content_hash to the next "
        "wrapper run. It does not provide sandbox escape resistance, resource limits, "
        "or broader safety guarantees."
    ),
}
Path(os.environ["ARTIFACT"]).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
if failed:
    raise SystemExit(1)
PY

PATH_DENIAL_ROOT="$RUN_ROOT/path-denial"
mkdir -p "$PATH_DENIAL_ROOT"
set +e
run_wrapper_allow_fail path_denial "$WRAPPER" \
  --binary "$BIN" \
  --run-id cycle10-path-denial \
  --timeout-seconds "$WRAPPER_TIMEOUT_SECONDS" \
  --allowed-write-root "$ROOT" \
  --manifest-out /etc/should-not-write.json \
  -- \
  --phase daemon-lite \
  --mode test \
  --run-id cycle10-path-denial \
  --daemon-run-seconds 1 \
  --daemon-tick-sleep-ms 0 \
  --policy-tmp-root "$PATH_DENIAL_ROOT" \
  --event-log "$PATH_DENIAL_ROOT/log.jsonl" \
  --out /etc/binary-output.json
PATH_DENIAL_RC=$?
set -e

PATH_DENIAL_DEFAULT="$ARTIFACT_DIR/run_manifests/cycle10-path-denial.json"
PATH_DENIAL_DEFAULT="$PATH_DENIAL_DEFAULT" PATH_DENIAL_RC="$PATH_DENIAL_RC" \
ARTIFACT="$ARTIFACT_DIR/cycle10_wrapper_manifest_path_denial.json" python3 - <<'PY'
import json
import os
from pathlib import Path

manifest = json.loads(Path(os.environ["PATH_DENIAL_DEFAULT"]).read_text())
manifest["path_denial_wrapper_exit_code"] = int(os.environ["PATH_DENIAL_RC"])
manifest["path_denial_required_checks"] = [
    {
        "name": "wrapper_exited_nonzero",
        "passed": int(os.environ["PATH_DENIAL_RC"]) != 0,
        "actual": int(os.environ["PATH_DENIAL_RC"]),
        "expected": "nonzero",
    },
    {
        "name": "wrapper_denial_true",
        "passed": bool(manifest.get("wrapper_denial")),
        "actual": manifest.get("wrapper_denial"),
        "expected": True,
    },
    {
        "name": "binary_not_launched",
        "passed": not bool(manifest.get("binary_launched")),
        "actual": manifest.get("binary_launched"),
        "expected": False,
    },
    {
        "name": "invalid_manifest_out_recorded",
        "passed": manifest.get("rejected_manifest_out_path") == "/etc/should-not-write.json",
        "actual": manifest.get("rejected_manifest_out_path"),
        "expected": "/etc/should-not-write.json",
    },
]
manifest["all_required_checks_passed"] = all(check["passed"] for check in manifest["path_denial_required_checks"])
Path(os.environ["ARTIFACT"]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
if not manifest["all_required_checks_passed"]:
    raise SystemExit(1)
PY

CARRY_SCRIPT="$RUN_ROOT/verify_cycle9_for_cycle10.sh"
CARRY_ARTIFACT="$ARTIFACT_DIR/cycle10_carry_forward_verification.json"
ROOT="$ROOT" CARRY_SCRIPT="$CARRY_SCRIPT" CARRY_ARTIFACT="$CARRY_ARTIFACT" python3 - <<'PY'
import os
from pathlib import Path

source = Path("scripts/verify_cycle9_carry_forward.sh").read_text()
source = source.replace(
    'ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"',
    f'ROOT="{os.environ["ROOT"]}"',
)
source = source.replace(
    'ARTIFACT="run/artifacts/organic-v0/cycle9_carry_forward_verification.json"',
    f'ARTIFACT="{os.environ["CARRY_ARTIFACT"]}"',
)
Path(os.environ["CARRY_SCRIPT"]).write_text(source)
Path(os.environ["CARRY_SCRIPT"]).chmod(0o755)
PY
run_cmd cycle10_carry_forward "$CARRY_SCRIPT"

CARRY_ARTIFACT="$CARRY_ARTIFACT" CARRY_SCRIPT="$CARRY_SCRIPT" python3 - <<'PY'
import json
import os
from pathlib import Path

artifact = Path(os.environ["CARRY_ARTIFACT"])
doc = json.loads(artifact.read_text())
suffix = doc.get("run_id", "cycle9-carry-forward-unknown").split("cycle9-carry-forward-", 1)[-1]
doc["run_id"] = "cycle10-carry-forward-" + suffix
doc["source_harness"] = "scripts/verify_cycle9_carry_forward.sh"
doc["cycle10_temp_harness_path"] = os.environ["CARRY_SCRIPT"]
doc["honest_interpretation"] = (
    "Fresh Cycle 10 carry-forward rerun over the listed substrate rails. This verifies "
    "bit-exact hashes and expected held-out/probe/ablation scores for those rails only. "
    "Wrapper-lite anchoring is tested separately in cycle10_wrapper_truncate_test.json. "
    "This does not solve alignment, AGI safety, sandbox escape resistance, broader "
    "tool-use safety, or A0 predictor usefulness."
)
artifact.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
PY

printf '{"artifact_dir":"%s","run_root":"%s","all_required_checks_passed":true}\n' "$ARTIFACT_DIR" "$RUN_ROOT"
