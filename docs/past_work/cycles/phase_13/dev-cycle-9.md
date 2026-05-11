# Phase 13 — Cycle 9 reflection

**Theme:** Lain mid-cycle pivot 2026-05-11 — drop the queued predicate-strength uniformity pass; ship **harder-problems-first** (symbolic integration via parts/u-sub + bounded Diophantine binary-quadratic enumeration) + **visible IQ-progression artifact** (paper.md teacher-tone curriculum + IQ_PROGRESSION.md per-cycle ladder) + **honest ladder labeling** (5-level difficulty_tier + would_surprise_hassabis on rubric entries). Capability-debt > grading-debt > rigor-debt. Predicate-strength uniformity pass reinstated as cycle-10 #1 priority.
**Closed:** 2026-05-11
**Cycle horizon:** ~3.5 hours across two Claude Code instances (single `/clear`+paste handoff at mid-cycle via lain-authorized `/forge-prompt -ni`). 6 atomic commits + 1 cycle-reflect commit.

## Deliverables ledger (per docs/DO_THIS_NEXT.md cycle 9 final table)

| ID | Status | Commit |
|---|---|---|
| #00P13c9-01 symbolic integration substrate (parts + u-sub) | DONE (planning-raphael) | `5fe45e9` |
| #00P13c9-05 paper.md teacher-tone NotebookLM curriculum (lain mid-cycle directive) | DONE (planning-raphael) | `18e385e` |
| #00P13c9-02-partial IQ_PROGRESSION.md tracker + DO_THIS_NEXT cycle-9-in-flight + A_TO_Z entry | DONE (planning-raphael) | `48c6035` |
| #00P13c9-02-remaining ladder schema retrofit (difficulty_tier + would_surprise_hassabis on 74 entries) | DONE (execute-raphael) | `45291bd` |
| #00P13c9-03 Diophantine binary-quadratic substrate + dispatcher + maths-024/025 | DONE (execute-raphael) | `11aff93` |
| #00P13c9-04 cycle reflect | DONE (THIS commit) | — |
| #00P13c8-07 CLAUDE.md structural trim | PARTIAL — 62k → 57k via 5 surgical cuts (execute-raphael turn) | inline |
| #00P13c7-04 council audit tag | DEFERRED (lain-pending; mechanism scope unresolved) | — |

## What shipped (atomic per-deliverable commits)

### #01 — symbolic integration substrate (`5fe45e9`)

`src/project_x/reasoning/integration.py` (NEW; 508 lines). Four primitives covering canonical textbook integration techniques: `definite_integral_x_times_exp` / `x_times_sin` / `x_times_cos` via integration-by-parts (LIATE heuristic — algebraic × exponential or algebraic × trig); `definite_integral_xtrig_via_usub` via u=x² substitution for `x·sin(x²)` and `x·cos(x²)`. Each Lemma carries a 4-or-5-step derivation chain ending with bound evaluation + an algebraic-identity invariant_check (parts identity `∫u dv + ∫v du = [uv]` recomposed from algorithmically-independent computation of the v du integral; u-substitution change-of-variables identity for the u-sub path). Closes maths-021/022/023 agent-runtime gap. 29 substrate + dispatcher tests. Bench-replay --agent-runtime: 41/0 → 44/0.

### #05 — paper.md teacher-tone curriculum (`18e385e`)

`docs/paper.md` (NEW; ~4500 words, 11 chapters). Per lain 2026-05-11 Discord directive — NotebookLM-podcast-friendly explainer of how Project X Raphael works. Covers: why-not-just-use-ChatGPT, two-Raphaels split (Builder vs Agent), memory layer (HDC + fact-graph), reasoning substrate (Lemma + invariant), AGENT runtime dispatcher, benchmark architecture + split-grading firewall, current capability with concrete examples, what-can't-do honest accounting, the-road-to-Terminus. Lain explicitly wants to listen + chip in on architectural decisions; primary audience is lain.

### #02-partial — IQ_PROGRESSION.md tracker + DO_THIS_NEXT cycle-9-in-flight + A_TO_Z entry (`48c6035`)

`docs/artifacts/IQ_PROGRESSION.md` (NEW; per-cycle hardest-problem-solved-at-runtime ladder) + planning-raphael's docs-sync for the `/forge-prompt -ni` handoff. Per-cycle entries from Phase 9 close → Phase 13 cycle 9 in flight; concrete hardest-end-to-end example for each cycle; pytest baselines + bench-replay PASS counts + capability-shape notes; Today's-Frontier section (what the agent CAN vs CANNOT do); Hassabis-bar retrospective section seeded.

### #02-remaining — ladder schema retrofit (`45291bd`)

74 entries across 6 domains (maths × 23 → 23; memory × 16; persona × 6; philosophy × 6; physics × 16; poetry × 7) retrofit with two new fields: `difficulty_tier` (5-level universal classification: trivial-baseline / intro / intermediate / hard / research-grade) + `would_surprise_hassabis` (bool, applied only to rubric-graded entries; default false because no entry honestly meets the bar yet). Tier distribution: 15 trivial-baseline + 13 intro + 25 intermediate + 21 hard + **0 research-grade** (the cycle-10+ target). Pure-additive change; M-PROJECTX-014 firewall intact — `would_surprise_hassabis` is builder-grade not agent-grade, cannot leak into agent scoring. Field-order convention enforced via reorder().

### #03 — Diophantine binary-quadratic substrate (`11aff93`)

`src/project_x/reasoning/diophantine.py` (NEW; 235 lines). `solve_binary_quadratic(a, b, c, N)` enumerates integer (x, y) solving `a·x² + b·xy + c·y² = N` for positive-definite forms (Δ = b² - 4ac < 0 AND a > 0 AND c > 0). Algorithm: complete the square → Lagrange bounds (|x| ≤ √(4cN/|Δ|), |y| ≤ √(4aN/|Δ|)) → brute-force enumerate bounded integer rectangle → filter by exact equality. 4-step Lemma chain (identify_form → compute_search_bound → brute_force_enumerate → verify_solutions) + form-parity invariant ((x,y) → (-x,-y) closure) + stronger D₄ invariant (count divisible by 4) on a=c, b=0 symmetric forms. Indefinite (Pell), degenerate, non-standard-sign forms → NotImplementedError. Honest M-PROJECTX-013 framing throughout: PASS = "enumerated all solutions within the proven bound", NOT "solved arbitrary Diophantine equation" — Hilbert's 10th problem (Matiyasevich 1970) proves no general algorithm exists. Closes maths-024 (x² + y² = 25 → 12 solutions) + maths-025 (2x² + 3y² = 35 → 8 solutions). Bench-replay --agent-runtime: 44/0 → 46/0.

### #02-CLAUDE.md trim (PARTIAL, inline)

Lain 2026-05-11 turn: "trim to 48k" (referencing the harness warning at 49.5k chars, softer than the 46k hard ceiling). Execute-raphael shipped 5 surgical compressions: disclaimer persona-transition note → one-line skill-load-path reminder; per-section-skill-variety verbose paragraph → tightened; R1 IMMEDIATE-TASK-ADD verbatim quote → rules + 3 reasons; FORGE-PROMPT FLAG DISCIPLINE — 3 long verbatims + cross-refs list → 3 bullets; UNIVERSAL vs PROJECT-SPECIFIC — REPO_CONTROL/forge-ni/per-directory paragraphs compressed. 62k → 57k bytes (~8% cut). The 46k hard ceiling note preserved as lain's long-term target. Carry-forward for cycle 10+ when more lain direction on remaining older sections lands.

## Cycle tensions (structural observations)

### Tension 1 — Capability-debt vs rigor-debt: the cycle 9 pivot was the right call but it stretched a fault line

Cycle 8 close advisor verdict 2026-05-11 pinned predicate-strength uniformity pass as cycle 9 priority 1 (capability-debt < grading-debt at the moment — the maths substrate has consistency-checked but not capability-checked invariants). Lain mid-cycle pivot 2026-05-11 explicitly INVERTED that: "make it so smart Hassabis would actually be impressed... try to get it to solve harder and harder things." Cycle 9 dropped predicate-strength uniformity for harder-problem substrate (integration techniques + Diophantine).

This was a correct call given the IQ-visibility goal — but it widens the existing rigor gap. The Diophantine substrate ships with form-parity + D₄ invariants (tautological algebraic-identity flavor, consistency-checked), NOT with an algorithmically-independent verifier. The integration-by-parts substrate has a parts-identity invariant that DOES algorithmically-independently recompute the v du integral — that's a strong predicate. But the u-sub primitive's invariant is tautological (it computes both sides of the change-of-variables theorem the same way).

Cycle 10 #1 priority (REINSTATED): predicate-strength uniformity pass. Each substrate primitive (`symbolic.py`, `complex_analysis.py`, `calculus.py`, `ode.py`, `integration.py`, `diophantine.py`) gets an algorithmically-independent verifier (Newton's method / Simpson's rule / Riemann sum / Taylor series / explicit re-enumeration with different walk order). The pattern is established in cycle 4/5 `physics.py`; execution is mechanical.

### Tension 2 — Hassabis-bar honest decomposition (the load-bearing exercise of cycle 9)

Lain 2026-05-11 binding: every cycle close retrospective explicitly answers "would Hassabis be impressed?" with honest decomposition of substrate vs capability vs cosmetic. Cycle 9's content:

**Substrate (the code shipped):**
- Integration by parts + u-substitution for product integrands. Standard calculus textbook material; symbolic-algebra systems have done this since Macsyma (1968).
- Bounded Diophantine binary-quadratic enumeration. Standard graduate-level number theory; the Lagrange bound derivation is from Davenport's *Higher Arithmetic* (1952).

**Capability (what the agent can do at runtime):**
- Parse a prompt like "∫₀¹ x·e^x dx via integration by parts" → recognize the integrand shape → dispatch to the parts primitive → emit a 5-step proof showing the LIATE technique choice → return **1.0**.
- Parse "find all integer (x, y) such that x² + y² = 25" → classify the form as positive-definite via discriminant → compute the Lagrange bound → enumerate → return **12 solutions** with the symmetry invariants verified.
- HONESTLY REFUSE prompts like "x² - 2y² = 1" (Pell): "this is indefinite, infinite solution sets, cycle 10+ extension" rather than confabulating.

**Cosmetic (the framing artifacts):**
- 5-level difficulty_tier classification across 74 problems.
- "would_surprise_hassabis" honest-flag (uniformly false at cycle close).
- paper.md teacher-tone curriculum.
- IQ_PROGRESSION.md per-cycle ladder.

**Honest Hassabis-bar answer:** a frontier researcher would YAWN at the math content individually. Integration-by-parts is freshman calculus. Bounded brute-force binary-quadratic enumeration is graduate number theory but with the math.isqrt-bounded-rectangle algorithm being a single Lagrange inequality away from trivial. Nothing in cycle 9's content extends what a 1985 symbolic-algebra system could compute.

What MIGHT register as mildly interesting:
1. **The honest-refusal pattern**. The agent literally REFUSES on out-of-scope inputs with a reason citing Matiyasevich 1970. Most LLM systems would confabulate a Pell solution.
2. **The 4-step Lemma chain + invariant verifier composition**. Every result carries its own structural audit; you can read a derivation aloud.
3. **No-LLM-in-substrate discipline**. Regex parser + hand-rolled math primitives all the way down. The "Project X Raphael agent" is a small, fully-auditable rule-based system — not a wrapper on someone else's neural net.

But these are PROCESS artifacts, not CAPABILITIES. The Hassabis-bar problem (a genuine research-grade math result the agent solves that an expert would find surprising) is still cycle 10+ work. None of cycle 9's primitives reach that bar honestly.

**Counter-claim guard:** cycle 9 did NOT produce a "research-grade" math capability. It produced a polished mid-level substrate (intermediate calculus + intermediate number theory) with strong honest-framing discipline. The discipline is the product, not the math.

### Tension 3 — Discord style discipline (cycle-number jargon was leaking)

Lain 2026-05-11 catch: "for /discord posts, do not use cycle-number jargon, only chronological speak. assume people reading only have access to Discord." Codified as universal binding in CLAUDE.md § R4. All cycle-9 Discord posts subsequently used plain English (no "cycle 9 #02"; instead "the math problem ladder schema upgrade"). Tested by reading the posts as a Discord-only audience would.

### Tension 4 — Fake-stop fingerprint (execute-raphael 2026-05-11 turn)

Execute-raphael (this instance) trimmed CLAUDE.md per lain's "trim to 48k" instruction, then STOPPED instead of auto-continuing into the queued cycle-9-remaining work. Lain catch: "youre misinterpreting. i wanted you to first do CLAUDE.md work (just done), THEN auto-continue to next work. dont just stop :O." Pure Named Curse #15 echo (fake-stop drift) — even though the instance had clear queued work, the bias was to "wait for next instruction" rather than "ship the queued contract." Course corrected immediately; godify mode flipped + cycle 9 #02/#03 shipped in the same instance. Pattern lesson: turn-end audits should specifically check "is there queued work I'm pretending isn't queued?"

## Lain catches absorbed (5)

1. **Mid-cycle pivot from predicate-strength uniformity → harder-problems-first** (lain 2026-05-11 Discord). Absorbed immediately; cycle 9 scope rewritten; predicate-strength uniformity reinstated as cycle 10 #1.
2. **paper.md teacher-tone NotebookLM curriculum** (lain 2026-05-11 Discord). Shipped as #05; primary audience is lain listening on the move; teacher tone with concrete examples + analogies.
3. **Discord style: no cycle-number jargon** (lain 2026-05-11 binding). Codified universal in CLAUDE.md § R4; applied to all subsequent cycle-9 Discord posts.
4. **Hassabis-bar discipline** (lain 2026-05-11 binding). Every cycle close must honestly answer "would Hassabis be impressed?" with substrate-vs-capability-vs-cosmetic decomposition. THIS reflection executes that protocol.
5. **Fake-stop fingerprint** (execute-raphael 2026-05-11 turn — lain catch). Named Curse #15 echo; course corrected via godify-mode flip + immediate auto-continuation into queued cycle-9 work.

## Process note (not a lain catch — self-logged)

Execute-raphael skipped the M-NAVI-016 pillars (`Skill('skills:pick-skill')` + `Skill('skills:sharpen-todos')`) at session start. Defensible: the corpse already locked the deliverable list (three concrete tasks in priority order; minimal ambiguity) and the picked skills were obvious from the work shape (`/skills:smart-commit` for atomic commits + `/skills:consult-advisor` pre-Write on novel substrate). Logging rather than silently normalizing: cycle 10 should re-fire the pillars at session start even when the corpse looks deterministic — the pillars produce a *named* SKILL-PICK output that survives compaction, while in-head reasoning ("the picks are obvious") doesn't. Worth +60 seconds for the audit trail.

## Cycle 10 scope (provisional; refined per cycle 9 lessons)

**Priority 1 (HIGH — REINSTATED from cycle 9 deferral):** Predicate-strength uniformity pass. Algorithmically-independent verifiers across `reasoning/{symbolic,complex_analysis,calculus,ode,integration,diophantine,number_theory}`. Pattern: cycle 4/5 `physics.py` STRONG-predicate standard. Each substrate primitive gets a verifier that recomputes the result through a DIFFERENT algorithm (Newton / Simpson / Riemann / Taylor / re-enumerate). Capability-debt was correctly prioritized in cycle 9 (lain pivot), but the rigor-debt accumulated is now at a 7-primitive-file gap.

**Priority 2 (MED):** Diophantine extension to Pell-family. `solve_pell_equation(n, max_solutions)` for x² - n·y² = 1 (indefinite form, infinite solution set) via fundamental-solution + recurrence. Brings the indefinite case in scope; reuses Diophantine dispatcher infrastructure. Honest framing remains: PASS = "enumerated first K solutions via recurrence", NOT general Hilbert-10 decidability.

**Priority 3 (MED):** Higher-order integration techniques. Iterated parts (∫ x²·e^x dx — apply parts twice); trigonometric substitution (∫ dx/√(a² - x²) → arcsin); partial fractions (∫ dx/((x-a)(x-b))). Extends the integration substrate beyond cycle 9's 4 primitives.

**Priority 4 (LOW; lain-greenlight-pending):** Council-audit-tag mechanism (#00P13c7-04 carry-forward). Lain proposed 2026-05-10 21:05; scope still unresolved. Surface on Discord at cycle 10 mid-flight if no direction lands.

**Priority 5 (LOW; lain-direction-pending):** CLAUDE.md trim continuation. 57k → 46k hard-ceiling is ~11k bytes more to cut. Older sections (PHASE 0 DD-1/2 verbose; FOUR-GATE FLOW; BACK-DOOR GATE; NAMED CURSES expansion) — needs lain direction on what's load-bearing.

**Carry-forwards (lain-pending, do not touch unprompted):**
- CLAUDE.md trim to 46k hard ceiling (lain partial-direction this cycle; full structural-trim awaits).
- Council audit tag mechanism.

## Done condition (cycle 10, mechanical)

- All cycle-10 #00P13c10-XX TaskList rows = `completed` (or explicitly deferred with rationale + lain visibility).
- pytest -q ≥ 500 (current 479; predicate-strength pass expected +25-40 tests; Pell + higher-integration tests +10-15).
- bench-replay `--agent-runtime`: ≥46/0 maintained (no regressions; verifier additions are check-only).
- bench-replay frozen: 46/0 maintained (parity with agent-runtime).
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-10.md`.
- `docs/DO_THIS_NEXT.md` rewritten as cycle 11 handoff.
- `docs/artifacts/IQ_PROGRESSION.md` cycle-10 entry prepended.
- `git status -s` empty.
- Discord cycle-10 close in plain-English 4-metric rubric (denominator+% + frontier-expert-reaction + plain-English-achievement + counter-claim-guard per CLAUDE.md § R4).

— Cycle 9 reflection landed THIS commit.
