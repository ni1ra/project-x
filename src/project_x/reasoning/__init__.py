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
from project_x.reasoning.integration import (
    INTRO_INTEGRATION_BY_PARTS_X_COS,
    INTRO_INTEGRATION_BY_PARTS_X_EXP,
    INTRO_INTEGRATION_BY_PARTS_X_SIN,
    INTRO_USUB_X_TRIG_X_SQUARED,
    definite_integral_x_times_cos,
    definite_integral_x_times_exp,
    definite_integral_x_times_sin,
    definite_integral_xtrig_via_usub,
)
from project_x.reasoning.number_theory import (
    INTRO_COLLATZ_VERIFICATION,
    INTRO_GOLDBACH_VERIFICATION,
    INTRO_MERTENS_BOUND_VERIFICATION,
    INTRO_TWIN_PRIMES_VERIFICATION,
    collatz_verify_range,
    goldbach_verify_range,
    mertens_bound_verify,
    twin_primes_in_range,
)
from project_x.reasoning.ode import (
    INTRO_FIRST_ORDER_LINEAR_ODE_EXP,
    first_order_linear_ode_exp_solution,
)
from project_x.reasoning.physics import (
    INTRO_FREE_FALL,
    INTRO_LARGE_ANGLE_PENDULUM,
    INTRO_PENDULUM,
    INTRO_PROJECTILE_HORIZONTAL_RANGE,
    INTRO_RELATIVISTIC_DOPPLER_SHIFT,
    INTRO_RELATIVISTIC_MOMENTUM,
    free_fall_time,
    large_angle_pendulum_period,
    pendulum_period,
    projectile_horizontal_range,
    relativistic_doppler_shift,
    relativistic_momentum,
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
    "INTRO_COLLATZ_VERIFICATION",
    "INTRO_DETERMINANT_3X3",
    "INTRO_FIRST_ORDER_LINEAR_ODE_EXP",
    "INTRO_FREE_FALL",
    "INTRO_GOLDBACH_VERIFICATION",
    "INTRO_INTEGRATION_BY_PARTS_X_COS",
    "INTRO_INTEGRATION_BY_PARTS_X_EXP",
    "INTRO_INTEGRATION_BY_PARTS_X_SIN",
    "INTRO_LARGE_ANGLE_PENDULUM",
    "INTRO_MERTENS_BOUND_VERIFICATION",
    "INTRO_PENDULUM",
    "INTRO_POLYNOMIAL_DEFINITE_INTEGRAL",
    "INTRO_PROJECTILE_HORIZONTAL_RANGE",
    "INTRO_QUADRATIC",
    "INTRO_RELATIVISTIC_DOPPLER_SHIFT",
    "INTRO_RELATIVISTIC_MOMENTUM",
    "INTRO_RESIDUE_UNIT_QUADRATIC",
    "INTRO_TWIN_PRIMES_VERIFICATION",
    "INTRO_USUB_X_TRIG_X_SQUARED",
    "DerivationStep",
    "InvariantCheck",
    "Lemma",
    "collatz_verify_range",
    "determinant_3x3",
    "expand_characteristic_polynomial_2x2",
    "first_order_linear_ode_exp_solution",
    "free_fall_time",
    "goldbach_verify_range",
    "large_angle_pendulum_period",
    "mertens_bound_verify",
    "numerical_verify",
    "pendulum_period",
    "polynomial_definite_integral",
    "projectile_horizontal_range",
    "relativistic_doppler_shift",
    "relativistic_momentum",
    "residue_theorem_unit_quadratic",
    "solve_quadratic",
    "twin_primes_in_range",
]
