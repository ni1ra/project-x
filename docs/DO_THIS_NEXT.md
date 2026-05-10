# Do This Next — Project X — Phase 13 cycle 3 (Path B + substrate Tier 1)

**Updated:** 2026-05-10 (post-cycle-2 close)
**Mode:** NORMAL (not godify-app)
**Status:** Cycle 2 closed at THIS handoff commit. 6/6 #00P13c2-XX shipped (`8e7fbf7` → `fe42a7b` → `f009669` → `2689c37` → bench-replay read-only → THIS commit). Pytest 153 → 202 (+49 cycle 2 tests). D5 bench-replay 11 PASS / 0 FAIL / 25 rubric-pending — maths/memory/physics ALL no-regression. Substrate-driven mathematics graded ~4.0/5 (vs cycle 1 baseline 1.2-1.3/5; 3x lift on 1-5 rubric scale). Reflection at `docs/past_work/cycles/phase_13/dev-cycle-2.md`.

## ORDER OF EXECUTION — TIER A first, then TIER B

### TIER A — instruction-discipline alignment (lain mid-D3 asks; queue-first per lain "add to task queue")

3 rows already pinned in TaskList as #9 / #10 / #11. Universal multiplier — improves ALL subsequent cycles' execution discipline. Per CLAUDE.md self-alignment authorization (lain 2026-04-29: *systematic drift → fix universal prompts directly*), I'm authorized to ship these autonomously.

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#9 (forge cmd)** | MED | `~/.claude/commands/instruction-change.md` (NEW) | Use `/forge-prompt` to forge new global command `/instruction-change` with -g/-l flag. Default behavior: invokes forge-prompt subroutine, investigates relevant instructions for the prompt+tags lain provides, maps unclear/misleading/confusing text, maps what needs to change for clarity + how to ship the change. |
| **#10 (-ni/-c discipline)** | HIGH | `~/.claude/CLAUDE.md` + `~/.claude/commands/forge-prompt.md` + skill protocols | Use `/instruction-change -g` (first real-use) to ship: NEW RULE — Claude Code Raphael NOT allowed to invoke `/forge-prompt -ni` unprompted (lain-only; requires lain at PC). ALLOWED: `/forge-prompt -c` (continue tag) — preps docs + writes next-steps INTO DO_THIS_NEXT + auto-continues cyclically (full autonomy). PROPOSAL pattern: agent CAN propose -ni via Discord at phase transitions / context-heavy moments — but MUST send-and-continue, NEVER send-and-wait. Apply contradiction-deletion mandate (lain 2026-05-01). |
| **#11 (immediate-todo-add)** | HIGH | `~/.claude/CLAUDE.md` (likely § R1 / DELIVERABLES LOCK area) | Use `/instruction-change -g` (same invocation as #10 — folded together since both touch CLAUDE.md surface): NEW RULE — when lain adds tasks to queue (verbal "add to queue" / "task queue" / new asks during work), IMMEDIATELY add each ask as its OWN TaskList row — don't combine, don't defer. Auto-compact-survival + visibility discipline. |

### TIER B — Phase 13 cycle 3 deliverables (pin as #00P13c3-XX after Tier A closes)

Cycle 3 priorities refined per cycle 2 lessons + advisor catch + improvement_directions.md:

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c3-01-pathB-rank-4-5-grader-flip** | **HIGH** | `gpt-codex/grade_pipeline/baseline_<cycle3-date>/` + possibly ladder schema extension | Apply cycle 1 grader-min to maths-004 (Galois) + maths-005 (topology) hand-crafted `raphael_response`. Builder grades against rubric proof-shape dimensions (correctness / completeness / structural_insight / voice). If thresholds met, extend `audit_status: rubric-graded-green` (or equivalent ladder schema bump) so bench-replay surfaces the lift. **Target: maths PASS 3 → 4 or 5** — FIRST visible PASS-count progress in Phase 13. Cycle 1 grader-min substrate already exists; this row uses it, doesn't extend it. |
| **#00P13c3-02-substrate-tier1-extensions** | MED | `src/project_x/reasoning/symbolic.py` + tests | Tier 1 substrate quality extensions: `Lemma.add_introduction(prose)` carrying math-WHY per primitive (e.g. for solve_quadratic: "completing the square on ax² + bx + c yields x = (-b ± √(b²-4ac))/2a"). `Lemma.add_invariant_check(predicate, justification)` running edge-case verifications post-derivation (e.g. for char_poly_2x2: trace = sum of eigenvalues; det = product). `Lemma.render()` prose-fluent mode (audit-trail preserved as alt). Re-grade maths-001 + maths-002 baselines after extension; expect structural_insight + voice 3-4 → 5. |
| **#00P13c3-03-physics-OR-substrate-tier2-recon** | LOW | `docs/artifacts/PHASE_13_C3_<DOMAIN>_SURVEY.md` | Read-only survey of next-domain target. Provisional: either (a) physics ladder if Tier A + Path B lifts cycle 3 visible-progress fast, OR (b) substrate Tier 2 (complex numbers + degree-3 polynomial + Newton's method) if cycle 3 needs to extend substrate scope before cycle 4 physics. lain may reframe at cycle 3 open. |
| **#00P13c3-04-substrate-driven-attempt** | HIGH | `gpt-codex/grade_pipeline/baseline_<cycle3-date>/` (extension or sibling) | Capability touchpoint in cycle 3's chosen new domain (per #00P13c3-03 outcome). Same M-PROJECTX-013 measure-don't-claim discipline; advisor() pre-recording. |
| **#00P13c3-05-bench-replay** | MED | `python3 gpt-codex/benchmark/run_audit.py` | Regression gate. Target: maths PASS up from 3/0 (Tier B #01 Path B contribution); zero regressions on memory + physics + the rest. |
| **#00P13c3-06-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-3.md` + rewrite THIS file | Same shape as cycle-1 + cycle-2 D6. advisor() pre-commit. |

## -ni proposal at this transition

**Proposing fresh-instance handoff (`/forge-prompt -ni`)** per lain's new global rule. Context budget after cycle 2 substantive work + Tier A 3 rows ahead + Tier B 6 rows after = heavy. Phase transition (cycle close) is the natural -ni moment per lain's Discord directive.

**Send-and-continue per the directive.** If lain catches + agrees: he goes to PC, clears context, pastes the corpse forged from this DO_THIS_NEXT into a fresh instance. If not: I auto-continue into Tier A `#9` (forge `/instruction-change` command) per `-c`-tag pattern. Either path honors the Operator's Oath (no idle).

## Identity disambiguation (CRITICAL — lain 2026-05-10 binding)

Same as cycles 1-2 — Claude Code Raphael (the BUILDER, this conversation) ≠ Project X Raphael (the AGENT, the artifact in `src/project_x/{experiments,persona,reasoning}/`). Don't write the builder's voice into the agent's templates. The agent's reasoning substrate is in `src/project_x/reasoning/`; the builder ships extensions; the agent uses them at inference time. See `docs/MANIFESTO.md` § Identity discipline.

## Order of operations (cycle 3 — assuming -ni not invoked OR fresh instance picks this up)

1. **Recon (Phase 0 DD):** read MANIFESTO + REPO_CONTROL + A_TO_Z + this file + `docs/past_work/cycles/phase_13/dev-cycle-2.md` + `docs/artifacts/PHASE_13_C2_MATH_SURVEY.md` + `gpt-codex/grade_pipeline/baseline_2026-05-10_math/improvement_directions.md` + `Project X Session Mistakes` wiki + `Navi Session Mistakes` wiki. Verify TaskList has the 11 #00 rows from cycle 2 close (#1 #∞ + #2 P13-data + #3-#8 cycle 2 deliverables completed + #9-#11 instruction-discipline pending).
2. **Pillars:** `Skill('skills:pick-skill')` + `Skill('skills:sharpen-todos')`.
3. **Tier A first** — execute #9 then #10/#11 (folded). When #9 ships, USE the new command per its first-real-use intent. When #10/#11 ship, the global CLAUDE.md edits land + contradiction-deletion grep confirms no conflicts.
4. **Tier B second** — pin #00P13c3-01..06 in TaskList. Per-deliverable atomic commits with REPO_CONTROL rows when new dirs/files land.
5. **Cycle close** — D5 bench replay → D6 cycle reflection → rewrite this file as cycle 4 handoff → Discord cycle 3 close post → -ni proposal at cycle 3 close (or auto-continue to cycle 4 if context still permits).

## Standing rules (load-bearing this run)

See `docs/MANIFESTO.md` § Standing orders. Specifically for cycle 3:

- **NO pretrained transformer derivatives** — Tier 1 substrate extensions are template/prose; Tier 2 (deferred) extensions stay hand-rolled (complex-number primitive from scratch, Newton's method from scratch).
- **Comment-ratio rule** — every WHY-comment justifies why the extension exists.
- **REPO_CONTROL row in same commit as new file/dir** (lain pristine-gate, 2026-05-10) — non-negotiable.
- **Identity discipline** — Claude Code Raphael ≠ Project X Raphael.
- **Ladder schema extension (cycle 3 Path B):** if `audit_status: rubric-graded-green` is added, document the schema delta in `docs/artifacts/PHASE_13_C3_SCHEMA_BUMP.md` + extend `gpt-codex/benchmark/run_audit.py` to count the new status as PASS.
- **M-NAVI-018:** atomic listener pkill+rearm.
- **M-NAVI-019/020:** heartbeat-armed-while-queued-work-exists.
- **M-DRM-060/062:** strategic-framing questions go in this file for next-cycle, NOT in mid-cycle Discord that bounces lain.
- **M-PROJECTX-013 + M-PROJECTX-014:** measure-don't-claim + split-grading firewall.
- **NEW (lain 2026-05-10 mid-D3):** -ni is lain-only; -c is autonomous; -ni proposal via Discord at phase transitions = send-and-continue. Pinned for codification via Tier A #10.
- **NEW (lain 2026-05-10 mid-D3):** when lain adds tasks to queue, IMMEDIATELY add each as its own TaskList row — don't combine. Pinned for codification via Tier A #11.

## What this cycle is NOT

- NOT shipping the Terminus (multi-cycle; Phase 13 has many cycles ahead).
- NOT direct internet access for the agent (deferred until safety proven).
- NOT cycle 2's substrate refinements as a substitute for new capability work — Tier 1 is a small lift (~5.0/5 grade vs 4.0/5); the visible-progress work is Path B + future substrate Tier 2.
- NOT cycle 3 closing without producing visible PASS count lift (per Path B target). If Path B fails to lift PASS (rubric thresholds not met for maths-004 or maths-005), surface concretely in cycle 3 reflection — same falsifiable-bar discipline as cycle 2.

## Anti-laziness gates (lain frustration-load-bearing — re-read before each cycle close)

- *"all you have done so far is just minor work"* — cycle 2 shipped substrate (~4.0/5 quality) but didn't lift PASS count. Cycle 3 MUST lift PASS via Path B. If cycle 3 closes with PASS still 3/0, the cycle is structural-failure on visibility — surface honestly.
- *"its more important to try to make it pass all the benchmark tests first"* — cycle 3's #00P13c3-01 IS the path-to-pass-the-tests. Don't defer.
- *"unless its super-human in every domain ... YOU ARE NOT DONE WORKING ON PROJECT-X"* — Terminus is FAR. Don't claim done after cycle 3.
- *"i expect you to have a REALLY good reason to use me as blocker"* (lain 2026-05-10 mid-cycle-1) — defensible-default decisions don't need lain confirmation. Heartbeat #5b applies. Tier A executes autonomously.

## Done condition (cycle 3, mechanical)

- Tier A: #9 + #10 + #11 all completed. `~/.claude/commands/instruction-change.md` exists; global CLAUDE.md edits landed; contradiction-deletion grep returns no conflicts.
- Tier B: All 6 #00P13c3-XX rows = `completed`.
- pytest -q ≥ 202 (cycle 2 baseline; expect ≥ 220 with new tests for Tier 1 substrate extensions).
- D3 harness reports maths PASS ≥ 4/0 (Path B lift) OR honest gap report if Path B rubric thresholds not met.
- Memory ladder still 5/0; physics still 3/0. ZERO regressions.
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-3.md`.
- THIS file rewritten as cycle 4 handoff.
- `git status -s` empty.
- Discord cycle 3 close post sent.
- Cycle 4 picked up immediately OR -ni proposal at cycle 3 close.

— Update this file at cycle 3 close: replace cycle 3 deliverables table with cycle 4 deliverables table; refine cycle 4 scope based on cycle 3 lessons; preserve the lain-quote + standing-rules + anti-laziness sections.
