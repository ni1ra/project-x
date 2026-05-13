# Do This Next — Project X — Terminus Learning Harness v1 + Chat-loop Bootstrap

Generated: 2026-05-13 by GOJO SATORU v2

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/REPO_CONTROL.md`
4. `docs/paper.md` Chapter 8 (What comes next)

## Current State

**Terminus Learning Harness v0 is SHIPPED.**
- `TemporalTraceBank` lives in `src/project_x/learning/temporal_trace.py`
- Hidden-rule benchmark: 48 tasks, 75% held-out pass rate on seed=1729
- 679 tests passing, 48/48 benchmark audit green
- **No chat loop exists. Chattability criteria baseline = 0/6.**

**This cycle expands scope from substrate-only to substrate + chat-loop.**

## Build This Next

### A. Substrate v1

- [ ] **Cross-seed reliability sweep** — `scripts/terminus_cross_seed_sweep.py` (10+ seeds, characterize variance)
- [ ] **Non-linear scoring** — add max-based, softmax-gated, competitive-inhibition scorers to `TemporalTraceBank`
- [ ] **Scale repeats 3→5→7** — parameterize `make_hidden_rule_tasks(repeats=N)`, measure learning curve
- [ ] **HebbianBank integration** — wire `TemporalTraceBank` into `AuditLog.apply_rating()` so natural-mode ratings shape action bias

### B. Chat-loop bootstrap

- [ ] **Local REPL** — `src/project_x/experiments/chat_loop.py` wired to `ReasoningAgent` + `SemanticHDCMemory` + persona wrap
- [ ] **Discord bot** — `src/project_x/experiments/discord_chat_bot.py` cursor-aware polling in `#raphael-chat`
- [ ] **10-prompt probe** — self-author 10 prompts covering all 6 chattability criteria
- [ ] **Transcript artifact** — save to `docs/artifacts/chat-probe-2026-05-13.md`
- [ ] **Honest scoring** — N/6 with 1-line evidence per test

### C. Docs + verdict

- [ ] **Substrate artifact** — `docs/artifacts/terminus-learning-harness-v1-2026-05-13.md`
- [ ] **REPO_CONTROL rows** — `chat_loop.py`, `discord_chat_bot.py`, probe artifact
- [ ] **Verdict** — learned-vs-hand-coded ratio paragraph (#00d)

## Do Not Touch

- Do not add new hand-coded math or physics solvers
- Do not add new domain route branches to `ReasoningAgent` unless fixing a blocking bug
- Do not tune dispatcher constants to make benchmarks look better
- Do not modify `docs/MANIFESTO.md` unless you find a direct contradiction
- Do not grade subjective domains with self-scores
- Do NOT template-stitch chat responses without labeling them as scaffold in #00d

## Verification

```bash
PYTHONPATH=src python3 -m pytest tests/test_temporal_trace_bank.py tests/test_hidden_rule_actions.py -q
PYTHONPATH=src python3 scripts/terminus_learning_harness_demo.py --mode test --output /tmp/project-x-terminus-learning-harness.json
PYTHONPATH=src python3 gpt-codex/benchmark/run_audit.py
PYTHONPATH=src python3 src/project_x/experiments/chat_loop.py --smoke
git diff --check
git status --short
```

## Artifacts To Produce

1. `docs/artifacts/terminus-learning-harness-v1-2026-05-13.md`
2. `docs/artifacts/chat-probe-2026-05-13.md`

## Next Cycle Handoff (v2 provisional)

- Conversational corpus curation (the meta-blocker)
- Manual-grade harness formalization for chattability criteria
- Learned generator seed training on probe transcripts + corpus
