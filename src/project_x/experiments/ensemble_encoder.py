"""
ensemble_encoder.py — Phase 9 Cycle 4 Track B.

Combines two organic encoders (CharNgramHashEncoder floor + RandomIndexHebbianEncoder
with negative sampling) by averaging their cosine matrices. The two have
COMPLEMENTARY failure modes per Cycle 3 evidence:

  CharNgramHash      → wins paraphrase (38.3%) via surface-substring overlap
  RandomIndexHebbian → wins exact (62% w/ neg=5) and contradiction (23%)
                       via word-co-occurrence statistics

Combination rules tested:
  alpha-blend: combined_cos = alpha * floor_cos + (1 - alpha) * hebbian_cos
  max:         combined_cos = max(floor_cos, hebbian_cos)
  per-type:    if query starts with "what does X prefer" / "what did we decide" → hebbian
               else → floor (cheap heuristic; cycle 5 could learn this)

The ensemble does NOT introduce any pretrained model — it's a linear combination
of cosines from two organic encoders, plus an optional rule-based router.

Author: Raphael
Phase: 9 — semantic_hdc_memory_agent (Cycle 4 Track B, council ensemble idea)
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from project_x.experiments.encoder import (
    CharNgramHashEncoder,
    cosine_matrix_bipolar,
)
from project_x.experiments.random_index_hebbian import RandomIndexHebbianEncoder


def evaluate_top1(
    cos_mat: np.ndarray,  # (n_queries, n_turns)
    queries: list[dict],
) -> tuple[dict[str, float | None], list[float], list[float]]:
    """Returns (accuracy_by_type, expected_cosines, absent_top1_cosines)."""
    bucket: dict[str, dict] = {}
    expected_cos: list[float] = []
    absent_cos: list[float] = []
    for qi, q in enumerate(queries):
        qtype = q["type"]
        sims = cos_mat[qi]
        top1_idx = int(np.argmax(sims))
        expected_ids = q["expected_turn_ids"]
        b = bucket.setdefault(qtype, {"correct": 0, "n": 0})
        if expected_ids:
            b["n"] += 1
            if top1_idx in expected_ids:
                b["correct"] += 1
            expected_cos.append(float(sims[expected_ids[0]]))
        else:
            absent_cos.append(float(sims[top1_idx]))
    acc = {
        k: round(b["correct"] / b["n"], 4) if b["n"] > 0 else None
        for k, b in bucket.items()
    }
    return acc, expected_cos, absent_cos


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=str,
                        default="gpt-codex/runs/phase9_dataset_full")
    parser.add_argument("--out", type=str,
                        default="gpt-codex/runs/phase9_encoder_ensemble")
    parser.add_argument("--D", type=int, default=10000)
    parser.add_argument("--negative-samples", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1337)
    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    with (dataset_dir / "conversation.jsonl").open() as f:
        turns = [json.loads(line) for line in f]
    with (dataset_dir / "queries.jsonl").open() as f:
        queries = [json.loads(line) for line in f]
    turn_texts = [t["text"] for t in turns]
    query_texts = [q["text"] for q in queries]

    # Train both encoders
    t0 = time.time()
    floor = CharNgramHashEncoder(D=args.D, feature_dim=4096, n=3, seed=args.seed)
    hebbian = RandomIndexHebbianEncoder(
        D=args.D, n_active=10, window=3, subsample_threshold=1e-3,
        negative_samples=args.negative_samples, seed=args.seed,
    )
    hebbian.fit(turn_texts)
    fit_wall = time.time() - t0

    # Encode + compute cosine matrices for both
    t1 = time.time()
    floor_turn = floor.encode(turn_texts)
    floor_query = floor.encode(query_texts)
    heb_turn = hebbian.encode(turn_texts)
    heb_query = hebbian.encode(query_texts)
    encode_wall = time.time() - t1

    floor_cos = cosine_matrix_bipolar(floor_query, floor_turn)
    heb_cos = cosine_matrix_bipolar(heb_query, heb_turn)

    # --- Combination rules ---

    # 1. alpha-blend across alpha ∈ {0.3, 0.4, 0.5, 0.6, 0.7}
    blend_results = {}
    for alpha in [0.3, 0.4, 0.5, 0.6, 0.7]:
        combined = alpha * floor_cos + (1.0 - alpha) * heb_cos
        acc, exp_cos, abs_cos = evaluate_top1(combined, queries)
        gap = (np.mean(exp_cos) - np.mean(abs_cos)) if exp_cos and abs_cos else None
        blend_results[f"alpha_{alpha}"] = {
            "top1": acc,
            "signal_gap": round(float(gap), 4) if gap is not None else None,
        }

    # 2. max-cosine
    max_combined = np.maximum(floor_cos, heb_cos)
    max_acc, max_exp, max_abs = evaluate_top1(max_combined, queries)
    max_result = {
        "top1": max_acc,
        "signal_gap": round(float(np.mean(max_exp) - np.mean(max_abs)), 4),
    }

    # 3. per-type rule-based router
    router_top1 = {}
    router_correct: dict[str, dict] = {}
    router_exp_cos: list[float] = []
    router_abs_cos: list[float] = []
    for qi, q in enumerate(queries):
        text_lower = q["text"].lower()
        # Routing rule: paraphrase-shaped queries → floor; everything else → hebbian
        # (paraphrase queries use rephrased natural language; floor handles surface
        #  overlap; hebbian handles exact-fact and contradiction lookups)
        if "remind me" in text_lower or "what is" in text_lower or "tend" in text_lower or "favorite" in text_lower:
            sims = floor_cos[qi]
        else:
            sims = heb_cos[qi]
        top1_idx = int(np.argmax(sims))
        expected_ids = q["expected_turn_ids"]
        b = router_correct.setdefault(q["type"], {"correct": 0, "n": 0})
        if expected_ids:
            b["n"] += 1
            if top1_idx in expected_ids:
                b["correct"] += 1
            router_exp_cos.append(float(sims[expected_ids[0]]))
        else:
            router_abs_cos.append(float(sims[top1_idx]))
    for k, b in router_correct.items():
        router_top1[k] = round(b["correct"] / b["n"], 4) if b["n"] > 0 else None
    router_gap = float(np.mean(router_exp_cos) - np.mean(router_abs_cos))

    # --- Standalone references for comparison ---
    floor_acc, floor_exp, floor_abs = evaluate_top1(floor_cos, queries)
    heb_acc, heb_exp, heb_abs = evaluate_top1(heb_cos, queries)
    floor_gap = float(np.mean(floor_exp) - np.mean(floor_abs))
    heb_gap = float(np.mean(heb_exp) - np.mean(heb_abs))

    # --- Pick the best alpha by paraphrase + exact balance ---
    def score(r):
        acc = r["top1"]
        # weight: paraphrase 1.0, exact 1.0, contradiction 0.5, multi_hop 0.5; gap-positive bonus
        return (
            (acc.get("semantic_paraphrase") or 0)
            + (acc.get("exact_turn_lookup") or 0)
            + 0.5 * (acc.get("contradiction") or 0)
            + 0.5 * (acc.get("multi_hop") or 0)
            + (0.1 if (r["signal_gap"] or -1) > 0 else 0)
        )

    best_alpha_key = max(blend_results, key=lambda k: score(blend_results[k]))

    result = {
        "run_id": f"phase9_encoder_ensemble_seed{args.seed}_neg{args.negative_samples}",
        "config": {
            "D": args.D,
            "negative_samples": args.negative_samples,
            "seed": args.seed,
            "n_turns": len(turns),
            "n_queries": len(queries),
            "floor": floor.name(),
            "hebbian": hebbian.name(),
        },
        "metrics": {
            "fit_wall_seconds": round(fit_wall, 4),
            "encode_wall_seconds": round(encode_wall, 4),
            "standalone_floor": {
                "top1": floor_acc, "signal_gap": round(floor_gap, 4),
            },
            "standalone_hebbian": {
                "top1": heb_acc, "signal_gap": round(heb_gap, 4),
            },
            "alpha_blend": blend_results,
            "max_cosine": max_result,
            "rule_based_router": {
                "top1": router_top1, "signal_gap": round(router_gap, 4),
            },
            "best_alpha_by_combined_score": best_alpha_key,
        },
        "notes": [
            "Ensemble combines floor + Hebbian (with optional negative sampling) by combining their cosine matrices.",
            "Paraphrase queries depend on surface overlap (floor's strength); exact/contradiction depend on word-content (hebbian's strength).",
            "Rule-based router is a cheap heuristic — cycle 5 could learn the routing.",
        ],
    }
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))

    # Pretty print summary
    print(f"ENSEMBLE  D={args.D}  neg={args.negative_samples}  seed={args.seed}")
    print(f"  fit/encode wall: {fit_wall:.3f}s / {encode_wall:.3f}s")
    print(f"  standalone floor   : top1={floor_acc} gap={floor_gap:+.4f}")
    print(f"  standalone hebbian : top1={heb_acc} gap={heb_gap:+.4f}")
    print(f"  alpha-blend variants:")
    for k, r in blend_results.items():
        print(f"    {k}: top1={r['top1']} gap={r['signal_gap']:+.4f}")
    print(f"  max_cosine        : top1={max_result['top1']} gap={max_result['signal_gap']:+.4f}")
    print(f"  rule_based_router : top1={router_top1} gap={router_gap:+.4f}")
    print(f"  best alpha by score: {best_alpha_key}")
    print(f"  wrote {out_dir / 'result.json'}")


if __name__ == "__main__":
    main()
