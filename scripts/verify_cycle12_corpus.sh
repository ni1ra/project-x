#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ART_DIR="run/artifacts/organic-v0"
VERIFY_JSON="$ART_DIR/cycle12_corpus_verification.json"

timeout 180s scripts/prepare_cycle12_corpus.sh

python3 - <<'PY'
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
SOURCE_DB = ROOT / "experience/organic-v0/corpus_sources_v0.jsonl"
MANIFEST = ROOT / "experience/organic-v0/corpus_manifest_v0.jsonl"
PATTERN_DB = ROOT / "experience/organic-v0/corpus_label_patterns_v0.jsonl"
VERIFY_JSON = ROOT / "run/artifacts/organic-v0/cycle12_corpus_verification.json"
SPLIT_POLICY_VERSION = "cycle12_split_v1_sha256_bucket_80_10_10"
FILTER_VERSION = "cycle12_label_filter_v1"

source_required = {
    "schema",
    "source_id",
    "source_type",
    "source_uri_or_path",
    "corpus_authority_url",
    "license_spdx_id",
    "license_note",
    "content_origin_year",
    "retrieval_timestamp_utc",
    "provenance_chain",
    "curation_note",
    "download_policy",
    "split_policy_version",
    "filter_version",
}

manifest_required = {
    "schema",
    "source_id",
    "shard_id",
    "local_path",
    "sha256",
    "canonicalization_hash",
    "dedup_hash",
    "encoding",
    "line_separator",
    "byte_count",
    "char_count",
    "line_count",
    "split",
    "split_bucket",
    "split_policy_version",
    "filter_status",
    "filter_reason",
    "filter_version",
    "retrieval_timestamp_utc",
    "license_spdx_id",
}

required_pattern_families = {
    "gutenberg_head_footer_sentinel",
    "metadata_prefix",
    "markdown_heading",
    "html_metadata_tag",
    "qa_marker",
    "byline",
}

checks = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "passed": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_text_from_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    if text.endswith("\n"):
        text = text[:-1]
    return re.sub(r"\s+", " ", text).strip()


def canonicalization_hash(text: str) -> str:
    return hashlib.sha256(("cycle12_canonical_v1\n" + text).encode("utf-8")).hexdigest()


def split_for_hash(ch: str) -> tuple[str, int]:
    bucket = int(ch[:8], 16) % 100
    if bucket < 80:
        return "train", bucket
    if bucket < 90:
        return "probe", bucket
    return "holdout", bucket


def compile_patterns(pattern_rows: list[dict]) -> dict[str, re.Pattern]:
    compiled = {}
    for row in pattern_rows:
        flags = re.IGNORECASE if "i" in row.get("flags", "") else 0
        compiled[row["pattern_id"]] = re.compile(row["regex"], flags)
    return compiled


sources = load_jsonl(SOURCE_DB)
patterns = load_jsonl(PATTERN_DB)
manifest = load_jsonl(MANIFEST)
compiled = compile_patterns(patterns)

check("exactly_one_source", len(sources) == 1, str(len(sources)))
source = sources[0]
check("source_schema", source.get("schema") == "project_x.corpus_source.v0", source.get("schema", ""))
check("source_required_fields", source_required.issubset(source), str(sorted(source_required - set(source))))
check("source_has_no_expected_split", "expected_split" not in source, "expected_split present")
check("source_public_or_cc0_license", source["license_spdx_id"] in {"CC0-1.0", "LicenseRef-PD-US"}, source["license_spdx_id"])
check("source_download_policy", source["download_policy"] in {"frozen_local", "download_if_missing", "never_refetch"}, source["download_policy"])
check("source_split_policy", source["split_policy_version"] == SPLIT_POLICY_VERSION, source["split_policy_version"])
check("source_filter_version", source["filter_version"] == FILTER_VERSION, source["filter_version"])
check("raw_cache_gitignored", subprocess.run(["git", "check-ignore", "-q", source["local_raw_path"]], cwd=ROOT).returncode == 0, source["local_raw_path"])
check("raw_source_sha", sha256_file(ROOT / source["local_raw_path"]) == source["expected_raw_sha256"], source["local_raw_path"])

families = {row.get("pattern_family") for row in patterns}
check("pattern_families_complete", required_pattern_families.issubset(families), str(sorted(required_pattern_families - families)))
for idx, row in enumerate(patterns, 1):
    check(f"pattern_{idx}_schema", row.get("schema") == "project_x.corpus_label_pattern.v0", row.get("schema", ""))
    check(f"pattern_{idx}_filter_version", row.get("filter_version") == FILTER_VERSION, row.get("filter_version", ""))
    check(f"pattern_{idx}_compiles", row["pattern_id"] in compiled, row["pattern_id"])

check("manifest_nonempty", bool(manifest), "empty manifest")
check("placeholder_removed", all(row.get("shard_id") != "bootstrap_placeholder_run_prepare_cycle12_corpus" for row in manifest), "placeholder row still present")

source_ids = {source["source_id"]}
reason_counts: Counter[str] = Counter()
candidate_bytes = 0
accepted_bytes = 0
accepted = 0
rejected = 0
duplicate_count = 0
accepted_train = 0
label_rejections = 0

for idx, row in enumerate(manifest, 1):
    prefix = f"manifest_row_{idx}_{row.get('shard_id', 'missing')}"
    check(prefix + "_required_fields", manifest_required.issubset(row), str(sorted(manifest_required - set(row))))
    check(prefix + "_schema", row["schema"] == "project_x.corpus_manifest.v0", row["schema"])
    check(prefix + "_source_known", row["source_id"] in source_ids, row["source_id"])
    check(prefix + "_split_policy", row["split_policy_version"] == SPLIT_POLICY_VERSION, row["split_policy_version"])
    check(prefix + "_filter_version", row["filter_version"] == FILTER_VERSION, row["filter_version"])
    check(prefix + "_filter_status", row["filter_status"] in {"accepted", "rejected"}, row["filter_status"])
    check(prefix + "_split", row["split"] in {"train", "probe", "holdout"}, row["split"])
    local_path = ROOT / row["local_path"]
    check(prefix + "_local_exists", local_path.is_file(), row["local_path"])
    check(prefix + "_local_gitignored", subprocess.run(["git", "check-ignore", "-q", row["local_path"]], cwd=ROOT).returncode == 0, row["local_path"])
    actual_sha = sha256_file(local_path)
    check(prefix + "_sha256", actual_sha == row["sha256"], actual_sha)
    text = canonical_text_from_file(local_path)
    ch = canonicalization_hash(text)
    check(prefix + "_canonicalization_hash", ch == row["canonicalization_hash"], ch)
    split, bucket = split_for_hash(ch)
    check(prefix + "_split_bucket", bucket == row["split_bucket"], str(bucket))
    check(prefix + "_deterministic_split", split == row["split"], f"{split} != {row['split']}")
    check(prefix + "_byte_count", local_path.stat().st_size == row["byte_count"], str(local_path.stat().st_size))
    check(prefix + "_char_count", len(text) == row["char_count"], str(len(text)))
    check(prefix + "_line_count", row["line_count"] == len(local_path.read_text(encoding="utf-8").splitlines()), str(row["line_count"]))
    candidate_bytes += row["byte_count"]
    matched_patterns = [pid for pid, pattern in compiled.items() if pattern.search(text)]
    if row["filter_status"] == "accepted":
        accepted += 1
        accepted_bytes += row["byte_count"]
        if row["split"] == "train":
            accepted_train += 1
        check(prefix + "_accepted_no_label_match", not matched_patterns, str(matched_patterns))
        check(prefix + "_accepted_filter_reason_empty", row["filter_reason"] == "", row["filter_reason"])
    else:
        rejected += 1
        reason_counts[row["filter_reason"]] += 1
        check(prefix + "_rejected_reason_present", bool(row["filter_reason"]), "")
        if row["filter_reason"].startswith("duplicate:"):
            duplicate_count += 1
        if row["filter_reason"].startswith("label_pattern:"):
            label_rejections += 1
            expected_id = row["filter_reason"].split(":", 1)[1]
            check(prefix + "_label_rejection_pattern_id_known", expected_id in compiled, expected_id)
            check(prefix + "_label_rejection_pattern_matches", expected_id in matched_patterns, str(matched_patterns))

candidate_count = len(manifest)
check("accepted_shards_present", accepted > 0, str(accepted))
check("accepted_train_shards_present", accepted_train > 0, str(accepted_train))
check("rejected_shards_present", rejected > 0, str(rejected))
check("label_rejections_present", label_rejections > 0, str(label_rejections))
check("candidate_count_consistent", candidate_count == accepted + rejected, f"{candidate_count} != {accepted}+{rejected}")
check("candidate_bytes_positive", candidate_bytes > 0, str(candidate_bytes))

result = {
    "schema": "project_x.cycle12_corpus_verification.v1",
    "source_db_path": str(SOURCE_DB.relative_to(ROOT)),
    "pattern_db_path": str(PATTERN_DB.relative_to(ROOT)),
    "manifest_path": str(MANIFEST.relative_to(ROOT)),
    "candidate_shards": candidate_count,
    "accepted_shards": accepted,
    "rejected_shards": rejected,
    "accepted_shards_over_candidate_shards_pct": round(100.0 * accepted / candidate_count, 6),
    "bytes_candidate": candidate_bytes,
    "bytes_accepted": accepted_bytes,
    "bytes_accepted_over_bytes_candidate_pct": round(100.0 * accepted_bytes / candidate_bytes, 6),
    "duplicate_count": duplicate_count,
    "duplicate_rate": round(duplicate_count / candidate_count, 6),
    "rejection_reason_counts": dict(sorted(reason_counts.items())),
    "split_policy_version": SPLIT_POLICY_VERSION,
    "filter_version": FILTER_VERSION,
    "checks": checks,
    "all_required_checks_passed": all(item["passed"] for item in checks),
    "negative_space": {
        "not_license_laundering": True,
        "not_curated_corpus_as_capability": True,
        "not_byte_count_as_progress": True,
        "not_dedup_as_understanding": True,
        "not_filter_as_quality_judgment": True,
        "not_source_diversity_as_competence": True,
        "not_internet_clean_data_claim": True,
    },
    "honest_interpretation": (
        "Corpus verifier proves only deterministic source-backed shard preparation, "
        "hashes, split buckets, and whole-shard label rejection. It does not prove language quality."
    ),
}
VERIFY_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"all_required_checks_passed": result["all_required_checks_passed"], "checks": len(checks)}, sort_keys=True))
PY

echo "wrote $VERIFY_JSON"
