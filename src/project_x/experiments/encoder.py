"""
encoder.py — Phase 9 Layer 2. Organic encoders for text → bipolar HDC.

NO pretrained transformer models. NO BGE, NO MiniLM, NO sentence-transformers,
NO llama.cpp, NO Qwen, NO Mistral. Per lain 2026-05-09 17:53 CEST:
  *"organic and real from the core and the beginning. No borrowing other LLM
   models, remember, we are moving past the transformer."*

Three organic encoder families staged across cycles:

  Cycle 2 (this file): CharNgramHashEncoder — deterministic, no learning.
                       Character n-grams → hash bucket → multi-hot → random
                       Gaussian projection → sign → bipolar HDC vector.
                       FLOOR baseline.

  Cycle 3 (next):      HebbianCooccurrenceEncoder — words as random HDC atoms;
                       sentence-co-occurrence Hebbian superposition; trained
                       atoms encode semantic relatedness via their cosines;
                       sentence = bound superposition of trained word atoms.

  Phase 10+:           SNN spike-train extension to hdc_snn_bridge.lif_encode
                       (drive char/byte-level inputs into the LIF bank).

Anti-spec: an encoder violates Project X's thesis if it routes through any
pretrained transformer. The interface (`OrganicEncoder`) is the gate; new
implementations must satisfy it without importing torch.hub/transformers/etc.

Author: Raphael (post-persona-shift, 2026-05-09)
Phase: 9 — semantic_hdc_memory_agent (organic-encoder edition, lain override 17:53)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np


# =============================================================================
# Protocol — the gate
# =============================================================================


class OrganicEncoder(Protocol):
    """Protocol for from-scratch text encoders. No pretrained models allowed.

    Implementers must encode text into bipolar HDC vectors WITHOUT routing
    through any pretrained transformer derivative. Determinism per seed is
    expected so result JSONs are reproducible.
    """

    D: int  # output bipolar HDC dimension

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return shape (n, D), dtype int8, values in {-1, +1}."""
        ...

    def name(self) -> str:
        """Short identifier for result JSONs."""
        ...


# =============================================================================
# Helpers
# =============================================================================


def _char_ngrams(text: str, n: int) -> list[str]:
    """Lowercase + space-padded char n-grams; padding marks word boundaries."""
    s = " " + text.lower() + " "
    if len(s) < n:
        return [s]
    return [s[i : i + n] for i in range(len(s) - n + 1)]


def _stable_hash(token: str) -> int:
    """Stable cross-process hash. Python's built-in hash() is randomized per session."""
    return int.from_bytes(
        hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big"
    )


def cosine_bipolar(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine for bipolar vectors. |a| = |b| = sqrt(D), so cos = (a·b) / D."""
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} vs {b.shape}")
    return float(np.sum(a.astype(np.int32) * b.astype(np.int32))) / float(a.shape[0])


def cosine_matrix_bipolar(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """(n_a, D) · (n_b, D)^T → (n_a, n_b) cosine matrix in [-1, +1]."""
    return (A.astype(np.int32) @ B.astype(np.int32).T) / float(A.shape[1])


# =============================================================================
# CharNgramHashEncoder — Cycle 2 floor
# =============================================================================


@dataclass
class CharNgramHashEncoder:
    """Deterministic char-n-gram → hash → multi-hot → random projection → sign.

    No learning. Captures lexical/morphological overlap (shared substrings),
    not deep semantics — by design. This is the FLOOR baseline that cycle 3's
    Hebbian encoder must beat to claim "learned semantics."

    Math:
      ngrams = char_ngrams(text, n)         # length grows ~ |text|
      feat   = sum_g onehot(hash(g) % F)    # (F,) multi-hot, L2-normalized
      proj   = feat @ G                     # G ~ N(0, 1/sqrt(F)), shape (F, D)
      vec    = sign(proj)                   # bipolar (D,)
    """

    D: int = 10000
    feature_dim: int = 4096
    n: int = 3
    seed: int = 1337
    _proj: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        rng = np.random.default_rng(self.seed)
        self._proj = (
            rng.standard_normal((self.feature_dim, self.D)).astype(np.float32)
            / np.sqrt(self.feature_dim)
        )

    def name(self) -> str:
        return (
            f"char_ngram_hash_n{self.n}_F{self.feature_dim}_D{self.D}_seed{self.seed}"
        )

    def _multihot(self, text: str) -> np.ndarray:
        ngrams = _char_ngrams(text, self.n)
        if not ngrams:
            return np.zeros(self.feature_dim, dtype=np.float32)
        feat = np.zeros(self.feature_dim, dtype=np.float32)
        for g in ngrams:
            idx = _stable_hash(g) % self.feature_dim
            feat[idx] += 1.0
        norm = float(np.linalg.norm(feat))
        if norm > 0:
            feat /= norm
        return feat

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.D), dtype=np.int8)
        feats = np.stack([self._multihot(t) for t in texts])  # (n, F)
        proj = feats @ self._proj  # (n, D)
        # sign(0) → +1 by convention to keep bipolar invariant
        bipolar = np.where(proj == 0, 1, np.sign(proj)).astype(np.int8)
        return bipolar


# =============================================================================
# Smoke benchmark — encode dataset, run paraphrase retrieval, write result.json
# =============================================================================


def run_smoke(
    dataset_dir: Path,
    out_dir: Path,
    D: int,
    feature_dim: int,
    n: int,
    seed: int,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    with (dataset_dir / "conversation.jsonl").open() as f:
        turns = [json.loads(line) for line in f]
    with (dataset_dir / "queries.jsonl").open() as f:
        queries = [json.loads(line) for line in f]

    encoder = CharNgramHashEncoder(D=D, feature_dim=feature_dim, n=n, seed=seed)
    turn_texts = [t["text"] for t in turns]
    query_texts = [q["text"] for q in queries]

    t0 = time.time()
    turn_vecs = encoder.encode(turn_texts)
    query_vecs = encoder.encode(query_texts)
    encode_wall = time.time() - t0

    t1 = time.time()
    cos_mat = cosine_matrix_bipolar(query_vecs, turn_vecs)  # (n_q, n_t)
    retrieval_wall = time.time() - t1

    # Per-query top-1 retrieval
    top1_bucket: dict[str, dict] = {}
    samples = []
    absent_top1_cosines: list[float] = []
    expected_top1_cosines: list[float] = []  # for queries with expected ids — proxy for "signal strength"

    for qi, q in enumerate(queries):
        qtype = q["type"]
        sims = cos_mat[qi]
        top1_idx = int(np.argmax(sims))
        top1_cos = float(sims[top1_idx])
        expected_ids = q["expected_turn_ids"]

        bucket = top1_bucket.setdefault(
            qtype, {"correct": 0, "total": 0, "n_with_expected": 0}
        )
        bucket["total"] += 1

        if expected_ids:
            bucket["n_with_expected"] += 1
            if top1_idx in expected_ids:
                bucket["correct"] += 1
            # Cosine of the actually-correct turn (expected_ids[0]) — signal proxy.
            expected_top1_cosines.append(float(sims[expected_ids[0]]))
        else:
            absent_top1_cosines.append(top1_cos)

        if qi < 12:
            is_correct = (top1_idx in expected_ids) if expected_ids else None
            samples.append(
                {
                    "query_id": q["query_id"],
                    "type": qtype,
                    "text": q["text"],
                    "expected_turn_ids": expected_ids,
                    "top1_turn_id": top1_idx,
                    "top1_cosine": round(top1_cos, 4),
                    "correct": is_correct,
                }
            )

    accuracy_by_type: dict[str, float | None] = {}
    for qtype, bucket in top1_bucket.items():
        if bucket["n_with_expected"] > 0:
            accuracy_by_type[qtype] = round(
                bucket["correct"] / bucket["n_with_expected"], 4
            )
        else:
            accuracy_by_type[qtype] = None

    # Pairwise cosine distribution on a turn-vector sample (orthogonality check)
    sample_size = min(500, len(turn_vecs))
    sample_idx = np.random.default_rng(1337).choice(
        len(turn_vecs), size=sample_size, replace=False
    )
    sample_vecs = turn_vecs[sample_idx]
    sample_cos = cosine_matrix_bipolar(sample_vecs, sample_vecs)
    iu = np.triu_indices(sample_size, k=1)
    off_diag = sample_cos[iu]

    result = {
        "run_id": f"phase9_encoder_cngram_seed{seed}",
        "config": {
            "encoder": encoder.name(),
            "D": D,
            "feature_dim": feature_dim,
            "n_gram_size": n,
            "seed": seed,
            "n_turns": len(turns),
            "n_queries": len(queries),
            "dataset": str(dataset_dir),
        },
        "metrics": {
            "encode_wall_seconds": round(encode_wall, 4),
            "retrieval_wall_seconds": round(retrieval_wall, 4),
            "top1_accuracy_by_type": accuracy_by_type,
            "pairwise_cosine_off_diagonal": {
                "n_pairs": int(len(off_diag)),
                "mean": round(float(np.mean(off_diag)), 6),
                "std": round(float(np.std(off_diag)), 6),
                "min": round(float(np.min(off_diag)), 6),
                "max": round(float(np.max(off_diag)), 6),
                "p25": round(float(np.percentile(off_diag, 25)), 6),
                "p50": round(float(np.percentile(off_diag, 50)), 6),
                "p75": round(float(np.percentile(off_diag, 75)), 6),
            },
            "expected_turn_cosine": (
                {
                    "n": len(expected_top1_cosines),
                    "mean": round(float(np.mean(expected_top1_cosines)), 4),
                    "std": round(float(np.std(expected_top1_cosines)), 4),
                }
                if expected_top1_cosines
                else None
            ),
            "absent_top1_cosine": (
                {
                    "n": len(absent_top1_cosines),
                    "mean": round(float(np.mean(absent_top1_cosines)), 4),
                    "std": round(float(np.std(absent_top1_cosines)), 4),
                }
                if absent_top1_cosines
                else None
            ),
        },
        "samples": samples,
        "notes": [
            "FLOOR baseline. Captures lexical/morphological overlap, NOT deep semantics.",
            "Cycle 3 HebbianCooccurrenceEncoder must beat top1_accuracy_by_type[semantic_paraphrase].",
            "Pairwise cosine off-diagonal mean ≈ 0 confirms HDC orthogonality property.",
            "expected_turn_cosine vs absent_top1_cosine gap ≈ signal-vs-noise margin for retrieval threshold calibration.",
        ],
    }

    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=str, default="gpt-codex/runs/phase9_dataset_full"
    )
    parser.add_argument("--D", type=int, default=10000)
    parser.add_argument("--feature-dim", type=int, default=4096)
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument(
        "--out", type=str, default="gpt-codex/runs/phase9_encoder_cngram"
    )
    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    out_dir = Path(args.out)
    print(
        f"encoder smoke  D={args.D}  feature_dim={args.feature_dim}  n={args.n}  seed={args.seed}"
    )
    result = run_smoke(dataset_dir, out_dir, args.D, args.feature_dim, args.n, args.seed)
    acc = result["metrics"]["top1_accuracy_by_type"]
    pc = result["metrics"]["pairwise_cosine_off_diagonal"]
    print(f"  encoder: {result['config']['encoder']}")
    print(f"  encode_wall = {result['metrics']['encode_wall_seconds']}s")
    print(f"  retrieval_wall = {result['metrics']['retrieval_wall_seconds']}s")
    print(f"  top-1 accuracy by type: {acc}")
    print(
        f"  pairwise cosine off-diagonal: mean={pc['mean']:+.4f} std={pc['std']:.4f}  "
        f"(target |mean|<0.05 for orthogonality)"
    )
    if result["metrics"].get("expected_turn_cosine") and result["metrics"].get(
        "absent_top1_cosine"
    ):
        ec = result["metrics"]["expected_turn_cosine"]
        ac = result["metrics"]["absent_top1_cosine"]
        gap = ec["mean"] - ac["mean"]
        print(
            f"  signal-vs-noise: expected_turn_cos {ec['mean']:.4f} vs absent_top1_cos {ac['mean']:.4f}  "
            f"(gap = {gap:+.4f})"
        )
    print(f"  wrote {out_dir / 'result.json'}")


if __name__ == "__main__":
    main()
