"""Cross-seed reliability sweep for the Terminus Learning Harness.

Characterizes pass-rate variance across N seeds. Emits JSON artifact with:
- per-seed train and held-out metrics
- summary statistics (mean, std, min, max)
- failure-mode classification

Usage:
    PYTHONPATH=src python3 scripts/terminus_cross_seed_sweep.py \
        --seeds 1729 42 0 1 99 123 456 789 1337 2024 31415 \
        --output /tmp/terminus-cross-seed-sweep.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from project_x.benchmarks.hidden_rule_actions import (
    ACTIONS,
    evaluate_policy,
    explore_train,
    make_hidden_rule_tasks,
    random_baseline,
)
from project_x.learning.temporal_trace import TemporalTraceBank


DEFAULT_SEEDS = (1729, 42, 0, 1, 99, 123, 456, 789, 1337, 2024, 31415)


def _classify_failure(rollout) -> str:
    """Tag a failure with its likely root cause."""
    pred = list(rollout.predicted_actions)
    exp = list(rollout.expected_actions)
    if len(pred) >= 1 and len(exp) >= 1 and pred[0] != exp[0]:
        return "first_step_wrong"
    if len(pred) >= 2 and len(exp) >= 2 and pred[0] == exp[0] and pred[1] != exp[1]:
        return "second_step_wrong"
    return "other"


def run_seed(seed: int, repeats: int = 3, mode: str = "linear") -> dict:
    """Train and evaluate on one seed. Returns metric dict."""
    tasks = make_hidden_rule_tasks(seed=seed, repeats=repeats)
    bank = TemporalTraceBank(scoring_mode=mode)
    train_stats = explore_train(bank, tasks, actions=ACTIONS, seed=seed)
    held_result = evaluate_policy(bank, tasks, split="heldout", actions=ACTIONS)
    random_result = random_baseline(tasks, split="heldout", actions=ACTIONS, seed=seed)

    failure_modes = {}
    for rollout in held_result.rollouts:
        if not rollout.passed:
            tag = _classify_failure(rollout)
            failure_modes[tag] = failure_modes.get(tag, 0) + 1

    return {
        "seed": seed,
        "repeats": repeats,
        "train": {
            "task_count": train_stats["train_task_count"],
            "attempt_count": train_stats["attempt_count"],
            "correct_attempt_count": train_stats["correct_attempt_count"],
            "trace_count": train_stats["trace_count"],
            "reward_count": train_stats["reward_count"],
        },
        "heldout": {
            "task_count": held_result.task_count,
            "pass_count": held_result.pass_count,
            "pass_rate": round(held_result.pass_rate, 4),
            "action_accuracy": round(held_result.action_accuracy, 4),
            "failure_modes": failure_modes,
            "failures": [
                {
                    "task_id": f["task_id"],
                    "expected": f["expected_actions"],
                    "predicted": f["predicted_actions"],
                }
                for f in held_result.failures
            ],
        },
        "random_baseline": {
            "pass_rate": round(random_result.pass_rate, 4),
            "action_accuracy": round(random_result.action_accuracy, 4),
        },
        "bank_entries": bank.entry_count(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(DEFAULT_SEEDS),
        help="Seeds to sweep",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=3,
        help="Training repeats per task family",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/tmp/terminus-cross-seed-sweep.json",
        help="JSON output path",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="linear",
        choices=("linear", "max", "softmax", "competitive"),
        help="Scoring mode to use in TemporalTraceBank",
    )
    args = parser.parse_args()

    results = []
    for seed in args.seeds:
        print(f"Sweeping seed={seed} ...", file=sys.stderr)
        result = run_seed(seed, repeats=args.repeats, mode=args.mode)
        results.append(result)
        print(
            f"  pass_rate={result['heldout']['pass_rate']:.2%} "
            f"action_acc={result['heldout']['action_accuracy']:.2%} "
            f"bank_entries={result['bank_entries']}",
            file=sys.stderr,
        )

    pass_rates = [r["heldout"]["pass_rate"] for r in results]
    action_accs = [r["heldout"]["action_accuracy"] for r in results]
    random_rates = [r["random_baseline"]["pass_rate"] for r in results]

    summary = {
        "mode": args.mode,
        "repeats": args.repeats,
        "seed_count": len(args.seeds),
        "pass_rate": {
            "mean": round(sum(pass_rates) / len(pass_rates), 4),
            "std": round(
                (sum((x - sum(pass_rates) / len(pass_rates)) ** 2 for x in pass_rates) / len(pass_rates)) ** 0.5,
                4,
            ),
            "min": round(min(pass_rates), 4),
            "max": round(max(pass_rates), 4),
        },
        "action_accuracy": {
            "mean": round(sum(action_accs) / len(action_accs), 4),
            "std": round(
                (sum((x - sum(action_accs) / len(action_accs)) ** 2 for x in action_accs) / len(action_accs)) ** 0.5,
                4,
            ),
            "min": round(min(action_accs), 4),
            "max": round(max(action_accs), 4),
        },
        "random_baseline_pass_rate": {
            "mean": round(sum(random_rates) / len(random_rates), 4),
        },
        "results": results,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
