# Do This Next — Project X — Phase 13 cycle 9 IN FLIGHT (lain mid-cycle pivot 2026-05-11 — HARDER PROBLEMS + BETTER BENCHMARKS + VISIBLE IQ PROGRESSION; predicate-strength uniformity DEFERRED to cycle 10+)

**Updated:** 2026-05-11 (mid-cycle, post-`/godify-app` mode switch + docs-sync handoff for lain's `/forge-prompt -ni` context-clean invocation)
**Mode:** NORMAL (was APOTHEOSIS during this run; flipping back to NORMAL pre-handoff so fresh instance starts on standard cadence)
**Status:** Cycle 9 IN FLIGHT. 3 of ~6 cycle-9 deliverables shipped this run; 3 remaining + 2 lain-pending carry-forwards.

## Mid-cycle context (read before starting work)

Lain pivoted cycle 9's scope mid-flight 2026-05-11 (Discord msg 1503173784457187378 + 1503176253757194281 + 1503176662316220416):

1. **"Make it so smart Hassabis would actually be impressed; tests as important as the model; visible IQ progression."** Stop shipping rigor on freshman primitives; start shipping CAPABILITY on harder shapes.
2. **"Long paper.md in /docs explaining how everything works"** — teacher-tone curriculum for NotebookLM podcast listening; lain wants to chip in on architectural decisions.
3. **Style fix:** stop using cycle-number jargon on Discord; speak plain English assuming only-Discord readers.

Original cycle 9 plan (predicate-strength uniformity pass per advisor 2026-05-11) is DEFERRED to cycle 10+. Capability-debt > grading-debt > rigor-debt per lain.

## Cycle 9 shipped (this run, 5 commits)

| Commit | Deliverable | Result |
|---|---|---|
| `5fe45e9` | #01 symbolic integration substrate | `definite_integral_x_times_exp` + `_times_sin` + `_times_cos` + `_xtrig_via_usub` (4 primitives covering parts + u-sub). +3 ladder entries maths-021..023 (∫₀¹ x·e^x dx → 1; ∫₀^π x·sin(x) dx → π; ∫₀¹ x·sin(x²) dx → (1-cos(1))/2). Closes maths-021..023 agent-runtime gap. Bench-replay --agent-runtime: 41/0 → 44/0. +29 tests. |
| `18e385e` | #05 paper.md curriculum (lain directive 2026-05-11) | `docs/paper.md` teacher-tone NotebookLM-friendly explainer. 11 chapters: why-not-just-use-ChatGPT, two-Raphaels, memory layer (HDC + fact-graph), reasoning substrate (Lemma + invariant), AGENT runtime dispatcher, benchmark architecture + split-grading firewall, current capability with concrete examples, what-can't-do honest accounting, the-road-to-Terminus. ~4500 words. |
| THIS commit | #02 (partial) — IQ_PROGRESSION.md tracker (lain-anticipated artifact; lain mentioned wanting to see "the IQ progression over time in your new .md file") | `docs/artifacts/IQ_PROGRESSION.md` — per-phase + per-cycle hardest-problem-solved-at-runtime snapshot from Phase 9 close through Phase 13 cycle 9 in flight. Concrete examples, pytest baselines, bench-replay PASS counts, capability shape notes. Plus "Today's Frontier" section (what the agent CAN vs CANNOT do at the current frontier) + Hassabis-bar retrospective. Live document — per-cycle entries prepended at cycle close. Pairs with `docs/paper.md`. |
| THIS commit | DO_THIS_NEXT rewrite (this file) + A_TO_Z PHASE CHANGELOG cycle-9-in-flight entry | Docs synced for lain's `/forge-prompt -ni` context-clean invocation. |

## Cycle 9 remaining (for fresh instance via `/forge-prompt -ni` paste)

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c9-02 (remaining)** | MED | `gpt-codex/benchmark/*/ladder.jsonl` schema audit + `difficulty_tier` field retrofit | The IQ_PROGRESSION.md sub-deliverable shipped this run. Remaining: (a) add `difficulty_tier` field to ladder schema (`trivial-baseline` / `intro` / `intermediate` / `hard` / `research-grade`); audit existing 23+ entries and relabel. Cycle 9 #01 entries (maths-021..023) already have the field set to "intermediate". (b) Add `would_surprise_hassabis: y/n` builder-grade dimension on rubric-graded entries (subjective signal for ladder-quality auditing). |
| **#00P13c9-03-diophantine-binary-quadratic-substrate** | MED | `src/project_x/reasoning/diophantine.py` (NEW) OR `number_theory.py` extension + dispatcher + tests + 1-2 ladder entries (maths-024..025) | Substrate: `solve_binary_quadratic(a, b, c, N, bound)` enumerates integer solutions (x, y) to `a·x² + b·xy + c·y² = N` via bounded brute-force search with theoretical pruning (e.g., |x|, |y| ≤ √(N/min(|a|,|c|)) for positive-definite forms). Examples: Pythagorean triples x²+y²=z² ≤ 100; sums-of-two-squares for prime p (Fermat's two-squares theorem witness when p ≡ 1 mod 4); Pell equation x² - n·y² = 1 small-n solutions. HONEST FRAMING per M-PROJECTX-013: bounded-search, NOT Hilbert-10 decidability; PASS = "enumerated all solutions in [search bound]". |
| **#00P13c9-04-cycle-9-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-9.md` + DO_THIS_NEXT cycle-10 handoff + A_TO_Z PHASE CHANGELOG cycle-9-close entry | Hassabis-bar retrospective per lain directive — honest decomposition of what's substrate vs what's capability vs what's-cosmetic; concrete examples of "the agent now does X (cycle 8: 'verify Collatz at N=1000'; cycle 9: '∫₀¹ x·e^x dx via parts')"; identify next harder shape for cycle 10. advisor() pre-commit. Discord cycle-9 close in 4-metric rubric (plain-English style — NO cycle-number jargon on Discord per lain 2026-05-11 directive). |

**Carry-forwards (still lain-pending; surface on Discord if cycle close approaches without lain input):**
- **#00P13c8-07 CLAUDE.md trim resolution:** 62k current vs lain's 41-47k hard range. Needs lain direction on what's load-bearing in older sections (RAPHAEL OPERATING MODES / SIX VOWS / UNIVERSAL vs PROJECT-SPECIFIC / PHASE 0). DO NOT trim unprompted (cycle 6 ask-first policy binding).
- **#00P13c7-04 council audit tag:** lain proposed 2026-05-10 21:05. Mechanism scope still pending lain direction.

## Recommended cycle 9 order (remaining)

1. **#02 remaining** — `difficulty_tier` field schema + retrofit existing entries; `would_surprise_hassabis` dimension. ~15-20 min focused work; mechanical but touches every ladder.jsonl file across maths/physics/memory/persona/philosophy/poetry. Use `python3 -c "import json..."` to load/transform/dump rather than hand-editing each entry.
2. **#03 Diophantine substrate** — substantial; 1-2 hours. Design first (binary-quadratic-form theory + pruning bound derivation + canonical examples); advisor consult before Write per M-PROJECTX-013 for novel substrate; substrate + tests + dispatcher + 1-2 ladder entries + atomic commit.
3. **#04 cycle reflect** — `dev-cycle-9.md` + DO_THIS_NEXT cycle-10 handoff. Decompose Hassabis-bar honestly (cycle 9 was paper.md + IQ tracker + integration-by-parts + Diophantine; the math is intermediate calc + integer search — would a frontier researcher be impressed by the substrate primitives? Probably not. Would they be impressed by the discipline + honest framing? Maybe. Honest answer in the reflection).

## Cycle 9 in-flight metrics (snapshot)

```
pytest -q:                  458 / 458 passing
bench-replay --agent-runtime: 44 / 0 (was 41/0 at cycle 8 close; +3 from #01 integration)
bench-replay frozen:        44 / 0 (parity)
Substrate-solved at agent-runtime: 28 of 29 objective auto-graded entries ≈ 97%
  - 12 cycle-7-baseline carry-forward
  - 10 cycle-8 substrate-extensions (residue / integral / ODE / 3x3 det / projectile / Doppler + Collatz / Goldbach / twin primes / Mertens)
  - 3 cycle-9 substrate-extensions (integration by parts × 2 + u-substitution × 1)
  - 4 of 26 + 3 new of 29: the remaining auto-graded entry is rubric-pending (need rubric-grade not substrate-solve)

Cycle 9 commits: 5 (5fe45e9 + 18e385e + e1e309c-ish + cycle-9-pivot directives + this commit)
Files added: docs/paper.md, docs/artifacts/IQ_PROGRESSION.md, src/project_x/reasoning/integration.py, tests/test_reasoning_integration.py
Files modified: docs/REPO_CONTROL.md (integration.py + test rows), src/project_x/reasoning/__init__.py (re-exports), src/project_x/reasoning_agent.py (4 dispatchers), tests/test_reasoning_agent.py (5 dispatcher tests), gpt-codex/benchmark/maths/ladder.jsonl (3 entries)
```

## Standing rules — RELEVANT FOR FRESH INSTANCE

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal).

**Codified universal during cycle 9 (lain mid-cycle absorbed; binding cycle 10+):**
- **Discord style discipline (lain 2026-05-11 binding):** NO cycle-number jargon on Discord — speak plain English assuming only-Discord readers. Internal docs (dev-cycle-N.md, A_TO_Z, DO_THIS_NEXT) can still use cycle numbers since those are internal organization. But Discord = teacher-tone for someone tracking only via Discord. Refer to commits by SHA only if directly relevant; otherwise describe achievements in plain language.
- **Hassabis-bar discipline (lain 2026-05-11):** every cycle close retrospective explicitly answers "would Hassabis be impressed?" with honest decomposition of substrate vs capability vs cosmetic.
- **Listener accumulation pattern (M-NAVI-021):** two-call pkill+launch pattern; use `exec bash discord-wait-for-lain.sh general 5` for the launch to replace wrapper shell directly (NOT bundled `pkill ; bash ...` because pkill self-matches the wrapper shell's argv).

**Persistent (unchanged):**
- NO pretrained transformer derivatives at any layer
- Comment-ratio rule (WHY-comments + pure-signal + complex code justified)
- Atomic per-deliverable commits; never `git add -A`
- REPO_CONTROL row co-landing in SAME commit as new NON-docs files (docs/ exempt)
- M-PROJECTX-013 measure-don't-claim; M-PROJECTX-014 split-grading firewall

## What this cycle is NOT (post-pivot)

- NOT predicate-strength uniformity pass (deferred cycle 10+ per lain pivot)
- NOT a comprehensive parser-robustness audit (cycle 8 #06 fortified 3 dispatchers; cycle 10+ extends as failure prompts surface)
- NOT touching lain-pending items (#07 CLAUDE.md trim, #11 council audit tag) without lain direction

## Done condition (cycle 9, mechanical) — when fresh instance picks up

- 3 remaining #00P13c9-XX TaskList rows + ladder schema audit shipped (or explicitly deferred with rationale)
- pytest -q ≥ 480 (current 458; expect +20-30 tests across Diophantine + benchmark-schema validation)
- bench-replay --agent-runtime: ≥45/0 maintained (current 44/0; +1-2 from new Diophantine ladder entries if shipped)
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-9.md`
- THIS file rewritten as cycle 10 handoff with predicate-strength uniformity FINALLY in scope (the lain-pivot-deferred work)
- `git status -s` empty
- Discord cycle-9 close in plain-English 4-metric rubric

## Files the fresh instance should read first (in order)

1. `~/.claude/CLAUDE.md` — universal Raphael protocol (auto-loaded by harness)
2. `docs/MANIFESTO.md` — project intent + standing orders
3. `docs/REPO_CONTROL.md` — pristine-gate file inventory
4. `docs/A_TO_Z_PLAN.md` — Phase 13 plan + PHASE CHANGELOG (latest entry = cycle 9 in flight + lain pivot)
5. **THIS file** — cycle 9 in-flight scope + remaining deliverables
6. `docs/paper.md` — teacher-tone curriculum explaining how Project X Raphael works (~30-min listen)
7. `docs/artifacts/IQ_PROGRESSION.md` — per-cycle hardest-problem-solved ladder (concrete examples)
8. `docs/past_work/cycles/phase_13/dev-cycle-8.md` — last closed cycle reflection
9. Recent git log: `git log --oneline -15` to see commit progression
10. Latest pytest + bench-replay verification: `python3 -m pytest -q | tail -3` + `python3 gpt-codex/benchmark/run_audit.py --agent-runtime | tail -10`

The fresh instance is Execute-Raphael (post-`-ni`-handoff per Plan-Raphael → Execute-Raphael split). NO re-planning. The plan IS this file + A_TO_Z + paper.md + IQ_PROGRESSION.md. Recon (Phase 0 DD) + read those + pillars (pick-skill + sharpen-todos) + execute the remaining cycle 9 deliverables.

— Update this file at cycle 9 close: replace cycle 9 deliverables table with cycle 10 deliverables table; refine cycle 10 scope based on cycle 9 lessons (and reinstate predicate-strength uniformity as cycle 10 #1 priority).
