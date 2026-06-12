#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 - <<'PY'
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
SOURCE_DB = ROOT / "experience/organic-v0/corpus_sources_v0.jsonl"
PATTERN_DB = ROOT / "experience/organic-v0/corpus_label_patterns_v0.jsonl"
MANIFEST = Path(os.environ.get(
    "CYCLE13_TEST_MANIFEST_PATH",
    str(ROOT / "experience/organic-v0/corpus_manifest_v0.jsonl"),
))
ARTIFACT = ROOT / "run/artifacts/organic-v0/cycle12_corpus_prepare.json"
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
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    return re.sub(r"\s+", " ", text).strip()


def canonicalization_hash(text: str) -> str:
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
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
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


def source_raw_path(source: dict) -> Path:
    return ROOT / source["local_raw_path"]


def fetch_source(source: dict) -> bytes:
    raw_path = source_raw_path(source)
    expected_sha = source.get("expected_raw_sha256")
    if raw_path.exists():
        data = raw_path.read_bytes()
    else:
        legacy = ROOT / "run/corpus/organic-v0/cycle12/pg932.txt"
        if legacy.exists() and (not expected_sha or sha256_bytes(legacy.read_bytes()) == expected_sha):
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(legacy, raw_path)
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
        raise SystemExit(f"raw source sha mismatch for {raw_path}: {actual_sha} != {expected_sha}")
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
    existing = {}
    for row in rows:
        if row.get("shard_id") == "bootstrap_placeholder_run_prepare_cycle12_corpus":
            continue
        existing[row_key(row)] = row
    return existing


def main() -> None:
    sources = load_jsonl(SOURCE_DB)
    if len(sources) != 1:
        raise SystemExit(f"Cycle 12B requires exactly one source row, found {len(sources)}")
    source = sources[0]
    if "expected_split" in source:
        raise SystemExit("source descriptor must not include expected_split")
    if source["split_policy_version"] != SPLIT_POLICY_VERSION:
        raise SystemExit("source split policy mismatch")
    if source["filter_version"] != FILTER_VERSION:
        raise SystemExit("source filter version mismatch")

    pattern_rows = load_jsonl(PATTERN_DB)
    patterns = compile_patterns(pattern_rows)
    raw_bytes = fetch_source(source)
    raw_text = raw_bytes.decode("utf-8-sig")

    shard_dir = ROOT / "run/corpus/organic-v0/cycle12" / source["source_id"] / "shards"
    shard_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    seen_dedup: dict[str, str] = {}
    reason_counts: Counter[str] = Counter()
    candidate_bytes = 0
    accepted_bytes = 0
    duplicate_count = 0

    for index, (_kind, text) in enumerate(candidate_texts(raw_text), 1):
        if not text:
            continue
        shard_id = f"{source['source_id']}_shard_{index:05d}"
        ch = canonicalization_hash(text)
        dh = dedup_hash(text)
        split, bucket = split_for_hash(ch)
        local_path = shard_dir / f"{shard_id}.txt"
        payload = (text + "\n").encode("utf-8")
        local_path.write_bytes(payload)
        file_sha = sha256_bytes(payload)
        candidate_bytes += len(payload)

        filter_status = "accepted"
        filter_reason = ""
        matched = first_label_match(text, patterns)
        if matched:
            filter_status = "rejected"
            filter_reason = f"label_pattern:{matched}"
        elif dh in seen_dedup:
            filter_status = "rejected"
            filter_reason = f"duplicate:{seen_dedup[dh]}"
            duplicate_count += 1
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
            accepted_bytes += len(payload)

        if filter_status == "rejected":
            reason_counts[filter_reason] += 1

        rows.append({
            "schema": "project_x.corpus_manifest.v0",
            "source_id": source["source_id"],
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

    accepted = [row for row in rows if row["filter_status"] == "accepted"]
    rejected = [row for row in rows if row["filter_status"] == "rejected"]
    train = [row for row in accepted if row["split"] == "train"]
    if not accepted:
        raise SystemExit("corpus preparation produced zero accepted shards")
    if not train:
        raise SystemExit("corpus preparation produced zero accepted train shards")
    if not rejected:
        raise SystemExit("corpus preparation produced zero rejected shards")

    existing = load_existing_manifest()
    allow_manifest_rewrite = os.environ.get("CYCLE12_ALLOW_MANIFEST_REWRITE") == "1"
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

    MANIFEST.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    candidate_count = len(rows)
    accepted_count = len(accepted)
    result = {
        "schema": "project_x.cycle12_corpus_prepare.v1",
        "source_id": source["source_id"],
        "source_db_path": str(SOURCE_DB.relative_to(ROOT)),
        "pattern_db_path": str(PATTERN_DB.relative_to(ROOT)),
        "manifest_path": display_path(MANIFEST),
        "raw_source_path": source["local_raw_path"],
        "raw_source_sha256": sha256_bytes(raw_bytes),
        "candidate_shards": candidate_count,
        "accepted_shards": accepted_count,
        "rejected_shards": len(rejected),
        "accepted_shards_over_candidate_shards_pct": round(100.0 * accepted_count / candidate_count, 6),
        "bytes_candidate": candidate_bytes,
        "bytes_accepted": accepted_bytes,
        "bytes_accepted_over_bytes_candidate_pct": round(100.0 * accepted_bytes / candidate_bytes, 6),
        "duplicate_count": duplicate_count,
        "duplicate_rate": round(duplicate_count / candidate_count, 6),
        "rejection_reason_counts": dict(sorted(reason_counts.items())),
        "split_policy_version": SPLIT_POLICY_VERSION,
        "filter_version": FILTER_VERSION,
        "negative_space": {
            "not_license_laundering": True,
            "not_curated_corpus_as_capability": True,
            "not_byte_count_as_progress": True,
            "not_filter_as_quality_judgment": True,
            "not_source_diversity_as_competence": True,
        },
        "honest_interpretation": (
            "Cycle 12 corpus preparation creates deterministic source-backed shards and "
            "whole-shard label rejections only. It does not claim language quality or capability."
        ),
    }
    ARTIFACT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "manifest": display_path(MANIFEST),
        "artifact": str(ARTIFACT.relative_to(ROOT)),
        "candidate_shards": candidate_count,
        "accepted_shards": accepted_count,
        "rejected_shards": len(rejected),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
PY
