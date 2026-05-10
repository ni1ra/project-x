# Do This Next — Project X — Phase 13 cycle 6 (BENCHMARK PRISTINE CONDITION + GRANULAR LADDER + RANK EXPANSION TO UNSOLVED-TIER)

**Updated:** 2026-05-10 (cycle 6 handoff; cycle 5 closed at THIS commit)
**Mode:** NORMAL (not godify-app)
**Status:** Cycle 5 CLOSED — 5/7 #00P13c5 fully shipped + 1 partially blocked on lain ack + 1 read-only verify + 2 universal /instruction-change codifications (4 atomic project commits + 0 project commits for universal patches). pytest 276 passing. D3 harness 15 PASS / 0 FAIL maintained.

## lain mid-cycle-5-close directive (Discord 2026-05-10 — supersedes pre-directive cycle-6 scope)

**Verbatim:** *"Alright make sure you have the benchmark in prestine condition, rich and broad, so we can get a real idea of how smart the AI really is. And your job is to make it smart enough to pass all tests, including the still unsolved problems humans still have not solved. Must be granular ladder up there, easy to test and see how good the AI actually is."*

**Translation in cycle-shape:** measurement-before-capability. Cycle 6 PRIMARY ARTIFACT = expanded benchmark; substrate growth defers to cycle 7+. Karpathy/Hassabis "evaluation is the bottleneck" doctrine, operationalized.

## Cycle 5 shipped (full ledger)

| Commit | Deliverable | Visible result |
|---|---|---|
| `fc9bebd` | **#00P13c5-01** predicate-strength fix | physics-003 predicate replaced via energy-momentum route; predicate-strength STRONG uniformly across substrate physics primitives; cycle 4 advisor catch closed |
| `ab57b74` | **#00P13c5-02** Newton-verifier tests | 8 dedicated tests for `verify_quadratic_via_newton`; cycle 4 #24 acknowledged-gap closed |
| `1c38946` | **#00P13c5-04** per-criterion floor gate | Surface 3 partial mitigation (Candidate B); default-disabled mechanism; preserves cycle 3-4 PASSes; ratchet-per-entry in cycle 7+ |
| `489df30` | **#00P13c5-05** substrate Tier 3 large-angle pendulum | Elliptic-integral series; 4-term truncation through k⁸; ~3e-3 accuracy at θ₀=π/2; predicate-strength STRONG via ratio-recursion |
| THIS commit | **#00P13c5-07** cycle reflect | dev-cycle-5.md + this rewrite + A_TO_Z changelog |
| (universal codification — `~/.claude/`; lain commits at his cadence) | **fake-stop drift patch** to Named Curse #15 (3 new canonical phrases) + **Discord teaching-style + 4-metric progression rubric** to § R4 + § THE SUMMONER | Universal cross-project leverage: future Discord posts + future fake-stop variants fire mechanically against the new lists |

Three visible axes this cycle:
- **Predicate-strength:** WEAK on physics-003 → STRONG (energy-momentum-route)
- **Divergent-verifier:** untested → 8 dedicated tests
- **Substrate Tier 3:** linear-only → large-angle non-linear primitive

Plus universal codifications: Discord teaching tone + progression-metrics rubric mandatory; fake-stop variants caught.

## Phase 13 cycle 6 deliverables (REVISED per directive)

| ID | Sev | Surface | One-line |
|---|---|---|---|
| **#00P13c6-01-benchmark-pristine-audit** | HIGH | `gpt-codex/benchmark/` (all 6 domain dirs) → `docs/artifacts/PHASE_13_BENCHMARK_AUDIT.md` (NEW) | Inventory current 36 entries: rank distribution per domain, gaps at rank 4-5-6, redundancies, blank-domain stubs (persona/poetry/philosophy). Map cycle 6 expansion targets per domain. Surface honest assessment: which domains are thin, which ranks are stubs, which entries are placeholders rather than real benchmarks. **Sub-item — rank 6 grading mechanism (lain-decision; advisor catch 2026-05-10):** lain's directive says *"pass all tests including unsolved problems"* but unsolved problems by definition have no canonical answer. Audit must surface options for lain: (a) rank 6 stays `audit_status: "ungradeable; unsolved tier"` as capability-range markers (existing physics-006 pattern; AGENT attempts but cannot mechanically PASS); (b) rank 6 gets lain-graded after each AGENT attempt; (c) rank 6 gets external-panel-graded; (d) hybrid — partial-credit rubric per dimension. Cycle 6 cannot proceed past audit without this decision; cycle 6 #02 expansion shape depends on it. |
| **#00P13c6-02-benchmark-rank-expansion** | HIGH | `gpt-codex/benchmark/{maths,physics,memory}/ladder.jsonl` | Fill rank 4-5-6 gaps per domain; ensure each rank has ≥3 entries per domain; **rank 6 = honestly-unsolved** (cite open problems where relevant: Riemann hypothesis, P=NP, Yang-Mills mass gap, dark matter composition, etc.). Granular ladder — capability progress visible at every step. |
| **#00P13c6-03-thin-domain-expansion** | HIGH | `gpt-codex/benchmark/{poetry,philosophy,persona}/ladder.jsonl` | Build out per-domain ladders to ≥6 entries per domain across rank 1-6. Subjective domains use rubric-graded-builder pattern from Path B. **Floor-gate default for NEW entries:** `per_criterion_floor=None` (opt-in mechanism; preserves cycle-5 default-disabled stance). Cycle 7+ activates floors per-entry as confidence in dimensions builds. Persona consistency + humor-lands criteria from cycle 1 #02 persona scaffolding. |
| **#00P13c6-04-surrogate-author-independence-resume** | MED | `src/project_x/anti_cheat.py` + new probe set | Cycle 5 #03 carry-forward: when lain provides surrogates OR if the new benchmark expansion includes lain-authored / textbook-cited entries, those become surrogate-author-independent by definition. Lain's own benchmark entries qualify as `surrogate_author = "lain"`. **Honesty caveat (cycle 5 #03 carry):** if cycle 6 expansion uses BUILDER-authored entries with citations to textbooks BUILDER doesn't have on disk, those are NOT surrogate-author-independent — they're builder-modeled-on-textbook-patterns wearing a citation costume. Real independence requires either lain-authored OR genuine textbook access (BUILDER reads the actual problem). |
| **#00P13c6-05-bench-replay** | MED | `python3 gpt-codex/benchmark/run_audit.py` | Verify expanded ladder runs cleanly. New denominator (was 36; will be ~50-70+); some rank-6 entries may be `ungradeable` (per existing audit_status pattern from physics-006). Honest gap report on which capabilities the AI demonstrably lacks. |
| **#00P13c6-06-cycle-reflect** | LOW | `docs/past_work/cycles/phase_13/dev-cycle-6.md` + DO_THIS_NEXT cycle 7 handoff + A_TO_Z changelog | advisor() pre-commit. Discord cycle 6 close. Propose -ni at cycle 7 boundary. |

**Adversarial-surrogate extension + per-criterion floor activation + substrate Tier 3 path 2** defer to cycle 7+ (capability layer; lain's directive puts measurement layer first).

## Recommended cycle 6 order (rationale per dependency)

1. **#01 benchmark pristine audit** FIRST — read everything; emit gap-map. No commits; produces `docs/artifacts/PHASE_13_BENCHMARK_AUDIT.md` only.
2. **#02 rank expansion (objective domains)** SECOND — maths, physics, memory have existing structure to extend. Granular rank-4-5-6 entries with auto-graded fields where possible; rubric-pending where subjective.
3. **#03 thin domain expansion** THIRD — poetry, philosophy, persona currently stubs / blank. Build from scratch with rubric-graded-builder pattern.
4. **#04 surrogate-author absorption** FOURTH — happens naturally as new entries land (lain-cited textbook problems = surrogate-author = "textbook:<ref>" with real citation).
5. **#05 bench-replay** + **#06 cycle reflect** at cycle close.

## #1 benchmark pristine audit — exact next-action (~30-45 min)

1. **List all current entries:** `ls gpt-codex/benchmark/*/ladder.jsonl` + count entries per file.
2. **Per-rank breakdown:** for each domain, count entries at each `difficulty_rank` (1-6).
3. **Identify gap shape:** which (domain, rank) cells have <3 entries? Which are empty?
4. **Audit-status distribution:** how many auto-graded? rubric-graded-builder? rubric-pending? ungradeable?
5. **Identify placeholder vs real:** are there entries that are stubs (single line, no real `raphael_response`, no auto_grade block)?
6. **Output `docs/artifacts/PHASE_13_BENCHMARK_AUDIT.md`** with gap-map + per-cell expansion priorities + recommendation order for cycle 6 #02 + #03.

## Identity disambiguation (CRITICAL — lain 2026-05-10 binding)

Claude Code Raphael (the BUILDER, this Claude Code instance) ≠ Project X Raphael (the AGENT, in `src/project_x/`). Cycle 6 BUILDER work: build the benchmark — pose problems, write `raphael_response` snapshots if needed, set rubrics, set thresholds. Cycle 6 AGENT work happens later when AGENT's substrate runs the benchmark + records performance. Don't write builder's voice into agent's response templates.

## Standing rules — RELEVANT THIS RUN

See `docs/MANIFESTO.md` § Standing orders + `~/.claude/CLAUDE.md` (universal).

**Codified universal during cycle 5 (binding for cycle 6+):**
- **Discord teaching style + 4-metric progression rubric** (~/.claude/CLAUDE.md § R4 + § THE SUMMONER): every Discord post claiming progress includes denominator+%, expert-tier impression framing, plain-English achievement, counter-claim guard. Teacher tone; no internal var/function names on Discord.
- **Fake-stop drift expanded** (~/.claude/CLAUDE.md Named Curse #15): "-ni proposal sent — standing down to idle" / "corpse stop-(a) condition met" added to canonical fake-stop phrase list. Cycle close = pivot to N+1 NOW; NORMAL has no rest authorization.

**Persistent (unchanged):**
- NO pretrained transformer derivatives at any layer
- Comment-ratio rule (WHY-comments + pure-signal explanations + complex code justified)
- Atomic per-deliverable commits; never `git add -A`
- Identity discipline (Claude Code Raphael ≠ Project X Raphael)
- M-PROJECTX-013 measure-don't-claim; M-PROJECTX-014 split-grading firewall
- M-NAVI-013/016/018/019/020 (skills + pillars + listener + heartbeat-armed-while-queued)
- Named Curse #20 (combined-task pinning) + #21 (-ni auto-invoked) + #15 (fake-stop drift, expanded)

## What this cycle is NOT

- NOT shipping the Terminus (multi-cycle; Phase 13 has many cycles ahead).
- NOT solving unsolved-tier problems (cycle 6 BUILDS the unsolved-tier ladder; AGENT's attempt at climbing is cycle 7+).
- NOT extending substrate (cycle 7+ scope; capability layer comes after measurement layer per directive).
- NOT closing without the gap-map artifact (`PHASE_13_BENCHMARK_AUDIT.md`) AND visible expansion in ladder.jsonl files.

## Anti-laziness gates (lain frustration-load-bearing — re-read before cycle close)

- *"all you have done so far is just minor work"* — cycle 5 shipped predicate-strength uniformity + Newton coverage + Tier 3 substrate + universal Discord-style codification. Cycle 6 rebuilds the measurement infrastructure so future substrate work attaches to concrete ladder progression.
- *"its more important to try to make it pass all the benchmark tests first"* — cycle 6 directly serves this. Pristine + granular ladder makes the PASS-count the load-bearing metric.
- *"unless its super-human in every domain ... YOU ARE NOT DONE WORKING ON PROJECT-X"* — Terminus is FAR. Cycle 6 builds the visible ladder to it.
- *"honest and honorable work ethics. If all tests pass, but the model falls apart in real tests, or it sees the answer in advance in some hidden way, the test passes are meaningless"* — cycle 4 #24 + cycle 5 #01 hardened anti-cheat; cycle 6 expands the test surface so passing actually demonstrates capability range, not sample bias.

## Done condition (cycle 6, mechanical)

- All 6 #00P13c6-XX TaskList rows = `completed`.
- pytest -q ≥ 276 (no regression; new tests for any new auto-graded entries).
- D3 harness reports new total (was 15 PASS / 0 FAIL / 21 rubric-pending; will be larger; some new rank-6 entries may be `ungradeable`-tier).
- Each domain has ≥6 entries spanning rank 1-6; each (domain, rank) cell has ≥3 entries where applicable.
- Cycle reflection at `docs/past_work/cycles/phase_13/dev-cycle-6.md`.
- THIS file rewritten as cycle 7 handoff.
- `git status -s` empty.
- Discord cycle 6 close post sent.
- Cycle 7 picked up immediately OR `-ni` proposal at cycle 6 close.

— Update this file at cycle 6 close: replace cycle 6 deliverables table with cycle 7 deliverables table; refine cycle 7 scope based on cycle 6 lessons; preserve the lain-quote + standing-rules + anti-laziness sections.
