"""From-scratch symbolic reasoning primitives — Project X Phase 13 cycle 2 (#00P13c2-02).

Lemma chain dataclass + derivation step recorder + closed-form arithmetic primitives
(quadratic solver + 2x2 characteristic polynomial expansion).

Organic-thesis compliance is load-bearing here:
- NO sympy (default-DENY per docs/MANIFESTO.md § Standing orders + DO_THIS_NEXT cycle 2
  encoded decision). sympy IS a symbolic-AI library — counts as "borrowing other tools"
  against the post-transformer thesis. Closed-form arithmetic uses Python stdlib `math`,
  which is a calculator, not a symbolic-AI substrate.
- NO numpy in substrate (the agent's reasoning side). The cycle 2 D3 verifier MAY use
  numpy in the sandbox-side verification SCRIPT it generates, but that's verifier-tooling,
  not substrate-tooling — the script runs in the sandbox subprocess against the agent's
  hand-rolled derivation, confirming correctness.
- NO LLM wrappers anywhere. Output is template-string composition of recorded steps.

This module ships the SUBSTRATE primitives only. The Project X Raphael agent (NOT the
Claude Code Raphael builder) consumes these primitives at inference time to build
gradeable derivations. The verifier (#00P13c2-03) closes the loop by running an
independent numerical computation in the cycle 1 sandbox.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DerivationStep:
    """One step in a Lemma's derivation chain.

    Each step records OPERATION (what computational primitive ran), INPUTS it consumed,
    OUTPUT it produced, and JUSTIFICATION (the WHY this step is valid given prior steps).
    Together these compose a proof-shape audit trail readable as a Raphael-voice
    derivation rendering — see Lemma.render().
    """

    step_index: int
    operation: str
    inputs: dict[str, Any]
    output: Any
    justification: str


@dataclass
class Lemma:
    """A complete claim + derivation chain + verification metadata.

    The agent populates `derivation_steps` and `actual_value` via primitives like
    `solve_quadratic`. The verifier (#00P13c2-03) populates `match` after running an
    independent sandbox computation against `expected_value` (sourced from a ladder
    entry's `auto_grade.expected_*` field).
    """

    id: str
    claim: str
    derivation_steps: list[DerivationStep] = field(default_factory=list)
    verification_method: str = "numerical_close"
    expected_value: Any = None
    actual_value: Any = None
    tolerance: float = 0.001
    match: bool | None = None

    def add_step(
        self,
        operation: str,
        inputs: dict[str, Any],
        output: Any,
        justification: str,
    ) -> DerivationStep:
        step = DerivationStep(
            step_index=len(self.derivation_steps),
            operation=operation,
            inputs=inputs,
            output=output,
            justification=justification,
        )
        self.derivation_steps.append(step)
        return step

    def render(self) -> str:
        """Render the derivation as a Raphael-voice proof-shape string.

        Output mimics the hand-crafted `raphael_response` shape in the ladder JSONL
        (declarative "Notice." prelude + numbered steps with justification + final
        "Affirmative — <actual_value>" close). This matters for D4 baseline-attempt:
        the agent's substrate-generated output must read like the existing exemplars
        for builder rubric grading to compare apples-to-apples.
        """
        lines = [f"Notice. {self.claim}", ""]
        for step in self.derivation_steps:
            lines.append(f"Step {step.step_index + 1} — {step.operation}: {step.justification}")
            lines.append(f"  Inputs: {step.inputs}")
            lines.append(f"  Output: {step.output}")
        lines.append("")
        lines.append(f"Affirmative — {self.actual_value}")
        return "\n".join(lines)


def solve_quadratic(a: float, b: float, c: float, lemma_id: str = "quadratic") -> Lemma:
    """Solve ax² + bx + c = 0 via discriminant + closed-form root formula.

    Hand-rolled — uses only `math.sqrt` (Python stdlib calculator, not a symbolic-AI
    library). Returns a Lemma with the full 3-step derivation chain (discriminant →
    sqrt → root_pair) so D4 grading sees the proof-shape, not just the numerical roots.

    Coverage: real-distinct + real-repeated roots (discriminant >= 0). Complex-conjugate
    roots (discriminant < 0) are out of cycle 2 minimum-viable scope and raise
    NotImplementedError — surfacing the limit explicitly is more honest than silently
    returning a tuple of (real, imag) pairs and pretending the substrate handles them.
    """
    if a == 0:
        raise ValueError("not a quadratic — coefficient a is zero")

    lemma = Lemma(
        id=lemma_id,
        claim=f"Solve {a}x² + {b}x + {c} = 0 for x.",
        verification_method="numerical_close",
    )

    discriminant = b * b - 4 * a * c
    lemma.add_step(
        operation="discriminant",
        inputs={"a": a, "b": b, "c": c},
        output=discriminant,
        justification=f"D = b² - 4ac = ({b})² - 4·{a}·{c} = {discriminant}; sign determines root regime",
    )

    if discriminant < 0:
        raise NotImplementedError(
            f"complex-conjugate roots beyond cycle 2 scope (discriminant = {discriminant})",
        )

    sqrt_d = math.sqrt(discriminant)
    lemma.add_step(
        operation="sqrt",
        inputs={"discriminant": discriminant},
        output=sqrt_d,
        justification=f"√D = √{discriminant} = {sqrt_d}",
    )

    root_pos = (-b + sqrt_d) / (2 * a)
    root_neg = (-b - sqrt_d) / (2 * a)
    roots = sorted([root_pos, root_neg])
    lemma.add_step(
        operation="root_pair",
        inputs={"a": a, "b": b, "sqrt_d": sqrt_d},
        output=roots,
        justification=f"x = (-b ± √D) / 2a = ({-b} ± {sqrt_d}) / {2 * a} → {roots}",
    )

    lemma.actual_value = roots
    return lemma


def expand_characteristic_polynomial_2x2(
    matrix: list[list[float]],
    lemma_id: str = "char_poly_2x2",
) -> Lemma:
    """Compute 2x2 matrix eigenvalues via characteristic polynomial λ² - tr(A)λ + det(A) = 0.

    Reuses `solve_quadratic` — establishes the substrate's compositional discipline:
    each new primitive composes prior primitives rather than reaching for a numerical
    library. Hand-rolled trace + determinant; no `numpy.linalg.eigvals`.

    Composition matters because cycle 3+ extensions (e.g., 3x3 characteristic polynomial,
    Newton's method for higher-degree roots) build on these primitives. If we had imported
    numpy here, the substrate would be a numpy-wrapper rather than an organic computation
    layer — and the thesis would be silently violated.
    """
    if len(matrix) != 2 or any(len(row) != 2 for row in matrix):
        raise ValueError("matrix must be 2x2")

    a, b = matrix[0]
    c, d = matrix[1]

    lemma = Lemma(
        id=lemma_id,
        claim=f"Find eigenvalues of [[{a}, {b}], [{c}, {d}]] via characteristic polynomial.",
        verification_method="numerical_close",
    )

    trace = a + d
    lemma.add_step(
        operation="trace",
        inputs={"matrix": matrix},
        output=trace,
        justification=f"tr(A) = a + d = {a} + {d} = {trace}",
    )

    det = a * d - b * c
    lemma.add_step(
        operation="det",
        inputs={"matrix": matrix},
        output=det,
        justification=f"det(A) = ad - bc = {a}·{d} - {b}·{c} = {det}",
    )

    poly_a, poly_b, poly_c = 1.0, -trace, det
    lemma.add_step(
        operation="char_poly_coeffs",
        inputs={"trace": trace, "det": det},
        output={"a": poly_a, "b": poly_b, "c": poly_c},
        justification=f"det(A - λI) = λ² - tr(A)λ + det(A) = λ² - {trace}λ + {det} = 0",
    )

    quad_lemma = solve_quadratic(poly_a, poly_b, poly_c, lemma_id=f"{lemma_id}_quadratic")
    eigenvalues = quad_lemma.actual_value
    lemma.add_step(
        operation="solve_via_quadratic",
        inputs={"polynomial": f"λ² - {trace}λ + {det}"},
        output=eigenvalues,
        justification=f"Eigenvalues = roots of characteristic polynomial = {eigenvalues}",
    )

    lemma.actual_value = eigenvalues
    return lemma
