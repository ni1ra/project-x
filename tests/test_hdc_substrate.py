"""Tests for HDC primitives — hdc_substrate.py (audit-E1 coverage lift).

Pre-fix: 24% coverage (only `bind` + `superpose` exercised transitively via
semantic_hdc_memory imports). Post-fix: targets 70%+ by exercising every
primitive directly (bind/unbind round-trip, superpose with cleanup, write/read
single + multi-item, cleanup snap-to-nearest, bit_accuracy + shape-mismatch
error path, random_vector with default + explicit rng) plus the 4 in-module
unit tests via run_self_test.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout

import numpy as np
import pytest

from project_x.experiments.hdc_substrate import (
    D_DEFAULT,
    bind,
    bit_accuracy,
    cleanup,
    random_vector,
    read,
    run_self_test,
    superpose,
    unbind,
    write,
    # In-module unit tests — aliased so pytest doesn't auto-collect them as
    # test cases (their names start with `test_` but require `(rng, d)` args
    # that pytest can't supply, so direct re-import would error on collection).
    test_bind_self_inverse as _hdc_unit_bind_self_inverse,
    test_random_baseline_below_passline as _hdc_unit_random_baseline,
    test_superpose_capacity_2_items as _hdc_unit_superpose_capacity_2,
    test_write_read_single_item as _hdc_unit_write_read_single,
)


# =============================================================================
# random_vector
# =============================================================================

def test_random_vector_default_rng_shape_dtype():
    """random_vector with rng=None constructs its own default_rng."""
    v = random_vector(d=512)
    assert v.shape == (512,)
    assert v.dtype == np.int8
    assert set(np.unique(v).tolist()).issubset({-1, 1})


def test_random_vector_explicit_rng_deterministic():
    """Same explicit rng seed → identical output."""
    rng1 = np.random.default_rng(1337)
    rng2 = np.random.default_rng(1337)
    v1 = random_vector(d=256, rng=rng1)
    v2 = random_vector(d=256, rng=rng2)
    assert np.array_equal(v1, v2)


# =============================================================================
# bind / unbind
# =============================================================================

def test_bind_self_inverse_property():
    """bind(bind(a, b), b) == a in bipolar HDC (audit-E1: round-trip)."""
    rng = np.random.default_rng(1337)
    a = random_vector(512, rng)
    b = random_vector(512, rng)
    recovered = bind(bind(a, b), b)
    assert np.array_equal(a, recovered)


def test_unbind_is_bind_in_bipolar_hdc():
    """In bipolar HDC unbind == bind (both use elementwise multiply)."""
    rng = np.random.default_rng(1337)
    a = random_vector(512, rng)
    b = random_vector(512, rng)
    bound = bind(a, b)
    via_unbind = unbind(bound, b)
    via_bind = bind(bound, b)
    assert np.array_equal(via_unbind, via_bind)
    assert np.array_equal(via_unbind, a)


def test_bind_output_is_bipolar():
    """bind result must be int8 with values in {-1, +1}."""
    rng = np.random.default_rng(1337)
    a = random_vector(256, rng)
    b = random_vector(256, rng)
    out = bind(a, b)
    assert out.dtype == np.int8
    assert set(np.unique(out).tolist()).issubset({-1, 1})


# =============================================================================
# superpose
# =============================================================================

def test_superpose_recovers_via_cleanup():
    """superpose(a, b) cleanup against {a, b} returns one of them exactly."""
    rng = np.random.default_rng(1337)
    a = random_vector(2048, rng)
    b = random_vector(2048, rng)
    s = superpose(a, b)
    atoms = np.stack([a, b])
    snapped, idx, sim = cleanup(s, atoms)
    assert idx in (0, 1)
    # Snapped vector must EXACTLY match either a or b at high D.
    assert np.array_equal(snapped, atoms[idx])
    assert sim > 0.0  # positive cosine alignment


def test_superpose_three_items_at_high_d():
    """3-item superpose still cleans up to the correct atom at D=4096."""
    rng = np.random.default_rng(1337)
    a = random_vector(4096, rng)
    b = random_vector(4096, rng)
    c = random_vector(4096, rng)
    s = superpose(a, b, c)
    atoms = np.stack([a, b, c])
    _, idx, _ = cleanup(s, atoms)
    assert idx in (0, 1, 2)


def test_superpose_empty_raises():
    """superpose() with no args must raise ValueError (not silently return junk)."""
    with pytest.raises(ValueError, match="at least one"):
        superpose()


def test_superpose_zero_tie_breaks_positive():
    """At a position where the sum is exactly 0, the convention is +1 — not 0."""
    a = np.array([1, -1, 1], dtype=np.int8)
    b = np.array([-1, 1, -1], dtype=np.int8)  # sum = [0, 0, 0] → all +1 by convention
    s = superpose(a, b)
    assert np.array_equal(s, np.array([1, 1, 1], dtype=np.int8))


# =============================================================================
# write / read
# =============================================================================

def test_write_read_single_item_exact():
    """write(None, k, v) then read(M, k) recovers v EXACTLY at N=1 (no noise)."""
    rng = np.random.default_rng(1337)
    k = random_vector(2048, rng)
    v = random_vector(2048, rng)
    M = write(None, k, v)
    recovered = read(M, k)
    assert np.array_equal(recovered, v)


def test_write_with_existing_memory_accumulates():
    """write(M, k2, v2) when M is non-None ADDS the new binding (not overwrites).
    Both keys still recover their values at N=2; empirical per-bit accuracy
    on this seed lands ~0.74 at D=4096 — well above the 0.50 random baseline,
    confirming the binding signal survives the second write rather than being
    overwritten. Threshold 0.65 absorbs seed variance.
    """
    rng = np.random.default_rng(1337)
    k1, v1 = random_vector(4096, rng), random_vector(4096, rng)
    k2, v2 = random_vector(4096, rng), random_vector(4096, rng)
    M = write(None, k1, v1)
    M = write(M, k2, v2)
    rec_v1 = read(M, k1)
    rec_v2 = read(M, k2)
    assert bit_accuracy(rec_v1, v1) > 0.65
    assert bit_accuracy(rec_v2, v2) > 0.65


def test_read_zero_position_breaks_positive():
    """At positions where memory * k_query == 0, the output convention is +1."""
    # Construct a memory such that one position is 0 and others are non-zero.
    M = np.array([0, 5, -3, 0, 7], dtype=np.int32)
    k = np.array([1, 1, 1, 1, 1], dtype=np.int8)
    out = read(M, k)
    # Positions 0 and 3: 0 → +1. Position 1: 5 → +1. Position 2: -3 → -1. Position 4: 7 → +1.
    expected = np.array([1, 1, -1, 1, 1], dtype=np.int8)
    assert np.array_equal(out, expected)


# =============================================================================
# cleanup
# =============================================================================

def test_cleanup_returns_index_and_similarity():
    """cleanup returns (snapped, idx, sim_normalized). Verify shape + types."""
    rng = np.random.default_rng(1337)
    target = random_vector(1024, rng)
    other = random_vector(1024, rng)
    atoms = np.stack([other, target])
    snapped, idx, sim = cleanup(target, atoms)
    assert idx == 1
    assert np.array_equal(snapped, target)
    # Similarity normalized to D — exact-self match → 1.0.
    assert sim == pytest.approx(1.0)


def test_cleanup_orthogonal_query_low_similarity():
    """Cleanup on a noise vector vs random atoms gives near-zero similarity."""
    rng = np.random.default_rng(1337)
    noise = random_vector(2048, rng)
    atoms = np.stack([random_vector(2048, rng) for _ in range(5)])
    _, idx, sim = cleanup(noise, atoms)
    assert 0 <= idx < 5
    assert abs(sim) < 0.10  # well below any meaningful match at D=2048


# =============================================================================
# bit_accuracy
# =============================================================================

def test_bit_accuracy_self_is_one():
    rng = np.random.default_rng(1337)
    v = random_vector(1024, rng)
    assert bit_accuracy(v, v) == 1.0


def test_bit_accuracy_random_pair_near_half():
    """Two unrelated bipolar vectors at D=4096 → bit accuracy near 0.5."""
    rng = np.random.default_rng(1337)
    a = random_vector(4096, rng)
    b = random_vector(4096, rng)
    acc = bit_accuracy(a, b)
    assert 0.45 < acc < 0.55


def test_bit_accuracy_shape_mismatch_raises():
    """Different-shape inputs must raise ValueError, not silently broadcast."""
    a = np.array([1, -1, 1], dtype=np.int8)
    b = np.array([1, -1], dtype=np.int8)
    with pytest.raises(ValueError, match="shape mismatch"):
        bit_accuracy(a, b)


# =============================================================================
# In-module self-test functions — direct invocation
# =============================================================================

def test_inmodule_test_bind_self_inverse_passes():
    rng = np.random.default_rng(1337)
    ok, info = _hdc_unit_bind_self_inverse(rng, d=2048)
    assert ok, info


def test_inmodule_test_superpose_capacity_2_items_passes():
    rng = np.random.default_rng(1337)
    ok, info = _hdc_unit_superpose_capacity_2(rng, d=2048)
    assert ok, info


def test_inmodule_test_write_read_single_item_passes():
    rng = np.random.default_rng(1337)
    ok, info = _hdc_unit_write_read_single(rng, d=2048)
    assert ok, info


def test_inmodule_test_random_baseline_below_passline_passes():
    rng = np.random.default_rng(1337)
    ok, info = _hdc_unit_random_baseline(rng, d=10000)
    assert ok, info


# =============================================================================
# run_self_test — full CLI driver
# =============================================================================

def test_run_self_test_returns_zero_when_all_pass():
    """run_self_test returns 0 when all 4 sub-tests pass; verbose=False to
    suppress stdout chatter on the test runner."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = run_self_test(seed=1337, d=2048, verbose=False)
    assert rc == 0
    # Output still shows the 4/4 green summary regardless of verbose flag.
    out = buf.getvalue()
    assert "4/4 green" in out


# =============================================================================
# Module-level constants
# =============================================================================

def test_d_default_constant():
    """D_DEFAULT is exported and equals 10000 per the module docstring."""
    assert D_DEFAULT == 10_000
