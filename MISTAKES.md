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

# MISTAKES.md — WIRED-BRAIN Failure Log

> Do not repeat recorded patterns of failure.
> Severity scales with count: +L10 per occurrence (Count 7 = L70, Count 10 = L100)

---

## Pattern Summary (TOP 5 BY COUNT)

| Pattern | Count | Severity | Core Lesson |
|---------|-------|----------|-------------|
| Train/Eval Mismatch | 10 | L100 | BC demos MUST match eval env exactly |
| Protocol Violations | 9 | L90 | FULLAUTO skills are mandatory, not optional |
| Data/Distribution Mismatch | 7 | L70 | Verify data distributions before training |
| GPU/Training Infra | 5 | L50 | GPU busy ≠ training works; verify output |
| Metric Deception | 4 | L40 | Inspect episodes, not just aggregate numbers |

---

## Critical Patterns (Detailed)

### 1. Train/Eval Mismatch [L100] - Count: 10

**Pattern:** Training observations/actions differ from eval, model learns wrong associations.

**Recent Instance (2026-01-23):**
- BC demos had different terminal format after WRITE_FOCUS than eval env
- Training: `pytest_prefix + "Syntax OK"`, Eval: just `"Syntax OK"`
- Result: 0% WRITE_FOCUS in eval (model learned wrong terminal pattern)
- Fix: Removed pytest_prefix from create_post_fix_observation()

**Variants:**
- Empty focus in BC, filled focus in eval (Count: 1)
- Single-step training, multi-step eval (Count: 2)
- Forced actions create different h_t than natural actions (Count: 2)
- Terminal format mismatch (Count: 3)
- Loss function omitting critical bytes (Count: 1)

**Rule:** `assert (bc_obs == eval_obs).all()` before training

---

### 2. Protocol Violations [L90] - Count: 9

**Pattern:** Skipping established protocols that exist to prevent exactly these problems.

**Recent Instance (2026-01-21):**
- Failed to invoke /improve-todo, /doc-guardian, /recon at FULLAUTO layers
- Rationalized "already know what to do"
- Result: GPU guard killed training during BC→PPO transition

**Variants:**
- Ralph Loop premature stop (Count: 2)
- Deep-debug skipped (Count: 2)
- Context recovery skipped after compaction (Count: 1)
- FULLAUTO skill invocations skipped (Count: 2)
- Root file placement violation (Count: 2)

**Rule:** Protocol skills are EXECUTION STEPS, not suggestions

---

### 3. Data/Distribution Mismatch [L70] - Count: 7

**Pattern:** Assumptions about data turn out wrong; model learns garbage.

**Recent Instance (2026-01-24):**
- BC demos were 65:35 imbalanced (data_pipeline:rest_api templates)
- Model memorized vocab_idx=10 (`>`) for data_pipeline
- For rest_api, defaulted to vocab_idx=0 (`:\n`) instead of vocab_idx=22 (`1`)
- Result: 63.3% solve rate (data_pipeline 100%, rest_api 0%)
- Fix: `balance_templates=True` cycles through templates evenly → 100% solve rate

**Variants:**
- Ground truth leaked in observation (Count: 1)
- Format encoding mismatch (Count: 1)
- Augmentation without label adjustment (Count: 1)
- Loss on invalid targets (Count: 1)
- Byte pair coupling (byte 25 set, byte 26 random) (Count: 1)
- Imbalanced training data (Count: 2)

**Rule:** Check BC dataset distribution BEFORE training. Balance templates explicitly.

---

### 4. GPU/Training Infrastructure [L50] - Count: 5

**Pattern:** GPU issues that waste time or corrupt training.

**Recent Instances:**
- GPU burns blocking real work (2026-01-21)
- PPO rollout collection falsely flagged by GPU guard (2026-01-21)
- Training on CPU instead of GPU (2026-01-24)

**Rule:**
- First output MUST appear within 30 seconds
- "GPU busy" ≠ "training works" - verify actual progress

---

### 5. Metric Deception [L40] - Count: 4

**Pattern:** Metrics show "success" that doesn't mean what we think.

**Instances:**
- "90% success" counting tasks with no bug to fix (free wins)
- Web interface outputting constant ~2.1 for all inputs
- High BC accuracy on imbalanced data (predicting majority class)

**Rule:** NEVER trust success rates without inspecting individual episodes

---

## Quick Reference Rules

| Rule | Source Pattern |
|------|----------------|
| `assert (bc_obs == eval_obs).all()` | Train/Eval Mismatch |
| Protocol skills = mandatory execution | Protocol Violations |
| Check distribution before training | Data Mismatch |
| First output in 30 seconds | GPU Infrastructure |
| Inspect episodes, not aggregates | Metric Deception |
| Read ENTIRE file before editing | Protocol Violations |
| No standalone files in root | Protocol Violations |
| VRAM < 10GB, GPU util > 50% | GPU Infrastructure |

---

## Entry Template

```markdown
### [YYYY-MM-DD] - [Component]
**What:** [Objective description]
**Root cause:** [Why it failed]
**Fix:** [What was done]
**Pattern:** [Link to pattern above + increment count]
```
