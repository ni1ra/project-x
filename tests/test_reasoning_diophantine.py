"""Tests for src/project_x/reasoning/diophantine.py — Phase 13 cycle 9 #00P13c9-03.

Coverage:
- x² + y² = N (Fermat two-squares form; a=1, b=0, c=1): N=5 → 8 sols; N=13 → 8 sols
  (prime ≡ 1 mod 4 witness); N=25 → 12 sols (composite; (±5,0),(0,±5),(±3,±4),(±4,±3))
- Generic positive-definite with cross term: x² + xy + y² = 3 (Eisenstein form; Δ=-3)
- Generic positive-definite asymmetric: 2x² + 3y² = 35 → 8 sols (sign perms of (2,3),(4,1))
- Trivial branches: N=0 yields (0,0) only; N<0 yields empty set
- Rejection of indefinite forms (Δ ≥ 0): Pell x² - 2y² = 1 → NotImplementedError
- Rejection of non-standard signs (a ≤ 0 or c ≤ 0): NotImplementedError
- Lemma shape: 4 derivation steps (identify_form → bound → enumerate → verify) on full
  branch; introduction prose populated; invariant checks fire correctly
- Symmetry invariant (form parity (x,y)→(-x,-y)) holds on every returned solution set
- Stronger D₄ invariant for a=c, b=0 forms: count divisible by 4
- Thesis-compliance: no sympy / numpy / scipy / torch imports in substrate

Lain mid-cycle directive 2026-05-11 ("harder problems") + cycle 9 #03 corpse:
this is the agent's first Diophantine-flavored capability beyond cycle 8's empirical
unsolved-theorem verifications. Bounded-enumeration substrate; honest M-PROJECTX-013
framing — NOT general Hilbert-10 decidability.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from project_x.reasoning.diophantine import (
    INTRO_BINARY_QUADRATIC_DIOPHANTINE,
    INTRO_PELL_EQUATION,
    _two_squares_via_jacobi,
    solve_binary_quadratic,
    solve_pell_equation,
)


def _solutions(lemma) -> list[tuple[int, int]]:
    """Pull the enumerated solution list out of the 3rd derivation step."""
    return sorted(lemma.derivation_steps[2].output["solutions"])


def test_x2_plus_y2_eq_5_eight_solutions() -> None:
    """Canonical small case: x²+y²=5 has 8 integer solutions (sign perms of (1,2),(2,1))."""
    lemma = solve_binary_quadratic(1, 0, 1, 5)
    assert lemma.actual_value == 8
    expected = sorted(
        [(s1 * 1, s2 * 2) for s1 in (-1, 1) for s2 in (-1, 1)]
        + [(s1 * 2, s2 * 1) for s1 in (-1, 1) for s2 in (-1, 1)],
    )
    assert _solutions(lemma) == expected


def test_x2_plus_y2_eq_25_twelve_solutions() -> None:
    """x²+y²=25 has 12 solutions: (±5,0),(0,±5),(±3,±4),(±4,±3)."""
    lemma = solve_binary_quadratic(1, 0, 1, 25)
    assert lemma.actual_value == 12
    sols = set(_solutions(lemma))
    # axis-aligned
    for s in (-5, 5):
        assert (s, 0) in sols
        assert (0, s) in sols
    # 3-4-5 Pythagorean triple sign-permutations
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            assert (s1 * 3, s2 * 4) in sols
            assert (s1 * 4, s2 * 3) in sols


def test_fermat_two_squares_p13_eight_solutions() -> None:
    """Fermat's theorem witness: prime 13 ≡ 1 (mod 4) ⇒ 13 = 2² + 3². 8 sign-perm solutions."""
    lemma = solve_binary_quadratic(1, 0, 1, 13)
    assert lemma.actual_value == 8
    sols = set(_solutions(lemma))
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            assert (s1 * 2, s2 * 3) in sols
            assert (s1 * 3, s2 * 2) in sols


def test_eisenstein_form_with_cross_term() -> None:
    """x²+xy+y²=3 (Eisenstein form, Δ=-3). 6 solutions: (±1,±1) with x+y≠0 + 2 swap-pairs."""
    lemma = solve_binary_quadratic(1, 1, 1, 3)
    assert lemma.actual_value == 6
    sols = set(_solutions(lemma))
    # Verify every emitted solution satisfies the equation.
    for x, y in sols:
        assert x * x + x * y + y * y == 3


def test_asymmetric_positive_definite() -> None:
    """2x²+3y²=35: 8 solutions (sign perms of (2,3) and (4,1))."""
    lemma = solve_binary_quadratic(2, 0, 3, 35)
    assert lemma.actual_value == 8
    sols = set(_solutions(lemma))
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            assert (s1 * 2, s2 * 3) in sols
            assert (s1 * 4, s2 * 1) in sols


def test_trivial_n_zero_single_origin_solution() -> None:
    """Positive-definite Q(x,y)=0 iff (x,y)=(0,0). Single solution."""
    lemma = solve_binary_quadratic(1, 0, 1, 0)
    assert lemma.actual_value == 1


def test_trivial_n_negative_no_solutions() -> None:
    """Positive-definite Q ≥ 0 everywhere; N<0 yields empty solution set."""
    lemma = solve_binary_quadratic(1, 0, 1, -7)
    assert lemma.actual_value == 0


def test_indefinite_form_pell_raises() -> None:
    """Pell-style x²-2y²=1 has Δ=8>0 (indefinite); cycle 9 substrate rejects with reason."""
    with pytest.raises(NotImplementedError, match="indefinite|Δ"):
        solve_binary_quadratic(1, 0, -2, 1)


def test_degenerate_discriminant_zero_raises() -> None:
    """Δ=0 form (e.g. (x+y)² = x²+2xy+y², a=1,b=2,c=1) is degenerate; reject."""
    with pytest.raises(NotImplementedError, match=r"Δ"):
        solve_binary_quadratic(1, 2, 1, 4)


def test_non_standard_sign_raises() -> None:
    """a ≤ 0 or c ≤ 0 outside standard positive-definite shape; reject."""
    with pytest.raises(NotImplementedError, match="a > 0 AND c > 0|positive-definite"):
        solve_binary_quadratic(-1, 0, 1, 5)


def test_lemma_introduction_populated() -> None:
    """Introduction prose explaining discriminant + Lagrange bound must be set."""
    lemma = solve_binary_quadratic(1, 0, 1, 5)
    assert lemma.introduction == INTRO_BINARY_QUADRATIC_DIOPHANTINE
    assert "discriminant" in lemma.introduction.lower()
    assert "Hilbert" in lemma.introduction or "Matiyasevich" in lemma.introduction


def test_lemma_step_chain_shape() -> None:
    """Non-trivial branch produces 4 derivation steps: identify_form → bound → enumerate → verify."""
    lemma = solve_binary_quadratic(1, 0, 1, 25)
    assert [s.operation for s in lemma.derivation_steps] == [
        "identify_form",
        "compute_search_bound",
        "brute_force_enumerate",
        "verify_solutions",
    ]


def test_symmetric_form_dihedral_invariant_holds() -> None:
    """For a=c, b=0 forms, both the D₄ invariant (count divisible by 4) and the
    cycle 10 #01a Jacobi STRONG invariant must fire and hold. Three invariants
    in total: form parity + D₄ + Jacobi (the a=c=1, b=0 case is symmetric AND
    canonical sum-of-two-squares, so Jacobi applies)."""
    lemma = solve_binary_quadratic(1, 0, 1, 25)
    assert len(lemma.invariant_checks) == 3
    assert all(inv.holds for inv in lemma.invariant_checks)


def test_form_parity_invariant_only_for_asymmetric() -> None:
    """For a≠c or b≠0 forms, only the form-parity invariant fires (no D₄)."""
    lemma = solve_binary_quadratic(2, 0, 3, 35)
    # Asymmetric: a=2, c=3 — D₄ check should NOT fire.
    assert len(lemma.invariant_checks) == 1
    assert lemma.invariant_checks[0].predicate.startswith("solution set is closed under")
    assert lemma.invariant_checks[0].holds


def test_render_output_includes_diophantine_keyword() -> None:
    """Lemma.render() should surface the discriminant + solution-count in the proof shape."""
    lemma = solve_binary_quadratic(1, 0, 1, 13)
    rendered = lemma.render()
    assert "13" in rendered
    assert "8" in rendered  # solution count
    assert "Δ" in rendered or "discriminant" in rendered.lower()


def test_thesis_compliance_no_pretrained_imports() -> None:
    """Diophantine substrate must NOT import sympy / numpy / scipy / torch / transformers."""
    src = Path("src/project_x/reasoning/diophantine.py").read_text()
    forbidden = ["sympy", "numpy", "scipy", "torch", "transformers", "tensorflow"]
    for f in forbidden:
        assert f not in src, f"forbidden import '{f}' found in diophantine.py"


# --- Cycle 10 #01a — Jacobi STRONG verifier (algorithmically-independent) ---


def test_jacobi_two_squares_canonical_counts() -> None:
    """r₂(N) = 4·(d₁(N) - d₃(N)) on canonical cases. Verified by hand:
    N=0 → 1 trivial; N=1 → 4 ((±1,0),(0,±1)); N=2 → 4 ((±1,±1)); N=3 → 0 (3≡3 mod 4
    and not expressible); N=5 → 8; N=13 → 8 (Fermat); N=25 → 12 (3-4-5 perms); N=65 → 16."""
    cases = {0: 1, 1: 4, 2: 4, 3: 0, 4: 4, 5: 8, 8: 4, 9: 4, 13: 8, 25: 12, 50: 12, 65: 16}
    for N, expected in cases.items():
        assert _two_squares_via_jacobi(N) == expected, (
            f"_two_squares_via_jacobi({N}) returned "
            f"{_two_squares_via_jacobi(N)}, expected {expected}"
        )


def test_jacobi_handles_negative_target() -> None:
    """N < 0 has no two-squares representations; Jacobi returns 0 honestly."""
    assert _two_squares_via_jacobi(-1) == 0
    assert _two_squares_via_jacobi(-13) == 0


def test_jacobi_invariant_fires_and_holds_on_symmetric_form() -> None:
    """For symmetric forms (a=c=1, b=0), Jacobi STRONG invariant must fire + hold.
    This is the cycle 10 #01a load-bearing predicate-strength upgrade."""
    for N in (5, 13, 25, 50, 65):
        lemma = solve_binary_quadratic(1, 0, 1, N)
        jacobi_invariants = [
            inv for inv in lemma.invariant_checks
            if "Jacobi" in inv.predicate
        ]
        assert len(jacobi_invariants) == 1, (
            f"x²+y²={N}: expected exactly 1 Jacobi invariant, "
            f"got {len(jacobi_invariants)}"
        )
        assert jacobi_invariants[0].holds, (
            f"x²+y²={N}: Jacobi invariant did not hold "
            f"(expected {jacobi_invariants[0].expected_value}, "
            f"actual {jacobi_invariants[0].actual_value})"
        )


def test_jacobi_invariant_skipped_on_asymmetric_form() -> None:
    """For asymmetric forms (a ≠ c), Jacobi has no clean generalization; the
    invariant must NOT fire. 2x² + 3y² = 35 keeps only the form-parity check."""
    lemma = solve_binary_quadratic(2, 0, 3, 35)
    jacobi_invariants = [
        inv for inv in lemma.invariant_checks
        if "Jacobi" in inv.predicate
    ]
    assert jacobi_invariants == [], (
        "Jacobi invariant fired on asymmetric form 2x²+3y²=35 — "
        "should be skipped per scope-boundary documentation"
    )


def test_jacobi_invariant_skipped_on_cross_term_form() -> None:
    """For cross-term forms (b ≠ 0), Jacobi has no clean generalization; the
    invariant must NOT fire. x² + xy + y² = 3 keeps only the form-parity check."""
    lemma = solve_binary_quadratic(1, 1, 1, 3)
    jacobi_invariants = [
        inv for inv in lemma.invariant_checks
        if "Jacobi" in inv.predicate
    ]
    assert jacobi_invariants == [], (
        "Jacobi invariant fired on cross-term form x²+xy+y²=3 — "
        "should be skipped per scope-boundary documentation"
    )


def test_jacobi_independent_path_documentation_present() -> None:
    """The substrate file must carry the predicate-strength scope-boundary note
    explicitly so future audits don't try to retrofit Jacobi-style verifiers
    onto asymmetric or cross-term forms (where no closed-form exists)."""
    src = Path("src/project_x/reasoning/diophantine.py").read_text()
    assert "Predicate-strength note" in src
    assert "Jacobi" in src
    assert "Gauss reduction" in src or "Brandt-Eichler" in src or "theta-series" in src
    assert "no closed-form" in src or "no clean generalization" in src.lower() or (
        "no closed-form r" in src and "exists" in src
    )


# --- Cycle 10 #02 — Pell equation substrate ---


def test_continued_fraction_sqrt_canonical():
    """CF of √n on canonical Hardy+Wright examples."""
    from project_x.reasoning.diophantine import _continued_fraction_sqrt
    cases = {
        2: (1, [2]),
        3: (1, [1, 2]),
        5: (2, [4]),
        7: (2, [1, 1, 1, 4]),
        13: (3, [1, 1, 1, 1, 6]),
    }
    for n, (expected_a0, expected_period) in cases.items():
        a0, period = _continued_fraction_sqrt(n)
        assert a0 == expected_a0, f"n={n}: a0 mismatch {a0} vs {expected_a0}"
        assert period == expected_period, f"n={n}: period mismatch {period} vs {expected_period}"


def test_continued_fraction_sqrt_rejects_invalid_n():
    """n ≤ 1 and perfect-square n must be rejected with ValueError."""
    from project_x.reasoning.diophantine import _continued_fraction_sqrt
    for n in (-5, -1, 0, 1):
        with pytest.raises(ValueError, match="n ≥ 2"):
            _continued_fraction_sqrt(n)
    for n in (4, 9, 16, 25, 100):
        with pytest.raises(ValueError, match="perfect square"):
            _continued_fraction_sqrt(n)


def test_pell_fundamental_solution_canonical():
    """Fundamental (x₁, y₁) for canonical small-n Pell equations."""
    from project_x.reasoning.diophantine import _pell_fundamental_solution
    cases = {
        2: (3, 2),       # period odd → squared from (1, 1)
        3: (2, 1),       # period even → direct convergent
        5: (9, 4),       # period odd → squared from (2, 1)
        7: (8, 3),       # period 4-even
        13: (649, 180),  # period 5-odd → squared; famous Hardy+Wright case
        61: (1766319049, 226153980),  # extreme period-odd case
    }
    for n, (expected_x, expected_y) in cases.items():
        x1, y1 = _pell_fundamental_solution(n)
        assert (x1, y1) == (expected_x, expected_y), (
            f"n={n}: fundamental mismatch ({x1}, {y1}) vs ({expected_x}, {expected_y})"
        )
        # Integer verification
        assert x1 * x1 - n * y1 * y1 == 1


def test_pell_brute_force_fundamental_matches_cf():
    """Brute-force search over small-n produces the same fundamental as CF."""
    from project_x.reasoning.diophantine import (
        _pell_brute_force_fundamental, _pell_fundamental_solution,
    )
    for n in (2, 3, 5, 7, 11, 13):
        bf = _pell_brute_force_fundamental(n, max_x=1000)
        cf = _pell_fundamental_solution(n)
        assert bf == cf, f"n={n}: brute force {bf} vs CF {cf}"


def test_solve_pell_equation_n_eq_2_first_5():
    """Pell n=2: first 5 solutions match the classical sequence."""
    lemma = solve_pell_equation(2, k_max=5)
    assert lemma.actual_value == 5
    expected = [(3, 2), (17, 12), (99, 70), (577, 408), (3363, 2378)]
    assert lemma.derivation_steps[3].output["solutions"] == expected


def test_solve_pell_equation_n_eq_3_first_5():
    """Pell n=3: first 5 solutions (period-even-direct case)."""
    lemma = solve_pell_equation(3, k_max=5)
    expected = [(2, 1), (7, 4), (26, 15), (97, 56), (362, 209)]
    assert lemma.derivation_steps[3].output["solutions"] == expected


def test_solve_pell_equation_invariants_hold():
    """Both invariants (recurrence consistency + brute-force STRONG) hold for small n."""
    for n in (2, 3, 5, 7):
        lemma = solve_pell_equation(n, k_max=5)
        assert len(lemma.invariant_checks) == 2
        assert all(inv.holds for inv in lemma.invariant_checks)


def test_solve_pell_equation_skips_brute_force_for_large_fundamental():
    """For n where fundamental.x > 1000 (e.g. n=13 → x₁=649 still under cap; n=61 → 1.7e9
    way over), the brute-force verifier honestly skips with documented scope-boundary
    rather than running a multi-billion-iteration loop."""
    lemma = solve_pell_equation(61, k_max=3)
    # Find the second invariant (brute-force one)
    bf_inv = [i for i in lemma.invariant_checks if "brute-force" in i.predicate.lower()][0]
    assert "SKIPPED" in bf_inv.predicate
    assert bf_inv.expected_value == "skipped"
    assert bf_inv.actual_value == "skipped"
    # And the tautological invariant still holds
    taut_inv = [i for i in lemma.invariant_checks if "recurrence consistency" in i.predicate][0]
    assert taut_inv.holds


def test_solve_pell_equation_rejects_invalid_n():
    """Pell substrate rejects n ≤ 1 and perfect-square n at the helper layer."""
    for n in (-1, 0, 1):
        with pytest.raises(ValueError, match="n ≥ 2"):
            solve_pell_equation(n, k_max=5)
    for n in (4, 9, 25):
        with pytest.raises(ValueError, match="perfect square"):
            solve_pell_equation(n, k_max=5)


def test_solve_pell_equation_rejects_invalid_k_max():
    """k_max < 1 is degenerate (zero solutions requested)."""
    with pytest.raises(ValueError, match="k_max must be ≥ 1"):
        solve_pell_equation(2, k_max=0)
    with pytest.raises(ValueError, match="k_max must be ≥ 1"):
        solve_pell_equation(2, k_max=-3)


def test_pell_lemma_chain_shape():
    """4-step derivation chain: validate → CF → fundamental → recurrence."""
    lemma = solve_pell_equation(2, k_max=3)
    operations = [step.operation for step in lemma.derivation_steps]
    assert operations == [
        "validate_input",
        "compute_continued_fraction",
        "compute_fundamental_solution",
        "apply_recurrence",
    ]


def test_pell_introduction_carries_honest_framing():
    """INTRO_PELL_EQUATION mentions infinite solution set + Lagrange + recurrence."""
    from project_x.reasoning.diophantine import INTRO_PELL_EQUATION
    assert "infinite" in INTRO_PELL_EQUATION.lower()
    assert "Lagrange" in INTRO_PELL_EQUATION or "lagrange" in INTRO_PELL_EQUATION.lower()
    assert "recurrence" in INTRO_PELL_EQUATION.lower()
    assert "k_max" in INTRO_PELL_EQUATION or "first" in INTRO_PELL_EQUATION
