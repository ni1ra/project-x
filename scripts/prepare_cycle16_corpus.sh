#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# Cycle 16 multi-source corpus preparation.
#
# Forked from scripts/prepare_cycle12_corpus.sh with one structural change:
# the source DB and manifest are SEPARATE files (cycle16_corpus_sources.jsonl
# + cycle16_corpus_manifest.jsonl) so the Cycle 12B carry-forward rail
# (verify_cycle12_corpus.sh, which hardcodes "exactly one source") stays green.
# All other discipline (deterministic shard SHA, canonicalization-hash split
# bucket, whole-shard rejection only, append-only manifest with no-rewrite
# rail, label-pattern filter reuse) is preserved bit-for-bit.

python3 - <<'PY'
import hashlib
import json
import os
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
SOURCE_DB = ROOT / "experience/organic-v0/cycle16_corpus_sources.jsonl"
PATTERN_DB = ROOT / "experience/organic-v0/corpus_label_patterns_v0.jsonl"
MANIFEST = Path(os.environ.get(
    "CYCLE16_TEST_MANIFEST_PATH",
    str(ROOT / "experience/organic-v0/cycle16_corpus_manifest.jsonl"),
))
ARTIFACT = ROOT / "run/artifacts/organic-v0/cycle16_corpus_prepare.json"
SHARD_ROOT = ROOT / "run/corpus/organic-v0/cycle16"

# Cycle 16 reuses Cycle 12B's split + filter discipline verbatim. The version
# strings are the protocol's contract: the canonicalization function, the
# hash buckets, the length thresholds, and the label patterns must all match
# Cycle 12B exactly. A protocol change requires a new filter_version and a
# fresh cycle, not a silent rewrite.
SPLIT_POLICY_VERSION = "cycle12_split_v1_sha256_bucket_80_10_10"
FILTER_VERSION = "cycle12_label_filter_v1"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonicalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("﻿", "")
    return re.sub(r"\s+", " ", text).strip()


def canonicalization_hash(text: str) -> str:
    # Cycle 16 deliberately reuses the Cycle 12 canonicalization prefix so the
    # split bucket assignment is identical for the same canonical text across
    # cycles. Same text -> same bucket -> same split, regardless of which
    # cycle's prep wrote the row. This is a feature: a sentence that lands in
    # 'probe' under Cycle 12 will not silently flip to 'train' under Cycle 16.
    return hashlib.sha256(("cycle12_canonical_v1\n" + text).encode("utf-8")).hexdigest()


def dedup_hash(text: str) -> str:
    return hashlib.sha256(("cycle12_dedup_v1\n" + text.lower()).encode("utf-8")).hexdigest()


def split_for_hash(ch: str) -> tuple[str, int]:
    bucket = int(ch[:8], 16) % 100
    if bucket < 80:
        split = "train"
    elif bucket < 90:
        split = "probe"
    else:
        split = "holdout"
    return split, bucket


def compile_patterns(rows: list[dict]) -> list[tuple[dict, re.Pattern]]:
    compiled = []
    for row in rows:
        flags = re.IGNORECASE if "i" in row.get("flags", "") else 0
        compiled.append((row, re.compile(row["regex"], flags)))
    return compiled


def sentence_candidates(block: str) -> list[str]:
    sentences = [m.group(0) for m in re.finditer(r"[^.!?]+[.!?]", block)]
    return [canonicalize(sentence) for sentence in sentences]


def candidate_texts(raw_text: str) -> list[tuple[str, str]]:
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("﻿", "")
    out: list[tuple[str, str]] = []
    for line in normalized.splitlines():
        item = canonicalize(line)
        if item:
            out.append(("line", item))
    for block in re.split(r"\n\s*\n+", normalized):
        item = canonicalize(block)
        if not item:
            continue
        out.append(("block", item))
        for sentence in sentence_candidates(block):
            if sentence:
                out.append(("sentence", sentence))
    return out


def first_label_match(text: str, patterns: list[tuple[dict, re.Pattern]]) -> str | None:
    for row, pattern in patterns:
        if pattern.search(text):
            return row["pattern_id"]
    return None


def fetch_source(source: dict) -> bytes:
    raw_path = ROOT / source["local_raw_path"]
    expected_sha = source.get("expected_raw_sha256")
    if raw_path.exists():
        data = raw_path.read_bytes()
    elif source["download_policy"] == "download_if_missing":
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(source["source_uri_or_path"], timeout=60) as response:
            data = response.read()
        raw_path.write_bytes(data)
    else:
        raise SystemExit(f"missing frozen source and policy forbids download: {raw_path}")
    actual_sha = sha256_bytes(data)
    if expected_sha and actual_sha != expected_sha:
        raise SystemExit(
            f"raw source sha mismatch for {raw_path}: actual={actual_sha} expected={expected_sha}"
        )
    return data


def row_key(row: dict) -> tuple[str, str]:
    return row["source_id"], row["shard_id"]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_existing_manifest() -> dict[tuple[str, str], dict]:
    if not MANIFEST.exists():
        return {}
    rows = load_jsonl(MANIFEST)
    return {row_key(row): row for row in rows}


def main() -> None:
    sources = load_jsonl(SOURCE_DB)
    if not sources:
        raise SystemExit(f"{SOURCE_DB} contains zero sources; Cycle 16 requires at least one")
    seen_source_ids: set[str] = set()
    for src in sources:
        if "expected_split" in src:
            raise SystemExit(
                f"source descriptor {src.get('source_id')} must not include expected_split"
            )
        if src["split_policy_version"] != SPLIT_POLICY_VERSION:
            raise SystemExit(
                f"source {src['source_id']} split_policy_version != {SPLIT_POLICY_VERSION}"
            )
        if src["filter_version"] != FILTER_VERSION:
            raise SystemExit(
                f"source {src['source_id']} filter_version != {FILTER_VERSION}"
            )
        if src["source_id"] in seen_source_ids:
            raise SystemExit(f"duplicate source_id {src['source_id']}")
        seen_source_ids.add(src["source_id"])

    pattern_rows = load_jsonl(PATTERN_DB)
    patterns = compile_patterns(pattern_rows)

    # Dedup spans ALL sources in this run: a sentence shared between two
    # sources is rejected as a duplicate against whichever source emitted it
    # first (iteration order). This is the diagnostic we want — the corpus
    # cannot inflate accepted-shard count by re-counting boilerplate that
    # appears in two Gutenberg books.
    seen_dedup: dict[str, str] = {}
    rows: list[dict] = []
    per_source_stats: list[dict] = []

    for source in sources:
        source_id = source["source_id"]
        shard_dir = SHARD_ROOT / source_id / "shards"
        shard_dir.mkdir(parents=True, exist_ok=True)
        raw_bytes = fetch_source(source)
        raw_text = raw_bytes.decode("utf-8-sig")

        candidate_count_source = 0
        candidate_bytes_source = 0
        accepted_count_source = 0
        accepted_bytes_source = 0
        rejected_count_source = 0
        duplicate_count_source = 0
        reason_counts_source: Counter[str] = Counter()

        for index, (_kind, text) in enumerate(candidate_texts(raw_text), 1):
            if not text:
                continue
            shard_id = f"{source_id}_shard_{index:05d}"
            ch = canonicalization_hash(text)
            dh = dedup_hash(text)
            split, bucket = split_for_hash(ch)
            local_path = shard_dir / f"{shard_id}.txt"
            payload = (text + "\n").encode("utf-8")
            local_path.write_bytes(payload)
            file_sha = sha256_bytes(payload)
            candidate_count_source += 1
            candidate_bytes_source += len(payload)

            filter_status = "accepted"
            filter_reason = ""
            matched = first_label_match(text, patterns)
            if matched:
                filter_status = "rejected"
                filter_reason = f"label_pattern:{matched}"
            elif dh in seen_dedup:
                filter_status = "rejected"
                filter_reason = f"duplicate:{seen_dedup[dh]}"
                duplicate_count_source += 1
            elif len(text) < 40:
                filter_status = "rejected"
                filter_reason = "length_policy:min_40"
            elif len(text) > 320:
                filter_status = "rejected"
                filter_reason = "length_policy:max_320"
            elif any(ord(ch_) > 126 for ch_ in text):
                filter_status = "rejected"
                filter_reason = "delimiter_policy:non_ascii"
            elif "|" in text or "," in text or "\n" in text or "\r" in text:
                filter_status = "rejected"
                filter_reason = "delimiter_policy:pxstate_observation_delimiter"
            else:
                seen_dedup[dh] = shard_id
                accepted_count_source += 1
                accepted_bytes_source += len(payload)

            if filter_status == "rejected":
                reason_counts_source[filter_reason] += 1
                rejected_count_source += 1

            rows.append({
                "schema": "project_x.corpus_manifest.v0",
                "source_id": source_id,
                "shard_id": shard_id,
                "local_path": str(local_path.relative_to(ROOT)),
                "sha256": file_sha,
                "canonicalization_hash": ch,
                "dedup_hash": dh,
                "encoding": "utf-8",
                "line_separator": "LF",
                "byte_count": len(payload),
                "char_count": len(text),
                "line_count": 1,
                "split": split,
                "split_bucket": bucket,
                "split_policy_version": SPLIT_POLICY_VERSION,
                "filter_status": filter_status,
                "filter_reason": filter_reason,
                "filter_version": FILTER_VERSION,
                "retrieval_timestamp_utc": source["retrieval_timestamp_utc"],
                "license_spdx_id": source["license_spdx_id"],
            })

        per_source_stats.append({
            "source_id": source_id,
            "candidate_shards": candidate_count_source,
            "accepted_shards": accepted_count_source,
            "rejected_shards": rejected_count_source,
            "duplicate_count": duplicate_count_source,
            "bytes_candidate": candidate_bytes_source,
            "bytes_accepted": accepted_bytes_source,
            "rejection_reason_counts": dict(sorted(reason_counts_source.items())),
            "raw_source_sha256": sha256_bytes(raw_bytes),
            "raw_source_byte_count": len(raw_bytes),
            "local_raw_path": source["local_raw_path"],
        })

    accepted = [row for row in rows if row["filter_status"] == "accepted"]
    rejected = [row for row in rows if row["filter_status"] == "rejected"]
    train = [row for row in accepted if row["split"] == "train"]
    if not accepted:
        raise SystemExit("cycle 16 corpus preparation produced zero accepted shards")
    if not train:
        raise SystemExit("cycle 16 corpus preparation produced zero accepted train shards")
    if not rejected:
        # Rejected shards prove the filter is doing work. Zero rejections would
        # mean the patterns aren't matching anything, which is the strongest
        # smell that something silently changed in the rail.
        raise SystemExit("cycle 16 corpus preparation produced zero rejected shards")

    existing = load_existing_manifest()
    allow_manifest_rewrite = os.environ.get("CYCLE16_ALLOW_MANIFEST_REWRITE") == "1"
    generated = {row_key(row): row for row in rows}
    for key, old in existing.items():
        new = generated.get(key)
        if new is None and not allow_manifest_rewrite:
            raise SystemExit(f"manifest row would be silently removed: {key}")
        if new is not None and old != new and not allow_manifest_rewrite:
            raise SystemExit(
                "manifest row would be silently mutated: "
                f"{key}; create a new shard row/source id for new bytes"
            )

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    candidate_count = len(rows)
    accepted_count = len(accepted)
    aggregate_reason_counts: Counter[str] = Counter()
    candidate_bytes = 0
    accepted_bytes = 0
    duplicate_count = 0
    for stats in per_source_stats:
        candidate_bytes += stats["bytes_candidate"]
        accepted_bytes += stats["bytes_accepted"]
        duplicate_count += stats["duplicate_count"]
        for reason, count in stats["rejection_reason_counts"].items():
            aggregate_reason_counts[reason] += count

    result = {
        "schema": "project_x.cycle16_corpus_prepare.v1",
        "source_db_path": str(SOURCE_DB.relative_to(ROOT)),
        "pattern_db_path": str(PATTERN_DB.relative_to(ROOT)),
        "manifest_path": display_path(MANIFEST),
        "source_count": len(sources),
        "source_ids": [src["source_id"] for src in sources],
        "per_source_stats": per_source_stats,
        "candidate_shards": candidate_count,
        "accepted_shards": accepted_count,
        "rejected_shards": len(rejected),
        "accepted_shards_over_candidate_shards_pct": round(
            100.0 * accepted_count / candidate_count, 6
        ),
        "bytes_candidate": candidate_bytes,
        "bytes_accepted": accepted_bytes,
        "bytes_accepted_over_bytes_candidate_pct": round(
            100.0 * accepted_bytes / candidate_bytes, 6
        ),
        "duplicate_count": duplicate_count,
        "duplicate_rate": round(duplicate_count / candidate_count, 6),
        "rejection_reason_counts": dict(sorted(aggregate_reason_counts.items())),
        "split_policy_version": SPLIT_POLICY_VERSION,
        "filter_version": FILTER_VERSION,
        "carry_forward_isolation_note": (
            "Cycle 16 writes a SEPARATE sources file (cycle16_corpus_sources.jsonl) "
            "and SEPARATE manifest (cycle16_corpus_manifest.jsonl) so the Cycle 12B "
            "verifier rail (verify_cycle12_corpus.sh, hardcoded single-source check) "
            "stays green. corpus_sources_v0.jsonl and corpus_manifest_v0.jsonl are "
            "unchanged by this script."
        ),
        "negative_space": {
            "not_license_laundering": True,
            "not_curated_corpus_as_capability": True,
            "not_byte_count_as_progress": True,
            "not_filter_as_quality_judgment": True,
            "not_source_diversity_as_competence": True,
            "not_cross_source_dedup_as_understanding": True,
        },
        "honest_interpretation": (
            "Cycle 16 corpus preparation produces deterministic source-backed "
            "shards across multiple sources under the reused Cycle 12 filter and "
            "split policy. It does not claim language quality, semantic coverage, "
            "or generalization capability."
        ),
    }
    ARTIFACT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "manifest": display_path(MANIFEST),
        "artifact": str(ARTIFACT.relative_to(ROOT)),
        "source_count": len(sources),
        "candidate_shards": candidate_count,
        "accepted_shards": accepted_count,
        "rejected_shards": len(rejected),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
PY
