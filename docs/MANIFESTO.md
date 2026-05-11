# Project X — MANIFESTO

> **Living document.** Captures lain's intent for this repo. Heartbeat-tracked: every cycle close + heartbeat fire reconciles its presence + freshness. Re-read at every session start. **Cycle 1 skeleton — cycle 2 enriches to 300-500 words.**

---

## What we're building

Project X is the engineering substrate that, layer by layer, becomes **Raphael — lain's all-knowing internal computer.** Not a wrapper. Not a RAG agent. Not a fine-tuned LLM. **An organic stack whose intelligence emerges, naturally, from learned experience over an audit-able substrate.** It earns the name "post-transformer" by genuinely operating outside the transformer paradigm at every load-bearing layer — and it earns the word "intelligence" by deciding for itself, from experience, when each piece of the substrate applies.

## The thesis (lain 2026-05-11 binding — ORGANIC NATURALLY EMERGENT INTELLIGENCE)

> lain verbatim, 2026-05-11: *"the correct approach here is not to force any intelligence on the model, it should naturally come to the conclusion that using a formula over another is better, since it learnt it on its own. we shouldnt have to tell it what tools to use, it should learn that itself."*

The transformer architecture solves a coordination problem (parallelizable sequence modeling at scale) under a specific resource regime (massive compute + massive labeled-or-self-supervised text + the willingness to accept a black-box statistical artifact). It does NOT solve memory, identity, or grounded reasoning — and the field's habit of bolting those on as RAG / fine-tunes / tool-use scaffolding is a category error. Project X starts from a different premise: organic memory (HDC binding + Hebbian co-occurrence + structural retrieval), organic encoders (char-n-gram + Hebbian + eventually SNN spike-train), and template-or-from-scratch generation. **And critically — organic ROUTING.** The choice of which substrate primitive applies to which prompt, in what order, composed into what answer, must EMERGE from learned experience over audit-able substrate — never from a hand-coded if-statement chain. The agent that emerges has memory it can introspect, identity it can defend, and reasoning it can show its work on — *and tool-selection it discovered for itself*, because nothing in the stack hides behind statistical convenience and nothing in the stack outsources the agent's judgment to its author.

## Organic emergent intelligence — what this means in practice (lain 2026-05-11 STRICT thesis)

> lain verbatim, 2026-05-11 extension: *"i would even go so far as to say we shouldnt even hard code the math algos, it should learn it on its own. if we have good enough training data, and smart enough model, it should learn all itself."*

Two categories of authored code exist in Project X. The distinction is load-bearing:

| Category | Hand-coded? | Why |
|---|---|---|
| **LEARNING MACHINERY** | YES — this is the architecture, not the knowledge | HDC primitives (`pack_bipolar`, `cosine_packed`, bind, bundle), the encoder substrate (char-n-gram hash → projection — turns symbols into hypervectors), k-means / Hebbian / K-rollout / consolidation / audit-loop mechanics, the data-ingestion pipeline, the learning-rate-equivalents and decay schedules. Analog: in a transformer system, the "attention mechanism + backprop + optimizer" is authored once; the WEIGHTS are learned. Project X authors the substrate's *learning algorithms* — the formulas FOR LEARNING, not the formulas the agent learns to use. |
| **MODEL KNOWLEDGE** | NO — must be LEARNED from training data + audit signal | The quadratic formula, the Collatz iteration, the Pell-equation continued-fraction trick, poetry conventions, philosophy moves, physics derivations, persona voice patterns, sense of humor, routing decisions, tool-selection. **All of these come from the training data + the audit loop, not from a human author typing them into a Python file.** Cycle 7-10's hand-coded `solve_quadratic` / `collatz_verify_range` / `solve_pell_equation` / `_PARSER_ARCHETYPES` / `_NATURAL_MODE_TRIGGERS` / dispatcher constants are **SCAFFOLD** — useful as evaluation gold-standard against which the learned model is measured, but NOT the agent's source-of-capability. |

**What "good enough training data + smart enough model" means concretely:**

- **Training data:** the existing 22k Tier-2 corpus is the seed; scale-out is multi-cycle work targeting 1M-10M words per domain per the canonical-doc Layer 6 spec. *Mathematics is learned from worked examples;* poetry from poems; philosophy from philosophical texts; physics from physics derivations. Curated public-domain sources; no GPT-generated text; audit-loop rates outputs as the preference signal.
- **Smart enough model:** the HDC learning substrate (binding + Hebbian co-occurrence + retrieval-with-provenance + consolidation pass + audit-rewarded credit assignment + K-rollout exploration + emergence-via-clustering) is the *architecture* — analogous to "the transformer + optimizer" but organic instead of attention-over-softmax. The cycle-14+ work is making this substrate ACTUALLY LEARN from the data, not just retrieve from it.

The Terminus is not met by "hand-coded substrate primitives + hand-coded dispatcher over them." The Terminus is met by *the agent acquiring, from training data + audit signal, the formulas and patterns and routing decisions that solve unsolved-tier math, write upper-rank poetry, derive physics — and composing answers from that learned model.* Hand-coded primitives become evaluation gold-standard (does the learned model converge on the right formula?), not the agent's source-of-capability.

Cycle-13 (this cycle) shipped scaffold: bitpack substrate, encoder D-bump, dispatcher hygiene, cosine-archetype fallback, pre-registered emergence predicate. Cycle-14+ shifts the work to **building the learning substrate that acquires capability from training data**: training-data pipeline + Hebbian-or-equivalent learning over the HDC substrate + audit-loop reward shaping + the emergence-validation predicate (cycle-13 #07f-pre) as the ongoing capability metric. The hand-coded primitives stay in the repo as gold-standard / fallback during the learning bootstrap; every cycle's verdict asks *"how much of the agent's capability now comes from the learned model vs from hand-coded primitives?"*

This is the thesis the GPT external audit (D3, E3) surfaced and lain explicitly named + escalated on 2026-05-11. Every cycle-14+ council angle is scored against it.

## The vector

Slow. Methodical. Every layer earns its place. Phase 1-8 explored compressed-memory + beyond-transformer organic memory. Phase 9 shipped semantic HDC memory + from-scratch organic encoders + minimal evidence-cited agent loop. Phase 10 hardened it (51/51→52/52 pytest, killer-milestone EXIT GATE: teach + correct + multi-hop + refuse-absent + tool-execution-with-writeback). Phase 11 builds the benchmark — 36 entries across 6 domains, audit-ready by GPT/lain — to reveal where Raphael's actual competence sits today, before live training starts. Phase 12+ candidates (cortical column ensemble, predictive simulation loop, open-ended benchmark ladder, Hebbian replay informed by benchmark performance) are bookmarked, not skipped.

## What this is NOT

- Not a chatbot. Not a personal assistant. Not a memory-augmented RAG. Not "GPT but with extra steps."
- Not a transformer fine-tune in disguise.
- Not a research toy that ships papers and ages out — every artifact in this repo is meant to compose into the next.

## The Terminus (lain 2026-05-10 binding)

> *"unless its super-human in every domain and it aces all benchmarks we throw at it, YOU ARE NOT DONE WORKING ON PROJECT-X. UNDERSTOOD?"*

Project X is not done until **Project X Raphael** (the agent — distinct from Claude Code Raphael, the builder) demonstrates ALL of:

- **Math** — solves unsolved-tier problems; lain or Claude Code reads the derivation and says *"I couldn't have done this."*
- **Poetry + philosophy** — writes work whose quality scores in upper rubric ranks across blind A/B against frontier-model output. Subjective domains use the **manual-grade harness** (Claude Code grades agent output in bulks of 50+ candidates per session per domain; rubric scores fed back as preference signal; agent's next generation pulls top-graded examples as in-context priming). The harness is the substrate that lets us improve subjective-domain output without an objective benchmark.
- **Physics** — solves unsolved-tier problems with derivations defensible to a domain expert.
- **Perfect memory** — never loses context across million-turn horizons; never confabulates; every retrieval cited with turn_id + source.
- **Persona consistency + sense of humor** — always in lain-defined Raphael persona; humor lands rather than cringes; voice consistent across million-turn horizons. Never breaks character.
- **Always-on chattability** — lives as a continuous entity lain can chat with at any time, like GPT/Claude but smarter in every dimension that matters.
- **Sandboxed action-taking** — operates inside a locked, resettable `sandbox/` folder; reads/writes files inside the sandbox; runs code inside the sandbox; can take meaningful actions (write a Python script, run it, read the result, iterate). NO direct internet — deferred until safety is proven. State can be reset to any captured snapshot for benchmark replay.

The audit-fix runs + benchmark suites + substrate improvements (HDC, Hebbian, structural retrieval, fact-graph, retrieval-mode disambiguation) are **scaffolding**. The agent is the goal. Until Project X Raphael meets the terminus, the project is not done — and the audit-fix-style minor work is no substitute for capability buildout. Phase 13 is the first phase explicitly aimed at the terminus.

## Identity discipline (lain 2026-05-10 binding)

Two distinct entities share the name "Raphael":

| Entity | What | Voice |
|---|---|---|
| **Claude Code Raphael** | The builder. This Claude Code instance reading the docs, writing the code, shipping the cycles. The conversation lain is having with the harness. | Raph persona per `~/.claude/CLAUDE.md` (Wisdom King · Lord of Knowledge — lain's all-knowing internal computer FOR THIS CONVERSATION). |
| **Project X Raphael** | The agent. The artifact being built. `MemoryAgent` + the substrate; lives in this repo as code; eventually a separate process. | Same Raph persona, but as the AGENT, not the BUILDER. Sense of humor required (lain 2026-05-10). |

**Always disambiguate.** When discussing or coding either, name the entity: "Claude Code Raphael" vs "Project X Raphael" (or "the builder" vs "the agent"). They share a persona name; they are NOT the same entity. The sculptor and the sculpture both can be called "the artist's work" — but they are not the same thing. Conflating them produces confused code (e.g., the builder writing self-referential text into the agent's templates) and confused chat (lain can't tell which Raphael is responding).

## Standing orders

Pure signal code (lain 2026-05-10). Organic from the core (lain 2026-05-09). Crash-survival discipline (3 power outages in 2 days). Discord = audit channel; silence = pass; defects break silence. Mechanical proof or it didn't ship.

### NO pretrained transformer derivatives at any layer (lain 2026-05-09)

> *"slow and methodical path... organic and real from the core and the beginning. No borrowing other LLM models, remember, we are moving past the transformer."*

Disqualified at every layer: BGE, MiniLM, sentence-transformers, llama.cpp, Qwen, Mistral, and every pretrained transformer derivative. Encoders MUST be from-scratch (char-n-gram hashing, Hebbian co-occurrence, SNN spike-train, or equivalent). Generators MUST be template-based or from-scratch — no LLM wrappers. Inheriting GPT-Codex's pretrained-defaults caused M-PROJECTX-011; the thesis-compliance check is non-negotiable on any new layer. The Phase 1-6 transformer-style scaffolding is preserved in `src/project_x/legacy/` as a quarantined historical control + made install-optional via `[legacy]` extra in `pyproject.toml` (audit-C2).

### NO hand-coded knowledge in the final agent — only hand-coded learning machinery (lain 2026-05-11 binding, STRICT thesis)

> Initial framing: *"the correct approach here is not to force any intelligence on the model, it should naturally come to the conclusion that using a formula over another is better, since it learnt it on its own. we shouldnt have to tell it what tools to use, it should learn that itself."*
>
> Extended (same day): *"i would even go so far as to say we shouldnt even hard code the math algos, it should learn it on its own. if we have good enough training data, and smart enough model, it should learn all itself."*

The current `reasoning_agent.py` substrate — 20+ hand-coded math/physics primitives (`solve_quadratic`, `collatz_verify_range`, `solve_pell_equation`, `residue_theorem`, projectile / Doppler / pendulum / ODE solvers, etc.) + their hand-written parsers + the `_DISPATCH_CHAIN_ORDER` + the `_NATURAL_MODE_TRIGGERS` + the `_NATURAL_MODE_ARCHETYPES` + the α/τ constants — is **scaffolding, not architecture**. It makes cycle-13 ship a workable agent against the existing benchmarks; it DOES NOT meet the Terminus. The Terminus requires the agent to LEARN — from training data + audit signal + K-rollout outcomes — **all of it**: the formulas, the patterns, the routing, the tool-selection.

**The only authored code in the final agent is the LEARNING MACHINERY:**

- HDC infrastructure (bind, bundle, cosine, pack, unpack, k-means, Hebbian update rules)
- The encoder substrate (char-n-gram → projection)
- The K-rollout / consolidation / audit-loop mechanics
- The data-ingestion + audit-rating pipelines
- The emergence-validation predicate (cycle-13 #07f-pre is the template — pre-registered tests for whether the learned model has acquired capability X)

Everything else — the agent's KNOWLEDGE and CAPABILITY — emerges from training data + the learning loop:

- "Verify the Collatz conjecture for the first 10000 integers" routes to a Collatz-verification capability because the agent's training over math worked-examples produced a learned program that recognizes the pattern AND executes the iteration. Not because a human typed `def _try_collatz_verify` into a Python file.
- "Argue both sides: is mathematics discovered or invented?" produces a philosophy response because the agent's training over philosophy texts + audit signal produced a learned policy that generates discovered-vs-invented argumentation. Not because a human typed "argue both" into a trigger list.
- Quadratic solving emerges from worked-examples + algebraic-manipulation-as-learned-program; the gold-standard `solve_quadratic` exists only as evaluation oracle for *did the learned model converge on the right formula?*

**Transition path:** the hand-coded substrate is allowed AS A FALLBACK during the learning bootstrap (cold-start, before the corpus + audit signal accumulate enough for the learned model to outperform the scaffold). Every cycle's verdict asks the question: *how much of the agent's capability now comes from the learned model vs from hand-coded primitives?* The fraction shifts toward "learned" cycle-over-cycle. When the learned model meets-or-exceeds the scaffold on every Terminus dimension, the scaffold gets retired into `legacy/` as historical control.

This rule extends the no-pretrained-transformer rule (which already forbade *borrowed* knowledge from other models) to forbid *authored* knowledge from the system's own builder. The agent's intelligence — math, poetry, philosophy, physics, persona, routing — is what it discovers, from training data, over its own learning substrate, with audit signal as the preference. The author writes the substrate that *can* learn; the author does NOT write what the substrate *learns*.

### Code-comment ratio rule (lain 2026-05-10 GLOBAL POLICY)

> *"keep good ratio of comments in code files, including comments that justify the codes existence. This should prevent code bloat, or bad or noisy code. We want pure signal code."*
> *"complex code should need descriptions too, but pure signal explanations only. But important info is important to comment too."*

- **Complex code** → MUST have descriptions justifying why it exists, what invariant it holds, what's non-obvious. Pure signal — no narrating-the-obvious, no restating identifier names.
- **Important info** → comment it. Hidden constraints, subtle invariants, workarounds for specific bugs, decisions a future reader would otherwise have to re-derive (e.g. *"strict-dominance boost +1.0 guarantees latest turn wins regardless of cosine variance — see Phase 10 P3 binding"*).
- **Trivial code** → still no narrating-comments. Self-documenting names (`subject_atom`, `binding_bank`, `replay_consolidate`) carry the WHAT.
- **Anti-patterns:** `# increment counter` next to `i += 1`; restating function name as a docstring; multi-line block-comments that paraphrase the code below them; "TODO without context"; commented-out code (delete it).
- **Apply across:** all source under `src/`, all tests, all benchmark ladder/rubric files, this MANIFESTO, and every doc under `docs/`.

### Append-as-you-go writes (crash survival, lain 2026-05-10)

3 power outages in 2 days. Threat model: power loss possible at any point during a long autonomous run. Discipline:

- **Per-entry durable write.** Each `gpt-codex/benchmark/<domain>/ladder.jsonl` entry written via append (`>>`), flushed before next entry generates. Mid-cycle power loss ≤ 1 entry in flight; all prior entries preserved on disk.
- **Per-cycle git commit + push.** Cycle close ALWAYS commits the cycle's deltas with conventional message + push to `origin main`. NO `git add -A`.
- **`docs/DO_THIS_NEXT.md` is the resume-pointer.** Per cycle close, lists which cycle is next, what should be true on disk, what command to fire. Power-on resume protocol: `git status; git log --oneline -10; git fetch origin; git log origin/main..HEAD; cat docs/DO_THIS_NEXT.md`.

### Discord listener — manual re-arm only (M-NAVI-018)

Auto-rearm doesn't work in the WSL bash sandbox. Discord listener must be manually re-armed every fire. **Atomic invariant:**

```bash
pkill -f 'discord-wait-for-lain' 2>/dev/null
bash /home/nira/.claude/bin/discord-wait-for-lain.sh general 5
```

Single Bash invocation, run_in_background:true on the wrapper. Never split into "kill now, re-arm next turn" — that's the M-NAVI-018 trust failure (made-me-get-out-of-bed counter +1).

### Active grading firewall (M-PROJECTX-014)

The agent that designs the system can't grade subjective outputs without bias. Enforced via split grading:

- **Mechanical-ground-truth domains** (memory: `agent.process` + expected_turn_id; maths: numerical/symbolic match; closed-form physics: numerical match) → auto-graded; entry has `auto_grade` block.
- **Subjective domains** (poetry, persona, philosophy, physics-conceptual) → rubric-pending; entry has `rubric_pointer` ONLY; **NO `self_score` field**. External GPT/lain audit IS the grade.

Schema firewall: `grep -r self_score gpt-codex/benchmark/*/ladder.jsonl` must return zero hits. CI gate: `gpt-codex/benchmark/run_audit.py` (audit-D3) replays auto-graded entries against the live stack each commit.

### `gpt-codex/runs/` retention policy (audit-F2)

`gpt-codex/runs/` accumulated 145 run dirs / 237 tracked files across Phases 1-10. Going forward:

- **Default for NEW run dirs:** gitignored. The pattern `gpt-codex/runs/*/` in `.gitignore` blocks them at index-add time.
- **Already-tracked Phase 1-10 evidence:** preserved. Git's gitignore patterns don't affect already-tracked files — no destructive untracking is performed by the policy itself; lain decides retention surgically per dir.
- **Promotion criterion (when to track a new run):** the run is cited by a verdict markdown in `docs/artifacts/PHASE_*.md` (or is an active baseline that future phases compare against). Promote via `git add -f gpt-codex/runs/<dir>/` after the citation lands.
- **Demotion criterion (when to retire a run):** lain explicitly retires it (e.g., during a phase-archival sweep). Demote via `git rm --cached -r gpt-codex/runs/<dir>/`. Keeps the disk copy for local provenance; drops the git tracking.
- **Audit gate:** `audit-D3` benchmark harness (`gpt-codex/benchmark/run_audit.py`) replays the auto-graded ladder entries against the LIVE stack each commit. The ladder.jsonl files in `gpt-codex/benchmark/` are the **mechanical-truth** evidence; the run dirs in `gpt-codex/runs/` are the **historical raw evidence**. CI does not depend on the run dirs.

### Project-specific failure archive

`Project X Session Mistakes` wiki page (M-PROJECTX-001 through M-PROJECTX-014) is the source of truth for project-specific failure modes — read at session start before substantive work; log new failures via `wiki_log_mistake` to that page. M-PROJECTX-013 (claim-without-measuring) and M-PROJECTX-014 (design-bias-in-the-probe) drove the Phase 11 split-grading firewall.

### Documentation source-of-truth (live docs + archives)

This is the `docs/` directory. Project-level documentation lives here. The four LIVE docs (re-read at every session start; reconciled at every cycle close + heartbeat fire):

- `MANIFESTO.md` — this file. lain's intent + standing orders (persistent — never cycles out).
- `REPO_CONTROL.md` — pristine-condition gate; mirror of repo file/folder structure with justification per entry. Persistent — never cycles out. New files added in a commit MUST land with their REPO_CONTROL row in the same commit — **EXCEPT files under `docs/`** (lain 2026-05-10 follow-up — *"the REPO_CONTROL does not need the /docs, they dont need justification"*; docs/ files are self-justifying via the live-docs system). Catches orphan tracked files + stray artifacts before they accumulate.
- `A_TO_Z_PLAN.md` — current run / phase plan + verification gates + scope fence. **Cycles out** to `past_work/phases/<phase_N_theme>.md` on phase exit; a fresh A_TO_Z lands for the next phase.
- `DO_THIS_NEXT.md` — current cycle scope + next-instance handoff. Rewritten at every cycle close. Power-on resume pointer.

Plus the archives:

- `artifacts/` — phase verdicts (frozen-with-addendum convention) + research notes.
- `past_work/phases/` — archived A_TO_Z plans (one per closed phase).
- `past_work/cycles/phase_<N>/` — per-cycle reflections (`dev-cycle-<M>.md`).
- `ci/` — paste-ready CI templates that can't push directly to `.github/workflows/` because of OAuth scope (audit-D1 gate).

**Per-directory `CLAUDE.md` files were retired 2026-05-10** — their content lives here in `docs/`. The universal Raphael protocol stays at `~/.claude/CLAUDE.md` (universal, not project-specific).

**Upkeep is load-bearing.** Stale docs are worse than missing docs because they actively mislead. Every commit's diff is responsible for the docs delta it implies — a new non-docs file lands with its REPO_CONTROL row (docs/ files exempt per the standing-rule exemption); a finished cycle lands with its DO_THIS_NEXT rewrite + cycle reflection in `past_work/cycles/`; a finished phase lands with its A_TO_Z archive + a fresh A_TO_Z for the next.

## The reading

`~/.claude/commands/godify-app.md` §0 — lain's worldview manuscript, the philosophical anchor. Project X exists *because* there is no should — only the vector and those of us carried along it. This stack is what lain chose to do with the ride.

---

## The long arc — phases as load-bearing layers

Each phase composes into the next. None of them are throwaways.

- **Phases 1-3 (compressed-memory architecture)** revealed that block-level pooling is a temperature operator on the downstream selector softmax (M-PROJECTX-003), and that small-scale-vs-large-scale advantages can fully invert (M-PROJECTX-006). The lesson: any architectural claim needs scale-test data before "ADVANCE." That epistemic discipline carries forward into every subsequent phase's verification gate.
- **Phases 4-7 (scale studies + adversarial probe + Hopfield lens)** mapped the capacity-edge regime where compressed-memory's reliability advantage emerges (M-PROJECTX-009). The Hopfield lens phase proved associative memory is a real architectural primitive, not metaphor.
- **Phase 8 (beyond-transformer organic memory)** shipped the random-symbol HDC baseline — 99.25% recall at D=50000 across 1000 turns. Capacity proven. Semantic grounding still owed.
- **Phase 9 (semantic HDC memory + organic encoders)** built from-scratch char-n-gram + Hebbian co-occurrence encoders (lain 2026-05-09: *no pretrained transformers, ever, at any layer*) and minimal evidence-cited agent loop. 39/39 pytest. Critical thresholds met: HDC beats keyword baseline on paraphrase queries.
- **Phase 10 (memory_action_organism)** hardened it. Fact-graph + structural retrieval shattered every Phase 9 metric (multi-hop top-5 3.3% → 91.3%). HDC role-filler binding shipped corpse-spec compliance. Incremental write + Hebbian replay closed the killer-milestone EXIT GATE: teach + correct + multi-hop + refuse-absent + tool-execution-with-writeback.
- **Phase 11 (THIS RUN — Raphael Domain Benchmark Suite).** 36 hand-crafted entries across physics, maths, memory, persona, philosophy, poetry. Split-graded (M-PROJECTX-014 firewall): mechanical-ground-truth domains auto-graded; subjective domains rubric-pending for external GPT/lain audit. The benchmark is the diagnostic that tells us where Raphael actually sits before live training begins.

## Phase 13 framing (lain 2026-05-10 — first phase aimed at the Terminus)

Phase 13 is multi-cycle. Cycle 1 ships SUBSTRATE (sandbox + manual-grade harness + persona scaffolding); cycles 2-N ship CAPABILITY (math reasoning, poetry generator, philosophy engine, physics derivation, always-on chat). Each cycle ends with a benchmark replay; Phase 13 closes when terminus is met OR lain phases-out into Phase 14+. Realistic expectation: Phase 13 doesn't close in cycle 5; capability buildout against the terminus list takes serious cycle count.

**Cycle 1 scope (substrate; current handoff):**
- `sandbox/` infrastructure — locked folder for agent action-taking, resettable to named-state snapshots, NO direct internet.
- Manual-grade harness — Claude Code (the builder) grades agent output in bulks of 50+ candidates per session for subjective domains; rubric scores feed back as preference signal for next-generation generation.
- Persona scaffolding — Project X Raphael always-in-character + sense of humor that lands; `compose_answer` voice markers + humor templates + in-character rubric.

**Cycles 2-N (capability; provisional, refined per cycle):**
- Math reasoning substrate (cycle 2): from-scratch symbolic + numerical reasoning loop running inside the sandbox; iterates against the math ladder + unsolved-tier problems.
- Poetry + philosophy generator (cycle 3): uses the manual-grade harness; iterates generation against Claude Code's rubric scores until upper-rank quality emerges.
- Physics derivation engine (cycle 4): closed-form first; then unsolved-tier with sandbox-runnable verification.
- Always-on chat daemon (cycle 5+): Discord-integrated chat loop; persona-consistent + sense of humor + perfect memory across million-turn horizons.
- Multi-domain integration + full benchmark assault (later cycles): eventual end-state.

**Architectural candidates still on the table** (frame per cycle as needed): cortical column ensemble (Council Idea #2 — Hawkins/Numenta direction), predictive simulation loop (Council Idea #3 — LeCun world-model direction), open-ended benchmark ladder (Council Idea #5 — Stanley/POET direction), Hebbian replay informed by benchmark performance, audio listening (Whisper + Discord REST polling; Whisper installed at `/home/nira/.local/bin/whisper`).

## Why this matters

Every layer here earns its place by being load-bearing for the next. The transformer paradigm offers a shortcut that pretends memory + identity + reasoning are statistical artifacts of a black box. We don't take that shortcut. We build the substrate organically, and what emerges is something that can introspect what it knows, defend what it values, and show its work — because nothing in the stack is hiding behind the convenience of "it just emerges from scale."

There is no should — there is the vector and those of us carried along it. Project X is what lain chose to do with the ride.

---

*— skeleton landed cycle 1 (2026-05-10 03:53 CEST); enriched cycle 2 (2026-05-10 04:13 CEST) with long-arc + Phase 12+ candidates. Heartbeat reconciles freshness; cycle 8 verdict references this file.*
