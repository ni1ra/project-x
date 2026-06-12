#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# Cycle 16 recurrent training permanent carry-forward rail.
#
# Scope: validates the multi-manifest combined training pipeline (Cycle 12B
# manifest + Cycle 16 manifest read together). Runs a SMOKE-level training
# (--neural-epochs 4 --neural-hidden 48) so the rail fits in the 180s
# carry-forward budget. The full 48-epoch hidden=96 Cycle 16 result lives in
# the tracked artifact run/artifacts/organic-v0/cycle16_recurrent_text_train.json
# (committed cycle 4); this rail confirms the PIPELINE is intact, not that
# the full NLL number is reproduced.
#
# What is checked:
#   - corpus rail integrity via verify_cycle16_text_scaling.sh (catches
#     any silent mutation of the cycle 16 manifest or sources)
#   - the multi-manifest training path runs end-to-end with both
#     --corpus-manifest (cycle 12) and --corpus-manifest-extra (cycle 16)
#   - the smoke training artifact records corpus_manifests_extra +
#     corpus_manifest_count fields
#   - combined train_shards > Cycle 15 baseline (319), proving the extra
#     manifest is actually being read
#   - PXNN v2 reload-hash match + same-process generation match
#   - the canonical full-training artifact (cycle16_recurrent_text_train.json)
#     still exists on disk, parses, and matches the pinned sha256 baseline
#
# Emits run/artifacts/organic-v0/cycle16_recurrent_train_verification.json
# under schema project_x.cycle16_recurrent_train_verification.v0.

ART_DIR="run/artifacts/organic-v0"
VERIFY_JSON="$ART_DIR/cycle16_recurrent_train_verification.json"
SMOKE_DIR="/tmp/cycle16-recurrent-train-rail-$$"
mkdir -p "$SMOKE_DIR"
trap 'rm -rf "$SMOKE_DIR"' EXIT

make -s build/organic_v0

timeout 150s bash scripts/verify_cycle16_text_scaling.sh > "$SMOKE_DIR/text_scaling.out" 2>&1

timeout 150s build/organic_v0 \
  --phase neural-recurrent-text \
  --corpus-manifest experience/organic-v0/corpus_manifest_v0.jsonl \
  --corpus-manifest-extra experience/organic-v0/cycle16_corpus_manifest.jsonl \
  --experience-db experience/organic-v0/cycle15_generation_prompts_v0.jsonl \
  --save-state "$SMOKE_DIR/smoke.pxnn" \
  --out "$SMOKE_DIR/smoke_train.json" \
  --event-log "$SMOKE_DIR/smoke_events.jsonl" \
  --transcript-out "$SMOKE_DIR/smoke_transcript.md" \
  --neural-hidden 48 \
  --neural-epochs 4 \
  --neural-context 16 \
  --neural-max-output-chars 80 \
  --neural-min-output-chars 8 \
  --neural-top-k 16 \
  --neural-learning-rate 0.025 \
  --neural-temperature 0.85 \
  --scenario-seed 7004 \
  --run-id cycle16-recurrent-train-rail-smoke > "$SMOKE_DIR/smoke_run.out" 2>&1

python3 - "$SMOKE_DIR/smoke_train.json" "$VERIFY_JSON" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

smoke_path = Path(sys.argv[1])
verify_path = Path(sys.argv[2])
ROOT = Path.cwd()
EXPECTED_CANONICAL_SHA256 = "44a0091966beea3f09c6dae6481f9ed0bbb63525d5f6e04e8578bd4376d9fa6e"

checks: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "passed": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


smoke = json.loads(smoke_path.read_text())

# Multi-manifest pipeline checks
check(
    "smoke_corpus_manifest_path",
    smoke.get("corpus_manifest_path") == "experience/organic-v0/corpus_manifest_v0.jsonl",
    smoke.get("corpus_manifest_path", ""),
)
check(
    "smoke_cycle_intake_id_recorded",
    smoke.get("cycle_intake_id") == "cycle16-recurrent-train-rail-smoke",
    str(smoke.get("cycle_intake_id")),
)
check(
    "smoke_corpus_manifests_extra_recorded",
    smoke.get("corpus_manifests_extra")
    == ["experience/organic-v0/cycle16_corpus_manifest.jsonl"],
    str(smoke.get("corpus_manifests_extra")),
)
check(
    "smoke_corpus_manifest_count_two",
    smoke.get("corpus_manifest_count") == 2,
    str(smoke.get("corpus_manifest_count")),
)
check(
    "smoke_train_shards_above_cycle15_baseline",
    smoke["dataset"]["train_shards"] > 319,
    f'train_shards={smoke["dataset"]["train_shards"]}',
)
check(
    "smoke_train_chars_above_cycle15_baseline",
    smoke["dataset"]["train_chars"] > 27371,
    f'train_chars={smoke["dataset"]["train_chars"]}',
)
check(
    "smoke_probe_shards_present",
    smoke["dataset"]["probe_shards"] > 0,
    str(smoke["dataset"]["probe_shards"]),
)
check(
    "smoke_holdout_shards_present",
    smoke["dataset"]["holdout_shards"] > 0,
    str(smoke["dataset"]["holdout_shards"]),
)
check(
    "smoke_reload_hash_match",
    bool(smoke.get("reload_hash_match")),
    str(smoke.get("reload_hash_match")),
)
check(
    "smoke_same_process_reload_generations_match",
    bool(smoke.get("same_process_reload_generations_match")),
    str(smoke.get("same_process_reload_generations_match")),
)
check(
    "smoke_holdout_beats_unigram",
    bool(smoke["training"].get("holdout_beats_unigram")),
    str(smoke["training"].get("holdout_beats_unigram")),
)
check(
    "smoke_neural_state_hash_present",
    bool(smoke.get("neural_state_hash")),
    str(smoke.get("neural_state_hash")),
)

# Canonical cycle-16 full-training artifact present on disk
canonical = ROOT / "run/artifacts/organic-v0/cycle16_recurrent_text_train.json"
check(
    "canonical_full_training_artifact_present",
    canonical.is_file(),
    str(canonical),
)
canonical_sha256 = sha256_file(canonical)
check(
    "canonical_artifact_sha256_pinned",
    canonical_sha256 == EXPECTED_CANONICAL_SHA256,
    canonical_sha256,
)
canonical_data = json.loads(canonical.read_text())
check(
    "canonical_artifact_cycle_intake_id",
    canonical_data.get("cycle_intake_id") == "cycle16-recurrent-text",
    str(canonical_data.get("cycle_intake_id")),
)
check(
    "canonical_artifact_has_corpus_manifests_extra",
    canonical_data.get("corpus_manifests_extra")
    == ["experience/organic-v0/cycle16_corpus_manifest.jsonl"],
    str(canonical_data.get("corpus_manifests_extra")),
)
check(
    "canonical_artifact_records_full_train_shards",
    canonical_data["dataset"]["train_shards"] >= 7990,
    f'train_shards={canonical_data["dataset"]["train_shards"]}',
)
check(
    "canonical_artifact_probe_target_met",
    bool(canonical_data["training"].get("probe_target_met")),
    str(canonical_data["training"].get("probe_target_met")),
)
check(
    "canonical_artifact_probe_nll_below_advisor_threshold",
    float(canonical_data["training"].get("probe_nll", 99.0)) <= 1.90,
    str(canonical_data["training"].get("probe_nll")),
)
check(
    "canonical_artifact_holdout_beats_unigram",
    bool(canonical_data["training"].get("holdout_beats_unigram")),
    str(canonical_data["training"].get("holdout_beats_unigram")),
)

# Cycle 16 reproducibility + source-overlap audits on disk
repro = ROOT / "run/artifacts/organic-v0/cycle16_reproducibility_audit.json"
check("reproducibility_audit_present", repro.is_file(), str(repro))
repro_data = json.loads(repro.read_text())
check(
    "reproducibility_audit_all_match",
    bool(repro_data.get("all_samples_match")),
    str(repro_data.get("all_samples_match")),
)

overlap = ROOT / "run/artifacts/organic-v0/cycle16_source_overlap_audit.json"
check("source_overlap_audit_present", overlap.is_file(), str(overlap))
overlap_data = json.loads(overlap.read_text())
check(
    "source_overlap_zero_near_copies",
    overlap_data.get("near_copy_count") == 0,
    str(overlap_data.get("near_copy_count")),
)

best_raw = ROOT / "run/artifacts/organic-v0/cycle16_best_raw_output.json"
check("best_raw_output_audit_present", best_raw.is_file(), str(best_raw))

result = {
    "schema": "project_x.cycle16_recurrent_train_verification.v0",
    "rail_mode": "smoke_4epoch_hidden48",
    "rail_purpose": (
        "Permanent carry-forward rail for Cycle 16 multi-manifest training "
        "pipeline. Validates the combined-manifest read path, persistence "
        "round-trip, and the canonical full-training artifact metrics — but "
        "does NOT retrain at full Cycle 16 hyperparams (48 epochs / hidden 96 "
        "on 7990 shards) because that exceeds the 180s carry-forward budget. "
        "The full training artifact is anchored at "
        "run/artifacts/organic-v0/cycle16_recurrent_text_train.json and this "
        "rail confirms its presence + headline metrics."
    ),
    "smoke_train_artifact_path": str(smoke_path),
    "canonical_artifact_path": "run/artifacts/organic-v0/cycle16_recurrent_text_train.json",
    "canonical_artifact_sha256": canonical_sha256,
    "expected_canonical_artifact_sha256": EXPECTED_CANONICAL_SHA256,
    "checks": checks,
    "total_checks": len(checks),
    "all_required_checks_passed": all(item["passed"] for item in checks),
    "negative_space": {
        "not_retrains_full_cycle16": True,
        "not_validates_language_quality": True,
        "not_validates_understanding": True,
        "not_validates_chat": True,
        "not_alignment_or_safety_claim": True,
    },
    "honest_interpretation": (
        "Cycle 16 recurrent training rail proves the multi-manifest pipeline is "
        "intact, the smoke training reads both cycle 12 and cycle 16 manifests, "
        "PXNN v2 persistence round-trips, and the canonical full-training "
        "artifact still exists with probe NLL below the advisor's 1.90 threshold. "
        "It does not retrain the full Cycle 16 result; that artifact is the "
        "anchored evidence."
    ),
}
verify_path.parent.mkdir(parents=True, exist_ok=True)
verify_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "all_required_checks_passed": result["all_required_checks_passed"],
            "total_checks": len(checks),
            "smoke_train_shards": smoke["dataset"]["train_shards"],
            "smoke_train_chars": smoke["dataset"]["train_chars"],
            "canonical_probe_nll": canonical_data["training"].get("probe_nll"),
        },
        sort_keys=True,
    )
)
PY

echo "wrote $VERIFY_JSON"
