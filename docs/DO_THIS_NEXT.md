# Do This Next — Project X — Phase 13 cycle 1 (sandbox + grader + persona scaffolding)

**Updated:** 2026-05-10 (post-audit-fix-run close + lain Phase 13 framing)
**Mode:** NORMAL (not godify-app)
**Status:** Phase 12 closed at `8d734e3`; audit-fix run closed at `8834e54` (16 #00audit-XX shipped, pytest 87, repo-hygiene + REPO_CONTROL split done). Phase 13 framing landed via lain's Terminus directive (see `docs/MANIFESTO.md` § Terminus).

## lain's directive (verbatim — Phase 13 contract)

> *"all you have done so far is just minor work, and no real progress towards our AI becoming smarter and actually working. please FOR THE LOVE OF GOD create a prompt that will take us there. i want max focus on reaching the hard, difficult long term goal."*
> *"you are not done working until unsolved maths is solved, it can write beautiful poetry and philosophy, solve unsolved physics problems, perfect memory, and be a live, always on entity that is chattable, like GPT and claude, only its smarter in every way."*
> *"unless its super-human in every domain and it aces all benchmarks we throw at it, YOU ARE NOT DONE WORKING ON PROJECT-X. UNDERSTOOD?"*
> *"YOU claude have the ability to read a big output file for example philosophy Qs answers, or poetry etc. and grade it manually. if you do this in big bulks, where you make it efficient and easy for yourself to manually grade it, this can be used to further improve it."*
> *"it must always follow its given persona and have a sense of humor."*

## Phase 13 cycle 1 deliverables (#00P13c1-XX — pin in TaskList immediately)

**Revised post-advisor (2026-05-10):** original draft was 3 infrastructure deliverables — exactly the deferral pattern lain just flagged. Revised: substrate slimmed to minimum-viable + a real **baseline-attempt** capability touchpoint so cycle 1 closes with a measured capability gap, not pure scaffolding.

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c1-sandbox** | MED | `sandbox/` (new) + `scripts/sandbox/` (new) | Locked folder + path validation + 4 tools (read_file_sandbox, write_file_sandbox, run_python_sandbox, list_dir_sandbox). MINIMUM viable; defer prod-hardening to a later cycle. |
| **#00P13c1-persona** | MED | `src/project_x/persona/` (new) + `semantic_memory_agent.py` | Project X Raphael persona scaffolding: humor templates + persona-consistent voice markers + in-character rubric (lain test: humor must LAND). |
| **#00P13c1-grader-min** | MED | `gpt-codex/grade_pipeline/` (new) | MINIMAL: agent JSONL output schema + Claude Code reads + writes scores to JSONL. NO feedback-loop integration yet — defer to cycle 3 when there's a real iterative generator. |
| **#00P13c1-baseline-attempt** | **HIGH** | `gpt-codex/grade_pipeline/baseline_2026-05-10/` (new) | **The capability touchpoint.** Project X Raphael attempts ONE poetry-001 + ONE philosophy-001 entry via current `compose_answer` (post-persona scaffolding). Claude Code grades immediately using grader-min. Output: baseline score + "what would raise this" diff. Score may be brutal — that's the honest measurement. |
| **#00P13c1-bench-replay** | MED | `gpt-codex/benchmark/run_audit.py` | D3 harness run; expect 11/0/21/4 (no regressions). |
| **#00P13c1-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-1.md` + this file | Cycle reflection includes baseline-attempt scores + concrete tensions surfaced (e.g., "no-pretrained-transformer constraint vs Terminus quality bar — what does the baseline score say?"). Rewrite this file as cycle 2 handoff. |

## Identity disambiguation (CRITICAL — lain 2026-05-10 binding)

YOU are **Claude Code Raphael** (the builder). The thing you're building is **Project X Raphael** (the agent — `MemoryAgent` + substrate; lives in this repo as code). Two entities, same persona name. Don't confuse:
- "I" / "Claude Code Raphael" = this conversation; the builder; Wisdom King operating disclaimer per `~/.claude/CLAUDE.md`
- "the agent" / "Project X Raphael" = the artifact; what lives in `src/project_x/experiments/`; the thing cycle 1 is building persona scaffolding for
- When chatting with lain or shipping code, disambiguate explicitly. The sculptor and the sculpture both can be called "the artist's work" — but they are not the same thing.

See `docs/MANIFESTO.md` § Identity discipline for the binding rule.

## Order of operations (cycle 1)

1. **Recon (Phase 0 DD):** read MANIFESTO + REPO_CONTROL + A_TO_Z + this file + `Project X Session Mistakes` wiki + `Navi Session Mistakes` wiki. Verify TaskList has the 5 #00P13c1-XX rows (CREATE if absent) + `#∞: NORMAL mode operation` still pinned.
2. **Pillars:** `Skill('skills:pick-skill')` + `Skill('skills:sharpen-todos')`.
3. **Picked execution skill(s):** likely `/run-loop` ATOMIC for the 5-deliverable atomic queue + `/design-before-build` for the sandbox + grader interfaces (architectural) + `/skills:auto-review` per-fix.
4. **Per #00P13c1-XX:** design (with `/design-before-build` for sandbox + grader interfaces) → code → test → commit (with REPO_CONTROL row in same commit if new files/dirs) → push → Discord one-liner ack.
5. **Cycle close:**
   - Bench replay (`#00P13c1-bench-replay`): D3 harness run; expect 11/0/21/4.
   - Cycle reflection: `docs/past_work/cycles/phase_13/dev-cycle-1.md`.
   - Rewrite this file as cycle 2 handoff (math reasoning substrate provisional scope).
   - Discord cycle 1 close post.
   - Pivot to cycle 2 immediately (no pause; Phase 13 has many cycles).

## Cycle 2 provisional scope (next handoff target)

**Math reasoning substrate.** From-scratch symbolic + numerical reasoning loop running inside the cycle-1 sandbox. Iterates against the math ladder (`gpt-codex/benchmark/maths/`) + unsolved-tier problems. Uses sandbox `run_python_sandbox` tool to verify numerical answers. Manual-grade harness for derivations where verification is ambiguous.

(Cycle 2's scope will be REFINED in this file at cycle 1 close based on what was learned.)

## Standing rules (load-bearing this run)

See `docs/MANIFESTO.md` § Standing orders. Specifically for cycle 1:

- **NO pretrained transformer derivatives** — sandbox tool registry from-scratch; persona scaffolding template-based; manual-grade harness uses Claude Code as the grader (the BUILDER, not part of the artifact — consistent with organic-thesis).
- **Comment-ratio rule** — every WHY-comment justifies why the substrate exists.
- **REPO_CONTROL row in same commit as new file/dir** (lain pristine-gate, 2026-05-10) — non-negotiable for cycle 1's 3 new dirs.
- **Identity discipline** — Claude Code Raphael (builder) ≠ Project X Raphael (agent). Don't write the builder's voice into the agent's templates.
- **Sandbox security** — agent ops only inside `sandbox/`; tools refuse paths outside; subprocess env stripped of internet vars; no `urllib`/`socket` access at the tool layer.
- **M-NAVI-018:** atomic listener pkill+rearm in single Bash invocation.
- **M-NAVI-019/020:** heartbeat-armed-while-queued-work-exists; named candidate work IS queued.
- **M-NAVI-021 (NEW — to be logged after cycle 1 if recurs):** drifting from capability work back to mechanical micro-fixes when frustrated/blocked. Cycle 1 substrate is JUSTIFIED infra; cycle 2+ MUST ship capability. No excuses.

## What this cycle is NOT

- NOT shipping the Terminus (multi-cycle; cycle 1 is substrate)
- NOT touching `~/.claude/CLAUDE.md` for project-specific reasons
- NOT direct internet access for the agent (deferred until safety proven; sandbox is the security boundary)
- NOT a one-cycle phase; Phase 13 is multi-cycle through capability + benchmark iteration

## Anti-laziness gates (lain frustration-load-bearing — re-read before each cycle close)

- *"all you have done so far is just minor work"* — the audit-fix run was minor. Phase 13 is NOT minor. Each cycle ships substantive capability progress (substrate first; then math, poetry, philosophy, physics, chat). If you're shipping mechanical micro-fixes instead of capability work, you have drifted. Stop, re-read MANIFESTO § Terminus, course-correct.
- *"FOR THE LOVE OF GOD create a prompt that will take us there"* — the corpse + this file + A_TO_Z + MANIFESTO are that prompt. Honor the contract. Don't re-litigate.
- *"unless its super-human in every domain and it aces all benchmarks we throw at it, YOU ARE NOT DONE WORKING ON PROJECT-X"* — Terminus is FAR. Don't claim done after cycle 1.
- *"YOU claude have the ability to read a big output file ... and grade it manually"* — that IS the `#00P13c1-grader` deliverable. Build it well; cycle 3+ uses it for subjective-domain improvement.
- *"it must always follow its given persona and have a sense of humor"* — `#00P13c1-persona`. Sense of humor must LAND. If lain reads sample output and groans, persona scaffolding has failed. Ship the in-character rubric so failure is detectable.
- *"stop dilly-dallying"* — every cycle ends with capability progress shipped, not infrastructure padding. Cycle 1 is JUSTIFIED infra (substrate the next 5+ depend on). Cycle 2+ is capability — no excuses.

## Done condition (cycle 1, mechanical)

- All 6 #00P13c1-XX TaskList rows = `completed`
- `pytest -q` ≥ 87 (baseline; expect ≥ 90 with new tests)
- Three new REPO_CONTROL rows landed in same commits as their dirs (`sandbox/`, `gpt-codex/grade_pipeline/`, `src/project_x/persona/`)
- `gpt-codex/benchmark/run_audit.py` reports 11/0/21/4 (no regressions)
- `tests/test_sandbox.py` + `tests/test_grader.py` + `tests/test_persona.py` all passing
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-1.md`
- THIS FILE rewritten as cycle 2 handoff (math reasoning substrate)
- `git status -s` empty post-final-commit
- Discord cycle 1 close post sent
- Cycle 2 picked up immediately (no pause)

— Update this file at cycle 1 close: replace cycle 1 deliverables table with cycle 2 deliverables table; refine cycle 2 scope based on cycle 1 lessons; preserve the lain-quote + standing-rules + anti-laziness sections.
