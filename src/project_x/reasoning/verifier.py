"""Sandbox-bound numerical verifier — Project X Phase 13 cycle 2 (#00P13c2-03).

Closes the verification loop on the symbolic substrate (#00P13c2-02). Given an agent-
constructed Lemma whose `derivation_steps` end at some `actual_value`, the verifier
generates an INDEPENDENT Python script computing the same primitive via stdlib math,
writes it to the cycle 1 sandbox via `_tool_write_file_sandbox`, runs it via
`_tool_run_python_sandbox`, parses the printed result, and sets `lemma.match` against
the lemma's `expected_value` (or `actual_value` as consistency-check fallback).

The independence matters: a buggy substrate must be falsifiable. If `solve_quadratic`
silently flips the sign of the discriminant somewhere, the substrate-side `actual_value`
would be wrong AND the verifier (running the same substrate) would also be wrong —
collusion. To prevent collusion, the verifier's sandbox script does NOT import the
substrate; it re-derives the primitive's computation using only stdlib `math`. Within
cycle 2 minimum-viable scope this means the sandbox script duplicates the closed-form
formulas; cycle 3+ can add stronger second opinions (e.g. `numpy.linalg.eigvals` for
maths-002 cross-check, since numpy in the sandbox subprocess is not a substrate import).

Output parsing uses `ast.literal_eval` rather than `eval` — the sandbox subprocess'
stdout could in principle contain anything (assert errors, stack traces), so the parser
must refuse to execute arbitrary code even from a trusted source.
"""

from __future__ import annotations

import ast
import re
from typing import Any

from project_x.experiments.semantic_memory_agent import (
    _tool_run_python_sandbox,
    _tool_write_file_sandbox,
)
from project_x.reasoning.symbolic import Lemma


def numerical_verify(
    lemma: Lemma,
    expected_value: Any | None = None,
    tolerance: float | None = None,
) -> Lemma:
    """Run sandbox-side independent computation, set `lemma.match`, return lemma.

    Verification path is shaped by `lemma.derivation_steps[0].operation`:
    - `"discriminant"` → reuses `solve_quadratic` shape; sandbox runs (-b ± √D)/2a
      via stdlib math, sorts roots ascending, compares to `expected_value` or to
      `actual_value` as consistency check.
    - `"trace"` → reuses `expand_characteristic_polynomial_2x2` shape; sandbox runs
      eigenvalues via quadratic formula on the characteristic polynomial λ² - tr·λ + det.
    - any other operation → match=False, no exception raised. Cycle 3+ extends the
      supported operation set as new substrate primitives ship.

    The lemma is mutated in place AND returned (convenience for chaining).
    """
    if expected_value is not None:
        lemma.expected_value = expected_value
    if tolerance is not None:
        lemma.tolerance = tolerance

    if not lemma.derivation_steps:
        lemma.match = False
        return lemma

    first_step = lemma.derivation_steps[0]
    operation = first_step.operation

    if operation == "discriminant":
        a, b, c = (
            first_step.inputs["a"],
            first_step.inputs["b"],
            first_step.inputs["c"],
        )
        script = _quadratic_verification_script(a, b, c)
    elif operation == "trace":
        matrix = first_step.inputs["matrix"]
        script = _eigenvalue_2x2_verification_script(matrix)
    else:
        # Unsupported operation → graceful False; cycle 3+ extends supported ops.
        lemma.match = False
        return lemma

    write_result = _tool_write_file_sandbox("verify.py", script)
    if "tool error" in write_result:
        lemma.match = False
        return lemma

    run_result = _tool_run_python_sandbox(script, timeout=10)

    parsed = _parse_sandbox_output(run_result)
    if parsed is None:
        lemma.match = False
        return lemma

    reference = (
        lemma.expected_value if lemma.expected_value is not None else lemma.actual_value
    )
    lemma.match = _close_enough(parsed, reference, lemma.tolerance, lemma.verification_method)
    return lemma


def _quadratic_verification_script(a: float, b: float, c: float) -> str:
    """Generate a stdlib-only quadratic-root-finding Python script.

    The script writes a single VERIFY_RESULT line so the parser has a deterministic
    target. Negative discriminant prints a sentinel string so the parser returns
    None gracefully (substrate also raises NotImplementedError on D<0; the parser
    sentinel is the correlated cycle-2-scope check from the verifier side).
    """
    return (
        "import math\n"
        f"a, b, c = {a}, {b}, {c}\n"
        "D = b * b - 4 * a * c\n"
        "if D < 0:\n"
        "    print('VERIFY_RESULT:NEGATIVE_DISCRIMINANT')\n"
        "else:\n"
        "    sqrtD = math.sqrt(D)\n"
        "    r1 = (-b + sqrtD) / (2 * a)\n"
        "    r2 = (-b - sqrtD) / (2 * a)\n"
        "    roots = sorted([r1, r2])\n"
        "    print('VERIFY_RESULT:' + repr(roots))\n"
    )


def _quadratic_newton_verification_script(a: float, b: float, c: float) -> str:
    """Generate a Newton's-method + Vieta-deflation script — divergent verifier path.

    Phase 13 cycle 4 #00P13c4-24 — Surface 2 mitigation. The closed-form verifier
    (`_quadratic_verification_script`) shares its formula with substrate's
    `solve_quadratic` — a same-bug collusion vector. Newton-Raphson iterates
    `f(x) = ax² + bx + c` from x=1.0 until |f(x)| < 1e-12 OR 500 iterations.
    Vieta's formula (r₁ + r₂ = -b/a) deflates to the second root without
    repeating the closed-form. Different algorithm, same answer space — if both
    verifiers agree with substrate, the result is robust against shared
    closed-form bugs.

    Negative discriminant prints `NEGATIVE_DISCRIMINANT` sentinel; the closed-form
    verifier uses the same sentinel so the parser handles either uniformly.
    """
    return (
        "import math\n"
        f"a, b, c = {a}, {b}, {c}\n"
        "D = b * b - 4 * a * c\n"
        "if D < 0:\n"
        "    print('VERIFY_RESULT:NEGATIVE_DISCRIMINANT')\n"
        "else:\n"
        "    def f(x): return a*x*x + b*x + c\n"
        "    def df(x): return 2*a*x + b\n"
        "    # Newton-Raphson from x=1.0; converges to whichever real root is closer.\n"
        "    # Damped restart on near-zero derivative (vertex point) to avoid div-zero.\n"
        "    x = 1.0\n"
        "    for _ in range(500):\n"
        "        fx = f(x)\n"
        "        if abs(fx) < 1e-12:\n"
        "            break\n"
        "        dfx = df(x)\n"
        "        if abs(dfx) < 1e-12:\n"
        "            x = x + 0.5\n"
        "            continue\n"
        "        x = x - fx / dfx\n"
        "    r1 = x\n"
        "    # Vieta: r1 + r2 = -b/a, so r2 = -b/a - r1. No closed-form repeat.\n"
        "    r2 = -b / a - r1\n"
        "    roots = sorted([r1, r2])\n"
        "    print('VERIFY_RESULT:' + repr(roots))\n"
    )


def verify_quadratic_via_newton(
    a: float,
    b: float,
    c: float,
    expected: list[float],
    tolerance: float = 0.001,
) -> bool:
    """Run Newton's-method verification in sandbox; compare to expected roots.

    Divergent from `numerical_verify` (closed-form path). If both agree with
    substrate, the result is robust against shared closed-form bugs. Returns
    False on negative discriminant, sandbox failure, or root mismatch.
    """
    script = _quadratic_newton_verification_script(a, b, c)
    write_result = _tool_write_file_sandbox("verify_newton.py", script)
    if "tool error" in write_result:
        return False
    run_result = _tool_run_python_sandbox(script, timeout=10)
    parsed = _parse_sandbox_output(run_result)
    if parsed is None:
        return False
    return _close_enough(parsed, expected, tolerance, "numerical_close")


def _eigenvalue_2x2_verification_script(matrix: list[list[float]]) -> str:
    """Generate a stdlib-only 2x2-eigenvalue Python script.

    Computes eigenvalues via the characteristic polynomial λ² - tr·λ + det = 0
    (closed-form quadratic). Independent of substrate's
    `expand_characteristic_polynomial_2x2` re-implementation: substrate composes
    `solve_quadratic` (own primitive); sandbox re-derives the formula via stdlib —
    different code paths producing the same answer is the second-opinion gate.
    """
    a, b = matrix[0]
    c, d = matrix[1]
    return (
        "import math\n"
        f"a, b, c, d = {a}, {b}, {c}, {d}\n"
        "trace = a + d\n"
        "det = a * d - b * c\n"
        "# Characteristic polynomial: λ² - trace·λ + det = 0\n"
        "D = trace * trace - 4 * det\n"
        "if D < 0:\n"
        "    print('VERIFY_RESULT:COMPLEX_EIGENVALUES')\n"
        "else:\n"
        "    sqrtD = math.sqrt(D)\n"
        "    e1 = (trace + sqrtD) / 2\n"
        "    e2 = (trace - sqrtD) / 2\n"
        "    eigs = sorted([e1, e2])\n"
        "    print('VERIFY_RESULT:' + repr(eigs))\n"
    )


def _parse_sandbox_output(run_result: str) -> Any | None:
    """Extract VERIFY_RESULT payload from sandbox tool's combined output.

    Sandbox returns `"[sandbox python] exit=N\\nstdout: <out>stderr: <e>"`.
    Looks for `VERIFY_RESULT:<payload>` and returns ast.literal_eval(payload).
    Sentinel strings (NEGATIVE_DISCRIMINANT / COMPLEX_EIGENVALUES) → None.
    Anything else (parse failure, missing line) → None.

    `ast.literal_eval` refuses arbitrary code execution — only Python literals
    (list/tuple/dict/set/numeric/string/None/True/False). The sandbox subprocess
    is trusted to produce a literal, but the parser refuses to execute even if
    the subprocess produced something pathological.
    """
    match = re.search(r"VERIFY_RESULT:(.+)", run_result)
    if not match:
        return None
    payload = match.group(1).split("\n")[0].strip()
    if payload.startswith(("NEGATIVE_DISCRIMINANT", "COMPLEX_EIGENVALUES")):
        return None
    try:
        return ast.literal_eval(payload)
    except (ValueError, SyntaxError):
        return None


def _close_enough(parsed: Any, reference: Any, tolerance: float, method: str) -> bool:
    """Compare parsed sandbox output to reference per verification_method.

    Methods:
    - `"symbolic_match"`: exact equality (post-canonicalization is a future cycle).
    - `"numerical_close"`: element-wise abs-diff <= tolerance for lists; abs-diff
      <= tolerance for scalars. Length mismatch on lists fails.
    - any other method → False (refuse silent acceptance of unknown methods).
    """
    if method == "symbolic_match":
        return parsed == reference
    if method != "numerical_close":
        return False
    if isinstance(parsed, list) and isinstance(reference, list):
        if len(parsed) != len(reference):
            return False
        return all(abs(p - r) <= tolerance for p, r in zip(parsed, reference))
    if isinstance(parsed, (int, float)) and isinstance(reference, (int, float)):
        return abs(parsed - reference) <= tolerance
    return False
