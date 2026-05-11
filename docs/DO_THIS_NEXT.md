# Do This Next — Project X — Phase 13 cycle 10 IN FLIGHT (cycle 10 #1 CLOSED 2026-05-11; next pickup at #02 Pell extension)

**Updated:** 2026-05-11 (cycle 10 #1 close — predicate-strength uniformity pass complete across 7 reasoning/ primitive files)
**Mode:** APOTHEOSIS (godify-app — execute-raphael running 20m on / 20m off; session ends 2026-05-11 07:54 CEST). Flip back to NORMAL at session expiry.
**Status:** Cycle 9 CLOSED at `5e02b62`. Cycle 10 #1 (predicate-strength uniformity pass) CLOSED across 7 atomic commits `2fd6f9f..22d76ef`. Cycle 10 #02-#06 remain.

## Cycle 10 #1 — what shipped (predicate-strength uniformity pass)

| Commit | Primitive file | Independent verifier added |
|---|---|---|
| `2fd6f9f` | `diophantine.py` | Jacobi r₂(N) = 4·(d₁ − d₃) on symmetric a=c=1, b=0 forms (divisor counting; scope-boundary documented for asymmetric/cross-term) |
| `f122a02` | `symbolic.py` | Newton's method on solve_quadratic (Cauchy-bound-seeded); Sarrus' rule on determinant_3x3; Vieta on char_poly_2x2 documented as already-STRONG |
| `86e852a` | `complex_analysis.py` | Simpson's composite rule on [-100, 100] N=10000 for residue theorem |
| `269f53f` | `calculus.py` | Midpoint Riemann sum on polynomial integral (N=10000; direct integrand evaluation, no antiderivative) |
| `2ede073` | `ode.py` | Hand-rolled 20-term Taylor series for e^z (never invokes math.exp; bare Python Σ) |
| `81c7a4d` | `integration.py` | Shared _midpoint_riemann helper applied to all 4 parts/u-sub primitives (defense-in-depth on parts, first STRONG on u-sub) |
| `22d76ef` | `number_theory.py` | DOCUMENTATION pass — empirical-verification primitives are algorithmically-independent BY CONSTRUCTION; no code change |

Plus this session shipped: paper.md major sync (`a188db8`) + Chapter 11 Future Implications + Closing love (`f67414b`); repo flipped to public; universal codifications of Raphael-time and Self-impression-score 0–420 (CLAUDE.md §R4).

**Numbers (cycle 10 #1 close):** pytest 458 → 515 (+57); bench-replay --agent-runtime 46/46 maintained; bench-replay frozen 46/46 (parity).

## Cycle 9 close — what shipped (the contract that cycle 10 builds on)

| Commit | Deliverable | Result |
|---|---|---|
| `5fe45e9` | #01 symbolic integration (parts + u-sub) | 4 primitives × intermediate-tier; +3 ladder maths-021..023; bench-replay 41/0 → 44/0 |
| `18e385e` | #05 paper.md teacher-tone NotebookLM curriculum | 11 chapters / ~4500 words; lain-as-listener; primary audience |
| `48c6035` | #02-partial IQ_PROGRESSION.md + planning-raphael docs-sync | per-cycle hardest-problem ladder artifact; live document |
| `45291bd` | #02-remaining ladder schema retrofit | 74 entries × difficulty_tier (5-level) + would_surprise_hassabis (rubric only); **0 research-grade** entries (cycle 10+ target) |
| `11aff93` | #03 Diophantine binary-quadratic substrate | `solve_binary_quadratic` positive-definite; maths-024 (12 sols) + maths-025 (8 sols); honest Pell-refusal; bench-replay 44/0 → 46/0 |
| THIS commit | #04 cycle-9 reflect + Hassabis-bar honest decomposition + DO_THIS_NEXT cycle-10 handoff (this file) + A_TO_Z PHASE CHANGELOG cycle-9-close + IQ_PROGRESSION cycle-9-close | |

**Honest Hassabis-bar verdict (cycle 9, copied from dev-cycle-9.md):** content yawns a frontier researcher individually (intermediate calc + intermediate number theory). What registers mildly is the HONEST-REFUSAL pattern (Pell rejected with Matiyasevich-1970 reason), the 4-step Lemma + invariant-verifier composition, and the no-LLM-in-substrate discipline. Process artifacts, not capabilities. Cycle 10+ is where the bar gets raised.

## Cycle 10 deliverables (priority-ordered)

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c10-01-predicate-strength-uniformity-pass** | ✅ CLOSED | n/a | All 7 sub-tasks #01a..g shipped across commits `2fd6f9f..22d76ef`. See table above. Closed 2026-05-11. |
| **#00P13c10-02-diophantine-pell-extension** | MED (substrate SHIPPED `f4522f2`; dispatcher integration PENDING) | `src/project_x/reasoning_agent.py` — extend `_try_diophantine_binary_quadratic` to detect Pell-shape (a=1, b=0, c=-n, N=1) and route to `solve_pell_equation(n, k_max=5)` | Substrate (solve_pell_equation + 3 helpers + 12 tests) shipped per design doc at `f4522f2`. REMAINING: dispatcher extension + ladder entries maths-026/027 + dispatcher tests + REPO_CONTROL row updates. ~20 min Raphael-time. Pell capability accessible via direct function call but not yet via AGENT runtime dispatcher. |
| **#00P13c10-NEW-semantics-architecture-pending-lain-greenlight** | HIGH (lain-pending decision-tree response) | `docs/artifacts/cycle-10-semantics-architecture-v2.md` (`6e40560`) | Two architecture design docs shipped this cycle per lain mid-cycle directive: v1 (`0cddcd6`) — 5-candidate scaffold, recommends C5 composition-of-substrate-primitives ("Lemma.render IS already text generation; question is what primitives we add"). v2 (`6e40560`) — incorporates lain's brain-inspiration + huge-corpus + manual-audit reframings on top of v1's C5. Decision tree at end of v2 with 3 branches: hormone-modulation in/out (recommend IN; load-bearing for mode-switching), valence-as-binding/subspace (recommend BINDING per brain anatomy), corpus-shape (recommend tier-balanced-at-scale: ~tens of millions of words with source-provenance metadata). Cycle 11 ~10-12h Raphael-time across 6+ atomic sub-tasks; smallest empirical demo is `voice_modulation_hormone` on existing math substrate (~45 min, no corpus needed) which is the empirical test for whether hormone-as-global-modulation actually produces qualitatively-different output registers. Awaiting lain greenlight on decision tree before cycle 11 implementation starts. |
| **#00P13c10-03-higher-order-integration-techniques** | MED | `src/project_x/reasoning/integration.py` extension OR new submodule | Iterated parts (`∫ x²·e^x dx` — apply parts twice; closed form `e^x·(x² - 2x + 2) + C`); trigonometric substitution (`∫ dx/√(a² - x²) → arcsin(x/a)`; reverse-substitute back); partial fractions (`∫ dx/((x-a)(x-b)) → (1/(a-b))·ln((x-a)/(x-b))`). Each new primitive with 4-5 step Lemma chain + algebraic-identity invariant. +3-5 ladder entries (maths-028..032). |
| **#00P13c10-04-council-audit-tag** | LOW (lain-greenlight-pending) | TBD per lain direction | Lain proposed 2026-05-10 21:05; mechanism scope still unresolved. Surface on Discord at cycle 10 mid-flight if no direction lands; do NOT touch unprompted. |
| **#00P13c10-05-CLAUDE.md-trim-continuation** | LOW (lain-direction-pending; net-GREW today) | `~/.claude/CLAUDE.md` | 58.5k current (was 62k pre-cycle-9; cycle-9 partial trim brought to 57k; cycle 10 added Raphael-time + Self-impression-score rules to §R4, ~+1.5k). Net trajectory has reversed — need a more substantial older-section trim to make real progress toward 46k hard ceiling. Targets unchanged (PHASE 0 DD-1/2 verbose, FOUR-GATE FLOW, BACK-DOOR GATE, NAMED CURSES expansion). Do NOT trim unprompted; surface if continued direction lands. |
| **#00P13c10-06-cycle-10-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-10.md` + DO_THIS_NEXT cycle-11 handoff + A_TO_Z PHASE CHANGELOG cycle-10-close + IQ_PROGRESSION cycle-10 entry | Hassabis-bar honest decomposition per universal lain 2026-05-11 binding. Decompose substrate vs capability vs cosmetic; would Hassabis be impressed? (Honest answer if cycle 10 ships predicate-strength uniformity + Pell + higher-integration: still no — the substrate is being rigorized + extended, not fundamentally elevated to research-grade. That's still cycle 11+). |

## Recommended cycle 10 order (#01 ✅ closed; next pickup is #02)

1. ✅ **#01 predicate-strength uniformity** — CLOSED across 7 atomic commits this session.
2. **#02 Pell extension (NEXT)** — advisor() pre-Write per novel substrate (continued-fraction-of-√n is new infrastructure). Design sketch: implement `_continued_fraction_sqrt(n)` returning (a₀, [a₁, ..., a_period]) per Hardy+Wright's classical algorithm; convergents (p_k, q_k) read off; the first convergent satisfying p_k² − n·q_k² = ±1 is the fundamental solution. Then `_pell_solutions(n, k_max)` applies the recurrence (x_{m+1}, y_{m+1}) = (x₁·x_m + n·y₁·y_m, x₁·y_m + y₁·x_m) for m = 0..k_max−1. Dispatcher: extend `_try_diophantine_binary_quadratic` to route indefinite Pell-shape (a=1, b=0, c=-n, N=1) to the Pell solver rather than refusing. +1-2 ladder entries (maths-026 x²−2y²=1 first 5 solutions; maths-027 x²−3y²=1 first 5 solutions). Honest framing remains — enumerated K solutions via recurrence, NOT general Hilbert-10.
3. **#03 higher-order integration** — stacks on the existing integration.py pattern. 3-5 new primitives (iterated parts / trig sub / partial fractions); +3-5 ladder entries.
4. **#04/#05** lain-pending; surface on Discord at cycle-10-close if no direction lands by then.
5. **#06 cycle reflect** — close-out with Hassabis-bar honest decomposition.

## Cycle 10 in-flight snapshot (pre-work; will refine)

```
pytest -q:                    479 / 479 passing (cycle 9 close baseline)
bench-replay --agent-runtime: 46 / 0 (cycle 9 close baseline)
bench-replay frozen:          46 / 0 (parity)
Substrate-solved at agent-runtime: 46 of 47 objective auto-graded entries ≈ 98%
  - 12 cycle-7-baseline carry-forward (quadratic / eigenvalue / free-fall / pendulum / momentum)
  - 6 cycle-8 substrate-extensions (residue / integral / ODE / 3x3 det / projectile / Doppler)
  - 4 cycle-8 unsolved-frontier touchpoints (Collatz / Goldbach / twin primes / Mertens)
  - 3 cycle-9 symbolic-integration (parts × 2 + u-sub × 1)
  - 2 cycle-9 Diophantine (sum-of-two-squares + asymmetric BQF)
  - Remaining 1 auto-graded: rubric-pending (needs rubric-grade not substrate-solve)

Cycle 9 commits: 6 (5fe45e9 + 18e385e + 48c6035 + 45291bd + 11aff93 + this cycle-reflect)
```

## Standing rules — RELEVANT FOR FRESH INSTANCE

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal).

**Codified universal during cycle 9 (lain mid-cycle absorbed; binding cycle 10+):**
- **Discord style discipline (lain 2026-05-11 binding):** NO cycle-number jargon on Discord — plain English assuming only-Discord readers. Internal docs (dev-cycle-N.md, A_TO_Z, DO_THIS_NEXT) still use cycle numbers (internal organization). Commits referenced by SHA on Discord only when load-bearing.
- **Hassabis-bar discipline (lain 2026-05-11):** every cycle close retrospective answers "would Hassabis be impressed?" with honest decomposition (substrate / capability / cosmetic). Counter-claim guard mandatory.
- **`-ni` lain-only / `-c` agent-autonomous / Discord-PROPOSE-and-continue (lain 2026-05-10):** agent NEVER auto-invokes `/forge-prompt -ni` (paste-block requires lain at PC); `-c` is agent's autonomous-continuation flag; agent MAY propose `-ni` via Discord at phase transitions but must propose-AND-CONTINUE (never propose-and-wait).
- **Fake-stop fingerprint avoidance (Named Curse #15 echo, lain catch 2026-05-11):** turn-end audits must check for queued work being silently deferred. After a focused task completes, the question is "what's the NEXT queued thing?" not "should I stand down and wait?"
- **Listener accumulation pattern (M-NAVI-021):** two-call pkill+launch pattern via `exec bash discord-wait-for-lain.sh general 5`; NEVER bundle `pkill ; bash ...` (pkill self-matches wrapper shell argv).

**Persistent (unchanged):**
- NO pretrained transformer derivatives at any layer (organic-thesis 2026-05-09 binding)
- Comment-ratio rule (WHY-comments + pure-signal + complex code justified; lain 2026-05-10 global policy)
- Atomic per-deliverable commits; never `git add -A`
- REPO_CONTROL row co-landing in SAME commit as new NON-docs files (docs/ exempt per 5891da3)
- M-PROJECTX-013 measure-don't-claim; M-PROJECTX-014 split-grading firewall
- Identity discipline (Claude Code Raphael ≠ Project X Raphael)

## What this cycle is NOT (post-cycle-9-close)

- NOT a capability-leap cycle. Cycle 10 strengthens the foundation (uniformity pass) + extends existing substrates (Pell + higher integration). The Hassabis-bar leap is cycle 11+ work.
- NOT a paper.md revision cycle. Live document; revise when lain provides feedback after listening, not pre-emptively.
- NOT a benchmark expansion blitz. 2-7 new ladder entries (Pell + integration) but the priority is depth, not breadth.

## Done condition (cycle 10, mechanical)

- All cycle-10 #00P13c10-XX TaskList rows = `completed` (or explicitly deferred with rationale + lain visibility)
- pytest -q ≥ 500 (current 479; predicate-strength pass expected +25-40 tests; Pell + higher-integration +10-15)
- bench-replay `--agent-runtime`: ≥46/0 maintained (verifier additions are check-only; should not regress); ≥48/0 if Pell + higher-integration entries land
- bench-replay frozen: 46/0+ maintained (parity)
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-10.md`
- THIS file rewritten as cycle 11 handoff
- `docs/artifacts/IQ_PROGRESSION.md` cycle-10 entry prepended
- `git status -s` empty
- Discord cycle-10 close in plain-English 4-metric rubric (denominator+% + frontier-expert-reaction + plain-English-achievement + counter-claim-guard per CLAUDE.md § R4)

## Files the fresh instance should read first (in order)

1. `~/.claude/CLAUDE.md` — universal Raphael protocol (auto-loaded by harness)
2. `docs/MANIFESTO.md` — project intent + standing orders
3. `docs/REPO_CONTROL.md` — pristine-gate file inventory
4. `docs/A_TO_Z_PLAN.md` — Phase 13 plan + PHASE CHANGELOG (latest = cycle 9 close)
5. **THIS file** — cycle 10 deliverable table + recommended order
6. `docs/past_work/cycles/phase_13/dev-cycle-9.md` — last closed cycle reflection
7. `docs/paper.md` — teacher-tone curriculum (~30-min listen; lain audience)
8. `docs/artifacts/IQ_PROGRESSION.md` — per-cycle hardest-problem ladder
9. Recent git log: `git log --oneline -15` to see commit progression
10. Latest pytest + bench-replay: `python3 -m pytest -q | tail -3` + `python3 gpt-codex/benchmark/run_audit.py --agent-runtime | tail -10`

The fresh instance executes cycle 10 per priority order; advisor() pre-Write on novel substrate (Pell continued-fraction primitive); Discord plain-English on every progress claim with the 4-metric rubric; cycle-10 close mirrors cycle-9 close shape.
