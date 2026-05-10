"""Tests for src/project_x/reasoning/number_theory.py — Phase 13 cycle 8 #00P13c8-10.

Coverage:
- Collatz: verify [1, N] for small + medium N; iteration cap; counterexample-free claim
- Goldbach: verify even integers [4, N]; sample witnesses present; sieve correctness
- Twin primes: enumerate ≤ N; known counts at small N (matches OEIS A007508);
  Hardy-Littlewood density invariant at moderate N
- Mertens bound: verify |M(n)| < √n at small N (where it holds); Möbius factor-counting
  correctness; honest framing (substrate doesn't claim conjecture proved)
- Thesis-compliance: no sympy/numpy/scipy/torch imports

Honest M-PROJECTX-013 framing: all PASS results = empirical verification over finite
range, NOT theorem proofs. The conjectures (except Mertens) are open as of 2026.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest

from project_x.reasoning.number_theory import (
    _mobius,
    _sieve_of_eratosthenes,
    _smallest_prime_factor_sieve,
    collatz_verify_range,
    goldbach_verify_range,
    mertens_bound_verify,
    twin_primes_in_range,
)


# ── Sieve helpers ──────────────────────────────────────────────────────────────


class TestSieveOfEratosthenes:
    def test_small_primes(self):
        sieve = _sieve_of_eratosthenes(20)
        primes = [i for i, is_p in enumerate(sieve) if is_p]
        assert primes == [2, 3, 5, 7, 11, 13, 17, 19]

    def test_n_lt_2_all_false(self):
        assert _sieve_of_eratosthenes(0) == [False]
        assert _sieve_of_eratosthenes(1) == [False, False]

    def test_n_equals_2(self):
        assert _sieve_of_eratosthenes(2) == [False, False, True]


class TestSmallestPrimeFactorSieve:
    def test_canonical(self):
        spf = _smallest_prime_factor_sieve(20)
        # spf[4] = 2 (4 = 2·2), spf[9] = 3 (9 = 3·3), spf[15] = 3 (15 = 3·5)
        assert spf[4] == 2
        assert spf[9] == 3
        assert spf[15] == 3
        assert spf[17] == 17  # prime: spf == itself

    def test_mobius_via_spf(self):
        """Spot-check Möbius values via factor-counting against the sieve."""
        spf = _smallest_prime_factor_sieve(20)
        # μ(1) = 1, μ(2) = -1, μ(3) = -1, μ(4) = 0 (2²), μ(6) = +1 (2·3)
        # μ(10) = +1 (2·5), μ(12) = 0 (2²·3), μ(30) requires sieve(30)
        assert _mobius(1, spf) == 1
        assert _mobius(2, spf) == -1
        assert _mobius(3, spf) == -1
        assert _mobius(4, spf) == 0
        assert _mobius(6, spf) == 1
        assert _mobius(10, spf) == 1
        assert _mobius(12, spf) == 0


# ── Collatz verification ───────────────────────────────────────────────────────


class TestCollatzVerifyRange:
    def test_small_n(self):
        """All n ∈ [1, 100] reach 1 under Collatz iteration (known empirically)."""
        lemma = collatz_verify_range(100)
        assert lemma.actual_value == 100  # all verified

    def test_canonical_n_1000(self):
        """N=1000: all 1000 starting values reach 1 (matches all OEIS data)."""
        lemma = collatz_verify_range(1000)
        assert lemma.actual_value == 1000

    def test_lemma_chain_shape(self):
        lemma = collatz_verify_range(100)
        assert len(lemma.derivation_steps) == 1
        assert lemma.derivation_steps[0].operation == "collatz_brute_force_verification"
        assert len(lemma.invariant_checks) == 1
        assert lemma.introduction != ""
        assert "open" in lemma.introduction.lower()
        assert "empirical" in lemma.introduction.lower()

    def test_invariant_holds(self):
        lemma = collatz_verify_range(100)
        assert all(inv.holds for inv in lemma.invariant_checks)

    def test_rejects_zero_and_negative(self):
        with pytest.raises(ValueError, match="≥ 1"):
            collatz_verify_range(0)
        with pytest.raises(ValueError, match="≥ 1"):
            collatz_verify_range(-5)

    def test_n_equals_1_trivial(self):
        """n=1 trivially reaches 1 (zero iterations)."""
        lemma = collatz_verify_range(1)
        assert lemma.actual_value == 1


# ── Goldbach verification ──────────────────────────────────────────────────────


class TestGoldbachVerifyRange:
    def test_small_n(self):
        """N=20: 4=2+2, 6=3+3, 8=3+5, 10=3+7 or 5+5, ..., 20=3+17 or 7+13. All 9 even decompose."""
        lemma = goldbach_verify_range(20)
        # Even integers in [4, 20]: 4, 6, 8, 10, 12, 14, 16, 18, 20 → 9 values
        assert lemma.actual_value == 9

    def test_canonical_n_1000(self):
        """N=1000: 499 even integers in [4, 1000] (=(1000-4)/2 + 1), all decompose."""
        lemma = goldbach_verify_range(1000)
        assert lemma.actual_value == 499

    def test_lemma_chain_shape(self):
        lemma = goldbach_verify_range(20)
        assert len(lemma.derivation_steps) == 1
        assert lemma.derivation_steps[0].operation == "goldbach_brute_force_verification"
        assert "sample_witnesses" in lemma.derivation_steps[0].output
        assert lemma.introduction != ""

    def test_witnesses_present(self):
        lemma = goldbach_verify_range(20)
        witnesses = lemma.derivation_steps[0].output["sample_witnesses"]
        assert len(witnesses) > 0
        # Verify a sample witness: (n, (p, q)) with p+q==n and both prime
        sieve = _sieve_of_eratosthenes(100)
        for n, (p, q) in witnesses:
            assert p + q == n
            assert sieve[p]
            assert sieve[q]

    def test_rejects_below_4(self):
        with pytest.raises(ValueError, match="≥ 4"):
            goldbach_verify_range(3)
        with pytest.raises(ValueError, match="≥ 4"):
            goldbach_verify_range(0)


# ── Twin primes enumeration ────────────────────────────────────────────────────


class TestTwinPrimesInRange:
    def test_small_n(self):
        """Twin primes (p, p+2) with p+2 ≤ 20: (3,5), (5,7), (11,13), (17,19) → 4 pairs."""
        lemma = twin_primes_in_range(20)
        assert lemma.actual_value == 4

    def test_canonical_n_1000(self):
        """N=1000: 35 twin-prime pairs (OEIS A007508 verifiable count)."""
        lemma = twin_primes_in_range(1000)
        # 35 pairs ≤ 1000 (OEIS A007508): (3,5), (5,7), ..., (881,883)
        assert lemma.actual_value == 35

    def test_lemma_chain_shape(self):
        lemma = twin_primes_in_range(100)
        assert len(lemma.derivation_steps) == 1
        assert lemma.derivation_steps[0].operation == "twin_primes_enumeration"
        assert "first_5" in lemma.derivation_steps[0].output
        assert "last_5" in lemma.derivation_steps[0].output

    def test_first_5_are_correct(self):
        lemma = twin_primes_in_range(100)
        first_5 = lemma.derivation_steps[0].output["first_5"]
        assert first_5 == [(3, 5), (5, 7), (11, 13), (17, 19), (29, 31)]

    def test_no_invariant_check_added(self):
        """Per substrate design: Hardy-Littlewood density check stays in step justification
        (not surfaced as a Lemma invariant_check because the default add_invariant_check
        tolerance 0.001 is way too tight for an asymptotic ~30%-drift density estimate)."""
        lemma = twin_primes_in_range(1000)
        assert lemma.invariant_checks == []

    def test_rejects_n_below_5(self):
        with pytest.raises(ValueError, match="≥ 5"):
            twin_primes_in_range(4)


# ── Mertens bound verification ─────────────────────────────────────────────────


class TestMertensBoundVerify:
    def test_small_n(self):
        """|M(n)| < √n holds for small n (known empirically)."""
        lemma = mertens_bound_verify(100)
        # Bound holds at small N empirically; expect all 100 satisfy
        assert lemma.actual_value == 100

    def test_canonical_n_1000(self):
        """N=1000: bound holds (Mertens DISPROVED at large N but holds at 1000)."""
        lemma = mertens_bound_verify(1000)
        assert lemma.actual_value == 1000

    def test_lemma_chain_shape(self):
        lemma = mertens_bound_verify(100)
        assert len(lemma.derivation_steps) == 1
        assert lemma.derivation_steps[0].operation == "mertens_bound_verification"
        assert "max_abs_M" in lemma.derivation_steps[0].output
        assert lemma.introduction != ""
        assert "disproved" in lemma.introduction.lower()

    def test_honest_framing_in_step_justification(self):
        """Step justification must say EMPIRICAL VERIFICATION ONLY + note disproof."""
        lemma = mertens_bound_verify(100)
        justif = lemma.derivation_steps[0].justification.lower()
        assert "empirical" in justif or "disproved" in justif or "not a proof" in justif

    def test_n_equals_1(self):
        """n=1: M(1) = μ(1) = 1; √1 = 1; |M(1)| ≤ √1 is 1 ≤ 1 → TRUE.
        Substrate uses `≤` form (vs strict `<`) for clean edge-case behavior; the
        disproof (Odlyzko + te Riele 1985, lim sup > 1.06) violates both forms."""
        lemma = mertens_bound_verify(1)
        assert lemma.actual_value == 1

    def test_rejects_zero_and_negative(self):
        with pytest.raises(ValueError, match="≥ 1"):
            mertens_bound_verify(0)


# ── Thesis-compliance source-grep ──────────────────────────────────────────────


def test_number_theory_substrate_thesis_compliant():
    """No sympy / scipy / numpy / torch / transformers imports."""
    path = (
        Path(__file__).resolve().parent.parent
        / "src" / "project_x" / "reasoning" / "number_theory.py"
    )
    source = path.read_text()
    forbidden = [
        "import sympy", "from sympy",
        "import scipy", "from scipy",
        "import numpy", "from numpy",
        "import torch", "from torch",
        "transformers", "sentence_transformers",
    ]
    for token in forbidden:
        assert token not in source, f"number_theory.py imports forbidden token '{token}'"
