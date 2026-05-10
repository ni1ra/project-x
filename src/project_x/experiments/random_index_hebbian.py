"""
random_index_hebbian.py — Phase 9 Layer 2 semantic encoder.

Implements the Shrine Council winner (415/420): Sahlgren's Random Indexing
+ sliding-window Hebbian co-occurrence + Mikolov subsampling. Designed to
beat the CharNgramHashEncoder floor (38.3% paraphrase top-1, -0.047 signal
gap) AND flip the signal-vs-noise gap positive by exploiting unseen-word
orthogonality.

Algorithm (per council spec, see docs/artifacts/PHASE_9_SHRINE_COUNCIL_HEBBIAN.md):

  Init:
    For each word w in observed vocab:
      index_vec[w] = sparse-ternary (D-dim, n_active positions ±1, rest 0,
                     seeded by stable hash of w → deterministic across runs)
      context_vec[w] = int32 zero accumulator (D-dim)

  Fit (one pass, Hebbian co-occurrence):
    For each turn:
      tokens = tokenize(turn) filtered by Mikolov subsample probability
               P_drop(w) = 1 - sqrt(threshold / freq(w))   (clamped)
      For each i in range(len(tokens)):
        For j in range(max(0, i-window), min(len(tokens), i+window+1)):
          if i == j: continue
          context_vec[tokens[i]] += index_vec[tokens[j]]

    After pass:
      trained_vec[w] = sign(context_vec[w])   # bipolar int8

  Encode (text → bipolar HDC):
    tokens = tokenize(text)   # NOT subsampled at query time
    vecs = []
    for w in tokens:
      if w in trained_vec:
        vecs.append(trained_vec[w])
      else:
        vecs.append(sign(index_vec[w] or fresh hash-seeded sparse-ternary))
    sentence_vec = sign(sum(vecs))

The unseen-word fallback is the load-bearing trick: at query time, words that
never appeared in conversation training (Ghost1234, phantom-system-NNNN) get a
sparse-ternary signed vector that is near-orthogonal to ALL trained vectors →
their contribution drives the sentence cosine toward 0 → absent_answer queries
score LOW → the floor's NEGATIVE signal-vs-noise gap flips POSITIVE.

NO pretrained transformers. NO neural network training. Pure linear algebra +
co-occurrence statistics + biologically-inspired Hebbian update.

Author: Raphael (post-persona-shift, 2026-05-09)
Phase: 9 — semantic_hdc_memory_agent (council winner, lain organic-encoder constraint)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from project_x.experiments.encoder import (
    CharNgramHashEncoder,
    cosine_bipolar,
    cosine_matrix_bipolar,
)


# =============================================================================
# Tokenization — whitespace + lowercase + strip punctuation. NO BPE.
# =============================================================================

_WORD_RE = re.compile(r"[a-z0-9_]+(?:[./\-][a-z0-9_]+)*")


def tokenize(text: str) -> list[str]:
    """Lowercase, then extract word-like tokens. Keeps file paths intact
    (e.g. `src/project_x/foo.py`) and hyphenated identifiers, but does NOT
    consume leading or trailing punctuation. NO BPE, NO subword tokenizer."""
    return _WORD_RE.findall(text.lower())


# =============================================================================
# Sparse-ternary index vector — deterministic per word via stable hash
# =============================================================================


def _word_hash_seed(word: str, seed_offset: int) -> int:
    """Stable cross-process per-word seed (Python hash() is randomized)."""
    h = hashlib.blake2b(word.encode("utf-8"), digest_size=8).digest()
    return (int.from_bytes(h, "big") ^ seed_offset) & 0x7FFFFFFF


def make_index_vector(word: str, D: int, n_active: int, seed_offset: int) -> np.ndarray:
    """Sparse-ternary D-dim vector: n_active positions filled, half +1 / half -1.

    Deterministic given (word, D, n_active, seed_offset) — same word always maps
    to same index vector across sessions. Rest are 0 (sparse). Returns int8.
    Used during TRAINING as the per-word context-update signal.
    """
    rng = np.random.default_rng(_word_hash_seed(word, seed_offset))
    positions = rng.choice(D, size=n_active, replace=False)
    half = n_active // 2
    values = np.array([1] * half + [-1] * (n_active - half), dtype=np.int8)
    rng.shuffle(values)
    vec = np.zeros(D, dtype=np.int8)
    vec[positions] = values
    return vec


def make_random_bipolar(word: str, D: int, seed_offset: int) -> np.ndarray:
    """Full random bipolar D-dim vector for a word — every position ±1.

    Deterministic per (word, seed_offset). Used as the QUERY-TIME encoding
    fallback for unseen words. Two unseen words have near-zero cosine by HDC
    orthogonality (mean ≈ 0 with std ≈ 1/sqrt(D)). This is what flips the
    signal-vs-noise gap positive — sparse-ternary index vectors couldn't
    because sign(0)→+1 conventions floods them with +1 bits.
    """
    rng = np.random.default_rng(_word_hash_seed(word, seed_offset) ^ 0xDEADBEEF)
    return rng.choice(np.array([-1, 1], dtype=np.int8), size=D)


def _bipolarize_rank(v: np.ndarray) -> np.ndarray:
    """Rank-based median split: top D/2 elements → +1, bottom D/2 → -1.

    Guarantees EXACTLY 50% +1 / 50% -1 by construction. Two unrelated
    accumulator vectors (e.g., post-Hebbian context vectors of unrelated words)
    will have cross-cosine ≈ 0 because the median split is per-vector
    deterministic. Replaces naive `sign(v)` which collapses to +1-dominated
    when v has many zeros.
    """
    d = v.shape[0]
    # Stable double-argsort gives per-element rank in [0, d).
    ranks = np.argsort(np.argsort(v, kind="stable"), kind="stable")
    return np.where(ranks >= d // 2, 1, -1).astype(np.int8)


# =============================================================================
# RandomIndexHebbianEncoder — the council winner
# =============================================================================


@dataclass
class RandomIndexHebbianEncoder:
    """Sahlgren's RI + sliding-window Hebbian + Mikolov subsampling (per council).

    Optional Mikolov negative sampling (council #3, 400/420): for each positive
    co-occurrence pair within window, sample `negative_samples` random
    non-co-occurring vocab words and SUBTRACT half-weighted index vectors.
    Pushes unrelated words apart in HDC space → tighter signal-vs-noise gap,
    intended to flip Cycle 3's still-negative gap (-0.039) to clearly positive.
    """

    D: int = 10000
    n_active: int = 10                 # 5 +1 / 5 -1 / rest 0
    window: int = 3                    # half-width — pairs (i, j) with |i-j| <= window
    subsample_threshold: float = 1e-3  # Mikolov 2013 default
    negative_samples: int = 0          # >0 enables Mikolov contrastive subtraction
    seed: int = 1337

    # Internal state populated by .fit():
    _vocab: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _freq: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _total_tokens: int = field(default=0, init=False, repr=False)
    _drop_prob: dict[str, float] = field(default_factory=dict, init=False, repr=False)
    _index_vecs: dict[str, np.ndarray] = field(default_factory=dict, init=False, repr=False)
    _trained_vecs: dict[str, np.ndarray] = field(default_factory=dict, init=False, repr=False)
    _is_fit: bool = field(default=False, init=False, repr=False)

    def name(self) -> str:
        ns = f"_neg{self.negative_samples}" if self.negative_samples > 0 else ""
        return (
            f"random_index_hebbian_D{self.D}_act{self.n_active}_w{self.window}"
            f"_sub{self.subsample_threshold:.0e}{ns}_seed{self.seed}"
        )

    # --- Internal helpers -------------------------------------------------

    def _get_index_vec(self, word: str) -> np.ndarray:
        if word not in self._index_vecs:
            self._index_vecs[word] = make_index_vector(
                word, self.D, self.n_active, self.seed
            )
        return self._index_vecs[word]

    def _compute_drop_probs(self) -> None:
        """Per Mikolov 2013: P_drop(w) = 1 - sqrt(t / f(w)) where f is the
        word's relative frequency in the corpus. Words with f < t never drop."""
        if self._total_tokens == 0:
            return
        for w, c in self._freq.items():
            f = c / self._total_tokens
            if f <= self.subsample_threshold:
                self._drop_prob[w] = 0.0
            else:
                p = 1.0 - math.sqrt(self.subsample_threshold / f)
                self._drop_prob[w] = max(0.0, min(1.0, p))

    # --- Public API ------------------------------------------------------

    def fit(self, conversation_texts: list[str], reset: bool = False) -> None:
        """Build vocab + index vectors + Hebbian-trained context vectors.

        Args:
            conversation_texts: corpus to fit on.
            reset: if True, drop accumulated stats from any prior fit() call
                (audit-A2 — without this, two fit() calls produce a `_freq` and
                `_total_tokens` that reflect BOTH corpora, plus stale entries
                in `_vocab` / `_drop_prob` / `_trained_vecs` for words that
                only appeared in the older corpus). Default False preserves
                Phase 9 single-fit semantics. `_index_vecs` is NOT cleared on
                reset because index vectors are deterministic per word — the
                cache is correct regardless of corpus.
        """
        if reset:
            self._vocab.clear()
            self._freq.clear()
            self._total_tokens = 0
            self._drop_prob.clear()
            self._trained_vecs.clear()

        rng = np.random.default_rng(self.seed)

        all_tokens: list[list[str]] = []
        for text in conversation_texts:
            toks = tokenize(text)
            all_tokens.append(toks)
            for t in toks:
                self._freq[t] = self._freq.get(t, 0) + 1
                self._total_tokens += 1
        self._vocab = {w: i for i, w in enumerate(self._freq.keys())}

        self._compute_drop_probs()

        # Pre-materialize all index vectors. Deterministic per (word, D, n_active,
        # seed_offset) via blake2b hash → cross-process / cross-session stable;
        # `reset=True` callers can rebuild vocab without re-randomizing assignments.
        for w in self._vocab:
            self._get_index_vec(w)

        # 4. Initialize int32 context accumulators with deterministic random
        # bipolar noise per word. Zero-init was a bug: sparse Hebbian updates
        # only touch ~n_active positions per event, leaving most of the
        # accumulator at exactly 0. Two words then bipolarize to nearly the
        # same vector because their "zero" positions tie under any rule.
        # Random-bipolar init means unrelated words stay orthogonal even when
        # only a few Hebbian events fire; words with MANY events drift toward
        # their neighbors' indices and overwhelm the init noise.
        ctx: dict[str, np.ndarray] = {
            w: make_random_bipolar(w, self.D, self.seed).astype(np.int32)
            for w in self._vocab
        }

        vocab_keys = list(self._vocab.keys())
        n_vocab = len(vocab_keys)
        for toks in all_tokens:
            kept = [t for t in toks if rng.random() >= self._drop_prob.get(t, 0.0)]
            kept_set = set(kept)
            n = len(kept)
            for i in range(n):
                w_i = kept[i]
                lo = max(0, i - self.window)
                hi = min(n, i + self.window + 1)
                for j in range(lo, hi):
                    if i == j:
                        continue
                    w_j = kept[j]
                    ctx[w_i] += self._index_vecs[w_j]
                # Mikolov negative sampling: subtract index vectors of K random
                # non-co-occurring vocab words. Push w_i away from words it
                # never appears with → tightens signal-vs-noise gap. Each
                # subtraction has the same magnitude as one positive co-occ
                # update (no fractional weighting — int8 vectors don't divide).
                if self.negative_samples > 0 and n_vocab > 0:
                    for _ in range(self.negative_samples):
                        for _try in range(8):
                            w_neg = vocab_keys[int(rng.integers(0, n_vocab))]
                            if w_neg not in kept_set:
                                break
                        else:
                            continue
                        ctx[w_i] -= self._index_vecs[w_neg].astype(np.int32)

        # 6. Bipolarize. With random-bipolar init (step 4), naive sign() works
        # cleanly because nearly no positions are at exactly 0. Rank-bipolarize
        # would also work but adds cost without benefit when init has full
        # population.
        for w, v in ctx.items():
            self._trained_vecs[w] = np.where(v == 0, 1, np.sign(v)).astype(np.int8)

        self._is_fit = True

    def encode(self, texts: list[str]) -> np.ndarray:
        """Sentence vec = rank-bipolarize(sum of word vecs).

        Trained words → use their Hebbian-trained rank-bipolar vec.
        Unseen words → use `make_random_bipolar(word)` — a FULL bipolar D-dim
                       vector deterministic per word. Two unseen words have
                       cross-cosine ≈ 0 by HDC orthogonality. Combined with
                       trained vecs in a sentence sum, an unseen-heavy
                       sentence's encoding moves toward random-bipolar noise →
                       low cosine with all stored turn vecs → flips the
                       signal-vs-noise gap positive.
        Empty token list → neutral random-bipolar (deterministic on empty).
        """
        if not texts:
            return np.zeros((0, self.D), dtype=np.int8)
        if not self._is_fit:
            raise RuntimeError("call .fit(conversation_texts) before .encode(...)")
        out = np.zeros((len(texts), self.D), dtype=np.int8)
        for ti, text in enumerate(texts):
            toks = tokenize(text)
            if not toks:
                out[ti] = make_random_bipolar("__empty__", self.D, self.seed)
                continue
            acc = np.zeros(self.D, dtype=np.int32)
            for w in toks:
                if w in self._trained_vecs:
                    acc += self._trained_vecs[w].astype(np.int32)
                else:
                    # Full bipolar fallback — equal magnitude with trained vecs,
                    # near-orthogonal to all trained vecs by random construction.
                    acc += make_random_bipolar(w, self.D, self.seed).astype(np.int32)
            out[ti] = _bipolarize_rank(acc)
        return out


# =============================================================================
# Smoke benchmark — same protocol as encoder.py for direct comparison
# =============================================================================


def run_smoke(
    dataset_dir: Path,
    out_dir: Path,
    D: int,
    n_active: int,
    window: int,
    subsample_threshold: float,
    seed: int,
    floor_result_path: Path | None = None,
    negative_samples: int = 0,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)

    with (dataset_dir / "conversation.jsonl").open() as f:
        turns = [json.loads(line) for line in f]
    with (dataset_dir / "queries.jsonl").open() as f:
        queries = [json.loads(line) for line in f]

    encoder = RandomIndexHebbianEncoder(
        D=D, n_active=n_active, window=window,
        subsample_threshold=subsample_threshold,
        negative_samples=negative_samples, seed=seed,
    )

    turn_texts = [t["text"] for t in turns]
    query_texts = [q["text"] for q in queries]

    t0 = time.time()
    encoder.fit(turn_texts)
    fit_wall = time.time() - t0

    t1 = time.time()
    turn_vecs = encoder.encode(turn_texts)
    query_vecs = encoder.encode(query_texts)
    encode_wall = time.time() - t1

    t2 = time.time()
    cos_mat = cosine_matrix_bipolar(query_vecs, turn_vecs)
    retrieval_wall = time.time() - t2

    # Per-query top-1 retrieval (same protocol as floor)
    top1_bucket: dict[str, dict] = {}
    samples = []
    absent_top1_cosines: list[float] = []
    expected_top1_cosines: list[float] = []

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
            expected_top1_cosines.append(float(sims[expected_ids[0]]))
        else:
            absent_top1_cosines.append(top1_cos)

        if qi < 12:
            is_correct = (top1_idx in expected_ids) if expected_ids else None
            samples.append({
                "query_id": q["query_id"],
                "type": qtype,
                "text": q["text"],
                "expected_turn_ids": expected_ids,
                "top1_turn_id": top1_idx,
                "top1_cosine": round(top1_cos, 4),
                "correct": is_correct,
            })

    accuracy_by_type: dict[str, float | None] = {}
    for qtype, bucket in top1_bucket.items():
        if bucket["n_with_expected"] > 0:
            accuracy_by_type[qtype] = round(
                bucket["correct"] / bucket["n_with_expected"], 4
            )
        else:
            accuracy_by_type[qtype] = None

    # Pairwise cosine off-diagonal sample
    sample_size = min(500, len(turn_vecs))
    sample_idx = np.random.default_rng(1337).choice(
        len(turn_vecs), size=sample_size, replace=False
    )
    sample_vecs = turn_vecs[sample_idx]
    sample_cos = cosine_matrix_bipolar(sample_vecs, sample_vecs)
    iu = np.triu_indices(sample_size, k=1)
    off_diag = sample_cos[iu]

    # Vocab + drop-prob distribution stats
    drop_probs = sorted(encoder._drop_prob.items(), key=lambda kv: -kv[1])
    top_dropped = [(w, round(p, 3)) for w, p in drop_probs[:8]]

    result = {
        "run_id": f"phase9_encoder_riwh_seed{seed}",
        "config": {
            "encoder": encoder.name(),
            "D": D,
            "n_active": n_active,
            "window": window,
            "subsample_threshold": subsample_threshold,
            "seed": seed,
            "n_turns": len(turns),
            "n_queries": len(queries),
            "vocab_size": len(encoder._vocab),
            "total_tokens_seen": encoder._total_tokens,
            "dataset": str(dataset_dir),
        },
        "metrics": {
            "fit_wall_seconds": round(fit_wall, 4),
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
            "top_dropped_words": top_dropped,
        },
        "samples": samples,
    }

    # Side-by-side vs floor
    if floor_result_path and floor_result_path.exists():
        floor = json.loads(floor_result_path.read_text())
        floor_acc = floor["metrics"]["top1_accuracy_by_type"]
        floor_exp = floor["metrics"].get("expected_turn_cosine") or {}
        floor_abs = floor["metrics"].get("absent_top1_cosine") or {}
        floor_pc = floor["metrics"]["pairwise_cosine_off_diagonal"]
        riwh_exp = result["metrics"].get("expected_turn_cosine") or {}
        riwh_abs = result["metrics"].get("absent_top1_cosine") or {}
        result["comparison_vs_floor"] = {
            "floor_run_id": floor.get("run_id"),
            "delta_top1_accuracy_by_type": {
                k: round(
                    (accuracy_by_type.get(k) or 0) - (floor_acc.get(k) or 0), 4
                )
                for k in accuracy_by_type
            },
            "floor_signal_gap": round(
                (floor_exp.get("mean") or 0) - (floor_abs.get("mean") or 0), 4
            ),
            "riwh_signal_gap": round(
                (riwh_exp.get("mean") or 0) - (riwh_abs.get("mean") or 0), 4
            ),
            "signal_gap_flipped_positive": (
                (riwh_exp.get("mean") or 0) - (riwh_abs.get("mean") or 0)
            ) > 0,
            "delta_pairwise_cos_mean": round(
                result["metrics"]["pairwise_cosine_off_diagonal"]["mean"]
                - floor_pc["mean"], 4
            ),
        }

    result["notes"] = [
        "Council winner: Sahlgren's Random Indexing + sliding-window Hebbian + Mikolov subsampling.",
        "Unseen-word fallback: sparse-ternary index vector (n_active nonzero bits, rest 0) — near-orthogonal to all trained vecs by construction.",
        "If signal_gap_flipped_positive == False, the unseen-word orthogonality mechanism failed → debug index vector sparsity & encoding fallback.",
        "If paraphrase top-1 < floor (38.3%), the Hebbian co-occurrence captured the wrong correlations → check vocab size, subsample threshold, window size.",
    ]

    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=str, default="gpt-codex/runs/phase9_dataset_full"
    )
    parser.add_argument("--D", type=int, default=10000)
    parser.add_argument("--n-active", type=int, default=10)
    parser.add_argument("--window", type=int, default=3)
    parser.add_argument("--subsample", type=float, default=1e-3)
    parser.add_argument("--negative-samples", type=int, default=0)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument(
        "--out", type=str, default="gpt-codex/runs/phase9_encoder_riwh"
    )
    parser.add_argument(
        "--floor", type=str,
        default="gpt-codex/runs/phase9_encoder_cngram/result.json"
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    if args.negative_samples > 0 and out_dir.name == "phase9_encoder_riwh":
        out_dir = out_dir.parent / f"phase9_encoder_riwh_neg{args.negative_samples}"
    print(
        f"random_index_hebbian smoke  D={args.D}  n_active={args.n_active}  "
        f"window={args.window}  sub={args.subsample}  neg={args.negative_samples}  seed={args.seed}"
    )
    result = run_smoke(
        Path(args.dataset), out_dir, args.D, args.n_active, args.window,
        args.subsample, args.seed, Path(args.floor) if args.floor else None,
        negative_samples=args.negative_samples,
    )
    m = result["metrics"]
    print(f"  encoder: {result['config']['encoder']}")
    print(f"  vocab: {result['config']['vocab_size']} words, {result['config']['total_tokens_seen']} tokens")
    print(f"  fit/encode/retrieve wall: {m['fit_wall_seconds']}s / {m['encode_wall_seconds']}s / {m['retrieval_wall_seconds']}s")
    print(f"  top-1 by type: {m['top1_accuracy_by_type']}")
    pc = m["pairwise_cosine_off_diagonal"]
    print(f"  pairwise cos off-diag: mean={pc['mean']:+.4f} std={pc['std']:.4f}")
    if m.get("expected_turn_cosine") and m.get("absent_top1_cosine"):
        ec = m["expected_turn_cosine"]
        ac = m["absent_top1_cosine"]
        gap = ec["mean"] - ac["mean"]
        print(f"  signal-vs-noise: expected={ec['mean']:.4f} absent={ac['mean']:.4f} gap={gap:+.4f}")
    if "comparison_vs_floor" in result:
        c = result["comparison_vs_floor"]
        print(f"  ΔACCURACY vs floor: {c['delta_top1_accuracy_by_type']}")
        print(f"  signal_gap floor={c['floor_signal_gap']:+.4f} → riwh={c['riwh_signal_gap']:+.4f}  flipped_positive={c['signal_gap_flipped_positive']}")
    print(f"  top dropped (subsampled) words: {m['top_dropped_words'][:5]}")
    print(f"  wrote {out_dir / 'result.json'}")


if __name__ == "__main__":
    main()
