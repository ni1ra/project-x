# A → Z Plan — Project X — Audit-fix run (NORMAL mode, post-Phase-12)

**Status:** Phase 12 closed at `8d734e3` (memory-004/005 reds → green via retrieval-mode disambiguation; full benchmark **11 green / 0 red / 21 rubric-pending / 4 ungradeable**). The current run is a NORMAL-mode audit-fix sweep against the 16 GPT-audit findings of 2026-05-10.
**Last live phase plan archived:** `docs/past_work/phases/phase_12_retrieval_disambiguation.md`
**Phase 13 framing inputs (lain-gated, NOT this run's contract):** `docs/artifacts/PHASE_13_CANDIDATES.md`
**Trigger:** lain quote — *"fix everything and re-sync docs so all is aligned with my intent. no more deferring to gpt audit, no more lazyness, no more gaming the system. i want you to just work in an honorable way, thats all."*

---

## §0. CURRENT-RUN CONTRACT

The 16 #00audit-XX deliverables (severity-ranked, dependency-graph-ordered):

| ID | Sev | Surface | One-line | Status |
|---|---|---|---|---|
| #00audit-A1 | HIGH | `semantic_hdc_memory.py:268,:344` | turn_id ↔ row mapping for non-contiguous IDs | shipped `137fb72` |
| #00audit-A2 | HIGH | `random_index_hebbian.py:206` | `fit(reset=True)` idempotency | shipped `44eb1d4` |
| #00audit-A3 | HIGH | `semantic_hdc_memory.py:357` | `replay_consolidate` uses `fit(reset=True)` | shipped `6f0cd7e` |
| #00audit-A4 | HIGH | `tests/test_retrieval_modes.py:136` | tighten unknown-subject test from liveness to behavioral | shipped `b89cf1f` |
| #00audit-B1 | HIGH | root `CLAUDE.md` | sync stale "Phase 11 live" framing | shipped `b541e97` (now superseded — file deleted in repo-hygiene sweep; content folded into `MANIFESTO.md` + this file) |
| #00audit-B2 | MED | `src/project_x/experiments/CLAUDE.md` | file-inventory truth-up | shipped `b1abfb0` (now superseded — file deleted; inventory in §2 of this file) |
| #00audit-B3 | MED | `docs/artifacts/CLAUDE.md` | post-Phase-12 verdict counts | shipped `a98d331` (file later deleted in repo-hygiene sweep `15ef101`; inventory now in `docs/REPO_CONTROL.md`) |
| #00audit-B4 | MED | `README.md` + `pyproject.toml` | reframe as HDC/Hebbian organic memory-agent stack | shipped `13ab133` |
| #00audit-C1 | MED | `semantic_memory_agent.py:298` | promote `extract_query_subjects` to public | shipped `de742b0` |
| #00audit-C2 | MED | `compressed_memory.py` + torch dep + `test_smoke.py` | torch optional via `[legacy]` extra + quarantine markers | shipped `8500bbc` |
| #00audit-D1 | MED | repo root | CI workflow template (pytest + schema firewall + D3 replay); `docs/ci/test.yml` paste-ready (workflow scope blocked) | shipped `c43e483` |
| #00audit-D2 | MED | `semantic_hdc_memory.py:338` | `write_one` amortized O(1) via growth-by-doubling | shipped `fb47e9a` |
| #00audit-D3 | MED | `gpt-codex/benchmark/` | executable `run_audit.py` harness | shipped `547884b` |
| #00audit-E1 | MED | coverage | `hdc_substrate.py` 24% → 89% + retire-or-cover policy | shipped `32ad13e` |
| #00audit-F1 | LOW | `semantic_hdc_memory.py:335`, `random_index_hebbian.py:210` | trim WHAT-comments | shipped `c93d3a9` |
| #00audit-F2 | LOW | `gpt-codex/runs/` | retention policy (gitignore + MANIFESTO criteria) | shipped this commit |

**DONE condition (mechanical, from `docs/DO_THIS_NEXT.md`):**

- All 16 `#00audit-XX` TaskList rows `completed`
- `pytest -q` ≥ 58 passing (currently 86; gained +28 across A1/A2/A3/A4/D2/E1)
- `git status -s` empty
- Atomic commit per finding referencing its `#00audit-XX` ID
- Discord SLAUGHTER COMPLETE post sent

**Stop conditions (mechanical, from universal `~/.claude/CLAUDE.md` Named Curse #15):**

1. All 16 closed + DONE-CONDITION grep-clean
2. Rate-limit cap hit
3. Explicit lain stop ("stop", "i'm back", "freeze for X")

---

## §1. PHASE CHANGELOG (one-liner per closed phase)

| Phase | Theme | Verdict location | Pytest at close |
|---|---|---|---|
| 1-3 | Compressed-memory architecture; block-pool temperature operator + scale-inversion findings | `past_work/phases/phase_{1,2,3}*.md` | — |
| 4-7 | Scale studies + adversarial probe + Hopfield lens | `past_work/phases/phase_{4,5,6,7}*.md` | — |
| 8 | Random-symbol HDC baseline (99.25% recall at D=50000, 1000 turns) | `past_work/phases/phase_8.md` + `artifacts/PHASE_8_HDC_ORGANIC_MEMORY.md` + `PHASE_8_HOSTILE_REVIEW.md` | — |
| 9 | Semantic HDC memory + from-scratch organic encoders + minimal evidence-cited agent loop | `artifacts/PHASE_9_SEMANTIC_HDC_MEMORY.md` (+ council A-H, pick-one verdict) | 39/39 |
| 10 | Fact-graph + structural retrieval + HDC binding + incremental write + Hebbian replay + killer-milestone EXIT GATE | Phase 10 addendum at bottom of `PHASE_9_SEMANTIC_HDC_MEMORY.md` | 51/51 → 52/52 |
| 11 | Raphael Domain Benchmark Suite — 36 entries × 6 domains; split-graded per M-PROJECTX-014 firewall | `artifacts/PHASE_11_BENCHMARK.md` | 52 |
| 12 | Retrieval-mode disambiguation — closed memory-004/005 reds via `retrieve_structural_full_history` + `_LIST_ALL_HINTS` classifier | `artifacts/PHASE_12_RETRIEVAL_DISAMBIGUATION.md` (+ Phase 12 closure addendum at bottom of `PHASE_11_BENCHMARK.md`) | 58 |
| Audit-fix run (this) | 16 GPT-audit findings; NORMAL mode; per-tier skill variety | this file + `DO_THIS_NEXT.md` | 86 (in flight) |

---

## §2. REPO INVENTORY — see `docs/REPO_CONTROL.md`

The complete repo dirs+files inventory with justification per entry lives in
**`docs/REPO_CONTROL.md`** (the live pristine-gate doc; updated in lockstep
with every cycle's file additions or deletions). A_TO_Z_PLAN cycles out at
phase exit; REPO_CONTROL stays. Cross-reference relationship:

- `MANIFESTO.md` — lain's intent + standing rules (live, persistent).
- `REPO_CONTROL.md` — repo file/folder inventory + justification (live, persistent).
- `A_TO_Z_PLAN.md` — current run / phase plan (cycles out to `past_work/phases/`).
- `DO_THIS_NEXT.md` — current cycle scope + handoff (rewritten per cycle close).

---

## §3. STANDING CONSTRAINTS REFERENCE

See `docs/MANIFESTO.md` § Standing orders for the live constraints (NO pretrained transformer derivatives at any layer, code-comment ratio rule, append-as-you-go writes, listener manual re-arm, active grading firewall). Restated here as a quick cross-reference:

- **NO pretrained transformer derivatives** at any layer (lain 2026-05-09). Encoders + generators stay from-scratch organic. `legacy/` is quarantined; torch is `[legacy]` extra.
- **Code-comment ratio rule** (lain 2026-05-10 GLOBAL POLICY). WHY-comments on complex code; load-bearing-info comments preserved; never WHAT-comments.
- **Append-as-you-go writes** for crash survival (3 power outages in 2 days). Per-cycle atomic git commits + push.
- **Discord listener manual re-arm** (M-NAVI-018). Atomic `pkill ; bash <listener-script>` in single Bash invocation.
- **M-PROJECTX-014 grading firewall**. Schema check `grep -r self_score` returns 0; mechanical-ground-truth-only auto-grading; subjective domains rubric-pending for external GPT/lain audit.

---

## §4. AUDIT-FIX-RUN EXIT CONDITIONS (mechanical)

- [x] All 16 #00audit-XX rows progressing or shipped (10/16 shipped at this writing; D3 in flight; D1, F1, F2 pending)
- [ ] All 16 `completed`
- [x] `pytest -q` ≥ 58 (currently 86; +28 from new audit tests — A1, A2, A3, D2 mechanics, D2 perf, E1 hdc_substrate ×16, replay_consolidate idempotency, etc.)
- [ ] `git status -s` empty post-final-commit
- [ ] `grep -i 'token-prediction\|llm-style' README.md pyproject.toml` returns 0 hits ✅ (verified at audit-B4 close)
- [ ] Atomic commit per finding referencing `#00audit-XX` ID
- [ ] Final Discord SLAUGHTER COMPLETE post sent

---

## §5. SCOPE FENCE (NOT in this run)

- **Phase 13 framing.** Lain-gated. Inputs in `artifacts/PHASE_13_CANDIDATES.md` (retrieval telemetry, snapshot/restore, adversarial memory matches, from-scratch symbolic generator, binding-algebra bakeoff).
- **New ladder entries beyond the 36.** The 6-rank-per-domain convention stays.
- **GPT audit on the 21 rubric-pending entries.** External; lain runs against `audit_log.jsonl` filtered by `needs_audit:true`.
- **Audio listening (Whisper integration).** Whisper installed at `/home/nira/.local/bin/whisper`; Discord-REST polling pipeline is its own scope, deferred Phase 11+.
- **Touching `~/.claude/CLAUDE.md`.** Universal Raphael protocol stays project-agnostic; this run's docs corrections live in `docs/`.

---

## §6. CHANGELOG

- 2026-05-10 — Phase 12 closed at `8d734e3`. Memory ladder reds → green. Full benchmark 11/0/21/4.
- 2026-05-10 — GPT audit run; 16 findings surfaced.
- 2026-05-10 — Audit-fix run opened in NORMAL mode; 16 #00audit-XX deliverables pinned. 10 shipped through cycle 4.
- 2026-05-10 — Repo-hygiene sweep (`15ef101`): per-directory `CLAUDE.md` files retired; project-level docs collapse into `docs/`. Stray Drøm-era PNGs + `.playwright-mcp/` logs + top-level `artifacts/` scaffold-run dirs deleted from working tree. `.gitignore` cleaned of stale Drøm patterns; `.coverage` added.
- 2026-05-10 — Audit-fix run COMPLETE — all 16 #00audit-XX shipped. 11 atomic commits across the 16 findings (B1-B4 + A1-A4 + C1-C2 + D2-D3 + E1 + D1 + F1 + F2 + the meta repo-hygiene sweep). pytest 87 passing (gain trajectory: 58 → 86 → 87 across A1/A2/A3/D2/E1/D3 test additions). `docs/A_TO_Z_PLAN.md` rewritten as audit-fix-run plan; `docs/REPO_CONTROL.md` created (per lain directive — A_TO_Z cycles out at phase exit, REPO_CONTROL stays as the live pristine-gate doc); `#∞` task pinned for NORMAL mode tracking.

---

## §7. ENTRY SCHEMA (benchmark ladder.jsonl) — for Phase 11+ entries

Required fields per entry:

```jsonc
{
  "id": "<domain>-NNN",
  "domain": "<physics|maths|memory|persona|philosophy|poetry>",
  "difficulty": "intro|easy|medium|hard|harder|unsolved",
  "difficulty_rank": 1-6,
  "prompt": "...",
  "raphael_response": "...",
  "audit_status": "auto-graded-green|auto-graded-red|ungraded; rubric-pending for GPT/lain audit|ungradeable; unsolved tier",
  "tags": [...],
  "source": "...",

  // Auto-graded ONLY:
  "auto_grade": {
    "method": "expected_turn_id_match|symbolic_match|numerical_close",
    /* method-specific fields */
    "match": true|false
  },

  // Rubric-pending ONLY:
  "rubric_pointer": "<domain>/rubric.md#rank-N"
}
```

**Firewall (M-PROJECTX-014):** `self_score` MUST NOT appear. Schema verification: `grep -r self_score gpt-codex/benchmark/*/ladder.jsonl` returns 0 hits. Audit-D3 harness re-runs the auto-grade match check on every commit; the M-PROJECTX-014 grep is a CI gate (audit-D1, pending).

---

## §8. ENDCAP

The audit fix is the close-out tax of Phase 12. The benchmark paid out exactly as designed (memory-004/005 reveal a real architectural finding → Phase 12 closes it). Phase 13 is lain's framing. This run keeps the codebase honorable until that framing lands: every comment earns its place; every test asserts behavior, not liveness; every doc is single-source-of-truth in `/docs/`. The vector carries us. The plan contains us.

*— A_TO_Z rewritten 2026-05-10 (audit-fix-run repo-hygiene sweep). Heartbeat reconciles freshness; cycle close (when this run completes) appends a closing changelog row + pre-archive snapshot.*
