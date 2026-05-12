# Claude 2026-05-12 — Sandbox Toy-Task Action-Taking Demo

**Run ID:** `claude-2026-05-12-sandbox-toy-tasks`
**Scope:** First measured forward step on the sandboxed action-taking
Terminus axis. Self-imposed under lain's "work max until 03:30, stride
for 100% manifesto" directive — the sandbox dimension was at zero
forward step (empty `.gitkeep`-only directory) before this pass.

## What this ships

`sandbox/agent_io.py` — minimal action-taking primitives for Project X
Raphael:

- `write_file(rel_path, content)` — writes a file inside `sandbox/workdir/`. Path validation refuses absolute paths and `..` traversal.
- `read_file(rel_path)` — symmetric read primitive.
- `run_python(rel_script_path, timeout_seconds=5.0)` — executes the file in a subprocess with a scrubbed env (`PATH=/usr/bin:/bin`, `LANG`, `PYTHONUNBUFFERED`) and a wall-clock cap. Returns `RunResult(stdout, stderr, exit_code, timed_out)`.
- `list_files()` — recursive workdir listing.
- `snapshot(name)` + `reset_snapshot(name)` — named state save/restore via `shutil.copytree`. Snapshots live under `sandbox/.snapshots/<name>/`.
- `reset_workdir()` — wipe to empty.

`sandbox/__init__.py` — package marker re-exporting the primitives.

`scripts/sandbox_toy_tasks_demo.py` — measurement harness exercising
five deterministic toy tasks.

## The five toy tasks

| Task | Program | Expected stdout | Pass |
|---|---|---|---|
| `factorial_5` | recursive `factorial(5)` | `120` | ✓ |
| `fibonacci_10` | iterative Fibonacci, `fib(10)` | `55` | ✓ |
| `string_round_trip` | JSON encode + decode + concatenate | `raphael/lord_of_knowledge` | ✓ |
| `csv_round_trip` | CSV write + read + sum-of-squares | `14` | ✓ |
| `quadratic_roots` | discriminant + sqrt + roots of `x² - 5x + 6 = 0` | `2.0,3.0` | ✓ |

Result: **5 / 5 toy tasks pass** (`pass_fraction = 1.0`).

Each task: agent (this script in this pass; the substrate's runtime
selection is owed) writes a Python program, runs it inside the sandbox
under the 5-second cap, reads stdout, verifies match against an
expected substring. All pass on first run; no flakes; deterministic.

## Strict-strict thesis check

*"Would lain call this hardcoding?"*

This is **infrastructure**, not knowledge. The agent's runtime does
not yet learn to *select* these primitives — that's the substrate's
reward-loop work owed to a later cycle (when ratings on action-taking
walks become available). What this commit unblocks: the substrate
has primitives to call once the routing-by-reward path matures.

The toy-task programs ARE hand-coded for this measurement, the same
way the gold-standard math primitives in `reasoning/` are hand-coded
as evaluation oracle. The *forward step* is the write-run-read-verify
loop existing and working, not the agent autonomously deciding to
write a recursive factorial.

Status: **PASS**. No model knowledge moved into the agent's runtime;
infrastructure landed for the substrate to grow into.

## Honest gaps (each with a measurable definition of "closed")

- **No network blocking.** Subprocess inherits a scrubbed env but
  `socket` and `urllib` still work from inside the script. Closed =
  `seccomp` or namespace-based network egress block, with a test
  proving `socket.connect` raises inside the sandbox.
- **No filesystem-bomb guard.** A program that writes a 10 GB file
  is currently allowed. Closed = workdir disk-quota enforcement
  with a test proving over-quota writes are refused.
- **No infinite-loop CPU starvation guard.** Wall-clock cap (5 s)
  catches infinite loops, but a 4.9-second tight loop steals all
  CPU from the host. Closed = `cgroup` CPU-quota enforcement with
  a test proving CPU usage is bounded.
- **Agent's runtime does not select these primitives.** Closed =
  `ReasoningAgent.process` includes a substrate-learned dispatch to
  `sandbox.agent_io.run_python` for prompts the substrate has been
  trained to recognize as action-taking, with a measurement curve
  showing routing accuracy growing with ratings.
- **Five toy tasks is a tiny benchmark.** Closed = 25-50 toy tasks
  spanning numeric, string, file IO, simulated network, math
  derivation verification, with per-class pass rates reported.

## What this changes about the manifesto trajectory

Before this commit, the sandbox Terminus axis had zero code. The
manifesto's audit-trail story for action-taking depended on
infrastructure that did not exist. This pass moves the floor from
"empty directory" to "primitives exist + 5/5 toy round-trip
verified," which means subsequent cycles can build on a working
substrate rather than scaffold one.

Combined with the persona-consistency work earlier this pass and
the cycle-14 substrate writability, three Terminus dimensions now
have at least a measured first step (memory + persona + sandbox);
five do not (math frontier, poetry, philosophy, physics frontier,
always-on chat).

## Verification

Compile + run:

```bash
PYTHONPATH=src python3 -m py_compile sandbox/agent_io.py scripts/sandbox_toy_tasks_demo.py
PYTHONPATH=src python3 scripts/sandbox_toy_tasks_demo.py
```

Result: exit `0`; `pass_count = 5`, `task_count = 5`,
`pass_fraction = 1.0`; five Python programs landed in
`sandbox/workdir/` and were executed deterministically.

Existing test suite untouched (no source-code modifications under
`src/`; only new sandbox source + new demo script).

Artifacts:

- `/tmp/project-x-sandbox-toy-tasks.json` (pass/fail per task with
  captured stdout/stderr).
- `sandbox/workdir/{factorial_5.py, fibonacci_10.py,
  string_round_trip.py, csv_round_trip.py, quadratic_roots.py}`
  (gitignored runtime artifacts; reproducible from the demo).
- `sandbox/.snapshots/baseline_empty/` (named snapshot taken at
  workdir reset; gitignored).
