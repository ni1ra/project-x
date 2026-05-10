# Do This Next — Project X — Phase 13 cycle 8 (SUBSTRATE EXTENSIONS to close 6 agent-runtime FAIL gaps + CLAUDE.md structural trim per lain direction + then thin-domain expansion)

**Updated:** 2026-05-10 (cycle 8 handoff; cycle 7 closed PARTIAL at THIS commit)
**Mode:** NORMAL (not godify-app)
**Status:** Cycle 7 CLOSED PARTIAL. AGENT runtime dispatcher shipped end-to-end (lain "make agent actually solve" directive operationalized). pytest 310 passing. D3 harness frozen-mode: 37 PASS / 0 FAIL; **agent-runtime mode: 31 PASS / 6 FAIL** (real-results milestone — 14 of 22 objective auto-graded entries now solved by AGENT at runtime).

## Cycle 7 shipped (full ledger)

| Commit | Deliverable | Result |
|---|---|---|
| `841dd7a` | docs(P13c7) cycle 7 redirect per lain mid-directive | DO_THIS_NEXT prioritized AGENT-runtime over thin-domain |
| `26193ce` | **#39a** ReasoningAgent quadratic dispatch | maths-001/007/008 runtime-solved |
| `4a9566a` | **#39b** 2x2 eigenvalue dispatch | maths-002/009 runtime-solved |
| `4e53b1c` | **#39c** Physics free-fall dispatch | physics-001/008 runtime-solved |
| `25f87b6` | **#39d** Pendulum dispatch (small + large angle) | physics-002/009/010 runtime-solved |
| `9171dd1` | **#39e** Relativistic momentum dispatch | physics-003/011 runtime-solved |
| `6363b92` | **#39f** Bench-replay `--agent-runtime` flag wire-up | 31 PASS / 6 FAIL agent-runtime; honest gap-signal |
| `5961646` | **#01a** poetry-007 (trochaic scansion intro) | Methodical thin-domain kickoff before cycle 7 redirect |
| THIS commit | **#38** cycle reflect | dev-cycle-7.md + this rewrite + A_TO_Z changelog |

Cycle 7 #35 CLAUDE.md trim partial: 70687 → 62393 chars (cut 8.3k); lain's 41-47k hard range needs 15k+ more from older sections; awaits lain direction.

## Phase 13 cycle 8 deliverables

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c8-01-residue-theorem-substrate** | HIGH | `src/project_x/reasoning/symbolic.py` extension OR new `complex_analysis.py` + tests + reasoning_agent dispatcher | Hand-rolled contour-integration / residue-theorem substrate (closes maths-003 agent-runtime gap). |
| **#00P13c8-02-integral-substrate** | HIGH | `src/project_x/reasoning/calculus.py` (NEW) + tests + dispatcher | Definite-integral evaluator (polynomial via FTC; standard trig). Closes maths-010 gap. |
| **#00P13c8-03-ode-substrate** | HIGH | `src/project_x/reasoning/ode.py` (NEW) + tests + dispatcher | First-order linear ODE solver (separable + exponential growth/decay). Closes maths-011 gap. |
| **#00P13c8-04-nxn-determinant** | MED | symbolic.py extension + dispatcher | 3x3 cofactor-expansion determinant. Closes maths-012 gap. |
| **#00P13c8-05-physics-extensions** | MED | physics.py extension: projectile-range + Doppler shift | Closes physics-007/012 gaps. |
| **#00P13c8-06-parser-robustness** | MED | reasoning_agent.py multi-pattern fallback per shape | Brittle-phrasing-variation mitigation. Stress-test against rephrased prompts. |
| **#00P13c8-07-CLAUDE.md-structural-trim** | MED | `~/.claude/CLAUDE.md` per lain direction | Reach 41-47k hard range by structural rewrites of older sections. Lain decides what's load-bearing in RAPHAEL OPERATING MODES / SIX VOWS / UNIVERSAL vs PROJECT-SPECIFIC / PHASE 0. |
| **#00P13c8-08-bench-replay** | MED | `python3 gpt-codex/benchmark/run_audit.py --agent-runtime` | Target: agent-runtime PASS count 31 → ≥35 if extensions close 4+ gaps. |
| **#00P13c8-09-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-8.md` + DO_THIS_NEXT cycle 9 handoff + A_TO_Z changelog | advisor() pre-commit. |

## Recommended cycle 8 order

1. **#01 residue-theorem substrate** — hardest math; longest tail. Get this out of the way first.
2. **#02 integral substrate** — moderate; closed-form polynomial integration is straightforward.
3. **#03 ODE substrate** — moderate; first-order linear is closed-form too.
4. **#04 3x3 determinant** — small extension; cofactor expansion. Quick.
5. **#05 physics extensions** — projectile-range is straightforward kinematics; Doppler shift is a closed-form relativistic formula.
6. **#06 parser robustness** — once new substrate exists, stress-test parsers against rephrased prompts.
7. **#07 CLAUDE.md structural trim** — lain-direction-dependent.
8. **#08 bench-replay** + **#09 cycle reflect** at cycle close.

## #1 residue-theorem substrate — exact next-action

1. Inspect maths-003 prompt: `gpt-codex/benchmark/maths/ladder.jsonl` → maths-003 entry; understand expected answer shape.
2. Design from-scratch residue-calculation primitive — for the canonical integral ∫_{-∞}^{+∞} dx/(x²+1) the answer is π. Substrate computes residue at poles + applies residue theorem. Stdlib `math` only (organic-thesis binding).
3. Build `Lemma`-returning function mirroring cycle-2 symbolic.py pattern.
4. Wire into ReasoningAgent as `_try_residue_theorem` with detection via "residue theorem" / "contour integral" keywords + integrand-extraction regex.
5. Tests verifying maths-003 substrate match + agent-runtime PASS.
6. Atomic commit + REPO_CONTROL row + push.

## Identity disambiguation (CRITICAL — lain 2026-05-10 binding)

Claude Code Raphael (BUILDER) ≠ Project X Raphael (AGENT, in `src/project_x/`). Cycle 8 BUILDER work: extend substrate (closed-form math). AGENT consumes the new substrate at runtime via reasoning_agent dispatcher.

## Standing rules — RELEVANT THIS RUN

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal).

**Codified universal during cycle 7 (lain-authorized; binding cycle 8+):**
- Listener bg-task completion IS A TRIGGER, not a hint (DD-1/DD-2 rewrite + foolproof "🔔 LISTENER ARM" labeling)
- Named Curse #15 fake-stop drift compressed to principle
- CLAUDE.md 41-47k hard range; `wc -c` mandatory after every edit pass; edits REWRITE-to-incorporate not append-to-lists

**Persistent (unchanged):**
- NO pretrained transformer derivatives at any layer (binding to AGENT inference too — regex parsers only)
- Comment-ratio rule (WHY-comments + pure-signal explanations + complex code justified)
- Atomic per-deliverable commits; never `git add -A`
- M-PROJECTX-013 measure-don't-claim; M-PROJECTX-014 split-grading firewall

## What this cycle is NOT

- NOT shipping the Terminus (multi-cycle).
- NOT thin-domain expansion (poetry/philosophy/persona — defers until objective gaps closed per lain).
- NOT touching cycle-7 CLAUDE.md trim without lain direction.
- NOT closing without measurable agent-runtime PASS-count lift (target 31 → ≥35).

## Anti-laziness gates

- *"all you have done so far is just minor work"* — cycle 7 lifted AGENT-actually-solves from 0 → 14 entries at runtime. Cycle 8 closes 6 more gaps via substrate extensions.
- *"make the agent actually solve the problems"* — directly served by every cycle 8 deliverable. Each new substrate adds runtime-PASS entries.
- *"unless its super-human in every domain ... YOU ARE NOT DONE"* — Terminus is FAR.
- *"honest and honorable work ethics"* — agent-runtime mode IS the honest measurement: real capability, real gap-signal.

## Done condition (cycle 8, mechanical)

- All 9 #00P13c8-XX TaskList rows = `completed` (or explicitly deferred with rationale).
- pytest -q ≥ 310 (no regression; new substrate adds tests).
- D3 harness `--agent-runtime`: ≥35 PASS / ≤2 FAIL (4 of 6 cycle-7 FAIL gaps closed minimum).
- Frozen mode: 37 PASS / 0 FAIL maintained.
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-8.md`.
- THIS file rewritten as cycle 9 handoff.
- `git status -s` empty.
- Discord cycle 8 close in 4-metric rubric.
- Cycle 9 picked up immediately OR `-ni` proposal at cycle 8 close.

— Update this file at cycle 8 close: replace cycle 8 deliverables table with cycle 9 deliverables table; refine cycle 9 scope based on cycle 8 lessons.
