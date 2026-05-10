"""Anti-cheat mechanism — Project X Phase 13 cycle 4 (#00P13c4-24).

Mitigates leak surfaces 1+5 (substrate primitives hardcode the formula; agent
"attempt" runs a function whose body IS the answer) identified in
`docs/artifacts/PHASE_13_ANTICHEAT_AUDIT.md`. Three complementary mechanisms,
all rule-based + thesis-compliant (no LLM calls, no pretrained-transformer
derivatives at this layer):

  D — Surrogate-prompt regression: substrate must produce correct answer on
      canonical input AND on N rule-based surrogate variants. `AntiCheatProbe`
      pairs canonical with surrogates + an input-output predicate.
  E — Differential capability test: operationalized memorization-vs-reasoning
      gap. `memorization_signal = 1 - surrogate_pass_rate`; 0.0 = genuine
      capability (all surrogates pass), 1.0 = canonical-only (memorization or
      overfit signal).
  F — Divergent-verifier-path lives in `reasoning/verifier.py` — Newton's-method
      + Vieta-deflation second opinion for quadratics. Imported here only for
      the optional cross-verification helper at the bottom of this module.

The mechanism gates cycle 4 #19 substrate physics Tier 2 + #20 substrate-driven
attempt — both Surface-1/5 class. A substrate primitive passes the anti-cheat
gate iff `memorization_signal == 0.0` across its probe (all surrogates pass the
input-output predicate). Substrate that hardcodes the canonical answer fails
because the hardcoded output doesn't satisfy the canonical identity (e.g.,
a·r² + b·r + c ≈ 0) on surrogate inputs.

Honest framing (advisor carry-into-#24, from #23 audit pre-commit):
  - **Surrogate-author independence is ABSENT in this cycle.** Surrogates are
    Claude-authored via rule-based parameter substitution. `AntiCheatProbe.
    surrogate_author` documents the authorship. Cycle 5+ may introduce
    lain-authored or textbook-derived surrogates for stronger anti-cheat
    strength (parallel to Surface 3's threshold-grader independence absence).
  - **Per-criterion floor gates remain OUT OF SCOPE for cycle 4.** Path B
    grades use aggregate-only thresholds (4.0/5 weighted); a hypothetical
    uniformly-mediocre 4.01 still PASSES. Cycle 5+ when programmatic-rubric
    criteria (audit Candidate B) ship.

Organic-thesis compliance: rule-based generators only. NO LLM calls. The
predicate functions verify input-output appropriateness via closed-form
identities the substrate must satisfy — independent of substrate's internal
computation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from project_x.reasoning.symbolic import Lemma


@dataclass
class AntiCheatProbe:
    """A probe binding canonical input + surrogate variants + answer-shape predicate.

    The predicate verifies INPUT-OUTPUT APPROPRIATENESS — not just output shape.
    A fake substrate that hardcodes the canonical answer would pass a shape-only
    check (the hardcoded value IS a list-of-2-floats); the input-output
    predicate catches it because the hardcoded answer fails the canonical
    identity (a·r² + b·r + c ≈ 0 for quadratic roots) on surrogate inputs.
    """

    probe_id: str
    canonical_inputs: tuple
    surrogate_inputs: list[tuple]
    answer_predicate: Callable[[tuple, Any], bool]
    surrogate_author: str = "builder (rule-based)"
    notes: str = ""


@dataclass
class CapabilityTestResult:
    """Output of `differential_capability_test`. `memorization_signal` is the metric.

    Interpretation (only meaningful when `canonical_match` is True):
      0.0 → all surrogates passed (genuine capability)
      1.0 → canonical passes but no surrogate does (maximum memorization signal)
      intermediate → partial overfit / partial capability
    """

    probe_id: str
    canonical_match: bool
    surrogate_matches: list[bool]
    surrogate_pass_rate: float
    memorization_signal: float
    notes: str = ""


def differential_capability_test(
    substrate_fn: Callable[..., Lemma],
    probe: AntiCheatProbe,
) -> CapabilityTestResult:
    """Run substrate on canonical + each surrogate; compute memorization signal.

    Substrate raising on a surrogate (e.g., NotImplementedError on complex
    roots) counts as a non-match, not a test error — the test characterizes
    behavior across the probe, not crash on edge regimes.
    """
    canonical_match = _probe_call_matches(
        substrate_fn, probe.canonical_inputs, probe.answer_predicate,
    )
    surrogate_matches = [
        _probe_call_matches(substrate_fn, inputs, probe.answer_predicate)
        for inputs in probe.surrogate_inputs
    ]
    n = len(surrogate_matches)
    surrogate_pass_rate = sum(int(m) for m in surrogate_matches) / n if n > 0 else 0.0
    # memorization_signal is only meaningful when canonical itself passes; if
    # the substrate doesn't even handle canonical, "memorization" isn't the
    # diagnosis — substrate is broken. Signal collapses to 0.0 in that case
    # (test author should look at canonical_match=False separately).
    memorization_signal = (1.0 - surrogate_pass_rate) if canonical_match else 0.0
    return CapabilityTestResult(
        probe_id=probe.probe_id,
        canonical_match=canonical_match,
        surrogate_matches=surrogate_matches,
        surrogate_pass_rate=surrogate_pass_rate,
        memorization_signal=memorization_signal,
        notes=probe.notes,
    )


def _probe_call_matches(
    fn: Callable[..., Lemma],
    inputs: tuple,
    predicate: Callable[[tuple, Any], bool],
) -> bool:
    """Call substrate; return True iff result satisfies the predicate.

    Defensive: substrate raising → False (graceful degradation, not test
    error); non-Lemma return → False; missing `actual_value` → False.
    """
    try:
        lemma = fn(*inputs)
    except Exception:
        return False
    if not isinstance(lemma, Lemma) or lemma.actual_value is None:
        return False
    return predicate(inputs, lemma.actual_value)


# Surrogate generators — rule-based, deterministic, thesis-compliant.
# Each generator produces N variants preserving the canonical's regime
# (real-discriminant quadratics; real-eigenvalue 2x2 matrices).

def generate_surrogate_quadratic(
    canonical: tuple[float, float, float], n: int = 3,
) -> list[tuple[float, float, float]]:
    """Generate `n` surrogate quadratics preserving real-discriminant regime.

    Each surrogate has a DIFFERENT root pair (not a rescaling of canonical
    roots — rescaling would be trivially solvable via the same function call
    modulo a constant; the test would have no discriminating power).

    Patterns iterate a fixed family; first `n` with discriminant > 0 are
    returned. Raises if fewer than `n` real-discriminant surrogates exist in
    the pattern family (signals canonical is in an edge regime; expand
    patterns or skip the probe).
    """
    a, b, c = canonical
    if a == 0:
        raise ValueError("canonical 'a' coefficient must be non-zero")
    patterns: list[tuple[float, float, float]] = [
        (a + 4, b - 8, c * 2 - 1),
        (a * 2, b + 5, c - 3),
        (a + 1, b - 1, c - 5),
        (a - 1 if a > 1 else a + 2, -b, c),
        (a + 7, b - 11, c + 1),
        (1, b - a, c + b),
        (a * 3, b + 7, c * 0.5 - 2),
    ]
    out: list[tuple[float, float, float]] = []
    for new_a, new_b, new_c in patterns:
        if new_a == 0:
            continue
        discriminant = new_b * new_b - 4 * new_a * new_c
        if discriminant > 0:
            out.append((new_a, new_b, new_c))
            if len(out) == n:
                return out
    raise RuntimeError(
        f"generator exhausted patterns; only {len(out)}/{n} real-discriminant "
        f"surrogates produced from canonical {canonical}",
    )


def generate_surrogate_char_poly_2x2(
    canonical: list[list[float]], n: int = 3,
) -> list[list[list[float]]]:
    """Generate `n` surrogate 2x2 matrices preserving real-eigenvalue regime.

    Real eigenvalues iff `trace² - 4·det > 0`. Patterns vary entries while
    preserving the inequality. Each surrogate has a DIFFERENT eigenvalue pair.
    """
    a, b = canonical[0]
    c, d = canonical[1]
    patterns: list[list[list[float]]] = [
        [[a + 2, b], [c, d + 1]],
        [[a, b - 1], [c, d + 3]],
        [[a + 5, b + 2], [c - 1, d]],
        [[a * 2, b], [c, d - 1]],
        [[1, b + 1], [c, d]],
        [[a + 3, b], [c + 1, d]],
    ]
    out: list[list[list[float]]] = []
    for matrix in patterns:
        ta, tb = matrix[0]
        tc, td = matrix[1]
        trace = ta + td
        det = ta * td - tb * tc
        discriminant = trace * trace - 4 * det
        if discriminant > 0:
            out.append(matrix)
            if len(out) == n:
                return out
    raise RuntimeError(
        f"generator exhausted patterns; only {len(out)}/{n} real-eigenvalue "
        f"surrogates produced from canonical {canonical}",
    )


# Predicate functions — verify input-output appropriateness via closed-form
# identities the substrate must satisfy. These IDENTITIES are independent of
# substrate's internal computation: a fake substrate hardcoding the canonical
# answer fails the predicate on surrogate inputs because the canonical answer
# doesn't satisfy the surrogate's identity.

def quadratic_roots_predicate(inputs: tuple, output: Any) -> bool:
    """Output is a sorted 2-list of floats r with a·r² + b·r + c ≈ 0 for each r.

    Tolerance scales with input magnitude so coefficient-dominated terms (e.g.,
    a·r² when a is large) don't false-negative on legitimate float drift.
    """
    a, b, c = inputs
    if not isinstance(output, list) or len(output) != 2:
        return False
    if not all(isinstance(r, (int, float)) for r in output):
        return False
    if output[0] > output[1]:
        return False
    tolerance = 1e-4 * max(abs(a), abs(b), abs(c), 1.0)
    return all(abs(a * r * r + b * r + c) < tolerance for r in output)


def char_poly_2x2_eigenvalues_predicate(inputs: tuple, output: Any) -> bool:
    """Output is a sorted 2-list of eigenvalues satisfying Vieta (trace, det).

    Independent identity: λ₁ + λ₂ = trace(A); λ₁·λ₂ = det(A). Tolerance scales
    with the magnitude of the canonical invariants.
    """
    matrix = inputs[0]
    if not isinstance(output, list) or len(output) != 2:
        return False
    if not all(isinstance(e, (int, float)) for e in output):
        return False
    if output[0] > output[1]:
        return False
    a, b = matrix[0]
    c, d = matrix[1]
    expected_trace = a + d
    expected_det = a * d - b * c
    actual_trace = output[0] + output[1]
    actual_det = output[0] * output[1]
    tolerance = 1e-4 * max(abs(expected_trace), abs(expected_det), 1.0)
    return (
        abs(actual_trace - expected_trace) < tolerance
        and abs(actual_det - expected_det) < tolerance
    )
