#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 - <<'PY'
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
MANIFEST_SPECS = [
    ("cycle12", ROOT / "experience/organic-v0/corpus_manifest_v0.jsonl"),
    ("cycle16", ROOT / "experience/organic-v0/cycle16_corpus_manifest.jsonl"),
]
CONFIG_PATH = ROOT / "experience/organic-v0/phase5_bpe_config_v0.json"
VOCAB_PATH = ROOT / "experience/organic-v0/phase5_bpe_vocab_v0.json"
TOKEN_MANIFEST_PATH = ROOT / "experience/organic-v0/phase5_token_manifest_v0.jsonl"
PREPARE_PATH = ROOT / "run/artifacts/organic-v0/phase5_cycle2_bpe_prepare.json"

CONFIG_SCHEMA = "project_x.phase5_bpe_config.v0"
VOCAB_SCHEMA = "project_x.phase5_bpe_vocab.v0"
TOKEN_ROW_SCHEMA = "project_x.phase5_token_manifest_row.v0"
PREPARE_SCHEMA = "project_x.phase5_cycle2_bpe_prepare.v0"

MAX_VOCAB_SIZE = 512
MIN_PAIR_FREQUENCY = 2
SPECIAL_TOKENS = ["<pad>", "<unk>"]


def canonical_json(obj: object) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_line_no"] = line_no
        rows.append(row)
    return rows


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def file_bytes_for_row(row: dict) -> bytes:
    path = ROOT / row["local_path"]
    if not path.exists():
        raise SystemExit(f"missing corpus shard: {display_path(path)}")
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != row["sha256"]:
        raise SystemExit(
            f"corpus shard sha mismatch: {display_path(path)} actual={actual} expected={row['sha256']}"
        )
    return data


def bytes_to_symbols(data: bytes) -> list[str]:
    return [f"hex:{byte:02x}" for byte in data]


def payload_hex(symbol: str) -> str:
    if not symbol.startswith("hex:"):
        raise ValueError(symbol)
    return symbol[4:]


def merge_symbol(left: str, right: str) -> str:
    return "hex:" + payload_hex(left) + payload_hex(right)


def count_pairs(sequences: list[list[str]]) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for seq in sequences:
        for i in range(len(seq) - 1):
            counts[(seq[i], seq[i + 1])] += 1
    return counts


def apply_merge(seq: list[str], pair: tuple[str, str], merged: str) -> list[str]:
    out = []
    i = 0
    while i < len(seq):
        if i + 1 < len(seq) and seq[i] == pair[0] and seq[i + 1] == pair[1]:
            out.append(merged)
            i += 2
        else:
            out.append(seq[i])
            i += 1
    return out


def train_bpe(train_payloads: list[bytes], max_vocab_size: int) -> list[dict]:
    sequences = [bytes_to_symbols(data) for data in train_payloads]
    max_merges = max_vocab_size - len(SPECIAL_TOKENS) - 256
    merges = []
    seen_tokens = {f"hex:{i:02x}" for i in range(256)}
    for rank in range(max_merges):
        pair_counts = count_pairs(sequences)
        if not pair_counts:
            break
        best_pair, best_count = min(
            pair_counts.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1]),
        )
        if best_count < MIN_PAIR_FREQUENCY:
            break
        merged = merge_symbol(best_pair[0], best_pair[1])
        if merged in seen_tokens:
            break
        seen_tokens.add(merged)
        merges.append(
            {
                "rank": rank,
                "left": best_pair[0],
                "right": best_pair[1],
                "token": merged,
                "frequency": best_count,
            }
        )
        sequences = [apply_merge(seq, best_pair, merged) for seq in sequences]
    return merges


def encode_bytes(data: bytes, merges: list[dict], token_to_id: dict[str, int]) -> list[int]:
    seq = bytes_to_symbols(data)
    for merge in merges:
        seq = apply_merge(seq, (merge["left"], merge["right"]), merge["token"])
    return [token_to_id[token] for token in seq]


def split_counts(rows: list[dict]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts[row["split"]] += 1
    return dict(sorted(counts.items()))


def main() -> None:
    loaded: list[tuple[str, Path, str, list[dict]]] = []
    missing_manifests = [display_path(path) for _, path in MANIFEST_SPECS if not path.exists()]
    if missing_manifests:
        raise SystemExit("missing source manifests: " + ", ".join(missing_manifests))

    for alias, path in MANIFEST_SPECS:
        rows = read_jsonl(path)
        loaded.append((alias, path, sha256_file(path), rows))

    all_rows: list[dict] = []
    train_rows: list[dict] = []
    for alias, manifest_path, manifest_sha, rows in loaded:
        for row in rows:
            row["_manifest_alias"] = alias
            row["_manifest_path"] = display_path(manifest_path)
            row["_manifest_sha256"] = manifest_sha
            all_rows.append(row)
            if row.get("filter_status") == "accepted" and row.get("split") == "train":
                train_rows.append(row)

    if not train_rows:
        raise SystemExit("no accepted train rows found in source manifests")

    for row in all_rows:
        file_bytes_for_row(row)

    train_payloads = [file_bytes_for_row(row) for row in train_rows]
    source_summaries = []
    for alias, path, manifest_sha, rows in loaded:
        accepted_rows = [r for r in rows if r.get("filter_status") == "accepted"]
        accepted_train = [
            r for r in rows if r.get("filter_status") == "accepted" and r.get("split") == "train"
        ]
        source_summaries.append(
            {
                "alias": alias,
                "path": display_path(path),
                "sha256": manifest_sha,
                "row_count": len(rows),
                "accepted_row_count": len(accepted_rows),
                "accepted_train_row_count": len(accepted_train),
                "accepted_split_counts": split_counts(accepted_rows),
            }
        )

    config = {
        "schema": CONFIG_SCHEMA,
        "algorithm": "deterministic_byte_bpe",
        "algorithm_version": "phase5_cycle2_byte_bpe_v0",
        "token_namespace": "utf8_byte_hex_sequence",
        "normalization": "none_raw_file_bytes",
        "source_manifests": source_summaries,
        "parameters": {
            "max_vocab_size": MAX_VOCAB_SIZE,
            "min_pair_frequency": MIN_PAIR_FREQUENCY,
            "special_tokens": SPECIAL_TOKENS,
            "base_alphabet": "all_256_byte_values",
            "pair_count_scope": "accepted_train_rows_from_cycle12_and_cycle16",
            "tie_break": "highest_frequency_then_left_token_then_right_token_lexicographic",
        },
        "hash_algorithm": "sha256_canonical_json_excluding_self_hash",
        "self_hash_excluded_fields": ["config_hash"],
        "negative_space": {
            "not_pretrained": True,
            "not_rag": True,
            "not_language_capability_claim": True,
            "not_semantic_labeling": True,
            "not_expected_output_fixture": True,
            "not_subjective_quality_score": True,
        },
    }
    config["config_hash"] = sha256_bytes(canonical_json(config))

    merges = train_bpe(train_payloads, MAX_VOCAB_SIZE)
    token_to_id: dict[str, int] = {}
    vocab_entries = []
    for token in SPECIAL_TOKENS:
        token_to_id[token] = len(token_to_id)
        vocab_entries.append({"id": token_to_id[token], "token": token, "kind": "special"})
    for byte in range(256):
        token = f"hex:{byte:02x}"
        token_to_id[token] = len(token_to_id)
        vocab_entries.append({"id": token_to_id[token], "token": token, "kind": "byte"})
    for merge in merges:
        token = merge["token"]
        token_to_id[token] = len(token_to_id)
        merge["id"] = token_to_id[token]
        vocab_entries.append({"id": token_to_id[token], "token": token, "kind": "merge"})

    vocab = {
        "schema": VOCAB_SCHEMA,
        "algorithm_version": config["algorithm_version"],
        "config_hash": config["config_hash"],
        "source_manifest_hashes": {
            item["path"]: item["sha256"] for item in source_summaries
        },
        "vocab_size": len(vocab_entries),
        "merge_count": len(merges),
        "special_token_count": len(SPECIAL_TOKENS),
        "byte_token_count": 256,
        "tokens": vocab_entries,
        "merges": merges,
        "hash_algorithm": "sha256_canonical_json_excluding_self_hash",
        "self_hash_excluded_fields": ["vocab_hash"],
    }
    vocab["vocab_hash"] = sha256_bytes(canonical_json(vocab))

    token_rows = []
    status_counts: Counter[str] = Counter()
    split_status_counts: Counter[tuple[str, str]] = Counter()
    for row in all_rows:
        accepted = row.get("filter_status") == "accepted"
        token_ids = encode_bytes(file_bytes_for_row(row), merges, token_to_id) if accepted else []
        token_hash = sha256_bytes(canonical_json(token_ids))
        out = {
            "schema": TOKEN_ROW_SCHEMA,
            "row_id": f"{row['_manifest_alias']}:{row['_line_no']:06d}",
            "source_manifest_sha256": row["_manifest_sha256"],
            "source_manifest_line": row["_line_no"],
            "source_id": row["source_id"],
            "shard_id": row["shard_id"],
            "shard_sha256": row["sha256"],
            "split": row["split"],
            "split_bucket": row["split_bucket"],
            "tokenization_status": "accepted" if accepted else "rejected",
            "token_reject_reason": "" if accepted else row["filter_reason"],
            "token_count": len(token_ids),
            "token_sha256": token_hash,
            "config_hash": config["config_hash"],
            "vocab_hash": vocab["vocab_hash"],
        }
        token_rows.append(out)
        status_counts[out["tokenization_status"]] += 1
        split_status_counts[(out["split"], out["tokenization_status"])] += 1

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    VOCAB_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREPARE_PATH.parent.mkdir(parents=True, exist_ok=True)

    CONFIG_PATH.write_bytes(canonical_json(config))
    VOCAB_PATH.write_bytes(canonical_json(vocab))
    TOKEN_MANIFEST_PATH.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in token_rows),
        encoding="utf-8",
    )

    prepare = {
        "schema": PREPARE_SCHEMA,
        "command": "bash scripts/prepare_phase5_cycle2_bpe.sh",
        "config_path": display_path(CONFIG_PATH),
        "vocab_path": display_path(VOCAB_PATH),
        "token_manifest_path": display_path(TOKEN_MANIFEST_PATH),
        "source_manifests": source_summaries,
        "training_row_count": len(train_rows),
        "training_byte_count": sum(len(data) for data in train_payloads),
        "token_manifest_row_count": len(token_rows),
        "token_manifest_status_counts": dict(sorted(status_counts.items())),
        "token_manifest_split_status_counts": {
            f"{split}:{status}": count
            for (split, status), count in sorted(split_status_counts.items())
        },
        "vocab_size": vocab["vocab_size"],
        "merge_count": vocab["merge_count"],
        "config_hash": config["config_hash"],
        "vocab_hash": vocab["vocab_hash"],
        "artifact_sha256": {
            "config": sha256_file(CONFIG_PATH),
            "vocab": sha256_file(VOCAB_PATH),
            "token_manifest": sha256_file(TOKEN_MANIFEST_PATH),
        },
        "negative_space": config["negative_space"],
        "honest_interpretation": (
            "Cycle 2 prepares deterministic byte-level BPE vocabulary and token "
            "manifest infrastructure only. It makes no claim about language "
            "quality, cognition, semantic understanding, or recurrent model progress."
        ),
    }
    PREPARE_PATH.write_bytes(canonical_json(prepare))
    print(
        json.dumps(
            {
                "schema": PREPARE_SCHEMA,
                "vocab_size": vocab["vocab_size"],
                "merge_count": vocab["merge_count"],
                "token_manifest_row_count": len(token_rows),
                "config_hash": config["config_hash"],
                "vocab_hash": vocab["vocab_hash"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(1)
PY
