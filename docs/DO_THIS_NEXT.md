# Do This Next — Project X — Phase 12 Cycle 2 (Execute-Raphael — controller wiring + classifier)

**Cron fires:** 2026-05-10 11:02 CEST (one-shot `5ed226ac`)
**Persona:** Execute-Raphael
**End time:** 2026-05-10 13:28 CEST (cycle 7 verdict lands ~13:20)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

> **Cycle-1 absorbed cycle-2 scope.** `retrieve_structural_full_history` is already SHIPPED in `semantic_hdc_memory.py` (4 smoke tests pass; pytest 52 passing). Cycle 2 now owns what was originally cycle 3: controller routing + classifier + compose_answer extension in `semantic_memory_agent.py`.

---

## #00 deliverables (TaskList — Phase 12)

- **#1** `#∞ APOTHEOSIS mode` — in_progress (3h godify-app pickup, 7 cycles compressed)
- **#2** `#00P12-retrieval-mode-disambiguation` — in_progress (cycle-1 shipped half 1; THIS CYCLE ships half 2)
- **#3** `#00P12-flip-memory-reds` — pending (cycle 3 — 11:27, was cycle 4)
- **#4** `#00P12-tests` — pending (cycle 4 — 11:52, was cycle 5)
- **#5** `#00P12-verdict + END_TIME handoff` — pending (cycle 7 — 13:07)

---

## This cycle's scope — controller wiring + query-shape classifier

### Goal

In `src/project_x/experiments/semantic_memory_agent.py`:

1. **Add `_LIST_ALL_HINTS` tuple** at module-level (alongside `_QUESTION_HINTS` / `_ASSERT_HINTS`):
   ```python
   _LIST_ALL_HINTS = (
       "list all", "all of", "summarize", "trajectory",
       "history of", "all changes", "in chronological order",
       "in order", "every change", "full history",
   )
   ```
   The patterns are conservative — must NOT match plain current-preference queries like "What does Alice prefer?" (which has no hint). Subject-extraction gate (in `process`) provides the second layer of safety.

2. **Add `_is_list_all_query(text: str) -> bool`** classifier:
   ```python
   def _is_list_all_query(text: str) -> bool:
       """Returns True if `text` shape suggests caller wants full chronological
       history rather than current state. False on any current-preference shape.
       Used by MemoryAgent.process to route between retrieve_structural (strict
       dominance, latest-wins) and retrieve_structural_full_history (chronological,
       all-turns)."""
       lower = text.lower()
       return any(hint in lower for hint in _LIST_ALL_HINTS)
   ```

3. **Extend `MemoryAgent.process` question path** (currently line ~231):
   ```python
   # Phase 12 (#00P12-retrieval-mode-disambiguation): query-shape disambiguation
   # closes memory-004/005 reds. Phase 11 verdict surfaced that strict-dominance
   # collapses 'list all' / 'summarize' queries to top-1; route those to the
   # chronological full-history path instead. Subject-extraction gate guards
   # against false-positives — only route to full-history when the query
   # actually names a known subject.
   if _is_list_all_query(text) and self.memory._extract_query_subjects(text):
       top_k = self.memory.retrieve_structural_full_history(text, k=None)
       full_history_mode = True
   else:
       top_k = self.memory.retrieve_structural(text, k=self.k_retrieve)
       full_history_mode = False
   ```

4. **Extend `compose_answer`** to skip `cosine_threshold` filter when in full-history mode (or pass a sentinel; the cleanest API: add a `full_history: bool = False` kwarg):
   ```python
   def compose_answer(query, evidence, cosine_threshold=0.25, full_history=False):
       if not evidence:
           return ("No evidence found in conversation memory.", "absent", 0.0)
       if full_history:
           # Cite ALL evidence chronologically — caller wants the full chain,
           # not the threshold-filtered top picks. Phase 12 #00P12 enables
           # 'list all' / 'summarize' queries to surface the complete subject
           # history per the chronological retrieval path.
           parts = [f"'{e.text}'" for e in evidence]
           ids = [str(e.turn_id) for e in evidence]
           top_cos = max((e.cosine for e in evidence), default=0.0)
           return (
               f"Based on turns {', '.join(ids)}: {' AND '.join(parts)}",
               "retrieve_full_history",
               top_cos,
           )
       # ... existing threshold-gated logic unchanged
   ```

   Pass `full_history=full_history_mode` from `MemoryAgent.process` into `compose_answer`.

### Smoke tests inline this cycle

After wiring, run end-to-end against memory-004 + memory-005 fixtures to confirm `MemoryAgent.process` returns evidence with cited turn_ids matching expected. Use the verdict-builder shape but parse `response.evidence` (not regex on `answer_text`).

```python
from project_x.experiments.semantic_memory_agent import MemoryAgent
from project_x.experiments.semantic_hdc_memory import SemanticHDCMemory
import json

with open("gpt-codex/benchmark/memory/ladder.jsonl") as f:
    entries = [json.loads(line) for line in f]

for entry in entries:
    if entry["id"] not in ("memory-004", "memory-005"): continue
    mem = SemanticHDCMemory(); agent = MemoryAgent(memory=mem)
    for setup in entry["auto_grade"]["setup"]:
        agent.process(setup)
    response = agent.process(entry["auto_grade"]["query"])
    cited = sorted([e.turn_id for e in response.evidence])
    expected = sorted(entry["auto_grade"]["expected_turn_ids"])
    print(f"  {entry['id']}: cited={cited} expected={expected} match={set(expected).issubset(set(cited))}")
```

Expect:
- memory-004: cited=[0, 3, 5, 7], expected=[0, 3, 5, 7], match=True
- memory-005: cited⊇[1, 3, 5, 7, 9], match=True

(Cycle 3 will rebuild audit_log + flip ladder.jsonl status fields. Cycle 2 just confirms the wiring works.)

### Files to touch

- `src/project_x/experiments/semantic_memory_agent.py` — `_LIST_ALL_HINTS`, `_is_list_all_query`, `MemoryAgent.process` extension, `compose_answer` extension
- (cycle 3 will touch the benchmark JSON files)

### Comment-ratio rule (lain GLOBAL POLICY)

Every change has a WHY-comment pointing to Phase 11 verdict / memory-004/005 architectural finding. Pure signal — no narrating-the-obvious.

### Time budget

22 min substantive + 3 min close. Sub-budget:
- 8 min: write all 4 changes (`_LIST_ALL_HINTS`, classifier, `process` routing, `compose_answer` extension)
- 5 min: smoke test memory-004 + memory-005 inline → confirm cited turn_ids match expected
- 3 min: pytest -q regression (must still be 52 passing — no test changes yet)
- 6 min: PHASE CHANGELOG cycle-2 row, dev-cycle-2.md reflection, DO_THIS_NEXT.md cycle-3 rewrite, atomic commit + push, discord_send

### Cycle 2 close checklist

- [ ] `_LIST_ALL_HINTS` + `_is_list_all_query` added in `semantic_memory_agent.py`
- [ ] `MemoryAgent.process` routes between strict-dominance and full-history
- [ ] `compose_answer` handles `full_history=True` chronologically
- [ ] Smoke tests confirm memory-004 cited=[0,3,5,7], memory-005 cited⊇[1,3,5,7,9]
- [ ] `pytest -q` still 52 passing
- [ ] PHASE CHANGELOG cycle-2 row → ✅ closed
- [ ] Cycle reflection at `docs/past_work/cycles/phase_12/dev-cycle-2.md`
- [ ] DO_THIS_NEXT.md rewritten for cycle 3 (flip reds + audit_log + addendum)
- [ ] Atomic commit `feat(phase12): cycle 2 — controller wiring + _LIST_ALL_HINTS classifier`
- [ ] `git push origin main`
- [ ] `discord_send #general` cycle 2 close
- [ ] Clock out by minute 22; cycle 3 cron fires 11:27

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **GitHub remote:** https://github.com/ni1ra/project-x (private)
- **Last commit (cycle 1 close):** to land at end of THIS turn — cycle 1 ships A_TO_Z_PLAN.md + DO_THIS_NEXT.md + M-NAVI-019 + retrieve_structural_full_history + dev-cycle-1.md
- **Cron state:** 6 godify one-shots remain (`5ed226ac` → `21e719fa`)
- **Listener:** PID 12907 alive
- **Tests baseline:** 52 passing
- **Memory ladder reds:** memory-004 + memory-005 (will flip in cycle 3)

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

Phase 11 verdict surfaced: Phase 10 P3 strict-dominance recency boost is correct for current-preference queries (memory-001/002/003 all green) but defeats list-all / summarize-trajectory queries (memory-004/005 red — cited only the latest turn instead of the full chronological set). Phase 12 fix: query-shape disambiguation in the controller layer. Two retrieval modes co-exist; routing via `_LIST_ALL_HINTS` patterns + subject-extraction gate. Phase 10 P3 stays untouched for back-compat.

**Cycle-1 already shipped the new retrieval method** (`retrieve_structural_full_history` in `semantic_hdc_memory.py`); cycle 2 wires it into the controller.
