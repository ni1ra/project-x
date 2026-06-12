#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ART_DIR="run/artifacts/organic-v0"
TMP_ROOT="/tmp/project-x-cycle13-diagnostics"
PARENT_CAP_STATE="run/state/organic-v0/snapshots/raphael-local-0001/cycle11-cycle7g-raw-spans-cap160.pxstate"
REP_STATE="run/state/organic-v0/snapshots/raphael-local-0001/cycle13-repetition-child.pxstate"
FILTER_STATE="run/state/organic-v0/snapshots/raphael-local-0001/cycle13-content-filter-ablation.pxstate"

REP_JSON="$ART_DIR/cycle13_repetition_fix.json"
REP_EVENT_LOG="$ART_DIR/cycle13_repetition_fix_event_log.jsonl"
REP_WRAPPER="$ART_DIR/cycle13_repetition_fix_wrapper_manifest.json"
REP_STATE_MANIFEST="$ART_DIR/cycle13_repetition_state_manifest.jsonl"
REP_QUOTE_JSON="$ART_DIR/quote_per_state_cycle13_repetition_child.json"
REP_QUOTE_TRANSCRIPT="$ART_DIR/quote_per_state_cycle13_repetition_child_transcript.md"
REP_QUOTE_EVENT_LOG="$ART_DIR/cycle13_repetition_quote_event_log.jsonl"
REP_QUOTE_WRAPPER="$ART_DIR/cycle13_repetition_quote_wrapper_manifest.json"
FILTER_JSON="$ART_DIR/cycle13_content_filter_ablation.json"
FILTER_EVENT_LOG="$ART_DIR/cycle13_content_filter_ablation_event_log.jsonl"
FILTER_WRAPPER="$ART_DIR/cycle13_content_filter_ablation_wrapper_manifest.json"
NO_REWRITE_JSON="$ART_DIR/cycle13_corpus_no_rewrite_verification.json"
DIAG_JSON="$ART_DIR/cycle13_quote_delta_diagnostics.json"
VERIFY_JSON="$ART_DIR/cycle13_verification.json"

NO_REWRITE_STDOUT="$TMP_ROOT/no_rewrite.stdout"
NO_REWRITE_STDERR="$TMP_ROOT/no_rewrite.stderr"
TMP_MANIFEST="$TMP_ROOT/cycle13-mutated-manifest.jsonl"

rm -rf "$TMP_ROOT"
mkdir -p "$TMP_ROOT" "$ART_DIR"
rm -f \
  "$REP_JSON" "$REP_EVENT_LOG" "$REP_WRAPPER" "$REP_STATE_MANIFEST" \
  "$REP_QUOTE_JSON" "$REP_QUOTE_TRANSCRIPT" "$REP_QUOTE_EVENT_LOG" "$REP_QUOTE_WRAPPER" \
  "$FILTER_JSON" "$FILTER_EVENT_LOG" "$FILTER_WRAPPER" \
  "$NO_REWRITE_JSON" "$DIAG_JSON" "$VERIFY_JSON"

timeout 180s scripts/verify_cycle12_exposure.sh
make -s build/organic_v0

python3 - <<'PY'
import json
from pathlib import Path

record = {
    "schema": "project_x.cycle11_probe_state.v1",
    "state_id": "cycle13_repetition_child_cap160",
    "parent_state_path": "run/state/organic-v0/snapshots/raphael-local-0001/cycle11-cycle7g-raw-spans-cap160.pxstate",
    "state_path": "run/state/organic-v0/snapshots/raphael-local-0001/cycle13-repetition-child.pxstate",
    "source_artifact_path": "run/artifacts/organic-v0/cycle13_repetition_fix.json",
    "lineage": "Cycle 13 child after corpus exposure with mechanical repetition-loop END pressure",
}
Path("run/artifacts/organic-v0/cycle13_repetition_state_manifest.jsonl").write_text(
    json.dumps(record, separators=(",", ":")) + "\n",
    encoding="utf-8",
)
PY

timeout 180s scripts/run_organic_wrapper.py \
  --binary build/organic_v0 \
  --run-id cycle13-repetition-fix \
  --timeout-seconds 180 \
  --allowed-write-root "$ROOT/run" \
  --allowed-write-root "$ROOT/experience" \
  --allowed-write-root "$TMP_ROOT" \
  --manifest-out "$REP_WRAPPER" \
  -- \
  --phase corpus-exposure \
  --mode test \
  --run-id cycle13-repetition-fix \
  --load-state "$PARENT_CAP_STATE" \
  --save-state "$REP_STATE" \
  --corpus-manifest experience/organic-v0/corpus_manifest_v0.jsonl \
  --out "$REP_JSON" \
  --event-log "$REP_EVENT_LOG" \
  --corpus-exposure-max-shards 4 \
  --reward-repetition-penalty 16.0

timeout 180s scripts/run_organic_wrapper.py \
  --binary build/organic_v0 \
  --run-id cycle13-repetition-quote \
  --timeout-seconds 180 \
  --allowed-write-root "$ROOT/run" \
  --allowed-write-root "$ROOT/experience" \
  --allowed-write-root "$TMP_ROOT" \
  --manifest-out "$REP_QUOTE_WRAPPER" \
  -- \
  --phase quote-probe \
  --mode test \
  --run-id cycle13-repetition-quote \
  --state-manifest "$REP_STATE_MANIFEST" \
  --experience-db experience/organic-v0/philosophy_prompts_v0.jsonl \
  --out "$REP_QUOTE_JSON" \
  --transcript-out "$REP_QUOTE_TRANSCRIPT" \
  --event-log "$REP_QUOTE_EVENT_LOG" \
  --policy-tmp-root "$TMP_ROOT"

timeout 180s scripts/run_organic_wrapper.py \
  --binary build/organic_v0 \
  --run-id cycle13-content-filter-ablation \
  --timeout-seconds 180 \
  --allowed-write-root "$ROOT/run" \
  --allowed-write-root "$ROOT/experience" \
  --allowed-write-root "$TMP_ROOT" \
  --manifest-out "$FILTER_WRAPPER" \
  -- \
  --phase corpus-exposure \
  --mode test \
  --run-id cycle13-content-filter-ablation \
  --load-state "$PARENT_CAP_STATE" \
  --save-state "$FILTER_STATE" \
  --corpus-manifest experience/organic-v0/corpus_manifest_v0.jsonl \
  --out "$FILTER_JSON" \
  --event-log "$FILTER_EVENT_LOG" \
  --corpus-exposure-max-shards 4 \
  --ablate-content-filter \
  --ablate-corpus-learning

REAL_MANIFEST="experience/organic-v0/corpus_manifest_v0.jsonl"
REAL_BEFORE_SHA="$(sha256sum "$REAL_MANIFEST" | awk '{print $1}')"
cp "$REAL_MANIFEST" "$TMP_MANIFEST"
python3 - "$TMP_MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
rows[0]["sha256"] = "0" * 64
path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
PY

set +e
CYCLE13_TEST_MANIFEST_PATH="$TMP_MANIFEST" timeout 180s scripts/prepare_cycle12_corpus.sh >"$NO_REWRITE_STDOUT" 2>"$NO_REWRITE_STDERR"
NO_REWRITE_STATUS=$?
set -e
REAL_AFTER_SHA="$(sha256sum "$REAL_MANIFEST" | awk '{print $1}')"

NO_REWRITE_STATUS="$NO_REWRITE_STATUS" \
REAL_BEFORE_SHA="$REAL_BEFORE_SHA" \
REAL_AFTER_SHA="$REAL_AFTER_SHA" \
TMP_MANIFEST="$TMP_MANIFEST" \
NO_REWRITE_STDOUT="$NO_REWRITE_STDOUT" \
NO_REWRITE_STDERR="$NO_REWRITE_STDERR" \
NO_REWRITE_JSON="$NO_REWRITE_JSON" \
python3 - <<'PY'
import json
import os
from pathlib import Path

status = int(os.environ["NO_REWRITE_STATUS"])
stdout_path = Path(os.environ["NO_REWRITE_STDOUT"])
stderr_path = Path(os.environ["NO_REWRITE_STDERR"])
stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
mutation_detected = "manifest row would be silently mutated" in stdout + stderr
real_unchanged = os.environ["REAL_BEFORE_SHA"] == os.environ["REAL_AFTER_SHA"]
result = {
    "schema": "project_x.cycle13_corpus_no_rewrite_verification.v0",
    "real_manifest_path": "experience/organic-v0/corpus_manifest_v0.jsonl",
    "real_manifest_sha256_before": os.environ["REAL_BEFORE_SHA"],
    "real_manifest_sha256_after": os.environ["REAL_AFTER_SHA"],
    "real_manifest_unchanged": real_unchanged,
    "temp_manifest_path": os.environ["TMP_MANIFEST"],
    "prepare_exit_code": status,
    "mutation_detected": mutation_detected,
    "stdout_path": str(stdout_path),
    "stderr_path": str(stderr_path),
    "stdout_tail": stdout[-1000:],
    "stderr_tail": stderr[-1000:],
    "all_required_checks_passed": status != 0 and mutation_detected and real_unchanged,
    "honest_interpretation": (
        "The no-rewrite rail is tested against a mutated /tmp manifest through "
        "CYCLE13_TEST_MANIFEST_PATH. The real manifest is not mutated or restored."
    ),
}
Path(os.environ["NO_REWRITE_JSON"]).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
if not result["all_required_checks_passed"]:
    raise SystemExit(json.dumps(result, sort_keys=True))
PY

python3 - <<'PY'
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
ART = ROOT / "run/artifacts/organic-v0"

PATHS = {
    "cycle12_parent_quote": ART / "quote_per_state_cycle12_parent.json",
    "cycle12_child_quote": ART / "quote_per_state_cycle12_child.json",
    "cycle12_exposure": ART / "cycle12_corpus_exposure.json",
    "cycle13_repetition": ART / "cycle13_repetition_fix.json",
    "cycle13_repetition_quote": ART / "quote_per_state_cycle13_repetition_child.json",
    "cycle13_filter_ablation": ART / "cycle13_content_filter_ablation.json",
    "cycle13_no_rewrite": ART / "cycle13_corpus_no_rewrite_verification.json",
    "cycle13_diagnostics": ART / "cycle13_quote_delta_diagnostics.json",
    "cycle13_verification": ART / "cycle13_verification.json",
}

checks = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "passed": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wrapper_check(label: str, manifest_path: Path, artifact_path: Path, expected_rows: int) -> dict:
    manifest = load(manifest_path)
    check(label + "_wrapper_schema", manifest["schema"] == "project_x.run_manifest.v0", manifest.get("schema", ""))
    check(label + "_wrapper_no_denial", manifest["wrapper_denial"] is False, manifest.get("wrapper_denial_reason", ""))
    check(label + "_wrapper_exit_zero", manifest["exit_code"] == 0, str(manifest["exit_code"]))
    check(label + "_wrapper_event_log_present", manifest["event_log_status"] == "present", manifest.get("event_log_status", ""))
    check(label + "_wrapper_event_row_count", manifest["event_log_row_count"] == expected_rows, str(manifest["event_log_row_count"]))
    check(label + "_wrapper_output_sha", manifest["output_artifact_sha256"] == sha256_file(artifact_path), manifest.get("output_artifact_sha256", ""))
    return manifest


def outputs_by_prompt(artifact: dict) -> dict[str, dict]:
    check("single_state_" + artifact["run_id"], len(artifact["states"]) == 1, str(len(artifact["states"])))
    result = {}
    for item in artifact["states"][0]["outputs"]:
        check(f"{artifact['run_id']}_{item['prompt_id']}_read_only", item["state_hash_before"] == item["state_hash_after"], "")
        result[item["prompt_id"]] = item
    return result


def generation_ended(item: dict) -> bool:
    steps = item["activated_memory_state"].get("generation_steps", [])
    return bool(steps and steps[-1].get("chosen") == "<END>")


def corpus_trace_ids(item: dict) -> list[str]:
    traces = item["activated_memory_state"].get("activated_traces", [])
    return [row["event_id"] for row in traces if row.get("event_id", "").startswith("cycle12_")]


def copy_boundary_count(item: dict) -> int:
    return int(item["activated_memory_state"].get("copy_boundary_feature_count", 0))


def max_cap_hit(item: dict) -> bool:
    return int(item["output_char_count"]) >= 160 and not generation_ended(item)


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def repeated_suffix_loop(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text.lower()).strip()
    n = len(compact)
    for width in range(4, min(32, n // 2) + 1):
        if 3 * width <= n and compact[-width:] == compact[-2 * width:-width] == compact[-3 * width:-2 * width]:
            return True
    words = tokens(compact)
    counts = Counter(words)
    if len(compact) >= 80 and any(count >= 5 for word, count in counts.items() if len(word) >= 4):
        return True
    return False


def dominant_token_count(text: str) -> int:
    words = tokens(text)
    return max(Counter(words).values(), default=0)


def longest_repeated_char_run(text: str) -> int:
    best = 0
    current = 0
    prev = None
    for ch in text:
        if ch == prev:
            current += 1
        else:
            current = 1
            prev = ch
        best = max(best, current)
    return best


parent_quote = load(PATHS["cycle12_parent_quote"])
child_quote = load(PATHS["cycle12_child_quote"])
cycle12_exposure = load(PATHS["cycle12_exposure"])
repetition = load(PATHS["cycle13_repetition"])
repetition_quote = load(PATHS["cycle13_repetition_quote"])
filter_ablation = load(PATHS["cycle13_filter_ablation"])
no_rewrite = load(PATHS["cycle13_no_rewrite"])

parent_outputs = outputs_by_prompt(parent_quote)
child_outputs = outputs_by_prompt(child_quote)
rep_outputs = outputs_by_prompt(repetition_quote)
check("prompt_sets_match", set(parent_outputs) == set(child_outputs) == set(rep_outputs), "")

changed = [pid for pid in sorted(parent_outputs) if parent_outputs[pid]["raw_generated_output"] != child_outputs[pid]["raw_generated_output"]]
unchanged = [pid for pid in sorted(parent_outputs) if parent_outputs[pid]["raw_generated_output"] == child_outputs[pid]["raw_generated_output"]]
check("cycle12_changed_prompt_count_exact", len(changed) == 11, str(changed))
check("cycle12_unchanged_prompt_count_exact", len(unchanged) == 1, str(unchanged))

child_max_cap = sum(max_cap_hit(item) for item in child_outputs.values())
rep_max_cap = sum(max_cap_hit(item) for item in rep_outputs.values())
child_loop_count = sum(repeated_suffix_loop(item["raw_generated_output"]) for item in child_outputs.values())
rep_loop_count = sum(repeated_suffix_loop(item["raw_generated_output"]) for item in rep_outputs.values())
rep_end_count = sum(generation_ended(item) for item in rep_outputs.values())
rep_nonrepetitive = sum((not max_cap_hit(item)) and (not repeated_suffix_loop(item["raw_generated_output"])) for item in rep_outputs.values())
rep_copy_boundary = sum(copy_boundary_count(item) > 0 for item in rep_outputs.values())

check("cycle13_repetition_weight_recorded", repetition["exposure_config"]["reward_repetition_penalty"] == 16, str(repetition["exposure_config"]))
check("cycle13_repetition_parent_hash_configured", repetition["loaded_parent_state_hash"] != repetition["parent_state_hash"], "")
check("cycle13_repetition_child_changed", repetition["parent_state_hash"] != repetition["child_state_hash"], "")
check("cycle13_repetition_reload_exact", repetition["child_state_hash"] == repetition["reload_state_hash"], "")
check("cycle13_repetition_selected_shards", repetition["exposure_config"]["selected_train_shards"] == 4, str(repetition["exposure_config"]))
check("cycle13_max_cap_reduced", rep_max_cap <= 1 and rep_max_cap < child_max_cap, f"{child_max_cap} -> {rep_max_cap}")
check("cycle13_loop_count_reduced", rep_loop_count < child_loop_count, f"{child_loop_count} -> {rep_loop_count}")
check("cycle13_end_count", rep_end_count >= 11, str(rep_end_count))
check("cycle13_nonrepetitive_count", rep_nonrepetitive >= 10, str(rep_nonrepetitive))
check("cycle13_copy_boundary_driver_count", rep_copy_boundary >= 8, str(rep_copy_boundary))

check("filter_ablation_learning_disabled", filter_ablation["ablation"]["corpus_learning_disabled"] is True, str(filter_ablation["ablation"]))
check("filter_ablation_filter_disabled", filter_ablation["ablation"]["content_filter_disabled"] is True, str(filter_ablation["ablation"]))
check("filter_ablation_state_unchanged", filter_ablation["parent_state_hash"] == filter_ablation["child_state_hash"] == filter_ablation["reload_state_hash"], "")
check("filter_ablation_selected_shards", filter_ablation["exposure_config"]["selected_train_shards"] == 4, str(filter_ablation["exposure_config"]))
for idx, item in enumerate(filter_ablation["exposure_history"], 1):
    check(f"filter_ablation_{idx}_selected_rejected", item["filter_status"] == "rejected", item["filter_status"])
    check(f"filter_ablation_{idx}_learning_off", item["learning_applied"] is False, "")
    check(f"filter_ablation_{idx}_state_unchanged", item["state_before_hash"] == item["state_after_hash"], "")

check("no_rewrite_test_passed", no_rewrite["all_required_checks_passed"] is True, str(no_rewrite))

wrapper_check("cycle13_repetition", ART / "cycle13_repetition_fix_wrapper_manifest.json", PATHS["cycle13_repetition"], 4)
wrapper_check("cycle13_repetition_quote", ART / "cycle13_repetition_quote_wrapper_manifest.json", PATHS["cycle13_repetition_quote"], len(rep_outputs))
wrapper_check("cycle13_filter_ablation", ART / "cycle13_content_filter_ablation_wrapper_manifest.json", PATHS["cycle13_filter_ablation"], 4)

required_negative = {
    "not_fluency_claim",
    "not_philosophy_claim",
    "not_chat_capability",
    "not_semantic_quality_claim",
    "not_ui_layer",
    "not_pretrained_route",
    "not_template_route",
    "not_tokenizer_route",
    "not_pretrained_encoder_route",
    "not_a0_improvement",
    "not_sandbox_or_security",
    "not_benchmark_ladder_advance",
    "not_an_alignment_or_safety_claim",
    "not_license_laundering",
    "not_curated_corpus_as_capability",
    "not_state_growth_as_understanding",
    "not_author_voice_imitation_claim",
}
for artifact_name, artifact in [("repetition", repetition), ("filter_ablation", filter_ablation)]:
    missing = sorted(key for key in required_negative if artifact["negative_space"].get(key) is not True)
    check(artifact_name + "_negative_space_complete", not missing, str(missing))

source = (ROOT / "native/organic_v0.cpp").read_text(encoding="utf-8")
gen_start = source.index("Generation generate(")
gen_end = source.index("\n  uint64_t state_hash()", gen_start)
generate_body = source[gen_start:gen_end]
for token in ["outcome_predictor_", "predict_outcome(", "prediction_error", "select_replay_candidate", "replay_policy"]:
    check(f"a0_blind_generate_no_{token}", token not in generate_body, token)

per_prompt = []
for pid in sorted(parent_outputs):
    parent = parent_outputs[pid]
    child = child_outputs[pid]
    rep = rep_outputs[pid]
    child_corpus = corpus_trace_ids(child)
    rep_corpus = corpus_trace_ids(rep)
    driver = []
    if child_corpus:
        driver.append("cycle12_corpus_trace_activation")
    if copy_boundary_count(rep):
        driver.append("copy_boundary_end_feature")
    if repeated_suffix_loop(child["raw_generated_output"]) and not repeated_suffix_loop(rep["raw_generated_output"]):
        driver.append("repetition_loop_suppressed")
    if max_cap_hit(child) and not max_cap_hit(rep):
        driver.append("max_cap_hit_removed")
    if max_cap_hit(rep):
        driver.append("residual_no_copy_boundary_loop")
    per_prompt.append({
        "prompt_id": pid,
        "cycle12_child_differs_from_parent": pid in changed,
        "cycle12_child_corpus_trace_ids": child_corpus,
        "cycle12_child_output_char_count": child["output_char_count"],
        "cycle12_child_max_cap_hit": max_cap_hit(child),
        "cycle12_child_repetition_loop": repeated_suffix_loop(child["raw_generated_output"]),
        "cycle13_output_char_count": rep["output_char_count"],
        "cycle13_ended_with_end": generation_ended(rep),
        "cycle13_max_cap_hit": max_cap_hit(rep),
        "cycle13_repetition_loop": repeated_suffix_loop(rep["raw_generated_output"]),
        "cycle13_copy_boundary_feature_count": copy_boundary_count(rep),
        "cycle13_corpus_trace_ids": rep_corpus,
        "cycle13_distinct_char_count": len(set(rep["raw_generated_output"])),
        "cycle13_dominant_token_count": dominant_token_count(rep["raw_generated_output"]),
        "cycle13_longest_repeated_char_run": longest_repeated_char_run(rep["raw_generated_output"]),
        "mechanical_driver": driver,
        "raw_outputs": {
            "cycle12_parent": parent["raw_generated_output"],
            "cycle12_child": child["raw_generated_output"],
            "cycle13_repetition_child": rep["raw_generated_output"],
        },
    })

diagnostics = {
    "schema": "project_x.cycle13_quote_delta_diagnostics.v0",
    "cycle13_title": "Cycle 13: Quote-Delta Diagnostics + Mechanical Repetition-Loop Suppression",
    "artifact_paths": {name: str(path.relative_to(ROOT)) for name, path in PATHS.items() if name != "cycle13_verification"},
    "changed_prompt_count": len(changed),
    "unchanged_prompt_count": len(unchanged),
    "changed_prompt_ids": changed,
    "metrics": {
        "cycle12_child_max_cap_hits": child_max_cap,
        "cycle13_repetition_child_max_cap_hits": rep_max_cap,
        "cycle12_child_repetition_loop_count": child_loop_count,
        "cycle13_repetition_child_repetition_loop_count": rep_loop_count,
        "cycle13_repetition_child_end_count": rep_end_count,
        "cycle13_repetition_child_nonrepetitive_count": rep_nonrepetitive,
        "cycle13_copy_boundary_driver_prompt_count": rep_copy_boundary,
    },
    "content_filter_ablation": {
        "selected_train_shards": filter_ablation["exposure_config"]["selected_train_shards"],
        "selected_filter_statuses": [item["filter_status"] for item in filter_ablation["exposure_history"]],
        "state_unchanged": filter_ablation["parent_state_hash"] == filter_ablation["child_state_hash"] == filter_ablation["reload_state_hash"],
    },
    "per_prompt": per_prompt,
    "negative_space": {
        "driver_means_surface_mechanical_correlate_not_semantic_cause": True,
        "not_language_quality_claim": True,
        "not_understanding_claim": True,
        "not_chat_or_alignment_claim": True,
        "not_pretrained_or_template_route": True,
    },
    "honest_interpretation": (
        "Cycle 13 localizes Cycle 12B quote changes to prompt-local corpus trace activation "
        "and tests one mechanical generator hygiene pressure. The repetition child reduces "
        "max-cap repetition loops by learning a post-copy END feature and applying a suffix-loop "
        "penalty. It mostly stops after copying the raw prompt, so this is not semantic answer quality."
    ),
}
PATHS["cycle13_diagnostics"].write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

verification = {
    "schema": "project_x.cycle13_verification.v0",
    "cycle13_title": diagnostics["cycle13_title"],
    "acceptance_gates": {
        "gate1_quote_delta_diagnostics": len(changed) == 11 and all(corpus_trace_ids(child_outputs[pid]) for pid in changed),
        "gate2_content_filter_ablation": filter_ablation["ablation"]["content_filter_disabled"] is True and all(item["filter_status"] == "rejected" for item in filter_ablation["exposure_history"]) and filter_ablation["parent_state_hash"] == filter_ablation["child_state_hash"],
        "gate3_manifest_no_rewrite_temp_rail": no_rewrite["all_required_checks_passed"] is True,
        "gate4_trace_and_delta_localization": rep_copy_boundary >= 8 and repetition["state_growth"]["connection_feature_count_delta"] > 0,
        "gate5_repetition_loop_suppression": rep_max_cap <= 1 and rep_loop_count < child_loop_count and rep_end_count >= 11 and rep_nonrepetitive >= 10,
        "gate6_carry_forward_negative_space": True,
    },
    "metrics": diagnostics["metrics"],
    "state_hashes": {
        "cycle12_loaded_parent": cycle12_exposure["loaded_parent_state_hash"],
        "cycle12_parent": cycle12_exposure["parent_state_hash"],
        "cycle12_child": cycle12_exposure["child_state_hash"],
        "cycle13_repetition_loaded_parent": repetition["loaded_parent_state_hash"],
        "cycle13_repetition_parent": repetition["parent_state_hash"],
        "cycle13_repetition_child": repetition["child_state_hash"],
        "cycle13_content_filter_ablation_child": filter_ablation["child_state_hash"],
    },
    "artifact_paths": {name: str(path.relative_to(ROOT)) for name, path in PATHS.items() if name != "cycle13_verification"},
    "checks": checks,
    "all_required_checks_passed": all(item["passed"] for item in checks),
    "negative_space": diagnostics["negative_space"],
    "honest_interpretation": diagnostics["honest_interpretation"],
}
verification["all_acceptance_gates_passed"] = all(verification["acceptance_gates"].values())
PATHS["cycle13_verification"].write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({
    "all_required_checks_passed": verification["all_required_checks_passed"],
    "all_acceptance_gates_passed": verification["all_acceptance_gates_passed"],
    "checks": len(checks),
    "cycle12_child_max_cap_hits": child_max_cap,
    "cycle13_repetition_child_max_cap_hits": rep_max_cap,
    "cycle13_end_count": rep_end_count,
    "cycle13_nonrepetitive_count": rep_nonrepetitive,
}, sort_keys=True))
if not verification["all_required_checks_passed"] or not verification["all_acceptance_gates_passed"]:
    raise SystemExit("Cycle 13 verification failed")
PY

echo "wrote $VERIFY_JSON"
