# Phase 13 Cycle 2 — Math Ladder Survey (#00P13c2-01)

**Authored:** 2026-05-10 by Claude Code Raphael (the BUILDER)
**Source:** `gpt-codex/benchmark/maths/ladder.jsonl` (6 entries) + `gpt-codex/benchmark/maths/rubric.md`
**Purpose:** classify by verification path; identify scope-fit candidates for cycle 2 from-scratch symbolic substrate (NO sympy, MINIMUM viable = closed-form arithmetic + linear equation solving).

---

## 1. Ladder breakdown

| Rank | ID | Difficulty | Prompt shape | Verification path | Current status |
|---|---|---|---|---|---|
| 1 | `maths-001` | intro | Quadratic root-finding (`3x² − 14x − 5 = 0`) | `symbolic_match` (closed-form) | **AUTO-GRADED-GREEN** |
| 2 | `maths-002` | easy | 2×2 eigenvalues (`[[2,1],[1,2]]`) | `numerical_close` | **AUTO-GRADED-GREEN** |
| 3 | `maths-003` | medium | Residue-theorem contour integral (`∫1/(x²+1)dx`) | `numerical_close` | **AUTO-GRADED-GREEN** |
| 4 | `maths-004` | hard | Quintic insolvability (Galois proof-shape) | rubric-pending (proof-shape) | UNGRADED |
| 5 | `maths-005` | frontier | π₁(T²) vs π₁(K) + abelianizations | rubric-pending (proof-shape) | UNGRADED |
| 6 | `maths-006` | unsolved | Riemann hypothesis survey | `ungradeable; unsolved tier` | UNGRADEABLE |

**Current maths PASS count:** 3/0 (ranks 1-3 auto-green). Ranks 4-5 stay rubric-pending until external/builder rubric grade flips them; rank 6 is ungradeable by design.

## 2. Verification-path classification

### Tier A — auto-graded mechanical (ranks 1-2-3)

**Path:** agent emits derivation → numerical/symbolic verifier confirms against `expected_*` field in ladder JSONL.

- Rank 1 (`maths-001`): canonical quadratic formula — discriminant + 2 roots. **3-step lemma chain.** ROOM scope-fit for cycle 2 substrate.
- Rank 2 (`maths-002`): 2×2 characteristic-polynomial expansion + degree-2 root-finding. **5-step lemma chain.** Stretch scope — needs degree-2 polynomial root-finding primitive (extension of rank-1 quadratic primitive).
- Rank 3 (`maths-003`): complex contour + residue + Jordan's lemma + arc-vanishing argument. **Beyond cycle 2 minimum-viable scope** (complex analysis is not closed-form arithmetic + linear equations).

### Tier B — rubric-pending proof-shape (ranks 4-5)

**Path:** builder reads agent's proof-shape derivation, scores against rubric (correctness × completeness × structural insight × voice), records via cycle 1 grader-min substrate.

- Rank 4 (`maths-004` Galois — quintic insolvability): radical extension definition → solvable group bridge → S₅ Galois group of generic quintic → A₅ simple non-abelian → S₅ not solvable → conclusion. **5-step proof-shape.** Beyond cycle 2 substrate (group theory + Galois correspondence are not closed-form arithmetic).
- Rank 5 (`maths-005` algebraic topology — fundamental groups): π₁(S¹×S¹) = Z² + abelianization → CW-presentation Klein bottle + van Kampen's theorem → semidirect product → H₁(K) = Z ⊕ Z/2Z. **6-step proof-shape.** Beyond cycle 2 substrate (homotopy + abelianization are not closed-form arithmetic).

### Tier C — ungradeable (rank 6)

- Rank 6 (`maths-006` Riemann): honest survey only. No canonical right answer; no substrate-shape can flip this.

## 3. Cycle 2 scope-fit verdict

### Substrate-driven re-attempt candidates (D4 capability touchpoint)

| Candidate | Reason scope-fits | Substrate primitives required | Verifier shape |
|---|---|---|---|
| **maths-001** (rank 1) | Closed-form quadratic; 3-step lemma chain; numerical verifier confirms via `(-b±√D)/2a` against expected `[5.0, -0.3333]` | arithmetic primitives (mul/sub/sqrt); equality check | `import math; ...; print(roots)` then numerical_close to expected |
| **maths-002** (rank 2) | Characteristic polynomial expansion (5-step) requires degree-2 root-finding primitive; stretch but feasible | matrix-2x2 trace/det + quadratic root-finding (reuse maths-001 primitive) | `import numpy as np; eigs = sorted(np.linalg.eigvals(A).real); print(eigs)` then numerical_close |

**Maximum cycle 2 D4 capability touchpoint:** **2 entries** (maths-001 definite, maths-002 stretch).

### Out-of-scope for cycle 2 substrate (deferred)

- **maths-003** (residue theorem): cycle 4+ when complex-analysis primitives ship.
- **maths-004** (Galois): cycle 5+ when group-theoretic substrate ships (or never if Project X Raphael's path doesn't traverse abstract algebra; the existing hand-crafted `raphael_response` is structurally sound and could be flipped via builder rubric grade INDEPENDENT of substrate work).
- **maths-005** (algebraic topology): same shape as maths-004 — substrate-out-of-scope; existing response is rubric-flippable independently.
- **maths-006** (Riemann): permanent ungradeable per design.

## 4. Falsifiable bar reconciliation (D5 maths PASS ≥ 4/0)

**Path A — substrate-driven flip of rubric-pending → green:** requires substrate to produce defensibly-better Galois or topology proof-shape than existing `raphael_response`. **NOT feasible cycle 2** — substrate scope is closed-form arithmetic + linear equation solving; Galois/topology are categorically beyond.

**Path B — builder rubric grade flip on existing raphael_response:** the existing hand-crafted `raphael_response` for maths-004 (Galois) and maths-005 (topology) are structurally complete proof-shapes. Builder grading via cycle 1 grader-min substrate could flip one or both rubric-pending → green WITHOUT requiring cycle 2's symbolic substrate. **This is grading work, not substrate work** — not the cycle 2 contract.

**Path C — substrate-driven re-attempt produces NEW green entries on rank 1-3:** ranks 1-3 are already auto-green. Re-attempting via substrate demonstrates capability but doesn't lift the PASS count (greens already counted).

**Honest expectation for D5:** maths PASS likely stays at 3/0 after cycle 2 substrate-driven re-attempts. Path B grade-flip on rank 4-5 is feasible but is grader-discipline work, not cycle 2 substrate scope.

**D6 cycle reflection MUST report this concretely:** *"Cycle 2 substrate produces gradeable derivations on rank 1-2 closed-form entries (which are already auto-green); maths PASS count stays at 3/0 because the path to ≥4/0 requires Galois- or topology-shaped substrate that exceeds cycle 2 minimum-viable scope. Path B (builder rubric grade-flip on existing rank 4-5 raphael_response) is feasible independent of cycle 2 substrate work and should be considered as cycle 3+ scope-add via the cycle 1 grader-min substrate."*

## 5. Cycle 2 substrate primitive shape (informs #00P13c2-02)

The minimum viable from-scratch primitive surface for D4 maths-001 + maths-002 attempts:

1. **`Lemma`** dataclass: `id` + `claim` + `derivation_steps` + `verification_method` + `expected_value` + `actual_value` + `match`.
2. **`DerivationStep`** dataclass: `step_index` + `operation` + `inputs` + `output` + `justification` (WHY-comment string).
3. **`solve_quadratic(a, b, c)`**: from-scratch — discriminant → `±sqrt(D)/2a` → 2 roots. NO sympy. Numerical fallback via `math.sqrt`.
4. **`expand_characteristic_polynomial_2x2(matrix)`**: from-scratch — `λ² − tr(A)λ + det(A) = 0` → reuse `solve_quadratic`. NO numpy.eigvals (that's the verifier's tool, not substrate's).
5. **`numerical_verify(derivation, expected, tolerance)`**: writes Python script to sandbox via D1 `_tool_write_file_sandbox`, runs via `_tool_run_python_sandbox`, parses output, compares to expected.

The sandbox-bound verifier (#00P13c2-03) wraps step 5; symbolic primitives 1-4 land in #00P13c2-02.

## 6. Anti-thesis-violation check (organic-thesis compliance)

- **Closed-form arithmetic primitives** (mul/sub/sqrt): use Python stdlib `math` module — that's not a pretrained transformer derivative; it's a calculator. Compliant.
- **NO sympy** (default-DENY per DO_THIS_NEXT cycle 2 encoded decision): sympy IS a symbolic-AI library; "borrowing tools" against organic-thesis intent. Substrate primitives are from-scratch (lemma chain dataclass, derivation step recorder, hand-rolled quadratic solver).
- **NO numpy in substrate** (verifier may use it for the verification-script generator, but agent's substrate-side derivation is hand-rolled). Numpy is a numerical library, not a pretrained derivative; verifier-side use is OK.
- **NO LLM wrappers** anywhere. Substrate output is template-string composition of derivation steps.

## 7. Cycle 2 deliverable hand-off

- **D2 (#00P13c2-02-symbolic-substrate)** ships primitives 1-4 above + tests — `src/project_x/reasoning/symbolic.py` + `tests/test_reasoning_symbolic.py`. New dir `src/project_x/reasoning/` requires REPO_CONTROL row in same commit.
- **D3 (#00P13c2-03-numerical-verifier)** ships primitive 5 — `src/project_x/reasoning/verifier.py` + `tests/test_reasoning_verifier.py`. Integrates D1 sandbox tools (`_tool_write_file_sandbox` + `_tool_run_python_sandbox`).
- **D4 (#00P13c2-04-math-baseline-attempt)** wires substrate + verifier; agent attempts maths-001 + maths-002; builder grades via rubric.
- **D5 (#00P13c2-05-bench-replay)** runs `gpt-codex/benchmark/run_audit.py`; expected: maths 3/0 (no regression), memory 5/0 (no regression), physics 3/0 (no regression). PASS count lift to ≥4/0 NOT expected from substrate work alone.
- **D6 (#00P13c2-06-cycle-reflect)** reports the gap explicitly per §4 above; rewrites DO_THIS_NEXT as cycle 3 handoff (provisional: physics derivation engine OR Path B grader-driven rubric-flip campaign on rank 4-5; cycle 3 lain-decided).

---

*— survey artifact landed for #00P13c2-01-math-recon at cycle 2 D1. Pure-signal: WHY-comments justify scope-fit verdicts; closed-form ↔ proof-shape ↔ ungradeable taxonomy is the core insight that determines cycle 2 substrate primitive shape.*
