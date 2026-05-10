"""Project X Raphael reasoning substrate — cycle 2+ (Phase 13).

The AGENT's reasoning layer (Project X Raphael), distinct from Claude Code Raphael
(the BUILDER writing this code). The agent USES these primitives to construct
verifiable derivations; the builder writes the substrate but does not run inference
through it.

Cycle 2 shipped `symbolic.py` (Lemma + DerivationStep + solve_quadratic +
expand_characteristic_polynomial_2x2) and `verifier.py` (sandbox-bound numerical
verifier closing the loop through cycle 1 sandbox tools).

Cycle 8 added `complex_analysis.py` (#01 residue-theorem closed-form for unit-
quadratic real-line integrals), `calculus.py` (#02 FTC polynomial definite integral),
and `ode.py` (#03 first-order linear separable ODE closed-form).

Organic-thesis compliance: NO sympy (default-DENY), NO numpy in substrate-side code
(verifier may use numpy in sandbox-side script generation), NO pretrained transformer
derivatives anywhere. From-scratch primitives only.
"""

from project_x.reasoning.calculus import (
    INTRO_POLYNOMIAL_DEFINITE_INTEGRAL,
    polynomial_definite_integral,
)
from project_x.reasoning.complex_analysis import (
    INTRO_RESIDUE_UNIT_QUADRATIC,
    residue_theorem_unit_quadratic,
)
from project_x.reasoning.ode import (
    INTRO_FIRST_ORDER_LINEAR_ODE_EXP,
    first_order_linear_ode_exp_solution,
)
from project_x.reasoning.symbolic import (
    INTRO_CHAR_POLY_2X2,
    INTRO_DETERMINANT_3X3,
    INTRO_QUADRATIC,
    DerivationStep,
    InvariantCheck,
    Lemma,
    determinant_3x3,
    expand_characteristic_polynomial_2x2,
    solve_quadratic,
)
from project_x.reasoning.verifier import numerical_verify

__all__ = [
    "INTRO_CHAR_POLY_2X2",
    "INTRO_DETERMINANT_3X3",
    "INTRO_FIRST_ORDER_LINEAR_ODE_EXP",
    "INTRO_POLYNOMIAL_DEFINITE_INTEGRAL",
    "INTRO_QUADRATIC",
    "INTRO_RESIDUE_UNIT_QUADRATIC",
    "DerivationStep",
    "InvariantCheck",
    "Lemma",
    "determinant_3x3",
    "expand_characteristic_polynomial_2x2",
    "first_order_linear_ode_exp_solution",
    "numerical_verify",
    "polynomial_definite_integral",
    "residue_theorem_unit_quadratic",
    "solve_quadratic",
]
