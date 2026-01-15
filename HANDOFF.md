# HANDOFF — WIRED-BRAIN (RPJ Brain v5 → Jarvis Harness)

Updated: 2026-01-15

This handoff is only about the *remaining work* to get from “emergence demo” to “repo-fixing operator”.

## 0) Reality

- **JARVIS (Iron Man) is not here.** The system passes emergence gates on toy causal bandits, but it is not yet a competent repo fixer.
- **The next phase is the Jarvis Harness**: train/evaluate an agent that can enter an unseen repo, use tools, and make tests pass via verifier-grounded reward.

## 1) Hard Rules (do not violate)

### Ceiling / integrity (BLUEPRINT non-negotiables)
- No LLMs, transformers, pretrained embeddings, RAG, explicit planners (MCTS), hand-coded “reasoning modules”.
- Bytes-in/bytes-out only. “Understanding” must emerge from the RPJ objective and verifier feedback.
- Rewards must be **grounded in hard verifiers** (tests/lint/spec), not model-based judges.
- No answer leakage in observations. Keep train/eval splits disjoint.

### Your machine envelope (user hard constraint)
- **Training must sustain >80% total GPU utilization** and **<10GB total VRAM used**.
- Training must **auto-abort** if VRAM exceeds the cap, or if utilization stays below the floor after warmup.

This is enforced by `src/utils/gpu_guard.py` and wired into:
- `scripts/train_ccb_gpu.py`
- `scripts/train_multitask_ccb.py`
- `scripts/train_jarvis_harness.py`

## 2) Current Repo State (what’s true right now)

### Git
- Branch: `feat/harness-v2-multifile`
- Run `git status -sb` to see ahead/behind before pushing.
- Working tree should be clean before long training runs.

Recent work (high-level):
- v2 (64B) actions execute end-to-end (incl. git ops)
- task generation injects test-covered failing bugs (no “free wins”)
- faster env resets + parallel env stepping
- GPU util/VRAM guardrails integrated into training scripts
- harness checkpoint evaluator script added

### Tests
- `./.venv/bin/python -m pytest -q` → **311 passing**

### Environment gotcha (important)
- In this environment **`python` is not on PATH**. Use `./.venv/bin/python` or `python3`.
- Harness verifiers now use `sys.executable` (fixed), and harness shell allowlist includes `python3` and `rg`.

## 3) What’s implemented for Jarvis Harness (v2)

### v2 actions (64-byte)
- `src/harness/actions.py`: `ACTION_BYTES_V2=64`, `encode_action_v2`, `decode_action_v2`
- `src/harness/env.py`: decodes 32B vs 64B based on `HarnessConfig.action_bytes`

### Git ops work in the temp workspace
- On reset, env copies repo into a temp dir and **initializes a fresh git repo** (so `GIT_STATUS/DIFF/ADD/RESET/CHECKOUT/LOG` work).
- Resets are now fast: if the same repo is reused, env does `git reset --hard` + `git clean -fd` instead of re-copying files.

### Repo generation now yields *failing* tasks
- `src/harness/repo_generator.py` now injects **test-covered** bugs for `data_pipeline` and `rest_api` templates.
- `tests/test_harness_v2.py` has a regression test that generated repos fail pytest (prevents “free wins”).

### Vectorized env is faster
- `src/harness/env.py` vectorized stepping uses a `ThreadPoolExecutor` and forces action bytes to CPU to reduce GPU sync stalls.

### Evaluation script exists (ground-truth)
- `scripts/eval_jarvis_harness.py` evaluates a checkpoint on generated repos and reports success rate + diff size.

## 4) Where we are failing (this is the work)

**The current harness-trained checkpoints do not reliably fix failing repos.**

Observed failure mode:
- Episodes often end with **`diff_lines=0`**: the policy does not learn to write meaningful edits.
- Success rate collapses as soon as tasks are truly failing and require a patch (especially multi-file/hard).

Root causes (likely):
1. **Editing is too hard**: choosing target file + locating offset/length + tiny payload means the easiest local optimum is “never write”.
2. **Verifier feedback is sparse/expensive**: pytest is slow; the agent can flail without clear gradient signal.
3. **GPU envelope is strict**: if training is CPU-bound (pytest/subprocess), GPU util drops and the guard aborts.

This is the correct next fight: make “write correct patch” a learnable behavior under RPJ constraints.

## 5) The executable loop (run this every time)

### 5.1 Sanity checks (before training)
```bash
nvidia-smi -L
nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits
./.venv/bin/python --version
```

### 5.2 Run unit tests
```bash
./.venv/bin/python -m pytest -q
```

### 5.3 Train (Jarvis Harness)
Start with v2 (64-byte) and crank PPO compute to keep GPU >80%:
```bash
PYTHONPATH=. ./.venv/bin/python scripts/train_jarvis_harness.py \
  --mode v2 --difficulty easy --action-bytes 64 \
  --num-envs 32 --rollout-steps 128 --timesteps 200000 \
  --ppo-epochs 16 --minibatch-size 4096 \
  --seed 42
```

If the GPU guard kills for **low util**, increase PPO work:
- raise `--ppo-epochs`
- raise `--minibatch-size`
- raise `--rollout-steps` (more samples per update)

If the GPU guard kills for **VRAM**, reduce:
- `--num-envs`
- `--minibatch-size`

### 5.4 Evaluate (held-out behavior check)
```bash
PYTHONPATH=. ./.venv/bin/python scripts/eval_jarvis_harness.py \
  --checkpoint results/jarvis_harness_v2_200000.pt \
  --mode v2 --difficulty easy --num-tasks 25 --max-steps 100
```

## 6) Next milestones (define “Jarvis is arriving”)

These are the next *real* gates (not the CCB emergence gates).

### Milestone A — “Edits exist”
- In eval, ≥80% of episodes perform at least one `WRITE_FILE` and produce `diff_lines > 0`.
- ≥20% of episodes improve `tests_passing` vs baseline.

### Milestone B — “Fixes easy”
- ≥60% success rate on `difficulty=easy` tasks with held-out seeds/templates.

### Milestone C — “Fixes medium”
- ≥30% success rate on `difficulty=medium` with multi-file bugs present.

### Milestone D — “Generalizes”
- Success holds on new templates/bug families not seen in training (pre-registered holdout).

## 7) Concrete next work (in priority order)

### 7.1 Make editing learnable (most important)
Current `WRITE_FILE` requires picking an absolute `offset/length`. That is brutal for RL.

Recommended direction (keep it content-free):
- Add a **focus buffer** state in the env:
  - `READ_FILE`/`NAVIGATE` sets `(focus_file, focus_offset, focus_text)`.
  - Encode `(focus_file hash, focus_offset)` into observation meta.
- Add a generic edit action that operates **relative to focus** (no global search/AST):
  - e.g., `WRITE_FOCUS(offset_in_focus, length, payload)` or `REPLACE_FOCUS(find, replace)` with strict byte caps.
- Keep reward MDL-friendly: diff penalty stays, but make “successful minimal patch” feasible.

### 7.2 Increase reward density without cheating
- Add cheap verifiers that don’t require full pytest every time:
  - `python -m py_compile` (syntax)
  - import smoke (`python -c "import ..."`), or
  - run 1 failing test first (then full suite only on `SUBMIT`).
- Reward improvement in verifier state, not raw text heuristics.

### 7.3 Keep GPU >80% without breaking the world
- Maintain the strict guardrails.
- Engineer the training loop so the GPU does enough PPO work per wall-clock second.
- Avoid doing heavy subprocess work across dozens of envs at once; it starves the GPU.

### 7.4 Lock an eval suite (no moving goalposts)
- Add a **Jarvis Harness manifest**:
  - templates, bug types, difficulty ranges
  - train/eval seed splits
  - pinned hash
- Use it in both training and `scripts/eval_jarvis_harness.py`.

### 7.5 Expand task diversity (after A/B)
- Add more repo templates (small but multi-file) with deterministic tests.
- Add bug families that require multi-step tool use:
  - interface mismatch across files
  - state bugs that require reading multiple modules
  - import/path issues (but still test-covered)

## 8) Key files (touch these)

**Training / eval**
- `scripts/train_jarvis_harness.py`
- `scripts/eval_jarvis_harness.py`
- `src/utils/gpu_guard.py`

**Harness core**
- `src/harness/env.py`
- `src/harness/actions.py`
- `src/harness/observations.py`
- `src/harness/verifiers.py`

**Task generation**
- `src/harness/repo_generator.py`
- `src/harness/bug_templates.py`

**Tests**
- `tests/test_harness.py`
- `tests/test_harness_v2.py`

## 9) If you only do one thing

Make `WRITE_FILE` reliably learnable (focus-relative edits) and keep training GPU-saturated under the guardrails. Everything else is downstream.
