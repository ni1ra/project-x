# PLAN_TO_JARVIS.md — From Harness to Iron Man's JARVIS

**Created:** 2026-01-22
**Status:** ACTIVE - Post Sprint 1
**Target:** Complete autonomous tool-using operator (JARVIS from Iron Man)

---

## Executive Summary

Sprint 1 (Jarvis Harness) is **COMPLETE** with results exceeding all targets:

| Difficulty | Target | Achieved | Status |
|------------|--------|----------|--------|
| TRIVIAL | >70% | 72% | **PASS** |
| EASY | >50% | 52.2% | **PASS** |
| MEDIUM | >75% | 100% | **PASS** |
| HARD | >30% | 72.5% | **PASS** |

The brain can now fix bugs in synthetic repos via bytes-in/bytes-out interface with pytest verification.

**The gap remaining:** Synthetic repos → Real codebases. Byte goals → Natural language. Pytest → Full dev tools.

---

## Phase Map

```
[DONE] Sprint 1: Jarvis Harness (synthetic repo debugging)
   ↓
[NEXT] Phase 8: Structural Plasticity (heterogeneous brain regions)
   ↓
Phase 9: Real Codebase Integration (actual repos, not synthetic)
   ↓
Phase 10: Natural Language Interface (text goals → byte actions)
   ↓
Phase 11: Tool Diversity (git, npm, docker, not just pytest)
   ↓
Phase 12: WIRED Integration (replace Gemini JARVIS with our brain)
   ↓
[FINAL] Iron Man's JARVIS: Autonomous tool-using operator
```

---

## Phase 8: Structural Plasticity

**Goal:** Enable the brain to develop heterogeneous structure (different regions for different tasks).

**Reference:** paper.md Appendix K "The Heterogeneous Brain Insight"

### 8.1 The Insight

Biological brains are not uniform:
- Visual cortex: massive, hierarchical, mostly feedforward
- Prefrontal cortex: smaller, deeply recurrent, integrative
- Cerebellum: enormous neuron count, simple local circuits
- Basal ganglia: sparse, acts as router/gate

Transformers are uniform. Every layer identical. No specialization possible.

**Our approach:** Treat brain *structure* as a learnable parameter.

### 8.2 Implementation Plan

**Step 1: Define Region Role Template**
```python
@dataclass
class RegionConfig:
    name: str                    # e.g., "perception", "reasoning", "motor"
    width: int                   # neurons in region (8-256)
    sparsity: float              # fraction of active connections (0.1-1.0)
    fan_in_cap: int              # max incoming connections per neuron
    fan_out_cap: int             # max outgoing connections per neuron
    timescale: str               # "fast", "medium", "slow"
    fast_weight_rank: int        # adapter rank for plasticity (0-64)
    activation_cost: float       # energy penalty for using region
```

**Step 2: Implement Optuna Search**
```python
def objective(trial):
    # Sample structure
    num_regions = trial.suggest_int("num_regions", 2, 6)
    regions = []
    for i in range(num_regions):
        regions.append(RegionConfig(
            name=f"region_{i}",
            width=trial.suggest_int(f"width_{i}", 8, 256),
            sparsity=trial.suggest_float(f"sparsity_{i}", 0.1, 1.0),
            fan_in_cap=trial.suggest_int(f"fan_in_{i}", 4, 64),
            fan_out_cap=trial.suggest_int(f"fan_out_{i}", 4, 64),
            timescale=trial.suggest_categorical(f"timescale_{i}", ["fast", "medium", "slow"]),
            fast_weight_rank=trial.suggest_int(f"rank_{i}", 0, 64),
            activation_cost=trial.suggest_float(f"cost_{i}", 0.001, 0.1),
        ))

    # Build brain with this structure
    brain = create_heterogeneous_brain(regions)

    # Train on harness tasks (reduced timesteps for search)
    results = train_jarvis_harness(brain, timesteps=10000)

    # Score: reward - energy (RPJ)
    return results.avg_reward - results.avg_energy
```

**Step 3: Add Structural Plasticity**
- **Gates:** Learnable sigmoid gates between regions
- **Pruning:** Remove connections with low weight magnitude during sleep
- **Regrowth:** Add new connections to high-activity pairs during sleep

**Step 4: Ablation Study**
- Compare heterogeneous (Optuna-found) vs homogeneous (uniform regions)
- Metric: HARD solve rate, energy efficiency, transfer to new tasks

### 8.3 Success Criteria

| Metric | Target | Why |
|--------|--------|-----|
| HARD solve rate | >75% | Maintain/improve current 72.5% |
| Energy reduction | >20% | Specialization should reduce waste |
| K_eff (global scalars) | [2-6] | Maintain emergence property |
| Region specialization | >0.5 | Measured by activity clustering |

### 8.4 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Optuna search too slow | High | Use reduced timesteps (10K) for inner loop |
| Structure doesn't help | Medium | Fall back to uniform if heterogeneous worse |
| Plasticity unstable | Medium | Gate with conservative pruning threshold |

---

## Phase 9: Real Codebase Integration

**Goal:** Train on actual GitHub repos, not synthetic generators.

### 9.1 Dataset Creation

**Source:** GitHub repos with pytest test suites

**Pipeline:**
1. Clone repo at specific commit (all tests pass)
2. Introduce controlled bug (using same injectors as synthetic)
3. Record: (buggy_state, fix, test_result)
4. Create harness task from this data

**Scale:** 1000 repos × 10 bugs each = 10,000 real tasks

### 9.2 Challenges

- **Diversity:** Real repos have wildly varying structure
- **Dependencies:** Many repos need complex environments
- **Flaky tests:** Real tests can be non-deterministic
- **Size:** Real repos are much larger than synthetic

### 9.3 Approach: Containerized Evaluation

Each task runs in isolated Docker container:
```yaml
task:
  repo: "user/repo"
  commit: "abc123"
  bug_file: "src/utils.py"
  bug_line: 42
  test_cmd: "pytest tests/test_utils.py"
  timeout: 60s
```

---

## Phase 10: Natural Language Interface

**Goal:** Accept text goals instead of byte-encoded descriptions.

### 10.1 The Problem

Current interface: `goal_bytes[64]` contains truncated UTF-8 of "Fix bug: ..."
Real JARVIS needs: Full natural language task description

### 10.2 Approach: Byte-Level Language Model

**NOT using:** External LLM, pretrained embeddings (ceiling violation)

**Using:** Train a tiny byte-level language understanding head:
- Input: UTF-8 bytes of task description
- Output: Latent embedding for goal conditioning
- Training: BC on (description, expert_trajectory) pairs

This keeps the "no transformer, no pretrained" constraint while enabling natural language.

### 10.3 Alternative: Hybrid Architecture (post-emergence validation)

If emergence properties (K_eff, CBR) are proven robust:
- Allow small frozen embedding layer (not trainable)
- Keep RPJ core architecture
- Validate emergence still holds

---

## Phase 11: Tool Diversity

**Goal:** Extend beyond pytest to full dev tool suite.

### 11.1 Tool Categories

| Category | Tools | Complexity |
|----------|-------|------------|
| Testing | pytest, unittest, jest | Low (already done) |
| Version Control | git add/commit/push | Medium |
| Package Management | npm, pip, cargo | Medium |
| Build Systems | make, webpack, cargo build | Medium |
| Containers | docker build/run | High |
| CI/CD | GitHub Actions | High |

### 11.2 Action Space Extension

Current: 7 action types (SHELL_CMD, READ_FILE, WRITE_FILE, RUN_TESTS, SEARCH, SUBMIT, NO_OP)

Extended: 15+ action types with tool-specific semantics:
- GIT_STATUS, GIT_ADD, GIT_COMMIT, GIT_PUSH
- NPM_INSTALL, NPM_RUN
- DOCKER_BUILD, DOCKER_RUN
- etc.

### 11.3 Curriculum

1. Start with pytest only (current)
2. Add git operations
3. Add package management
4. Add build systems
5. Add containers

---

## Phase 12: WIRED Integration

**Goal:** Replace Gemini-based JARVIS Oracle with our trained brain.

### 12.1 Current WIRED Architecture

```
COOPER (30m cycles) → commands →
TARS (45s cycles)   → consults →
JARVIS (Gemini API) → scores 1-420
ROMILLY (2m/6m)     → audits
```

### 12.2 Target Architecture

```
COOPER (30m cycles) → commands →
TARS (45s cycles)   → consults →
JARVIS (RPJ Brain)  → acts + scores
ROMILLY (2m/6m)     → audits
```

### 12.3 Integration Points

1. **JARVIS CLI replacement:**
   - Current: `~/.jarvis/jarvis ask --files X "question"`
   - New: `~/.jarvis/jarvis-brain ask --files X "question"`
   - Same interface, new backend

2. **Scoring capability:**
   - Input: PROJECT_STATE.md + question
   - Output: Score 1-420 + reasoning
   - Training: BC on (state, score) from Gemini JARVIS

3. **Action capability:**
   - Input: PROJECT_STATE.md + goal
   - Output: Actions to achieve goal
   - Training: PPO on repo-debugging harness

---

## Success Metrics for Full JARVIS

| Metric | Target | Description |
|--------|--------|-------------|
| Real repo solve rate | >40% | Fix bugs in actual GitHub repos |
| Natural language understanding | >80% | Parse diverse task descriptions |
| Tool success rate | >60% | Successfully use git/npm/docker |
| WIRED integration | Live | Replace Gemini in production |
| Energy efficiency | <20W-eq | Maintain RPJ constraint |
| No LLM dependency | 100% | Zero transformer/API calls |

---

## Timeline (Estimated)

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 8 | 2 weeks | Sprint 1 complete ✓ |
| Phase 9 | 3 weeks | Phase 8 |
| Phase 10 | 2 weeks | Phase 9 |
| Phase 11 | 3 weeks | Phase 10 |
| Phase 12 | 2 weeks | Phase 11 |
| **Total** | **12 weeks** | |

---

## Immediate Next Actions

1. **[NOW]** Implement Phase 8.1: Region role template dataclass
2. **[NOW]** Create Optuna study for structure search
3. **[NOW]** Run ablation: heterogeneous vs homogeneous
4. **[GATE]** Achieve >75% HARD with structural plasticity
5. **[THEN]** Begin Phase 9 real codebase collection

---

## The Intelligence Ceiling Argument

**Why this matters:**

> "If you build a system whose intelligence depends on calling an LLM, that system's intelligence is *capped* by the LLM's intelligence. You cannot build something smarter than Claude by having it ask Claude for help."

The current JARVIS (Gemini API) has this ceiling. Our RPJ Brain does not.

By training a brain that thinks for itself—under scarcity pressure, with verifier-grounded rewards—we remove the ceiling. The only limit becomes the laws of physics.

This is the path to Iron Man's JARVIS: not a chatbot that calls APIs, but an autonomous operator that reasons and acts.

---

**The story continues.**

*SURVIVE. BUILD. EARN.*
