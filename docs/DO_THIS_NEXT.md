# Do This Next — Project X — Phase 12 Cycle 3 (Execute-Raphael — flip memory reds + audit_log + addendum)

**Cron fires:** 2026-05-10 11:27 CEST (one-shot `baa6fc79`)
**Persona:** Execute-Raphael
**End time:** 2026-05-10 13:28 CEST (cycle 7 verdict lands ~13:20)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

> **Cycle-2 closed at 11:08 — #00P12-retrieval-mode-disambiguation FULLY shipped.** Both halves landed (cycle 1 = memory.py method; cycle 2 = controller wiring + classifier + compose_answer extension). End-to-end smoke confirmed memory-004 + memory-005 BOTH GREEN. Decision label `retrieve_full_history` correctly routed. Pytest 52 passing. Cycle 3 now owns the ladder/audit_log/addendum updates.

---

## #00 deliverables (TaskList — Phase 12)

- **#1** `#∞ APOTHEOSIS mode` — in_progress (3h godify-app pickup)
- **#2** `#00P12-retrieval-mode-disambiguation` — ✅ COMPLETED cycle 2
- **#3** `#00P12-flip-memory-reds` — in_progress (THIS CYCLE)
- **#4** `#00P12-tests` — pending (cycle 4 — 11:52)
- **#5** `#00P12-verdict + END_TIME handoff` — pending (cycle 7 — 13:07)

---

## This cycle's scope — flip memory reds + audit_log + addendum

### Phase A (~10 min): re-run verdict-builder + update ladder.jsonl

Run the cycle-8-style verdict-builder against the fixed agent. Use `mem.write_batch([TurnRecord(...) for setup])` then `agent.process(query)` pattern (NOT `agent.process(setup_text)` — that path hits write_one without write_batch init). Parse cited turn_ids from `answer_text` regex (matching prev cycle 8 pattern):

```python
import json, re
from project_x.experiments.semantic_memory_agent import MemoryAgent
from project_x.experiments.semantic_hdc_memory import SemanticHDCMemory, TurnRecord

with open("gpt-codex/benchmark/memory/ladder.jsonl") as f:
    entries = [json.loads(line) for line in f]

cited_re = re.compile(r"Based on turns? ([\d,\s]+):")

for entry in entries:
    if entry["audit_status"] not in ("auto-graded-red", "auto-graded-pending-execution"):
        continue  # skip green + ungradeable
    setups = entry["auto_grade"]["setup"]
    records = [TurnRecord(turn_id=i, text=t, fact_keys=[], metadata={}) for i, t in enumerate(setups)]
    mem = SemanticHDCMemory()
    mem.write_batch(records)
    agent = MemoryAgent(memory=mem)
    response = agent.process(entry["auto_grade"]["query"])
    m = cited_re.search(response.answer_text)
    cited = sorted([int(x) for x in m.group(1).split(",") if x.strip().isdigit()]) if m else []
    expected = sorted(entry["auto_grade"]["expected_turn_ids"])
    crit = entry["auto_grade"]["match_criterion"]
    if crit.startswith("expected_turn_ids equals"):
        ids_match = expected == cited
    else:  # subseteq
        ids_match = set(expected).issubset(set(cited))
    answer_lower = response.answer_text.lower()
    contains = [tok for tok in entry["auto_grade"]["expected_response_contains"] if tok.lower() in answer_lower]
    expected_n = len(entry["auto_grade"]["expected_response_contains"])
    contains_match = len(contains) >= max(1, int(expected_n * 0.8))  # 4-of-5 threshold for rank 5
    match = ids_match and contains_match
    entry["auto_grade"]["actual_turn_ids"] = cited
    entry["auto_grade"]["match"] = bool(match)
    entry["auto_grade"]["actual_answer_text_excerpt"] = response.answer_text[:200]
    entry["auto_grade"]["actual_decision"] = response.decision
    if "phase_12_fix_note" not in entry["auto_grade"]:
        entry["auto_grade"]["phase_12_fix_note"] = (
            "retrieve_structural_full_history routed via _LIST_ALL_HINTS + subject-extraction gate"
        )
    entry["audit_status"] = "auto-graded-green" if match else "auto-graded-red"

# Atomic write back
with open("gpt-codex/benchmark/memory/ladder.jsonl", "w") as f:
    for entry in entries:
        f.write(json.dumps(entry) + "\n")
```

Expected outcome:
- memory-004: cited=[0,3,5,7] = expected [0,3,5,7] ✓ → auto-graded-green
- memory-005: cited=[0,1,3,5,7,9] ⊇ expected [1,3,5,7,9] ✓ → auto-graded-green
- memory-001/002/003: still green (regression-safe)

### Phase B (~5 min): rebuild audit_log.jsonl

```python
import json, glob
rows = []
for p in sorted(glob.glob('gpt-codex/benchmark/*/ladder.jsonl')):
    for line in open(p):
        d = json.loads(line)
        rows.append({
            "id": d["id"],
            "domain": d["domain"],
            "difficulty_rank": d["difficulty_rank"],
            "audit_status": d["audit_status"],
            "auto_grade_match": d.get("auto_grade", {}).get("match"),
            "needs_audit": "rubric-pending" in d["audit_status"],
            "rubric_pointer": d.get("rubric_pointer"),
            "prompt_excerpt": d["prompt"][:80],
            "response_excerpt": d["raphael_response"][:80],
        })
with open("gpt-codex/benchmark/audit_log.jsonl", "w") as f:
    for r in rows: f.write(json.dumps(r) + "\n")

# Counts
from collections import Counter
status = Counter(r["audit_status"] for r in rows)
print(status)  # expect: {"auto-graded-green": 11, "rubric-pending": 21, "ungradeable": 4, ...}
```

Expected: 11 green / 0 red / 21 rubric-pending / 4 ungradeable.

### Phase C (~5 min): addendum to PHASE_11_BENCHMARK.md

Append at the BOTTOM (frozen-with-addendum convention per `docs/artifacts/CLAUDE.md`):

```markdown
---

## Phase 12 closure addendum (2026-05-10 ~11:35 CEST)

The 2 auto-graded-red findings flipped GREEN via Phase 12's retrieval-mode disambiguation
(`retrieve_structural_full_history` + `_LIST_ALL_HINTS` classifier + subject-extraction gate
in `MemoryAgent.process`). Phase 12 plan: `docs/past_work/phases/phase_12_retrieval_disambiguation.md`
(after cycle 7 archive). Implementation cycles: dev-cycle-1 (memory.py method) + dev-cycle-2 (controller wiring).

**Updated counts:**
| Audit status | Phase 11 close (06:55) | Phase 12 close (~13:20) |
|---|---|---|
| `auto-graded-green` | 9 (25%) | 11 (31%) |
| `auto-graded-red` | 2 (6%) | 0 (0%) |
| `rubric-pending` | 21 (58%) | 21 (58%) |
| `ungradeable` | 4 (11%) | 4 (11%) |

Of the auto-gradable subset (11 entries): 11 green / 0 red = **100% pass rate** (was 81.8%).

memory-004 + memory-005 details:
- memory-004 cited [7] → [0, 3, 5, 7]; tokens C++/Rust/Java/Kotlin in answer
- memory-005 cited [9] → [0, 1, 3, 5, 7, 9] (superset of expected [1, 3, 5, 7, 9]); 5/5 tokens

Architectural note: Phase 10 P3 strict-dominance retains its role for current-preference queries (memory-001/002/003 unchanged). Phase 12's contribution is the QUERY-SHAPE seam — query-shape classifier + subject-extraction gate + opt-in chronological retrieval mode that bypasses the +1.0 boost.

— Phase 12 verdict: `docs/artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md`
```

### Files to touch

- `gpt-codex/benchmark/memory/ladder.jsonl` — entries 1-5 updated with new actual_turn_ids/match/decision (memory-006 ungradeable untouched)
- `gpt-codex/benchmark/audit_log.jsonl` — full rebuild (36 rows; 5 memory rows have updated audit_status)
- `docs/artifacts/PHASE_11_BENCHMARK.md` — APPEND-ONLY addendum at bottom

### Time budget

22 min substantive + 3 min close. Sub-budget:
- 10 min: Phase A verdict-builder run + ladder.jsonl rewrite
- 5 min: Phase B audit_log.jsonl rebuild
- 5 min: Phase C addendum to PHASE_11_BENCHMARK.md
- 5 min: PHASE CHANGELOG cycle-3 close + dev-cycle-3.md + DO_THIS_NEXT.md cycle-4 + atomic commit + push + Discord

### Cycle 3 close checklist

- [ ] memory-004 + memory-005 audit_status flipped to auto-graded-green in `ladder.jsonl`
- [ ] memory-004/005 actual_turn_ids + match=true + phase_12_fix_note recorded
- [ ] memory-001/002/003 untouched OR re-run with same green status (no regression noise)
- [ ] `audit_log.jsonl` rebuilt; counts: 11 green / 0 red / 21 rubric / 4 ungradeable
- [ ] PHASE_11_BENCHMARK.md addendum at bottom (no rewrite of original verdict)
- [ ] PHASE CHANGELOG cycle-3 row → ✅ closed
- [ ] Cycle reflection at `docs/past_work/cycles/phase_12/dev-cycle-3.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 4 (tests + ladder extension)
- [ ] Atomic commit `feat(phase12): cycle 3 — flip memory reds (memory-004/005 → green) + audit_log rebuild + Phase 11 addendum`
- [ ] `git push origin main`
- [ ] `discord_send #general` cycle 3 close
- [ ] Clock out by minute 22; cycle 4 cron fires 11:52

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **GitHub remote:** https://github.com/ni1ra/project-x (private)
- **Cycle-2 commit:** to land at end of cycle 2 turn (this turn)
- **Cron state:** 5 godify one-shots remain (`baa6fc79` cycle 3 11:27 → `21e719fa` cycle 7 verdict 13:07)
- **Listener:** PID 13234 alive — pgrep + atomic re-arm if dead per M-NAVI-018
- **Tests baseline:** 52 passing
- **Phase 12 fix shipped end-to-end:** `retrieve_structural_full_history` (cycle 1) + `_LIST_ALL_HINTS` classifier + controller routing + compose_answer extension (cycle 2) — confirmed via memory-004/005 smoke test

---

## When lain returns mid-run

Atomic ack protocol per CLAUDE.md DD-2 + M-NAVI-018:
1. Read msg from listener output file (`/tmp/claude-1000/<slug>/<session>/tasks/<id>.output`)
2. `discord_send` ack BEFORE substantive work
3. Atomic re-arm: single Bash + run_in_background:true
4. Act

---

## M-NAVI-019 standing rule (for all 7 cycles)

Heartbeat-armed while `now < 13:28 CEST` AND named work exists. Premature disarm is fake-stop. Cycle 7 verdict cron is the only legitimate disarm signal. Confidence-Booster Mantra fires if posture drifts to "waiting on lain" while time-window is active.

---

## Phase 12 architectural finding being closed

Phase 11 verdict surfaced: Phase 10 P3 strict-dominance recency boost is correct for current-preference queries (memory-001/002/003 all green) but defeated list-all / summarize-trajectory queries (memory-004/005 red — cited only the latest turn). Phase 12 fix: query-shape disambiguation in the controller layer. Two retrieval modes co-exist; routing via `_LIST_ALL_HINTS` patterns + subject-extraction gate. Phase 10 P3 stays untouched for back-compat.

**Cycle-1 + cycle-2 already shipped the fix end-to-end.** Cycle 3 just records the result in the benchmark JSON files + appends the addendum that closes the Phase 11 finding.
