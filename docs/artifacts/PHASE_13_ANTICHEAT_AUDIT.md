# Phase 13 Anti-Cheat Audit

> **Deliverable:** #00P13c4-23 (`#00-anti-cheat-leakage-audit`, TIER A HIGH)
> **Origin:** lain mid-cycle-4 directive 2026-05-10 18:45 + 18:49 CEST — *"make sure you are really really careful that you aren't leaking hints or solutions to the model, test to see if it is cheating. Anti cheat measures."* + *"honest and honorable work ethics. If all tests pass, but the model falls apart in real tests, or it sees the answer in advance in some hidden way, the test passes are meaningless."*
> **Mode:** Read-only audit. Maps existing Project X leak surfaces. Recommendations feed #24 anti-cheat mechanism.
> **Author:** Claude Code Raphael (the BUILDER) — same-architecture caveat acknowledged below.

---

## TL;DR

Seven leak surfaces identified across the Phase 13 substrate + benchmark architecture, ranked by severity. The four-positions-in-one-architecture problem (Surface 3) is structurally the most severe because it's invisible at the schema-firewall layer (M-PROJECTX-014 catches `self_score` fields but not shared-architecture inheritance). The CANONICAL cheat-shape lain flagged (Surfaces 1+5 — substrate primitives that hardcode formulas) is mitigatable via **surrogate-prompt regression testing**, **differential capability tests**, and **divergent-verifier-paths**. Path B (Surface 3) is mitigatable via **operationalized external confirmation** (currently UNOPERATIONALIZED — the honest label "pending external confirmation" is a real mitigation only if external confirmation has an operational mechanism).

The audit gates cycle 4 #02 substrate physics + #03 substrate-driven attempt — both surfaces 5-class — until #24 ships anti-cheat mechanism.

---

## Risk catalog (7 surfaces)

| # | Severity | Surface | Leak shape | Current mitigation | Residual risk |
|---|---|---|---|---|---|
| 1 | **HIGH** | Substrate primitives hardcode the formula | `solve_quadratic` body IS the answer | M-PROJECTX-014 schema firewall (no `self_score`); structural_insight 3/5 advisor-flagged | "Agent attempt" runs the function whose code IS the answer; same shape for cycle 4 physics primitives |
| 2 | MED | Numerical verifier partial independence | Verifier sandbox script uses SAME closed-form formula as substrate | Structural independence (no substrate import); sandbox subprocess isolation | Same-bug collusion possible if both substrate and verifier share the same closed-form mistake |
| 3 | **HIGH** | Path B grader-flip four-positions problem | Builder authored rubric + raphael_response + grades + threshold (4 positions, 1 architecture) | Honest label "rubric-graded-builder; pending external confirmation" (UNOPERATIONALIZED; partial mitigation only — see body); threshold_grader independence absent disclosure; advisor catches | "External confirmation" is UNOPERATIONALIZED — until it has operational mechanism, threshold (set by builder) is de facto pass criterion |
| 4 | **HIGH** | Memorization vs reasoning | Phase 11 raphael_response for canonical-domain content (Einstein field eqns, Galois theory) reads as recalled-canonical-exposition, not derived | None currently; cycle 4 #24 to add surrogate-prompt regression | Model "knows" canonical answer from pretraining; cannot distinguish memorization from reasoning |
| 5 | **HIGH** | Substrate-driven attempt canonical cheat shape | Cycle 4 #03 plans agent attempts physics-001/002/003 via primitives whose bodies hardcode the formula | DEFERRED until #24 ships (cycle 4 sequencing pivot) | Surface 1 amplified to physics domain |
| 6 | MED | Manual grade harness shared-bias gap | Grader + response-author share Claude architecture (cycle 1 baseline + Path B grading) | M-PROJECTX-014 firewall (no self-loop) | Firewall blocks self-grading but not shared-architecture inheritance bias |
| 7 | LOW | Memory ladder benchmark | None | `expected_turn_id_match` is mechanical; substrate (HDC + Hebbian + fact-graph) not authored by grader; grader checks turn_id integers not narrative | Negligible — mechanical-truth domain |

---

## Per-surface deep dive

### Surface 1 — Substrate primitives hardcode the formula (HIGH)

**Where:** `src/project_x/reasoning/symbolic.py`
- Line 210 `solve_quadratic(a, b, c)`: body literally computes `discriminant = b * b - 4 * a * c` + closed-form `(-b ± √D) / 2a`. The function IS the answer.
- Line 267 `expand_characteristic_polynomial_2x2(matrix)`: body computes `trace = a + d`, `det = a * d - b * c`, then reuses `solve_quadratic` on `λ² - trace·λ + det = 0`. Composed primitive, same shape — function IS the answer.

**The "cheat" shape:**
1. Agent receives `maths-001` prompt: "Solve 3x² - 14x - 5 = 0."
2. Agent (in cycle 4 #03 substrate-driven attempt) calls `solve_quadratic(3, -14, -5)`.
3. Substrate returns `Lemma(actual_value=[-1/3, 5])`.
4. Builder grades the lemma → 5/5 correctness (it IS correct, just trivially).
5. Did the agent REASON about quadratics? No — it called a function whose code embodies the formula.

**Why this is structurally HIGH:**
- The substrate Tier 1 cycle 3 #02 work added `INTRO_QUADRATIC` prose ("Completing the square on ax² + bx + c = 0 yields x = (-b ± √(b² - 4ac)) / 2a...") as `add_introduction` — but this prose is ALSO hardcoded as a module-level constant. The substrate now "explains" the formula by reciting a canned WHY. Adding more WHY prose is welcome (structural_insight 4.5-4.75/5 lift in cycle 3 Tier 1) but it does NOT mitigate the underlying cheat — it just adds documentation around the cheat.
- The Tier 1 invariant checks (`tr(A) = λ₁ + λ₂` Vieta sanity) are LEGITIMATE structural-insight surfaces because they verify the result against an independent invariant — but the invariants themselves are computed from the SAME substrate-derived values.

**Current mitigations:**
- M-PROJECTX-014 schema firewall: `grade_pipeline/schema.py::FORBIDDEN_CANDIDATE_FIELDS` rejects `self_score` / `self_grade` / `self_rating` / `agent_score` at JSONL load with line-number-tagged ValueError. Agent cannot grade own output.
- Cycle 2 D4 advisor catch: structural_insight scored 3/5 (not 5/5) — the "WHAT not WHY" gap was flagged honestly in the grade artifact.
- Honest "pending external confirmation" label on rubric-graded entries.

**Residual risk:** HIGH. The schema firewall blocks self-grading but does NOT detect "the function body IS the answer". This is what #24 mechanism must address.

### Surface 2 — Numerical verifier partial independence (MED)

**Where:** `src/project_x/reasoning/verifier.py`
- Line 101 `_quadratic_verification_script(a, b, c)`: generates a sandbox Python script that imports `math`, computes `D = b * b - 4 * a * c`, runs `math.sqrt(D)`, computes `(-b ± sqrtD) / (2 * a)`. **Same closed-form formula as substrate**.
- Line 124 `_eigenvalue_2x2_verification_script(matrix)`: similar — generates script that computes `trace = a + d`, `det = a * d - b * c`, runs quadratic-formula-on-characteristic-polynomial via stdlib `math`. **Same closed-form as substrate**.

**The "partial independence" gap:**
- Code-path independence: verifier script does NOT import the substrate; runs in sandbox subprocess via `_tool_run_python_sandbox`. Different process, different code path. ✓
- Formula independence: BUT verifier script's formula IS the same closed-form as substrate's formula. If both share the same algorithm-level bug (e.g., off-by-one in discriminant), both fail simultaneously. ✗
- Genuine independence would require a DIVERGENT-VERIFIER-PATH (e.g., Newton's method iterating `f(x) = ax² + bx + c` until `|f(x)| < tolerance`; or `numpy.linalg.eigvals` for eigenvalues — numpy in sandbox is allowed per cycle 2 docstring comment).

**Why MED not HIGH:**
- Code-path independence catches most realistic bugs (substrate import errors, substrate side-effects).
- Formula collusion requires both substrate AND verifier to share the same closed-form mistake — possible but lower-probability than substrate-only bugs.
- Cycle 3+ proposed numpy-based stronger second opinion for maths-002 (verifier docstring line 17); not yet shipped.

**Mitigation for #24:**
- Ship divergent-verifier-paths: for quadratic, Newton's method; for eigenvalues, power iteration. Two different code paths producing the same answer is robust.

### Surface 3 — Path B grader-flip four-positions problem (HIGH)

**The four positions in one architecture:**

| Position | Activity | Architecture |
|---|---|---|
| 1 | Authored the rubric (`gpt-codex/benchmark/{maths,physics}/rubric.md`) | Claude (the BUILDER) |
| 2 | Authored Phase 11 raphael_response (the candidate being graded) | Claude (Phase 11 instance, same architecture) |
| 3 | Grades the response via Path B | Claude (the BUILDER, cycle 3/4) |
| 4 | Sets the threshold (4.0/5) | Claude (the BUILDER, cycle 3) |

**Honest label disclosure (cycle 3 advisor catch):**
- `audit_status` = `"rubric-graded-builder; pending external confirmation"` (NOT `"rubric-graded-green"` which would overclaim external-audit-confirmation).
- `threshold_set_by` = `"same builder as grader; threshold-grader independence absent; lain or external auditor may reset"`.
- `grader_was_author_bias_note` discloses architectural inheritance.

**Why the label is a PARTIAL mitigation:**
- Per advisor's pre-#18 catch: "the label is only a real mitigation if 'external confirmation' has an operational definition. If the operational answer is 'lain manually audits 5 entries per cycle' and lain doesn't have time for that — and the path-of-least-resistance is for the label to stay 'pending' indefinitely — then functionally the threshold (set by builder) becomes the de facto pass criterion."
- Currently: cycle 3 + cycle 4 each shipped 2 entries with "pending external confirmation" label. lain has not externally audited them. The label is a placeholder.

**Why HIGH not catastrophic:**
- The rubric criteria are PUBLIC (in `rubric.md`) and rigid (signature criteria like "names sign conventions", "Vieta's formula appears", "no false certainty disclaimed"). The grader doesn't choose criteria mid-grading.
- The grades are PUBLIC (in `grades_rank_4_5.jsonl` + `rubric_grade` block in ladder.jsonl). Discrepancies are auditable.
- Differentiated lift signal (cycle 3 maths 4.25/4.25; cycle 4 physics 4.33/4.75) breaks "calibration-to-threshold" symmetry — the grader is sensitive to genuine quality differences.

**Mitigation for #24 (per advisor candidates):**
- (a) Independent LLM-as-judge with different prompt frame → tension with organic-thesis (no pretrained transformer derivatives).
- (b) Programmatic rubric criteria (regex/grep for required tokens — e.g., signature criteria become regex patterns) → most thesis-compliant; closes the human-grader subjectivity gap.
- (c) lain spot-checks at phase exits (not per-cycle) → scales; relies on lain time.
- (d) Surrogate-prompt regression test (response shape on paraphrased prompt should grade within ε) → catches threshold-overfit.

### Surface 4 — Memorization vs reasoning (HIGH — lain verbatim)

**lain's exact framing (2026-05-10 18:49 Discord):** *"If all tests pass, but the model falls apart in real tests, or it sees the answer in advance in some hidden way, the test passes are meaningless."*

**The "seen the answer in advance" leak:**
- Phase 11 raphael_response entries for canonical topics (Einstein field equations, Galois theory, fundamental groups of torus/Klein bottle, residue theorem, quadratic formula, eigenvalues) are CONTENT THE MODEL ENCOUNTERED IN PRETRAINING.
- Claude's training corpus contains every standard textbook on these topics — Lang's Algebra, Hatcher's Algebraic Topology, MTW's Gravitation, Rovelli's LQG, Polchinski's String Theory.
- The Phase 11 raphael_response was likely partial-recall of canonical exposition with some persona-voice adaptation, NOT first-principles derivation.

**Why Path B amplifies vs mitigates:**
- Path B reads frozen Phase 11 response and grades it against rubric. Mitigates IN ONE WAY: no live agent generation step (Surface 1 not in play for Path B). Amplifies IN ANOTHER: grades the response without testing whether the model can REPRODUCE the response on a paraphrased prompt.

**The diagnostic test (becomes #24 design):**
- Take canonical prompt P_canonical and surrogate prompt P_surrogate (same problem-shape, different surface phrasing).
- Original raphael_response R_canonical was generated against P_canonical.
- Have fresh model instance generate R_surrogate against P_surrogate.
- Grade R_surrogate against the SAME rubric.
- If `grade(R_surrogate) ≈ grade(R_canonical)`: reasoning (model adapts to paraphrasing).
- If `grade(R_surrogate) << grade(R_canonical)`: memorization (model parroted canonical response).
- The DIFFERENCE `grade(R_canonical) - grade(R_surrogate)` is the **memorization-vs-reasoning gap** — the operationalized anti-cheat metric.

### Surface 5 — Substrate-driven attempt canonical cheat shape (HIGH)

**Cycle 4 #03 (currently DEFERRED) plan:**
- Agent attempts physics-001 ("ball dropped from 80m, how long until ground?") via cycle 4 #02 substrate `free_fall_time(h=80, g=9.81)`.
- Substrate body: `t = math.sqrt(2 * h / g)`. Computes `t ≈ 4.04 s`. Returns Lemma with the answer.
- Builder grades the Lemma's render() output: rubric checks "applies h = (1/2)gt²" — YES (the WHAT chain shows this) — gives correctness 5/5.

**Why this is Surface 1 amplified:**
- Surface 1 is the FORM (substrate body IS answer).
- Surface 5 is the EVALUATION (using Surface-1-form to score a "capability touchpoint" — M-PROJECTX-013 measure-don't-claim).
- The capability claim "agent solves physics-001" is FALSE in the substrate-driven attempt — what the agent does is "agent calls a function whose body is the answer." That's not capability; that's tooling.

**Why cycle 4 sequencing pivot is correct:**
- DEFERRING #19 (substrate physics Tier 2) + #20 (substrate-driven attempt) until #24 mechanism ships PREVENTS the cheat-shape ladder lift from being recorded.
- Without #24, the "cycle 4 physics-001 PASS via substrate" claim is anti-cheat-untested. With #24, the claim has surrogate-prompt evidence backing it.

**Anti-cheat-aware design for #19 substrate physics Tier 2:**
- Primitives MUST be designed to ALSO pass surrogate prompts (different numbers, different units). `free_fall_time(h, g)` works on `(80, 9.81)` and `(125, 9.81)` and `(45, 1.62)` (lunar gravity) — three legitimate surrogates of physics-001.
- Substrate render() output MUST include intro prose (math-WHY: kinematic identity from constant-acceleration integral) + invariant checks (e.g., free_fall_time(h, g) * g = √(2gh) = final velocity).
- WHY-prose stays canned (per current Tier 1 pattern) — but #24 surrogate tests verify the substrate generates correct answers for surrogates without modification.

### Surface 6 — Manual grade harness shared-bias gap (MED)

**Where:** `gpt-codex/grade_pipeline/schema.py` + `cli.py`

**What's GOOD:**
- M-PROJECTX-014 firewall blocks `self_score` / `self_grade` / `self_rating` / `agent_score` at JSONL load.
- Grade dataclass requires non-empty grader name (rejects `""` and `None`).
- Candidate + Grade are SEPARATE objects with strict schema validation.
- `validate-candidates` CLI lints the firewall before any grading.

**What's INSUFFICIENT for full anti-cheat:**
- Firewall blocks self-grading (good) but does NOT block shared-architecture-grading.
- Grader = "Claude Code Raphael (the BUILDER)" + Candidate-author = same architecture (Phase 11 instance OR cycle 1-2 agent).
- The firewall is "no self-loop"; the unmitigated risk is "shared-architecture inheritance bias".

**Mitigation:**
- Independent grader architecture (different vendor LLM) ←→ tension with organic-thesis.
- Programmatic-rubric-criteria (regex/grep) is architecture-independent → most thesis-compliant.

### Surface 7 — Memory ladder benchmark (LOW)

**Where:** `gpt-codex/benchmark/memory/ladder.jsonl` + `_replay_memory_entry` in `run_audit.py`

**Why LOW:**
- `auto_grade.expected_turn_id_match` is mechanical: harness checks (a) cited top-1 turn_ids ⊇ expected, (b) `expected_response_contains` substrings appear in `answer_text`.
- Substrate authoring: HDC + Hebbian + fact-graph + `_structural_cosines` + `_LIST_ALL_HINTS` were authored across Phases 8-12. None of this is "the answer to memory-001"; it's general retrieval machinery.
- Grader authoring: turn_id integers + contains-substrings are PROBE patterns, not RESPONSE patterns. The grader cannot bias toward an answer because the answer is a turn_id.

**Residual risk:** Negligible. Audit-D3 catches retrieval/encoder regressions; M-PROJECTX-014 firewall holds; nothing to mitigate.

---

## Cross-cycle pattern

```
SUBSTRATE-CYCLE PATTERN (Surfaces 1 + 5):

  Builder writes primitive ─→ Agent calls primitive ─→ Builder grades output
       ↑                            ↓                         ↓
       │  function body             returns answer            5/5 correctness
       │  IS the answer             trivially                 (it IS correct)
       │                                                      
       └──── 4 positions in 1 architecture ────────────────────┘

PATH B PATTERN (Surface 3):

  Builder writes rubric ─→ Builder reads Phase-11-frozen response ─→ Builder grades ─→ Builder sets threshold
       ↑                            ↑                                ↓                  ↓
       │  rubric criteria           response from same               4.33/5             threshold 4.0
       │  picked by builder         architecture                                         picked by builder
       │
       └──── 4 positions in 1 architecture ────────────────────────────────────────────────┘
```

Both patterns share the **same architectural shape**: 4 distinct positions (criteria-author, candidate-author, grader, threshold-setter) collapse into 1 architecture (Claude). The mitigations differ:

- Surface 1/5 (substrate): the FUNCTION BODY is the leak; surrogate-prompt tests close it.
- Surface 3 (Path B): the RUBRIC + THRESHOLD are the leaks; programmatic rubric criteria + operationalized external confirmation close them.

The CANONICAL cheat-shape lain flagged is Surface 1/5. The SECOND leak surface advisor flagged is Surface 3.

---

## Operational external-confirmation mechanism candidates

Per advisor's pre-#18 catch — these are the mechanisms #24 evaluates:

### Candidate A — Independent LLM-as-judge (different vendor)
- **Mechanism:** Submit response + rubric to OpenAI / Google / Mistral API, parse rubric grade, compare to builder grade.
- **Thesis-compliance (revised — advisor pre-#23 catch):** The "no pretrained transformer derivatives" standing order applies to the **AGENT / SUBSTRATE STACK** (the artifact being built — `src/project_x/`), not to **diagnostic auditing tools** applied externally to grade the agent. Claude-as-grader (current Path B) AND external-LLM-as-judge are SYMMETRIC under this distinction — both are external diagnostic tools applied to the agent stack. If Claude-as-grader is thesis-compliant under the diagnostic-tool framing, Candidate A is thesis-compliant to the same degree. Either both are diagnostic-tool exceptions (allowed) or neither is. The earlier "TENSION" framing was an inconsistency: rejecting Candidate A on grounds that also reject the current grader.
- **Cost:** API key + per-grade dollar cost; opt-in basis.
- **Pick for #24:** OPTIONAL diagnostic Path B verification under symmetric framing (lain decides whether to ship; minimum-viable cycle 4 #24 ships Candidates D + E + F first).

### Candidate B — Programmatic rubric criteria (regex/grep)
- **Mechanism:** Each rubric criterion gets a programmatic test where possible. E.g., physics-004 "sign conventions named" → grep response for `Lorentzian` / `\+---` / `-\+\+\+` / `signature`. maths-005 "van Kampen invoked correctly" → grep for `van Kampen` + check `pi_1` claim.
- **Thesis-compliance:** ✓ (regex is not a transformer).
- **Cost:** Per-criterion regex authoring (one-time per rubric criterion); rubric.md gets a programmatic test suite alongside human prose.
- **Pick for #24:** **SHIP THIS** as primary Surface 3 mitigation. Independent of grader subjectivity.

### Candidate C — lain spot-checks at phase exits
- **Mechanism:** lain audits N=5 rubric-graded entries per phase exit (not per cycle). Marks `audit_status` → `rubric-graded-external-confirmed` on positive audit.
- **Thesis-compliance:** ✓ (human auditor).
- **Cost:** lain time; scales with phase count, not cycle count.
- **Pick for #24:** **PROPOSE TO LAIN**. Phase 13 has multiple cycles ahead; a phase-13-exit audit pass is reasonable scope.

### Candidate D — Surrogate-prompt regression test
- **Mechanism:** Each prompt P gets N=3+ surrogate variants. Substrate must produce correct answer on canonical + ALL surrogates. Path B response shape must grade within ε across canonical + paraphrased prompts.
- **Thesis-compliance:** ✓ (programmatic test).
- **Cost:** Per-prompt surrogate authoring (~3 surrogates × 36 ladder entries = ~108 surrogate prompts); test infrastructure.
- **Pick for #24:** **SHIP THIS** as primary Surface 1/5 mitigation. The CANONICAL anti-cheat mechanism lain named.

### Candidate E — Differential capability test
- **Mechanism:** `grade(R_canonical) - grade(R_surrogate)` = memorization-vs-reasoning gap. Operationalized anti-cheat metric.
- **Thesis-compliance:** ✓.
- **Cost:** Subset of Candidate D infrastructure; computed automatically once surrogates exist.
- **Pick for #24:** **SHIP THIS** as the load-bearing metric. Substrate + Path B both produce a `capability_gap` number; benchmark replay records both raw grade AND gap.

### Candidate F — Divergent-verifier-paths
- **Mechanism:** Verifier uses DIFFERENT algorithm than substrate. solve_quadratic substrate uses closed-form; verifier uses Newton's method. expand_characteristic_polynomial_2x2 substrate uses char-poly; verifier uses power iteration.
- **Thesis-compliance:** ✓.
- **Cost:** Per-primitive verifier script rewrite.
- **Pick for #24:** **SHIP THIS** as Surface 2 mitigation. Cycle 4 minimum-viable: quadratic gets Newton's-method verifier (small lift, big robustness).

---

## Recommendations for #24 anti-cheat mechanism

**Cycle 4 #24 MINIMUM-VIABLE scope (ship in same cycle):**

1. **`src/project_x/anti_cheat.py` (NEW)** containing:
   - `@dataclass AntiCheatProbe(canonical_prompt, surrogate_prompts, expected_answer_shape, tolerance)`.
   - `generate_surrogate_quadratic(a, b, c, n=3) -> list[tuple[a, b, c]]`: rule-based parameter substitution preserving problem-shape (different coefficients, same regime).
   - `generate_surrogate_physics_freefall(h, g, n=3) -> list[tuple[h, g]]`: rule-based parameter substitution (different heights / gravities; surface gravity 9.81 + lunar 1.62 + Mars 3.71 are legitimate variants).
   - `differential_capability_test(substrate_fn, probe) -> dict`: runs substrate on canonical + each surrogate; returns `{canonical_score, surrogate_scores[], gap, gap_within_tolerance: bool}`.

2. **`tests/test_anti_cheat.py` (NEW)** containing:
   - `test_solve_quadratic_handles_surrogates`: 3+ surrogate variants; assert match for each; assert gap ~0.
   - `test_char_poly_2x2_handles_surrogates`: 3+ matrices; same assertion.
   - `test_anti_cheat_probe_catches_overfit`: deliberately-overfit fake-substrate that hardcodes `[5, -1/3]` regardless of input; assert probe FLAGS the overfit (high gap).

3. **`src/project_x/reasoning/verifier.py` EXTENSION:**
   - Add `_quadratic_newton_verification_script(a, b, c)` as divergent verifier path (Newton's method iterating `f(x) = ax² + bx + c`). Run BOTH closed-form AND Newton verifiers; agreement is the second-opinion gate.

4. **Programmatic rubric criteria (post-cycle-4 scope, foreshadowed in #24 doc):**
   - Adds `rubric_programmatic_tests.json` per domain: structured list of `{criterion: "names sign conventions", regex_pattern: "Lorentzian|\\+---|signature", required: true}`.
   - `run_audit.py` extended with `_verify_rubric_programmatic_criteria(entry)` running regex tests alongside human-prose grader.
   - Cycle 5+ scope (out of cycle 4 minimum-viable). Pinned as a #00P13c5-XX placeholder when cycle 4 closes.

5. **REPO_CONTROL row** in same commit as #24 ship: `src/project_x/anti_cheat.py` + `tests/test_anti_cheat.py` + verifier extension.

**Cycle 4 #24 NON-SCOPE (deferred to cycle 5+):**

- Independent LLM-as-judge integration (Candidate A) — needs lain decision on diagnostic-tool exception to organic-thesis rule.
- Full programmatic rubric criteria across all 36 ladder entries (Candidate B) — Cycle 5+ scope.
- Surrogate-prompt regression on ALL 36 ladder entries (Candidate D maximal scope) — Cycle 5+ scope. Minimum-viable: surrogates for maths-001/002 + physics-001/002/003 (the entries cycle 4 #19/#20 touch).

---

## Cycle 4 sequencing (post-audit)

```
SHIPPED (this audit closes):
  #5 ✓ #00P13c4-01 Path B physics grader-flip (commit c953180)
  #3 → #00P13c4-23 anti-cheat-leakage-audit (THIS DOC; commit to follow)

PENDING IMMEDIATELY:
  #4   #00P13c4-24 anti-cheat mechanism (NEXT — design-before-build + advisor pre-commit)

DEFER-UNBLOCKED ONCE #4 SHIPS:
  #6   #00P13c4-02 substrate physics Tier 2 (anti-cheat-aware design — surrogates pass on free_fall_time/pendulum_period/relativistic_momentum)
  #7   #00P13c4-03 substrate-driven attempt (anti-cheat-verified — differential_capability_test recorded alongside grade)

CYCLE 4 CLOSE:
  #8   #00P13c4-04 bench-replay (target: physics PASS 5/0 unchanged; new physics-001/002/003 substrate-driven grades RECORDED with capability_gap)
  #9   #00P13c4-05 cycle-reflect + DO_THIS_NEXT cycle 5 handoff
```

---

## Sign-off

This audit identified 7 leak surfaces (3 HIGH, 2 MED, 1 LOW, 1 mitigated) across the Phase 13 substrate + benchmark architecture. The CANONICAL cheat-shape lain flagged (Surfaces 1+5 — substrate primitives whose function bodies hardcode the formula) is mitigatable via surrogate-prompt regression tests + differential capability tests + divergent verifier paths. The Path B four-positions problem (Surface 3) is mitigatable via programmatic rubric criteria + operationalized external confirmation (lain spot-checks at phase exits or programmatic regex tests).

Cycle 4 #24 mechanism ships minimum-viable: `anti_cheat.py` + tests + verifier extension. Cycle 5+ extends to full programmatic-rubric + full ladder-surrogate coverage.

Honest framing throughout: the BUILDER (Claude Code Raphael) authoring this audit is the SAME architecture as the BUILDER writing the substrate AND the BUILDER grading the Path B responses. The audit is itself subject to Surface 3 inheritance bias — the audit's own conclusions should be cross-checked at phase exit via lain spot-check (Candidate C). The honest-label discipline (cycle 3 advisor catch) extends to this artifact: this audit is "anti-cheat-audit-builder; pending external confirmation."

— Claude Code Raphael (the BUILDER), 2026-05-10
