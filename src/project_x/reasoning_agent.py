"""ReasoningAgent — rule-based AGENT runtime that consumes benchmark prompts and dispatches
to existing substrate primitives, returning computed Lemma renders.

Phase 13 cycle 7 #00P13c7-NEW — operationalizes lain's mid-cycle-7 directive 2026-05-10:
*"make the agent actually solve the problems ... real results, not just some tests pass."*

The AGENT (Project X Raphael) here REPLACES the BUILDER-authored frozen `raphael_response`
pattern for objective programmatically-testable benchmark entries. Pipeline per call:

  prompt (str)
    → rule-based parser identifies problem-shape + extracts numeric parameters
    → dispatcher routes to existing substrate primitive
    → substrate returns Lemma
    → AgentResponse wraps Lemma.render() as answer_text plus structured metadata

Organic-thesis compliance (binding): NO LLM at the agent layer. NO pretrained-transformer
derivatives. Parsers are rule-based regex; dispatcher is a hand-coded switch over the
matched problem-shapes. The substrate primitives themselves are already hand-rolled
(cycle 2 #02 symbolic.py + cycle 4 #02 physics.py); this module composes them.

Cycle 7 minimum-viable scope: maths quadratic dispatcher (covers maths-001/007/008 —
the 3 standard-form-quadratic entries on the existing ladder). Cycle 7+ extends to:
  - 2x2 eigenvalues (maths-002, maths-009)
  - Definite integrals (maths-010)
  - First-order ODEs (maths-011)
  - 3x3 determinants (maths-012)
  - Physics: free-fall (physics-001, physics-008), pendulum (physics-002, physics-009),
    relativistic momentum (physics-003, physics-011), large-angle pendulum (physics-010),
    Doppler shift (physics-012), projectile range (physics-007)

Each domain extension adds: (a) a regex pattern detecting the problem-shape, (b) a parser
extracting parameters, (c) a dispatcher branch routing to the existing substrate. Each
extension is independently testable; brittle phrasing variations show up as parser-misses
which the test suite catches.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from project_x.reasoning.calculus import polynomial_definite_integral
from project_x.reasoning.complex_analysis import residue_theorem_unit_quadratic
import numpy as np

from project_x.corpus.k_rollout import KRolloutComposer
from project_x.corpus.natural_mode import NaturalModeComposer
from project_x.experiments.encoder import CharNgramHashEncoder, cosine_bipolar
from project_x.reasoning.diophantine import solve_binary_quadratic, solve_pell_equation
from project_x.reasoning.integration import (
    definite_integral_x_times_cos,
    definite_integral_x_times_exp,
    definite_integral_x_times_sin,
    definite_integral_xtrig_via_usub,
)
from project_x.reasoning.number_theory import (
    collatz_verify_range,
    goldbach_verify_range,
    mertens_bound_verify,
    twin_primes_in_range,
)
from project_x.reasoning.ode import first_order_linear_ode_exp_solution
from project_x.reasoning.physics import (
    free_fall_time,
    large_angle_pendulum_period,
    pendulum_period,
    projectile_horizontal_range,
    relativistic_doppler_shift,
    relativistic_momentum,
)
from project_x.reasoning.symbolic import (
    Lemma,
    determinant_3x3,
    expand_characteristic_polynomial_2x2,
    solve_quadratic,
)


@dataclass
class AgentResponse:
    """Output of `ReasoningAgent.process()`.

    `lemma` is None when the parser couldn't identify a problem-shape; `answer_text`
    in that case carries a refusal-with-reason rather than an attempted-answer. Honest
    failure is preferred over confabulation per M-PROJECTX-013 measure-don't-claim.

    `dispatcher_metadata` (cycle 11 #00P13c11-01) carries BG-style dispatcher
    inspectability: combined-confidence score for the winning parser + the
    top-K candidate ranking. Kept OUT of `parsed_inputs` to avoid polluting
    strict-equality assertions on the substrate-input dict.
    """

    domain: str  # "maths" / "physics" / "open_domain" / "unrecognized"
    problem_shape: str  # "quadratic" / "char_poly_2x2" / "free_fall" / ... / "unrecognized"
    parsed_inputs: dict[str, Any]
    lemma: Lemma | None
    answer_text: str
    confidence: str  # "high" / "low" / "provenance-traced" / "refused"
    dispatcher_metadata: dict[str, Any] | None = None  # cycle 11 #00P13c11-01: BG-dispatcher inspectability


# Free-fall parser: extracts (h, g) from a drop/fall prompt.
# Robust to phrasing variation observed across physics-001 ("height of 80 m ... g = 9.81")
# and physics-008 ("fall from 50 m ... g = 3.71"). Two-gate filter: prompt must name
# drop/fall/dropped AND match both height + gravity patterns.
# Height pattern: cycle 8 #06 parser-robustness extension. Accept full-word "meters"
# / "metres" suffix (previously `m\b` required word boundary right after `m`, failing
# on "100 meters" since `e` is word-character; now `(?:eters?|etres?)?` swallows the
# suffix). Backward-compatible: "from 80 m" still matches via the empty optional group.
_HEIGHT_PATTERN = re.compile(
    r"(?:height of|from)\s+(\d+\.?\d*)\s*m(?:eters?|etres?)?\b", re.IGNORECASE
)
_GRAVITY_PATTERN = re.compile(r"g\s*=\s*(\d+\.?\d*)\s*m/s", re.IGNORECASE)


def _parse_free_fall(prompt: str) -> tuple[float, float] | None:
    """Extract (h, g) from a free-fall prompt. None if shape not recognized.

    Three-gate filter prevents misrouting: (1) prompt names fall/drop/dropped, (2) height
    pattern matches, (3) gravity pattern matches. All three required.
    """
    lower = prompt.lower()
    if not any(kw in lower for kw in ("drop", "fall", "dropped")):
        return None
    h_match = _HEIGHT_PATTERN.search(prompt)
    g_match = _GRAVITY_PATTERN.search(prompt)
    if not h_match or not g_match:
        return None
    return (float(h_match.group(1)), float(g_match.group(1)))


# Definite-integral parsers: extract bounds + quadratic-polynomial coefficients.
# Cycle 8 #02 minimum-viable scope: quadratic integrand `ax^2 + bx + c` over [lower, upper].
# Cycle 8+ parser-robustness extends to higher-degree + arbitrary phrasings.
_INTEGRAL_BOUNDS_PATTERN = re.compile(
    r"from\s+(-?\d+\.?\d*)\s+to\s+(-?\d+\.?\d*)", re.IGNORECASE
)
_INTEGRAL_QUADRATIC_POLY_PATTERN = re.compile(
    r"(-?\d+\.?\d*)\s*\*?\s*x\^2\s*([+-]\s*\d+\.?\d*)\s*\*?\s*x\s*([+-]\s*\d+\.?\d*)"
)

# Symbolic-integration parsers (cycle 9 #00P13c9-01): transcendental integrand shapes
# beyond polynomial — integration-by-parts (x·e^(cx), x·sin(cx), x·cos(cx)) and
# u-substitution (x·sin(x²), x·cos(x²)). Each has its own integrand pattern; the
# bounds regex is reused from cycle 8 #02.
# Coefficient c may be missing (=1) or "-" (=-1) before x in the exponent/argument.
_INTEGRAL_X_EXP_PATTERN = re.compile(
    r"x\s*[·*]?\s*e\^(?:\(\s*(-?\d*\.?\d*)\s*\*?\s*x\s*\)|x)", re.IGNORECASE
)
# Matches "x·e^x" (c=1 implicit, no group capture in 2nd branch) or "x·e^(2x)" / "x·e^(-1.5x)" (c captured)
_INTEGRAL_X_SIN_PATTERN = re.compile(
    r"x\s*[·*]?\s*sin\(\s*(?:(-?\d*\.?\d*)\s*\*?\s*)?x\s*\)", re.IGNORECASE
)
# Matches "x·sin(x)" (c=1 implicit, group empty) or "x·sin(2x)" (c=2)
_INTEGRAL_X_COS_PATTERN = re.compile(
    r"x\s*[·*]?\s*cos\(\s*(?:(-?\d*\.?\d*)\s*\*?\s*)?x\s*\)", re.IGNORECASE
)
# Matches "x·cos(x)" or "x·cos(2x)"
_INTEGRAL_XTRIG_USUB_SIN_PATTERN = re.compile(
    r"x\s*[·*]?\s*sin\(\s*x\s*\^?\s*[²2]\s*\)", re.IGNORECASE
)
# Matches "x·sin(x²)" or "x·sin(x^2)"
_INTEGRAL_XTRIG_USUB_COS_PATTERN = re.compile(
    r"x\s*[·*]?\s*cos\(\s*x\s*\^?\s*[²2]\s*\)", re.IGNORECASE
)
# Matches "x·cos(x²)" or "x·cos(x^2)"


def _parse_implicit_signed_coefficient(s: str | None) -> float:
    """Normalize a regex capture group representing an optional coefficient.

    Empty / None → 1.0 (implicit "1" before x). "-" → -1.0. Otherwise parsed as float.
    Used by symbolic-integration parsers where c may be implicit.
    """
    if s is None or s.strip() == "":
        return 1.0
    s_stripped = s.strip().replace("−", "-")
    if s_stripped == "-":
        return -1.0
    if s_stripped == "+":
        return 1.0
    return float(s_stripped)


def _parse_definite_integral_x_exp(prompt: str) -> tuple[float, float, float] | None:
    """Extract (lower, upper, c) for ∫_lower^upper x·e^(c·x) dx prompts (parts technique).

    Three-gate filter: (1) prompt names "integration by parts", (2) bounds match,
    (3) x·e^(cx) integrand pattern matches.
    """
    lower = prompt.lower()
    if "integration by parts" not in lower and "integration-by-parts" not in lower:
        return None
    bounds_match = _INTEGRAL_BOUNDS_PATTERN.search(prompt)
    if not bounds_match:
        return None
    integrand_match = _INTEGRAL_X_EXP_PATTERN.search(prompt)
    if not integrand_match:
        return None
    c = _parse_implicit_signed_coefficient(integrand_match.group(1))
    return (float(bounds_match.group(1)), float(bounds_match.group(2)), c)


def _parse_definite_integral_x_sin(prompt: str) -> tuple[float, float, float] | None:
    """Extract (lower, upper, c) for ∫_lower^upper x·sin(c·x) dx prompts (parts technique)."""
    lower = prompt.lower()
    if "integration by parts" not in lower and "integration-by-parts" not in lower:
        return None
    bounds_match = _INTEGRAL_BOUNDS_PATTERN.search(prompt)
    if not bounds_match:
        return None
    integrand_match = _INTEGRAL_X_SIN_PATTERN.search(prompt)
    if not integrand_match:
        return None
    c = _parse_implicit_signed_coefficient(integrand_match.group(1))
    return (float(bounds_match.group(1)), float(bounds_match.group(2)), c)


def _parse_definite_integral_x_cos(prompt: str) -> tuple[float, float, float] | None:
    """Extract (lower, upper, c) for ∫_lower^upper x·cos(c·x) dx prompts (parts technique)."""
    lower = prompt.lower()
    if "integration by parts" not in lower and "integration-by-parts" not in lower:
        return None
    bounds_match = _INTEGRAL_BOUNDS_PATTERN.search(prompt)
    if not bounds_match:
        return None
    integrand_match = _INTEGRAL_X_COS_PATTERN.search(prompt)
    if not integrand_match:
        return None
    c = _parse_implicit_signed_coefficient(integrand_match.group(1))
    return (float(bounds_match.group(1)), float(bounds_match.group(2)), c)


def _parse_definite_integral_xtrig_usub(prompt: str) -> tuple[float, float, str] | None:
    """Extract (lower, upper, trig_fn) for ∫_lower^upper x·sin(x²) or x·cos(x²) prompts (u-sub).

    Three-gate filter: (1) prompt names "u-substitution" (or "u substitution"), (2) bounds
    match, (3) one of the two u-sub integrand patterns matches (sin or cos of x²).
    """
    lower = prompt.lower()
    if "u-substitution" not in lower and "u substitution" not in lower:
        return None
    bounds_match = _INTEGRAL_BOUNDS_PATTERN.search(prompt)
    if not bounds_match:
        return None
    if _INTEGRAL_XTRIG_USUB_SIN_PATTERN.search(prompt):
        return (float(bounds_match.group(1)), float(bounds_match.group(2)), "sin")
    if _INTEGRAL_XTRIG_USUB_COS_PATTERN.search(prompt):
        return (float(bounds_match.group(1)), float(bounds_match.group(2)), "cos")
    return None


def _parse_definite_integral_quadratic(prompt: str) -> tuple[list[float], float, float] | None:
    """Extract (coeffs_descending, lower, upper) from a quadratic-integrand definite integral.

    Four-gate filter: prompt names integral / ∫ AND bounds match AND quadratic polynomial
    match. Cycle 8 #02 covers maths-010 specifically (∫₀² (3x² + 2x - 1) dx); higher-degree
    polynomials defer to cycle 8+ parser robustness work.
    """
    lower = prompt.lower()
    if "integral" not in lower and "∫" not in prompt:
        return None
    # Must NOT contain "residue theorem" or it would route to residue-theorem dispatcher.
    if "residue theorem" in lower or "contour integral" in lower:
        return None
    bounds_match = _INTEGRAL_BOUNDS_PATTERN.search(prompt)
    if not bounds_match:
        return None
    lower_b = float(bounds_match.group(1))
    upper_b = float(bounds_match.group(2))
    poly_match = _INTEGRAL_QUADRATIC_POLY_PATTERN.search(prompt)
    if not poly_match:
        return None
    a = float(poly_match.group(1).strip())
    b = float(poly_match.group(2).replace(" ", ""))
    c = float(poly_match.group(3).replace(" ", ""))
    return ([a, b, c], lower_b, upper_b)


# Residue-theorem real-line integral: matches `1/(a*x^2 + c)` or `1/(x^2 + c)` integrand.
# Coefficient `a` is captured as optional; defaults to 1 if absent. Used by maths-003 dispatch.
_RESIDUE_UNIT_QUADRATIC_PATTERN = re.compile(
    r"1\s*/\s*\(\s*(?P<a>\d*\.?\d*)\s*\*?\s*x\^2\s*\+\s*(?P<c>\d+\.?\d*)\s*\)"
)


def _parse_residue_unit_quadratic(prompt: str) -> tuple[float, float] | None:
    """Extract (a, c) from a residue-theorem real-line integral prompt of form 1/(a·x²+c).

    Three-gate filter prevents misrouting: (1) prompt names residue theorem (or contour
    integral), (2) prompt integrates over the real line (-infinity to infinity), (3) the
    integrand matches the 1/(a·x²+c) pattern.
    """
    lower = prompt.lower()
    if "residue theorem" not in lower and "contour integral" not in lower:
        return None
    if not ("infinity" in lower or "infty" in lower or "∞" in prompt):
        return None
    match = _RESIDUE_UNIT_QUADRATIC_PATTERN.search(prompt)
    if not match:
        return None
    a_str = match.group("a").strip()
    a = 1.0 if not a_str else float(a_str)
    c = float(match.group("c"))
    return (a, c)


# Projectile horizontal-range parsers: cliff-launched horizontal projectile.
# Closes physics-007. Reuses _GRAVITY_PATTERN; new _PROJECTILE_HEIGHT_PATTERN (accepts
# "from a 45 m cliff" / "from 45 m" / "height of 45 m") and _PROJECTILE_VELOCITY_PATTERN
# (accepts "at 20 m/s") — both gated by "projectile" + "horizontal" keywords to prevent
# misroute from free-fall prompts.
_PROJECTILE_HEIGHT_PATTERN = re.compile(
    r"(?:from\s+(?:a\s+)?|height of\s+)(\d+\.?\d*)\s*m\b", re.IGNORECASE
)
_PROJECTILE_VELOCITY_PATTERN = re.compile(
    r"at\s+(\d+\.?\d*)\s*m/s\b", re.IGNORECASE
)


def _parse_projectile_horizontal(prompt: str) -> tuple[float, float, float] | None:
    """Extract (h, v_horizontal, g) from a horizontally-launched projectile prompt.

    Four-gate filter: (1) "projectile" keyword, (2) "horizontal" keyword (specifies
    cliff-launched-horizontal mode vs angled launch), (3) height + velocity + gravity
    patterns all match. Both keywords required to prevent free-fall prompts (which
    have height + gravity but no horizontal velocity) from misrouting.
    """
    lower = prompt.lower()
    if "projectile" not in lower or "horizontal" not in lower:
        return None
    h_match = _PROJECTILE_HEIGHT_PATTERN.search(prompt)
    v_match = _PROJECTILE_VELOCITY_PATTERN.search(prompt)
    g_match = _GRAVITY_PATTERN.search(prompt)
    if not h_match or not v_match or not g_match:
        return None
    return (float(h_match.group(1)), float(v_match.group(1)), float(g_match.group(1)))


# Doppler-shift parsers: extract wavelength + β + direction.
# Closes physics-012. Wavelength accepts "λ₀ = 500 nm" or "wavelength λ_0 = 500 nm".
# β is parsed from velocity-as-fraction-of-c (reuses _VELOCITY_AS_C_PATTERN below).
# Direction is gated on explicit "approach" / "reced" / "moves away" keywords —
# no default; missing direction → refuse.
_WAVELENGTH_PATTERN = re.compile(
    r"(?:λ_?[0₀]?\s*=\s*|wavelength[^0-9]*?)(\d+\.?\d*)\s*nm", re.IGNORECASE
)


def _parse_doppler_shift(prompt: str) -> tuple[float, float, bool] | None:
    """Extract (wavelength_emit_nm, beta, approaching) from a Doppler-shift prompt.

    Four-gate filter: (1) "doppler" keyword, (2) explicit direction keyword
    (approach / recede / moves away), (3) wavelength pattern, (4) β extracted via
    velocity-as-fraction-of-c (e.g. "v = 0.6c"). Missing any gate → None.
    """
    lower = prompt.lower()
    if "doppler" not in lower:
        return None
    if "approach" not in lower and "reced" not in lower and "moves away" not in lower and "moving away" not in lower:
        return None
    lambda_match = _WAVELENGTH_PATTERN.search(prompt)
    beta_match = _VELOCITY_AS_C_PATTERN.search(prompt)
    if not lambda_match or not beta_match:
        return None
    wavelength_emit = float(lambda_match.group(1))
    beta = float(beta_match.group(1))
    approaching = "approach" in lower
    return (wavelength_emit, beta, approaching)


# Relativistic-momentum parsers: extract mass (scientific notation), velocity-as-fraction-of-c,
# and speed of light. Handles physics-003 (electron at 0.9c) and physics-011 (proton at 0.5c).
# Mass pattern is permissive on subscripts (m, m_e, m_p) and accepts scientific notation.
_MASS_PATTERN = re.compile(r"m_?\w?\s*=\s*([\d.]+(?:e[+-]?\d+)?)\s*kg", re.IGNORECASE)
# Velocity-as-fraction-of-c: "v = 0.9c" / "v = 0.5 c"
_VELOCITY_AS_C_PATTERN = re.compile(r"v\s*=\s*(\d+\.?\d*)\s*c\b", re.IGNORECASE)
# Speed of light: "c = 3.0e8 m/s"
_SPEED_OF_LIGHT_PATTERN = re.compile(r"c\s*=\s*([\d.]+(?:e[+-]?\d+)?)\s*m/s", re.IGNORECASE)


def _parse_relativistic_momentum(prompt: str) -> tuple[float, float, float] | None:
    """Extract (m, v, c) from a relativistic-momentum prompt.

    Velocity comes in as a fraction of c (e.g., "0.9c"); we multiply by the explicit
    speed-of-light value to get v in m/s for the substrate. Four-gate filter: "relativistic
    momentum" naming AND mass match AND velocity-fraction match AND speed-of-light match.
    """
    lower = prompt.lower()
    if "relativistic momentum" not in lower:
        return None
    m_match = _MASS_PATTERN.search(prompt)
    v_match = _VELOCITY_AS_C_PATTERN.search(prompt)
    c_match = _SPEED_OF_LIGHT_PATTERN.search(prompt)
    if not m_match or not v_match or not c_match:
        return None
    m = float(m_match.group(1))
    v_fraction = float(v_match.group(1))
    c = float(c_match.group(1))
    v = v_fraction * c
    return (m, v, c)


# Pendulum length parser: cycle 8 #06 parser-robustness extension. Accepts:
#   - "L = 1.0 m" (original form)
#   - "length L = 0.5 m" (original form)
#   - "length 1 m" / "length of 1 m" / "length 1 meter" (new rephrasings — e.g.
#     "a swinging pendulum of length 1 m")
# Plus full-word "meters" / "metres" suffix (mirrors _HEIGHT_PATTERN extension).
_LENGTH_PATTERN = re.compile(
    r"(?:L\s*=\s*|length(?:\s+of)?\s+)(\d+\.?\d*)\s*m(?:eters?|etres?)?\b",
    re.IGNORECASE,
)

# Pendulum amplitude parser: matches "from a Nθ angle" / "(θ₀ = N rad)" / "at N degrees"
# / "at N°". Captures BOTH a numeric value AND a unit indicator (rad/deg/° absent → deg
# typical-default, but we require explicit unit to avoid ambiguity).
_AMPLITUDE_PATTERN = re.compile(
    r"(?:θ_?0?\s*=\s*|amplitude[^0-9]*|angle[^0-9]*|from a\s+|at\s+)(\d+\.?\d*)\s*(?:°|deg(?:ree)?s?|rad(?:ian)?s?|π/\d+)",
    re.IGNORECASE,
)


def _parse_pendulum(prompt: str) -> tuple[float, float, float | None] | None:
    """Extract (L, g, theta_0_rad) from a pendulum prompt.

    `theta_0_rad` is None for small-angle prompts (the substrate doesn't need it); a
    positive radians value for large-angle prompts. Caller dispatches to small-angle
    or large-angle substrate based on the None-vs-float status.

    Three-gate filter: prompt must name pendulum AND length match AND gravity match.
    Small-angle keyword (\"small-angle\") or large-angle keyword (\"elliptic\" / \"large\")
    branches the dispatch.
    """
    lower = prompt.lower()
    if "pendulum" not in lower:
        return None
    L_match = _LENGTH_PATTERN.search(prompt)
    g_match = _GRAVITY_PATTERN.search(prompt)
    if not L_match or not g_match:
        return None
    L = float(L_match.group(1))
    g = float(g_match.group(1))

    # Large-angle detection: explicit "elliptic" / "large-angle" / amplitude θ in prompt
    is_large_angle = (
        "elliptic" in lower
        or "large-angle" in lower
        or "large angle" in lower
        or "not the small-angle" in lower
    )
    if not is_large_angle:
        return (L, g, None)

    # Try to extract amplitude in radians. Handle "θ₀ = π/3 rad" / "π/3 rad" forms first
    # (π/N pattern), then fall back to numeric+unit. Captures the radians value.
    pi_frac = re.search(r"π/(\d+\.?\d*)", prompt)
    if pi_frac:
        theta_0 = math.pi / float(pi_frac.group(1))
        return (L, g, theta_0)
    # Numeric amplitude with explicit unit
    amp_match = _AMPLITUDE_PATTERN.search(prompt)
    if amp_match:
        value = float(amp_match.group(1))
        # Detect unit from match suffix
        matched_text = amp_match.group(0).lower()
        if "rad" in matched_text:
            theta_0 = value
        elif "°" in matched_text or "deg" in matched_text:
            theta_0 = value * math.pi / 180.0
        else:
            theta_0 = value  # assume radians as conservative default
        return (L, g, theta_0)
    # Large-angle prompt without parseable amplitude → can't dispatch
    return None


# First-order linear separable homogeneous ODE: dy/dx = k·y with y(x_0) = y_0; report y(x_target).
# Closes maths-011 agent-runtime gap (cycle 8 #03). Three separate regexes capture (k, IC, target);
# domain keyword gate ("dy/dx" or "differential equation") gates the dispatch ahead of pattern match.
_ODE_LINEAR_K_PATTERN = re.compile(
    r"dy/dx\s*=\s*(-?\d*\.?\d*)\s*\*?\s*y", re.IGNORECASE
)
# IC: y(x_0) = y_0 with optional whitespace. Both groups required.
_ODE_IC_PATTERN = re.compile(
    r"y\s*\(\s*(-?\d+\.?\d*)\s*\)\s*=\s*(-?\d+\.?\d*)", re.IGNORECASE
)
# Target evaluation: "Report y(x_target)" / "Find y(x_target)" / "Evaluate y(x_target)" / "Compute y(x_target)".
# Action keyword gate prevents collision with IC pattern (which requires `=`).
_ODE_TARGET_PATTERN = re.compile(
    r"(?:report|find|evaluate|compute)\s+y\s*\(\s*(-?\d+\.?\d*)\s*\)", re.IGNORECASE
)


def _parse_first_order_ode(prompt: str) -> tuple[float, float, float, float] | None:
    """Extract (k, y_0, x_target, x_0) from a first-order linear ODE prompt.

    Four-gate filter prevents misrouting: (1) prompt names ODE via "dy/dx" or
    "differential equation", (2) the dy/dx = k·y coefficient pattern matches,
    (3) the IC y(x_0) = y_0 pattern matches, (4) the Report/Find/Evaluate y(x_target)
    pattern matches. All four required; otherwise None.

    Cycle 8 #03 minimum-viable scope: homogeneous first-order linear separable.
    Non-homogeneous (dy/dx + p(x)·y = q(x)) and separable-general (dy/dx = f(x)·g(y))
    defer to cycle 8+ extensions.
    """
    lower = prompt.lower()
    if "dy/dx" not in lower and "differential equation" not in lower:
        return None
    k_match = _ODE_LINEAR_K_PATTERN.search(prompt)
    ic_match = _ODE_IC_PATTERN.search(prompt)
    target_match = _ODE_TARGET_PATTERN.search(prompt)
    if not k_match or not ic_match or not target_match:
        return None
    k = _parse_signed_coefficient(k_match.group(1), implicit_one=True)
    x_0 = float(ic_match.group(1))
    y_0 = float(ic_match.group(2))
    x_target = float(target_match.group(1))
    return (k, y_0, x_target, x_0)


# Number-theory dispatchers (cycle 8 #00P13c8-10): Collatz / Goldbach / twin primes / Mertens.
# Each closes a programmatic-unsolved-theorem benchmark entry (maths-017..020) per lain
# mid-cycle directive 2026-05-11. Honest M-PROJECTX-013 framing: PASS = empirical
# verification over [1, N] only — NEVER theorem proof.
_NT_RANGE_1_PATTERN = re.compile(r"\[\s*1\s*,\s*(\d+)\s*\]")
_NT_RANGE_4_PATTERN = re.compile(r"\[\s*4\s*,\s*(\d+)\s*\]")
_NT_LEQ_N_PATTERN = re.compile(r"(?:≤|<=)\s*(\d+)")

# Cycle-13 #07d (audit B4 fix): widen [1, N]-bound extraction to accept prose forms.
# The demo P3 prompt "Verify the Collatz conjecture for the first 10000 integers..."
# previously fell through `_NT_RANGE_1_PATTERN` and silently routed to natural-mode
# (F5 in cycle-13 demo doc). Prose forms below cover common phrasings; the bracketed
# pattern remains the canonical form for benchmark prompts.
_NT_PROSE_PATTERNS_RANGE_1: tuple[re.Pattern[str], ...] = (
    re.compile(r"first\s+(\d+)\s+(?:integers|positive integers|natural numbers|values?|n)", re.IGNORECASE),
    re.compile(r"for\s+n\s+up\s+to\s+(\d+)", re.IGNORECASE),
    re.compile(r"in\s+the\s+first\s+(\d+)", re.IGNORECASE),
    re.compile(r"for\s+(?:all\s+)?(?:integers?\s+)?n\s+(?:≤|<=)\s*(\d+)", re.IGNORECASE),
    re.compile(r"up\s+to\s+n\s*=\s*(\d+)", re.IGNORECASE),
)


def _extract_range_1_N(prompt: str) -> int | None:
    """Try bracketed `[1, N]` first; fall back to prose forms. Cycle-13 #07d (audit B4)."""
    m = _NT_RANGE_1_PATTERN.search(prompt)
    if m:
        return int(m.group(1))
    for pattern in _NT_PROSE_PATTERNS_RANGE_1:
        m = pattern.search(prompt)
        if m:
            return int(m.group(1))
    return None


def _parse_collatz_verify(prompt: str) -> int | None:
    """Extract N from a Collatz verification prompt. Gated by 'collatz' or '3n+1'.

    Cycle-13 #07d: prose-form N extraction via `_extract_range_1_N` so demo prompts
    like 'first 10000 integers' route to formal mode (audit B4 catch).
    """
    lower = prompt.lower()
    if "collatz" not in lower and "3n+1" not in lower and "3n + 1" not in lower:
        return None
    return _extract_range_1_N(prompt)


def _parse_goldbach_verify(prompt: str) -> int | None:
    """Extract N from a Goldbach verification prompt. Gated by 'goldbach'."""
    lower = prompt.lower()
    if "goldbach" not in lower:
        return None
    m = _NT_RANGE_4_PATTERN.search(prompt)
    return int(m.group(1)) if m else None


def _parse_twin_primes(prompt: str) -> int | None:
    """Extract N from a twin-primes enumeration prompt. Gated by 'twin prime'."""
    lower = prompt.lower()
    if "twin prime" not in lower and "twin-prime" not in lower:
        return None
    m = _NT_LEQ_N_PATTERN.search(prompt)
    return int(m.group(1)) if m else None


def _parse_mertens_verify(prompt: str) -> int | None:
    """Extract N from a Mertens-bound verification prompt. Gated by 'mertens'.

    Cycle-13 #07d: prose-form N extraction via `_extract_range_1_N` so prose phrasings
    of the Mertens benchmark route to formal mode (symmetric with Collatz audit B4).
    """
    lower = prompt.lower()
    if "mertens" not in lower:
        return None
    return _extract_range_1_N(prompt)


# Diophantine binary-quadratic regex (cycle 9 #00P13c9-03). Parses the LHS of a
# Q(x, y) = N equation in the canonical shape a·x² + b·xy + c·y² = N. Handles:
# - unicode ² and ASCII ^2 (normalized to ^2 before regex)
# - middle dot · and asterisk * separators (normalized away)
# - whitespace (stripped)
# - implicit coefficients (a or c absent → 1; b absent → 0; explicit signs preserved)
# Cross-term and y² require explicit + or - sign because the x² term is the anchor.
_DIOPHANTINE_LHS_PATTERN = re.compile(
    r"(?P<a>[+-]?\d*)x\^2"                 # ax^2 (sign + magnitude both optional)
    r"(?:(?P<b>[+-]\d*)xy)?"               # optional cross term ±bxy
    r"(?P<c>[+-]\d*)y\^2"                  # ±cy^2 (sign required)
    r"=(?P<N>-?\d+)",                       # = N
)


def _parse_diophantine_binary_quadratic(prompt: str) -> tuple[int, int, int, int] | None:
    """Extract (a, b, c, N) from a Diophantine binary-quadratic problem prompt.

    Gated by a Diophantine-flavor keyword ('diophantine' / 'integer solutions' /
    'integer pairs' / 'binary quadratic form'). Returns None if the prompt isn't
    in this shape — caller (dispatcher chain) then falls through to next parser.

    Default coefficients on absent terms: a=1 (when prompt starts directly with x²);
    c=1 (no magnitude on +y² → +1); b=0 (no cross term in prompt).
    """
    lower = prompt.lower()
    if not any(
        kw in lower for kw in (
            "diophantine", "integer solutions", "integer pairs",
            "binary quadratic", "all integer (x", "all integer pairs",
        )
    ):
        return None

    # Normalize: drop spaces, swap unicode ² → ^2, drop · and * coefficient separators,
    # swap unicode minus − (U+2212) → ASCII -. Last step matches the cycle 8 #06 quadratic
    # parser-robustness fix — typographic minus is common in LaTeX-rendered prompts and
    # would otherwise miss the [+-] regex character class.
    normalized = (
        prompt
        .replace(" ", "")
        .replace("²", "^2")
        .replace("·", "")
        .replace("*", "")
        .replace("−", "-")
    )

    m = _DIOPHANTINE_LHS_PATTERN.search(normalized)
    if not m:
        return None

    def _coeff(s: str, default: int = 1) -> int:
        """Parse signed coefficient string into int. '' → default, '+' → 1, '-' → -1, '+3'→3."""
        if not s or s in ("+", "-"):
            sign = -1 if s == "-" else 1
            return sign * default
        return int(s)

    a = _coeff(m.group("a") or "", default=1)
    b = _coeff(m.group("b") or "", default=1) if m.group("b") else 0
    c = _coeff(m.group("c") or "+", default=1)
    N = int(m.group("N"))
    return (a, b, c, N)


# 3x3 matrix regex: matches `[[a, b, c], [d, e, f], [g, h, i]]` with optional whitespace.
# All nine entries captured as signed decimal strings; whitespace inside brackets allowed.
# Closes maths-012 (cycle 8 #00P13c8-04). Placed BEFORE 2x2 pattern so longer-match wins
# on prompts that mention both shapes; 2x2 pattern won't false-match a 3x3 literal anyway
# (the 2x2 inner-bracket anchor `\d, \d \]` doesn't match a 3-entry inner bracket `\d, \d, \d ]`).
_MATRIX_3X3_PATTERN = re.compile(
    r"\[\s*\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]\s*,"
    r"\s*\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]\s*,"
    r"\s*\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]\s*\]"
)


def _parse_matrix_3x3(prompt: str) -> list[list[float]] | None:
    """Extract `[[a, b, c], [d, e, f], [g, h, i]]` matrix from a determinant prompt.

    Two-gate filter: (1) prompt names "determinant", (2) 3x3 matrix literal matches.
    Keyword gate prevents misrouting from an eigenvalue/char-poly prompt that
    happens to have a 3x3 matrix literal (those route to the 2x2 path only if 2x2).
    """
    if "determinant" not in prompt.lower():
        return None
    match = _MATRIX_3X3_PATTERN.search(prompt)
    if not match:
        return None
    values = [float(x) for x in match.groups()]
    return [values[0:3], values[3:6], values[6:9]]


# 2x2 matrix regex: matches `[[a, b], [c, d]]` with optional whitespace.
# All four entries captured as signed decimal strings; whitespace inside brackets allowed.
_MATRIX_2X2_PATTERN = re.compile(
    r"\[\s*\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]\s*,"
    r"\s*\[\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*\]\s*\]"
)


def _parse_matrix_2x2(prompt: str) -> list[list[float]] | None:
    """Extract `[[a, b], [c, d]]` matrix from a prompt that mentions eigenvalues.

    Two gates must both pass: (1) the prompt names eigenvalues (or characteristic
    polynomial) so we don't accidentally route a non-eigenvalue matrix prompt here;
    (2) the regex matches a 2x2 matrix literal. Both gates failing → None.
    """
    if "eigenvalue" not in prompt.lower() and "characteristic polynomial" not in prompt.lower():
        return None
    match = _MATRIX_2X2_PATTERN.search(prompt)
    if not match:
        return None
    a, b, c, d = (float(x) for x in match.groups())
    return [[a, b], [c, d]]


# Natural-mode dispatcher v0 (cycle 11 #00P13c11-DEMO). Routes prompts that ASK
# for poetry / philosophy / meaning-of-life / free-form-question shapes to the
# NaturalModeComposer (v0 HDC walk over hand-seeded mini-corpus). Honest framing
# per M-PROJECTX-013: the agent is not GENERATING text; it is RETRIEVING and
# composing fragments with cited provenance. v0 capability proves the SHAPE of
# the canonical doc's Layer 4 § Natural mode; full implementation (Tier-1 +
# Tier-2 corpus + primitive emergence + hormone modulation + K-rollout) is
# cycle-11 remaining work.
_NATURAL_MODE_TRIGGERS: dict[str, tuple[str, ...]] = {
    "poetry": ("write a poem", "compose a poem", "write poetry", "compose poetry",
               "give me a poem", "compose verse", "write verse"),
    "philosophy": ("meaning of life", "what is the meaning", "philosophize",
                   "what do you think about", "philosophy of", "is it worth it",
                   "what does it mean to live", "purpose of existence",
                   "absurd", "consciousness", "free will"),
    # Cycle-13 #07d (audit B4 + synthesis-verdict §7 row 4 sub-bullet): triggers
    # tightened from bare "collatz" → phrase patterns. The demo P3 prompt "Verify
    # the Collatz conjecture for the first 10000 integers and discuss honestly..."
    # used to match bare "collatz" and route to natural-mode despite being a
    # formal-verification request. Phrase triggers preserve the open-conjecture
    # natural-mode path (test_agent_routes_collatz_open_conjecture_to_math) AND
    # release formal-form prompts to the structured Collatz dispatcher.
    "math": ("what does the collatz", "what is the collatz", "collatz conjecture mean",
             "collatz conjecture solved", "is collatz solved", "discuss collatz",
             "explain collatz", "what does the goldbach", "is goldbach solved",
             "discuss goldbach", "twin prime conjecture mean", "is twin prime solved",
             "discuss twin prime", "twin-prime conjecture mean",
             "riemann hypothesis", "matiyasevich", "hilbert tenth", "fermat",
             "honest framing about"),
    "lain_voice": ("project x", "what is raphael", "what is project x",
                   "your design philosophy", "your standing rules"),
    # Cycle 12 #00P13c12-01b — narrative_prose triggers for Tier-2-ingested
    # novels (Pride and Prejudice / Walden / Tale of Two Cities / Frankenstein
    # / Alice). Activated by "tell me a story / about / describe" phrasings.
    "narrative_prose": ("tell me a story", "tell me about", "describe a scene",
                        "narrate", "what happens in", "the story of"),
}


# BG-style dispatcher archetypes (cycle 11 #00P13c11-01). Canonical example
# prompts for each problem-shape; cosine similarity from input-prompt-HV to
# archetype-HV contributes to dispatcher confidence per canonical doc Layer 3.
# Archetypes are encoded once at first agent invocation via
# `CharNgramHashEncoder` (deterministic; no learning).
#
# Honest framing: these are HAND-PICKED canonical prompts. A future cycle-12+
# extension would expand to multiple archetypes per shape (representative-prompt
# clustering) and learn archetype centroids from observed prompts. v1 is the
# minimal viable mapping.
_PARSER_ARCHETYPES: dict[str, str] = {
    # Maths primitives
    "diophantine_binary_quadratic": "Find all integer solutions x y to the Diophantine equation x squared plus y squared equals 25.",
    "diophantine_binary_quadratic_out_of_scope": "Find integer solutions to a binary quadratic Diophantine equation that the substrate refuses.",
    "pell_equation": "Find the first 5 integer solutions x y to the Diophantine Pell equation x squared minus 2 y squared equals 1.",
    "pell_equation_degenerate": "Find solutions to a Pell equation where n is a perfect square so the equation is degenerate.",
    "collatz_verify_range": "Verify the Collatz 3n plus 1 conjecture for all integers in the range 1 to 1000.",
    "goldbach_verify_range": "Verify the Goldbach conjecture for all even integers in the range 4 to 1000.",
    "twin_primes_in_range": "Count the twin primes p and p plus 2 with both at most 1000.",
    "mertens_bound_verify": "Verify the Mertens bound absolute value of M of n is at most square root of n for all integers in the range 1 to 1000.",
    "residue_theorem_unit_quadratic": "Use the residue theorem to evaluate the integral 1 over a x squared plus c from minus infinity to infinity.",
    "definite_integral_x_times_exp": "Use integration by parts to compute the integral of x times e to the c x from 0 to 1.",
    "definite_integral_x_times_sin": "Use integration by parts to compute the integral of x times sine of c x from 0 to pi.",
    "definite_integral_x_times_cos": "Use integration by parts to compute the integral of x times cosine of c x from 0 to pi.",
    "definite_integral_xtrig_via_usub_sin": "Use u substitution with u equals x squared to compute the integral of x times sine of x squared from 0 to 1.",
    "definite_integral_xtrig_via_usub_cos": "Use u substitution with u equals x squared to compute the integral of x times cosine of x squared from 0 to 1.",
    "definite_integral_quadratic": "Compute the integral of 3 x squared plus 2 x minus 1 from 0 to 2.",
    "first_order_linear_ode_exp": "Solve the differential equation dy over dx equals 2 y with initial condition y at 0 equals 3; report y at 1.",
    "quadratic": "Solve the quadratic equation 3 x squared minus 14 x minus 5 equals 0.",
    "char_poly_2x2": "Find the eigenvalues of the 2 by 2 matrix 2 1 1 2.",
    "determinant_3x3": "Compute the determinant of the 3 by 3 matrix 1 2 3 4 5 6 7 8 10.",
    # Physics primitives
    "free_fall": "An object is dropped from a height of 80 meters with g equals 9.81 meters per second squared; compute the fall time.",
    "pendulum_small_angle": "Compute the period of a simple pendulum with length L equals 1.0 meters and g equals 9.81 meters per second squared.",
    "pendulum_large_angle": "Compute the period of an elliptic large angle pendulum with length 1 meter and amplitude pi over 3 radians.",
    "relativistic_momentum": "Compute the relativistic momentum of an electron with mass m equals 9.11e-31 kg at velocity v equals 0.9 c with speed of light c equals 3e8.",
    "projectile_horizontal_range": "A projectile is launched horizontally from a 45 m cliff at 20 m per s with g equals 9.81 meters per second squared; compute the horizontal range.",
    "relativistic_doppler_shift": "Compute the relativistic Doppler shift for emitted wavelength lambda 0 equals 500 nm at v equals 0.6 c approaching the observer.",
    # Natural-mode walks (cycle 11 #00P13c11-DEMO)
    "natural_mode_walk_poetry": "Write a poem about the changing seasons.",
    "natural_mode_walk_philosophy": "What is the meaning of life?",
    "natural_mode_walk_math": "What does the Collatz conjecture mean? Is it solved?",
    "natural_mode_walk_lain_voice": "What is Project X Raphael? What is your design philosophy?",
}


# Cycle 11 #00P13c11-08 dual-mode composer — register-archetype prompts for
# hormone-modulated intent classification. Per canonical doc Layer 2 § Hormone
# modulation: "Intent classification via HDC similarity (intent-subspace
# nearest-neighbor) drives hormone selection." V1 implements register-archetype
# cosine matching — input prompt → most-similar register archetype → render
# the Lemma at that register. Continuous (cosine) vs binary (keyword gates).
_REGISTER_ARCHETYPES: dict[str, str] = {
    "default": "Solve this problem and show your work in a structured proof.",
    "terse": "Just give me the answer, no explanation needed, one line.",
    "tutorial": "Explain how to solve this step by step and tell me why each step works pedagogically.",
    "casual": "Hey, what do you think about this — let's chat about it casually.",
}


def _classify_intent_register(
    prompt: str,
    encoder: "CharNgramHashEncoder | None" = None,
    archetype_hvs: "dict[str, np.ndarray] | None" = None,
) -> str:
    """V1 register classifier — cosine similarity to register archetypes.

    Returns one of 'default' / 'terse' / 'tutorial' / 'casual' based on which
    register archetype is most similar to the input prompt. Mirrors the BG-
    dispatcher's confidence-scored pattern but applied to register selection
    rather than parser selection.

    For test convenience, `encoder` and `archetype_hvs` are optional — if not
    provided, they're constructed on the fly (slow; ReasoningAgent caches them
    via class-level lazy init).
    """
    if encoder is None:
        encoder = CharNgramHashEncoder()
    if archetype_hvs is None:
        archetype_hvs = {
            name: encoder.encode([text])[0]
            for name, text in _REGISTER_ARCHETYPES.items()
        }
    prompt_hv = encoder.encode([prompt])[0]
    best_register = "default"
    best_sim = -2.0
    for name, hv in archetype_hvs.items():
        sim = cosine_bipolar(prompt_hv, hv)
        if sim > best_sim:
            best_sim = sim
            best_register = name
    return best_register


def _classify_natural_mode_domain(
    prompt: str,
    *,
    encoder: "CharNgramHashEncoder | None" = None,
    archetype_hvs: "dict[str, list[np.ndarray]] | None" = None,
    tau_dispatch: float = 0.10,
) -> str | None:
    """Identify which natural-mode domain a prompt invokes, or None if not natural-mode shape.

    Cycle-14 #08g — KEYWORD-GATE RETIRED. The previous two-stage classifier
    (cycle-13 #07e) ran a keyword phrase-match first, falling through to
    cosine-archetype matching only on no-keyword-hit. This cycle pre-retires
    the keyword-gate stage as proof-of-direction per the cycle-14 synthesis
    §4.a — the hand-coded keyword phrase list (`_NATURAL_MODE_TRIGGERS`) was
    the most-keyword-shaped, most-hand-picked piece of scaffolding in the
    dispatcher. Its removal forces ALL prompts through the cosine-archetype
    path; the substrate's cosine-similarity discrimination + cycle-14 #08c
    HebbianBank reward-shaped blend carry the routing instead.

    The `_NATURAL_MODE_TRIGGERS` constant remains in this file as the
    historical record of what the keyword gate used to match; downstream
    cycles can compare cosine-archetype coverage against the keyword set
    + verify no regression on the phrases the cycle-11-13 work relied on.

    Single-stage classification (cycle-14 #08g):
       The prompt is encoded; the domain with the MAXIMUM cosine to any of
       its archetypes wins iff the best score clears `tau_dispatch`. The
       max-of-cosines aggregation (not centroid bundling) is empirically
       more discriminative on the char-n-gram-hash floor encoder — a domain
       with 3 archetypes spanning poetry / sonnet / verse shapes scores well
       when ONE archetype matches strongly, even if the others share little
       with the prompt.

    Empirical τ_dispatch=0.10 on char-n-gram-hash D=10240 cleanly splits demo-
    REFUSE shapes (random / structured math / structured physics) from demo-ROUTE
    shapes (P4 philosophy 0.1145; P5 poetry 0.2773; meaning-of-life 0.4652).
    Cycle-15+ may recalibrate per the HebbianBank reward signal.

    Conservative ordering: structured math/physics dispatchers precede natural-
    mode in `process()`, AND the formal-priority-boost (#07d) further protects
    formal routing when both branches match. The cosine path activates for
    every prompt that gets here; downstream callers (e.g. `_try_natural_mode`)
    handle None as "no domain match — skip me."
    """
    if encoder is None or archetype_hvs is None:
        return None

    prompt_hv = encoder.encode([prompt])[0]
    best_domain: str | None = None
    best_sim = -2.0
    for domain, archetype_list in archetype_hvs.items():
        # Max cosine across this domain's archetypes — one strong match wins
        # the domain even if its sibling archetypes share little with the prompt.
        domain_max = max(cosine_bipolar(prompt_hv, hv) for hv in archetype_list)
        if domain_max > best_sim:
            best_sim = domain_max
            best_domain = domain
    return best_domain if best_sim >= tau_dispatch else None


# Cycle-13 #07e: per-domain archetypes used for cosine-fallback dispatch when
# the keyword phrase set doesn't fire. 2-4 archetypes per domain; each chosen to
# span the SHAPE of natural-mode invocations the domain serves rather than a
# specific keyword. Encoded once at agent lazy-init; per-domain max-cosine across
# archetypes is what `_classify_natural_mode_domain` scores against (centroid
# bundling smears the signal; max-of-cosines preserves single-archetype matches).
_NATURAL_MODE_ARCHETYPES: dict[str, tuple[str, ...]] = {
    "poetry": (
        "Write a poem about the changing seasons and what passes.",
        "Compose a sonnet on autumn evenings and stillness.",
        "Give me verse on grief and remembrance and loss.",
    ),
    "philosophy": (
        "What is the meaning of life and how should one live it?",
        "Argue both perspectives on a deep contested philosophical question.",
        "Reflect on consciousness and free will and what they mean.",
    ),
    "math": (
        "What does the Collatz conjecture mean? Is it solved or open?",
        "Explain what the Goldbach conjecture says in plain English.",
        "Why is the Riemann hypothesis still open and what would resolve it?",
    ),
    "lain_voice": (
        "What is Project X Raphael and your design philosophy?",
        "What are your standing rules and how do you operate?",
    ),
    "narrative_prose": (
        "Tell me a story about an old gardener and a forgotten orchard.",
        "Describe a scene from a Jane Austen novel and what passes.",
        "What happens in Frankenstein at the moment of creation?",
    ),
}

_TAU_NATURAL_DISPATCH: float = 0.10  # cycle-13 #07e empirical floor (calibrated on
# char-n-gram-hash D=10240 floor encoder against {asdf,quick-fox,formal-math,
# formal-physics,formal-quadratic} REFUSE set + {P4,P5,sonnet-on-X,meaning-of-life}
# ROUTE set). Cycle-14+ Hebbian semantic encoder will reshape this floor.


# Quadratic regex: matches `a x^2 [+-] b x [+-] c = 0` with optional whitespace + `*`.
# Cycle 8 #06 parser-robustness extensions:
#   - Accept unicode `x²` (U+00B2 superscript two) AS WELL AS ASCII `x^2`.
#   - Accept unicode minus `−` (U+2212) AS WELL AS ASCII `-` in b/c coefficient signs
#     (typography-conscious prompts often substitute unicode minus for visual quality).
# Group 1 = a-coefficient string (may be empty for implicit 1, or "-" for implicit -1).
# Group 2 = b-coefficient with leading sign + whitespace (e.g., "- 14" or "+ 4" or "− 14").
# Group 3 = c-constant with leading sign + whitespace.
# `_parse_signed_coefficient` normalizes unicode minus to ASCII before float() conversion.
_QUADRATIC_PATTERN = re.compile(
    r"(-?\d*\.?\d*)\s*\*?\s*(?:x\^2|x²)"            # a · x²  (a optional)
    r"\s*([+\-−]\s*\d*\.?\d*)\s*\*?\s*x"             # ± b · x
    r"\s*([+\-−]\s*\d*\.?\d*)\s*=\s*0",              # ± c = 0
)


def _parse_signed_coefficient(s: str, *, implicit_one: bool = True) -> float:
    """Normalize a coefficient string from regex match into a float.

    Handles the empty-string-means-1 convention (e.g., `x^2` → a=1, not a=0) when
    `implicit_one=True`. The standalone `-` (no digits) → -1 if `implicit_one=True`,
    raises ValueError otherwise. Whitespace inside `+ 14` style strings is stripped.

    Cycle 8 #06 parser-robustness extension: unicode minus `−` (U+2212) is normalized
    to ASCII `-` before float() conversion. Prompts using typographic minus (common
    in LaTeX-rendered math) now parse correctly without dispatcher modification.
    """
    s = s.strip().replace(" ", "").replace("−", "-")
    if not s or s == "+":
        return 1.0 if implicit_one else 0.0
    if s == "-":
        return -1.0 if implicit_one else 0.0
    return float(s)


def _parse_quadratic(prompt: str) -> tuple[float, float, float] | None:
    """Extract (a, b, c) coefficients from a quadratic-in-x prompt.

    Returns None if no quadratic pattern detected — caller treats as parser-miss
    (honest failure, not confabulation). The first regex match wins; benchmark
    prompts contain at most one quadratic.
    """
    match = _QUADRATIC_PATTERN.search(prompt)
    if not match:
        return None
    a_str, b_str, c_str = match.groups()
    a = _parse_signed_coefficient(a_str, implicit_one=True)
    # b and c always carry an explicit sign from the regex; implicit_one is False
    # because `+ x` would mean b=1 here, but `+ x` is also valid for b=1 — we use
    # implicit_one=True for b/c too so bare `+ x` parses as b=1 (and `- x` as b=-1).
    b = _parse_signed_coefficient(b_str, implicit_one=True)
    c = _parse_signed_coefficient(c_str, implicit_one=False)
    # c-as-empty would mean c=0 which solve_quadratic accepts; keep implicit_one=False
    # so a stray `+ x = 0` (no constant) doesn't get c=1 by mistake.
    return (a, b, c)


class ReasoningAgent:
    """Rule-based agent runtime for objective programmatically-testable benchmarks.

    Public API: `process(prompt: str) -> AgentResponse`. Cycle 11 #00P13c11-01:
    BG-style confidence-scored parallel-bid dispatch. Each parser in
    `_DISPATCH_CHAIN_ORDER` is invoked on the prompt; all non-None responses
    are collected; combined confidence = α × parser_match (1.0 if matched)
    + (1−α) × hv_similarity(prompt, problem_shape_archetype). Argmax wins
    with chain-order tiebreaker (earlier in chain = higher priority on ties).
    Combined confidence below `_TAU_DISPATCH` → honest refusal.

    Brain analogue per canonical synthesis doc Layer 3: basal ganglia direct
    (Go) + indirect (NoGo) pathways. The chain-order tiebreaker preserves
    cycle 7-10 disambiguation correctness (well-disjoint keyword-gated
    parsers mostly don't compete; when they do, prior priority wins).

    Honest failure mode (`AgentResponse` with `confidence='refused'`) when no
    parser matches OR all matching parsers are below the dispatch threshold.
    """

    # BG-style dispatch parameters (cycle 11 #00P13c11-01). Empirical tuning
    # is a cycle-11+ open question per canonical doc; v1 values below are
    # honest initial floors.
    _ALPHA: float = 0.6  # weight on parser-matched (binary 0/1); higher because regex match is high-precision
    _TAU_DISPATCH: float = 0.3  # combined-confidence floor to dispatch (else refuse)
    # Cycle-13 #07d (synthesis-verdict §7 row 4): when both formal and natural-mode
    # parsers match the SAME prompt, multiply formal candidates' combined confidence
    # by this factor before the argmax. Defense-in-depth against the demo F5 failure
    # (P3 Collatz prose-form: both formal `collatz_verify_range` and natural-mode-math
    # would match a permissive-trigger prompt; formal should win unambiguously when
    # the prompt has a parseable formal shape). Audit B4 widening alone is sufficient
    # for P3 specifically; the boost protects future demos where the natural-mode
    # archetype happens to be more cosine-similar to the prompt than the formal one.
    _FORMAL_PRIORITY_BOOST: float = 1.2

    # Ordered list of (problem_shape_for_archetype_lookup, method_attr_name).
    # Order serves as chain-order tiebreaker when combined confidences tie within ε.
    # Mirrors the historical first-match-wins ordering for backward compatibility.
    _DISPATCH_CHAIN_ORDER: tuple[tuple[str, str], ...] = (
        ("diophantine_binary_quadratic", "_try_diophantine_binary_quadratic"),
        ("collatz_verify_range", "_try_collatz_verify"),
        ("goldbach_verify_range", "_try_goldbach_verify"),
        ("twin_primes_in_range", "_try_twin_primes"),
        ("mertens_bound_verify", "_try_mertens_verify"),
        ("residue_theorem_unit_quadratic", "_try_residue_theorem"),
        ("definite_integral_x_times_exp", "_try_definite_integral_x_exp"),
        ("definite_integral_x_times_sin", "_try_definite_integral_x_sin"),
        ("definite_integral_x_times_cos", "_try_definite_integral_x_cos"),
        ("definite_integral_xtrig_via_usub_sin", "_try_definite_integral_xtrig_usub"),
        ("definite_integral_quadratic", "_try_definite_integral_quadratic"),
        ("projectile_horizontal_range", "_try_projectile_horizontal"),
        ("relativistic_doppler_shift", "_try_doppler_shift"),
        ("relativistic_momentum", "_try_relativistic_momentum"),
        ("pendulum_small_angle", "_try_pendulum"),
        ("free_fall", "_try_free_fall"),
        ("determinant_3x3", "_try_determinant_3x3"),
        ("char_poly_2x2", "_try_char_poly_2x2"),
        ("first_order_linear_ode_exp", "_try_first_order_ode"),
        ("quadratic", "_try_quadratic"),
        ("natural_mode_walk_poetry", "_try_natural_mode"),
    )

    # Class-level lazy-initialized archetype encoder + encoded archetype hvs.
    # Archetypes are canonical example prompts for each problem-shape; cosine
    # similarity from prompt-hv to archetype-hv contributes to dispatcher
    # confidence. Encoded once at first ReasoningAgent.process() call; cached.
    _archetype_encoder: CharNgramHashEncoder | None = None
    _archetype_hvs: dict[str, np.ndarray] | None = None
    # Cycle 11 #00P13c11-08 dual-mode composer — register archetype hvs for
    # hormone-modulated intent classification.
    _register_archetype_hvs: dict[str, np.ndarray] | None = None
    # Cycle-13 #07e natural-mode archetype hvs — per-domain LIST of bipolar
    # archetype hypervectors (NOT a single centroid; max-of-cosines is more
    # discriminative on the char-n-gram-hash floor encoder).
    _natural_mode_archetype_hvs: dict[str, list[np.ndarray]] | None = None

    @classmethod
    def _ensure_archetypes_encoded(cls) -> None:
        """Lazy init: encode all problem-shape, register, AND natural-mode-domain
        archetype prompts once. Natural-mode archetypes stored as per-domain
        LIST (max-of-cosines at dispatch); centroid bundling was tried and smears
        single-archetype matches (see `_classify_natural_mode_domain` docstring).
        """
        if cls._archetype_hvs is not None:
            return
        cls._archetype_encoder = CharNgramHashEncoder()
        cls._archetype_hvs = {
            name: cls._archetype_encoder.encode([archetype])[0]
            for name, archetype in _PARSER_ARCHETYPES.items()
        }
        cls._register_archetype_hvs = {
            name: cls._archetype_encoder.encode([archetype])[0]
            for name, archetype in _REGISTER_ARCHETYPES.items()
        }
        # Cycle-13 #07e: encode all archetypes per domain, keep as a list. The
        # encoder stacks them once; we split back to per-archetype hvs.
        cls._natural_mode_archetype_hvs = {}
        for domain, archetypes in _NATURAL_MODE_ARCHETYPES.items():
            stacked = cls._archetype_encoder.encode(list(archetypes))  # (k, D) int8
            cls._natural_mode_archetype_hvs[domain] = [stacked[i] for i in range(stacked.shape[0])]

    def process(self, prompt: str) -> AgentResponse:
        """BG-style confidence-scored parallel-bid dispatch (cycle 11 #00P13c11-01).

        For each parser in `_DISPATCH_CHAIN_ORDER`, invoke and collect the response
        if non-None. For each candidate, compute combined confidence = α × 1.0
        (parser matched) + (1−α) × normalized-cosine-similarity to the archetype
        for that response's problem_shape. Sort candidates by combined confidence
        descending, with chain-index ascending as tiebreaker (earlier in chain
        wins ties — preserves cycle 7-10 first-match-wins correctness on
        well-disjoint parsers). Top candidate wins if its combined confidence
        clears `_TAU_DISPATCH`; else honest refusal.
        """
        self._ensure_archetypes_encoded()
        prompt_hv = self._archetype_encoder.encode([prompt])[0]

        candidates: list[tuple[float, int, str, AgentResponse]] = []
        refused_candidates: list[tuple[int, str, AgentResponse]] = []
        for chain_index, (_archetype_key, method_name) in enumerate(self._DISPATCH_CHAIN_ORDER):
            method = getattr(self, method_name)
            response = method(prompt)
            if response is None:
                continue
            if response.confidence == "refused":
                refused_candidates.append((chain_index, method_name, response))
                continue
            # Look up the archetype for the ACTUAL problem_shape returned (handles
            # cases where one parser produces multiple shapes — e.g.,
            # `_try_diophantine_binary_quadratic` returns either
            # `diophantine_binary_quadratic` or `pell_equation` or
            # `pell_equation_degenerate` or `diophantine_binary_quadratic_out_of_scope`).
            archetype_hv = self._archetype_hvs.get(response.problem_shape)
            if archetype_hv is None:
                # Neutral fallback for problem-shapes without a dedicated
                # archetype. The old self-archetype fallback gave hv_sim=1.0,
                # which let missing-archetype candidates saturate confidence.
                # Refused candidates are filtered above; this neutral value is
                # for valid but newly-added shapes awaiting an archetype.
                hv_sim_normalized = 0.5
            else:
                cos_sim = cosine_bipolar(prompt_hv, archetype_hv)
                hv_sim_normalized = (cos_sim + 1.0) / 2.0  # map [-1, 1] → [0, 1]
            combined_confidence = self._ALPHA * 1.0 + (1.0 - self._ALPHA) * hv_sim_normalized
            candidates.append((combined_confidence, chain_index, method_name, response))

        if not candidates:
            if refused_candidates:
                refused_candidates.sort(key=lambda c: c[0])
                return refused_candidates[0][2]
            return AgentResponse(
                domain="unrecognized",
                problem_shape="unrecognized",
                parsed_inputs={},
                lemma=None,
                answer_text=(
                    "Notice. Prompt did not match any currently-supported problem-shape. "
                    "BG-style dispatcher ran all 21 parsers; none returned a match. "
                    "Honest failure preferred over confabulation per M-PROJECTX-013."
                ),
                confidence="refused",
            )

        # Cycle-13 #07d formal-priority boost: when BOTH formal and natural-mode
        # parsers match, lift formal candidates' confidence by _FORMAL_PRIORITY_BOOST.
        # `natural_mode_walk_*` shapes are emitted only by `_try_natural_mode`; every
        # other shape in the archetype table is formal. If no natural-mode candidate
        # is present, the boost is a no-op (only formal candidates compete; the lift
        # is uniform). Mathematically equivalent to: scale formal by 1.2 always; the
        # sort outcome is identical when only formal candidates exist.
        natural_mode_present = any(
            r.problem_shape.startswith("natural_mode_walk_") for _, _, _, r in candidates
        )
        formal_candidate_present = any(
            not r.problem_shape.startswith("natural_mode_walk_") for _, _, _, r in candidates
        )
        if natural_mode_present and not formal_candidate_present:
            formal_refusals = [
                item for item in refused_candidates if item[1] != "_try_natural_mode"
            ]
            if formal_refusals:
                formal_refusals.sort(key=lambda c: c[0])
                return formal_refusals[0][2]

        if natural_mode_present:
            candidates = [
                (
                    conf * self._FORMAL_PRIORITY_BOOST
                    if not r.problem_shape.startswith("natural_mode_walk_")
                    else conf,
                    idx, m, r,
                )
                for conf, idx, m, r in candidates
            ]

        # Sort by combined_confidence DESC, tiebreak by chain_index ASC
        candidates.sort(key=lambda c: (-c[0], c[1]))
        top_conf, _, top_method, top_response = candidates[0]

        if top_conf < self._TAU_DISPATCH:
            return AgentResponse(
                domain="unrecognized",
                problem_shape="unrecognized_low_confidence",
                parsed_inputs={"top_method": top_method, "top_confidence": top_conf},
                lemma=None,
                answer_text=(
                    f"Notice. BG-style dispatcher ran all parsers; top candidate "
                    f"'{top_method}' has combined confidence {top_conf:.3f} below "
                    f"dispatch threshold {self._TAU_DISPATCH}. Honest refusal."
                ),
                confidence="refused",
            )

        # Cycle 11 #00P13c11-08 dual-mode composer — register-archetype intent
        # classification + re-render at chosen register. The BG-dispatcher
        # picked WHICH parser; the register classifier picks WHICH FLAVOR of
        # rendered output. For formal-mode responses (lemma != None), re-render
        # at the chosen register if it's not the default. For natural-mode
        # responses (lemma == None; the K-rollout already rendered with
        # provenance trail), the register selection is informational only.
        register = _classify_intent_register(
            prompt, encoder=self._archetype_encoder,
            archetype_hvs=self._register_archetype_hvs,
        )
        if top_response.lemma is not None and register != "default":
            top_response.answer_text = top_response.lemma.render(register=register)

        # Annotate the response with BG dispatcher metadata for inspectability.
        # Limit to top-5 for context budget. Stored in dispatcher_metadata
        # (separate field) so strict `parsed_inputs == {...}` assertions stay
        # clean across the test suite.
        top_response.dispatcher_metadata = {
            "combined_confidence": round(top_conf, 4),
            "top5_candidates": [(m, round(c, 4)) for c, _, m, _ in candidates[:5]],
            "alpha": self._ALPHA,
            "tau_dispatch": self._TAU_DISPATCH,
            "intent_register": register,
        }
        return top_response

    # Class-level lazy singletons. Encoding 100+ fragments takes a few
    # milliseconds; cache them so test suites + repeated agent invocations
    # don't re-encode. `_natural_mode_composer` is the single-walk v0;
    # `_k_rollout_composer` wraps it with try-until-satisfied K-rollout
    # iteration per cycle 11 #00P13c11-03.
    _natural_mode_composer: NaturalModeComposer | None = None
    _k_rollout_composer: KRolloutComposer | None = None

    # K-rollout dispatch parameters (cycle 11 #00P13c11-04 integration).
    _K_ROLLOUT_K: int = 3
    # Cycle-14 #08e DEFERRED to cycle-15 — tau_satisfaction calibration is
    # structurally brittle on cycle-14 demo data:
    #   - cycle-14 misroute walks (P4 humour->math 0.1905; P5 chat->poetry
    #     0.1997) sit JUST above
    #   - cycle-13 desired natural-mode walks (Collatz framing-surface,
    #     "what does the Collatz conjecture mean?") sit BELOW 0.20 (~0.17)
    #   - acceptable cycle-14 on-topic walks (P2 0.2378, P3 0.2512) sit
    #     well ABOVE 0.20
    # No single global tau cleanly separates "good cycle-13 framing walks"
    # from "cycle-14 misroutes" because avg-cosine is not a quality
    # discriminator across these prompt regimes — both produce low-cosine
    # retrievals; one is desired (canonical framing surfacing), one is not
    # (wrong-domain confident emission). Per-domain tau + reward-shaped
    # blend (cycle-14 #08c HebbianBank) are the cycle-15 path: the bank's
    # accumulated approve/reject signal becomes the quality discriminator,
    # NOT bare cosine. Cycle-15 work: per-domain tau calibration sweep
    # over the rated audit log + (collatz-prompt, framing-fragment) pair
    # approvals so the bank's reward-blend correctly emits the framing
    # walks the cycle-13 tests assert. Tau stays 0.0 cycle-14 to preserve
    # the cycle-13 capability surface; misroute-refusal waits on rated
    # bank.
    _K_ROLLOUT_TAU: float = 0.0  # DEFERRED cycle-15 — see comment above

    def _try_natural_mode(self, prompt: str) -> AgentResponse | None:
        """Natural-mode K-rollout dispatcher (cycle 11 #00P13c11-DEMO + #03 + #04).

        Routes poetry / philosophy / open-conjecture / lain-voice prompts to
        the `KRolloutComposer` (K=3 rollouts with bind/bundle/greedy strategies;
        best-satisfied wins). Honest M-PROJECTX-013 framing: the agent
        retrieves and composes existing public-domain or project-authored
        fragments by HDC cosine similarity; it does NOT generate novel text.
        Provenance trail per emitted fragment.

        Conservative trigger gate (`_classify_natural_mode_domain`) prevents
        this branch from claiming structured math / physics prompts that
        precede it in the dispatch chain.

        Cycle 11 #00P13c11-04 integration: replaces the cycle-11 #DEMO single-
        walk path with K-rollout iteration. If all K rollouts fail to clear
        `_K_ROLLOUT_TAU`, returns AgentResponse(confidence='refused') with
        the K-rollout's honest-refusal text. v1 tau=0.0 makes refusal rare;
        cycle-11+ calibration could raise the floor.

        Cycle-13 #07e: classifier consults cosine-archetype centroids when the
        keyword phrase set doesn't fire, gated by `_TAU_NATURAL_DISPATCH=0.25`.
        Lifts demo P4 + P5 (which had no keyword match) into the natural-mode
        path without regressing existing keyword-matched routing.
        """
        self._ensure_archetypes_encoded()
        domain = _classify_natural_mode_domain(
            prompt,
            encoder=self._archetype_encoder,
            archetype_hvs=self._natural_mode_archetype_hvs,
            tau_dispatch=_TAU_NATURAL_DISPATCH,
        )
        if domain is None:
            return None
        if ReasoningAgent._k_rollout_composer is None:
            ReasoningAgent._k_rollout_composer = KRolloutComposer()
        result = ReasoningAgent._k_rollout_composer.compose(
            prompt=prompt, domain=domain, max_fragments=5,
            k=self._K_ROLLOUT_K, tau_satisfaction=self._K_ROLLOUT_TAU,
        )
        if result.chosen_strategy is None:
            # All K rollouts fell below tau_satisfaction → honest refusal
            # (cycle-14 #08e reverted — see _K_ROLLOUT_TAU comment for the
            # cycle-15 deferral rationale; at tau=0.0 this branch never fires).
            return AgentResponse(
                domain="open_domain",
                problem_shape=f"natural_mode_k_rollout_refused_{domain}",
                parsed_inputs={"domain_filter": domain, "k": self._K_ROLLOUT_K,
                               "tau_satisfaction": self._K_ROLLOUT_TAU},
                lemma=None,
                answer_text=result.render(),
                confidence="refused",
            )
        return AgentResponse(
            domain="open_domain",
            problem_shape=f"natural_mode_walk_{domain}",
            parsed_inputs={"domain_filter": domain, "k": self._K_ROLLOUT_K,
                           "chosen_strategy": result.chosen_strategy},
            lemma=None,
            answer_text=result.render(),
            confidence="provenance-traced",
        )

    def _try_quadratic(self, prompt: str) -> AgentResponse | None:
        coeffs = _parse_quadratic(prompt)
        if coeffs is None:
            return None
        a, b, c = coeffs
        lemma = solve_quadratic(a, b, c)
        return AgentResponse(
            domain="maths",
            problem_shape="quadratic",
            parsed_inputs={"a": a, "b": b, "c": c},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_char_poly_2x2(self, prompt: str) -> AgentResponse | None:
        matrix = _parse_matrix_2x2(prompt)
        if matrix is None:
            return None
        lemma = expand_characteristic_polynomial_2x2(matrix)
        return AgentResponse(
            domain="maths",
            problem_shape="char_poly_2x2",
            parsed_inputs={"matrix": matrix},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_determinant_3x3(self, prompt: str) -> AgentResponse | None:
        matrix = _parse_matrix_3x3(prompt)
        if matrix is None:
            return None
        lemma = determinant_3x3(matrix)
        return AgentResponse(
            domain="maths",
            problem_shape="determinant_3x3",
            parsed_inputs={"matrix": matrix},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_collatz_verify(self, prompt: str) -> AgentResponse | None:
        N = _parse_collatz_verify(prompt)
        if N is None:
            return None
        lemma = collatz_verify_range(N)
        return AgentResponse(
            domain="maths",
            problem_shape="collatz_verify_range",
            parsed_inputs={"N": N},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_goldbach_verify(self, prompt: str) -> AgentResponse | None:
        N = _parse_goldbach_verify(prompt)
        if N is None:
            return None
        lemma = goldbach_verify_range(N)
        return AgentResponse(
            domain="maths",
            problem_shape="goldbach_verify_range",
            parsed_inputs={"N": N},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_twin_primes(self, prompt: str) -> AgentResponse | None:
        N = _parse_twin_primes(prompt)
        if N is None:
            return None
        lemma = twin_primes_in_range(N)
        return AgentResponse(
            domain="maths",
            problem_shape="twin_primes_in_range",
            parsed_inputs={"N": N},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_mertens_verify(self, prompt: str) -> AgentResponse | None:
        N = _parse_mertens_verify(prompt)
        if N is None:
            return None
        lemma = mertens_bound_verify(N)
        return AgentResponse(
            domain="maths",
            problem_shape="mertens_bound_verify",
            parsed_inputs={"N": N},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_diophantine_binary_quadratic(self, prompt: str) -> AgentResponse | None:
        """Cycle 9 #00P13c9-03 + cycle 10 #00P13c10-02 — Diophantine dispatcher with Pell route.

        Parses (a, b, c, N) for Q(x, y) = a·x² + b·xy + c·y² = N. Cycle 10 #02 adds
        Pell-shape detection: (a=1, b=0, c<0, N=1) ⇒ x² − n·y² = 1 (with n = -c) routes
        to `solve_pell_equation(n, k_max=5)` instead of falling through to
        `solve_binary_quadratic` (which would raise NotImplementedError on the indefinite
        form). Honest M-PROJECTX-013 framing: PASS = "enumerated first 5 positive integer
        solutions via continued-fraction fundamental + recurrence", NOT general Hilbert-10
        decidability. Perfect-square n (degenerate Pell — equation factors as linear-form
        difference) → refused-with-reason via the helper's ValueError. Other non-positive-
        definite forms still fall through to the existing solve_binary_quadratic refusal.
        """
        parsed = _parse_diophantine_binary_quadratic(prompt)
        if parsed is None:
            return None
        a, b, c, N = parsed

        # Cycle 10 #02 — Pell-shape route. x² − n·y² = 1 has a=1, b=0, c=-n, N=1.
        # We require n > 0 (Pell form); perfect-square n is rejected inside the helper
        # because the equation degenerates to (x − √n·y)(x + √n·y) = 1 with only trivial
        # integer solutions. Non-Pell indefinite forms (N ≠ 1, or other shape) keep
        # falling through to solve_binary_quadratic's NotImplementedError path below.
        if a == 1 and b == 0 and c < 0 and N == 1:
            n = -c
            try:
                lemma = solve_pell_equation(n, k_max=5)
            except ValueError as e:
                return AgentResponse(
                    domain="maths",
                    problem_shape="pell_equation_degenerate",
                    parsed_inputs={"a": a, "b": b, "c": c, "N": N, "n": n},
                    lemma=None,
                    answer_text=(
                        f"Notice. Pell-shaped prompt parsed as x² − {n}·y² = 1, but "
                        f"n = {n} is degenerate (perfect square or n ≤ 1): {e} "
                        f"Honest framing — perfect-square n reduces Pell to a linear-form "
                        f"difference with only trivial integer solutions."
                    ),
                    confidence="refused",
                )
            return AgentResponse(
                domain="maths",
                problem_shape="pell_equation",
                parsed_inputs={"a": a, "b": b, "c": c, "N": N, "n": n, "k_max": 5},
                lemma=lemma,
                answer_text=lemma.render(),
                confidence="high",
            )

        try:
            lemma = solve_binary_quadratic(a, b, c, N)
        except NotImplementedError as e:
            return AgentResponse(
                domain="maths",
                problem_shape="diophantine_binary_quadratic_out_of_scope",
                parsed_inputs={"a": a, "b": b, "c": c, "N": N},
                lemma=None,
                answer_text=(
                    f"Notice. Diophantine binary-quadratic prompt parsed as "
                    f"({a})x² + ({b})xy + ({c})y² = {N}, but the substrate refuses: {e} "
                    f"Honest M-PROJECTX-013 framing — Hilbert's 10th (Matiyasevich 1970) "
                    f"proves no general Diophantine algorithm exists; the cycle 9 substrate "
                    f"handles positive-definite (Δ < 0) only, and the cycle 10 #02 Pell "
                    f"extension handles the canonical x² − n·y² = 1 shape — other indefinite "
                    f"shapes remain cycle 11+ territory."
                ),
                confidence="refused",
            )
        return AgentResponse(
            domain="maths",
            problem_shape="diophantine_binary_quadratic",
            parsed_inputs={"a": a, "b": b, "c": c, "N": N},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_free_fall(self, prompt: str) -> AgentResponse | None:
        params = _parse_free_fall(prompt)
        if params is None:
            return None
        h, g = params
        lemma = free_fall_time(h, g)
        return AgentResponse(
            domain="physics",
            problem_shape="free_fall",
            parsed_inputs={"h_meters": h, "g_m_per_s_squared": g},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_definite_integral_quadratic(self, prompt: str) -> AgentResponse | None:
        params = _parse_definite_integral_quadratic(prompt)
        if params is None:
            return None
        coeffs, lower, upper = params
        lemma = polynomial_definite_integral(coeffs, lower, upper)
        return AgentResponse(
            domain="maths",
            problem_shape="definite_integral_quadratic",
            parsed_inputs={"coeffs_descending": coeffs, "lower": lower, "upper": upper},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_definite_integral_x_exp(self, prompt: str) -> AgentResponse | None:
        params = _parse_definite_integral_x_exp(prompt)
        if params is None:
            return None
        lower, upper, c = params
        lemma = definite_integral_x_times_exp(lower, upper, c)
        return AgentResponse(
            domain="maths",
            problem_shape="definite_integral_x_times_exp",
            parsed_inputs={"lower": lower, "upper": upper, "c": c},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_definite_integral_x_sin(self, prompt: str) -> AgentResponse | None:
        params = _parse_definite_integral_x_sin(prompt)
        if params is None:
            return None
        lower, upper, c = params
        lemma = definite_integral_x_times_sin(lower, upper, c)
        return AgentResponse(
            domain="maths",
            problem_shape="definite_integral_x_times_sin",
            parsed_inputs={"lower": lower, "upper": upper, "c": c},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_definite_integral_x_cos(self, prompt: str) -> AgentResponse | None:
        params = _parse_definite_integral_x_cos(prompt)
        if params is None:
            return None
        lower, upper, c = params
        lemma = definite_integral_x_times_cos(lower, upper, c)
        return AgentResponse(
            domain="maths",
            problem_shape="definite_integral_x_times_cos",
            parsed_inputs={"lower": lower, "upper": upper, "c": c},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_definite_integral_xtrig_usub(self, prompt: str) -> AgentResponse | None:
        params = _parse_definite_integral_xtrig_usub(prompt)
        if params is None:
            return None
        lower, upper, trig_fn = params
        lemma = definite_integral_xtrig_via_usub(lower, upper, trig_fn=trig_fn)
        return AgentResponse(
            domain="maths",
            problem_shape=f"definite_integral_xtrig_via_usub_{trig_fn}",
            parsed_inputs={"lower": lower, "upper": upper, "trig_fn": trig_fn},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_residue_theorem(self, prompt: str) -> AgentResponse | None:
        params = _parse_residue_unit_quadratic(prompt)
        if params is None:
            return None
        a, c = params
        lemma = residue_theorem_unit_quadratic(a, c)
        return AgentResponse(
            domain="maths",
            problem_shape="residue_theorem_unit_quadratic",
            parsed_inputs={"a": a, "c": c},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_relativistic_momentum(self, prompt: str) -> AgentResponse | None:
        params = _parse_relativistic_momentum(prompt)
        if params is None:
            return None
        m, v, c = params
        lemma = relativistic_momentum(m, v, c)
        return AgentResponse(
            domain="physics",
            problem_shape="relativistic_momentum",
            parsed_inputs={"m_kg": m, "v_m_per_s": v, "c_m_per_s": c},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_projectile_horizontal(self, prompt: str) -> AgentResponse | None:
        params = _parse_projectile_horizontal(prompt)
        if params is None:
            return None
        h, v_h, g = params
        lemma = projectile_horizontal_range(h, v_h, g)
        return AgentResponse(
            domain="physics",
            problem_shape="projectile_horizontal_range",
            parsed_inputs={"h_meters": h, "v_horizontal_m_per_s": v_h, "g_m_per_s_squared": g},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_doppler_shift(self, prompt: str) -> AgentResponse | None:
        params = _parse_doppler_shift(prompt)
        if params is None:
            return None
        wavelength_emit, beta, approaching = params
        lemma = relativistic_doppler_shift(wavelength_emit, beta, approaching=approaching)
        return AgentResponse(
            domain="physics",
            problem_shape="relativistic_doppler_shift",
            parsed_inputs={"wavelength_emit_nm": wavelength_emit, "beta": beta, "approaching": approaching},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_pendulum(self, prompt: str) -> AgentResponse | None:
        params = _parse_pendulum(prompt)
        if params is None:
            return None
        L, g, theta_0 = params
        if theta_0 is None:
            # Small-angle: physics-002 / physics-009 shape
            lemma = pendulum_period(L, g)
            return AgentResponse(
                domain="physics",
                problem_shape="pendulum_small_angle",
                parsed_inputs={"L_meters": L, "g_m_per_s_squared": g},
                lemma=lemma,
                answer_text=lemma.render(),
                confidence="high",
            )
        # Large-angle: physics-010 shape (elliptic-integral series)
        lemma = large_angle_pendulum_period(L, g, theta_0)
        return AgentResponse(
            domain="physics",
            problem_shape="pendulum_large_angle",
            parsed_inputs={"L_meters": L, "g_m_per_s_squared": g, "theta_0_rad": theta_0},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )

    def _try_first_order_ode(self, prompt: str) -> AgentResponse | None:
        params = _parse_first_order_ode(prompt)
        if params is None:
            return None
        k, y_0, x_target, x_0 = params
        lemma = first_order_linear_ode_exp_solution(k, y_0, x_target, x_0=x_0)
        return AgentResponse(
            domain="maths",
            problem_shape="first_order_linear_ode_exp",
            parsed_inputs={"k": k, "y_0": y_0, "x_target": x_target, "x_0": x_0},
            lemma=lemma,
            answer_text=lemma.render(),
            confidence="high",
        )
