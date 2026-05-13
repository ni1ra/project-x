"""Hidden-rule action benchmark for the Terminus Learning Harness v0.

The task pack tests whether a domain-neutral temporal trace learner can infer
action choice from rewarded experience. The rules are local to the benchmark
environment; the learner only sees feature atoms, actions, results, and rewards.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Literal, Sequence

from project_x.learning.temporal_trace import ExperienceTrace, TemporalTraceBank, TraceEvent


ACTIONS: tuple[str, ...] = ("act_a", "act_b", "act_c", "act_d")
Split = Literal["train", "heldout"]

_FIRST_ACTION_RULES: dict[str, dict[str, str]] = {
    "color": {
        "red": "act_a",
        "blue": "act_b",
        "green": "act_c",
        "yellow": "act_d",
    },
    "shape": {
        "circle": "act_b",
        "square": "act_c",
        "triangle": "act_d",
        "star": "act_a",
    },
    "texture": {
        "smooth": "act_c",
        "rough": "act_d",
        "striped": "act_a",
        "dotted": "act_b",
    },
}

_SECOND_ACTION_RULE: dict[str, str] = {
    "act_a": "act_c",
    "act_b": "act_d",
    "act_c": "act_a",
    "act_d": "act_b",
}

_VALUES_BY_FAMILY = {
    family: tuple(mapping.keys())
    for family, mapping in _FIRST_ACTION_RULES.items()
}


@dataclass(frozen=True)
class HiddenRuleStep:
    """One hidden-rule action step with a machine-verifiable expected action."""

    observation: tuple[str, ...]
    expected_action: str
    result_on_success: tuple[str, ...]

    def verify(self, action: str) -> bool:
        return action == self.expected_action


@dataclass(frozen=True)
class HiddenRuleTask:
    """Two-step hidden-rule task.

    Step 1 rewards feature -> action learning. Step 2 rewards ordered temporal
    learning: previous action + previous result feature -> next action.
    """

    task_id: str
    split: Split
    relevant_family: str
    relevant_value: str
    steps: tuple[HiddenRuleStep, ...]

    def oracle_trace(self) -> ExperienceTrace:
        events = []
        for idx, step in enumerate(self.steps):
            events.append(
                TraceEvent.build(
                    observation=step.observation,
                    action=step.expected_action,
                    result=step.result_on_success,
                    reward=1.0,
                    task_id=self.task_id,
                    episode_id=self.task_id,
                    step_index=idx,
                )
            )
        return ExperienceTrace(trace_id=f"oracle:{self.task_id}", events=tuple(events))


@dataclass(frozen=True)
class RolloutResult:
    task_id: str
    split: Split
    expected_actions: tuple[str, ...]
    predicted_actions: tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class EvaluationResult:
    split: str
    task_count: int
    pass_count: int
    pass_rate: float
    action_accuracy: float
    failures: tuple[dict[str, object], ...]
    rollouts: tuple[RolloutResult, ...]


def _other_family_value(family: str, task_index: int, seed: int) -> list[str]:
    """Pick random distractor values from other families, reproducibly."""
    rng = random.Random(task_index + seed)
    features: list[str] = []
    for other_family in _VALUES_BY_FAMILY:
        if other_family == family:
            continue
        values = _VALUES_BY_FAMILY[other_family]
        value = rng.choice(values)
        features.append(f"{other_family}:{value}")
    return features


def _make_task(
    *,
    task_id: str,
    split: Split,
    family: str,
    value: str,
    offset: int,
    task_index: int,
    seed: int,
) -> HiddenRuleTask:
    first_action = _FIRST_ACTION_RULES[family][value]
    result_feature = f"result:{first_action}"
    second_action = _SECOND_ACTION_RULE[first_action]
    first_observation = (
        "phase:probe",
        f"focus:{family}",
        f"{family}:{value}",
        *_other_family_value(family, task_index, seed),
        f"noise:{offset % 5}",
    )
    second_observation = (
        "phase:commit",
        f"focus:{family}",
        f"commit-slot:{offset % 3}",
    )
    return HiddenRuleTask(
        task_id=task_id,
        split=split,
        relevant_family=family,
        relevant_value=value,
        steps=(
            HiddenRuleStep(
                observation=first_observation,
                expected_action=first_action,
                result_on_success=(result_feature, "status:unlocked"),
            ),
            HiddenRuleStep(
                observation=second_observation,
                expected_action=second_action,
                result_on_success=(f"done:{second_action}", "status:complete"),
            ),
        ),
    )


def make_hidden_rule_tasks(seed: int = 1729, repeats: int = 3) -> tuple[HiddenRuleTask, ...]:
    """Build deterministic train + held-out hidden-rule tasks.

    Training covers each feature/action mapping across multiple distractor
    contexts. Held-out tasks use new task IDs and distractor combinations; they
    are never consumed by `explore_train`.
    """
    rng = random.Random(seed)
    tasks: list[HiddenRuleTask] = []
    families = tuple(_FIRST_ACTION_RULES.keys())

    task_index = 0
    for repeat in range(repeats):
        for family in families:
            values = list(_VALUES_BY_FAMILY[family])
            rng.shuffle(values)
            for value in values:
                tasks.append(
                    _make_task(
                        task_id=f"train-{task_index:03d}",
                        split="train",
                        family=family,
                        value=value,
                        offset=task_index + repeat,
                        task_index=task_index,
                        seed=seed,
                    )
                )
                task_index += 1

    heldout_index = 0
    for family in families:
        for value in _VALUES_BY_FAMILY[family]:
            tasks.append(
                _make_task(
                    task_id=f"heldout-{heldout_index:03d}",
                    split="heldout",
                    family=family,
                    value=value,
                    offset=100 + heldout_index * 2,
                    task_index=task_index,
                    seed=seed,
                )
            )
            heldout_index += 1
            task_index += 1

    return tuple(tasks)


def _tasks_by_split(tasks: Iterable[HiddenRuleTask], split: Split) -> tuple[HiddenRuleTask, ...]:
    return tuple(task for task in tasks if task.split == split)


def explore_train(
    bank: TemporalTraceBank,
    tasks: Sequence[HiddenRuleTask],
    *,
    actions: Sequence[str] = ACTIONS,
    seed: int = 1729,
    max_attempts_per_step: int | None = None,
) -> dict[str, int]:
    """Train from verifier reward by trying actions until a step succeeds.

    The learner is not given rule IDs or expected actions. The benchmark
    environment supplies reward through each step's verifier.
    """
    rng = random.Random(seed)
    train_tasks = _tasks_by_split(tasks, "train")
    attempts = 0
    correct_attempts = 0
    traces = 0
    reward_events = 0

    for task in train_tasks:
        previous_success: TraceEvent | None = None
        for step_index, step in enumerate(task.steps):
            ranked = [score.action for score in bank.rank_actions(
                step.observation,
                actions,
                previous_action=previous_success.action if previous_success else None,
                previous_result=previous_success.result if previous_success else (),
            )]
            remaining = [action for action in actions if action not in ranked]
            rng.shuffle(remaining)
            action_order = [*ranked, *remaining]
            limit = max_attempts_per_step or len(actions)

            for action in action_order[:limit]:
                attempts += 1
                passed = step.verify(action)
                reward = 1.0 if passed else -0.2
                result = step.result_on_success if passed else ("status:error", f"miss:{action}")
                event = TraceEvent.build(
                    observation=step.observation,
                    action=action,
                    result=result,
                    reward=reward,
                    task_id=task.task_id,
                    episode_id=task.task_id,
                    step_index=step_index,
                )
                bank.learn_event(event, previous_event=previous_success)
                reward_events += 1
                if passed:
                    previous_success = event
                    correct_attempts += 1
                    break
            else:
                previous_success = None
        traces += 1

    bank.traces_seen += traces
    return {
        "train_task_count": len(train_tasks),
        "trace_count": traces,
        "attempt_count": attempts,
        "correct_attempt_count": correct_attempts,
        "reward_count": reward_events,
    }


def rollout_task(
    bank: TemporalTraceBank,
    task: HiddenRuleTask,
    *,
    actions: Sequence[str] = ACTIONS,
) -> RolloutResult:
    previous_action: str | None = None
    previous_result: tuple[str, ...] = ()
    predicted: list[str] = []
    expected: list[str] = []

    for step in task.steps:
        action = bank.choose_action(
            step.observation,
            actions,
            previous_action=previous_action,
            previous_result=previous_result,
        )
        predicted.append(action)
        expected.append(step.expected_action)
        if step.verify(action):
            previous_action = action
            previous_result = step.result_on_success
        else:
            previous_action = action
            previous_result = ("status:error", f"miss:{action}")

    return RolloutResult(
        task_id=task.task_id,
        split=task.split,
        expected_actions=tuple(expected),
        predicted_actions=tuple(predicted),
        passed=tuple(predicted) == tuple(expected),
    )


def evaluate_policy(
    bank: TemporalTraceBank,
    tasks: Sequence[HiddenRuleTask],
    *,
    split: Split = "heldout",
    actions: Sequence[str] = ACTIONS,
) -> EvaluationResult:
    selected = _tasks_by_split(tasks, split)
    rollouts = tuple(rollout_task(bank, task, actions=actions) for task in selected)
    pass_count = sum(1 for rollout in rollouts if rollout.passed)
    total_actions = sum(len(rollout.expected_actions) for rollout in rollouts)
    correct_actions = sum(
        1
        for rollout in rollouts
        for expected, predicted in zip(rollout.expected_actions, rollout.predicted_actions)
        if expected == predicted
    )
    failures = tuple(
        {
            "task_id": rollout.task_id,
            "expected_actions": list(rollout.expected_actions),
            "predicted_actions": list(rollout.predicted_actions),
        }
        for rollout in rollouts
        if not rollout.passed
    )
    return EvaluationResult(
        split=split,
        task_count=len(rollouts),
        pass_count=pass_count,
        pass_rate=pass_count / len(rollouts) if rollouts else 0.0,
        action_accuracy=correct_actions / total_actions if total_actions else 0.0,
        failures=failures,
        rollouts=rollouts,
    )


def random_baseline(
    tasks: Sequence[HiddenRuleTask],
    *,
    split: Split = "heldout",
    actions: Sequence[str] = ACTIONS,
    seed: int = 1729,
) -> EvaluationResult:
    rng = random.Random(seed)
    selected = _tasks_by_split(tasks, split)
    rollouts: list[RolloutResult] = []
    for task in selected:
        predicted = tuple(rng.choice(actions) for _ in task.steps)
        expected = tuple(step.expected_action for step in task.steps)
        rollouts.append(
            RolloutResult(
                task_id=task.task_id,
                split=task.split,
                expected_actions=expected,
                predicted_actions=predicted,
                passed=predicted == expected,
            )
        )

    pass_count = sum(1 for rollout in rollouts if rollout.passed)
    total_actions = sum(len(rollout.expected_actions) for rollout in rollouts)
    correct_actions = sum(
        1
        for rollout in rollouts
        for expected, predicted in zip(rollout.expected_actions, rollout.predicted_actions)
        if expected == predicted
    )
    failures = tuple(
        {
            "task_id": rollout.task_id,
            "expected_actions": list(rollout.expected_actions),
            "predicted_actions": list(rollout.predicted_actions),
        }
        for rollout in rollouts
        if not rollout.passed
    )
    return EvaluationResult(
        split=f"{split}:random",
        task_count=len(rollouts),
        pass_count=pass_count,
        pass_rate=pass_count / len(rollouts) if rollouts else 0.0,
        action_accuracy=correct_actions / total_actions if total_actions else 0.0,
        failures=failures,
        rollouts=tuple(rollouts),
    )
