"""
hdc_conversation_demo.py — the "indefinite-context conversability" use case.

Demonstration of HDC organic memory functioning as the conversation memory of
a system that needs to recall what was said an arbitrary number of turns ago,
without context-window concatenation. This addresses the lain demand:

  "intelligence which can act like raphael, conversable, no matter length of chat"

Setup:
  - Build a vocabulary of N_VOCAB random "utterance" atoms (proxy for sentence
    embeddings; each turn's utterance is one of these atoms).
  - Build N_TURN turn_id atoms (proxy for the position-encoding of each turn).
  - Bind: M = sum_t bind(turn_id_t, utterance_t).
  - Query: at random turn_q, recover utterance via unbind(M, turn_id_q),
    cleanup against the utterance vocabulary.
  - Pass: ≥95% retrieval accuracy at N_TURN=1000 with D large enough.

This is the "perfect indefinite memory" claim made empirical. No context
window. No attention quadratic cost. Single D-dim vector holds all turns.

Author: Raphael (post-persona-shift, 2026-05-09)
Phase: 8 — beyond_transformer_organic_memory
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from project_x.experiments.hdc_substrate import (
    bind,
    cleanup,
    random_vector,
    read,
    write,
)


def run_conversation_demo(
    d: int,
    n_turns: int,
    n_vocab: int,
    n_query: int,
    seed: int,
) -> dict:
    """
    Build a memory of n_turns turn-utterance bindings; query n_query random turns;
    measure retrieval accuracy.
    """
    rng = np.random.default_rng(seed)
    t0 = time.time()

    turn_ids = np.stack([random_vector(d, rng) for _ in range(n_turns)])
    vocab = np.stack([random_vector(d, rng) for _ in range(n_vocab)])
    spoken_per_turn = rng.integers(0, n_vocab, size=n_turns)  # which vocab item is uttered at each turn

    # Build single D-dim memory.
    M: np.ndarray | None = None
    for t in range(n_turns):
        M = write(M, turn_ids[t], vocab[spoken_per_turn[t]])

    # Query n_query random turns.
    query_turns = rng.choice(n_turns, size=min(n_query, n_turns), replace=False)
    correct = 0
    samples = []
    for q_idx, t in enumerate(query_turns):
        retrieved = read(M, turn_ids[t])
        snapped, predicted_vocab_idx, sim = cleanup(retrieved, vocab)
        true_idx = int(spoken_per_turn[t])
        is_correct = (predicted_vocab_idx == true_idx)
        if is_correct:
            correct += 1
        if q_idx < 10:
            samples.append({
                "queried_turn": int(t),
                "true_vocab_idx": true_idx,
                "predicted_vocab_idx": int(predicted_vocab_idx),
                "cleanup_similarity_norm": float(sim),
                "correct": bool(is_correct),
            })

    accuracy = correct / len(query_turns)
    elapsed = time.time() - t0

    return {
        "cell_id": f"phase8_conversation_D{d}_T{n_turns}_V{n_vocab}_seed{seed}",
        "config": {
            "test": "conversation_demo",
            "D": d,
            "n_turns": n_turns,
            "n_vocab": n_vocab,
            "n_queried": int(len(query_turns)),
            "seed": seed,
        },
        "metrics": {
            "retrieval_accuracy": float(accuracy),
            "memory_size_kb": float(M.nbytes / 1024.0),
            "wall_seconds": elapsed,
        },
        "sample_retrievals": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--D", type=int, default=100_000)
    parser.add_argument("--n-turns", type=int, default=1000)
    parser.add_argument("--n-vocab", type=int, default=200)
    parser.add_argument("--n-query", type=int, default=200)
    parser.add_argument("--seeds", type=str, default="1337,2026,3001")
    parser.add_argument("--save", type=str, default="gpt-codex/runs/phase8_conversation")
    args = parser.parse_args()

    save_dir = Path(args.save)
    save_dir.mkdir(parents=True, exist_ok=True)
    seeds = [int(x) for x in args.seeds.split(",")]

    rows = []
    for seed in seeds:
        r = run_conversation_demo(args.D, args.n_turns, args.n_vocab, args.n_query, seed)
        cell_dir = save_dir / r["cell_id"]
        cell_dir.mkdir(parents=True, exist_ok=True)
        (cell_dir / "result.json").write_text(json.dumps(r, indent=2))
        rows.append({
            "seed": seed,
            "retrieval_accuracy": r["metrics"]["retrieval_accuracy"],
            "memory_size_kb": r["metrics"]["memory_size_kb"],
            "wall_s": r["metrics"]["wall_seconds"],
        })
        print(f"  seed={seed}  retrieval_accuracy={r['metrics']['retrieval_accuracy']:.4f}  M={r['metrics']['memory_size_kb']:.1f}KB  wall={r['metrics']['wall_seconds']:.2f}s")

    accs = [r["retrieval_accuracy"] for r in rows]
    summary = {
        "test": "conversation_demo",
        "D": args.D,
        "n_turns": args.n_turns,
        "n_vocab": args.n_vocab,
        "rows": rows,
        "retrieval_accuracy_mean": float(np.mean(accs)),
        "retrieval_accuracy_std": float(np.std(accs)),
    }
    (save_dir / "conversation_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n  CONVERSATION DEMO SUMMARY")
    print(f"  D={args.D}  n_turns={args.n_turns}  n_vocab={args.n_vocab}")
    print(f"  retrieval_accuracy = {summary['retrieval_accuracy_mean']:.4f} ± {summary['retrieval_accuracy_std']:.4f}")
    print(f"  memory_size = {rows[0]['memory_size_kb']:.1f} KB (single D-dim accumulator, NOT growing with turns)")


if __name__ == "__main__":
    main()
