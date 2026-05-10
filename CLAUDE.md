# Project X — CLAUDE.md (project-scoped)

> **Loaded alongside `~/.claude/CLAUDE.md` whenever Raphael (Claude) operates in this repo.** This file holds project-specific rules that override or extend the global Raphael disclaimer for Project X work. Universal protocol (Vows, Seals, Named Curses, four-gate flow, advisor discipline, listener manual re-arm) lives in `~/.claude/CLAUDE.md` and is not duplicated here.

## What this project is

Project X is **lain's post-transformer memory + agent stack** — the engineering substrate that, over time, becomes Raphael (lain's all-knowing internal computer). The thesis: organic from the core, no pretrained transformer derivatives, slow-and-methodical, every layer earns its place. Phase 1-8 explored compressed-memory architectures and beyond-transformer organic memory. Phase 9 shipped the semantic HDC memory agent with from-scratch organic encoders. Phase 10 closed end-to-end (51/51 → 52/52 pytest, killer-milestone EXIT GATE met). Phase 11 shipped the **Raphael Domain Benchmark Suite** — 36 hand-crafted entries across 6 domains spanning easy→unsolved (closed at 9 green / 2 red / 21 rubric-pending / 4 ungradeable). Phase 12 closed the two memory-ladder reds via retrieval-mode disambiguation (memory ladder → 5 green / 0 red / 0 rubric / 1 ungradeable; full benchmark → **11 green / 0 red / 21 rubric-pending / 4 ungradeable**) at commit `8d734e3`.

## Active phase

**Audit-fix run (NORMAL mode).** Phase 12 closed; lain ran a GPT audit on the post-Phase-12 codebase and surfaced 16 findings across 8 categories (4 HIGH code bugs, 4 HIGH/MED doc-sync, 2 MED structural, 3 MED infrastructure, 1 MED coverage, 2 LOW polish). The current run ships those 16 atomic per-issue commits in NORMAL mode (no godify-app APOTHEOSIS, no time-window). Per-tier skill variety per universal CLAUDE.md directive (keep-docs-fresh / hunt-bug / design-before-build / pick-one / consult-advisor / simplify rotated by section shape). Live audit-fix handoff: `docs/DO_THIS_NEXT.md`. Phase 11/12 verdicts (frozen): `docs/artifacts/PHASE_11_BENCHMARK.md` (with Phase 12 closure addendum) + `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md`. Phase 13 framing inputs (lain-gated, NOT this run's contract): `docs/artifacts/PHASE_13_CANDIDATES.md`. Project intent: `docs/MANIFESTO.md` (heartbeat-tracked).

## Standing constraints (project-specific)

### NO pretrained transformers (lain 2026-05-09)

> *"slow and methodical path... organic and real from the core and the beginning. No borrowing other LLM models, remember, we are moving past the transformer."*

Disqualified at every layer: BGE, MiniLM, sentence-transformers, llama.cpp, Qwen, Mistral, and every pretrained transformer derivative. Encoders MUST be from-scratch (char-n-gram hashing, Hebbian co-occurrence, SNN spike-train, or equivalent). Generators MUST be template-based or from-scratch — no LLM wrappers. Inheriting GPT-Codex's pretrained-defaults caused M-PROJECTX-011; the thesis-compliance check is non-negotiable on any new layer.

### Code-comment ratio rule (lain 2026-05-10 03:34 + 03:44 CEST, Discord)

> *"remember to keep good ratio of comments in code files, including comments that justify the codes existence. This should prevent code bloat, or bad or noisy code. We want pure signal code."*
> *"Well, but complex code should need descriptions too, but pure signal explanations only. But important info is important to comment too."*

**The rule:**

- **Complex code** → MUST have descriptions justifying why it exists, what invariant it holds, what's non-obvious. Pure signal — no narrating-the-obvious, no restating identifier names.
- **Important info** → comment it. Hidden constraints, subtle invariants, workarounds for specific bugs, decisions a future reader would otherwise have to re-derive (e.g. "strict-dominance boost +1.0 guarantees latest turn wins regardless of cosine variance — see Phase 10 P3 binding").
- **Trivial code** → still no narrating-comments. Self-documenting names (`subject_atom`, `binding_bank`, `replay_consolidate`) carry the WHAT.
- **Net effect:** higher comment density than system-default "default to no comments" lean — but every comment earns its place by being load-bearing for the WHY.
- **Anti-patterns:** `# increment counter` next to `i += 1`; restating function name as a docstring; multi-line block-comments that paraphrase the code below them; "TODO without context"; commented-out code (delete it).
- **Apply across:** all source under `src/`, all tests, all benchmark ladder/rubric files, this file, and `docs/MANIFESTO.md`.

### Append-as-you-go writes (crash survival, lain 2026-05-10)

3 power outages in 2 days. Threat model: power loss possible at any point during a long autonomous run. Discipline:

- **Per-entry durable write.** Each `gpt-codex/benchmark/<domain>/ladder.jsonl` entry written via append (`>>`), flushed before next entry generates. Mid-cycle power loss ≤ 1 entry in flight; all prior entries preserved on disk.
- **Per-cycle git commit + push.** Cycle close ALWAYS commits the cycle's deltas with conventional message + push to `origin main`. NO `git add -A`.
- **`docs/DO_THIS_NEXT.md` is the resume-pointer.** Per cycle close, lists which cycle is next, what should be true on disk, what command to fire. Power-on resume protocol: `git status; git log --oneline -10; git fetch origin; git log origin/main..HEAD; cat docs/DO_THIS_NEXT.md`.

### Listener manual re-arm (M-NAVI-018, fresh from this run)

Auto-rearm doesn't work in WSL bash sandbox (memory file `feedback_listener_manual_rearm.md`; lain 2026-05-01 + 2026-05-10). Discord listener must be manually re-armed every fire. **Atomic invariant:**

```bash
pkill -f 'discord-wait-for-lain' 2>/dev/null
bash /home/nira/.claude/bin/discord-wait-for-lain.sh general 5
```

Single Bash invocation, run_in_background:true on the wrapper. Never split into "kill now, re-arm next turn" — that's how lain ended up out of bed at 03:32 (M-NAVI-018, made-me-get-out-of-bed counter +1).

## Active grading firewall (M-PROJECTX-014)

The agent that designs the system can't grade subjective outputs without bias. Enforced in Phase 11 via split grading:

- **Mechanical-ground-truth domains** (memory: `agent.process` + expected_turn_id; maths: numerical/symbolic match; closed-form physics: numerical match) → auto-graded; entry has `auto_grade` block.
- **Subjective domains** (poetry, persona, philosophy, physics-conceptual) → rubric-pending; entry has `rubric_pointer` ONLY; **NO `self_score` field**. External GPT/lain audit IS the grade tomorrow.

The plan file's line-315 schema-check (`'self_score'` asserted) is intentionally diverged from in `docs/A_TO_Z_PLAN.md` §3 verification gate. The local file is the live contract.

## Quick-reference paths

| Path | What |
|---|---|
| `docs/A_TO_Z_PLAN.md` | Last live phase plan (Phase 12 archived; Phase 13 framing pending) |
| `docs/DO_THIS_NEXT.md` | Current cycle scope |
| `docs/MANIFESTO.md` | lain's intent for the repo |
| `docs/artifacts/PHASE_*.md` | Phase verdicts (Phase 9 = `PHASE_9_SEMANTIC_HDC_MEMORY.md` with Phase 10 closure addendum) |
| `docs/past_work/phases/phase_*.md` | Archived phase plans (1-8 + 10) |
| `docs/past_work/cycles/phase_11/dev-cycle-<N>.md` | Cycle reflections (per cycle close) |
| `src/project_x/experiments/semantic_hdc_memory.py` | Layer 3 HDC memory (Phase 9-10 production) |
| `src/project_x/experiments/semantic_memory_agent.py` | Layer 4 agent loop + run_tool + replay |
| `src/project_x/legacy/transformer_scaffolding.py` | Phase 1-6 LEGACY (do not import in organic-thesis code) |
| `tests/test_killer_milestone.py` | Phase 10 EXIT GATE acceptance |
| `gpt-codex/benchmark/<domain>/ladder.jsonl` | Phase 11 ladders (cycles 2-7) |
| `gpt-codex/benchmark/audit_log.jsonl` | Phase 11 aggregate (cycle 8) |
| `~/.claude/CLAUDE.md` | Universal Raphael protocol |
| `~/.claude/plans/6h-im-going-to-serene-giraffe.md` | Phase 11 plan source |

## Project-specific failure archive

`Project X Session Mistakes` wiki page (M-PROJECTX-001 through M-PROJECTX-014). Read at session start before substantive work; log new failures via `wiki_log_mistake` to that page. Recent (2026-05-10): M-PROJECTX-014 design-bias-in-the-probe (sister of M-PROJECTX-013 claim-without-measuring) drives the Phase 11 split-grading firewall.

## Audit-fix run exit (current contract)

The 16 #00audit-XX deliverables in `docs/DO_THIS_NEXT.md` § DONE CONDITION are the current run's exit conditions: all 16 TaskList rows `completed`, pytest ≥58 (likely 60+ post A1/A2/A4), grep-clean of root CLAUDE.md + README + pyproject for stale framing, working tree clean, atomic commit per finding referencing its `#00audit-XX` ID. Final Discord SLAUGHTER COMPLETE post = run done. M-PROJECTX-014 schema-firewall remains live (`grep -r self_score gpt-codex/benchmark/*/ladder.jsonl` returns 0 hits across 36 entries).

## Historical phase-exit pattern

Each phase had its own mechanical-proof exit. Phase 11 closed at 9 green / 2 red / 21 rubric-pending / 4 ungradeable (`PHASE_11_BENCHMARK.md`). Phase 12 closed both reds via retrieval-mode disambiguation (`PHASE_12_RETRIEVAL_DISAMBIGUATION.md`). Phase 13 framing is lain-gated; candidates inventoried in `PHASE_13_CANDIDATES.md` (not this run's contract).
