# WIRED-BRAIN: RPJ Brain v5

A 1.5M parameter neural agent demonstrating **emergent brain-like architecture** from reward-per-joule optimization.

## Results

Source of truth: run the reproducibility gate `./reproduce.sh` (tests + fixed-checkpoint evals).

Historical headline numbers (from a prior passing run):

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| K_eff (neuromodulator compression) | 5.19 | [2-6] | **PASS** |
| DoErr (causal reasoning accuracy) | 0.027 | ≤0.05 | **PASS** |
| CBR_B (bimodal compute allocation) | 0.578 | >0.555 | **PASS** |
| OD-NDT SR_novel (one-shot transfer) | 0.65 | ≥0.60 | **PASS** |

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

## Project Structure

```
src/
  core/
    rpj_brain.py      # Integrated RPJ Brain (1.5M params)
    substrate.py      # LN-GRU with sparse routing
    plasticity.py     # Fast weight adaptation
    byte_interface.py # Bytes-in/bytes-out encoding
    ppo_trainer.py    # PPO training loop
    sleep.py          # Offline consolidation
  benchmarks/
    multitask_ccb.py  # Multi-Task CCB (primary training env)
    ccb.py            # Single-task CCB
    od_ndt.py         # One-shot transfer harness
web/
  server.py           # FastAPI server (/chat, /ccb, /math)
  static/index.html   # Web UI
scripts/
  train_multitask_ccb.py  # Primary training script
  run_server.py           # Web server launcher
  run_training.py         # Training wrapper (Windows compatible)
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

Energy tracked via proxy:
```
E_step = kappa_F * FLOPs + kappa_M * BytesMoved
```

Target: P_bar ≤ 20W equivalent
