#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ART_DIR="run/artifacts/organic-v0"
TMP_ROOT="/tmp/project-x-cycle14-neural-text"
STATE_PATH="run/state/organic-v0/snapshots/raphael-local-0001/cycle14-neural-text-head.pxnn"

TRAIN_JSON="$ART_DIR/cycle14_neural_text_train.json"
PROBE_JSON="$ART_DIR/cycle14_neural_text_probe.json"
QUOTE_JSON="$ART_DIR/cycle14_neural_quote_outputs.json"
TRANSCRIPT="$ART_DIR/cycle14_neural_text_transcript.md"
WRAPPER_MANIFEST="$ART_DIR/cycle14_neural_text_wrapper_manifest.json"
VERIFY_JSON="$ART_DIR/cycle14_neural_text_verification.json"

rm -rf "$TMP_ROOT"
mkdir -p "$TMP_ROOT" "$ART_DIR"
rm -f "$TRAIN_JSON" "$PROBE_JSON" "$QUOTE_JSON" "$TRANSCRIPT" "$WRAPPER_MANIFEST" "$VERIFY_JSON"

make -s build/organic_v0

timeout 180s scripts/run_organic_wrapper.py \
  --binary build/organic_v0 \
  --run-id cycle14-neural-text \
  --timeout-seconds 180 \
  --allowed-write-root "$ROOT/run" \
  --allowed-write-root "$ROOT/experience" \
  --allowed-write-root "$TMP_ROOT" \
  --manifest-out "$WRAPPER_MANIFEST" \
  -- \
  --phase neural-text-quality \
  --mode test \
  --run-id cycle14-neural-text \
  --scenario-seed 7004 \
  --corpus-manifest experience/organic-v0/corpus_manifest_v0.jsonl \
  --experience-db experience/organic-v0/philosophy_prompts_v0.jsonl \
  --save-state "$STATE_PATH" \
  --out "$TRAIN_JSON" \
  --transcript-out "$TRANSCRIPT" \
  --neural-epochs 8 \
  --neural-context 16 \
  --neural-hidden 64 \
  --neural-learning-rate 0.025 \
  --neural-temperature 0.85 \
  --neural-max-output-chars 160 \
  --neural-min-output-chars 32

python3 - <<'PY'
import hashlib
import json
from pathlib import Path

ROOT = Path.cwd()
ART = ROOT / "run/artifacts/organic-v0"
TRAIN_JSON = ART / "cycle14_neural_text_train.json"
PROBE_JSON = ART / "cycle14_neural_text_probe.json"
QUOTE_JSON = ART / "cycle14_neural_quote_outputs.json"
WRAPPER_MANIFEST = ART / "cycle14_neural_text_wrapper_manifest.json"
VERIFY_JSON = ART / "cycle14_neural_text_verification.json"
MANIFEST = ROOT / "experience/organic-v0/corpus_manifest_v0.jsonl"

checks = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "passed": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def accepted_count(split: str) -> int:
    total = 0
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["filter_status"] == "accepted" and row["split"] == split:
            total += 1
    return total


def all_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from all_keys(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from all_keys(value)


artifact = load(TRAIN_JSON)
wrapper = load(WRAPPER_MANIFEST)

check("artifact_schema", artifact["schema"] == "project_x.cycle14_neural_text_quality.v0", artifact.get("schema", ""))
check("scenario_seed_recorded", artifact["model_config"]["scenario_seed"] == 7004, str(artifact["model_config"]))
check("wrapper_schema", wrapper["schema"] == "project_x.run_manifest.v0", wrapper.get("schema", ""))
check("wrapper_no_denial", wrapper["wrapper_denial"] is False, wrapper.get("wrapper_denial_reason", ""))
check("wrapper_exit_zero", wrapper["exit_code"] == 0, str(wrapper["exit_code"]))
check("wrapper_output_sha", wrapper["output_artifact_sha256"] == sha256_file(TRAIN_JSON), str(wrapper.get("output_artifact_sha256")))

dataset = artifact["dataset"]
training = artifact["training"]
quote = artifact["quote_metrics"]
outputs = artifact["quote_outputs"]

check("train_uses_all_accepted_train_shards", dataset["train_shards"] == accepted_count("train"), str(dataset))
check("probe_uses_all_accepted_probe_shards", dataset["probe_shards"] == accepted_count("probe"), str(dataset))
check("no_holdout_training_field", "holdout_shards" not in dataset, str(dataset))
check("reload_hash_match", artifact["reload_hash_match"] is True, "")
check("reload_generations_match", artifact["reload_generations_match"] is True, "")
check("state_path_under_run_state", artifact["saved_neural_state_path"].startswith("run/state/organic-v0/"), artifact["saved_neural_state_path"])
check("train_loss_decreases", training["epoch_train_nll"][0] > training["epoch_train_nll"][-1], str(training["epoch_train_nll"]))
check("probe_beats_unigram", training["probe_nll"] < training["unigram_probe_nll"], str(training))
check("probe_improvement_threshold", training["probe_nll_improvement_over_unigram_pct"] >= 10.0, str(training["probe_nll_improvement_over_unigram_pct"]))

check("quote_prompt_count", quote["prompt_count"] == 12 == len(outputs), str(quote))
check("quote_nonempty", quote["nonempty_count"] == 12, str(quote))
check("quote_no_prompt_echo", quote["prompt_echo_count"] == 0, str(quote))
check("quote_repetition_loop_count", quote["repetition_loop_count"] <= 1, str(quote))
check("quote_printable", quote["printable_output_count"] == 12, str(quote))
check("quote_end_count", quote["ended_with_end_count"] >= 10, str(quote))

for item in outputs:
    check(f"{item['prompt_id']}_nonempty", item["output_char_count"] > 0, "")
    check(f"{item['prompt_id']}_not_prompt_echo", item["prompt_echo_prefix_chars"] < len(item["prompt_text"]), str(item["prompt_echo_prefix_chars"]))
    check(f"{item['prompt_id']}_steps_present", bool(item["generation_steps"]), "")
    check(f"{item['prompt_id']}_no_loop", item["repetition_loop"] is False, "")

required_negative = {
    "not_template_generation",
    "not_pretrained_model",
    "not_hosted_model_call",
    "not_rag_or_retrieval_answer",
    "not_semantic_parser",
    "not_response_polish",
    "not_subjective_quality_score",
    "not_philosophy_claim",
    "not_understanding_claim",
    "not_chat_solved_claim",
    "not_alignment_or_safety_claim",
}
missing = sorted(key for key in required_negative if artifact["negative_space"].get(key) is not True)
check("negative_space_complete", not missing, str(missing))

banned = {"expected_output", "target_output", "quality_score", "semantic_score", "subjective_score", "label", "labels", "answer_template"}
present = sorted(key for key in all_keys(artifact) if key in banned)
check("no_oracle_or_quality_fields", not present, str(present))

probe_artifact = {
    "schema": "project_x.cycle14_neural_text_probe.v0",
    "source_artifact_path": "run/artifacts/organic-v0/cycle14_neural_text_train.json",
    "dataset": dataset,
    "training": training,
    "all_required_checks_passed": training["probe_nll"] < training["unigram_probe_nll"],
    "honest_interpretation": "Held-out probe loss evidence only. This is not semantic quality scoring.",
}
PROBE_JSON.write_text(json.dumps(probe_artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

quote_artifact = {
    "schema": "project_x.cycle14_neural_quote_outputs.v0",
    "source_artifact_path": "run/artifacts/organic-v0/cycle14_neural_text_train.json",
    "quote_metrics": quote,
    "quote_outputs": outputs,
    "all_required_checks_passed": quote["nonempty_count"] == 12 and quote["prompt_echo_count"] == 0 and quote["repetition_loop_count"] <= 1,
    "honest_interpretation": "Raw continuations from a locally trained native neural char head. They are not answer-quality or understanding claims.",
}
QUOTE_JSON.write_text(json.dumps(quote_artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

result = {
    "schema": "project_x.cycle14_neural_text_verification.v0",
    "cycle14_title": "Cycle 14: Native Neural Text Head v0",
    "acceptance_gates": {
        "gate1_native_neural_head": artifact["model_config"]["hidden"] > 0 and artifact["model_config"]["context"] > 0,
        "gate2_train_probe_split": dataset["train_shards"] == accepted_count("train") and dataset["probe_shards"] == accepted_count("probe"),
        "gate3_persist_reload": artifact["reload_hash_match"] is True and artifact["reload_generations_match"] is True,
        "gate4_probe_loss_beats_unigram": training["probe_nll_improvement_over_unigram_pct"] >= 10.0,
        "gate5_raw_quote_outputs": quote["nonempty_count"] == 12 and quote["prompt_echo_count"] == 0,
        "gate6_mechanical_text_quality": quote["repetition_loop_count"] <= 1 and quote["printable_output_count"] == 12 and quote["ended_with_end_count"] >= 10,
        "gate7_negative_space": not missing and not present,
    },
    "artifact_paths": {
        "train": "run/artifacts/organic-v0/cycle14_neural_text_train.json",
        "probe": "run/artifacts/organic-v0/cycle14_neural_text_probe.json",
        "quote": "run/artifacts/organic-v0/cycle14_neural_quote_outputs.json",
        "transcript": "run/artifacts/organic-v0/cycle14_neural_text_transcript.md",
        "wrapper": "run/artifacts/organic-v0/cycle14_neural_text_wrapper_manifest.json",
        "state": artifact["saved_neural_state_path"],
    },
    "metrics": {
        "train_shards": dataset["train_shards"],
        "probe_shards": dataset["probe_shards"],
        "final_train_nll": training["final_train_nll"],
        "probe_nll": training["probe_nll"],
        "unigram_probe_nll": training["unigram_probe_nll"],
        "probe_nll_improvement_over_unigram_pct": training["probe_nll_improvement_over_unigram_pct"],
        "quote_nonempty_count": quote["nonempty_count"],
        "quote_prompt_echo_count": quote["prompt_echo_count"],
        "quote_repetition_loop_count": quote["repetition_loop_count"],
        "quote_ended_with_end_count": quote["ended_with_end_count"],
    },
    "checks": checks,
    "all_required_checks_passed": all(item["passed"] for item in checks),
    "negative_space": {key: True for key in sorted(required_negative)},
    "honest_interpretation": (
        "Cycle 14 adds a native locally trained neural text head and verifies held-out loss "
        "plus raw output mechanics. The outputs are more text-like than Cycle 13 prompt echoes, "
        "but they remain nonsense continuations and do not prove understanding or answer quality."
    ),
}
result["all_acceptance_gates_passed"] = all(result["acceptance_gates"].values())
VERIFY_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({
    "all_required_checks_passed": result["all_required_checks_passed"],
    "all_acceptance_gates_passed": result["all_acceptance_gates_passed"],
    "checks": len(checks),
    "probe_nll_improvement_over_unigram_pct": result["metrics"]["probe_nll_improvement_over_unigram_pct"],
    "quote_repetition_loop_count": result["metrics"]["quote_repetition_loop_count"],
}, sort_keys=True))
if not result["all_required_checks_passed"] or not result["all_acceptance_gates_passed"]:
    raise SystemExit("Cycle 14 verification failed")
PY

echo "wrote $VERIFY_JSON"
