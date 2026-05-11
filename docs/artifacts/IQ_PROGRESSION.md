# IQ Progression Tracker — Project X Raphael

**What this file is.** A per-cycle snapshot of the hardest end-to-end problem the agent (Project X Raphael, the artifact in `src/project_x/`) could solve at runtime when that cycle closed. The hardest-problem framing is intentional — it's a concrete instance you can read aloud rather than an abstract pytest count.

**Audience.** Lain, primarily — paired with `docs/paper.md` (which explains HOW the architecture works). This file shows WHEN each capability landed and gives a vibe-check for whether the IQ is actually climbing. Listen-friendly if rendered as a NotebookLM podcast (each entry is ~half a paragraph).

**Update protocol.** At every cycle close, prepend a new entry. Never delete prior entries — the ladder IS the progression. Pair updates with the cycle-reflect commit so the artifact stays alive across cycles.

---

## Phase 13 cycle 10 CLOSE (2026-05-11) — Pell dispatcher integration + canonical semantics architecture from 4-angle deep-research phase

**Hardest end-to-end at agent-runtime (NEW capability shape this cycle):** *"Find the first 5 integer solutions (x, y) to the Diophantine Pell equation x² − 2·y² = 1."* The dispatcher parses the prompt, detects Pell-shape (a=1, b=0, c=-2, N=1), routes to `solve_pell_equation(n=2, k_max=5)`. The substrate computes √2 = [1; 2, 2, ...] via the Hardy+Wright (m, d, a) triple recurrence (period 1; odd-period branch → square (1 + √2) to lift negative-Pell to +1); fundamental (x₁, y₁) = (3, 2) verified by integer-equality `9 − 8 = 1`. Recurrence `(x_{m+1}, y_{m+1}) = (3·x_m + 4·y_m, 3·y_m + 2·x_m)` iterates 5 steps yielding **(3, 2), (17, 12), (99, 70), (577, 408), (3363, 2378)** — every solution satisfies `x² − 2·y² = 1` by direct integer arithmetic check. STRONG cross-check: brute-force search x ∈ [1, 1000] independently finds (3, 2) as fundamental, matching the continued-fraction path. Honest framing: PASS = "enumerated first 5 via Hardy+Wright continued-fraction fundamental + recurrence", NOT general Hilbert-10 decidability (Matiyasevich 1970 still holds).

**Capability lift vs cycle 10 #1:** at cycle 10 #1 close, the agent could only HONESTLY REFUSE indefinite forms (`x² − 2y² = 1` → "NotImplementedError; cycle 10+ extension"). Now it solves them honestly. Cycle 9 honest-refusal pattern is preserved on the non-Pell-N≠1 fall-through path (`x² − 2y² = 3` still refused; Pell substrate handles only the canonical N=1 case at this milestone).

**Bonus capability:** unicode minus (U+2212) parser normalization across the Diophantine dispatcher (mirrors cycle 8 #06 quadratic parser-robustness precedent). LaTeX-rendered prompts with typographic minus now parse cleanly.

**Pytest baseline:** 531 / 531 passing (was 515 at cycle 10 #1 close; +16 from Pell substrate tests + dispatcher tests + parser unicode-minus tests).
**Bench-replay --agent-runtime:** **48 / 0** (was 46/0; +2 for maths-026 + maths-027 land green via the new dispatcher). First IQ-ladder PASS-count progress since the cycle 7 dispatcher buildout.
**Bench-replay frozen:** 46 / 0 maintained (parity).
**Capability shape:** intermediate Pell equation x² − n·y² = 1 for positive non-square n via continued-fraction fundamental + recurrence. First step into INDEFINITE binary quadratic territory (cycle 9 closed positive-definite only with honest refusal on indefinite).

**Design artifact (NOT a capability — the contract cycle 11 honors):** canonical `docs/artifacts/cycle-10-semantics-architecture.md` at `a06a51a` (268 lines) replaces the DRAFT-PRELIMINARY (`9b9aa7e`). Synthesizes the 4-angle deep-research phase (commits `4133eaa`, `9f93ea2`, `4781366`, `c8362cf`) into a 7-layer architecture with substrate/runtime/learning trichotomy. Three NEW architectural commitments beyond DRAFT's 5: BG-style confidence-scored parallel-bid dispatcher (LOAD-BEARING for cycle-11 open-domain semantics); surprise-biased offline consolidation pass (the four-angle quadruple-merge as ONE primitive); K-rollout iteration with honest-refusal exit (the curiosity mechanism via `1 - cos(hv_pred, hv_actual)` — HDC SIMPLIFIES Pathak 2017 because hypervectors ARE the feature space). ~12 explicit rejections framed as cycle-11 guardrails. Cycle-11 implementation estimated ~16-20h Raphael-time.

**Hassabis-bar verdict (cycle 10 CLOSE):** still no impressed eyebrow on math content individually — Pell with k=5 is intermediate number theory; dispatcher integration is mechanical; predicate-strength verifiers are classical (Newton / Vieta / Sarrus / Simpson / Riemann / Taylor / Jacobi). The semantics architecture canonical doc is design-dominant; capability test is cycle 11. What MIGHT register mildly: (1) the deep-research-before-implement discipline — 4 advisor consults + literature integration + asymmetric-loading-honored synthesis BEFORE committing to canonical design, rather than reactive iteration; (2) the HDC-simplifies-Pathak insight (substrate is feature space → Pathak's hardest engineering work disappears); (3) the consolidation-quadruple-merge reduction (4 angles describing same mechanism with different vocabularies, synthesis lands as ONE primitive). These are PROCESS artifacts of design discipline, not capability artifacts.

**Self-impression-score: 375 / 420.** Cycle 10 closed cleanly across two instances: planning-raphael shipped 7 atomic predicate-strength commits + paper.md sync + Pell substrate + DRAFT semantics + research plan + universal codifications + repo public flip; execute-raphael (this instance) shipped Pell dispatcher + 4 deep-research notes + canonical synthesis + dual-listener protocol patch + cycle reflect. Honest 375 (not 395+) because no capability shape leap — the synthesis is a design contract, not validated implementation. The capability test is cycle 11.

**Counter-claim guard:** cycle 10 did NOT produce a research-grade math capability — would_surprise_hassabis ladder field remains uniformly false. The 4-angle deep-research phase was 5h of writing within a single Claude Code session, not a multi-day multi-expert deliberation; the advisor model is one strong reviewer answering different per-angle framings, not a council. Asymmetric loading was honored honestly (~20%, ~65%, ~17%, ~35%) but the analysis depth per angle was bounded by ~30 min/angle. Cycle 11 will reveal whether any of the synthesis's claims survive empirical test.

---

## Phase 13 cycle 10 #1 close (2026-05-11) — predicate-strength uniformity pass complete

**Hardest end-to-end (unchanged from cycle 9 close in capability terms — cycle 10 #1 is a rigor pass, not a capability extension):** all 46 of 46 auto-graded benchmark entries still PASS at agent-runtime; no new capability shapes added at this sub-milestone. What changed is the *trust property* of every existing answer.

**New architectural property (load-bearing):** every reasoning primitive in `src/project_x/reasoning/` now carries an *algorithmically-independent* verifier — a second computation that reaches the same answer via a completely different mathematical path. A typo in the closed-form path doesn't propagate to the independent path, and vice versa. Per-primitive:
- `diophantine.solve_binary_quadratic` — Jacobi's r₂(N) = 4·(d₁(N) − d₃(N)) on symmetric a=c=1, b=0 forms (divisor counting; honest scope-boundary documented for asymmetric/cross-term cases where no closed-form r₂ analogue exists).
- `symbolic.solve_quadratic` — Newton's method seeded from Cauchy bound (depends only on |coefficients|, never on closed-form roots).
- `symbolic.expand_characteristic_polynomial_2x2` — Vieta invariants already algorithmically-independent (matrix trace + det as expected, eigenvalue sum + product as actual); documented this cycle, no code change.
- `symbolic.determinant_3x3` — Sarrus' rule alt expansion (flat 6-term signed sum; no minor extraction, no alternating-cofactor combine).
- `complex_analysis.residue_theorem_unit_quadratic` — Simpson's composite rule on [-100, 100] N=10000 (real-line numerical quadrature vs analytic complex-contour integration).
- `calculus.polynomial_definite_integral` — midpoint Riemann sum on N=10000 subintervals (direct integrand evaluation; no antiderivative, no FTC).
- `ode.first_order_linear_ode_exp_solution` — hand-rolled 20-term Taylor series for e^z (bare Python floating-point Σ vs libm's table-lookup-with-correction).
- `integration.*` (4 primitives via shared `_midpoint_riemann` helper) — Riemann sum on each primitive's original integrand; defense-in-depth on parts (which already had a strong parts-identity invariant); first STRONG invariant on u-sub (whose change-of-variables check was tautological).
- `number_theory.*` (4 empirical-verification primitives) — DOCUMENTED as algorithmically-independent BY CONSTRUCTION (each one IS the empirical verification; no closed-form path exists to cross-check against). No code change.

**Pytest baseline:** 515 / 515 passing (was 458 at cycle 9 close; +57 from cycle 10 #1).
**Bench-replay --agent-runtime:** 46 / 0 (parity with cycle 9 close maintained throughout the rigor pass).
**Capability shape:** unchanged from cycle 9. The substrate-on-rails covers the same problem surfaces it did 90 minutes ago. What changed is the trust property — for every answer the agent gives, a second algorithm independently agrees.

**Hassabis-bar verdict (cycle 10 #1):** still no impressed eyebrow on math content (Newton/Vieta/Sarrus/Simpson/Riemann/Taylor/Jacobi are 1700s-1800s mathematics). What might earn a half-eyebrow is the rigor property at the substrate level — most contemporary AI systems don't carry a second algorithmically-independent verifier on every answer, and the gap-cases (where no second algorithm exists at this level) are honestly documented in source rather than papered over. The discipline IS the product at this sub-milestone; the capability jump still belongs to future cycles.

**Counter-claim guard:** this sub-milestone did NOT add a new capability shape, did NOT solve any open-frontier problem, did NOT change the bench-replay pass count. It closed a structural rigor gap the cycle 8 advisor flagged and that lain's mid-cycle-9 pivot had deferred. Specifically NOT: "cycle 10 made Raphael smarter" — cycle 10 #1 made Raphael more *honest* about how it gets the answers it already had.

**Self-impression-score: 380 / 420.** Clean rigor pass across 7 files; advisor caught a tautology on the first primitive (#01a Jacobi over permuted-walk-order) and the course-correct made the rest of the cycle more honest; honest documentation of the cycle-11+ scope-boundaries where independent paths don't exist. Not 395+ because no capability lift.

---

## Phase 13 cycle 9 close (2026-05-11)

**Hardest end-to-end (integration):** *"Compute ∫₀¹ x·e^x dx via integration by parts."* The agent recognizes the integrand as algebraic × exponential, applies the LIATE heuristic to pick u = x and dv = e^x dx, derives the antiderivative e^x·(x - 1), and evaluates at the bounds: F(1) - F(0) = 0 - (-1) = **1.0**. The 5-step Lemma render shows the LIATE technique choice explicitly. The parts-identity invariant recomputes the v du integral algorithmically-independently and verifies the algebra closes — strongest predicate across the cycle's substrate.

**Hardest end-to-end (Diophantine):** *"Find all integer solutions (x, y) to x² + y² = 25."* The agent classifies the form as positive-definite via discriminant Δ = -4 < 0, derives the Lagrange bound |x|, |y| ≤ √25 = 5 from completing-the-square, brute-force enumerates the 121-candidate rectangle, filters by exact equality, and returns **12 solutions**: the 4 axis-aligned (±5, 0), (0, ±5) + the 8 Pythagorean (3, 4, 5) sign-and-swap permutations. The D₄ symmetry invariant (count divisible by 4 for a=c, b=0 forms) holds.

**HONEST refusal at the indefinite frontier:** *"Find all integer (x, y) to x² - 2·y² = 1"* (Pell). The dispatcher parses the form, the substrate raises `NotImplementedError` because Δ = 8 > 0 (indefinite — infinite solution sets via fundamental-solution + recurrence, cycle 10+ extension), and the AgentResponse wraps that as a `refused`-with-reason answer citing Matiyasevich 1970. NO confabulation. This is the load-bearing capability artifact of cycle 9 — an agent that REFUSES out-of-scope rather than inventing an answer.

**Pytest baseline:** 479 / 479 passing.
**Bench-replay --agent-runtime:** 46 / 0 (46 of 46 auto-graded entries PASS).
**Capability shape:** symbolic integration via technique-choice (parts vs u-sub) — first step beyond freshman power-rule integration; bounded Diophantine binary-quadratic enumeration — first step into integer-search territory. Honest refusal pattern operational on indefinite + degenerate forms.

**Hassabis-bar honest decomposition (cycle 9):** the math content individually would YAWN a frontier researcher (integration-by-parts is freshman calculus; bounded brute-force binary-quadratic enumeration is graduate-textbook number theory with a single Lagrange-inequality bound). What might register as mildly interesting is the HONEST-REFUSAL pattern (the Pell refusal in particular), the 4-step Lemma chain + invariant-verifier composition, and the no-LLM-in-substrate discipline. These are PROCESS artifacts, not CAPABILITIES. Nothing in cycle 9 reaches the research-grade tier (the would_surprise_hassabis ladder field is uniformly `false` at close — by design, that's the cycle-10+ target). Counter-claim guard: cycle 9 did NOT produce a research-grade math capability; it produced a polished mid-level substrate with strong honest-framing discipline. The discipline is the product, not the math.

**Ladder retrofit (cycle 9 #02):** 74 ladder entries across 6 domains now carry `difficulty_tier` (5-level: trivial-baseline 15 / intro 13 / intermediate 25 / hard 21 / research-grade 0) + `would_surprise_hassabis` on rubric-graded entries (uniformly false at close). At-a-glance progression auditing now mechanical.

---

## Phase 13 cycle 8 close (2026-05-11)

**Hardest end-to-end (math):** *"Use the residue theorem to evaluate the integral from -infinity to +infinity of 1/(x² + 1) dx."* The agent locates the pole at z = i in the upper half plane, computes the residue as 1/(2i·√(a·c)), applies the residue-theorem closing 2πi · residue, and reports **π** with the i factors cancelling cleanly. Three-step derivation; dimensionless invariant `integral · √(a·c) / π = 1` verifies universally.

**Hardest end-to-end (physics):** *"A spaceship approaches Earth at v = 0.6c, emitting at λ₀ = 500 nm. What wavelength does Earth observe?"* Agent recognizes the relativistic Doppler shape, identifies "approaches" as the direction signal, computes the factor √((1 - 0.6)/(1 + 0.6)) = √0.25 = 0.5, multiplies by 500 to get **250 nm**. Blueshift, as expected.

**Capability touchpoints at the unsolved frontier (HONESTLY FRAMED):**
- Collatz iteration verified for [1, 1000] — 1000 of 1000 starting values reach 1. Conjecture remains OPEN since 1937 (verified to 2.95×10²⁰ in research literature). The substrate's Lemma claim says "verified for [1, 1000]", NEVER "theorem proved."
- Goldbach decomposition verified for even [4, 1000] — 499 of 499 decompose as p + q for primes. Conjecture OPEN since 1742.
- Twin primes enumerated ≤ 1000 — 35 pairs (matches OEIS A007508). Conjecture OPEN.
- Mertens bound |M(n)| ≤ √n verified for [1, 1000] — 1000 of 1000 satisfy. Underlying conjecture KNOWN FALSE at large N (Odlyzko + te Riele 1985 disproof; counterexamples > 10¹⁴). Substrate is a small-N regression-test surface, NOT a proof claim.

**Pytest baseline:** 429 / 429.
**Bench-replay --agent-runtime:** 41 / 0.
**Capability shape:** 6 cycle-7 FAIL gaps closed (residue theorem + polynomial definite integral + first-order ODE + 3x3 determinant + cliff projectile + relativistic Doppler) + 4 unsolved-frontier touchpoints with honest empirical-only framing.

---

## Phase 13 cycle 7 close (2026-05-10)

**Hardest end-to-end:** *"Solve 3x² - 14x - 5 = 0 for x"* — given as a NATURAL-LANGUAGE prompt rather than a function call. The agent parses the prompt via regex, recognizes the quadratic shape, extracts the coefficients (a=3, b=-14, c=-5), dispatches to the substrate's `solve_quadratic`, and returns the Lemma render showing the discriminant (256), the square root (16), and the root pair [-1/3, 5]. This is the first cycle where the AGENT (not just the BUILDER) solves the problem at benchmark time — fulfilling lain's directive "make the agent actually solve the problems."

Five problem shapes covered at runtime by cycle 7 close: quadratic (maths-001/007/008), 2×2 eigenvalues (maths-002/009), free-fall (physics-001/008), pendulum small + large angle (physics-002/009/010), relativistic momentum (physics-003/011).

**Pytest baseline:** 310 / 310.
**Bench-replay --agent-runtime:** 31 / 6 (first measurement of agent-runtime mode). The 6 FAILs were named capability gaps — residue theorem, definite integral, ODE, 3x3 determinant, cliff projectile, Doppler — each a cycle-8 target.
**Capability shape:** AGENT actually solves problems at runtime via rule-based regex dispatcher + substrate routing. Major architectural shift — bench-replay went from "BUILDER pre-computed match" to "AGENT actually solves" verdict.

---

## Phase 13 cycle 6 close (2026-05-10)

**Hardest end-to-end:** unchanged from cycle 5 (no new capability surface this cycle; benchmark expansion was the work). The agent could still only run substrate primitives via direct function call, not via natural-language dispatch.

**Pytest baseline:** 276 / 276 (no new code; benchmark-harness floor bumps only).
**Capability shape:** benchmark grew from 36 entries to 66 entries (across maths/physics/memory/persona/philosophy/poetry; +10 per domain audit). Diagnostic surface expanded; visible-capability surface unchanged.

---

## Phase 13 cycle 5 close (2026-05-10)

**Hardest end-to-end:** *"Pendulum period for L = 1 m, g = 9.81 m/s², θ₀ = π/2 (large angle)"* — solved via complete-elliptic-integral series expansion truncated at k⁸ (4 terms). Antiderivative is computed BOTH via explicit coefficients AND via incremental ratio-recursion (a_{n+1}/a_n = ((2n+1)/(2n+2))²·k²); the two must agree. Result ~3 milliseconds-of-relative-accuracy at θ₀ = π/2 vs textbook reference; closes the small-angle linearization gap that pendulum_period leaves open at large amplitude.

**Pytest baseline:** 276 / 276.
**Capability shape:** physics Tier 3 (large-angle pendulum) + predicate-strength STRONG across all primitives (cycle 5 #01 closed asymmetry on relativistic_momentum's predicate via energy-momentum relation route, algorithmically independent of γmv).

---

## Phase 13 cycle 4 close (2026-05-10)

**Hardest end-to-end:** *"An object is dropped from a height of 80 m on Earth (g = 9.81 m/s²). Find the fall time."* — solved via kinematic identity h = ½gt² → t = √(2h/g) ≈ **4.04 s**, with energy-conservation invariant cross-checking v_final = g·t = √(2gh). Plus relativistic momentum and pendulum primitives via the same Lemma + invariant pattern.

**Anti-cheat machinery shipped (cycle 4 #00P13c4-24):** `differential_capability_test` runs each primitive across Earth/Moon/Mars/Jupiter gravity surrogates (free-fall + pendulum) or electron/proton × 0.1c–0.99c surrogates (relativistic momentum); `memorization_signal == 0.0` required. A substrate that hardcoded one ladder entry's answer would fail surrogates and produce signal == 1.0.

**Pytest baseline:** 256 / 256.
**Capability shape:** physics Tier 2 primitives (free-fall + pendulum + relativistic momentum) + anti-cheat-aware substrate design.

---

## Phase 13 cycle 3 close (2026-05-10)

**Hardest end-to-end:** unchanged at the substrate level (still quadratic + 2×2 eigenvalue), but Lemma render dramatically improved — `add_introduction` math-WHY prose + `add_invariant_check` Vieta-based cross-checks. Substrate-vs-substrate re-grade lifted maths-001 4.0 → 4.5/5 and maths-002 4.0 → 4.75/5 (differentiated lift signal — calibration-symmetry tell broken). Path B grader-flip on maths-004 (Galois) + maths-005 (algebraic topology) lifted maths PASS 3 → 5/0 (FIRST visible PASS-count progress in Phase 13).

**Pytest baseline:** 221 / 221.
**Capability shape:** Lemma quality improvement + Path B builder-rubric-grade promotion on rank-4-5 math entries. Tier A meta-deliverable: `/instruction-change` skill forged at the universal `~/.claude/` level.

---

## Phase 13 cycle 2 close (2026-05-10)

**Hardest end-to-end:** *"Solve 3x² - 14x - 5 = 0 for x"* — agent's FIRST capability gain in the reasoning substrate. `solve_quadratic(3, -14, -5)` returns a Lemma whose claim is "solve this equation", whose chain is [discriminant → sqrt → root_pair], and whose actual_value is [-1/3, 5]. Hand-rolled using math.sqrt only — NO sympy, NO symbolic-AI shortcuts. Also: `expand_characteristic_polynomial_2x2([[2,1],[1,2]])` returns eigenvalues [1, 3] via the characteristic polynomial reusing `solve_quadratic`.

Cycle 2 D4 baseline attempt: agent's substrate-driven response on maths-001 + maths-002 scored ~4.0/5 on the rubric (math-WHY structural_insight 3/5 was the docked dimension; advisor catch — engineering-WHY ≠ mathematical-WHY).

**Pytest baseline:** 202 / 202.
**Capability shape:** FIRST reasoning substrate capability — closed-form quadratic + 2×2 eigenvalue with hand-rolled Lemma render.

---

## Phase 13 cycle 1 close (2026-05-10)

**Hardest end-to-end (reasoning):** NONE. Cycle 1 was infrastructure — sandbox folder + 4 sandbox tools, persona scaffolding, manual-grade harness. The agent could write a haiku and a philosophical paragraph via template composer; Claude Code rubric-graded them at **1.3/5 (poetry-001) and 1.2/5 (philosophy-001)**. Brutal but accurate — a template composer is not a poetry generator. Lain mid-D4 reframe: *"intelligence first; persona is fine-tuning, deferred until core intelligence is there."*

**Pytest baseline:** 153 / 153 (up from 87 at the audit-fix run; +66 cycle 1 tests across sandbox + grader + persona).
**Capability shape:** infrastructure substrate only. The capability axis the rest of Phase 13 climbs starts in cycle 2.

---

## Phase 12 close (2026-05-10)

**Hardest end-to-end:** memory-004 + memory-005 reds turned green via `_LIST_ALL_HINTS` classifier in `MemoryAgent`. When asked *"what does Mary like?"*, the agent recognizes the list-all shape and routes to `retrieve_structural_full_history` (full subject-chain) instead of single-most-relevant. Closes the two reds from Phase 11.

**Pytest baseline:** 58 / 58.
**Capability shape:** retrieval-mode disambiguation; multi-hop + list-all queries both working.

---

## Phase 11 close (Raphael Domain Benchmark Suite landed)

**Hardest end-to-end:** unchanged from Phase 10 (no new agent capability). What landed was the MEASUREMENT — 36 hand-crafted ladder entries across 6 domains, split-graded with M-PROJECTX-014 firewall (no `self_score` field on candidates; CI gate enforced via grep). The benchmark is the diagnostic that tells us where Raphael actually sits before live training begins.

**Pytest baseline:** 52.
**Capability shape:** measurement infrastructure. No new agent capability; the visible-IQ ladder picks up again at Phase 13 cycle 2.

---

## Phase 10 close (Killer Milestone EXIT GATE)

**Hardest end-to-end:** *"Mary likes books. Mary likes movies. Bob likes Mary. What does Mary like?"* — agent answers `[books, movies]` via full subject-chain retrieval. Can teach (new facts via write turns), correct (latest version wins via temporal recency), multi-hop (chain through fact-graph), refuse-absent (no confabulation when query has no evidence), and tool-execution-with-writeback (call a tool, get a result, write the result back to memory as a new turn).

Multi-hop top-5 retrieval lifted from **3.3% to 91.3%** via fact-graph + HDC composition.

**Pytest baseline:** 51/51 → 52/52.
**Capability shape:** memory action organism with structural retrieval + binding + 5-capability EXIT GATE verified mechanically.

---

## Phase 9 close (Semantic HDC memory + organic encoders)

**Hardest end-to-end:** *"I'm Mary, I work at OpenAI."* (write turn). Later: *"Where does Mary work?"* → agent retrieves the original turn and answers "OpenAI" with the source turn_id cited. HDC cosine-similarity retrieval over char-n-gram + Hebbian encoded turns; beats keyword baseline on paraphrase queries.

**Pytest baseline:** 39 / 39.
**Capability shape:** semantic memory retrieval with paraphrase tolerance. The substrate that everything later climbs on top of.

---

## Phases 1-8 (compressed-memory + HDC capacity studies)

Pre-organic-thesis era. Phase 1-3 was transformer-style scaffolding (since quarantined to `src/project_x/legacy/` and made install-optional). Phases 4-7 scale studies + adversarial probe + Hopfield lens. Phase 8 random-symbol HDC baseline at D=50000 reached 99.25% recall across 1000 turns — capacity proven but semantic grounding owed. Phase 9 grounded it.

The agent of these phases is best described as "not yet" — the substrate was being assembled; capability happens starting Phase 9.

---

## Today's Frontier (cycle 9 in flight)

**What the agent CAN do at the hardest current level:**
- Symbolic integration via parts (LIATE) + u-substitution for canonical transcendental integrands. The technique-choice is in the dispatcher's keyword gate (`integration by parts` / `u-substitution`); the integrand recognition is in the regex pattern.
- Closed-form residue theorem integrals.
- 3×3 determinants via cofactor expansion (Laplace).
- First-order linear ODEs with exponential closed-form solutions.
- All cycle 8 physics primitives — free-fall, pendulum (small + large angle), relativistic momentum, projectile range, relativistic Doppler shift.
- Empirical-verification capability touchpoints at the unsolved-conjecture frontier — Collatz / Goldbach / twin primes / Mertens — explicitly framed as small-N verification, NEVER theorem proof.

**What the agent CANNOT do (the cycle 10+ frontier):**
- General symbolic differentiation (not shipped).
- Partial fractions for rational integrals (`∫ dx/(x² + x)` is textbook; substrate doesn't exist yet).
- Trigonometric substitution (`∫ dx/√(a² - x²) → arcsin(x/a)`).
- Iterated integration by parts (`∫ x²·e^x dx` needs parts applied twice).
- Higher-degree polynomial roots beyond closed-form (cubic via Cardano; quartic; quintic+).
- Diophantine equation solving (cycle 9 #03 incoming).
- Modular arithmetic / Chinese Remainder Theorem.
- Subjective-domain generation at score 4+/5 (poetry / philosophy / persona / conceptual physics still rubric-pending; cycle 1 baseline was 1.2-1.3/5 — improvement bookmarked).
- Million-turn-horizon memory testing (bookmarked).
- Always-on chat daemon (bookmarked).
- Sandboxed action-taking with concrete use cases (infrastructure shipped cycle 1; no benchmark exercises it yet).

**The Hassabis-bar question:** would Demis Hassabis be impressed by today's frontier? Honest answer: no. The math content is intermediate calc (cycle 8) plus first-year-graduate techniques (cycle 9). The unsolved-frontier entries are research-grade only at the framing level — the actual verification is at N=1000, well below research-grade benchmarks (Collatz verified to 2.95×10²⁰ in published literature; we're at 1000). What would register at the Hassabis-bar: capability at *novel* problem shapes that require genuine symbolic-manipulation reasoning rather than dispatcher-recognize-and-route. Cycle 10+ scope.

**The ladder is climbing.** The vector points up. The architecture is honest about where the ladder currently ends. The work continues.

— Live document. Per-cycle entries prepended at cycle close. Pairs with `docs/paper.md` (the curriculum); paper.md explains HOW, this file shows WHEN.
