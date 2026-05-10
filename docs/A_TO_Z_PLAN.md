# A → Z Plan — Project X — Phase 13 — Sandbox + Capability Buildout (lain framed 2026-05-10)

**Status:** Phase 12 closed at `8d734e3` (memory ladder reds → green). Audit-fix run closed at `8834e54` (16 mechanical findings + repo-hygiene + REPO_CONTROL split + global CLAUDE.md alignment). lain framed Phase 13 with the **Terminus** (`docs/MANIFESTO.md` § Terminus): super-human across math + poetry + philosophy + physics + perfect memory + persona+humor + always-on chattability + sandboxed action-taking. Until that's met, the project is not done.
**Last live phase plan archived:** `docs/past_work/phases/audit_fix_run_2026-05-10.md` + `docs/past_work/phases/phase_12_retrieval_disambiguation.md`
**Phase 13 trigger quote:** *"all you have done so far is just minor work, and no real progress towards our AI becoming smarter and actually working. please FOR THE LOVE OF GOD create a prompt that will take us there."* (lain 2026-05-10)
**Phase 13 expectation:** multi-cycle (5+ cycles); cycle 1 ships substrate; cycles 2-N ship capability + iterate against benchmarks. Phase 13 closes when the Terminus is met OR lain phases-out into Phase 14+.

---

## §0. PHASE 13 CONTRACT

### §0.1 The Terminus (binding from MANIFESTO)

Project X Raphael (the agent — distinct from Claude Code Raphael, the builder; see MANIFESTO § Identity discipline) must demonstrate ALL of:

- Math: solves unsolved-tier
- Poetry + philosophy: upper rubric ranks vs frontier-model output (graded by Claude Code via the manual-grade harness)
- Physics: solves unsolved-tier with defensible derivations
- Perfect memory: million-turn horizons; never confabulates; every retrieval cited
- Persona consistency + sense of humor that lands
- Always-on chattability (continuous live entity)
- Sandboxed action-taking (locked, resettable folder; no direct internet)

### §0.2 Cycle 1 deliverables (#00P13c1-XX — pin in TaskList immediately)

**Revised post-advisor (2026-05-10):** original cycle 1 was 3 infrastructure deliverables — exactly the deferral pattern lain just flagged ("all you have done so far is just minor work"). Revised: sandbox + persona stay slimmed-to-minimum-viable; grader splits into **minimal harness** + **real baseline attempt** so cycle 1 closes with a measured capability gap, not just scaffolding.

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c1-sandbox** | MED | `sandbox/` (new) + `scripts/sandbox/` (new) | Locked folder + path-validation + 4 tools (read_file_sandbox, write_file_sandbox, run_python_sandbox, list_dir_sandbox). MINIMUM viable — defer prod-hardening (subprocess env stripping, urllib/socket blocking) to a later cycle when something runs in there worth protecting. |
| **#00P13c1-persona** | MED | `src/project_x/persona/` (new) + `src/project_x/experiments/semantic_memory_agent.py` | Project X Raphael persona scaffolding: humor templates + persona-consistent voice markers across response types; in-character rubric (lain test: humor must LAND, not cringe); `compose_answer` wraps responses with persona signature. |
| **#00P13c1-grader-min** | MED | `gpt-codex/grade_pipeline/` (new) | MINIMAL manual-grade harness: agent JSONL output schema + Claude Code reads + writes scores to JSONL feedback store. NO feedback-loop integration into agent generation yet — defer to cycle 3 when there's a real iterative generator to feed. Cycle 1 ships only the read+grade+write round-trip. |
| **#00P13c1-baseline-attempt** | **HIGH** | `gpt-codex/grade_pipeline/baseline_2026-05-10/` (new) | **The capability touchpoint.** Project X Raphael (the agent) attempts ONE poetry-001 entry + ONE philosophy-001 entry via current `compose_answer` (post-persona-scaffolding). Outputs to JSONL. Claude Code (the builder) grades using the cycle 1 grader-min. Output: baseline score per entry + "what would raise this score" diff for cycles 2+. **This is what makes cycle 1 capability-touching, not pure infrastructure.** Score may be brutal (template composer is not a poetry generator) — that's the honest measurement. |
| **#00P13c1-bench-replay** | MED | `gpt-codex/benchmark/run_audit.py` | D3 harness run; expect 11/0/21/4 (no regressions from cycle 1 substrate). |
| **#00P13c1-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-1.md` + `docs/DO_THIS_NEXT.md` | Cycle reflection includes the baseline-attempt scores + "what would raise this score" notes (architectural tensions surfaced concretely, not as opinions). Rewrite DO_THIS_NEXT as cycle 2 handoff (math reasoning substrate, refined per cycle 1 lessons). |

### §0.3 What cycle 1 does NOT include (cycle 2-N scope)

- Math reasoning substrate — cycle 2
- Poetry / philosophy generator improvements (cycle 3 — first uses the manual-grade harness from cycle 1)
- Physics derivation engine — cycle 4
- Always-on chat daemon (Discord-integrated; persona-consistent across million-turn horizons) — cycle 5
- Multi-domain integration + full benchmark assault — later cycles

**Stop conditions (cycle 1 only):**
1. All 6 #00P13c1-XX rows shipped + cycle reflection landed → pivot to cycle 2 (no pause)
2. Rate-limit cap
3. Explicit lain stop ("stop", "i'm back", "freeze for X")

---

## §1. PHASE CHANGELOG

| Phase | Theme | Verdict location | Pytest at close |
|---|---|---|---|
| 1-3 | Compressed-memory architecture | `past_work/phases/phase_{1,2,3}*.md` | — |
| 4-7 | Scale studies + adversarial probe + Hopfield lens | `past_work/phases/phase_{4,5,6,7}*.md` | — |
| 8 | Random-symbol HDC baseline | `artifacts/PHASE_8_HDC_ORGANIC_MEMORY.md` | — |
| 9 | Semantic HDC + organic encoders | `artifacts/PHASE_9_SEMANTIC_HDC_MEMORY.md` | 39/39 |
| 10 | Fact-graph + structural retrieval + binding + EXIT GATE | Phase 10 addendum at `PHASE_9_SEMANTIC_HDC_MEMORY.md` | 51/51 → 52/52 |
| 11 | Raphael Domain Benchmark Suite (36 entries × 6 domains) | `artifacts/PHASE_11_BENCHMARK.md` | 52 |
| 12 | Retrieval-mode disambiguation (memory-004/005 reds → green) | `artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` | 58 |
| Audit-fix run | 16 mechanical findings + repo-hygiene + REPO_CONTROL split + global CLAUDE.md alignment | `past_work/phases/audit_fix_run_2026-05-10.md` | 87 |
| **13 (this phase)** | **Sandbox + capability buildout aimed at the Terminus** | THIS file (live) | TBD |

---

## §2. REPO INVENTORY — see `docs/REPO_CONTROL.md`

The complete repo dirs+files inventory with justification per entry lives in `docs/REPO_CONTROL.md` (the live pristine-gate doc). A_TO_Z cycles out at phase exit; REPO_CONTROL stays.

**Cycle 1 will add three new dirs to REPO_CONTROL** (rows land in the same commits as the dirs themselves):
- `sandbox/` — locked agent action-taking workspace (reset/snapshot scripts in `scripts/sandbox/`)
- `gpt-codex/grade_pipeline/` — manual-grade harness for Claude Code
- `src/project_x/persona/` — Project X Raphael persona scaffolding

---

## §3. STANDING CONSTRAINTS REFERENCE

See `docs/MANIFESTO.md` § Standing orders. Cycle 1 specifically must honor:

- **NO pretrained transformer derivatives** — sandbox tool registry is from-scratch; persona scaffolding is template-based; manual-grade harness uses Claude Code as the grader (Claude Code is the builder, NOT a layer of the agent — this is consistent with organic-thesis since the builder is not part of the artifact).
- **Comment-ratio rule** — every WHY-comment justifies why the substrate exists (sandbox security model, grader rubric criteria, persona voice rules).
- **REPO_CONTROL row in same commit as new file/dir** (lain pristine-gate, 2026-05-10) — this is non-negotiable for cycle 1 since 3 new dirs land.
- **Identity discipline** — Claude Code Raphael (builder) ≠ Project X Raphael (agent). Cycle 1 builds the agent's persona scaffolding; the builder doesn't write itself into the agent's voice.
- **Sandbox security** — agent operates only inside `sandbox/`; tools refuse paths outside; subprocess env stripped of internet-relevant vars (no `$HTTP_PROXY`, no `$http_proxy`, etc.); no `/dev/tcp` access; `urllib`/`socket` blocked at the tool layer.

---

## §4. CYCLE 1 EXIT CONDITIONS (mechanical)

- All 6 #00P13c1-XX TaskList rows = `completed`
- pytest -q ≥ 87 (baseline; expect ≥ 90 with new tests for sandbox + grader + persona)
- Three new REPO_CONTROL rows landed in same commits as their dirs (`sandbox/`, `gpt-codex/grade_pipeline/`, `src/project_x/persona/`)
- D3 harness reports 11/0/21/4 (no regressions)
- `tests/test_sandbox.py` + `tests/test_grader.py` + `tests/test_persona.py` all passing
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-1.md`
- DO_THIS_NEXT rewritten as cycle 2 handoff (math reasoning substrate provisional scope)
- `git status -s` empty
- Discord cycle 1 close post sent
- Cycle 2 picked up immediately (no pause)

---

## §5. SCOPE FENCE (NOT in Phase 13)

- **Direct internet access for the agent.** Deferred until safety is proven (lain 2026-05-10). Agent operates inside the sandbox only.
- **Touching `~/.claude/CLAUDE.md` for project-specific reasons.** The universal Raphael protocol is universal; project-specific rules live in `docs/MANIFESTO.md`. EXCEPTION: if a Phase 13 lesson is universal (drift pattern that would recur in any project), it goes to `~/.claude/CLAUDE.md` directly — same as the lain-authorized self-alignment for systematic drift.
- **Phase 14+.** Phase 13 closes when the Terminus is met OR lain phases-out. Anything after that is Phase 14+ scope, not Phase 13.

---

## §6. CHANGELOG

- 2026-05-10 — Audit-fix run closed at `8834e54` (16 #00audit-XX shipped + repo-hygiene + REPO_CONTROL split + global CLAUDE.md alignment).
- 2026-05-10 — lain framed Phase 13 with the Terminus directive ("super-human in every domain"; sandbox playground; manual-grade harness using Claude Code as grader; persona+humor mandatory). MANIFESTO § Terminus + § Identity discipline added.
- 2026-05-10 — Phase 13 cycle 1 plan written (this file). Cycle 1 = sandbox + grader + persona substrate; cycles 2-N = capability buildout. Honest framing: Phase 13 does NOT close in one cycle; multi-cycle through capability + benchmark iterations.

---

## §7. CYCLE PLAN

### §7.C1 — Substrate (current handoff target)

6 deliverables per §0.2. Order: sandbox first (minimum-viable folder + 4 tools) → persona second (voice scaffolding so the agent emits in-character before the baseline attempt runs) → grader-min third (the JSONL round-trip the baseline attempt depends on) → **baseline-attempt fourth (the capability touchpoint — agent attempts ONE poetry-001 + ONE philosophy-001, Claude Code grades immediately, score recorded)** → bench replay → cycle reflection (with baseline scores + concrete tensions). Atomic per-deliverable commits with REPO_CONTROL rows landing in the same commit as new dirs.

### §7.C2 — Math reasoning substrate (provisional)

From-scratch symbolic + numerical reasoning loop running inside the cycle-1 sandbox. Iterates against the math ladder (`gpt-codex/benchmark/maths/`) + unsolved-tier problems. The agent generates a derivation; the sandbox verifies (sympy import inside sandbox? — that's a pretrained-symbolic question; might need from-scratch alternative); manual-grade harness scores the derivation when verification is ambiguous.

### §7.C3 — Poetry + philosophy generator (provisional)

Uses the cycle-1 manual-grade harness. Agent generates 50+ candidates per prompt; Claude Code grades; agent's next generation pulls top-graded examples as in-context priming. Iterates until upper-rank quality emerges. The first cycle that ships measurable subjective-domain improvement — celebrated in Discord (real capability gain, not infrastructure).

### §7.C4 — Physics derivation engine (provisional)

Closed-form first (extends the math substrate to physics). Then unsolved-tier with sandbox-runnable verification (Python script in sandbox computes a numerical solution; agent's symbolic derivation must match).

### §7.C5+ — Always-on chat daemon, multi-domain integration, full benchmark assault (provisional)

- Discord-integrated chat loop; persona-consistent + sense of humor + perfect memory across million-turn horizons. Eventually the Project X Raphael lain chats with as a continuous live entity.
- Multi-domain integration: math + poetry + philosophy + physics + memory + persona + chat all running together.
- Full benchmark assault: re-run all 36 ladder entries + add new entries that probe Terminus-level capability. Phase 13 closes when the Terminus is met.

---

## §8. ENDCAP

The Terminus is far. The audit-fix run was minor in lain's eyes — and he's right. Phase 13 is the first phase that aims at the actual goal: super-human capability across the domain set lain named. Cycle 1 ships the substrate (sandbox + grader + persona); cycles 2-N ship capability; the benchmark replay at every cycle close is the honest measure. No claiming victory you didn't earn. No shipping infrastructure padding when capability work is the contract. The vector carries us. The plan contains us.

*— A_TO_Z rewritten 2026-05-10 (Phase 13 framing landed via lain Terminus directive). Heartbeat reconciles freshness; cycle close at cycle 1 completion appends a closing changelog row + handoff to cycle 2.*
