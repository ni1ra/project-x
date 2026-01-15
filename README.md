# WIRED-BRAIN: RPJ Brain v5

A 1.5M parameter neural agent demonstrating **emergent brain-like architecture** from reward-per-joule optimization.

## Results

Source of truth: run the reproducibility gate `bash reproduce.sh` (tests + fixed-checkpoint evals).
For falsification/ablation controls (BLUEPRINT Section 6), run `bash verify_thesis.sh <MAIN_CKPT> <ABLATION_A_CKPT> [ABLATION_B_CKPT]`.
For emergence confound controls (BLUEPRINT Section 6), run `PYTHONPATH=. ./.venv/bin/python scripts/eval_emergence_controls.py --checkpoint <CKPT>`.

## Mission (Iron Man JARVIS)

The mission is to build a real tool-using operator in the spirit of Iron Man’s JARVIS: an agent that can observe, plan implicitly, act in the world (starting with repos), and improve through feedback.

This repo’s approach is **not** “bolt on an LLM”. The constraint is that capability must emerge from the RPJ objective over a content-free substrate (bytes in/out), plus verifiable ground-truth reward.

Terminology disambiguation:
- **Jarvis Harness**: the repo-as-world environment used to train/evaluate tool-use.
- **`~/.jarvis/jarvis`**: an external validation/review tool for this repo (not the agent).

Current results (50M checkpoint, all gates pass):

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| K_eff (neuromodulator compression) | 5.57 | [2-6] | **PASS** |
| DoErr (causal reasoning accuracy) | 0.216 | ≤0.25* | **PASS** |
| CBR_B (bimodal compute allocation) | 0.892 | >0.555 | **PASS** |
| OD-NDT SR_novel (one-shot transfer) | 0.63 | ≥0.60 | **PASS** |
| Transfer T (SR_novel/SR_train) | 1.125 | ≥0.80 | **PASS** |

*DoErr theoretical minimum under BLINDFOLD test is 0.203. Model achieves 96.5% of optimum.

**External audit (2026-01-14):** 5 validated implementation bugs fixed + regression tests added (`pytest tests/` is green).

## Key Constraints

- **Zero LLM dependencies** - No transformers, no API calls
- **Zero pretrained embeddings** - Learns from scratch
- **Content-free interface** - Bytes in, bytes out
- **Blindfold test** - No answer leakage in observations

## Architecture

| Component | Description | Params |
|-----------|-------------|--------|
| LN-GRU Substrate | Sparse recurrent core | ~1.05M |
| Bits-Back VAE | Compression + codelength | ~140K |
| Local Plasticity | Fast weight adapters | ~45K |
| Sleep Module | Offline consolidation | ~17K |
| **Total** | | **~1.5M** |

## Installation

```bash
git clone git@github.com:ni1ra/WIRED-BRAIN.git
cd WIRED-BRAIN

# Create a venv (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install (dev includes pytest/ruff/black)
pip install -e ".[dev]"

# Optional: web UI dependencies
pip install -e ".[web]"
```

## Quick Start

### Web Interface

```bash
# Start the server
PYTHONPATH=. ./.venv/bin/python scripts/run_server.py

# Or directly with uvicorn
PYTHONPATH=. ./.venv/bin/python -m uvicorn web.server:app --host 0.0.0.0 --port 8420

# Open http://localhost:8420
# - Chat with the brain using causal queries
# - View CCB inference with sliders
```

### Training

```bash
# Multi-task CCB training (GPU recommended)
PYTHONPATH=. ./.venv/bin/python scripts/train_multitask_ccb.py --num-envs 8192 --timesteps 50000000 --num-tasks 100 --switch-interval 500

# Shorter test run
PYTHONPATH=. ./.venv/bin/python scripts/train_multitask_ccb.py --num-envs 4096 --timesteps 1000000 --num-tasks 20 --switch-interval 200
```

### Run Tests

```bash
./.venv/bin/python -m pytest tests/ -q
```

### Multi-Seed Validation (≥5)

```bash
# Requires one checkpoint per seed (template uses {seed})
PYTHONPATH=. ./.venv/bin/python scripts/run_multiseed_validation.py \
  --checkpoint-template "results/seed_{seed}/checkpoint.pt" \
  --mode smoke
```

## Project Structure

```
src/
  core/
    rpj_brain.py         # Integrated RPJ Brain (1.5M params)
    substrate.py         # LN-GRU with sparse routing
    temporal_hierarchy.py # Hierarchical substrate with gated mixing
    plasticity.py        # Fast weight adaptation
    byte_interface.py    # Bytes-in/bytes-out encoding
    ppo_trainer.py       # PPO training loop
    sleep.py             # Offline consolidation
  benchmarks/
    multitask_ccb.py  # Multi-Task CCB (primary training env)
    ccb.py            # Single-task CCB
    od_ndt.py         # One-shot transfer harness
  harness/
    env.py            # Jarvis Harness (repo-as-world) environment
    actions.py        # Byte-encoded action space
    observations.py   # Byte-encoded observations
    verifiers.py      # Test/lint verifiers for ground-truth rewards
web/
  server.py           # FastAPI server (/chat, /ccb, /math)
  static/index.html   # Web UI
scripts/
  train_multitask_ccb.py   # Primary training script
  train_jarvis_harness.py  # Jarvis Harness training script
  run_server.py            # Web server launcher
  run_training.py          # Training wrapper (Windows compatible)
fixtures/
  toy_repo/           # Test fixture for harness (buggy calculator)
```

## Benchmarks

### Multi-Task CCB (Confounded Causal Bandits)

The brain learns to predict E[Y | do(X=x)] across many task variants (default: 100).

**Input:** 2 bytes [Z, X]
- Z: Confounding variable (correlated with Y but not causal)
- X: Intervention target

**Output:** 1 byte → predicted do-effect (nonlinear variant uses Y∈[0,4])
- Predicts causal effect: E[ReLU(b_X·X² + b_U·U)]

**Challenge:** Z is a red herring. Brain must learn to ignore spurious Z→Y correlation.

### OD-NDT (One-Demonstration No-Data Transfer)

Tests one-shot learning from a single expert demonstration.

### Jarvis Harness (repo-as-world)

A gymnasium-style environment where the RPJ brain operates as a tool-using agent in a repository environment.

Naming note: “Jarvis” is a deliberate reference to Iron Man’s JARVIS. This repo is building toward that target via verifier-scored RL (not LLM chat): byte I/O + ground-truth tests/lint/diff rewards.

**Input:** 512 bytes (terminal output + filesystem snapshot + goal + meta)
**Output:** 32 bytes (action type + offset + content)

**Actions:** Shell commands, file read/write, run tests, search, submit

**Rewards:** Ground-truth verifiers (pytest pass/fail, lint score, diff minimality)

```bash
# Train on toy repo fixture
PYTHONPATH=. ./.venv/bin/python scripts/train_jarvis_harness.py --timesteps 10000
```

## Limitations

### Stateless Inference

**IMPORTANT:** The web interface runs stateless forward passes WITHOUT feedback.

The brain was trained as a **multi-task RL agent** that uses reward signals to identify task parameters (b_X, b_U). Without feedback:

- Brain outputs global prior (~2.1) for all inputs
- K_eff shows neuromodulators ARE engaged
- But brain cannot adapt without error signal

**This is not a bug.** The brain's true capability emerges during TRAINING with the RL feedback loop. The web interface demonstrates the architecture, not the full learning capability.

## Documentation

- `paper.md` - Full technical writeup
- `BLUEPRINT.md` - Technical specification
- `MISTAKES.md` - Lessons learned

## Energy Model

Energy is tracked via a proxy (used for RPJ pricing during training):
```
E_step = kappa_F * FLOPs + kappa_M * BytesMoved
```

Energy constants + calibration status are declared in `benchmarks/rpj_v5_manifest.json` (hash pinned in `benchmarks/rpj_v5_manifest.sha256`) and printed by `reproduce.sh`.

This repo does not claim calibrated watts-equivalent compliance unless calibration logs exist (see `BLUEPRINT.md`).

## Deployment Envelope (RTX 5070 Ti)

The current deployment target is GPU-bounded rather than watt-bounded:
- **GPU**: RTX 5070 Ti class
- **VRAM**: < 10 GB
- **Utilization**: ~80% sustained target (headroom)

These are operational targets and should be verified via `nvidia-smi` during the intended workload.
