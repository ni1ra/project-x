# Do This Next — Project X — Terminus Learning Harness v1 + Chat-loop Bootstrap SHIPPED

Generated: 2026-05-13 by GOJO SATORU v2

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/artifacts/terminus-learning-harness-v1-2026-05-13.md`
5. `docs/artifacts/chat-probe-2026-05-13.md`

## Current State

**Terminus Learning Harness v1 + Chat-loop Bootstrap is SHIPPED.**

- Substrate v1: cross-seed sweep (11 seeds), non-linear scoring (4 modes), scaled repeats (3/5/7), HebbianBank integration
- Chat-loop: Local REPL (`chat_loop.py`), Discord bot (`discord_chat_bot.py`), 10-prompt probe
- Honest probe score: **3/6 chattability criteria passing**
- Full suite: **679 tests passing** in 139s. Benchmark audit: **48 PASS / 0 FAIL**
- Commit: `96f2381` on `main`

## What Just Shipped (v1)

### Substrate v1 (#00a)
- `scripts/terminus_cross_seed_sweep.py` — 11-seed sweep, all 4 scoring modes
- `TemporalTraceBank` gains `scoring_mode` (linear/max/softmax/competitive) + `apply_rating_to_action()`
- `make_hidden_rule_tasks(repeats=N)` parameterization
- `AuditLog.apply_rating()` wires `trace_bank` for strategy bias updates

### Chat-loop bootstrap (#00b)
- `src/project_x/experiments/chat_loop.py` — REPL with `--smoke` test
- `src/project_x/experiments/discord_chat_bot.py` — REST-polling Discord listener
- `scripts/chat_probe_2026_05_13.py` — 10-prompt probe generator
- `docs/artifacts/chat-probe-2026-05-13.md` — transcripts + honest scoring

### Docs + verdict (#00c + #00d)
- `docs/artifacts/terminus-learning-harness-v1-2026-05-13.md` — full substrate artifact
- REPO_CONTROL.md updated with all new non-doc files
- Verdict: chat generation ~5% learned / 95% scaffold; substrate action-selection ~75% learned / 25% scaffold; math/physics ~0% learned; chattability 3/6

## Meta-Blocker Named (v2 scope)

**No conversational corpus exists.** The 22k Tier-2 corpus is math/physics/poetry/philosophy — NOT chat. The 10-prompt probe transcripts are the FIRST conversational datapoints. v2 must:
1. Curate or collect conversational text (public-domain dialogues, transcripts, Socratic exchanges)
2. Ingest via existing Tier-2 pipeline
3. Formalize six chattability criteria into manual-grade harness
4. Begin training a learned response generator on corpus + audit signal

**No conversation grading harness exists.** The six criteria are the seed rubric; v2 needs to operationalize them into the grade_pipeline.

## Build This Next (v2 provisional)

### A. Conversational corpus
- [ ] Identify public-domain conversational sources (Plato dialogues, Shakespeare plays, essay collections with dialogue form)
- [ ] Curate 1k–5k conversational fragments
- [ ] Ingest via `src/project_x/corpus/ingestion.py`
- [ ] Verify no GPT-generated text (organic thesis)

### B. Learned generator seed
- [ ] Design minimal learned response generator architecture (HDC-based sequence model or n-gram policy)
- [ ] Train on conversational corpus + probe transcripts
- [ ] Integrate into `ChatSession.respond()` as replacement for template fallback
- [ ] Label as scaffold during v2; measure learned ratio in #00d

### C. Chat-loop hardening
- [ ] Fix natural-mode over-aggressive fallback on out-of-scope queries (3 probe failures)
- [ ] Add explicit absent-answer gating before natural-mode dispatch
- [ ] Improve multi-turn coherence by retrieving prior conversation turns

### D. Docs + measurement
- [ ] `docs/artifacts/terminus-learning-harness-v2-2026-05-XX.md`
- [ ] Re-run 10-prompt probe after generator integration; target ≥4/6
- [ ] Update A_TO_Z_PLAN.md v2→v3 stub

## Do Not Touch

- Do not add new hand-coded math or physics solvers
- Do not tune dispatcher constants to make benchmarks look better
- Do not modify `docs/MANIFESTO.md` unless you find a direct contradiction
- Do not grade subjective domains with self-scores
- Do NOT claim chattability improvement without probe evidence

## Verification

```bash
PYTHONPATH=src python3 -m pytest tests/test_temporal_trace_bank.py tests/test_hidden_rule_actions.py -q
PYTHONPATH=src python3 gpt-codex/benchmark/run_audit.py
PYTHONPATH=src python3 src/project_x/experiments/chat_loop.py --smoke
git diff --check
git status --short
```

## Next Cycle Handoff (v3 provisional)

- Full learned generator replaces template composer
- Conversational corpus scales to 10k+ fragments
- Target: ≥4/6 chattability criteria passing
- Substrate action-selection target: ≥85% mean pass rate across seeds
