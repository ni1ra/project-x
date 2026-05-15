#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ART_DIR="run/artifacts/organic-v0"
PROMPT_DB="experience/organic-v0/philosophy_prompts_v0.jsonl"
STATE_MANIFEST="experience/organic-v0/cycle11_probe_states_v0.jsonl"
OUT_JSON="$ART_DIR/quote_per_state_cycle11.json"
TRANSCRIPT="$ART_DIR/quote_per_state_cycle11_transcript.md"
EVENT_LOG="$ART_DIR/cycle11_voice_pressure_event_log.jsonl"
WRAPPER_MANIFEST="$ART_DIR/cycle11_voice_pressure_manifest.json"
VERIFY_JSON="$ART_DIR/cycle11_voice_pressure_verification.json"
TMP_ROOT="/tmp/project-x-cycle11-voice-pressure"

rm -rf "$TMP_ROOT"
mkdir -p "$TMP_ROOT" "$ART_DIR"
rm -f "$OUT_JSON" "$TRANSCRIPT" "$EVENT_LOG" "$WRAPPER_MANIFEST" "$VERIFY_JSON"

make -s build/organic_v0

timeout 180s scripts/run_organic_wrapper.py \
  --binary build/organic_v0 \
  --run-id cycle11-voice-pressure \
  --timeout-seconds 180 \
  --allowed-write-root "$ROOT/run" \
  --allowed-write-root "$ROOT/experience" \
  --allowed-write-root "$TMP_ROOT" \
  --manifest-out "$WRAPPER_MANIFEST" \
  -- \
  --phase quote-probe \
  --mode test \
  --run-id cycle11-voice-pressure \
  --state-manifest "$STATE_MANIFEST" \
  --experience-db "$PROMPT_DB" \
  --generation-max-output-chars 160 \
  --derive-raw-text-spans \
  --out "$OUT_JSON" \
  --transcript-out "$TRANSCRIPT" \
  --event-log "$EVENT_LOG" \
  --policy-tmp-root "$TMP_ROOT"

python3 - <<'PY'
import hashlib
import json
from pathlib import Path

root = Path.cwd()
artifact_path = root / "run/artifacts/organic-v0/quote_per_state_cycle11.json"
manifest_path = root / "run/artifacts/organic-v0/cycle11_voice_pressure_manifest.json"
verify_path = root / "run/artifacts/organic-v0/cycle11_voice_pressure_verification.json"
prompt_path = root / "experience/organic-v0/philosophy_prompts_v0.jsonl"
event_log_path = root / "run/artifacts/organic-v0/cycle11_voice_pressure_event_log.jsonl"
source_path = root / "native/organic_v0.cpp"

checks = []

def check(name, ok, detail=""):
    checks.append({"name": name, "passed": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")

artifact = json.loads(artifact_path.read_text())
manifest = json.loads(manifest_path.read_text())

prompt_records = []
for line_no, line in enumerate(prompt_path.read_text().splitlines(), 1):
    if not line.strip():
        continue
    record = json.loads(line)
    prompt_records.append(record)
    forbidden = {"label", "labels", "correction_output", "expected_output", "target_output", "reward", "score"}
    present = sorted(forbidden.intersection(record))
    check(f"prompt_{line_no}_unlabeled", not present, f"forbidden keys: {present}")

summary = artifact["summary_metrics"]
states = artifact["states"]
generation_count = sum(len(state["outputs"]) for state in states)

check("artifact_schema", artifact["schema"] == "project_x.quote_per_state_cycle11.v0", artifact.get("schema", ""))
check("state_count", summary["state_count"] == len(states) >= 5, str(summary["state_count"]))
check("prompt_count", summary["prompt_count"] == len(prompt_records) >= 10, str(summary["prompt_count"]))
check("generation_count", summary["generation_count"] == generation_count == len(states) * len(prompt_records), str(generation_count))
check("runtime_budget_override", artifact["generation_budget"]["runtime_override_applied"] and artifact["generation_budget"]["runtime_max_output_chars"] == 160, str(artifact["generation_budget"]))
check("no_expected_outputs", artifact["oracle_access"]["expected_outputs_present"] is False, str(artifact["oracle_access"]))
check("no_semantic_scoring", artifact["oracle_access"]["semantic_quality_scoring"] is False, str(artifact["oracle_access"]))
check("state_hash_self_checks", summary["all_state_hash_self_checks"] is True, str(summary))
check("generation_read_only", summary["all_generations_state_unchanged"] is True, str(summary))
check("nonempty_outputs", summary["nonempty_output_count"] > 0, str(summary["nonempty_output_count"]))
check("longer_than_legacy_cap", artifact["larger_budget_result"]["at_least_one_output_exceeded_legacy_cap"] is True, str(artifact["larger_budget_result"]))

for state in states:
    check(f"{state['state_id']}_hash_self_check", state["hash_self_check"] is True, state["loaded_state_hash"])
    for output in state["outputs"]:
        check(f"{state['state_id']}_{output['prompt_id']}_state_unchanged", output["state_unchanged"] is True, "")
        check(f"{state['state_id']}_{output['prompt_id']}_state_hash_link", output["state_hash_before"] == state["loaded_state_hash"], output["state_hash_before"])

event_lines = [json.loads(line) for line in event_log_path.read_text().splitlines() if line.strip()]
check("event_log_row_count", len(event_lines) == generation_count, str(len(event_lines)))
prev = "GENESIS"
for idx, row in enumerate(event_lines, 1):
    check(f"event_log_{idx}_schema", row.get("schema") == "project_x.event_log.v2", row.get("schema", ""))
    check(f"event_log_{idx}_prev_chain", row.get("prev_event_content_hash") == prev, row.get("prev_event_content_hash", ""))
    prev = row.get("event_content_hash")

check("wrapper_schema", manifest["schema"] == "project_x.run_manifest.v0", manifest.get("schema", ""))
check("wrapper_no_denial", manifest["wrapper_denial"] is False, manifest.get("wrapper_denial_reason", ""))
check("wrapper_exit_zero", manifest["exit_code"] == 0, str(manifest["exit_code"]))
check("wrapper_event_log_present", manifest["event_log_status"] == "present", manifest.get("event_log_status", ""))
check("wrapper_row_count_matches", manifest["event_log_row_count"] == generation_count, str(manifest["event_log_row_count"]))
check("wrapper_tail_hash_matches", manifest["event_log_last_event_content_hash"] == prev, str(manifest["event_log_last_event_content_hash"]))
check("wrapper_output_sha_present", bool(manifest.get("output_artifact_sha256")), str(manifest.get("output_artifact_sha256")))
actual_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
check("wrapper_output_sha_matches", manifest["output_artifact_sha256"] == actual_sha, actual_sha)

source = source_path.read_text()
start = source.index("Generation generate(")
end = source.index("\n  uint64_t state_hash()", start)
generate_body = source[start:end]
for token in ["outcome_predictor_", "predict_outcome(", "prediction_error", "select_replay_candidate", "replay_policy"]:
    check(f"a0_blind_generate_no_{token}", token not in generate_body, token)

result = {
    "schema": "project_x.cycle11_voice_pressure_verification.v0",
    "artifact_path": str(artifact_path.relative_to(root)),
    "wrapper_manifest_path": str(manifest_path.relative_to(root)),
    "event_log_path": str(event_log_path.relative_to(root)),
    "prompt_db_path": str(prompt_path.relative_to(root)),
    "checks": checks,
    "all_required_checks_passed": all(item["passed"] for item in checks),
    "honest_interpretation": "Mechanical Cycle 11 voice-pressure verification only: raw outputs are linked to loaded state hashes, event-log rows, and wrapper receipt. It does not score semantic quality or prove philosophy."
}
verify_path.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"all_required_checks_passed": result["all_required_checks_passed"], "checks": len(checks)}, sort_keys=True))
PY

echo "wrote $VERIFY_JSON"
