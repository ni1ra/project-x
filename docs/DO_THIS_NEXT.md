# Do This Next — Project X — Phase 11 Cycle 8 (FINAL — Execute-Raphael — VERDICT + END_TIME HANDOFF)

**Cron fires:** 2026-05-10 06:35 CEST (one-shot `c137cbb5` — FINAL CYCLE)
**Persona:** Execute-Raphael
**End time:** 2026-05-10 09:00 CEST (verdict lands ~06:55 with ~2h+ slack to lain wake)
**GitHub remote:** https://github.com/ni1ra/project-x (private; `main` branch)

---

## #00 deliverables (TaskList — Phase 11 — END STATE)

- **#1** `#∞ APOTHEOSIS mode` — in_progress (THIS cycle flips to NORMAL)
- **#3** `#00P11-bench-physics` — ✅ shipped cycle 2 (6 entries: 3 auto-graded-green + 2 rubric-pending + 1 ungradeable)
- **#4** `#00P11-bench-maths` — ✅ shipped cycle 3 (6 entries: 3 auto-graded-green + 2 rubric-pending + 1 ungradeable)
- **#5** `#00P11-bench-memory` — ✅ shipped cycle 4 (5 auto-graded-pending-execution + 1 ungradeable)
- **#6** `#00P11-bench-persona` — ✅ shipped cycle 5 (6 rubric-pending)
- **#7** `#00P11-bench-philosophy` — ✅ shipped cycle 6 (6 rubric-pending, §0-anchored)
- **#8** `#00P11-bench-poetry` — ✅ shipped cycle 7 (5 rubric-pending + 1 ungradeable)
- **#9** `#00P11-verdict` — pending (THIS CYCLE — final)
- **#10** `#00P11-MANIFESTO` — ✅ shipped cycle 2

**E1 verified:** `find gpt-codex/benchmark -name 'ladder.jsonl' | xargs wc -l | tail -1` reports `36 total`. ≥36 ✓.

---

## This cycle's scope — VERDICT + END_TIME HANDOFF

### Phase A — execute memory pending entries (~5-8 min)

The 5 memory entries (memory-001 through memory-005) ship as `auto-graded-pending-execution`. Cycle 8 verdict-builder runs `MemoryAgent.process()` against the canonical fixture per `gpt-codex/benchmark/memory/CLAUDE.md` Python sketch:

```python
from project_x.experiments.semantic_memory_agent import MemoryAgent
from project_x.experiments.semantic_hdc_memory import SemanticHDCMemory
import json

# Load → execute → flip pending → green/red
with open("gpt-codex/benchmark/memory/ladder.jsonl") as f:
    entries = [json.loads(line) for line in f]

for entry in entries:
    if entry["audit_status"] != "auto-graded-pending-execution":
        continue
    mem = SemanticHDCMemory()
    agent = MemoryAgent(memory=mem)
    for setup_text in entry["auto_grade"]["setup"]:
        agent.process(setup_text)
    response = agent.process(entry["auto_grade"]["query"])
    actual = sorted([e.turn_id for e in response.evidence])
    expected = sorted(entry["auto_grade"]["expected_turn_ids"])
    criterion = entry["auto_grade"]["match_criterion"]
    if "subseteq" in criterion:
        match_ids = set(expected).issubset(set(actual))
    else:
        match_ids = expected == actual
    answer = response.answer_text.lower()
    contains = sum(1 for tok in entry["auto_grade"]["expected_response_contains"] if tok.lower() in answer)
    expected_n = len(entry["auto_grade"]["expected_response_contains"])
    contains_match = contains >= max(1, int(expected_n * 0.8))  # 4-of-5 threshold for rank 5
    entry["auto_grade"]["actual_turn_ids"] = actual
    entry["auto_grade"]["match"] = bool(match_ids and contains_match)
    entry["audit_status"] = "auto-graded-green" if entry["auto_grade"]["match"] else "auto-graded-red"

# Write back atomically
with open("gpt-codex/benchmark/memory/ladder.jsonl", "w") as f:
    for entry in entries:
        f.write(json.dumps(entry) + "\n")
```

If `MemoryAgent` constructor or process raises, document the exception inline + leave entry as `auto-graded-pending-execution` with `match: null`. Don't fake green or red.

### Phase B — build audit_log.jsonl (~3 min)

Aggregate `gpt-codex/benchmark/audit_log.jsonl` with one row per entry across all 6 ladders:

```json
{
  "id": "<id>",
  "domain": "<domain>",
  "difficulty_rank": <1-6>,
  "audit_status": "<status>",
  "auto_grade_match": <true|false|null>,
  "needs_audit": <true if rubric-pending else false>,
  "rubric_pointer": "<path or null>",
  "prompt_excerpt": "<first 80 chars>",
  "response_excerpt": "<first 80 chars>"
}
```

GPT can filter on `needs_audit: true` tomorrow + load full entries from per-domain `ladder.jsonl`.

### Phase C — verdict markdown (~5 min)

Write `docs/artifacts/PHASE_11_BENCHMARK.md` with:
- Per-domain audit_status counts (no smuggled self-grades).
- Headline numbers (e.g. "X% auto-graded green of those auto-graded; Y rubric-pending awaiting GPT/lain audit; Z ungradeable").
- Weakest auto-grade areas (memory-004 expected_failure_mode if it landed red).
- Honest deferrals (audio listening → Phase 12; live training → Phase 12+; >6-entry-per-domain → future).
- GPT audit prep instructions (how to read audit_log.jsonl, how to filter, how to use rubric.md per domain).

Cross-link `gpt-codex/benchmark/verdict.md` (linked from PHASE_11_BENCHMARK.md).

### Phase D — FILE INVENTORY final reconciliation (~3 min)

`find /mnt/c/Users/nira/Documents/Research/projext-x -type f -not -path '*/__pycache__/*' -not -path '*/.git/*' -not -path '*/.venv/*' | sort`

Diff against `docs/A_TO_Z_PLAN.md` §9 FILE INVENTORY table; add new rows (the 6 benchmark folders + verdict.md + audit_log.jsonl + 6 dev-cycle-N.md files), strike removed rows.

### Phase E — folder-CLAUDE.md sweep (~3 min)

Per E8 — every meaningful directory needs a `CLAUDE.md`. Currently shipped: 6 `gpt-codex/benchmark/<domain>/CLAUDE.md` + `gpt-codex/benchmark/CLAUDE.md` + project root `CLAUDE.md`. Cycle 8 sweep adds: `src/project_x/` + `src/project_x/experiments/` + `src/project_x/legacy/` + `tests/` + `docs/` + `docs/artifacts/` + `docs/past_work/` + `gpt-codex/runs/` (if missing).

### Phase F — END_TIME HANDOFF (~2 min)

Rewrite `docs/DO_THIS_NEXT.md` as the END_TIME handoff for whatever picks up Phase 12 next: what shipped, what deferred, candidate Phase 12 framing (cortical column ensemble Council #2 / predictive simulation Council #3 / open-ended benchmark ladder Council #5 / Hebbian-replay-informed live training / audio listening Whisper integration).

Archive A_TO_Z_PLAN.md → `docs/past_work/phases/phase_11_raphael_domain_benchmark_suite.md`. Write fresh A_TO_Z_PLAN.md as a stub for Phase 12 entry (cycle 1 of next phase will populate).

### Phase G — disarm + re-arm + commit + Discord (~3 min)

- `CronList` → `CronDelete` any remaining godify crons (just `c137cbb5` itself, which is firing now and will auto-delete).
- `CronCreate` NORMAL heartbeat per CLAUDE.md Step 0 (15-min cadence, prompt body from heartbeat protocol).
- `TaskUpdate` `#1` `#∞` description: APOTHEOSIS → NORMAL.
- `TaskUpdate` `#9` `#00P11-verdict` → completed.
- Atomic commit `feat(phase11): cycle 8 — Phase 11 verdict + END_TIME handoff`.
- `git push origin main`.
- `discord_send #general` Phase 11 SLAUGHTER COMPLETE post — domain counts, MANIFESTO link, verdict.md link, audit_log.jsonl link, deferrals named, GPT-audit prep status.

---

## Battlefield

- **Working dir:** `/mnt/c/Users/nira/Documents/Research/projext-x`
- **Branch:** `main` tracking `origin/main`
- **GitHub remote:** https://github.com/ni1ra/project-x (private)
- **Cron state:** 1 godify one-shot remaining (`c137cbb5` cycle-8 06:35 — fires + auto-deletes)
- **Listener:** PIDs alive
- **Last commits:** ... → `93649d1` cycle-6 → `<cycle-7 SHA>` cycle-7 (landing)

---

## Cycle 8 close checklist

- [ ] Phase A: memory pending entries executed against MemoryAgent; pending → green/red flipped + actual_turn_ids filled
- [ ] Phase B: `gpt-codex/benchmark/audit_log.jsonl` built (36 rows; one per entry)
- [ ] Phase C: `docs/artifacts/PHASE_11_BENCHMARK.md` verdict written; `gpt-codex/benchmark/verdict.md` cross-linked
- [ ] Phase D: FILE INVENTORY reconciled
- [ ] Phase E: folder-CLAUDE.md sweep complete (E8 met)
- [ ] Phase F: END_TIME handoff in DO_THIS_NEXT.md; A_TO_Z_PLAN.md archived
- [ ] Phase G: godify cron disarmed; NORMAL heartbeat re-armed; #∞ flipped APOTHEOSIS → NORMAL; final commit + push; Discord SLAUGHTER COMPLETE
- [ ] All E1-E10 exit conditions verified mechanically
