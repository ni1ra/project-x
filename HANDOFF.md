# HANDOFF: WIRED-BRAIN (JARVIS)

Generated: 2026-01-22 05:30

## 1. PROJECT CONTEXT

### What Is This?
JARVIS - An autonomous AI coding agent that fixes bugs in Python codebases, trained via BC pre-training + RL fine-tuning. Goal: Build Iron Man's JARVIS.

### What Problem Does It Solve?
Automated bug fixing without LLM API calls - a 20W-equivalent brain that learns to debug code through architectural emergence.

### Tech Stack
- Core: PyTorch 2.0+, Python 3.12
- Training: PPO, Behavioral Cloning
- Environment: Custom harness with synthetic bug generation
- Search: Optuna for architecture optimization

## 2. CURRENT STATUS

### Git State
```
Branch: main (uncommitted changes ready for PR)
Last commit: 65b204b feat(phase8): add structural plasticity infrastructure
Uncommitted changes: Paper rewrite reflecting Phase 8 action collapse reality
```

### Sprint 1 Results (COMPLETE - ALL TARGETS EXCEEDED)
| Difficulty | Target | Achieved | Status |
|------------|--------|----------|--------|
| TRIVIAL | >70% | **72%** | PASS |
| EASY | >50% | **52.2%** | PASS |
| MEDIUM | >75% | **100%** | PASS |
| HARD | >30% | **73.1%** | PASS (2.4x target) |

### Phase 8 Status - EVALUATION COMPLETE
- [x] HeterogeneousSubstrate integrated into RPJBrain
- [x] Optuna search found optimal 3-region architecture
- [x] Training completed (50,000 steps with --use-heterogeneous)
- [x] **EVALUATION RUN** - Result: ACTION COLLAPSE (0% solve rate)
- [x] Paper.md updated to reflect honest results

### Phase 8 Evaluation Results
```
Heterogeneous Model (Phase 8):
- HARD solve rate: 0% (0/26 eligible)
- Action: Same output every step (WRITE_FOCUS offset=0 vocab=8)
- Status: ACTION COLLAPSE - model memorized single pattern

Homogeneous Model (baseline):
- HARD solve rate: 73.1% (19/26 eligible)
- Action: Varied by task (actually fixes bugs)
- Status: PRODUCTION MODEL
```

## 3. WHAT WAS JUST COMPLETED (THIS SESSION)

### Phase 8 Evaluation
1. Ran heterogeneous evaluation: 0% solve rate (action collapse confirmed)
2. Ran homogeneous baseline: 73.1% solve rate (meets target)
3. Decision: Use homogeneous baseline as production model

### Paper.md Updated
1. **Abstract** - Updated Phase 8 claims to reflect action collapse
2. **Section 1.3** - Added honest acknowledgment
3. **Act XIII (13.4)** - Added "The Action Collapse" section with root cause analysis
4. **Act XIII (13.5)** - Added "Future Work" for Phase 8 fixes
5. **Epilogue Phase 3** - Updated to "Research Direction" status
6. **Appendix K.5** - Updated with full evaluation results table

## 4. NEXT STEPS

### Immediate
1. Log Phase 8 action collapse in MISTAKES.md
2. Create PR with all documentation updates
3. Merge to main

### Future Phase 8 Work (not blocking)
1. Entropy regularization during BC training
2. Larger heterogeneous models (width=512 total)
3. Direct RL training (skip BC entirely)
4. Mixed training: heterogeneous BC + homogeneous fine-tuning

## 5. KEY ARCHITECTURE DETAILS

### Production Model (Homogeneous)
```
Hidden dim: 512
Blocks: 64
Global channels: 16
Parameters: ~3.2M
HARD solve rate: 73.1%
```

### Research Direction (Heterogeneous - needs fixing)
```
Region 1: fast_perception - width=96, sparsity=0.74, FAST timescale
Region 2: slow_memory - width=224, sparsity=0.48, SLOW timescale
Region 3: fast_execution - width=64, sparsity=0.80, FAST timescale
Total hidden dim: 384
Parameters: ~2.1M (33% smaller)
HARD solve rate: 0% (action collapse)
```

## 6. COMMANDS

### Development
```bash
cd /mnt/c/Users/nira/Documents/Research/WIRED/WIRED-BRAIN
source .venv/bin/activate
```

### Run Evaluation (Homogeneous - Production)
```bash
PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_v2_100000.pt \
    --difficulty hard \
    --num-tasks 40
```

### Run Evaluation (Heterogeneous - Research)
```bash
PYTHONPATH=. .venv/bin/python scripts/eval_jarvis_harness.py \
    --checkpoint results/jarvis_harness_50000.pt \
    --use-heterogeneous \
    --difficulty hard \
    --num-tasks 40
```

## 7. SUCCESS CRITERIA

### Sprint 1 (COMPLETE)
- [x] TRIVIAL >= 70%: 72%
- [x] EASY >= 50%: 52.2%
- [x] MEDIUM >= 75%: 100%
- [x] HARD >= 30%: 73.1%

### Phase 8 (CONCEPT VALIDATED, IMPLEMENTATION NEEDS WORK)
- [x] Structure search completed (Optuna)
- [x] Optimal architecture found (3-region fast/slow/fast)
- [ ] HARD solve rate >= 72.5% with heterogeneous: **FAILED (0%)**
- [ ] Changes committed via PR: **PENDING**

## 8. QUICK START FOR NEW INSTANCE

```
Continue WIRED-BRAIN documentation updates.

CONTEXT:
- Sprint 1 is COMPLETE with 73.1% HARD solve rate (homogeneous model)
- Phase 8 heterogeneous training FAILED with action collapse
- Paper.md has been updated with honest results

NEXT ACTION:
1. Log Phase 8 failure in MISTAKES.md
2. Create PR with documentation changes
3. Merge to main

Production model: jarvis_harness_v2_100000.pt (homogeneous)
Research model: jarvis_harness_50000.pt (heterogeneous - broken)

Goal: Build Iron Man's JARVIS. Do not stop until complete.
```
