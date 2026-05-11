# Do This Next — Project X — Phase 13 cycle 10 handoff (cycle 9 CLOSED 2026-05-11 — REINSTATING predicate-strength uniformity pass as #1 priority)

**Updated:** 2026-05-11 (cycle 9 close; cycle 10 handoff)
**Mode:** APOTHEOSIS (godify-app — execute-raphael running 20m on / 20m off; session ends 2026-05-11 07:54 CEST). Flip back to NORMAL at session expiry.
**Status:** Cycle 9 CLOSED with 5 atomic deliverables shipped + cycle-reflect committed. Cycle 10 reinstates the predicate-strength uniformity pass that lain's mid-cycle-9 pivot deferred.

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
| **#00P13c10-01-predicate-strength-uniformity-pass** | HIGH | `src/project_x/reasoning/{symbolic,complex_analysis,calculus,ode,integration,diophantine,number_theory}.py` — algorithmically-independent verifier per primitive | REINSTATED from cycle 9 deferral. Cycle 8 close advisor verdict 2026-05-11 pinned this as cycle 9 #1 before lain pivoted to harder-problems-first. Capability-debt was correctly prioritized in cycle 9, but the rigor-debt is now at a 7-primitive-file gap. Pattern: cycle 4/5 `physics.py` STRONG-predicate standard. Per-primitive verifier candidates: `symbolic.py` quadratic via Newton's method + Vieta cross-check, 2x2 eigenvalue via Vieta, 3x3 determinant via Sarrus alt expansion; `complex_analysis.py` residue via Simpson's-rule numerical-integration on [-100, 100]; `calculus.py` polynomial integral via Riemann sum / midpoint rule; `ode.py` first-order linear via Taylor series for e^(kx) (manual factorial + power, truncated N=10); `integration.py` parts primitives — extend existing parts-identity invariant to non-tautological recomposition; u-sub primitive — add Riemann-sum independent computation; `diophantine.py` solve_binary_quadratic — verify by re-enumerating with permuted (x, y) walk order (catches enumeration-loop ordering bugs); `number_theory.py` primitives are already independent-path by construction (iteration / sieve vs nothing else to compare against) — document this in cycle 10 reflection rather than retrofit. Expected: +25-40 tests across substrate files. Atomic commits per primitive file. |
| **#00P13c10-02-diophantine-pell-extension** | MED | `src/project_x/reasoning/diophantine.py` — add `solve_pell_equation(n, max_solutions)` for x² - n·y² = 1 + dispatcher + 1-2 ladder entries (maths-026 + maths-027) | Extends cycle 9 #03 to indefinite forms (Δ > 0) via fundamental-solution-from-continued-fraction-of-√n + recurrence (x_{k+1}, y_{k+1}) = (x₁·x_k + n·y₁·y_k, x₁·y_k + y₁·x_k). Honest framing per M-PROJECTX-013: PASS = "enumerated first K solutions via recurrence", NOT general Hilbert-10. Canonical examples: x² - 2y² = 1 fundamental (3, 2) yields (3, 2), (17, 12), (99, 70), ...; x² - 3y² = 1 fundamental (2, 1). Requires continued-fraction-of-√n primitive (hand-rolled, no math library; pattern from Hardy + Wright *Theory of Numbers*). advisor() pre-Write. |
| **#00P13c10-03-higher-order-integration-techniques** | MED | `src/project_x/reasoning/integration.py` extension OR new submodule | Iterated parts (`∫ x²·e^x dx` — apply parts twice; closed form `e^x·(x² - 2x + 2) + C`); trigonometric substitution (`∫ dx/√(a² - x²) → arcsin(x/a)`; reverse-substitute back); partial fractions (`∫ dx/((x-a)(x-b)) → (1/(a-b))·ln((x-a)/(x-b))`). Each new primitive with 4-5 step Lemma chain + algebraic-identity invariant. +3-5 ladder entries (maths-028..032). |
| **#00P13c10-04-council-audit-tag** | LOW (lain-greenlight-pending) | TBD per lain direction | Lain proposed 2026-05-10 21:05; mechanism scope still unresolved. Surface on Discord at cycle 10 mid-flight if no direction lands; do NOT touch unprompted. |
| **#00P13c10-05-CLAUDE.md-trim-continuation** | LOW (lain-direction-pending) | `~/.claude/CLAUDE.md` | 57k current after cycle-9 partial-trim; 46k hard ceiling. ~11k more to cut. Older sections likely targets (PHASE 0 DD-1/2 verbose, FOUR-GATE FLOW, BACK-DOOR GATE, NAMED CURSES expansion) — needs lain direction on what's load-bearing. Do NOT trim unprompted; surface if continued direction lands. |
| **#00P13c10-06-cycle-10-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-10.md` + DO_THIS_NEXT cycle-11 handoff + A_TO_Z PHASE CHANGELOG cycle-10-close + IQ_PROGRESSION cycle-10 entry | Hassabis-bar honest decomposition per universal lain 2026-05-11 binding. Decompose substrate vs capability vs cosmetic; would Hassabis be impressed? (Honest answer if cycle 10 ships predicate-strength uniformity + Pell + higher-integration: still no — the substrate is being rigorized + extended, not fundamentally elevated to research-grade. That's still cycle 11+). |

## Recommended cycle 10 order

1. **#01 predicate-strength uniformity** — start here. Atomic per-primitive-file commits (7 files); each commit verifies pytest + bench-replay parity. Frontload because (a) cycle 9 deferred this, accumulating debt; (b) the pattern is established + mechanical; (c) it strengthens the foundation before more substrate lands on top.
2. **#02 Pell extension** — once uniformity passes are in. advisor() pre-Write per novel substrate (continued-fraction primitive is new infrastructure). +1-2 ladder entries. Atomic commit.
3. **#03 higher-order integration** — third because it stacks on the existing integration.py pattern. 3-5 new primitives; +3-5 ladder entries; atomic per-technique commits (iterated parts / trig sub / partial fractions as separate commits if scope allows).
4. **#04/#05** only if lain direction surfaces during cycle.
5. **#06 cycle reflect** — close-out.

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
