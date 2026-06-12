#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ART_DIR="run/artifacts/organic-v0"
TMP_ROOT="/tmp/project-x-cycle12-exposure"
PARENT_SOURCE_STATE="run/state/organic-v0/snapshots/raphael-local-0001/cycle7g-raw-spans.pxstate"
PARENT_CAP_STATE="run/state/organic-v0/snapshots/raphael-local-0001/cycle11-cycle7g-raw-spans-cap160.pxstate"
CHILD_STATE="run/state/organic-v0/snapshots/raphael-local-0001/cycle12-cycle7g-corpus-exposure.pxstate"
ABLATE_STATE="run/state/organic-v0/snapshots/raphael-local-0001/cycle12-cycle7g-corpus-exposure-ablate.pxstate"

PARENT_STATE_MANIFEST="$ART_DIR/cycle12_quote_parent_state_manifest.jsonl"
CHILD_STATE_MANIFEST="$ART_DIR/cycle12_quote_child_state_manifest.jsonl"
PARENT_QUOTE_JSON="$ART_DIR/quote_per_state_cycle12_parent.json"
PARENT_QUOTE_TRANSCRIPT="$ART_DIR/quote_per_state_cycle12_parent_transcript.md"
PARENT_QUOTE_EVENT_LOG="$ART_DIR/cycle12_quote_parent_event_log.jsonl"
PARENT_QUOTE_WRAPPER="$ART_DIR/cycle12_quote_parent_wrapper_manifest.json"
EXPOSURE_JSON="$ART_DIR/cycle12_corpus_exposure.json"
EXPOSURE_EVENT_LOG="$ART_DIR/cycle12_corpus_exposure_event_log.jsonl"
EXPOSURE_WRAPPER="$ART_DIR/cycle12_corpus_exposure_wrapper_manifest.json"
ABLATE_JSON="$ART_DIR/cycle12_corpus_exposure_ablation.json"
ABLATE_EVENT_LOG="$ART_DIR/cycle12_corpus_exposure_ablation_event_log.jsonl"
ABLATE_WRAPPER="$ART_DIR/cycle12_corpus_exposure_ablation_wrapper_manifest.json"
CHILD_QUOTE_JSON="$ART_DIR/quote_per_state_cycle12_child.json"
CHILD_QUOTE_TRANSCRIPT="$ART_DIR/quote_per_state_cycle12_child_transcript.md"
CHILD_QUOTE_EVENT_LOG="$ART_DIR/cycle12_quote_child_event_log.jsonl"
CHILD_QUOTE_WRAPPER="$ART_DIR/cycle12_quote_child_wrapper_manifest.json"
VERIFY_JSON="$ART_DIR/cycle12_exposure_verification.json"

rm -rf "$TMP_ROOT"
mkdir -p "$TMP_ROOT" "$ART_DIR"
rm -f \
  "$PARENT_STATE_MANIFEST" "$CHILD_STATE_MANIFEST" \
  "$PARENT_QUOTE_JSON" "$PARENT_QUOTE_TRANSCRIPT" "$PARENT_QUOTE_EVENT_LOG" "$PARENT_QUOTE_WRAPPER" \
  "$EXPOSURE_JSON" "$EXPOSURE_EVENT_LOG" "$EXPOSURE_WRAPPER" \
  "$ABLATE_JSON" "$ABLATE_EVENT_LOG" "$ABLATE_WRAPPER" \
  "$CHILD_QUOTE_JSON" "$CHILD_QUOTE_TRANSCRIPT" "$CHILD_QUOTE_EVENT_LOG" "$CHILD_QUOTE_WRAPPER" \
  "$VERIFY_JSON"

timeout 180s scripts/verify_cycle12_corpus.sh
make -s build/organic_v0

timeout 180s build/organic_v0 \
  --phase state-config-copy \
  --mode test \
  --run-id cycle12-parent-cap160 \
  --load-state "$PARENT_SOURCE_STATE" \
  --save-state "$PARENT_CAP_STATE" \
  --generation-max-output-chars 160

python3 - <<'PY'
from pathlib import Path

parent = {
    "schema": "project_x.cycle11_probe_state.v1",
    "state_id": "cycle12_parent_cap160",
    "parent_state_path": "run/state/organic-v0/snapshots/raphael-local-0001/cycle7g-raw-spans.pxstate",
    "state_path": "run/state/organic-v0/snapshots/raphael-local-0001/cycle11-cycle7g-raw-spans-cap160.pxstate",
    "source_artifact_path": "run/artifacts/organic-v0/text_experience_raw_spans_cycle7g.json",
    "lineage": "Cycle 12 baseline quote over the capped Cycle 11 raw-span child state",
}
child = {
    "schema": "project_x.cycle11_probe_state.v1",
    "state_id": "cycle12_child_corpus_exposed_cap160",
    "parent_state_path": "run/state/organic-v0/snapshots/raphael-local-0001/cycle11-cycle7g-raw-spans-cap160.pxstate",
    "state_path": "run/state/organic-v0/snapshots/raphael-local-0001/cycle12-cycle7g-corpus-exposure.pxstate",
    "source_artifact_path": "run/artifacts/organic-v0/cycle12_corpus_exposure.json",
    "lineage": "Cycle 12 child after manifest-backed raw corpus exposure",
}
import json
Path("run/artifacts/organic-v0/cycle12_quote_parent_state_manifest.jsonl").write_text(json.dumps(parent, separators=(",", ":")) + "\n", encoding="utf-8")
Path("run/artifacts/organic-v0/cycle12_quote_child_state_manifest.jsonl").write_text(json.dumps(child, separators=(",", ":")) + "\n", encoding="utf-8")
PY

timeout 180s scripts/run_organic_wrapper.py \
  --binary build/organic_v0 \
  --run-id cycle12-quote-parent \
  --timeout-seconds 180 \
  --allowed-write-root "$ROOT/run" \
  --allowed-write-root "$ROOT/experience" \
  --allowed-write-root "$TMP_ROOT" \
  --manifest-out "$PARENT_QUOTE_WRAPPER" \
  -- \
  --phase quote-probe \
  --mode test \
  --run-id cycle12-quote-parent \
  --state-manifest "$PARENT_STATE_MANIFEST" \
  --experience-db experience/organic-v0/philosophy_prompts_v0.jsonl \
  --out "$PARENT_QUOTE_JSON" \
  --transcript-out "$PARENT_QUOTE_TRANSCRIPT" \
  --event-log "$PARENT_QUOTE_EVENT_LOG" \
  --policy-tmp-root "$TMP_ROOT"

timeout 180s scripts/run_organic_wrapper.py \
  --binary build/organic_v0 \
  --run-id cycle12-corpus-exposure \
  --timeout-seconds 180 \
  --allowed-write-root "$ROOT/run" \
  --allowed-write-root "$ROOT/experience" \
  --allowed-write-root "$TMP_ROOT" \
  --manifest-out "$EXPOSURE_WRAPPER" \
  -- \
  --phase corpus-exposure \
  --mode test \
  --run-id cycle12-corpus-exposure \
  --load-state "$PARENT_CAP_STATE" \
  --save-state "$CHILD_STATE" \
  --corpus-manifest experience/organic-v0/corpus_manifest_v0.jsonl \
  --out "$EXPOSURE_JSON" \
  --event-log "$EXPOSURE_EVENT_LOG" \
  --corpus-exposure-max-shards 4

timeout 180s scripts/run_organic_wrapper.py \
  --binary build/organic_v0 \
  --run-id cycle12-corpus-exposure-ablation \
  --timeout-seconds 180 \
  --allowed-write-root "$ROOT/run" \
  --allowed-write-root "$ROOT/experience" \
  --allowed-write-root "$TMP_ROOT" \
  --manifest-out "$ABLATE_WRAPPER" \
  -- \
  --phase corpus-exposure \
  --mode test \
  --run-id cycle12-corpus-exposure-ablation \
  --load-state "$PARENT_CAP_STATE" \
  --save-state "$ABLATE_STATE" \
  --corpus-manifest experience/organic-v0/corpus_manifest_v0.jsonl \
  --out "$ABLATE_JSON" \
  --event-log "$ABLATE_EVENT_LOG" \
  --corpus-exposure-max-shards 4 \
  --ablate-corpus-learning

timeout 180s scripts/run_organic_wrapper.py \
  --binary build/organic_v0 \
  --run-id cycle12-quote-child \
  --timeout-seconds 180 \
  --allowed-write-root "$ROOT/run" \
  --allowed-write-root "$ROOT/experience" \
  --allowed-write-root "$TMP_ROOT" \
  --manifest-out "$CHILD_QUOTE_WRAPPER" \
  -- \
  --phase quote-probe \
  --mode test \
  --run-id cycle12-quote-child \
  --state-manifest "$CHILD_STATE_MANIFEST" \
  --experience-db experience/organic-v0/philosophy_prompts_v0.jsonl \
  --out "$CHILD_QUOTE_JSON" \
  --transcript-out "$CHILD_QUOTE_TRANSCRIPT" \
  --event-log "$CHILD_QUOTE_EVENT_LOG" \
  --policy-tmp-root "$TMP_ROOT"

python3 - <<'PY'
import hashlib
import json
from pathlib import Path

ROOT = Path.cwd()
ART = ROOT / "run/artifacts/organic-v0"
EXPOSURE_JSON = ART / "cycle12_corpus_exposure.json"
ABLATE_JSON = ART / "cycle12_corpus_exposure_ablation.json"
PARENT_QUOTE_JSON = ART / "quote_per_state_cycle12_parent.json"
CHILD_QUOTE_JSON = ART / "quote_per_state_cycle12_child.json"
VERIFY_JSON = ART / "cycle12_exposure_verification.json"

checks = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "passed": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def all_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from all_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from all_keys(item)


def wrapper_check(label: str, manifest_path: Path, artifact_path: Path, expected_rows: int) -> dict:
    manifest = load(manifest_path)
    check(label + "_wrapper_schema", manifest["schema"] == "project_x.run_manifest.v0", manifest.get("schema", ""))
    check(label + "_wrapper_no_denial", manifest["wrapper_denial"] is False, manifest.get("wrapper_denial_reason", ""))
    check(label + "_wrapper_exit_zero", manifest["exit_code"] == 0, str(manifest["exit_code"]))
    check(label + "_wrapper_event_log_present", manifest["event_log_status"] == "present", manifest.get("event_log_status", ""))
    check(label + "_wrapper_event_row_count", manifest["event_log_row_count"] == expected_rows, str(manifest["event_log_row_count"]))
    check(label + "_wrapper_output_sha", manifest["output_artifact_sha256"] == sha256_file(artifact_path), manifest.get("output_artifact_sha256", ""))
    return manifest


def quote_outputs(artifact):
    states = artifact["states"]
    check("single_state_" + artifact["run_id"], len(states) == 1, str(len(states)))
    outputs = states[0]["outputs"]
    for item in outputs:
        check(f"{artifact['run_id']}_{item['prompt_id']}_generation_read_only", item["state_hash_before"] == item["state_hash_after"], "")
        for forbidden in ["self_score", "self_grade", "semantic_score", "quality_score", "subjective_score"]:
            check(f"{artifact['run_id']}_{item['prompt_id']}_no_{forbidden}", forbidden not in item, forbidden)
    return {item["prompt_id"]: item["raw_generated_output"] for item in outputs}


exposure = load(EXPOSURE_JSON)
ablation = load(ABLATE_JSON)
parent_quote = load(PARENT_QUOTE_JSON)
child_quote = load(CHILD_QUOTE_JSON)

check("exposure_schema", exposure["schema"] == "project_x.corpus_exposure_cycle12.v1", exposure.get("schema", ""))
check("ablation_schema", ablation["schema"] == "project_x.corpus_exposure_cycle12.v1", ablation.get("schema", ""))
check("parent_child_hash_differs", exposure["parent_state_hash"] != exposure["child_state_hash"], "")
check("reload_matches_child", exposure["reload_state_hash"] == exposure["child_state_hash"], "")
check("ablation_hash_unchanged", ablation["parent_state_hash"] == ablation["child_state_hash"] == ablation["reload_state_hash"], "")
check("exposure_reload_bit_exact", exposure["child_reload_bit_exact"] is True, "")
check("ablation_reload_bit_exact", ablation["child_reload_bit_exact"] is True, "")
check("exposure_selected_shards", exposure["exposure_config"]["selected_train_shards"] == 4, str(exposure["exposure_config"]["selected_train_shards"]))
check("ablation_selected_shards", ablation["exposure_config"]["selected_train_shards"] == 4, str(ablation["exposure_config"]["selected_train_shards"]))

for idx, item in enumerate(exposure["exposure_history"], 1):
    check(f"exposure_history_{idx}_learned", item["learning_applied"] is True, "")
    check(f"exposure_history_{idx}_changed", item["state_before_hash"] != item["state_after_hash"], "")
    check(f"exposure_history_{idx}_accepted", item["filter_status"] == "accepted", item["filter_status"])
    check(f"exposure_history_{idx}_raw_only", item["observations"] and all(obs.startswith("raw_utterance:") for obs in item["observations"]), str(item["observations"]))
for idx, item in enumerate(ablation["exposure_history"], 1):
    check(f"ablation_history_{idx}_not_learned", item["learning_applied"] is False, "")
    check(f"ablation_history_{idx}_unchanged", item["state_before_hash"] == item["state_after_hash"], "")

for label, artifact in [("exposure", exposure), ("ablation", ablation)]:
    banned = {"correction_output", "expected_output", "target_output", "label", "labels", "reward", "score", "self_score", "self_grade", "semantic_score", "quality_score", "subjective_score"}
    present = sorted(key for key in all_keys(artifact) if key in banned)
    check(label + "_no_label_or_score_fields", not present, str(present))

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
    "not_byte_count_as_progress",
    "not_dedup_as_understanding",
    "not_filter_as_quality_judgment",
    "not_source_diversity_as_competence",
    "not_internet_clean_data_claim",
    "not_state_growth_as_understanding",
    "not_author_voice_imitation_claim",
    "not_curator_intelligence_claim",
}
missing_negative = sorted(key for key in required_negative if exposure["negative_space"].get(key) is not True)
check("exposure_negative_space_complete", not missing_negative, str(missing_negative))

parent_outputs = quote_outputs(parent_quote)
child_outputs = quote_outputs(child_quote)
check("quote_prompt_sets_match", set(parent_outputs) == set(child_outputs), "")
changed = [pid for pid in sorted(parent_outputs) if parent_outputs[pid] != child_outputs[pid]]
unchanged = [pid for pid in sorted(parent_outputs) if parent_outputs[pid] == child_outputs[pid]]
check("changed_quote_prompt_count_positive", len(changed) >= 1, str(len(changed)))

wrapper_check("parent_quote", ART / "cycle12_quote_parent_wrapper_manifest.json", PARENT_QUOTE_JSON, len(parent_outputs))
wrapper_check("child_quote", ART / "cycle12_quote_child_wrapper_manifest.json", CHILD_QUOTE_JSON, len(child_outputs))
wrapper_check("exposure", ART / "cycle12_corpus_exposure_wrapper_manifest.json", EXPOSURE_JSON, exposure["exposure_config"]["selected_train_shards"])
wrapper_check("ablation", ART / "cycle12_corpus_exposure_ablation_wrapper_manifest.json", ABLATE_JSON, ablation["exposure_config"]["selected_train_shards"])

source = (ROOT / "native/organic_v0.cpp").read_text(encoding="utf-8")
gen_start = source.index("Generation generate(")
gen_end = source.index("\n  uint64_t state_hash()", gen_start)
generate_body = source[gen_start:gen_end]
exp_start = source.index("void corpus_exposure_phase(")
exp_end = source.index("\n// Orchestrate the persistence round-trip", exp_start)
exposure_body = source[exp_start:exp_end]
for token in ["outcome_predictor_", "predict_outcome(", "prediction_error", "select_replay_candidate", "replay_policy"]:
    check(f"a0_blind_generate_no_{token}", token not in generate_body, token)
    check(f"a0_blind_exposure_no_{token}", token not in exposure_body, token)

result = {
    "schema": "project_x.cycle12_exposure_verification.v1",
    "artifact_paths": {
        "corpus_verification": "run/artifacts/organic-v0/cycle12_corpus_verification.json",
        "exposure": "run/artifacts/organic-v0/cycle12_corpus_exposure.json",
        "exposure_wrapper": "run/artifacts/organic-v0/cycle12_corpus_exposure_wrapper_manifest.json",
        "ablation": "run/artifacts/organic-v0/cycle12_corpus_exposure_ablation.json",
        "parent_quote": "run/artifacts/organic-v0/quote_per_state_cycle12_parent.json",
        "child_quote": "run/artifacts/organic-v0/quote_per_state_cycle12_child.json",
    },
    "candidate_shards": exposure["candidate_shards"],
    "accepted_shards": exposure["accepted_shards"],
    "rejected_shards": exposure["rejected_shards"],
    "accepted_shards_over_candidate_shards_pct": exposure["accepted_shards_over_candidate_shards_pct"],
    "bytes_candidate": exposure["bytes_candidate"],
    "bytes_accepted": exposure["bytes_accepted"],
    "bytes_accepted_over_bytes_candidate_pct": exposure["bytes_accepted_over_bytes_candidate_pct"],
    "duplicate_count": exposure["duplicate_count"],
    "duplicate_rate": exposure["duplicate_rate"],
    "rejection_reason_counts": exposure["rejection_reason_counts"],
    "parent_state_hash": exposure["parent_state_hash"],
    "child_state_hash": exposure["child_state_hash"],
    "reload_state_hash": exposure["reload_state_hash"],
    "changed_quote_prompt_count": len(changed),
    "unchanged_quote_prompt_count": len(unchanged),
    "changed_prompt_ids": changed,
    "checks": checks,
    "all_required_checks_passed": all(item["passed"] for item in checks),
    "negative_space": {key: True for key in sorted(required_negative)},
    "honest_interpretation": (
        "Cycle 12B proves only that one-source manifest-backed unlabeled corpus exposure "
        "can mutate persisted state, reload bit-exactly, and mechanically change raw quote-probe output. "
        "It does not prove language quality."
    ),
}
VERIFY_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"all_required_checks_passed": result["all_required_checks_passed"], "checks": len(checks), "changed_quote_prompt_count": len(changed)}, sort_keys=True))
PY

echo "wrote $VERIFY_JSON"
