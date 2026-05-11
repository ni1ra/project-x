"""Tests for `src/project_x/hdc_infra/bitpack.py` — cycle-13 #07b.

The load-bearing claim: `cosine_packed(pack(a), pack(b), D)` is mathematically
exact-equal to `cosine_bipolar(a, b)` for bipolar a, b ∈ {-1, +1}^D. The
identity is bit-precise (integer math under the hood); the float division at
the end is the only source of floating-point error and even that vanishes
for the typical D values used here (powers-of-2 or close).

The smoke at commit `ff46c2b` showed diff = 0.00e+00 on D=10240. These tests
formalize that across 50 random pairs + edge cases + boundary conditions.
"""

from __future__ import annotations

import numpy as np
import pytest

from project_x.experiments.encoder import cosine_bipolar
from project_x.hdc_infra import (
    PACK_DTYPE,
    cosine_packed,
    pack_bipolar,
    unpack_bipolar,
)


# ---------- helpers ----------


def random_bipolar(D: int, rng: np.random.Generator) -> np.ndarray:
    """Random ±1 bipolar hypervector at dimension D."""
    return (rng.integers(0, 2, size=D, dtype=np.int8) * 2 - 1).astype(np.int8)


# ---------- round-trip ----------


def test_round_trip_D10240():
    """pack → unpack is bit-exact at the cycle-13 default dim."""
    rng = np.random.default_rng(42)
    D = 10240
    hv = random_bipolar(D, rng)
    packed = pack_bipolar(hv)
    assert packed.shape == (D // 32,), f"expected {(D//32,)}, got {packed.shape}"
    assert packed.dtype == PACK_DTYPE
    unpacked = unpack_bipolar(packed, D)
    assert unpacked.dtype == np.int8
    assert np.array_equal(hv, unpacked), "round-trip failed at D=10240"


@pytest.mark.parametrize("D", [32, 64, 96, 128, 256, 512, 1024, 4096, 9984, 10240])
def test_round_trip_multiple_D(D):
    """Round-trip is bit-exact across a range of D % 32 == 0 dimensions."""
    rng = np.random.default_rng(D)  # seed = D for reproducibility per dim
    hv = random_bipolar(D, rng)
    packed = pack_bipolar(hv)
    assert packed.shape == (D // 32,)
    assert packed.dtype == PACK_DTYPE
    unpacked = unpack_bipolar(packed, D)
    assert np.array_equal(hv, unpacked), f"round-trip failed at D={D}"


# ---------- cosine equivalence ----------


def test_cosine_equivalence_50_random_pairs():
    """The load-bearing test: 50 random bipolar pairs at D=10240; cosine_packed
    matches cosine_bipolar to <1e-9 (in practice exact integer math)."""
    rng = np.random.default_rng(1337)
    D = 10240
    for trial in range(50):
        a = random_bipolar(D, rng)
        b = random_bipolar(D, rng)
        a_p = pack_bipolar(a)
        b_p = pack_bipolar(b)
        c_bipolar = cosine_bipolar(a, b)
        c_packed = cosine_packed(a_p, b_p, D)
        assert abs(c_bipolar - c_packed) < 1e-9, (
            f"trial {trial}: cosine_bipolar={c_bipolar}, "
            f"cosine_packed={c_packed}, diff={abs(c_bipolar - c_packed)}"
        )


@pytest.mark.parametrize("D", [32, 64, 96, 128, 1024, 10240])
def test_cosine_equivalence_per_dim(D):
    """Cosine equivalence holds at each tested D, not just the default."""
    rng = np.random.default_rng(D * 7)
    for _ in range(5):
        a = random_bipolar(D, rng)
        b = random_bipolar(D, rng)
        a_p = pack_bipolar(a)
        b_p = pack_bipolar(b)
        diff = abs(cosine_bipolar(a, b) - cosine_packed(a_p, b_p, D))
        assert diff < 1e-9, f"D={D}: diff={diff}"


# ---------- trivial sanity cases ----------


def test_self_cosine_is_plus_one():
    """cos(a, a) = 1.0 exactly."""
    rng = np.random.default_rng(0)
    D = 10240
    a = random_bipolar(D, rng)
    a_p = pack_bipolar(a)
    assert cosine_packed(a_p, a_p, D) == 1.0


def test_antipodal_cosine_is_minus_one():
    """cos(a, -a) = -1.0 exactly."""
    rng = np.random.default_rng(0)
    D = 10240
    a = random_bipolar(D, rng)
    a_p = pack_bipolar(a)
    neg_a = (-a).astype(np.int8)
    neg_a_p = pack_bipolar(neg_a)
    assert cosine_packed(a_p, neg_a_p, D) == -1.0


def test_all_plus_one_round_trip():
    """All-ones bipolar → packed-all-ones → unpack-all-ones."""
    D = 64
    hv = np.ones(D, dtype=np.int8)
    packed = pack_bipolar(hv)
    # 64 bits all 1 = two uint32 words both = 0xFFFFFFFF
    assert packed[0] == 0xFFFFFFFF
    assert packed[1] == 0xFFFFFFFF
    assert cosine_packed(packed, packed, D) == 1.0
    unpacked = unpack_bipolar(packed, D)
    assert np.array_equal(hv, unpacked)


def test_all_minus_one_round_trip():
    """All-minus-one bipolar → packed-all-zeros → unpack-all-minus-ones."""
    D = 64
    hv = -np.ones(D, dtype=np.int8)
    packed = pack_bipolar(hv)
    assert packed[0] == 0
    assert packed[1] == 0
    assert cosine_packed(packed, packed, D) == 1.0
    unpacked = unpack_bipolar(packed, D)
    assert np.array_equal(hv, unpacked)


# ---------- error / edge cases ----------


def test_D_not_divisible_by_32_raises_on_pack():
    """D=10000 (the legacy default) must raise — encoder must bump to D=10240."""
    rng = np.random.default_rng(0)
    hv = random_bipolar(10000, rng)
    with pytest.raises(ValueError, match=r"D % 32 == 0"):
        pack_bipolar(hv)


def test_pack_rejects_2d_input():
    """pack_bipolar is single-vector; batched callers should iterate or use encode_packed."""
    arr = np.ones((4, 32), dtype=np.int8)
    with pytest.raises(ValueError, match=r"1-D input"):
        pack_bipolar(arr)


def test_unpack_rejects_wrong_dtype():
    """unpack must receive uint32; defensive against shape-only debugging."""
    arr = np.zeros(10, dtype=np.uint8)
    with pytest.raises(ValueError, match=r"uint32 input"):
        unpack_bipolar(arr, D=320)


def test_unpack_rejects_inconsistent_D():
    """If packed shape doesn't match D/32, raise — catches the user passing
    the wrong D after a copy/concatenate operation."""
    rng = np.random.default_rng(0)
    a = random_bipolar(64, rng)
    a_p = pack_bipolar(a)
    assert a_p.shape == (2,)
    with pytest.raises(ValueError, match=r"shape mismatch"):
        unpack_bipolar(a_p, D=128)  # D=128 expects (4,) packed, not (2,)


def test_cosine_shape_mismatch_raises():
    """Different-D packed vectors must fail loudly, not return garbage."""
    rng = np.random.default_rng(0)
    a_p = pack_bipolar(random_bipolar(64, rng))
    b_p = pack_bipolar(random_bipolar(128, rng))
    with pytest.raises(ValueError, match=r"shape mismatch"):
        cosine_packed(a_p, b_p, D=64)


def test_cosine_D_inconsistent_with_packed_shape():
    """D=128 with (2,)-shaped packed (D=64) is internally inconsistent."""
    rng = np.random.default_rng(0)
    a_p = pack_bipolar(random_bipolar(64, rng))
    b_p = pack_bipolar(random_bipolar(64, rng))
    with pytest.raises(ValueError, match=r"inconsistent"):
        cosine_packed(a_p, b_p, D=128)


def test_cosine_wrong_dtype():
    """Non-uint32 inputs to cosine_packed raise — float32 sneak-in would
    silently produce wrong XOR results otherwise."""
    a = np.zeros(10, dtype=np.uint8)
    b = np.zeros(10, dtype=np.uint8)
    with pytest.raises(ValueError, match=r"uint32"):
        cosine_packed(a, b, D=80)
