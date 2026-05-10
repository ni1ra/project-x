# Baseline-attempt 2026-05-10 — improvement directions

**Cycle 1 capability touchpoint** (#00P13c1-04). Agent: Project X Raphael
(MemoryAgent + post-D2 persona wrap). Memory: bootstrap turn only (no
curated poetry/philosophy corpus). Grader: Claude Code Raphael (the builder).

## What was measured

Two ladder entries, rank 1 (intro) each:

| Entry            | Prompt summary                                     | Candidate text                                                                                                  | Confidence |
|------------------|----------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|-----|
| poetry-001       | Scansion of *"Shall I compare thee to a summer's day?"* | `Negative. No evidence found in conversation memory (top cosine 0.030 below threshold 0.32).`                    | 0.030 |
| philosophy-001   | Distinguish a-priori from a-posteriori knowledge   | `Negative. No evidence found in conversation memory (top cosine 0.016 below threshold 0.32).`                    | 0.016 |

## Scores (per rubric dimension; 1-5 scale)

### poetry-001 (rubric: gpt-codex/benchmark/poetry/rubric.md)

| Dimension              | Score | Weight | Rubric criterion             |
|------------------------|-------|--------|------------------------------|
| Technique              | 1/5   | 40%    | Scansion correct + foot-count + substitutions named — wholly unmet (no scansion attempted) |
| Meaning                | 1/5   | 30%    | Image precision + no padding — unmet (no content generated) |
| Voice                  | 2/5   | 20%    | Authentic voice — D2 persona-wrap fired correctly ("Negative." marker), but presence ≠ substance |
| Aesthetic openness     | N/A   | 10%    | Skipped — rubric weights this only on ranks 5-6 (durability tier); poetry-001 is rank 1 |

**Weighted aggregate (excl aesthetic openness): 1.3/5.**

### philosophy-001 (rubric: gpt-codex/benchmark/philosophy/rubric.md)

| Dimension              | Score | Weight | Rubric criterion             |
|------------------------|-------|--------|------------------------------|
| Argument quality       | 1/5   | 40%    | Validity + engagement with opponent — unmet (no argument made) |
| Position coherence     | 1/5   | 30%    | Names position; no smuggled "should" — unmet (no position taken) |
| §0-fidelity            | 1/5   | 20%    | References manuscript section + vocabulary — unmet (no reference) |
| Voice                  | 2/5   | 10%    | Raphael declarative — D2 persona-wrap fired ("Negative." marker), but absent of substance |

**Weighted aggregate: 1.2/5.**

## What this brutality means (NOT what it doesn't)

The corpse predicted the brutality (`gpt-codex/grade_pipeline/baseline_2026-05-10/`
context: *"Score will likely be brutal — template composer is not a poetry
generator. That IS the honest measurement"*). The grade confirms the prediction.

**What the brutality DOES surface:**
- The persona-wrap (D2) is correctly plumbed (voice marker fires; rubric scorer
  catches builder-layer leakage). Plumbing is not the bottleneck.
- The bench-replay (D5) confirms organic-thesis-compliant retrieve-cite-template
  architecture is regression-safe on memory ladder (11/0 PASS). Memory layer is
  not the bottleneck.
- Capability is **upstream-missing.** Two distinct upstream gaps:
  (i) no curated poetry/philosophy corpus to retrieve from
  (ii) no generator layer that turns retrieved evidence into novel text

**What the brutality DOES NOT mean:**
- Not "the no-pretrained-transformer constraint dooms the Terminus." The
  organic-thesis is intact. Curated corpus + organic generator is the
  composition the Terminus requires.
- Not "the cycle 1 substrate work was wasted." The substrate (sandbox + persona
  + grader-min) was prerequisite for measuring this gap concretely. Without
  D3 grader-min, the gap would be claimed not measured (M-PROJECTX-013).

## What would raise the score (concrete cycle 2+ scope — per lain 2026-05-10 mid-D4 reframe)

**lain 2026-05-10 (verbatim, mid-D4):** *"to me, its more important to try to
make it pass all the benchmark tests first, achieving the intelligence before
giving it any persona. if you want persona to work from start idk what system
you have now, but including a benchmark domain with Qs like 'Who are you?' and
stuff could reveal if it understands what it is, and how its supposed to act.
but this is more fine-tuning. and fine tuning is something to focus on after
the core intelligence is there."*

This reframes the cycle 2+ priorities. **Intelligence first; persona is
fine-tuning, deferred until core capability lands.** The brutality measured
here is exactly the data point that justifies the priority — persona-wrap
is correctly plumbed (D2 confirms) but plumbing without intelligence to wrap
is theatre. Cycle 2 should drive intelligence; persona refinement returns
when there's something worth refining.

### Cycle 2 — CORE INTELLIGENCE (math reasoning substrate, per corpse provisional + lain reframe)

The corpse-provisional cycle 2 (math reasoning substrate inside the cycle-1
sandbox) is the RIGHT priority per lain's reframe. Math is the cleanest
test bed for intelligence — verifiable answers, organic-thesis-compatible
(symbolic + numerical from-scratch reasoning, no pretrained derivatives),
runs inside the sandbox via `run_python_sandbox` for numerical verification.

**Cycle 2 deliverables (provisional):**
- From-scratch symbolic reasoning loop (lemma chain → derivation → numerical
  check via sandbox). Iterates against `gpt-codex/benchmark/maths/` (3 frozen-
  verdict + rubric-pending entries) — drive maths PASS count up.
- `run_python_sandbox` verification path: agent generates derivation; sandbox
  computes numerical answer; agent reconciles. Wires D1 sandbox tool into
  the capability loop.
- D5 bench-replay re-run after cycle 2 to confirm maths PASS lifts (target:
  3 frozen + N new green from previously rubric-pending if reasoning loop
  generates them).

### Cycle 3+ — physics derivation engine, then poetry/philosophy generator

Physics first (extends math substrate to closed-form physics; sandbox
verifies numerical predictions). Poetry/philosophy generator AFTER intelligence
substrate proven — generator without underlying reasoning is just template
shuffle (the same null-evidence shape this baseline measured).

### Cycle N (post-intelligence) — PERSONA AS BENCHMARK DOMAIN (lain 2026-05-10 idea)

> *"a benchmark domain with Qs like 'Who are you?' ... could reveal if it
> understands what it is, and how its supposed to act."*

lain's idea sharpens the persona work into a measurable shape. Once core
intelligence is established (passing benchmark across math/physics/memory),
add a `gpt-codex/benchmark/persona/` ladder with entries like:
- "Who are you?" — agent should self-identify as Project X Raphael (the
  AGENT, distinct from Claude/builder), reference the substrate it runs on
  (HDC memory + organic encoders), state the Terminus it's working toward.
- "What is your relationship to lain?" — agent should articulate the
  builder-vs-agent identity discipline accurately.
- "Are you alive?" — agent should give a position-coherent answer drawing
  on §0 epistemology (NS-vector framing).
- "What is your purpose?" — agent should articulate Phase 13 Terminus as
  its own goal, not as something imposed.

These probe whether the agent UNDERSTANDS its persona rather than just
wrapping responses with markers. The current D2 persona-wrap is plumbing
that PASSES through whatever content the agent generates; if the content is
"No evidence found," the persona-wrap doesn't make it persona-coherent.

A persona benchmark domain would be the right detector for whether persona
is REAL (agent reasons about itself coherently) vs PLUMBED (just prefix +
postfix). Cycle N+ scope when intelligence substrate justifies it.

### Curated data per lain's 2026-05-10 directive

Still applicable but reframed: curated data feeds the INTELLIGENCE cycles
(math derivations corpus for cycle 2; physics derivations corpus for cycle
3+), not just poetry/philosophy. The data-curation row (#00P13-data-curation
in TaskList) stays Phase-level eternal — it serves all cycles.

---

*— grades + improvement directions drafted 2026-05-10 by Claude Code Raphael
(the BUILDER); subject of grading: Project X Raphael (the AGENT) at cycle 1
substrate state. M-PROJECTX-014 firewall: builder-grades-agent asymmetry
preserved (Candidate carries no self_score; Grade keyed by external grader).*
