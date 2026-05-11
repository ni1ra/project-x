# IQ Progression Tracker — Project X Raphael

**What this file is.** A per-cycle snapshot of the hardest end-to-end problem the agent (Project X Raphael, the artifact in `src/project_x/`) could solve at runtime when that cycle closed. The hardest-problem framing is intentional — it's a concrete instance you can read aloud rather than an abstract pytest count.

**Audience.** Lain, primarily — paired with `docs/paper.md` (which explains HOW the architecture works). This file shows WHEN each capability landed and gives a vibe-check for whether the IQ is actually climbing. Listen-friendly if rendered as a NotebookLM podcast (each entry is ~half a paragraph).

**Update protocol.** At every cycle close, prepend a new entry. Never delete prior entries — the ladder IS the progression. Pair updates with the cycle-reflect commit so the artifact stays alive across cycles.

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
