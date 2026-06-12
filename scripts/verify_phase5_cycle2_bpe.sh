#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

python3 - <<'PY'
import hashlib
import json
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
VERIFY_PATH = ROOT / "run/artifacts/organic-v0/phase5_cycle2_bpe_verification.json"

FORBIDDEN_FIELDS = {
    "semantic_label",
    "semantic_labels",
    "expected_output",
    "expected_outputs",
    "subjective_score",
    "quality_score",
    "answer_template",
    "template",
}


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


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def train_bpe(train_payloads: list[bytes], max_vocab_size: int, min_pair_frequency: int, special_tokens: list[str]) -> list[dict]:
    sequences = [bytes_to_symbols(data) for data in train_payloads]
    max_merges = max_vocab_size - len(special_tokens) - 256
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
        if best_count < min_pair_frequency:
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


def without_key(obj: dict, key: str) -> dict:
    out = dict(obj)
    out.pop(key, None)
    return out


checks: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append({"name": name, "passed": bool(ok), "detail": detail})
    if not ok:
        raise AssertionError(f"{name}: {detail}")


def file_bytes_for_row(row: dict) -> bytes:
    path = ROOT / row["local_path"]
    check(f"shard_exists_{row['_manifest_alias']}_{row['_line_no']}", path.exists(), display_path(path))
    data = path.read_bytes()
    actual = sha256_bytes(data)
    check(
        f"shard_sha_{row['_manifest_alias']}_{row['_line_no']}",
        actual == row["sha256"],
        f"{display_path(path)} actual={actual} expected={row['sha256']}",
    )
    return data


def main() -> None:
    for path in [CONFIG_PATH, VOCAB_PATH, TOKEN_MANIFEST_PATH, PREPARE_PATH]:
        check(f"required_file_exists_{path.name}", path.exists(), display_path(path))

    config = read_json(CONFIG_PATH)
    vocab = read_json(VOCAB_PATH)
    prepare = read_json(PREPARE_PATH)
    token_rows = read_jsonl(TOKEN_MANIFEST_PATH)

    check("config_schema", config.get("schema") == "project_x.phase5_bpe_config.v0", config.get("schema", ""))
    check("vocab_schema", vocab.get("schema") == "project_x.phase5_bpe_vocab.v0", vocab.get("schema", ""))
    check("prepare_schema", prepare.get("schema") == "project_x.phase5_cycle2_bpe_prepare.v0", prepare.get("schema", ""))
    check("all_token_row_schema", all(r.get("schema") == "project_x.phase5_token_manifest_row.v0" for r in token_rows), str(len(token_rows)))

    config_hash = sha256_bytes(canonical_json(without_key(config, "config_hash")))
    vocab_hash = sha256_bytes(canonical_json(without_key(vocab, "vocab_hash")))
    check("config_hash_recomputes", config_hash == config.get("config_hash"), config_hash)
    check("vocab_hash_recomputes", vocab_hash == vocab.get("vocab_hash"), vocab_hash)
    check("vocab_config_hash_matches", vocab.get("config_hash") == config_hash, vocab.get("config_hash", ""))
    check("prepare_config_hash_matches", prepare.get("config_hash") == config_hash, prepare.get("config_hash", ""))
    check("prepare_vocab_hash_matches", prepare.get("vocab_hash") == vocab_hash, prepare.get("vocab_hash", ""))

    loaded: list[tuple[str, Path, str, list[dict]]] = []
    all_source_rows: list[dict] = []
    train_rows: list[dict] = []
    for alias, path in MANIFEST_SPECS:
        check(f"source_manifest_exists_{alias}", path.exists(), display_path(path))
        manifest_sha = sha256_file(path)
        rows = read_jsonl(path)
        loaded.append((alias, path, manifest_sha, rows))
        for row in rows:
            row["_manifest_alias"] = alias
            row["_manifest_path"] = display_path(path)
            row["_manifest_sha256"] = manifest_sha
            all_source_rows.append(row)
            if row.get("filter_status") == "accepted" and row.get("split") == "train":
                train_rows.append(row)

    check("token_manifest_row_count_matches_sources", len(token_rows) == len(all_source_rows), f"{len(token_rows)} vs {len(all_source_rows)}")
    check("accepted_train_rows_present", len(train_rows) > 0, str(len(train_rows)))

    source_hashes = {display_path(path): sha for _, path, sha, _ in loaded}
    check("config_source_manifest_hashes_match", {item["path"]: item["sha256"] for item in config["source_manifests"]} == source_hashes, "")
    check("vocab_source_manifest_hashes_match", vocab["source_manifest_hashes"] == source_hashes, "")

    params = config["parameters"]
    special_tokens = params["special_tokens"]
    train_payloads = [file_bytes_for_row(row) for row in train_rows]
    recomputed_merges = train_bpe(
        train_payloads,
        int(params["max_vocab_size"]),
        int(params["min_pair_frequency"]),
        list(special_tokens),
    )
    check("merge_table_recomputes", recomputed_merges == [{k: m[k] for k in ["rank", "left", "right", "token", "frequency"]} for m in vocab["merges"]], "")

    token_to_id: dict[str, int] = {}
    expected_tokens = []
    for token in special_tokens:
        token_to_id[token] = len(token_to_id)
        expected_tokens.append({"id": token_to_id[token], "token": token, "kind": "special"})
    for byte in range(256):
        token = f"hex:{byte:02x}"
        token_to_id[token] = len(token_to_id)
        expected_tokens.append({"id": token_to_id[token], "token": token, "kind": "byte"})
    expected_merges_with_ids = []
    for merge in recomputed_merges:
        item = dict(merge)
        token_to_id[item["token"]] = len(token_to_id)
        item["id"] = token_to_id[item["token"]]
        expected_merges_with_ids.append(item)
        expected_tokens.append({"id": item["id"], "token": item["token"], "kind": "merge"})

    check("vocab_tokens_recompute", vocab["tokens"] == expected_tokens, "")
    check("vocab_merges_with_ids_recompute", vocab["merges"] == expected_merges_with_ids, "")
    check("vocab_size_count", vocab["vocab_size"] == len(expected_tokens), str(vocab["vocab_size"]))
    check("merge_count_count", vocab["merge_count"] == len(expected_merges_with_ids), str(vocab["merge_count"]))

    source_by_row_id = {}
    for row in all_source_rows:
        source_by_row_id[f"{row['_manifest_alias']}:{row['_line_no']:06d}"] = row

    status_counts: Counter[str] = Counter()
    split_status_counts: Counter[tuple[str, str]] = Counter()
    forbidden_hits = []
    for token_row in token_rows:
        forbidden_hits.extend(sorted(FORBIDDEN_FIELDS & set(token_row)))
        source = source_by_row_id.get(token_row["row_id"])
        check(f"token_row_source_exists_{token_row['_line_no']}", source is not None, token_row["row_id"])
        assert source is not None
        accepted = source["filter_status"] == "accepted"
        expected_ids = encode_bytes(file_bytes_for_row(source), expected_merges_with_ids, token_to_id) if accepted else []
        check(f"token_row_source_manifest_sha_{token_row['_line_no']}", token_row["source_manifest_sha256"] == source["_manifest_sha256"], token_row["row_id"])
        check(f"token_row_shard_sha_{token_row['_line_no']}", token_row["shard_sha256"] == source["sha256"], token_row["row_id"])
        check(f"token_row_split_bucket_{token_row['_line_no']}", token_row["split_bucket"] == source["split_bucket"], token_row["row_id"])
        check(f"token_row_status_{token_row['_line_no']}", token_row["tokenization_status"] == ("accepted" if accepted else "rejected"), token_row["row_id"])
        check(f"token_row_ids_omitted_{token_row['_line_no']}", "token_ids" not in token_row, token_row["row_id"])
        check(f"token_row_count_{token_row['_line_no']}", token_row["token_count"] == len(expected_ids), token_row["row_id"])
        check(f"token_row_hash_{token_row['_line_no']}", token_row["token_sha256"] == sha256_bytes(canonical_json(expected_ids)), token_row["row_id"])
        check(f"token_row_config_hash_{token_row['_line_no']}", token_row["config_hash"] == config_hash, token_row["row_id"])
        check(f"token_row_vocab_hash_{token_row['_line_no']}", token_row["vocab_hash"] == vocab_hash, token_row["row_id"])
        status_counts[token_row["tokenization_status"]] += 1
        split_status_counts[(token_row["split"], token_row["tokenization_status"])] += 1

    check("no_forbidden_semantic_fields", not forbidden_hits, ",".join(sorted(set(forbidden_hits))))
    check("prepare_status_counts_match", prepare["token_manifest_status_counts"] == dict(sorted(status_counts.items())), "")
    check(
        "prepare_split_status_counts_match",
        prepare["token_manifest_split_status_counts"]
        == {f"{split}:{status}": count for (split, status), count in sorted(split_status_counts.items())},
        "",
    )
    check("artifact_config_sha_matches_file", prepare["artifact_sha256"]["config"] == sha256_file(CONFIG_PATH), "")
    check("artifact_vocab_sha_matches_file", prepare["artifact_sha256"]["vocab"] == sha256_file(VOCAB_PATH), "")
    check("artifact_token_manifest_sha_matches_file", prepare["artifact_sha256"]["token_manifest"] == sha256_file(TOKEN_MANIFEST_PATH), "")

    result = {
        "schema": "project_x.phase5_cycle2_bpe_verification.v0",
        "command": "bash scripts/verify_phase5_cycle2_bpe.sh",
        "config_path": display_path(CONFIG_PATH),
        "vocab_path": display_path(VOCAB_PATH),
        "token_manifest_path": display_path(TOKEN_MANIFEST_PATH),
        "prepare_artifact_path": display_path(PREPARE_PATH),
        "source_manifest_hashes": source_hashes,
        "vocab_size": vocab["vocab_size"],
        "merge_count": vocab["merge_count"],
        "token_manifest_row_count": len(token_rows),
        "token_manifest_status_counts": dict(sorted(status_counts.items())),
        "token_manifest_split_status_counts": {
            f"{split}:{status}": count
            for (split, status), count in sorted(split_status_counts.items())
        },
        "config_hash": config_hash,
        "vocab_hash": vocab_hash,
        "total_checks": len(checks),
        "checks_failed": [c for c in checks if not c["passed"]],
        "checks_sample_first_100": checks[:100],
        "all_required_checks_passed": all(item["passed"] for item in checks),
        "negative_space": {
            "not_pretrained": True,
            "not_rag": True,
            "not_language_capability_claim": True,
            "not_semantic_labeling": True,
            "not_expected_output_fixture": True,
            "not_subjective_quality_score": True,
        },
        "honest_interpretation": (
            "Verifier independently recomputed deterministic byte-level BPE "
            "merges, vocab IDs, token manifest hashes, source manifest hashes, "
            "and negative-space field absence. This validates tokenizer prep "
            "infrastructure only, not language quality or cognition."
        ),
    }
    VERIFY_PATH.parent.mkdir(parents=True, exist_ok=True)
    VERIFY_PATH.write_bytes(canonical_json(result))
    print(
        json.dumps(
            {
                "all_required_checks_passed": result["all_required_checks_passed"],
                "total_checks": result["total_checks"],
                "vocab_size": result["vocab_size"],
                "merge_count": result["merge_count"],
                "token_manifest_row_count": result["token_manifest_row_count"],
                "config_hash": result["config_hash"],
                "vocab_hash": result["vocab_hash"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
PY
