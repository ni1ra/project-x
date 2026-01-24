<!--
================================================================================
WIRED-BRAIN ROOT DOCUMENTATION STRUCTURE
================================================================================

ROOT FILES ARE STATIC - DO NOT ADD NEW FILES TO ROOT.
New content must go into existing docs or subdirectories (scripts/, src/, etc.)

Root Documents:
- README.md        : Project overview, quick start, current results
- BLUEPRINT.md     : Core thesis, architecture design, falsification criteria
- PLAN_TO_JARVIS.md: Phased roadmap to Jarvis (Phase 1-10 plans, future work)
- HANDOFF.md       : Context for continuing work in new Claude instances
- MISTAKES.md      : Failure log with patterns and lessons learned
- paper.md         : Academic write-up of methodology and results

Subdirectories:
- src/             : Source code (core/, harness/, utils/)
- scripts/         : Training, evaluation, and diagnostic scripts
- results/         : Checkpoints and evaluation outputs
- tests/           : Unit and integration tests

RULE: If you need to create a new doc, integrate it into an existing root doc
or place it in the appropriate subdirectory. Single files in root = violation.
================================================================================
-->

# WIRED-BRAIN: RPJ Brain v5

A 1.5M parameter neural agent demonstrating **emergent brain-like architecture** from reward-per-joule optimization.

## Mission: Iron Man's JARVIS

Build an autonomous AI coding agent that fixes bugs WITHOUT LLM API calls. The constraint is **zero transformer dependencies** - capability must emerge from the RPJ objective.

## Current Results

| Benchmark | Value | Target | Status |
|-----------|-------|--------|--------|
| **Synthetic EASY Bug Fixes** | 100% | >50% | **PASS** |
| **Real Repo Bug Fixes** | 0% | >50% | IN PROGRESS |
| K_eff (neuromodulator compression) | 5.57 | [2-6] | **PASS** |
| DoErr (causal reasoning) | 0.216 | ≤0.25 | **PASS** |
| CBR_B (compute allocation) | 0.892 | >0.555 | **PASS** |

**Jarvis Harness:** The brain can fix bugs in synthetic Python repos via bytes-in/bytes-out interface with pytest verification.

**Phase 9 Status:** Vocabulary expanded to 64 tokens (added Python keywords). Next: BC demos for real repo patterns.

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

## Quick Start

### Installation
```bash
git clone git@github.com:ni1ra/WIRED-BRAIN.git
cd WIRED-BRAIN
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Train Jarvis Harness
```bash
PYTHONPATH=. .venv/bin/python scripts/train_jarvis_harness.py \
    --mode v2 --difficulty easy --timesteps 0 \
    --bc-epochs 50 --bc-demos 1000 --bc-sequential \
    --v2-subprocess-heavy --gpu-low-util-patience-s 300
```

### Evaluate
```bash
PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_0.pt \
    --difficulty easy --num-tasks 30
```

### Run Tests
```bash
.venv/bin/python -m pytest tests/ -q
```

## Project Structure

```
src/
  core/
    rpj_brain.py         # Integrated RPJ Brain (1.5M params)
    substrate.py         # LN-GRU with sparse routing
    plasticity.py        # Fast weight adaptation
  harness/
    env.py               # Jarvis Harness environment
    actions.py           # Byte-encoded action space
    observations.py      # Byte-encoded observations
    expert_trajectories.py # BC demo generation
scripts/
  train_jarvis_harness.py  # Training script
  eval_jarvis_harness.py   # Evaluation script
```

## Documentation

| Doc | Purpose |
|-----|---------|
| BLUEPRINT.md | Core thesis, architecture, falsification criteria |
| PLAN_TO_JARVIS.md | Phased roadmap (Phase 8-12) |
| HANDOFF.md | Context for continuing work |
| MISTAKES.md | Failure patterns and lessons |
| paper.md | Academic write-up |

## Deployment Envelope

- **GPU**: RTX 5070 Ti class
- **VRAM**: < 10 GB
- **Utilization**: ~80% sustained

---

**The Intelligence Ceiling:** Using any LLM caps intelligence at that LLM's level. To build something smarter than Claude, the system CANNOT use Claude.
