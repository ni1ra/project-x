"""Run Terminus Learning Harness v0 and emit a JSON evidence artifact."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from project_x.benchmarks.hidden_rule_actions import (
    ACTIONS,
    evaluate_policy,
    explore_train,
    make_hidden_rule_tasks,
    random_baseline,
)
from project_x.learning.temporal_trace import TemporalTraceBank


def _eval_to_dict(result) -> dict[str, object]:
    return {
        "split": result.split,
        "task_count": result.task_count,
        "pass_count": result.pass_count,
        "pass_rate": result.pass_rate,
        "action_accuracy": result.action_accuracy,
        "failure_cases": list(result.failures),
        "rollouts": [asdict(rollout) for rollout in result.rollouts],
    }


def run_demo(*, mode: str, seed: int) -> dict[str, object]:
    run_id = f"terminus-learning-harness-{int(time.time() * 1_000_000)}"
    tasks = make_hidden_rule_tasks(seed=seed)
    train_tasks = [task for task in tasks if task.split == "train"]
    heldout_tasks = [task for task in tasks if task.split == "heldout"]

    cold_bank = TemporalTraceBank()
    cold = evaluate_policy(cold_bank, tasks, split="heldout")
    random_result = random_baseline(tasks, split="heldout", seed=seed)

    learned_bank = TemporalTraceBank()
    train_stats = explore_train(learned_bank, tasks, seed=seed)
    learned = evaluate_policy(learned_bank, tasks, split="heldout")

    margin_vs_random = learned.pass_rate - random_result.pass_rate
    margin_vs_cold = learned.pass_rate - cold.pass_rate
    passed = (
        len(tasks) >= 10
        and len(heldout_tasks) >= 10
        and learned.pass_rate >= 0.70
        and margin_vs_random >= 0.20
        and margin_vs_cold >= 0.20
    )

    return {
        "run_id": run_id,
        "mode": mode,
        "seed": seed,
        "task_pack": {
            "total_task_count": len(tasks),
            "train_task_count": len(train_tasks),
            "heldout_task_count": len(heldout_tasks),
            "train_task_ids": [task.task_id for task in train_tasks],
            "heldout_task_ids": [task.task_id for task in heldout_tasks],
            "actions": list(ACTIONS),
            "steps_per_task": 2,
        },
        "action_budget": {
            "max_attempts_per_step": len(ACTIONS),
            "train_attempt_count": train_stats["attempt_count"],
        },
        "trace_count": train_stats["trace_count"],
        "reward_count": train_stats["reward_count"],
        "bank_entry_count": learned_bank.entry_count(),
        "train_stats": train_stats,
        "cold_trace_baseline": _eval_to_dict(cold),
        "random_baseline": _eval_to_dict(random_result),
        "learned_trace": _eval_to_dict(learned),
        "margins": {
            "pass_rate_vs_random": margin_vs_random,
            "pass_rate_vs_cold": margin_vs_cold,
            "action_accuracy_vs_random": learned.action_accuracy - random_result.action_accuracy,
            "action_accuracy_vs_cold": learned.action_accuracy - cold.action_accuracy,
        },
        "pass": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("test", "full"), default="test")
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--output", type=Path, help="Optional JSON artifact path.")
    args = parser.parse_args()

    result = run_demo(mode=args.mode, seed=args.seed)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
