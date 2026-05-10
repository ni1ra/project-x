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
from project_x.reasoning.physics import (
    free_fall_time,
    large_angle_pendulum_period,
    pendulum_period,
    relativistic_momentum,
)
from project_x.reasoning.symbolic import (
    Lemma,
    expand_characteristic_polynomial_2x2,
    solve_quadratic,
)


@dataclass
class AgentResponse:
    """Output of `ReasoningAgent.process()`.

    `lemma` is None when the parser couldn't identify a problem-shape; `answer_text`
    in that case carries a refusal-with-reason rather than an attempted-answer. Honest
    failure is preferred over confabulation per M-PROJECTX-013 measure-don't-claim.
    """

    domain: str  # "maths" / "physics" / "unrecognized"
    problem_shape: str  # "quadratic" / "char_poly_2x2" / "free_fall" / ... / "unrecognized"
    parsed_inputs: dict[str, Any]
    lemma: Lemma | None
    answer_text: str
    confidence: str  # "high" (parsed cleanly, substrate ran) / "low" (parser uncertain) / "refused" (no match)


# Free-fall parser: extracts (h, g) from a drop/fall prompt.
# Robust to phrasing variation observed across physics-001 ("height of 80 m ... g = 9.81")
# and physics-008 ("fall from 50 m ... g = 3.71"). Two-gate filter: prompt must name
# drop/fall/dropped AND match both height + gravity patterns.
_HEIGHT_PATTERN = re.compile(r"(?:height of|from)\s+(\d+\.?\d*)\s*m\b", re.IGNORECASE)
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


# Pendulum length parser: matches "L = 1.0 m" or "length L = 0.5 m" forms.
_LENGTH_PATTERN = re.compile(r"L\s*=\s*(\d+\.?\d*)\s*m\b", re.IGNORECASE)

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


# Quadratic regex: matches `a x^2 [+-] b x [+-] c = 0` with optional whitespace and *.
# Group 1 = a-coefficient string (may be empty for implicit 1, or "-" for implicit -1).
# Group 2 = b-coefficient with leading sign and whitespace (e.g., "- 14" or "+ 4").
# Group 3 = c-constant with leading sign and whitespace (e.g., "- 5" or "+ 6").
# The character class for digits/dot accepts both integer and decimal coefficients.
_QUADRATIC_PATTERN = re.compile(
    r"(-?\d*\.?\d*)\s*\*?\s*x\^2"  # a · x²  (a optional; "-" → -1, "" → 1)
    r"\s*([+-]\s*\d*\.?\d*)\s*\*?\s*x"  # ± b · x  (b coefficient with sign)
    r"\s*([+-]\s*\d*\.?\d*)\s*=\s*0",  # ± c = 0  (c constant with sign)
)


def _parse_signed_coefficient(s: str, *, implicit_one: bool = True) -> float:
    """Normalize a coefficient string from regex match into a float.

    Handles the empty-string-means-1 convention (e.g., `x^2` → a=1, not a=0) when
    `implicit_one=True`. The standalone `-` (no digits) → -1 if `implicit_one=True`,
    raises ValueError otherwise. Whitespace inside `+ 14` style strings is stripped.
    """
    s = s.strip().replace(" ", "")
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

    Public API: `process(prompt: str) -> AgentResponse`. Routes to a dispatcher per
    problem-shape; first matching shape wins. Honest failure mode (`AgentResponse`
    with `confidence='refused'`) when no parser matches — better than confabulation.

    Cycle 7 minimum-viable: maths quadratic only. Cycle 7+ extends by adding
    per-shape `_try_<shape>()` methods + adding them to the `process` dispatch chain.
    """

    def process(self, prompt: str) -> AgentResponse:
        """Attempt to solve `prompt` by dispatching to a matched problem-shape parser."""
        # Maths residue theorem — covers maths-003. Specific keyword gate.
        response = self._try_residue_theorem(prompt)
        if response is not None:
            return response

        # Maths definite integral (quadratic) — covers maths-010. Checked AFTER residue theorem
        # so residue-form integrals don't accidentally route here (residue check excludes those anyway).
        response = self._try_definite_integral_quadratic(prompt)
        if response is not None:
            return response

        # Physics relativistic momentum — covers physics-003/011. Specific keyword.
        response = self._try_relativistic_momentum(prompt)
        if response is not None:
            return response

        # Physics pendulum (small-angle + large-angle) — covers physics-002/009/010.
        # Pendulum-keyword gate.
        response = self._try_pendulum(prompt)
        if response is not None:
            return response

        # Physics free-fall — covers physics-001/008. Domain-keyword gate.
        response = self._try_free_fall(prompt)
        if response is not None:
            return response

        # Maths 2x2 eigenvalues — covers maths-002/009. Eigenvalue-naming gate.
        response = self._try_char_poly_2x2(prompt)
        if response is not None:
            return response

        # Maths quadratic — covers maths-001/007/008.
        response = self._try_quadratic(prompt)
        if response is not None:
            return response

        # No parser matched. Honest refusal with reason.
        return AgentResponse(
            domain="unrecognized",
            problem_shape="unrecognized",
            parsed_inputs={},
            lemma=None,
            answer_text=(
                "Notice. Prompt did not match any currently-supported problem-shape. "
                "Cycle 7 minimum-viable scope is maths quadratic; other shapes "
                "(eigenvalues, integrals, ODEs, physics primitives) pending cycle 7+ "
                "extension. Honest failure preferred over confabulation per "
                "M-PROJECTX-013 measure-don't-claim."
            ),
            confidence="refused",
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
