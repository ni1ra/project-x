# Do This Next - Project X v2

Generated: 2026-05-13

## Read First

1. `docs/MANIFESTO.md`
2. `docs/A_TO_Z_PLAN.md`
3. `docs/past_work/` only when historical context is needed

## Current Repo State

The repo has been intentionally reset.

Expected live files:

- `docs/MANIFESTO.md`
- `docs/A_TO_Z_PLAN.md`
- `docs/DO_THIS_NEXT.md`
- `docs/past_work/**`

Expected absent:

- `src/`
- `tests/`
- `scripts/`
- `gpt-codex/`
- `data/`
- `sandbox/`
- `docs/artifacts/`
- old README/pyproject/test scaffolds

Environment-owned empty busy directories such as `.agents/` or `.codex/` may remain on disk but are not project content.

## Immediate Instruction For The Next Coding Pass

Do not restore v1.

Build the smallest possible `organic-v0` that emits from learned internal state:

1. event log
2. tiny HDC/VSA memory spine
3. plasticity rule
4. learned connection state
5. generator that emits a full string from that state
6. tiny benchmark ladder with granular held-out tasks
7. result artifact with bad outputs included

No templates. No hardcoded answer routes. No solver in the answer path. No pretrained transformer.

## First Benchmark Requirement

The benchmark suite starts immediately, but it must measure organic learning, not polish.

Initial benchmark domains:

- learned memory recall
- hidden-rule learning
- causal-chain prediction
- minimal language expression
- abstention when unsupported

Each domain should have levels 0-3 at first:

- level 0: emits from learned state
- level 1: learns a toy rule
- level 2: handles held-out variants
- level 3: handles noise/adversarial wording

Later extend to math, physics, coding, games, philosophy, poetry, science, and beyond-human verified candidate discoveries.

## Hard Gates

Reject any implementation that:

- adds parser-dispatcher logic for benchmark answers
- adds fixed response text as the agent output
- scores itself on subjective quality
- hides bad outputs
- creates many files before one honest organism loop exists
- optimizes for "all tests pass" over organic learning

## Suggested First Command Sequence After Implementing v0

```bash
PYTHONPATH=src python3 scripts/train_organic_v0.py --mode test --out run/artifacts/organic-v0/train.json
PYTHONPATH=src python3 scripts/eval_organic_v0.py --mode test --out run/artifacts/organic-v0/eval.json
git status --short
```

If these files do not exist yet, that is expected. The next pass creates them.

## Close Criteria For The Next Pass

- Code exists only where needed for the minimal loop.
- Test/eval mode finishes in under 180 seconds.
- The first model emits output from learned state.
- At least one benchmark result is machine-readable.
- Failure cases are written down honestly.
- The final report explains what structural change would improve intelligence next.
