"""Tests for src/project_x/reasoning/complex_analysis.py — Phase 13 #00P13c8-01.

Coverage:
- Canonical case: ∫ dx/(x²+1) = π (closes maths-003 substrate gap)
- General unit-quadratic: ∫ dx/(a·x²+c) = π/√(a·c)
- Invariant check: dimensionless integral·√(a·c)/π = 1
- Boundary cases: a <= 0 or c <= 0 raises (integral diverges)
- Lemma render structure: intro + 3 derivation steps + invariant
- Thesis-compliance: no scipy/sympy imports

Cycle 8 minimum-viable scope; cycle 8+ extends to higher-degree denominators + numerators.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from project_x.reasoning.complex_analysis import residue_theorem_unit_quadratic


def test_residue_unit_quadratic_canonical_maths_003():
    """maths-003 form: ∫ dx/(x²+1) = π (a=1, c=1)."""
    lemma = residue_theorem_unit_quadratic(1.0, 1.0)
    assert abs(lemma.actual_value - math.pi) < 1e-12


def test_residue_unit_quadratic_scaled_denominator():
    """∫ dx/(x²+4) = π/2 (a=1, c=4; √(a·c)=2)."""
    lemma = residue_theorem_unit_quadratic(1.0, 4.0)
    assert abs(lemma.actual_value - math.pi / 2) < 1e-12


def test_residue_unit_quadratic_scaled_leading():
    """∫ dx/(2·x²+8) = π/4 (a=2, c=8; √(a·c)=4)."""
    lemma = residue_theorem_unit_quadratic(2.0, 8.0)
    assert abs(lemma.actual_value - math.pi / 4) < 1e-12


def test_residue_unit_quadratic_invariant_holds():
    """Dimensionless integral · √(a·c) / π = 1 universally."""
    for a, c in [(1.0, 1.0), (1.0, 4.0), (2.0, 8.0), (0.5, 2.0), (3.0, 12.0)]:
        lemma = residue_theorem_unit_quadratic(a, c)
        assert all(inv.holds for inv in lemma.invariant_checks), (
            f"invariant check failed for (a={a}, c={c})"
        )


def test_residue_unit_quadratic_lemma_chain_shape():
    """Lemma has 3 derivation steps (locate_poles + compute_residue + closing)."""
    lemma = residue_theorem_unit_quadratic(1.0, 1.0)
    assert len(lemma.derivation_steps) == 3
    assert lemma.derivation_steps[0].operation == "locate_poles"
    assert lemma.derivation_steps[1].operation == "compute_residue"
    assert lemma.derivation_steps[2].operation == "residue_theorem_closing"


def test_residue_unit_quadratic_render_includes_intro_and_invariant():
    """Render mirrors physics/maths substrate shape — intro + steps + invariant block."""
    lemma = residue_theorem_unit_quadratic(1.0, 1.0)
    rendered = lemma.render()
    assert "residue theorem" in rendered.lower()
    assert "upper half plane" in rendered.lower() or "upper-half-plane" in rendered.lower()
    assert "Invariant checks:" in rendered


def test_residue_unit_quadratic_rejects_non_positive_a():
    """a <= 0 puts pole on real line; integral diverges (out of scope)."""
    with pytest.raises(ValueError, match="positive"):
        residue_theorem_unit_quadratic(0, 1.0)
    with pytest.raises(ValueError, match="positive"):
        residue_theorem_unit_quadratic(-1.0, 1.0)


def test_residue_unit_quadratic_rejects_non_positive_c():
    """c <= 0 same problem (real roots on integration path)."""
    with pytest.raises(ValueError, match="positive"):
        residue_theorem_unit_quadratic(1.0, 0)
    with pytest.raises(ValueError, match="positive"):
        residue_theorem_unit_quadratic(1.0, -1.0)


def test_complex_analysis_substrate_thesis_compliant():
    """No scipy/sympy/numpy/torch imports in complex_analysis.py."""
    path = Path(__file__).resolve().parent.parent / "src" / "project_x" / "reasoning" / "complex_analysis.py"
    source = path.read_text()
    forbidden = [
        "import sympy", "from sympy",
        "import scipy", "from scipy",
        "import numpy", "from numpy",
        "import torch", "from torch",
        "transformers", "sentence_transformers",
    ]
    for token in forbidden:
        assert token not in source, f"complex_analysis.py imports forbidden token '{token}'"
