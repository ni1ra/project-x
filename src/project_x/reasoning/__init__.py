"""Project X Raphael reasoning substrate — cycle 2+ (Phase 13 #00P13c2-02).

The AGENT's reasoning layer (Project X Raphael), distinct from Claude Code Raphael
(the BUILDER writing this code). The agent USES these primitives to construct
verifiable derivations; the builder writes the substrate but does not run inference
through it.

Cycle 2 ships `symbolic.py` — Lemma + DerivationStep dataclasses + closed-form
arithmetic primitives (`solve_quadratic`, `expand_characteristic_polynomial_2x2`).
Cycle 2 D3 ships `verifier.py` — sandbox-bound numerical verifier closing the loop
through the cycle 1 sandbox tools.

Organic-thesis compliance: NO sympy (default-DENY), NO numpy in substrate-side code
(verifier may use numpy in sandbox-side script generation), NO pretrained transformer
derivatives anywhere. From-scratch primitives only.
"""

from project_x.reasoning.symbolic import (
    DerivationStep,
    Lemma,
    expand_characteristic_polynomial_2x2,
    solve_quadratic,
)
from project_x.reasoning.verifier import numerical_verify

__all__ = [
    "DerivationStep",
    "Lemma",
    "expand_characteristic_polynomial_2x2",
    "numerical_verify",
    "solve_quadratic",
]
