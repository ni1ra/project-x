#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# Cycle 16 multi-source corpus rail verifier (scaffold).
#
# Mirrors scripts/verify_cycle12_corpus.sh structure, but adapted for the
# Cycle 16 multi-source rail:
#   - reads experience/organic-v0/cycle16_corpus_sources.jsonl (>= 1 source)
#   - reads experience/organic-v0/cycle16_corpus_manifest.jsonl
#   - reuses experience/organic-v0/corpus_label_patterns_v0.jsonl (same
#     filter_version as Cycle 12B; Cycle 16 deliberately does NOT bump
#     filter_version so identical canonical text lands in the same split
#     bucket across cycles)
#   - validates per-row schema, source-id membership, deterministic split
#     bucket from canonicalization hash, sha256 + canonicalization +
#     dedup hashes recompute correctly, accepted/rejected accounting
#     consistent, label-rejection pattern IDs are known.
#   - ALSO validates the cycle 16 carry-forward isolation: corpus_sources_v0,
#     corpus_manifest_v0, corpus_label_patterns_v0 bytewise unchanged from
#     their Cycle 12B baseline state (so verify_cycle12_corpus.sh stays
#     green).
#
# Writes run/artifacts/organic-v0/cycle16_text_scaling_verification.json
# under schema project_x.cycle16_text_scaling_verification.v1.
#
# This is a SCAFFOLD verifier (godify-cycle 2 of Cycle 16). Future cycles
# (3-5) will extend it with neural-train-result checks, generation-batch
# checks, source-overlap audits, and reproducibility audits — adding rows
# to the same artifact under additional check categories.

timeout 180s scripts/prepare_cycle16_corpus.sh > /tmp/cycle16-prepare.out

python3 - <<'PY'
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
SOURCE_DB = ROOT / "experience/organic-v0/cycle16_corpus_sources.jsonl"
MANIFEST = ROOT / "experience/organic-v0/cycle16_corpus_manifest.jsonl"
PATTERN_DB = ROOT / "experience/organic-v0/corpus_label_patterns_v0.jsonl"
VERIFY_JSON = ROOT / "run/artifacts/organic-v0/cycle16_text_scaling_verification.json"
SPLIT_POLICY_VERSION = "cycle12_split_v1_sha256_bucket_80_10_10"
FILTER_VERSION = "cycle12_label_filter_v1"

# Cycle 12B carry-forward isolation baseline — the v0 files MUST be
# bytewise unchanged after Cycle 16 work. These are the sha256 values
# captured at HEAD bc2adba (cycle 11 close), before Cycle 16 cycle 1.
# If any of these change, verify_cycle12_corpus.sh would be put at risk
# and Cycle 12B's 28,536-check rail would silently regress.
CYCLE12_V0_BASELINE_SHAS = {
    "experience/organic-v0/corpus_sources_v0.jsonl":
        "85a20542e6d0aa9fe5aee67ab19b1671a9bd53646e4e780f6a426483c6c95362",
    "experience/organic-v0/corpus_manifest_v0.jsonl":
        "3f6ba71383834905f87c2e9ee97d2841053197eff73c41ab1691561a462c0f74",
    "experience/organic-v0/corpus_label_patterns_v0.jsonl":
        "788cf8ff89b94f6637513f159e8c623ceb7c892a51f7aca4bc7aa78209dd5384",
}

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
    "expected_raw_sha256",
    "local_raw_path",
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

checks: list[dict] = []


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
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("﻿", "")
    if text.endswith("\n"):
        text = text[:-1]
    return re.sub(r"\s+", " ", text).strip()


def canonicalization_hash(text: str) -> str:
    return hashlib.sha256(
        ("cycle12_canonical_v1\n" + text).encode("utf-8")
    ).hexdigest()


def dedup_hash(text: str) -> str:
    return hashlib.sha256(
        ("cycle12_dedup_v1\n" + text.lower()).encode("utf-8")
    ).hexdigest()


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


# Carry-forward isolation: the Cycle 12B v0 files must NOT have been
# mutated by any Cycle 16 work. This check runs FIRST because if it
# fails, the rest of the verification is moot — the rail is broken.
for rel_path, baseline_sha in CYCLE12_V0_BASELINE_SHAS.items():
    actual_sha = sha256_file(ROOT / rel_path)
    check(
        f"cycle12_baseline_unchanged_{Path(rel_path).name}",
        actual_sha == baseline_sha,
        f"{rel_path}: actual={actual_sha} baseline={baseline_sha}",
    )

sources = load_jsonl(SOURCE_DB)
patterns = load_jsonl(PATTERN_DB)
manifest = load_jsonl(MANIFEST)
compiled = compile_patterns(patterns)

check("at_least_one_cycle16_source", len(sources) >= 1, str(len(sources)))

seen_source_ids: set[str] = set()
for idx, source in enumerate(sources, 1):
    check(
        f"source_{idx}_schema",
        source.get("schema") == "project_x.corpus_source.v0",
        source.get("schema", ""),
    )
    check(
        f"source_{idx}_required_fields",
        source_required.issubset(source),
        str(sorted(source_required - set(source))),
    )
    check(
        f"source_{idx}_no_expected_split",
        "expected_split" not in source,
        "expected_split present",
    )
    check(
        f"source_{idx}_public_or_cc0_license",
        source["license_spdx_id"] in {"CC0-1.0", "LicenseRef-PD-US"},
        source["license_spdx_id"],
    )
    check(
        f"source_{idx}_download_policy",
        source["download_policy"]
        in {"frozen_local", "download_if_missing", "never_refetch"},
        source["download_policy"],
    )
    check(
        f"source_{idx}_split_policy",
        source["split_policy_version"] == SPLIT_POLICY_VERSION,
        source["split_policy_version"],
    )
    check(
        f"source_{idx}_filter_version",
        source["filter_version"] == FILTER_VERSION,
        source["filter_version"],
    )
    check(
        f"source_{idx}_unique_source_id",
        source["source_id"] not in seen_source_ids,
        source["source_id"],
    )
    seen_source_ids.add(source["source_id"])
    raw_path = ROOT / source["local_raw_path"]
    check(
        f"source_{idx}_raw_gitignored",
        subprocess.run(
            ["git", "check-ignore", "-q", source["local_raw_path"]], cwd=ROOT
        ).returncode == 0,
        source["local_raw_path"],
    )
    check(
        f"source_{idx}_raw_sha",
        sha256_file(raw_path) == source["expected_raw_sha256"],
        source["local_raw_path"],
    )

families = {row.get("pattern_family") for row in patterns}
check(
    "pattern_families_complete",
    required_pattern_families.issubset(families),
    str(sorted(required_pattern_families - families)),
)
for idx, row in enumerate(patterns, 1):
    check(
        f"pattern_{idx}_schema",
        row.get("schema") == "project_x.corpus_label_pattern.v0",
        row.get("schema", ""),
    )
    check(
        f"pattern_{idx}_filter_version",
        row.get("filter_version") == FILTER_VERSION,
        row.get("filter_version", ""),
    )
    check(
        f"pattern_{idx}_compiles",
        row["pattern_id"] in compiled,
        row["pattern_id"],
    )

check("manifest_nonempty", bool(manifest), "empty manifest")

reason_counts: Counter[str] = Counter()
per_source_counts: dict[str, dict] = {sid: {"accepted": 0, "rejected": 0, "candidate": 0, "bytes_candidate": 0, "bytes_accepted": 0} for sid in seen_source_ids}
candidate_bytes = 0
accepted_bytes = 0
accepted = 0
rejected = 0
duplicate_count = 0
accepted_train = 0
label_rejections = 0
accepted_dedup_hashes: set[str] = set()

for idx, row in enumerate(manifest, 1):
    prefix = f"manifest_row_{idx}_{row.get('shard_id', 'missing')}"
    check(
        prefix + "_required_fields",
        manifest_required.issubset(row),
        str(sorted(manifest_required - set(row))),
    )
    check(
        prefix + "_schema",
        row["schema"] == "project_x.corpus_manifest.v0",
        row["schema"],
    )
    check(
        prefix + "_source_known",
        row["source_id"] in seen_source_ids,
        row["source_id"],
    )
    check(
        prefix + "_split_policy",
        row["split_policy_version"] == SPLIT_POLICY_VERSION,
        row["split_policy_version"],
    )
    check(
        prefix + "_filter_version",
        row["filter_version"] == FILTER_VERSION,
        row["filter_version"],
    )
    check(
        prefix + "_filter_status",
        row["filter_status"] in {"accepted", "rejected"},
        row["filter_status"],
    )
    check(prefix + "_split", row["split"] in {"train", "probe", "holdout"}, row["split"])
    local_path = ROOT / row["local_path"]
    check(prefix + "_local_exists", local_path.is_file(), row["local_path"])
    check(
        prefix + "_local_gitignored",
        subprocess.run(
            ["git", "check-ignore", "-q", row["local_path"]], cwd=ROOT
        ).returncode == 0,
        row["local_path"],
    )
    actual_sha = sha256_file(local_path)
    check(prefix + "_sha256", actual_sha == row["sha256"], actual_sha)
    text = canonical_text_from_file(local_path)
    ch = canonicalization_hash(text)
    check(
        prefix + "_canonicalization_hash",
        ch == row["canonicalization_hash"],
        ch,
    )
    dh = dedup_hash(text)
    check(prefix + "_dedup_hash", dh == row["dedup_hash"], dh)
    split, bucket = split_for_hash(ch)
    check(prefix + "_split_bucket", bucket == row["split_bucket"], str(bucket))
    check(
        prefix + "_deterministic_split",
        split == row["split"],
        f"{split} != {row['split']}",
    )
    check(
        prefix + "_byte_count",
        local_path.stat().st_size == row["byte_count"],
        str(local_path.stat().st_size),
    )
    check(prefix + "_char_count", len(text) == row["char_count"], str(len(text)))
    candidate_bytes += row["byte_count"]
    per_source_counts[row["source_id"]]["candidate"] += 1
    per_source_counts[row["source_id"]]["bytes_candidate"] += row["byte_count"]
    matched_patterns = [
        pid for pid, pattern in compiled.items() if pattern.search(text)
    ]
    if row["filter_status"] == "accepted":
        accepted += 1
        accepted_bytes += row["byte_count"]
        per_source_counts[row["source_id"]]["accepted"] += 1
        per_source_counts[row["source_id"]]["bytes_accepted"] += row["byte_count"]
        if row["split"] == "train":
            accepted_train += 1
        check(
            prefix + "_accepted_no_label_match",
            not matched_patterns,
            str(matched_patterns),
        )
        check(
            prefix + "_accepted_filter_reason_empty",
            row["filter_reason"] == "",
            row["filter_reason"],
        )
        check(
            prefix + "_accepted_dedup_unique",
            dh not in accepted_dedup_hashes,
            dh,
        )
        accepted_dedup_hashes.add(dh)
    else:
        rejected += 1
        per_source_counts[row["source_id"]]["rejected"] += 1
        reason_counts[row["filter_reason"]] += 1
        check(
            prefix + "_rejected_reason_present",
            bool(row["filter_reason"]),
            "",
        )
        if row["filter_reason"].startswith("duplicate:"):
            duplicate_count += 1
        if row["filter_reason"].startswith("label_pattern:"):
            label_rejections += 1
            expected_id = row["filter_reason"].split(":", 1)[1]
            check(
                prefix + "_label_rejection_pattern_id_known",
                expected_id in compiled,
                expected_id,
            )
            check(
                prefix + "_label_rejection_pattern_matches",
                expected_id in matched_patterns,
                str(matched_patterns),
            )

candidate_count = len(manifest)
check("accepted_shards_present", accepted > 0, str(accepted))
check("accepted_train_shards_present", accepted_train > 0, str(accepted_train))
check("rejected_shards_present", rejected > 0, str(rejected))
check("label_rejections_present", label_rejections > 0, str(label_rejections))
check(
    "candidate_count_consistent",
    candidate_count == accepted + rejected,
    f"{candidate_count} != {accepted}+{rejected}",
)
check("candidate_bytes_positive", candidate_bytes > 0, str(candidate_bytes))
check(
    "accepted_dedup_hashes_unique_across_sources",
    len(accepted_dedup_hashes) == accepted,
    f"{len(accepted_dedup_hashes)} accepted_dedup unique vs {accepted} accepted",
)

result = {
    "schema": "project_x.cycle16_text_scaling_verification.v1",
    "source_db_path": str(SOURCE_DB.relative_to(ROOT)),
    "pattern_db_path": str(PATTERN_DB.relative_to(ROOT)),
    "manifest_path": str(MANIFEST.relative_to(ROOT)),
    "source_count": len(sources),
    "source_ids": sorted(seen_source_ids),
    "per_source_counts": per_source_counts,
    "candidate_shards": candidate_count,
    "accepted_shards": accepted,
    "rejected_shards": rejected,
    "accepted_shards_over_candidate_shards_pct": round(
        100.0 * accepted / candidate_count, 6
    ),
    "bytes_candidate": candidate_bytes,
    "bytes_accepted": accepted_bytes,
    "bytes_accepted_over_bytes_candidate_pct": round(
        100.0 * accepted_bytes / candidate_bytes, 6
    ),
    "duplicate_count": duplicate_count,
    "duplicate_rate": round(duplicate_count / candidate_count, 6),
    "rejection_reason_counts": dict(sorted(reason_counts.items())),
    "split_policy_version": SPLIT_POLICY_VERSION,
    "filter_version": FILTER_VERSION,
    "cycle12_baseline_isolation": {
        "baseline_shas": CYCLE12_V0_BASELINE_SHAS,
        "all_baselines_unchanged": all(
            sha256_file(ROOT / rel_path) == sha
            for rel_path, sha in CYCLE12_V0_BASELINE_SHAS.items()
        ),
    },
    "total_checks": len(checks),
    "checks_failed": [c for c in checks if not c["passed"]],
    "checks_sample_first_100": checks[:100],
    "all_required_checks_passed": all(item["passed"] for item in checks),
    "negative_space": {
        "not_license_laundering": True,
        "not_curated_corpus_as_capability": True,
        "not_byte_count_as_progress": True,
        "not_filter_as_quality_judgment": True,
        "not_source_diversity_as_competence": True,
        "not_internet_clean_data_claim": True,
        "not_neural_training_validation": True,
        "not_language_quality_validation": True,
    },
    "honest_interpretation": (
        "Cycle 16 text-scaling verifier proves only deterministic "
        "multi-source shard preparation, hashes, split buckets, whole-shard "
        "label rejection, cross-source dedup integrity, and Cycle 12B "
        "baseline isolation. It does not prove language quality, "
        "generalization, or training utility. Neural-train-result checks, "
        "generation-batch audits, source-overlap audits, and reproducibility "
        "audits land in cycle-3 through cycle-5 extensions of this scaffold."
    ),
}
VERIFY_JSON.parent.mkdir(parents=True, exist_ok=True)
VERIFY_JSON.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "all_required_checks_passed": result["all_required_checks_passed"],
            "checks": len(checks),
            "source_count": len(sources),
            "accepted_shards": accepted,
            "cycle12_baseline_unchanged": result["cycle12_baseline_isolation"][
                "all_baselines_unchanged"
            ],
        },
        sort_keys=True,
    )
)
PY

echo ""
echo "wrote run/artifacts/organic-v0/cycle16_text_scaling_verification.json"
