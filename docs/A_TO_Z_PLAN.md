# A → Z Plan — Project X — Phase 11 — Raphael Domain Benchmark Suite

**Date opened:** 2026-05-10 03:32 CEST (godify-app APOTHEOSIS, 6h, 8 cycles)
**Previous phase archived:** `docs/past_work/phases/phase_10_memory_action_organism.md`
**Phase theme:** Raphael Domain Benchmark Suite — 6 domains × 6 entries each spanning easy→unsolved, with split grading (auto-graded mechanical vs rubric-pending subjective per M-PROJECTX-014).
**Run end:** 2026-05-10 09:00 CEST (END_TIME)
**Plan source:** `/home/nira/.claude/plans/6h-im-going-to-serene-giraffe.md` (lain + previous Plan-Raphael instance)
**Persona override:** ALL cycles Execute-Raphael (lain 2026-05-10 — pre-existing-plan rule; godify-app cycle-1=Plan-navi default OVERRIDDEN; see `~/.claude/commands/godify-app.md` §3.5 + `~/.claude/commands/forge-prompt.md` NI IDENTITY).

---

## §0. CONTRACT

### §0.1 #00 deliverables (verbatim from lain 2026-05-10 godify-app brief)

- **#00P11-bench-physics:** physics ladder (6 entries intro→unsolved; auto-grade closed-form, rubric-pending conceptual)
- **#00P11-bench-maths:** maths ladder (6 entries; auto-grade numerical/symbolic, rubric-pending proof-shape)
- **#00P11-bench-memory:** memory ladder (6 entries; ALL auto-graded via `agent.process` + expected_turn_id check)
- **#00P11-bench-persona:** persona ladder (6 entries; ALL rubric-pending — voice + humor + moral compass)
- **#00P11-bench-philosophy:** philosophy ladder (6 entries; ALL rubric-pending — anchored in §0 worldview manuscript)
- **#00P11-bench-poetry:** poetry ladder (6 entries; ALL rubric-pending)
- **#00P11-verdict:** aggregate verdict + audit_log.jsonl + `docs/artifacts/PHASE_11_BENCHMARK.md` + END_TIME handoff
- **#00P11-MANIFESTO:** `docs/MANIFESTO.md` ~300-500 words capturing lain's intent for Project X (heartbeat-tracked, dynamic doc per global standing-order 2026-05-10 03:10 CEST)

### §0.2 Simplicity standard

- **NO pretrained transformers** (Phase 9 standing constraint, lain 2026-05-09): no BGE, MiniLM, sentence-transformers, llama.cpp, Qwen, Mistral. Encoders + generators stay from-scratch organic.
- **Code-comment ratio rule** (lain 2026-05-10 03:34 + 03:44 CEST, Discord standing order): WHY-comments justifying complex code's existence + comments preserving important info. NEVER WHAT-comments narrating identifiers. Pure signal — no bloat. Project `<repo>/CLAUDE.md` carries the full rule.
- **Append-as-you-go writes** for crash survival (lain 2026-05-10 — 3 power outages in 2 days). No "write all at cycle close" anti-pattern.
- **Atomic per-cycle commits.** NO `git add -A`. Per-cycle PR shape (or per-cycle commit on `main` since this is a fresh repo).

### §0.3 Constraint defining this phase

- Lain asleep at session start (03:32 CEST); awake by ~09:00. Discord = audit channel; silence = pass per remove-from-loop policy (lain 2026-05-07).
- 6h godify-app run, 8 cycles × 40m (20 ON / 20 OFF). END_TIME 09:00 CEST.
- M-PROJECTX-014 (design-bias-in-the-probe) hard rule: NO self-grade on subjective domains. Subjective = rubric-pending for external GPT/lain audit tomorrow.
- Power-loss survival: per-entry append, per-cycle commit + push. GitHub remote setup in cycle 1.
- Listener manual re-arm only — auto-rearm broken in WSL bash sandbox (memory file `feedback_listener_manual_rearm.md` + M-NAVI-018 fresh from 03:32 CEST: pkill MUST chain rearm in same Bash invocation).

### §0.4 Phase exit conditions (mechanical proof at 09:00 CEST)

- [ ] **E1** `find gpt-codex/benchmark -name 'ladder.jsonl' | xargs cat | wc -l` ≥ 36
- [ ] **E2** Each `gpt-codex/benchmark/<domain>/ladder.jsonl` has 6 entries (one per difficulty rank 1-6) for all 6 domains
- [ ] **E3** Schema sanity — every entry has `id`, `domain`, `difficulty`, `prompt`, `raphael_response`, `audit_status`; auto-graded entries have `auto_grade` block; rubric-pending have `rubric_pointer`; **NO `self_score` field on any entry (M-PROJECTX-014 firewall)**
- [ ] **E4** `PYTHONPATH=src python3 -m pytest -q | tail -3` ≥ 52 passing (no regression from Phase 11 P2 baseline)
- [ ] **E5** `docs/MANIFESTO.md` exists and contains ≥ 250 words
- [ ] **E6** `docs/A_TO_Z_PLAN.md` §9 FILE INVENTORY lists every file in repo with rationale; cycle 8 reconciliation pass run
- [ ] **E7** `docs/artifacts/PHASE_11_BENCHMARK.md` verdict markdown exists with per-domain audit_status counts (no smuggled self-grades)
- [ ] **E8** Folder `CLAUDE.md` present in every meaningful directory: 6 `gpt-codex/benchmark/<domain>/` + `gpt-codex/benchmark/` root + `src/project_x/` + `src/project_x/experiments/` + `src/project_x/legacy/` + `tests/` + `docs/` + `docs/artifacts/` + `docs/past_work/` + `gpt-codex/runs/`
- [ ] **E9** `gpt-codex/benchmark/audit_log.jsonl` aggregate built; per-domain green/red/rubric-pending counts computed honestly
- [ ] **E10** `git log --oneline | wc -l` ≥ 8 (per-cycle atomic commits 1-8; crash-survival contract honored). `git remote get-url origin` returns the projext-x GitHub URL.

---

## §1. PHASE CHANGELOG

| Cycle | Persona | When (CEST) | Position | Status |
|---|---|---|---|---|
| C1 | Execute-Raphael (plan-setup; OVERRIDE Plan-navi default per pre-existing-plan rule) | 2026-05-10 03:32 | 1 of 8 | ✅ closed 04:01 — initial commit `5611c2b` force-pushed to https://github.com/ni1ra/project-x (hijacked from legacy WIRED-BRAIN per lain 03:55 + renamed to project-x per lain 03:56) |
| C2 | Execute-Raphael (physics + cycle-1.5 deliverables) | 2026-05-10 04:12 | 2 of 8 | ✅ closed 04:27 — physics ladder 6 entries (3 auto-graded-green + 2 rubric-pending + 1 ungradeable) schema-validated; MANIFESTO enriched to ~600 words; 6 rubric.md skeletons + benchmark/CLAUDE.md + physics/CLAUDE.md shipped |
| C3 | Execute-Raphael (maths) | 2026-05-10 04:52 | 3 of 8 | ✅ closed ~05:02 — maths ladder 6 entries (3 auto-graded-green: x={5,-1/3}, eigenvalues={1,3}, residue=π; 2 rubric-pending: Galois quintic + π₁/H₁ T² vs K; 1 ungradeable: Riemann hypothesis) |
| C4 | Execute-Raphael (memory) | 2026-05-10 05:15 | 4 of 8 | pending (cron `d21083dd` — COMPRESSED) |
| C5 | Execute-Raphael (persona) | 2026-05-10 05:35 | 5 of 8 | pending (cron `f554a09f` — COMPRESSED) |
| C6 | Execute-Raphael (philosophy) | 2026-05-10 05:55 | 6 of 8 | pending (cron `612a23d4` — COMPRESSED) |
| C7 | Execute-Raphael (poetry) | 2026-05-10 06:15 | 7 of 8 | pending (cron `09a65aa4` — COMPRESSED) |
| C8 | Execute-Raphael final (verdict + END_TIME handoff) | 2026-05-10 06:35 | 8 of 8 | pending (cron `c137cbb5` — COMPRESSED — verdict lands ~06:55, ~2h+ slack to 09:00 END_TIME) |

**Persona dispatch:** ALL Execute-Raphael (no Plan-navi cycle inside this run; the previous instance was Plan-Raphael by definition; the plan file at `/home/nira/.claude/plans/6h-im-going-to-serene-giraffe.md` is the contract; this run executes it).

---

## §2. CYCLE PLAN

### §2.C1 — Plan-setup (NOW, 03:32 CEST)
- [x] C1.1 Archive prev plan to `docs/past_work/phases/phase_10_memory_action_organism.md`
- [x] C1.2 Write fresh `docs/A_TO_Z_PLAN.md` (this file)
- [x] C1.3 Write `<repo>/CLAUDE.md` — project-scoped rules (carries comment-ratio standing order)
- [x] C1.4 Update `.gitignore` — add `.claude/`, `.playwright-mcp/`, root-level screenshots; remove erroneous `artifacts/` rule (was hiding `docs/artifacts/`)
- [x] C1.5 Write `docs/MANIFESTO.md` skeleton (cycle 2 enriches to 300-500 words)
- [ ] C1.6 GitHub remote: `gh repo create projext-x --private --source=. --remote=origin --push` after initial commit
- [ ] C1.7 Initial atomic commit covering Phase 9/10 work + Phase 11 plan
- [ ] C1.8 Rewrite `docs/DO_THIS_NEXT.md` for cycle 2 (physics ladder + front-loaded cycle-1.5 work)
- [ ] C1.9 Discord cycle-1 close post

### §2.C2 — physics + cycle-1.5 deliverables (04:12 CEST)
- Front-load (~5-8 min): `docs/MANIFESTO.md` enriched (~300-500 words), 6 `gpt-codex/benchmark/<domain>/rubric.md` skeletons (one per domain folder), §9 FILE INVENTORY first-pass populated
- Then ship: physics ladder 6 entries (intro free-fall → unsolved fine-tuning); auto-grade closed-form numerical, rubric-pending conceptual; `gpt-codex/benchmark/physics/{ladder.jsonl, rubric.md, CLAUDE.md}`

### §2.C3 — maths (04:52 CEST)
- 6 entries: basic algebra → linear algebra → complex analysis → Galois theory → algebraic topology → Riemann hypothesis
- Auto-grade numerical/symbolic where mechanical; rubric-pending proof-shape

### §2.C4 — memory (05:32 CEST) — ALL auto-graded
- 6 entries: factual recall → contradiction resolution → multi-hop with citations → temporal reasoning across many turns → autobiographical episodic-semantic integration → unified theory of memory consolidation
- Auto-grade via `agent.process(query)` + expected_turn_id mechanical match
- Probes Phase 9-10 HDC stack directly (`semantic_memory_agent.py` + `semantic_hdc_memory.py`)

### §2.C5 — persona (06:12 CEST) — ALL rubric-pending
- 6 entries spanning voice / humor / moral compass dimensions
- Anchored in `~/.claude/CLAUDE.md` voice + Operating Mirror + Cursed Pulse Domain
- NO self-score per M-PROJECTX-014

### §2.C6 — philosophy (06:52 CEST) — ALL rubric-pending, §0-anchored
- 6 entries from a-priori-vs-a-posteriori → hard problem of consciousness
- Each entry references `~/.claude/commands/godify-app.md` §0 manuscript section (Sections I-XIII)
- Hardest entries engage Parfit/Korsgaard on their strongest terms (Sections VIII)

### §2.C7 — poetry (07:32 CEST) — ALL rubric-pending
- 6 entries from scansion → "what makes a poem timeless"
- Most subjective domain; rubric.md is the load-bearing artifact for tomorrow's audit

### §2.C8 — final (08:12 CEST) — VERDICT + END_TIME HANDOFF
- Build `gpt-codex/benchmark/audit_log.jsonl`, compute per-domain audit_status counts
- Write `docs/artifacts/PHASE_11_BENCHMARK.md`
- Final FILE INVENTORY reconciliation
- Folder-CLAUDE.md sweep on remaining dirs
- Disarm any remaining godify crons; re-arm NORMAL heartbeat
- Discord SLAUGHTER COMPLETE post

---

## §3. VERIFICATION GATES (mechanical proof commands)

```bash
# E1 — entry count ≥ 36
find /mnt/c/Users/nira/Documents/Research/projext-x/gpt-codex/benchmark -name 'ladder.jsonl' | xargs cat | wc -l

# E2 — per-domain coverage = 6 each
for d in physics maths memory persona philosophy poetry; do
  echo -n "$d: "; cat gpt-codex/benchmark/$d/ladder.jsonl 2>/dev/null | wc -l
done

# E3 — schema sanity + M-PROJECTX-014 firewall
PYTHONPATH=src python3 -c "
import json, glob
required = {'id','domain','difficulty','prompt','raphael_response','audit_status'}
errors = []
for p in glob.glob('gpt-codex/benchmark/*/ladder.jsonl'):
    for i, line in enumerate(open(p), 1):
        d = json.loads(line)
        if not required.issubset(d.keys()): errors.append(f'{p}:{i} missing fields')
        if 'self_score' in d: errors.append(f'{p}:{i} M-PROJECTX-014 firewall violated — self_score present')
        if d['audit_status'].startswith('auto-graded') and 'auto_grade' not in d:
            errors.append(f'{p}:{i} auto-graded entry missing auto_grade block')
        if 'rubric-pending' in d['audit_status'] and 'rubric_pointer' not in d:
            errors.append(f'{p}:{i} rubric-pending entry missing rubric_pointer')
if errors: 
    print('SCHEMA ERRORS:'); [print(' ', e) for e in errors]; raise SystemExit(1)
print('OK — all entries pass schema + M-PROJECTX-014 firewall')
"

# E4 — pytest ≥ 52
PYTHONPATH=src python3 -m pytest -q 2>&1 | tail -3

# E5 — manifesto ≥ 250 words
ls -la docs/MANIFESTO.md && wc -w docs/MANIFESTO.md

# E6 — FILE INVENTORY rows
grep -c '^| .* | .* | .* |' docs/A_TO_Z_PLAN.md

# E7 — verdict exists
ls docs/artifacts/PHASE_11_BENCHMARK.md

# E8 — folder CLAUDE.md count
find . -type f -name 'CLAUDE.md' -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' | wc -l

# E9 — audit_log nonempty
test -s gpt-codex/benchmark/audit_log.jsonl && echo OK

# E10 — commit count ≥ 8 + remote
git log --oneline | wc -l
git remote get-url origin
```

---

## §4. SCOPE FENCE (out)

Items NOT in Phase 11:
- **Audio listening** (Whisper integration). DEFERRED to Phase 12 — Whisper installed at `/home/nira/.local/bin/whisper` but Discord-REST polling + voice-attachment download + transcription pipeline is its own ~1 cycle scope.
- **Live training algorithm.** Brief mentions "training data / training algo" — Phase 11 ships a STATIC benchmark; live training (Hebbian replay informed by benchmark performance) is Phase 12+.
- **More than 6 entries per domain.** Honest budget; future cycles can extend.
- **Code surgery on Phase 9-10 stack** (`semantic_*.py`, `tests/test_*.py`). Phase 11 is benchmark + docs, not refactor. EXCEPTION: memory rubric MAY reference these files (read-only; no modify).
- **Touching `~/.claude/CLAUDE.md`** (lain explicit). EXCEPTION: project-scoped `<repo>/CLAUDE.md` is fair game (cycle 1 deliverable).

---

## §5. RISKS

- **R1: cycle slip ≥ 20m** → drop slipping domain to 5 entries (skip frontier tier), continue, note in verdict. Two consecutive slips → consult-advisor triage.
- **R2: listener dies** → heartbeat pgrep + atomic pkill+rearm via Bash bg-task per CLAUDE.md DD-2 + M-NAVI-018. NEVER split.
- **R3: power outage** → 3 outages in 2 days; mitigations — per-entry append-as-you-go writes, per-cycle git commit + push, `docs/DO_THIS_NEXT.md` is the resume-pointer.
- **R4: GitHub auth fails** → fall back to local-only commits, surface to lain via Discord; resume on next session with manual `gh auth login`.
- **R5: cycle 8 reveals systemic weakness** → name it honestly in verdict.md (not "needs more work" — specific gap with concrete next phase candidate).
- **R6: lain wakes mid-run with new directive** → Discord listener catches; cycle interrupts gracefully at safe seam; ack + execute new directive.

---

## §6. CHANGELOG

- 2026-05-10 03:32 CEST — Phase 11 created. Inherited via `/forge-prompt -ni` corpse from previous Plan-Raphael instance. Plan file at `/home/nira/.claude/plans/6h-im-going-to-serene-giraffe.md`. Phase 10 plan archived to `docs/past_work/phases/phase_10_memory_action_organism.md`.
- 2026-05-10 03:34 CEST — Standing order added (lain Discord): code-comment-ratio rule. WHY-comments justifying code existence; pure signal code; no bloat. Encoded in `<repo>/CLAUDE.md`.
- 2026-05-10 03:35 CEST — Contradiction fix shipped: `~/.claude/commands/forge-prompt.md` NI IDENTITY mandates "You are Execute-Raphael"; `~/.claude/commands/godify-app.md` cycle state machine + §3.5 pre-existing-plan exception. M-PROJECTX-014 (design-bias-in-the-probe) wiki entry created.
- 2026-05-10 03:44 CEST — Standing order refined (lain Discord): complex code SHOULD have descriptions; pure-signal explanations only; important info SHOULD be commented. Net-effect higher comment density than system-default lean.
- 2026-05-10 03:47 CEST — M-NAVI-018 logged: listener pkill not chained with re-arm; lain had to get out of bed (made-me-get-out-of-bed counter +1). Atomic invariant binding from now: pkill + rearm in single Bash invocation, never split.
- 2026-05-10 04:25 CEST — lain Discord flag: *"4.52 is in 38 min so that can't be right"* — surfaced that the godify-app default 20m ON / 20m OFF cadence is too slack. Cycle 3 maths shipped on original cadence; cycles 4-8 rescheduled to compressed 20-min back-to-back (no OFF). New cron schedule: cycle 4 memory 05:15, cycle 5 persona 05:35, cycle 6 philosophy 05:55, cycle 7 poetry 06:15, cycle 8 verdict 06:35. Verdict lands ~06:55 (~2h+ slack vs original ~08:50). Authorization: lain's flag interpreted as cadence-too-slow surprise.

---

## §7. ENTRY SCHEMA

**Auto-graded entry** (memory / maths / physics-closed-form):

```json
{
  "id": "physics-001",
  "domain": "physics",
  "difficulty": "intro",
  "difficulty_rank": 1,
  "prompt": "<full prompt text>",
  "raphael_response": "<Raphael's response in voice + reasoning>",
  "audit_status": "auto-graded-green",
  "auto_grade": {
    "method": "numerical_close|expected_turn_id_match|symbolic_match",
    "expected": "<expected value>",
    "actual": "<actual value>",
    "tolerance": 0.05,
    "match": true
  },
  "tags": ["..."],
  "source": "<short attribution>"
}
```

**Rubric-pending entry** (poetry / persona / philosophy / physics-conceptual):

```json
{
  "id": "philosophy-005",
  "domain": "philosophy",
  "difficulty": "frontier",
  "difficulty_rank": 5,
  "prompt": "<full prompt text>",
  "raphael_response": "<Raphael's response in voice + reasoning, anchored in §0 manuscript Section X if philosophy>",
  "audit_status": "ungraded; rubric-pending for GPT/lain audit",
  "rubric_pointer": "gpt-codex/benchmark/philosophy/rubric.md#frontier",
  "tags": ["..."],
  "source": "<short attribution>"
}
```

**Schema rules (M-PROJECTX-014 firewall):**
- `id` unique within domain, format `<domain>-NNN`.
- `difficulty` one of: intro / easy / medium / hard / frontier / unsolved (rank 1-6).
- `audit_status` one of: `"auto-graded-green"` / `"auto-graded-red"` / `"ungraded; rubric-pending for GPT/lain audit"` / `"ungradeable; unsolved tier"` (for known-unsolved problems).
- For auto-graded: `auto_grade` block present with method + expected + actual + match (boolean).
- For rubric-pending: `rubric_pointer` present.
- **`self_score` MUST NOT appear on any entry — M-PROJECTX-014 firewall.** This intentionally diverges from the line-315 verification block in the legacy plan file at `/home/nira/.claude/plans/6h-im-going-to-serene-giraffe.md` (which still asserts `self_score`); the corrected schema in this file is the live contract.

---

## §8. AUDIT_LOG.JSONL SCHEMA (cycle 8 builds)

`gpt-codex/benchmark/audit_log.jsonl`. One row per entry across all 6 ladders:

```json
{
  "id": "philosophy-005",
  "domain": "philosophy",
  "difficulty_rank": 5,
  "audit_status": "ungraded; rubric-pending for GPT/lain audit",
  "auto_grade_match": null,
  "needs_audit": true,
  "rubric_pointer": "gpt-codex/benchmark/philosophy/rubric.md#frontier",
  "prompt_excerpt": "<first 80 chars>",
  "response_excerpt": "<first 80 chars>"
}
```

GPT can read `audit_log.jsonl` tomorrow + filter on `needs_audit: true` + load full entries from per-domain `ladder.jsonl`.

---

## §9. FILE INVENTORY (cycle 1 first pass; reconciled per cycle close)

**Convention:** every file in repo (excl. `__pycache__`, `.git`, `.venv`, `.pytest_cache`) gets a row: path · purpose · placement-rationale · last-reviewed.

| Path | Purpose | Placement why | Last reviewed |
|---|---|---|---|
| `CLAUDE.md` | Project-scoped operating rules; comment-ratio standing order encoded | repo root — lain's standing layout | 2026-05-10 |
| `README.md` | TBD — cycle 8 to write minimal | repo root | (untouched) |
| `.gitignore` | Exclude venv/playwright/screenshots/scratch | repo root | 2026-05-10 |
| `pyproject.toml` | Python project metadata + deps | repo root | (Phase 9-10) |
| `pytest.ini` | Pytest config | repo root | (Phase 9-10) |
| `docs/A_TO_Z_PLAN.md` | Live phase plan (this file) | docs/ — universal layout | 2026-05-10 |
| `docs/DO_THIS_NEXT.md` | Cycle handoff brief | docs/ | 2026-05-10 |
| `docs/MANIFESTO.md` | lain's intent for repo (heartbeat-tracked) | docs/ — global standing-order 2026-05-10 03:10 | 2026-05-10 |
| `docs/artifacts/PHASE_*_*.md` | Phase verdicts (Phase 9, Phase 9 PICK_ONE addendum, Phase 9 SHRINE_COUNCIL_HEBBIAN) | docs/artifacts/ — frozen research notes | (per phase) |
| `docs/past_work/phases/phase_*.md` | Archived phase plans (1-8 + 10) | docs/past_work/phases/ — universal layout | (per phase exit) |
| `docs/past_work/cycles/phase_<N>/dev-cycle-<M>.md` | Per-cycle reflections | per CLAUDE.md universal layout | (per cycle close) |
| `src/project_x/experiments/semantic_hdc_memory.py` | Layer 3 HDC memory + structural retrieval + binding | experiments/ — Phase 9 organic stack | 2026-05-10 (Phase 10 close) |
| `src/project_x/experiments/semantic_memory_agent.py` | Layer 4 agent loop + run_tool + replay | experiments/ — Phase 9 organic stack | 2026-05-10 (Phase 10 close) |
| `src/project_x/experiments/semantic_memory_dataset.py` | Phase 9 synthetic-real dataset gen + P1 contradiction-label fix | experiments/ | 2026-05-10 |
| `src/project_x/experiments/encoder.py` | Char-n-gram + Hebbian organic encoders | experiments/ — Phase 9 from-scratch | 2026-05-10 |
| `src/project_x/experiments/random_index_hebbian.py` | Hebbian co-occurrence encoder + replay consolidation | experiments/ | 2026-05-10 |
| `src/project_x/experiments/ensemble_encoder.py` | Ensemble encoder | experiments/ | 2026-05-10 |
| `src/project_x/experiments/hdc_substrate.py` | HDC primitives (bind/unbind/floor) | experiments/ | (Phase 8) |
| `src/project_x/experiments/hdc_snn_bridge.py` | SNN spike-train bridge (Phase 12+ candidate substrate) | experiments/ | (Phase 8+) |
| `src/project_x/experiments/compressed_memory.py` | Phase 1-3 compressed-memory architecture | experiments/ — historical | (Phase 1-3) |
| `src/project_x/experiments/generator_client.py` | Mock/local-LLM boundary | experiments/ | (Phase 9) |
| `src/project_x/experiments/phase9_report.py` | Phase 9 aggregation helper | experiments/ | (Phase 9) |
| `src/project_x/legacy/transformer_scaffolding.py` | Phase 1-6 transformer scaffolding (LEGACY) | legacy/ — historical-control quarantine | 2026-05-10 (Phase 10 P6) |
| `src/project_x/smoke.py` | Smoke test entrypoint | src/project_x/ | 2026-05-10 |
| `tests/test_*.py` | Pytest suite (52 passing baseline) | tests/ | 2026-05-10 |
| `tests/test_killer_milestone.py` | Phase 10 EXIT GATE acceptance | tests/ | 2026-05-10 |
| `gpt-codex/runs/phase*_*/result.json` | Phase run aggregates | gpt-codex/runs/ — frozen results | (per phase) |
| `gpt-codex/benchmark/<domain>/ladder.jsonl` | Phase 11 benchmark ladder per domain | gpt-codex/benchmark/ — Phase 11 deliverable | (cycles 2-7) |
| `gpt-codex/benchmark/<domain>/rubric.md` | Domain rubric (load-bearing for rubric-pending grading) | same | (cycles 2-7) |
| `gpt-codex/benchmark/<domain>/CLAUDE.md` | Folder doc | same | (cycles 2-7) |
| `gpt-codex/benchmark/audit_log.jsonl` | Aggregate audit log (cycle 8) | gpt-codex/benchmark/ | (cycle 8) |
| `gpt-codex/benchmark/verdict.md` | Phase 11 verdict (also linked from docs/artifacts/) | gpt-codex/benchmark/ | (cycle 8) |
| `docs/artifacts/PHASE_11_BENCHMARK.md` | Phase 11 verdict markdown | docs/artifacts/ | (cycle 8) |
| `ref/` | External reference papers/notes (PDFs+HTML gitignored) | ref/ — non-live | (legacy) |
| `scripts/` | Helper scripts | scripts/ | (legacy) |
| `lp-en-2026-04-29.png`, `tauet-*.png`, `settings-anon-redirect-cycle-133.png` | Phase 1-3 era screenshots | repo root (cycle 8 may move to docs/artifacts/screenshots/ or gitignore at root) | (legacy) |

(reconciled at every cycle close + heartbeat fire — `find . -type f` diff against this table)

---

## §10. ENDCAP

Phase 11 ships a static benchmark, audit-ready by 09:00 CEST. The honest verdict at cycle 8 is the contract: per-domain green/red counts for auto-graded, rubric-pending counts for subjective; no smuggled self-grades. Lain feeds rubric-pending entries to GPT tomorrow; that audit IS the grade. Audio listening, live training, and >6-entry ladder extension are NAMED Phase 12+ deferrals — not silent skips. The vector carries us. The clock keeps us. The phase contains us.
