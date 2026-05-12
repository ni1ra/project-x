"""Sandbox toy-task action-taking measurement.

Runs five deterministic toy tasks through the sandbox primitives.
Each task: agent (in this script's role for now; the substrate's
own decision-making to use these primitives is owed to a later cycle)
writes a Python program into the sandbox workdir, runs it via
`sandbox.agent_io.run_python`, reads the output, and the script
verifies the output matches the expected answer.

Result counts as forward motion on the sandboxed action-taking
Terminus axis: the primitives now exist, the round-trip works, and
the per-task pass/fail is mechanically measured.

Honest framing: the agent's *runtime* did not select these tasks.
The script supplies the program text. The forward step is the
write-run-read-verify infrastructure, not autonomous action.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sandbox.agent_io import (  # noqa: E402
    list_files,
    read_file,
    reset_workdir,
    run_python,
    snapshot,
    write_file,
)


RUN_ID = "claude-2026-05-12-sandbox-toy-tasks"


@dataclass
class ToyTask:
    name: str
    program: str
    expected_stdout_contains: str
    verify: Callable[[str], bool]


def _make_tasks() -> list[ToyTask]:
    return [
        ToyTask(
            name="factorial_5",
            program=(
                "def factorial(n):\n"
                "    return 1 if n <= 1 else n * factorial(n - 1)\n"
                "print(factorial(5))\n"
            ),
            expected_stdout_contains="120",
            verify=lambda out: out.strip() == "120",
        ),
        ToyTask(
            name="fibonacci_10",
            program=(
                "def fib(n):\n"
                "    a, b = 0, 1\n"
                "    for _ in range(n):\n"
                "        a, b = b, a + b\n"
                "    return a\n"
                "print(fib(10))\n"
            ),
            expected_stdout_contains="55",
            verify=lambda out: out.strip() == "55",
        ),
        ToyTask(
            name="string_round_trip",
            program=(
                "import json\n"
                "data = {'name': 'raphael', 'role': 'lord_of_knowledge'}\n"
                "encoded = json.dumps(data, sort_keys=True)\n"
                "decoded = json.loads(encoded)\n"
                "print(decoded['name'] + '/' + decoded['role'])\n"
            ),
            expected_stdout_contains="raphael/lord_of_knowledge",
            verify=lambda out: out.strip() == "raphael/lord_of_knowledge",
        ),
        ToyTask(
            name="csv_round_trip",
            program=(
                "import csv, io\n"
                "rows = [['n', 'sq'], [1, 1], [2, 4], [3, 9]]\n"
                "buf = io.StringIO()\n"
                "csv.writer(buf).writerows(rows)\n"
                "buf.seek(0)\n"
                "back = list(csv.reader(buf))\n"
                "total = sum(int(r[1]) for r in back[1:])\n"
                "print(total)\n"
            ),
            expected_stdout_contains="14",
            verify=lambda out: out.strip() == "14",
        ),
        ToyTask(
            name="quadratic_roots",
            program=(
                "import math\n"
                "a, b, c = 1, -5, 6\n"
                "disc = b * b - 4 * a * c\n"
                "r1 = (-b + math.sqrt(disc)) / (2 * a)\n"
                "r2 = (-b - math.sqrt(disc)) / (2 * a)\n"
                "roots = sorted([r1, r2])\n"
                "print(f'{roots[0]:.1f},{roots[1]:.1f}')\n"
            ),
            expected_stdout_contains="2.0,3.0",
            verify=lambda out: out.strip() == "2.0,3.0",
        ),
    ]


def run_demo(*, output: Path) -> dict[str, Any]:
    reset_workdir()
    snapshot("baseline_empty")

    tasks = _make_tasks()
    results: list[dict[str, Any]] = []

    for task in tasks:
        rel_path = f"{task.name}.py"
        write_file(rel_path, task.program)
        run_result = run_python(rel_path, timeout_seconds=5.0)
        passed = (
            not run_result.timed_out
            and run_result.exit_code == 0
            and task.verify(run_result.stdout)
        )
        results.append(
            {
                "name": task.name,
                "expected_substring": task.expected_stdout_contains,
                "stdout": run_result.stdout,
                "stderr": run_result.stderr,
                "exit_code": run_result.exit_code,
                "timed_out": run_result.timed_out,
                "pass": passed,
            }
        )

    artifacts = list_files()
    pass_count = sum(1 for r in results if r["pass"])
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "task_count": len(results),
        "pass_count": pass_count,
        "pass_fraction": pass_count / len(results) if results else 0.0,
        "artifacts": artifacts,
        "results": results,
        "interpretation": (
            "Sandbox infrastructure round-trip verified on five "
            "deterministic toy tasks. Forward motion on the sandboxed "
            "action-taking Terminus axis is the primitives + the "
            "write-run-read-verify loop; autonomous action-selection "
            "by the substrate's runtime is owed to a later cycle."
        ),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/project-x-sandbox-toy-tasks.json"),
    )
    args = parser.parse_args()
    result = run_demo(output=args.output)
    print(json.dumps(
        {
            "run_id": result["run_id"],
            "pass_count": result["pass_count"],
            "task_count": result["task_count"],
            "pass_fraction": result["pass_fraction"],
            "artifacts": result["artifacts"],
        },
        indent=2,
        sort_keys=True,
    ))
    return 0 if result["pass_count"] == result["task_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
