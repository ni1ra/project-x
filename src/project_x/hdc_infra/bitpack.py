"""Bit-packed binary HDC primitives — cycle-13 #1 substrate.

Maps bipolar `{-1, +1}` int8 hypervectors ↔ binary `{0, 1}` uint32-packed
representation; computes cosine on the packed form via popcount-over-XOR.
The identity:

    For bipolar a, b ∈ {-1, +1}^D:
        cos(a, b) = (a · b) / D
                  = (#agreements − #disagreements) / D
                  = (D − 2·#disagreements) / D

    Mapping -1 → 0, +1 → 1:
        #disagreements_bipolar(a, b) == popcount(binary_a XOR binary_b)

    Therefore:
        cos(a, b) = (D − 2·popcount(packed_a XOR packed_b)) / D

This is mathematically EXACT for bipolar input — not an approximation. The
empirical-equivalence test in `tests/test_bitpack.py` verifies floating-point
equality to `< 1e-9` over random + edge-case bipolar pairs.

Storage: D=10240 bipolar int8 → 10240 bytes; D=10240 packed uint32 → 1280
bytes (320 uint32 × 4 bytes). ≈8× compression vs int8; ≈32× vs int32. At
22k-fragment Tier-2 corpus × ~80k unique trigrams, int8 footprint exceeds
the 7.8 GB WSL ceiling (cycle-12 crash); packed footprint fits in ~96-239 MB.

Constraint: D % 32 == 0 (one packed uint32 word covers 32 bipolar dims). The
encoder's default D bumps from 10000 to 10240 (320 × 32) to satisfy this;
existing D=10000 callers can pad or re-encode at D=10240.
"""

from __future__ import annotations

import numpy as np

# 32 bits per packed word. uint to avoid sign-bit confusion under shifts;
# the popcount identity is bit-level so signedness doesn't matter for the
# arithmetic, but uint keeps the abstraction clean.
PACK_DTYPE = np.uint32


def pack_bipolar(hv: np.ndarray) -> np.ndarray:
    """Convert a bipolar (D,) int8 hypervector to a packed (D/32,) uint32.

    Mapping: -1 → 0 bit, +1 → 1 bit. The bipolar convention `sign(0) = +1`
    is honored by mapping `hv >= 0` (not `hv > 0`); zero inputs (rare; the
    encoder produces ±1 by `sign(proj)` which only yields 0 for exactly-zero
    projections) become +1 in the packed form, mirroring `cosine_bipolar`'s
    treatment.

    Raises ValueError if D % 32 != 0 — the constraint is documented at the
    module level and callers (encoder + downstream) must satisfy it.
    """
    if hv.ndim != 1:
        raise ValueError(f"pack_bipolar expects 1-D input, got shape {hv.shape}")
    D = hv.shape[0]
    if D % 32 != 0:
        raise ValueError(
            f"pack_bipolar requires D % 32 == 0; got D={D}. "
            f"Bump encoder default to D=10240 (320×32) or D=9984 (312×32)."
        )
    # Pack the boolean mask (hv >= 0) into a uint8 array (8 bits per byte),
    # then re-view 4 consecutive bytes as one uint32 word. `bitorder='big'`
    # keeps the MSB-first convention consistent with the unpacking inverse.
    # The view preserves byte order; popcount is endian-independent so the
    # downstream cosine_packed is also endian-independent.
    bits = (hv >= 0).astype(np.uint8)
    packed_u8 = np.packbits(bits, bitorder="big")
    # (D/8,) uint8 → (D/32,) uint32 via view. The view is a re-interpretation,
    # not a copy.
    return packed_u8.view(PACK_DTYPE)


def unpack_bipolar(packed: np.ndarray, D: int) -> np.ndarray:
    """Inverse of `pack_bipolar`. Returns (D,) int8 with values in {-1, +1}.

    The `D` parameter is REQUIRED because packed shape alone underdetermines
    the trailing-bit count (a (D/32,) uint32 array is the same shape whether
    D=320 or D=320+1 truncated — but D % 32 != 0 was rejected at pack time,
    so this is mostly defensive). The argument also serves as documentation
    at every callsite.
    """
    if packed.dtype != PACK_DTYPE:
        raise ValueError(
            f"unpack_bipolar expects {PACK_DTYPE.__name__} input, got {packed.dtype}"
        )
    if D % 32 != 0:
        raise ValueError(f"unpack_bipolar requires D % 32 == 0; got D={D}")
    expected_words = D // 32
    if packed.shape != (expected_words,):
        raise ValueError(
            f"unpack_bipolar shape mismatch: D={D} requires {expected_words} uint32 "
            f"words; got {packed.shape}"
        )
    # uint32 → uint8 view → unpackbits → bool mask → ±1.
    packed_u8 = packed.view(np.uint8)
    bits = np.unpackbits(packed_u8, bitorder="big")  # (D,) uint8 ∈ {0, 1}
    # 0 → -1, 1 → +1. Multiply-by-2-minus-1 keeps it as int8 cleanly.
    return (bits.astype(np.int8) * 2 - 1).astype(np.int8)


def cosine_packed(a_packed: np.ndarray, b_packed: np.ndarray, D: int) -> float:
    """Cosine between two packed bipolar hypervectors. Mathematically equal
    to `cosine_bipolar(unpack_bipolar(a_packed, D), unpack_bipolar(b_packed, D))`.

    Identity used:
        cos = (D − 2·popcount(a_packed XOR b_packed)) / D

    Uses `np.bitwise_count` (NumPy 2.0+) for vectorized per-element popcount;
    falls back to `np.unpackbits` if `bitwise_count` is unavailable.
    """
    if a_packed.shape != b_packed.shape:
        raise ValueError(
            f"cosine_packed shape mismatch: {a_packed.shape} vs {b_packed.shape}"
        )
    if a_packed.dtype != PACK_DTYPE or b_packed.dtype != PACK_DTYPE:
        raise ValueError(
            f"cosine_packed expects both inputs to be {PACK_DTYPE.__name__}; "
            f"got {a_packed.dtype}, {b_packed.dtype}"
        )
    if D % 32 != 0 or D // 32 != a_packed.shape[0]:
        raise ValueError(
            f"cosine_packed D={D} inconsistent with packed shape {a_packed.shape}; "
            f"expected ({D // 32},)"
        )
    xor = a_packed ^ b_packed
    if hasattr(np, "bitwise_count"):
        # NumPy 2.0+: vectorized popcount per element, sum across the array.
        popcount = int(np.bitwise_count(xor).sum())
    else:
        # Fallback: view as uint8, unpackbits, sum the resulting bool array.
        # ~3-5× slower than bitwise_count but correctness-equivalent.
        popcount = int(np.unpackbits(xor.view(np.uint8)).sum())
    return float(D - 2 * popcount) / float(D)
