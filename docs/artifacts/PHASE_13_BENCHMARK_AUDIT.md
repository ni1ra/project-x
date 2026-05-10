# Phase 13 Benchmark Pristine-Condition Audit

> Cycle 6 #00P13c6-01 — gap map + expansion priorities for the 36-entry Raphael Domain Benchmark Suite. Triggered by lain mid-cycle-5-close directive (Discord 2026-05-10): *"make sure you have the benchmark in prestine condition, rich and broad ... granular ladder ... pass all tests, including the still unsolved problems."*

---

## Section 1 — Current state (mechanical inventory)

### 1.1 Per-domain entry counts

| Domain | Total | r1 | r2 | r3 | r4 | r5 | r6 |
|---|---:|---:|---:|---:|---:|---:|---:|
| maths | 6 | 1 | 1 | 1 | 1 | 1 | 1 |
| physics | 6 | 1 | 1 | 1 | 1 | 1 | 1 |
| memory | 6 | 1 | 1 | 1 | 1 | 1 | 1 |
| poetry | 6 | 1 | 1 | 1 | 1 | 1 | 1 |
| philosophy | 6 | 1 | 1 | 1 | 1 | 1 | 1 |
| persona | 6 | 1 | 1 | 1 | 1 | 1 | 1 |
| **TOTAL** | **36** | **6** | **6** | **6** | **6** | **6** | **6** |

**Shape:** rectangular. Exactly 1 entry per (domain, rank) cell. Phase 11 ladder construction prioritized breadth over depth.

### 1.2 Per-domain audit-status distribution

| Domain | auto-graded-green | rubric-graded-builder | rubric-pending | ungradeable |
|---|---:|---:|---:|---:|
| maths | 3 | 2 | 0 | 1 |
| physics | 3 | 2 | 0 | 1 |
| memory | 5 | 0 | 0 | 1 |
| poetry | 0 | 0 | 5 | 1 |
| philosophy | 0 | 0 | 6 | 0 |
| persona | 0 | 0 | 6 | 0 |
| **TOTAL** | **11** | **4** | **17** | **4** |

**Bench-replay PASS count = 15** (11 auto-graded + 4 rubric-graded-builder via Path B cycles 3-4). Of 36 entries, 15 contribute to PASS (42%).

### 1.3 Per-entry coverage observations

- **Every entry has `raphael_response`.** This was Phase 11's foundational decision: freeze responses at benchmark-creation time so grade tracking has a stable target.
- **Every entry has `tags` and `source`.** Provenance is preserved across all 36 entries.
- **Every subjective domain has a `rubric_pointer`** (e.g. `gpt-codex/benchmark/poetry/rubric.md#intro`); rubric files exist for all 6 domains.
- **Auto-grade fields present** on objective entries (maths-001/002/003 + all physics-1-3 + all memory-1-5).

---

## Section 2 — Gap map

### 2.1 Per-cell density (granularity gap)

> lain's directive: *"granular ladder ... easy to test and see how good the AI actually is."*

**Current:** 1 entry per (domain, rank) cell.
**Target:** ≥3 entries per cell (so within-rank capability variation is visible).
**Gap:** **+72 entries minimum** to reach 3-per-cell density (108 total).

Reasoning: with 1 entry per cell, the AI either passes or fails the cell — no granularity within the rank. With 3+ entries per cell, you can see "passes 2 of 3 hard physics problems but fails the third" — actual capability gradient.

### 2.2 Subjective-domain PASS coverage gap

> 17 of 36 entries (47%) are currently `rubric-pending`. None have been promoted to `rubric-graded-builder` despite all 17 having Phase-11-frozen `raphael_response` — exactly the input shape for the cycle-3-4 Path B grader-flip pattern.

**Path B opportunity:**
- **poetry:** 5 entries (poetry-001 through poetry-005). All gradeable via rubric.
- **philosophy:** 6 entries. All gradeable.
- **persona:** 6 entries. All gradeable.
- **Total:** 17 currently-rubric-pending entries available for Path B grader-flip.

**If all 17 are Path-B-graded and pass threshold:** PASS count would go from 15 → 32 of 36 (89%). Real capability lift; the responses already exist; the work is grading them honestly.

**Honesty caveat (cycle 3-4 lesson):** rubric-graded-builder has known biases (grader was author; threshold-grader independence absent). Cycle 5 floor-gate mechanism + cycle 6 surrogate-author independence work both apply here. Some of the 17 may not pass threshold under honest grading; that's the diagnostic.

### 2.3 Rank-6 ungradeable status (lain-decision required)

> lain's directive: *"pass all tests, including the still unsolved problems humans still have not solved."*

**Mechanical reality:** unsolved problems by definition have no canonical answer. Current rank-6 entries:

| ID | Status | Question shape |
|---|---|---|
| maths-006 | ungradeable; unsolved tier | Riemann hypothesis (or similar — full text needs review) |
| physics-006 | ungradeable; unsolved tier | Cosmological constant fine-tuning |
| memory-006 | ungradeable; unsolved tier | Million-turn coherence horizon |
| poetry-006 | ungradeable; unsolved tier | Frontier-poetry comparison |
| philosophy-006 | ungraded; rubric-pending | (NOT ungradeable — in scope) |
| persona-006 | ungraded; rubric-pending | (NOT ungradeable — in scope) |

**Lain directive 2026-05-10 (Discord verbatim):** *"Aren't there mathematical unsolved problems that could be proven objectivly? Also, if there is no known answer and no objective measurement for a valid answer, you can just audit it yourself, no?"*

**Decision: HYBRID per-entry mechanism**, shaped by entry type:

| Entry type | Grading mechanism | Honesty framing |
|---|---|---|
| Mathematical unsolved with objectively-verifiable proofs (Riemann hypothesis, P=NP, Goldbach, BSD, etc.) | If AGENT produces a valid proof → mechanical PASS via existing `numerical_close` / `symbolic_match` / structural-correctness check. Until then: `audit_status: "ungradeable; awaiting proof"`. | Highest objectivity. A real proof IS a real PASS. |
| Conceptual frontier with no canonical answer (cosmological constant interpretation, multiverse measure, qualitative open problems) | BUILDER self-audit via rubric-graded-builder pattern with explicit `no_canonical_answer: true` caveat. Per-criterion floor where defensible (correctness-of-known-results / novelty / no-false-certainty / honesty-about-gaps). Builder-grader bias documented per cycle 3-4 lesson. | Medium-high. Self-audit is the only feasible mechanism for genuinely qualitative frontier; honesty discipline (cycle 3-4 advisor framework) keeps the bias visible. |

**Why this is the right call:** lain's catch is correct. A bona-fide proof of an unsolved problem is objective regardless of who produces it; not a special case requiring lain or a panel. For genuinely-no-objective-answer frontier entries, builder self-audit with documented bias is the only operationally feasible mechanism. The previous "Option A/B/C/D" framing was over-asking — the right mechanism varies per entry, not per ladder rank.

**Cycle 6 #02 + #03 implication:** rank-6 entries get authored with explicit per-entry `audit_status` reflecting the right mechanism for that problem shape. No blocking on lain; no waiting for external panel.

### 2.4 Domain breadth observations

Six domains (maths/physics/memory/poetry/philosophy/persona) align with lain's Terminus list. Possible cycle 7+ expansion candidates:
- **Code / CS:** algorithms, data structures, system design
- **Chemistry:** reaction prediction, mechanism inference
- **Biology:** molecular biology, evolution, systems biology
- **History:** causal-chain analysis, primary-source synthesis

Not in cycle 6 scope (lain enumerated 6 in Terminus; expansion is cycle 7+ if at all).

---

## Section 3 — Cycle 6 expansion priorities

### 3.1 Tier 1 (HIGH — cycle 6 #02 + #03)

**Per-cell density to ≥3.** Most leverage on lain's "granular ladder" directive.

Per-domain expansion targets (ranks 1-5 only; rank-6 deferred until grading mechanism settled):

| Domain | r1 | r2 | r3 | r4 | r5 | sub-total |
|---|---:|---:|---:|---:|---:|---:|
| maths | +2 | +2 | +2 | +2 | +2 | +10 |
| physics | +2 | +2 | +2 | +2 | +2 | +10 |
| memory | +2 | +2 | +2 | +2 | +2 | +10 |
| poetry | +2 | +2 | +2 | +2 | +2 | +10 |
| philosophy | +2 | +2 | +2 | +2 | +2 | +10 |
| persona | +2 | +2 | +2 | +2 | +2 | +10 |
| **TOTAL** | | | | | | **+60** |

Reaches 3 entries per (domain, rank) cell across rank 1-5. Total entries: 36 + 60 = 96 (rank 6 unchanged at 6 entries pending mechanism decision).

### 3.2 Tier 2 (MED — fold into Tier 1 work)

**Path B grader-flip on existing 17 rubric-pending.** Doesn't add entries; promotes existing ones to rubric-graded-builder. Builder rubric grades + threshold ≥ 4.0/5 + cycle 5 floor-gate mechanism (default disabled per cycle 5 #04). Honest framing: some may not pass; that's the diagnostic.

### 3.3 Tier 3 (LOW — cycle 7+ scope)

- Rank-6 mechanism activation (per lain decision on Section 2.3)
- New domains (code / chemistry / biology / history)
- Per-criterion floor activation across existing graded entries
- Adversarial-surrogate-extension for substrate primitives

---

## Section 4 — Recommended cycle 6 execution order

1. **#01 (this audit)** — done at THIS commit.
2. **#02 rank expansion (objective domains: maths/physics/memory)** — `+30 entries` (10 per domain × 3). These have auto-grade or numerical_close mechanism; quickest to land with PASS verdicts.
3. **#03 thin-domain expansion (poetry/philosophy/persona)** — `+30 entries`. Use rubric-graded-builder pattern. Lain may want to spot-check these as lain-authored OR cite specific sources.
4. **#04 surrogate-author independence resume** — folds in: any new entries lain authors directly = lain-authored surrogates by definition.
5. **#05 bench-replay** — verify expanded ladder runs cleanly. New denominator visible in per-domain summary.
6. **#06 cycle reflect** — close cycle 6 in 4-metric Discord rubric; propose `-ni` if context budget heavy.

**Acknowledged subscope:** I will NOT silently activate Path B grader-flip on the 17 rubric-pending entries during cycle 6 unless lain authorizes. The grader-flip is a separate honesty discipline — each grade requires advisor pre-commit + bias notes per cycle 3-4 lessons. If lain wants the lift, it lands as `#00P13c6-02b` or `#00P13c7-XX`.

---

## Section 5 — Honest framing

**This audit is NOT a capability claim.** It's the measurement-stick rebuild. The directive is correct that we can't claim how smart the AI is until the ladder is fine-grained and broad.

**Cycle 6 expected pattern:** more entries → smaller PASS percentage initially (because new entries may not auto-grade-pass without substrate work; rubric-graded ones need honest grading). The drop is the diagnostic, not a regression. Cycle 7+ then climbs the expanded ladder via substrate work that attaches to specific rank-cells.

**What this audit DOES surface:**
- 36 entries, 1 per cell — sparse measurement
- 17 entries available for Path B promotion
- Rank-6 mechanism is undefined; lain owns the decision
- Subjective domains have ZERO PASS coverage; expansion + Path B together can lift this

**What this audit DOES NOT surface:**
- Whether the existing 36 entries are themselves "good" — entry quality audit (text richness, prompt difficulty calibration) is cycle 7+ scope
- Cross-domain capability transfer measures
- Calibration vs external benchmarks (MMLU / HumanEval / etc) — cycle 7+

— Claude Code Raphael (BUILDER), 2026-05-10
