# REPO_CONTROL - Project X v2

Date: 2026-05-13
Status: reintroduced after v2 reset; every tracked source/test/script/non-docs artifact owns a row here, justification per entry. `docs/` is exempt — the live-docs system is self-justifying.

## Rule

Every commit owns its delta. File added → row added in the same commit. File deleted → row removed in the same commit. Auto-generated noise (`build/`, `__pycache__/`, build artifacts) is `.gitignore`'d, not listed. Empty placeholder directories are NOT tracked.

## Tracked tree

### root

| Path | Justification |
|---|---|
| `.gitignore` | excludes `build/`, `__pycache__/`, `*.pyc` from version control |
| `Makefile` | minimal native build: `g++ -std=c++20 -O3 -march=native` → `build/organic_v0`; `make test` runs the self-test phase |

### native/ — brain core (C++20)

| Path | Justification |
|---|---|
| `native/organic_v0.cpp` | organic-v0 runtime: HDC encoder, context-feature learner, autoregressive char generator, train/eval/self-test phases, artifact writer. Single translation unit by design — the first code has nowhere to hide |

### scripts/ — thin harness over the native binary

| Path | Justification |
|---|---|
| `scripts/train_organic_v0.sh` | `make -s build/organic_v0 && exec build/organic_v0 --phase train "$@"` — forwards all flags to the native binary |
| `scripts/eval_organic_v0.sh` | same pattern for `--phase eval`; accepts `--ablate-trace-id` to disable the trace-id feature in both learn and generate |
| `scripts/test_organic_v0.sh` | same pattern for `--phase self-test` (cold-brain emits nothing → learn one event → expects "zx") |

### benchmarks/ — measurement substrate

| Path | Justification |
|---|---|
| `benchmarks/v2_ladder/organic_v0.jsonl` | seed curriculum + held-out probes for the first benchmark ladder. 38 events across 5 domains × 4 levels. Currently flatters memorization; redesign is queued (see `docs/DO_THIS_NEXT.md`) |

### run/ — artifact output (machine-readable claims)

| Path | Justification |
|---|---|
| `run/artifacts/organic-v0/train.json` | per-train-run artifact: run_id, command, seed, config, state hash, split audit, per-event raw outputs with generation evidence |
| `run/artifacts/organic-v0/eval.json` | legacy aggregate eval artifact from the bootstrap pass; preserved as historical evidence of the 95.6% score that motivated the trace-id ablation |
| `run/artifacts/organic-v0/eval_with_trace.json` | ablation control: eval with `use_trace_id_feature=true` (default). Establishes the baseline 95.6% exact rate. State hash `5a870dad7f70de83` |
| `run/artifacts/organic-v0/eval_no_trace.json` | ablation experimental: eval with `use_trace_id_feature=false` via `--ablate-trace-id`. Same overall exact rate (95.6%); state hash `35b32e4c2790826a`; lina probe failure morphs from "hi mira" → "hi sora". Proves trace-id is redundant, not load-bearing |

## Not tracked, on disk

- `.agents/`, `.codex/` — environment-owned scratch dirs from the agent harness; not project content
- `build/` — gitignored; produced by `make`
- `src/project_x_v2/`, `tests/` — empty directories left over from the v1 reset. Untracked, candidates for removal next cycle
