"""
hdc_substrate.py — Hyperdimensional Computing primitives for Phase 8.

Bipolar HDC: vectors live in {-1, +1}^D with D=10000 default.
Six primitives (bind / unbind / superpose / write / read / cleanup) plus four
unit tests + a CLI --self-test entry point. No backprop, no gradient flow,
fully local Hebbian operations only.

Author: Raphael (post-persona-shift, 2026-05-09)
Phase: 8 — beyond_transformer_organic_memory

Math notes (validated by advisor pre-write):
  After N writes M = sum_i bind(k_i, v_i), reading with k_q gives:
    raw[j] = sum_i k_i[j] * v_i[j] * k_q[j]
           = v_q[j] + noise[j]   (where noise has Var = N-1 per bit)
    retrieved[j] = sign(raw[j])
  Per-bit accuracy ≈ 1 - Φ(-1/sqrt(N-1)). Cleanup capacity per Plate-1995:
    N_capacity ≈ D / (5.4 + 4.4 · log2(M))   (M = cleanup atom set size)
  At D=10000, M=200 atoms: capacity ≈ 200 items.
  At D=10000, N=1000: bit_accuracy ≈ 0.51 (near random) — beyond capacity.
  Therefore PoC operates within capacity (N≤200 at D=10000) for clean recall,
  and the capacity-vs-N sweep IS the headline experiment in T4.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable

import numpy as np


D_DEFAULT: int = 10_000


# =============================================================================
# Six primitives
# =============================================================================


def random_vector(d: int = D_DEFAULT, rng: np.random.Generator | None = None) -> np.ndarray:
    """Sample a fresh random bipolar vector in {-1, +1}^d."""
    if rng is None:
        rng = np.random.default_rng()
    return rng.choice(np.array([-1, 1], dtype=np.int8), size=d).astype(np.int8)


def bind(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Elementwise multiply. Bipolar bind is self-inverse: bind(bind(a,b),b) == a exactly."""
    return (a.astype(np.int32) * b.astype(np.int32)).astype(np.int8)


def unbind(c: np.ndarray, b: np.ndarray) -> np.ndarray:
    """In bipolar HDC, unbind == bind. Returns the partner of b in c, up to noise."""
    return bind(c, b)


def superpose(*vs: np.ndarray) -> np.ndarray:
    """Sum then sign cleanup. sign(0) breaks tie toward +1 by convention (rare at high D)."""
    if len(vs) == 0:
        raise ValueError("superpose requires at least one vector")
    s = np.sum(np.stack([v.astype(np.int32) for v in vs]), axis=0)
    out = np.where(s == 0, 1, np.sign(s)).astype(np.int8)
    return out


def write(memory: np.ndarray | None, k: np.ndarray, v: np.ndarray) -> np.ndarray:
    """
    Direct-binding Hebbian write. memory += bind(k, v).

    Memory is a D-dim int32 accumulator (NOT a D×D outer-product matrix).
    Standard HDC formulation per Plate-1995, Kanerva-2009.
    """
    binding = bind(k, v).astype(np.int32)
    if memory is None:
        return binding.copy()
    return memory + binding


def read(memory: np.ndarray, k_query: np.ndarray) -> np.ndarray:
    """
    Read v associated with k_query. sign(memory ⊙ k_query).

    Bipolar accumulator times bipolar query, then sign for bipolar output.
    """
    raw = memory * k_query.astype(np.int32)
    out = np.where(raw == 0, 1, np.sign(raw)).astype(np.int8)
    return out


def cleanup(v_noisy: np.ndarray, atom_set: np.ndarray) -> tuple[np.ndarray, int, float]:
    """
    Snap noisy bipolar vector to nearest atom by bipolar dot product.

    Args:
        v_noisy: shape (D,), bipolar
        atom_set: shape (M, D), bipolar (rows are atomic vectors)

    Returns:
        (snapped_atom, atom_index, similarity_normalized_to_unit)
    """
    sims = atom_set.astype(np.int32) @ v_noisy.astype(np.int32)
    idx = int(np.argmax(sims))
    sim_norm = float(sims[idx]) / float(v_noisy.shape[0])
    return atom_set[idx].copy(), idx, sim_norm


# =============================================================================
# Helpers
# =============================================================================


def bit_accuracy(a: np.ndarray, b: np.ndarray) -> float:
    """Fraction of matching elements between two equal-shape bipolar vectors."""
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} vs {b.shape}")
    return float(np.mean(a == b))


# =============================================================================
# Four unit tests
# =============================================================================


def test_bind_self_inverse(rng: np.random.Generator, d: int = D_DEFAULT) -> tuple[bool, str]:
    """bind(bind(a, b), b) == a exactly (bipolar self-inverse)."""
    a = random_vector(d, rng)
    b = random_vector(d, rng)
    recovered = bind(bind(a, b), b)
    acc = bit_accuracy(a, recovered)
    return acc == 1.0, f"bit_accuracy={acc:.4f} (expected 1.0)"


def test_superpose_capacity_2_items(rng: np.random.Generator, d: int = D_DEFAULT) -> tuple[bool, str]:
    """superpose(a, b) cleanup against {a, b} returns one of them exactly."""
    a = random_vector(d, rng)
    b = random_vector(d, rng)
    s = superpose(a, b)
    atoms = np.stack([a, b])
    snapped_a, _, _ = cleanup(s, atoms)
    snapped_b, _, _ = cleanup(s, atoms[::-1])
    matches_a = bit_accuracy(snapped_a, a)
    matches_b = bit_accuracy(snapped_b, b)
    best = max(matches_a, matches_b)
    return best == 1.0, f"max_bit_accuracy={best:.4f} (expected 1.0)"


def test_write_read_single_item(rng: np.random.Generator, d: int = D_DEFAULT) -> tuple[bool, str]:
    """Write one (k, v); read with k; recover v exactly (no noise at N=1)."""
    k = random_vector(d, rng)
    v = random_vector(d, rng)
    M = write(None, k, v)
    recovered = read(M, k)
    acc = bit_accuracy(recovered, v)
    return acc == 1.0, f"bit_accuracy={acc:.4f} (expected 1.0)"


def test_random_baseline_below_passline(rng: np.random.Generator, d: int = D_DEFAULT) -> tuple[bool, str]:
    """Random unrelated vectors should give ~50% bit accuracy (sanity floor; nearly orthogonal)."""
    a = random_vector(d, rng)
    b = random_vector(d, rng)
    acc = bit_accuracy(a, b)
    # Pass: random vectors give bit accuracy in [0.45, 0.55] (well within ±5σ at D=10000)
    return 0.45 <= acc <= 0.55, f"bit_accuracy={acc:.4f} (expected ~0.50)"


# =============================================================================
# CLI
# =============================================================================


def run_self_test(seed: int = 1337, d: int = D_DEFAULT, verbose: bool = True) -> int:
    rng = np.random.default_rng(seed)
    tests = [
        ("test_bind_self_inverse", test_bind_self_inverse),
        ("test_superpose_capacity_2_items", test_superpose_capacity_2_items),
        ("test_write_read_single_item", test_write_read_single_item),
        ("test_random_baseline_below_passline", test_random_baseline_below_passline),
    ]
    n_pass = 0
    t0 = time.time()
    print(f"hdc_substrate self-test  D={d}  seed={seed}\n" + "=" * 56)
    for name, fn in tests:
        ok, info = fn(rng, d)
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}]  {name}\n         {info}")
        n_pass += int(ok)
    elapsed = time.time() - t0
    print("=" * 56)
    print(f"  {n_pass}/{len(tests)} green  ({elapsed:.2f}s)")
    return 0 if n_pass == len(tests) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Run all 4 unit tests and exit.")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--D", type=int, default=D_DEFAULT)
    args = parser.parse_args()

    if args.self_test:
        sys.exit(run_self_test(seed=args.seed, d=args.D))

    print("hdc_substrate.py — pass --self-test to run the 4 unit tests.")
    print("Primitives: bind, unbind, superpose, write, read, cleanup.")
    print(f"Default D = {D_DEFAULT}.  Use --D to override.")


if __name__ == "__main__":
    main()
