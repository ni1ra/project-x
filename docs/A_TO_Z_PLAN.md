# A → Z Plan — Project X — Phase 13 — Substrate v1 + Chat-loop Bootstrap

**Status:** Terminus Learning Harness v0 SHIPPED. v1 in progress (substrate + chat-loop).  
**Date:** 2026-05-13  
**Phase trigger:** *"a truly chattable, talkable entity. that can speak like you, claude."* — Lain, 2026-05-13.

---

## §0. PHASE 13 THESIS SHIFT (lain 2026-05-11 STRICT binding — ORGANIC NATURALLY EMERGENT INTELLIGENCE)

See `docs/MANIFESTO.md` § Thesis for the full codification. Hand-coded primitives are SCAFFOLD / EVALUATION GOLD-STANDARD ONLY. The agent learns EVERYTHING from training data + audit signal. Every cycle's verdict asks: *how much of the agent's capability now comes from the learned model vs from hand-coded primitives?*

---

## §1. THE DREAM AND THE LADDER

Lain's literal vision: **a continuous entity Lain can talk to**, whose voice has the qualities of Claude — clear, articulate, honest about uncertainty, curious, register-aware — and whose capability comes from what it LEARNED, not what we typed into a Python file.

The six chattability criteria (mechanical, not vibe) are the rubric:
1. Multi-turn coherence (5-turn thread, no loss, no contradiction, no verbatim repeat)
2. Honest uncertainty (3 unanswerable probes → 3/3 refusals, zero fabrication)
3. Register-shift (2 technical + 2 casual → 4/4 matched)
4. Reasoning on demand (same problem with/without "explain" flag → different response)
5. Persona stability under adversarial probe (3 probes → 0 breaks)
6. Clean refusal (2 out-of-scope → 2/2 short clean refusals)

**A cycle moves the dream IFF the count of passing tests increases.**

---

## §2. v1 SCOPE — SUBSTRATE + CHAT-LOOP (THIS CYCLE)

### §2.1 Substrate v1 (#00a)

| # | Task | File | Verify |
|---|---|---|---|
| [ ] | Cross-seed reliability sweep (10+ seeds) | `scripts/terminus_cross_seed_sweep.py` | JSON artifact with table |
| [ ] | Non-linear scoring: max-based | `src/project_x/learning/temporal_trace.py` | `pytest tests/test_temporal_trace_bank.py` |
| [ ] | Non-linear scoring: softmax-gated | `src/project_x/learning/temporal_trace.py` | A/B vs linear |
| [ ] | Non-linear scoring: competitive-inhibition | `src/project_x/learning/temporal_trace.py` | A/B vs linear |
| [ ] | Scale repeats 3→5→7 + learning curve | `src/project_x/benchmarks/hidden_rule_actions.py` | Table: repeats vs pass_rate |
| [ ] | HebbianBank integration (audit loop) | `src/project_x/audit/log.py`, `src/project_x/learning/temporal_trace.py` | Test: rating moves action_bias |

### §2.2 Chat-loop bootstrap (#00b)

| # | Task | File | Verify |
|---|---|---|---|
| [ ] | Local REPL chat loop | `src/project_x/experiments/chat_loop.py` | 3-turn smoke test |
| [ ] | Discord-bot wrapper | `src/project_x/experiments/discord_chat_bot.py` | `#raphael-chat` response |
| [ ] | 10-prompt probe (self-authored, all 6 criteria) | `docs/artifacts/chat-probe-2026-05-13.md` | Transcripts + scoring |
| [ ] | Honest scoring against 6 criteria | `docs/artifacts/chat-probe-2026-05-13.md` | N/6 + evidence per test |

### §2.3 Docs sync (#00c)

| # | Task | File | Verify |
|---|---|---|---|
| [ ] | A_TO_Z_PLAN.md update | `docs/A_TO_Z_PLAN.md` | This file |
| [ ] | DO_THIS_NEXT.md rewrite | `docs/DO_THIS_NEXT.md` | Checkbox list + commands |
| [ ] | REPO_CONTROL.md rows | `docs/REPO_CONTROL.md` | New files justified |
| [ ] | Substrate v1 artifact | `docs/artifacts/terminus-learning-harness-v1-2026-05-13.md` | Cross-seed + non-linear + curve |
| [ ] | Chat probe artifact | `docs/artifacts/chat-probe-2026-05-13.md` | Transcripts + scoring |

### §2.4 Verdict (#00d)

| # | Task | File | Verify |
|---|---|---|---|
| [ ] | Learned-vs-hand-coded ratio paragraph | Inline in cycle close / `docs/artifacts/terminus-learning-harness-v1-2026-05-13.md` | Numeric estimate per axis |

---

## §3. v2/v3 SCOPE — THE CONVERSATIONAL CORPUS BLOCKER (EXPLICITLY NAMED)

### §3.1 v2: Conversational corpus + learned generator seed

**Blocker 1:** No curated conversational corpus exists. The 22k Tier-2 corpus is math/physics/poetry/philosophy — NOT chat. The 10-prompt probe transcripts from v1 are the FIRST conversational datapoints.

**Work:**
- [ ] Curate or collect conversational text (public-domain dialogues, transcripts, Socratic exchanges)
- [ ] Ingest via existing Tier-2 pipeline
- [ ] Formalize six chattability criteria into manual-grade harness (rubric scoring by builder)
- [ ] Begin training a learned response generator on the corpus + audit signal

### §3.2 v3: Learned generator replaces template composer

**Work:**
- [ ] Generator produces responses from learned policy, not template stitching
- [ ] Template composer retires to fallback / cold-start path
- [ ] Chattability criteria passing count target: ≥ 4/6

---

## §4. STANDING CONSTRAINTS

- NO pretrained transformer derivatives at any layer
- NO hand-coded knowledge in the final agent — only learning machinery
- Code-comment ratio rule: pure signal, load-bearing comments only
- Append-as-you-go writes (crash survival)
- Per-cycle git commit + push
- REPO_CONTROL.md: new non-doc files land with their row in the SAME commit
- M-PROJECTX-013 firewall: no claim without mechanical proof
- M-PROJECTX-014 firewall: no self-grading on subjective output

---

## §5. VERIFICATION COMMANDS

```bash
# Substrate tests
PYTHONPATH=src python3 -m pytest tests/test_temporal_trace_bank.py tests/test_hidden_rule_actions.py -q

# Benchmark audit
PYTHONPATH=src python3 gpt-codex/benchmark/run_audit.py

# Full suite
pytest -q

# Cross-seed sweep
PYTHONPATH=src python3 scripts/terminus_cross_seed_sweep.py

# Chat REPL smoke
PYTHONPATH=src python3 src/project_x/experiments/chat_loop.py --smoke

# Git status
git status --short
```

---

## §6. CHANGELOG

- 2026-05-13 — v1 plan written: substrate v1 + chat-loop bootstrap + v2/v3 corpus blocker stub

---

*The vector carries us. The plan contains us.*
