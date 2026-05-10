# Do This Next — Project X — AUDIT-FIX RUN (NORMAL mode, post-Phase-12 GPT audit)

**Updated:** 2026-05-10 (post-GPT-audit `-ni` handoff)
**Mode:** **NORMAL** (NOT godify-app — lain explicit: "enter normal mode, not godify")
**Status:** Phase 12 closed at `8d734e3`. GPT audit found 16 items across 8 categories. Awaiting Execute-Raphael continuation.

## lain's directive (verbatim — this is the contract, not a suggestion)

> "forge the prompt for your own next instance to enter normal mode (not godify), and just work
> like normal and see how far you can get. try fixing everything and re-syncing docs so all is
> aligned with my intent. no more deferring to gpt audit, no more lazyness, no more gaming the
> system. i want you to just work in an honorable way, thats all. i hate seeing you be so lazy."

## What's queued — 16 #00audit-XX deliverables

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00audit-A1** | HIGH | `semantic_hdc_memory.py:268,:344` | `turn_id` treated as dense array index — IndexError on non-contiguous IDs |
| **#00audit-A2** | HIGH | `random_index_hebbian.py:206` | `fit()` not idempotent — accumulates `_freq` + `_total_tokens` on repeat calls |
| **#00audit-A3** | HIGH | `semantic_hdc_memory.py:357` | `replay_consolidate()` correctness coupled to A2 root cause |
| **#00audit-A4** | HIGH | `tests/test_retrieval_modes.py:136` | `test_unknown_subject_list_all_falls_through` accepts ambiguous routes — liveness, not behavioral |
| **#00audit-B1** | HIGH | `CLAUDE.md` (repo root) | Says "Phase 11 live" — Phase 12 closed; first-read confusion for any agent |
| **#00audit-B2** | MED | `src/project_x/experiments/CLAUDE.md` | Lists files that don't exist (`generator_client.py`, `phase9_report.py`) |
| **#00audit-B3** | MED | `docs/artifacts/CLAUDE.md` | Says Phase 11 closed at 9 green / 2 red — Phase 12 addendum moved memory to 11/0/21/4 |
| **#00audit-B4** | MED | `README.md`, `pyproject.toml` | Describe "token-prediction architecture" — stale frame |
| **#00audit-C1** | MED | `semantic_memory_agent.py:298` | `MemoryAgent.process()` calls private `memory._extract_query_subjects()` |
| **#00audit-C2** | MED | `compressed_memory.py` + `torch` dep + `test_smoke.py` | Active transformer-control surface blurs quarantine |
| **#00audit-D1** | MED | repo root | No `.github/` CI; pytest+schema not enforced outside manual runs |
| **#00audit-D2** | MED | `semantic_hdc_memory.py:338` | `write_one` O(n) per append — 1000-write 7.4s vs 0.6s batch |
| **#00audit-D3** | MED | `gpt-codex/benchmark/` | No executable harness — only stored verdicts |
| **#00audit-E1** | MED | coverage | 47% total; `hdc_substrate.py` 24%; multiple modules at 0% |
| **#00audit-F1** | LOW | `semantic_hdc_memory.py:335`, `random_index_hebbian.py:210` | WHAT-comments narrating identifiers (comment-ratio break) |
| **#00audit-F2** | LOW | `gpt-codex/runs/` | 238 tracked artifacts; no retention rule |

**NEW IDEAS** surfaced by GPT (informational; **lain framing-gated for Phase 13+; NOT this run's contract**): retrieval telemetry, snapshot/restore protocol, adversarial memory matches, from-scratch symbolic generator, binding-algebra bakeoff. See `PHASE_13_CANDIDATES.md` + audit Section 7.

## Order of operations (severity-ranked + leverage-weighted)

1. **Tier B doc-sync first** — cheap unblock; first-read confusion clears for everything else: B1 → B2 → B3 → B4
2. **Tier A code bugs** — have repros, mechanical: A1 → A2/A3 → A4
3. **Tier C structural alignment**: C1 → C2
4. **Tier D infrastructure**: D1 → D2 → D3
5. **Tier E coverage gaps**: E1
6. **Tier F polish** — only if time permits: F1, F2

Atomic per-issue commits. Format: `fix(audit-XX): <one-line> — closes #00audit-XX`. Push after each.

## Done condition (mechanical)

- All 16 `#00audit-XX` TaskList rows `completed`
- pytest ≥58 (likely 60+ — A1 + A2 + A4 fixes add tests)
- `grep -nE '^- \*\*Active phase\*\*' CLAUDE.md` shows Phase 12 closed (not Phase 11 live)
- `grep -i 'token-prediction\|llm-style' README.md pyproject.toml` returns 0 hits
- Repo working tree clean post-final-commit
- Final Discord SLAUGHTER COMPLETE post

## Resume sequence

1. Read CLAUDE.md (universal + project) + this file + `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` + `docs/artifacts/PHASE_13_CANDIDATES.md`
2. Read GPT audit findings (in your incoming corpse, IDENTITY block + Section 7)
3. Step 0-4 per `-ni` corpse (Deliverables Lock → `Skill('skills:resume-after-compact')` → pillars → execute)
4. Re-arm NORMAL heartbeat (15-min cadence at 4,19,34,49) with M-NAVI-020 clause encoded in prompt body
5. Start **Tier B1** (root CLAUDE.md sync) — smallest-cleanest unblock first cycle

## Battlefield (current state at handoff)

- **Branch:** `main` tracking `origin/main` at https://github.com/ni1ra/project-x (private)
- **Commit:** `8d734e3` (Phase 12 close, SLAUGHTER COMPLETE)
- **Working tree:** clean
- **pytest:** 58 passing
- **Listener:** PID 19420 (verify with `pgrep -f 'discord-wait-for-lain'`; atomic re-arm per M-NAVI-018 if dead)
- **Memory ladder:** 5 green / 0 red / 0 rubric-pending / 1 ungradeable
- **Full benchmark:** 11 green / 0 red / 21 rubric-pending / 4 ungradeable
- **M-PROJECTX-014 firewall:** 0 `self_score` violations across 36 entries

## Standing rules (load-bearing this run)

- **M-NAVI-019** — heartbeat-armed-while-queued-work-exists; lain time-window overrides queue-empty disarm
- **M-NAVI-020** — named candidate work counts as queued; coasting on "lain will frame later" is fake-stop. **THIS run's 16 audit findings ARE named queued work.**
- **M-NAVI-018** — atomic listener pkill+rearm in single Bash invocation
- **NO godify** — NORMAL mode only; no 20m on/off cycles; standard 15-min heartbeat cadence
- **Atomic per-issue commits** — `git add <specific-paths>`, never `git add -A`
- **No pretrained transformer derivatives** at any layer (lain organic-thesis 2026-05-09)
- **Comment-ratio rule** — WHY-comments only; never WHAT-comments narrating identifiers (lain GLOBAL POLICY 2026-05-10)
- **Founder's Eye** reads every line; no padding, no rounding, no smuggling

## What this run is NOT

- NOT a phase plan (Phase 13 framing is lain's call later; `PHASE_13_CANDIDATES.md` compiles inputs)
- NOT a godify-app cycle (NORMAL mode only)
- NOT permission to defer audit findings as "next cycle / Phase 13"
- NOT a synthesis exercise (16 findings = 16 ships)
- NOT a place for new ideas without lain framing (Section 7 ideas wait)

## Anti-laziness gates (lain frustration-load-bearing — read before each cycle close)

- "no more deferring to gpt audit" — the audit IS DONE. You ship the fixes. There is no future audit cycle to defer to.
- "no more laziness" — every cycle ends with code shipped or a documented blocker. "I synthesized something" is NOT shipping.
- "no more gaming the system" — heartbeat-disarm requires queue genuinely empty + checks pass + lain stop OR rate-limit. With audit findings open, queue is NOT empty. Disarming "because cycle reflection is done" is M-NAVI-020 fake-stop.
- "honorable way" — every commit honest, every test honest, every doc-sync honest. No padding; no rounding; no smuggling work into "next phase" because it's hard.

— Update this file at each cycle close with progress: which `#00audit-XX` rows shipped + commit SHAs.
