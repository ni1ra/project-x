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
| #00audit-B3 | MED | `docs/artifacts/CLAUDE.md` | post-Phase-12 verdict counts | shipped `a98d331` (now superseded — file deleted; inventory in §2) |
| #00audit-B4 | MED | `README.md` + `pyproject.toml` | reframe as HDC/Hebbian organic memory-agent stack | shipped `13ab133` |
| #00audit-C1 | MED | `semantic_memory_agent.py:298` | promote `extract_query_subjects` to public | shipped `de742b0` |
| #00audit-C2 | MED | `compressed_memory.py` + torch dep + `test_smoke.py` | torch optional via `[legacy]` extra + quarantine markers | shipped `8500bbc` |
| #00audit-D1 | MED | repo root | `.github/workflows/test.yml` (pytest + schema firewall) | pending |
| #00audit-D2 | MED | `semantic_hdc_memory.py:338` | `write_one` amortized O(1) via growth-by-doubling | shipped `fb47e9a` |
| #00audit-D3 | MED | `gpt-codex/benchmark/` | executable `run_audit.py` harness | in flight |
| #00audit-E1 | MED | coverage | `hdc_substrate.py` 24% → 89% + retire-or-cover policy | shipped `32ad13e` |
| #00audit-F1 | LOW | `semantic_hdc_memory.py:335`, `random_index_hebbian.py:210` | trim WHAT-comments | pending |
| #00audit-F2 | LOW | `gpt-codex/runs/` | retention policy | pending |

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

## §2. REPO INVENTORY — every dir + every load-bearing file with justification

### `/` — repo root (3 files)

| Path | Justification |
|---|---|
| `README.md` | Public-facing brief — what the project is, quick-start, key artifacts. Reframed `13ab133` from "token-prediction architecture" to "post-transformer organic memory + agent stack" (audit-B4). |
| `pyproject.toml` | Setuptools build config + deps. `numpy`, `pydantic`, `requests` are core. `torch>=2.2` moved to `[legacy]` optional extra (audit-C2 quarantine). `dev` extra: `pytest`, `ruff`. |
| `pytest.ini` | Pytest config — adds `src/` to PYTHONPATH so `from project_x.*` imports work without `pip install -e .`. |
| `.gitignore` | Standard Python ignores + coverage tooling output + `.claude/` + `.playwright-mcp/` + large reference materials in `ref/papers/` and `ref/pages/` + the codex extracted-content blobs in `gpt-codex/extracted/` and `gpt-codex/sources/` (metadata-only tracking; raw blobs stay local). |

**Per-directory `CLAUDE.md` files were retired 2026-05-10** (project-root + 15 sub-dir CLAUDE.md files deleted). Documentation single-source-of-truth is `docs/`. Universal Raphael protocol stays at `~/.claude/CLAUDE.md` (untouched per lain directive).

### `docs/` — project documentation (4 live + 23 frozen artifacts + cycle archives)

| Path | Justification |
|---|---|
| `docs/MANIFESTO.md` | lain's intent + standing orders (NO transformers; comment-ratio; append-as-you-go; listener manual re-arm; M-PROJECTX-014 firewall). Live; heartbeat-tracked; re-read at session start. |
| `docs/A_TO_Z_PLAN.md` | THIS file — current-run plan + complete repo inventory + phase changelog. Rotates to `past_work/phases/` on phase exit. |
| `docs/DO_THIS_NEXT.md` | Current cycle scope + handoff. Rewritten at every cycle close. Power-on resume pointer. |
| `docs/artifacts/` | Phase verdicts (frozen-with-addendum convention) + research notes. See sub-table below. |
| `docs/past_work/phases/` | Archived phase plans. One file per closed phase: `phase_<N>_<theme>.md`. |
| `docs/past_work/cycles/phase_<N>/` | Per-cycle reflections — `dev-cycle-<M>.md` written at each cycle close. Phases 1, 4-12 represented. |

#### `docs/artifacts/` (frozen verdicts + research notes)

| Path | Phase / topic |
|---|---|
| `PHASE_7_HOPFIELD_LENS.md` | Phase 7 Hopfield lens proof |
| `PHASE_8_HDC_ORGANIC_MEMORY.md` | Phase 8 random-symbol HDC baseline (99.25% recall at D=50000) |
| `PHASE_8_HOSTILE_REVIEW.md` | Phase 8 hostile review |
| `PHASE_9_PICK_ONE_VERDICT.md` | Phase 9 pick-one verdict + lain organic-only addendum (2026-05-09) |
| `PHASE_9_SEMANTIC_HDC_MEMORY.md` | Phase 9 verdict + Phase 10 closure addenda |
| `PHASE_9_SHRINE_COUNCIL_HEBBIAN.md` | Council reasoning (Plate dossier especially relevant for Phase 10 P3 fact-graph) |
| `PHASE_11_BENCHMARK.md` | Phase 11 verdict (9/2/21/4) + Phase 12 closure addendum (11/0/21/4) |
| `PHASE_12_RETRIEVAL_DISAMBIGUATION.md` | Phase 12 verdict — `retrieve_structural_full_history` + `_LIST_ALL_HINTS` classifier closing memory-004/005 |
| `PHASE_13_CANDIDATES.md` | Phase 13 framing inputs (lain-gated, NOT a verdict) — retrieval telemetry, snapshot/restore, adversarial memory matches, from-scratch symbolic generator, binding-algebra bakeoff |
| `COUNCIL_A_ENCODER.md` … `COUNCIL_H_BEYOND_HUMAN_CAP.md` | Phase 9 council deliberations across 8 architectural axes |
| `DISCORD_BRIEF_RAPHAEL_ROADMAP.md` | Discord brief on Raphael roadmap |
| `RESEARCH_NOTE.md` | Older research notes |
| `ROADMAP_TO_RAPHAEL.md` | Older long-arc roadmap |
| `SHRINE_COUNCIL_PHASE_8.md` | Phase 8 council |
| `T4_bit_accuracy_curve.png`, `T4_capacity_curve.png`, `T4_cliff_vs_D.png`, `T4_dscaling_curves.png` | Phase 4 figures (bit-accuracy, capacity, cliff, D-scaling) |

### `src/project_x/` — runnable research harness

#### Live Phase 9-10 production organic stack — `src/project_x/experiments/`

| Path | Justification |
|---|---|
| `semantic_hdc_memory.py` | Layer 3 — `SemanticHDCMemory`: HDC accumulator + fact-graph (P3 subject indexing) + structural retrieval + HDC role-filler binding (#00c-2) + incremental `write_one` (audit-D2 amortized-O(1) growth) + `replay_consolidate` (P4) + `retrieve_structural_full_history` (Phase 12). turn_id ↔ row mapping (audit-A1) for non-contiguous IDs. `extract_query_subjects` is the public API surface (audit-C1). |
| `semantic_memory_agent.py` | Layer 4 — `MemoryAgent.process(text)` rule-based controller; routes write vs retrieve; `_LIST_ALL_HINTS` classifier (Phase 12) routes list-all queries to `retrieve_structural_full_history`; template composer (NO LLM); evidence packet with cited turn IDs; absent-answer threshold gating; `compose_answer` formats single-turn / multi-turn / full-history evidence. |
| `semantic_memory_dataset.py` | Phase 9 synthetic-real conversation generator + labeled query set (P1 contradiction-label fix). |
| `encoder.py` | Char-n-gram + Hebbian organic encoders. From-scratch; no pretrained transformers. |
| `random_index_hebbian.py` | Hebbian co-occurrence encoder + replay-consolidation extension. `fit(reset=True)` (audit-A2) for idempotent re-fit. Sparse-ternary index vectors + Mikolov subsampling + optional negative sampling. |
| `ensemble_encoder.py` | Phase 9 Cycle 4 prototype — alpha-blend / max / per-type ensemble strategies. Alpha-blend logic was inlined into `SemanticHDCMemory._ensemble_cosines`; this module is retained as historical reference for max / per-type strategies that may be revisited. |
| `hdc_substrate.py` | HDC primitives — `bind`, `unbind`, `superpose`, `write`, `read`, `cleanup`, `random_vector`, `bit_accuracy`. Self-test CLI via `--self-test`. Coverage 24% → 89% (audit-E1). |
| `hdc_snn_bridge.py` | SNN spike-train bridge — Phase 13+ candidate substrate (research script, CLI-driven). |
| `__init__.py` | Package marker (empty). |

##### Phase 4-8 historical research scripts (CLI-driven, coverage policy: scripts not library)

| Path | Justification |
|---|---|
| `hdc_capacity.py` | T1 within-capacity recall + T4 capacity cliff sweep |
| `hdc_compose.py` | T2 compositional binding battery (role-filler retrieval + cleanup) |
| `hdc_continual.py` | T3 continual-learning retention test (100 random pairs across time) |
| `hdc_conversation_demo.py` | Indefinite-context conversability use-case demo |
| `hdc_vs_naive_comparison.py` | Memory-vs-accuracy trade-off — HDC accumulator vs naive per-turn storage |
| `hopfield_lens.py` | Post-hoc Modern Hopfield Network energy-regime analysis (β-effective + regime classification from saved `selector_snapshot` tensors) |

##### Quarantined / utility (audit-C2; torch-dependent; `[legacy]` extra)

| Path | Justification |
|---|---|
| `compressed_memory.py` | Phase 1-3 transformer-style historical control. **DO NOT IMPORT in organic-thesis code.** |
| `tasks.py` | Task registry exclusively for `compressed_memory` experiments. Quarantine surface. |
| `util_harness.py` | Phase 7 GPU-utility harness — pre/during/post `nvidia-smi` sampling for the 70-90% util-band check. |

#### Quarantine — `src/project_x/legacy/`

| Path | Justification |
|---|---|
| `transformer_scaffolding.py` | Phase 1-6 transformer-style scaffolding (was at `src/project_x/model.py` until P6 quarantine). **DO NOT IMPORT in organic-thesis code.** Required for the `legacy` extra; gated by `pytest.importorskip("torch")` in `test_smoke.py`. |
| `__init__.py` | Package marker. |

#### Top-level `src/project_x/` files

| Path | Justification |
|---|---|
| `config.py` | `ModelConfig` + `RunConfig` dataclasses for the legacy `ProjectXModel`. Used by `smoke.py` and `legacy/transformer_scaffolding.py`. |
| `smoke.py` | Smoke entry-point exercising the legacy `ProjectXModel`. Quarantined; torch-dependent. |
| `__init__.py` | Package marker. |

### `tests/` — pytest suite (86 tests passing as of this run)

| Path | Justification |
|---|---|
| `test_compressed_memory.py` | Phase 1-3 quarantine smoke. `pytest.importorskip("torch")` so the active suite runs without the `[legacy]` extra. |
| `test_encoder.py` | Phase 9 char-n-gram + Hebbian organic encoder coverage. |
| `test_hdc_substrate.py` | HDC primitives + 4 self-test fns + `run_self_test` CLI driver (audit-E1; 24% → 89% coverage on hdc_substrate). |
| `test_killer_milestone.py` | Phase 10 EXIT GATE acceptance — 5 capabilities (teach + correct + multi-hop + refuse-absent + tool-execution-with-writeback). |
| `test_random_index_hebbian.py` | Phase 9 + audit-A2 (`fit(reset=True)` idempotency regression guard). |
| `test_retrieval_modes.py` | Phase 12 retrieval-mode disambiguation regression guard (6 tests; audit-A4 tightened the unknown-subject behavioral assertion). |
| `test_semantic_hdc_memory.py` | Phase 9-10 Layer 3 HDC memory + audit-A1 (non-contiguous turn_ids regression guard) + audit-A3 (replay_consolidate idempotency) + audit-D2 (write_one amortized-O(1) mechanics + perf-ratio < 5x batch). |
| `test_semantic_memory_agent.py` | Phase 9-10 Layer 4 agent loop + run_tool + replay coverage. |
| `test_semantic_memory_dataset.py` | Phase 9 synthetic dataset gen. |
| `test_smoke.py` | Phase 1-6 legacy scaffolding smoke. `pytest.importorskip("torch")` (audit-C2). |
| `test_benchmark_harness.py` | Audit-D3 — invokes `gpt-codex/benchmark/run_audit.py` in-process; asserts all auto-graded entries replay green against the live stack. |

### `gpt-codex/` — Phase 9-12 inputs + benchmark + run results

| Path | Justification |
|---|---|
| `gpt-codex/benchmark/` | **Phase 11 Raphael Domain Benchmark Suite.** 6 domain ladders × 6 entries (`physics/`, `maths/`, `memory/`, `persona/`, `philosophy/`, `poetry/`), each with `ladder.jsonl` + `rubric.md`. Entry schema in §7 below. M-PROJECTX-014 firewall: NO `self_score` field anywhere. Aggregate `audit_log.jsonl` (one row per entry, `needs_audit:true` filter for GPT pass) + `verdict.md` (cross-linked from `artifacts/PHASE_11_BENCHMARK.md`). |
| `gpt-codex/benchmark/run_audit.py` | Audit-D3 harness — replays auto-graded entries against the live stack each commit. Memory domain: build `MemoryAgent` + `write_batch(setup)` + `agent.process(query)` + verify cited turn_ids ⊇ expected + `expected_response_contains` tokens in `answer_text`. Maths/physics: verify recorded `auto_grade.match` (frozen symbolic / numerical). Subjective domains: skipped (rubric-pending per M-PROJECTX-014). Exit code 0 = all pass; nonzero = regression. |
| `gpt-codex/runs/` | Per-run aggregate `result.json` directories. Phase 1-9 training/sweep runs and Phase 9 encoder runs (~80+ subdirs covering compressed-memory baselines, Phase 4 adversarial, Phase 7 hbsweep + lrc-distill, Phase 8 T1-T4 + comparison + snnbridge, Phase 9 dataset + encoder + agent_demo + memory). Frozen-per-phase: once a phase's verdict lands in `artifacts/`, run dirs are immutable. (Audit-F2 retention policy pending.) |
| `gpt-codex/notes/` | Reading notes (`architecture_mechanisms_matrix.md`, `deepseek_v4_reading_notes.md`, `frontier_model_notes.md`, `open_questions.md`). Source-grounded notes that informed Phase 1-3 + Phase 7 design. |
| `gpt-codex/brainstorm/` | Phase 1 ideation artifacts (`ARCHITECTURE_CANDIDATES.md`, `FINAL_RECOMMENDATION.md`, `IDEA_BANK.md`, `KILL_CRITERIA.md`, `NOVELTY_MATRIX.md`, `TOP_3_DESIGNS.md`). Frozen — historical record of the design-space exploration that picked the compressed-memory direction. |
| `gpt-codex/logs/` | Curl/pdftotext logs from Phase 1 source ingestion. `.log`-pattern is gitignored at filename level but tracked here historically. |
| `gpt-codex/extracted/` | (gitignored) Codex extracted-content blobs — large, metadata-only via `ref/SOURCE_MANIFEST.md`. |
| `gpt-codex/sources/` | (gitignored) Source pages cache — large, metadata-only via `ref/SOURCE_MANIFEST.md`. |

### `ref/` — public reference material

| Path | Justification |
|---|---|
| `ref/SOURCE_MANIFEST.md` | Manifest of public reference sources (papers, model reports). |
| `ref/sources.json` | Machine-readable source list. |
| `ref/papers/` | (gitignored binary blobs) PDFs of reference papers. |
| `ref/pages/` | (gitignored HTML blobs) Cached source pages. |

### `scripts/` — research-scripts that don't fit `src/`

| Path | Justification |
|---|---|
| `aggregate_phase7_results.py` | Aggregates Phase 7 hbsweep + lrc-distill results across seeds. |
| `fetch_refs.py` | Source-fetch driver for `ref/`. |
| `generate_docs.py` | Source-doc generator (Phase 1 era). |
| `phase7_baseline.sh`, `run_phase7_grid.sh`, `run_phase7_hbsweep.sh` | Phase 7 sweep runners. |
| `plot_phase8_dscaling.py`, `plot_phase8_t4.py` | Plot generators for Phase 8 figures (the T4_*.png set in `docs/artifacts/`). |

### `.github/workflows/` — CI (audit-D1, pending)

To be created — `test.yml` running `pytest -q` + the M-PROJECTX-014 schema firewall (`grep -r self_score gpt-codex/benchmark/*/ladder.jsonl` returns 0) + `gpt-codex/benchmark/run_audit.py` (audit-D3). Status gate for push/PR.

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
- 2026-05-10 — Repo-hygiene sweep (this commit): per-directory `CLAUDE.md` files retired; project-level docs collapse into `docs/MANIFESTO.md` + `docs/A_TO_Z_PLAN.md` + `docs/DO_THIS_NEXT.md` + `docs/past_work/`. Stray Drøm-era PNGs + `.playwright-mcp/` logs + top-level `artifacts/` scaffold-run dirs deleted from working tree. `.gitignore` cleaned of stale Drøm patterns; `.coverage` added.

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
