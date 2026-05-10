"""
hdc_vs_naive_comparison.py — quantify the memory-vs-accuracy trade-off.

For a given D and N, run the same conversation-style task two ways:
  (a) HDC: single D-dim accumulator, Hebbian writes, sign-cleanup retrieval
  (b) Naive: store all (key, value) bipolar pairs explicitly; query by
      argmax-dot-product key match, return the matched value

Compare:
  - retrieval_accuracy: HDC drops as N exceeds capacity; naive stays 100%
  - memory_bytes_conversation: HDC is constant in N; naive grows linearly
  - retrieval_wall_seconds: HDC is one matvec; naive is N matvecs

Author: Raphael
Phase: 8 — beyond_transformer_organic_memory
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from project_x.experiments.hdc_substrate import (
    cleanup,
    random_vector,
    read,
    write,
)


def run_hdc_arm(d: int, n_turns: int, n_vocab: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    turn_ids = np.stack([random_vector(d, rng) for _ in range(n_turns)])
    vocab = np.stack([random_vector(d, rng) for _ in range(n_vocab)])
    spoken = rng.integers(0, n_vocab, size=n_turns)

    M: np.ndarray | None = None
    t_write = time.time()
    for t in range(n_turns):
        M = write(M, turn_ids[t], vocab[spoken[t]])
    write_secs = time.time() - t_write

    correct = 0
    t_read = time.time()
    for t in range(n_turns):
        retrieved = read(M, turn_ids[t])
        snapped, idx, _ = cleanup(retrieved, vocab)
        if idx == int(spoken[t]):
            correct += 1
    read_secs = time.time() - t_read

    # Memory = D-dim int32 accumulator (the conversation-dependent part)
    memory_bytes = M.nbytes
    return {
        "method": "HDC",
        "memory_bytes": int(memory_bytes),
        "retrieval_accuracy": correct / n_turns,
        "write_seconds": write_secs,
        "read_seconds": read_secs,
    }


def run_naive_arm(d: int, n_turns: int, n_vocab: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    turn_ids = np.stack([random_vector(d, rng) for _ in range(n_turns)])
    vocab = np.stack([random_vector(d, rng) for _ in range(n_vocab)])
    spoken = rng.integers(0, n_vocab, size=n_turns)

    # Naive: store explicit (key, value) pairs.
    # Stored values are vocab[spoken[t]] for each turn.
    keys_store = turn_ids                              # shape (n_turns, D)
    values_store = vocab[spoken]                       # shape (n_turns, D)

    t_write = time.time()
    write_secs = time.time() - t_write  # writes are O(1) per item (just append, in this NumPy block-allocated form already done)

    correct = 0
    t_read = time.time()
    for t in range(n_turns):
        # Find the key that best matches the query key (here: identical, so argmax matches turn t)
        sims = keys_store @ turn_ids[t].astype(np.int32)
        match_idx = int(np.argmax(sims))
        retrieved_value = values_store[match_idx]
        # Cleanup against vocabulary (same as HDC arm for fair comparison)
        snapped, vocab_idx, _ = cleanup(retrieved_value, vocab)
        if vocab_idx == int(spoken[t]):
            correct += 1
    read_secs = time.time() - t_read

    memory_bytes = keys_store.nbytes + values_store.nbytes  # the conversation-dependent storage
    return {
        "method": "Naive",
        "memory_bytes": int(memory_bytes),
        "retrieval_accuracy": correct / n_turns,
        "write_seconds": write_secs,
        "read_seconds": read_secs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--D", type=int, default=10000)
    parser.add_argument("--n-grid", type=str, default="100,500,1000,2000,5000")
    parser.add_argument("--n-vocab", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--save", type=str, default="gpt-codex/runs/phase8_comparison")
    args = parser.parse_args()
    save_dir = Path(args.save)
    save_dir.mkdir(parents=True, exist_ok=True)

    n_grid = [int(x) for x in args.n_grid.split(",")]
    rows = []
    print(f"D={args.D}  n_vocab={args.n_vocab}  seed={args.seed}")
    print(f"{'N':>6} {'method':>8} {'mem_KB':>10} {'accuracy':>10} {'read_s':>8}")
    print("=" * 50)
    for n in n_grid:
        hdc = run_hdc_arm(args.D, n, args.n_vocab, args.seed)
        naive = run_naive_arm(args.D, n, args.n_vocab, args.seed)
        rows.append({"N": n, "hdc": hdc, "naive": naive,
                     "memory_savings_factor": naive["memory_bytes"] / hdc["memory_bytes"]})
        print(f"{n:>6d} {'HDC':>8} {hdc['memory_bytes']/1024:>10.1f} {hdc['retrieval_accuracy']:>10.4f} {hdc['read_seconds']:>8.2f}")
        print(f"{n:>6d} {'Naive':>8} {naive['memory_bytes']/1024:>10.1f} {naive['retrieval_accuracy']:>10.4f} {naive['read_seconds']:>8.2f}")
        print(f"       savings: {rows[-1]['memory_savings_factor']:.1f}x")
        print()

    summary = {
        "D": args.D,
        "n_vocab": args.n_vocab,
        "seed": args.seed,
        "n_grid": n_grid,
        "rows": rows,
    }
    (save_dir / f"comparison_D{args.D}_v{args.n_vocab}_s{args.seed}.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
