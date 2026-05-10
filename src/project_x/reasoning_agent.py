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

import re
from dataclasses import dataclass
from typing import Any

from project_x.reasoning.symbolic import Lemma, solve_quadratic


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
        # Maths quadratic — covers maths-001/007/008 on the current ladder.
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
