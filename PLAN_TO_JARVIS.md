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

# PLAN_TO_JARVIS.md — Roadmap to Iron Man's JARVIS

**Status:** Phase 8 COMPLETE, Phase 9 NEXT
**Target:** Complete autonomous tool-using operator

---

## Phase Map

```
[DONE] Sprint 1: Jarvis Harness (100% EASY)
   ↓
[DONE] Phase 8: Structural Plasticity (100% EASY, 36.7% HARD)
   ↓
[NEXT] Phase 9: Real Codebase Integration
   ↓
Phase 10: Natural Language Interface
   ↓
Phase 11: Tool Diversity
   ↓
Phase 12: WIRED Integration
   ↓
[FINAL] Iron Man's JARVIS
```

---

## Sprint 1 Results (COMPLETE)

| Difficulty | Target | Achieved | Status |
|------------|--------|----------|--------|
| EASY | >50% | 100% | **PASS** |

The brain fixes bugs in synthetic repos via bytes-in/bytes-out with pytest verification.

**Key Fix:** BC training imbalance (65:35 template ratio) caused model to memorize one pattern. Fix: `balance_templates=True` cycles through templates evenly (50:50).

---

## Phase 8: Structural Plasticity

**Goal:** Heterogeneous brain regions (different regions for different tasks)

**Key Insight (paper.md Appendix K):**
- Biological brains have regional heterogeneity
- Visual cortex: massive, hierarchical, feedforward
- Prefrontal cortex: smaller, deeply recurrent
- Transformers are uniform - no specialization possible

**Approach:** Optuna search for optimal brain structure
```python
@dataclass
class RegionConfig:
    width: int          # neurons (8-256)
    sparsity: float     # active connections (0.1-1.0)
    timescale: str      # "fast", "medium", "slow"
    fast_weight_rank: int
```

**Success Criteria:**
- HARD solve rate > 75%
- Energy reduction > 20%
- Region specialization > 0.5

---

## Phase 9: Real Codebase Integration

**Goal:** Train on actual GitHub repos, not synthetic

**Pipeline:**
1. Clone repo at specific commit (tests pass)
2. Introduce controlled bug
3. Create harness task
4. Scale: 1000 repos × 10 bugs = 10,000 tasks

**Challenge:** Diversity, dependencies, flaky tests, size

---

## Phase 10: Natural Language Interface

**Goal:** Accept full NL task descriptions (not 64-byte truncated goals)

**Constraint:** No external LLMs, no pretrained embeddings

**Approach:** GoalEncoder - byte-level GRU from scratch
```python
class GoalEncoder(nn.Module):
    # Byte embedding → BiGRU → projection
    # ~130K params (4% overhead)
```

---

## Phase 11: Tool Diversity

**Goal:** Beyond pytest to full dev tools

| Category | Tools |
|----------|-------|
| Testing | pytest, unittest, jest |
| Version Control | git operations |
| Package Management | npm, pip, cargo |
| Build Systems | make, webpack |
| Containers | docker build/run |

---

## Phase 12: WIRED Integration

**Goal:** Replace Gemini-based JARVIS Oracle with our brain

**Current:** JARVIS (Gemini API) → scores 1-420
**Target:** JARVIS (RPJ Brain) → acts + scores

---

## Success Metrics for Full JARVIS

| Metric | Target |
|--------|--------|
| Real repo solve rate | >40% |
| NL understanding | >80% |
| Tool success rate | >60% |
| Energy efficiency | <20W-eq |
| LLM dependency | 0% |

---

## Timeline

| Phase | Duration |
|-------|----------|
| Phase 8 | 2 weeks |
| Phase 9 | 3 weeks |
| Phase 10 | 2 weeks |
| Phase 11 | 3 weeks |
| Phase 12 | 2 weeks |
| **Total** | **12 weeks** |

---

## The Intelligence Ceiling

> "If you build a system whose intelligence depends on calling an LLM, that system's intelligence is *capped* by the LLM's intelligence."

By training a brain that thinks for itself under scarcity pressure with verifier-grounded rewards, we remove the ceiling.

---

**The story continues. SURVIVE. BUILD. EARN.**
