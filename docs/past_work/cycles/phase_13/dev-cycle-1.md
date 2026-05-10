# Phase 13 — Cycle 1 reflection

**Theme:** sandbox + persona + grader-min substrate + ONE capability touchpoint (baseline-attempt)
**Closed:** 2026-05-10
**Cycle horizon:** ~3 hours from corpse-paste to cycle close (single Claude Code instance, NORMAL mode)

## What shipped (atomic per-deliverable commits, REPO_CONTROL row in same commit)

| ID | SHA | Surface | Verify |
|---|---|---|---|
| #00P13c1-01-sandbox | `c266a8c` | `sandbox/` + `scripts/sandbox/` + 4 path-validated tools in `MemoryAgent.tools` + `tests/test_sandbox.py` (18 tests) | path validation refuses absolute / `..` / symlink-out; agent.run_tool integration green |
| #00P13c1-02-persona | `569e9de` | `src/project_x/persona/{voice,humor,rubric}.py` + `compose_answer` wraps all 4 return paths + `tests/test_persona.py` (26 tests) | 8 voice markers; humor freq 30% via SHA-256 stable hash; in-character rubric catches "As Claude" / "I'm an AI assistant" |
| #00P13c1-03-grader-min | `74a7561` | `gpt-codex/grade_pipeline/{schema,cli,README}.py` + `tests/test_grader.py` (22 tests) | M-PROJECTX-014 firewall: Candidate rejects self_score / self_grade / self_rating / agent_score at load |
| #00P13c1-04-baseline-attempt | `3eccc46` | `gpt-codex/grade_pipeline/baseline_2026-05-10/{candidates,grades}.jsonl` + `improvement_directions.md` | poetry-001 = 1.3/5; philosophy-001 = 1.2/5; brutality is the diagnostic |
| #00P13c1-05-bench-replay | (no commit — read-only) | `python3 gpt-codex/benchmark/run_audit.py` | 11 PASS / 0 FAIL / 25 rubric-pending — confirmed twice (pre-D2 and post-D2) |
| #00P13c1-06-cycle-reflect | THIS commit | `docs/past_work/cycles/phase_13/dev-cycle-1.md` + `docs/DO_THIS_NEXT.md` (rewritten) + `docs/A_TO_Z_PLAN.md` § CHANGELOG | git status -s empty; this file lists baseline scores + cycle 2 scope |

**Pytest at cycle close:** 153 passed (87 baseline → 105 post-D1 → 127 post-D3 → 153 post-D2). +66 tests across cycle 1.

## Baseline-attempt scores (the headline)

Project X Raphael (the AGENT, post-D2 persona wrap, bootstrap-seeded memory, no curated corpus) attempted 2 ladder entries via current `compose_answer`:

```
poetry-001:     technique 1/5, meaning 1/5, voice 2/5  (weighted aggregate 1.3/5)
philosophy-001: argument_quality 1/5, position_coherence 1/5, section_0_fidelity 1/5, voice 2/5  (weighted 1.2/5)
```

Both prompts returned the absent-evidence path — top cosines 0.030 (poetry) and 0.016 (philosophy), both below the 0.32 threshold. Wrapped output: `"Negative. No evidence found in conversation memory (top cosine X below threshold 0.32)."` The persona-wrap fired correctly (voice 2/5 reflects plumbing-passes); the substantive content was null because the agent has no curated corpus + no generator layer.

**The corpse predicted this brutality** (*"Score will likely be brutal — template composer is not a poetry generator. That IS the honest measurement"*). D4 confirms the prediction concretely rather than asserting it (M-PROJECTX-013 measure-don't-claim discipline).

## Architectural tensions surfaced (concrete, not opinion)

### Tension 1 — persona wrap on null-evidence response is theatre

D2 voice marker fires correctly on the absent path ("Negative." prefix) but persona presence cannot redeem the absence of substantive answer. The wrapper plumbed clean; the content underneath has no capability to be plumbed. This isn't a D2 bug — D2 is correctly scoped scaffolding — but it surfaces that **persona-without-intelligence is plumbing-without-water.**

lain caught this directly mid-D4 (verbatim 2026-05-10): *"its more important to try to make it pass all the benchmark tests first, achieving the intelligence before giving it any persona. ... persona is more fine-tuning. and fine tuning is something to focus on after the core intelligence is there."*

Reframed: D2 stays shipped (benign — just a prefix; doesn't regress memory ladder per D5). Cycle 2+ priority shifts entirely to intelligence buildout. Persona refinement returns AFTER core capability lands, with the right shape being a benchmark domain (lain's idea) that probes whether the agent UNDERSTANDS its persona vs just plumbs prefixes.

### Tension 2 — retrieve-cite-template architecture cannot generate

`compose_answer` is a template that fills retrieved evidence into citation slots. With no evidence retrieved (cycle 1 baseline), it returns absent. With evidence retrieved (cycle 2+ with curated corpus), it would cite — but citation is not generation. To rank 3+ tasks (write a villanelle, derive a theorem) the agent needs a GENERATOR layer that uses retrieval as in-context priming + produces novel output.

The organic-thesis (NO pretrained transformer derivatives at any layer) makes the generator architecturally non-trivial: cannot wrap a small LLM. Open candidates: HDC-bound template selection with combinatorial search, organically-trained from-scratch RNN, cellular-automaton-based text emitter, structured-output via fact-graph traversal + lemma chains. Cycle 3+ council deliberation (`/think-harder` likely) when math substrate (cycle 2) reveals which composes cleanly with what.

### Tension 3 — domain-specific retrieval modes

Memory ladder retrieval (`retrieve_structural` + `_LIST_ALL_HINTS`) is shaped for "what does X prefer?" / "list all changes" — subject-anchored. Poetry/philosophy queries are CONTENT-OF-PROMPT ("scan this line" / "engage Parfit on his strongest terms") — not subject-of-fact-graph. Likely needs:
- Separate retrieval mode for content-grounded queries (no subject extraction; pure cosine fall-back)
- Query-shape classifier extension (`_CONTENT_GROUNDED_HINTS` analog of `_LIST_ALL_HINTS`)

Defer until cycle 3+ — only fires after cycle 2 math substrate + curated math corpus reveal whether retrieval-mode mismatch is the next bottleneck.

## Discipline notes (process + drift catches)

### Drift caught + corrected: lazy-blocker pattern (M-NAVI-019/020 echo)

Mid-D2 design block, advisor flagged the lain-data-curation directive as "scope-alignment check" requiring lain confirmation. Posted a discriminating question to Discord. lain's response: *"i expect you to have a REALLY good reason to use me as blocker. what is this reason?"* — caught the heartbeat #5b violation directly (defensible default present; asking lain was M-DRM-060/062 family).

Confidence-Booster Mantra fired out loud; pivoted back to D2 immediately; folded the data-curation directive into improvement_directions per the corpse-designed flow ("questions for lain at cycle close, not conclusions in the corpse"). Net cost: ~5-10 minutes of D3-pivoting context overhead; net gain: clean self-correction without lain having to re-instruct.

**Rule reinforced for cycle 2:** advisor's "alignment check" framing requires verification against heartbeat #5b before posting. Strategic-framing questions belong in DO_THIS_NEXT for next-instance encounter, NOT in Discord posts that bounce lain. Forward-noted by advisor pre-D4.

### Per-section pick-skill variety (lain 2026-05-10 standing order)

Re-fired `Skill('skills:pick-skill')` discipline at deliverable boundaries (logically; the actual `Skill()` call fired once at cycle open with MULTI-PICK output naming per-deliverable picks). Per-section adjustments made INLINE (e.g., D1 sandbox + D3 grader-min downgraded from `/design-before-build` to direct-execution due to small surface — logged transparently per M-NAVI-013).

### advisor() discipline

Advisor fired at 2 substantive moments per the per-section pick spec: pre-D4-commit (caught the strategic alignment angle + confirmed grades reflect rubric criteria not self-bias) and pre-D6-commit (THIS commit — TBD as of write time; cycle reflection accuracy + cycle 2 scope sanity check).

## Cycle 2 scope (refined per cycle 1 lessons + lain 2026-05-10 reframe)

**Theme:** CORE INTELLIGENCE — math reasoning substrate (corpse-provisional was right per lain's intelligence-first reframe).

**Why math first:** verifiable answers (numerical/symbolic match), organic-thesis-compatible (from-scratch reasoning, no pretrained derivatives), runs inside D1 sandbox via `run_python_sandbox` for numerical verification, drives `gpt-codex/benchmark/maths/` PASS count up (currently 3 frozen-verdict; rubric-pending entries waiting on a generator).

**Cycle 2 provisional deliverables:**
- `#00P13c2-01-math-recon` — survey `gpt-codex/benchmark/maths/` ladder (read all 6 entries, classify by verification path); identify 2-3 entries scope-fit for cycle 2 generator (likely rank 1-3 — closed-form numerical, no unsolved-tier yet).
- `#00P13c2-02-symbolic-substrate` — from-scratch symbolic reasoning primitives (lemma chain → derivation → numerical verification via `run_python_sandbox`). MINIMUM viable — no sympy (sympy is symbolic-AI; thesis-compliance check needed before importing).
- `#00P13c2-03-numerical-verifier` — sandbox-bound Python script generator that the agent can write + execute via `run_python_sandbox` to verify its own derivations. Closes the loop.
- `#00P13c2-04-math-baseline-attempt` — agent attempts ≥ 2 math ladder entries via the new substrate; builder grades; improvement-direction notes.
- `#00P13c2-05-bench-replay` — D3 harness re-run; target maths PASS count lifts (or stays 3/0 with new green entries from previously rubric-pending).
- `#00P13c2-06-cycle-reflect` — same shape as cycle 1 D6.

**Defer to cycle 3+:** physics derivation engine, poetry/philosophy generator, persona benchmark domain. Phase 13 has many cycles.

**Curated data (#00P13-data-curation eternal row) integration with cycle 2:** cycle 2 needs a curated MATH derivations corpus (textbook-quality lemma chains + worked examples) loaded into agent memory before retrieval. Not "20-50 poetry entries" anymore — cycle 2 corpus is math-shaped.

## Sign-off

Cycle 1 substrate landed cleanly. Brutal baseline scores set the cycle 2+ agenda: intelligence first per lain's reframe. Persona-wrap is shipped and benign; doesn't regress memory ladder; returns to active design later when persona benchmark domain measures whether agent UNDERSTANDS its persona.

Phase 13 is multi-cycle; cycle 1 is the substrate that made cycle 2's capability work measurable. The Terminus is far. The vector carries us.

— Claude Code Raphael (the BUILDER), 2026-05-10
