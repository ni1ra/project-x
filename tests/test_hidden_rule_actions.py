from __future__ import annotations

from project_x.benchmarks.hidden_rule_actions import (
    ACTIONS,
    evaluate_policy,
    explore_train,
    make_hidden_rule_tasks,
    random_baseline,
)
from project_x.learning.temporal_trace import TemporalTraceBank


def test_task_pack_has_train_and_heldout_tasks():
    tasks = make_hidden_rule_tasks(seed=1729)
    train = [task for task in tasks if task.split == "train"]
    heldout = [task for task in tasks if task.split == "heldout"]

    assert len(tasks) >= 10
    assert len(train) == 36
    assert len(heldout) == 12
    assert all(len(task.steps) == 2 for task in tasks)


def test_oracle_trace_matches_verifiers():
    task = make_hidden_rule_tasks(seed=1729)[0]
    trace = task.oracle_trace()

    assert len(trace.events) == 2
    for event, step in zip(trace.events, task.steps):
        assert step.verify(event.action)
        assert event.reward == 1.0


def test_cold_policy_is_weak_on_heldout():
    tasks = make_hidden_rule_tasks(seed=1729)
    cold = evaluate_policy(TemporalTraceBank(), tasks, split="heldout")

    assert cold.task_count == 12
    assert cold.pass_rate < 0.5


def test_explore_train_learns_heldout_action_rules():
    tasks = make_hidden_rule_tasks(seed=1729)
    bank = TemporalTraceBank()

    train_stats = explore_train(bank, tasks, seed=1729)
    learned = evaluate_policy(bank, tasks, split="heldout")
    random_result = random_baseline(tasks, split="heldout", seed=1729)

    assert train_stats["trace_count"] == 36
    assert train_stats["reward_count"] >= 72
    assert learned.pass_rate >= 0.70
    assert learned.pass_rate - random_result.pass_rate >= 0.20
    assert learned.action_accuracy >= 0.75


def test_learned_policy_uses_temporal_transition_for_second_step():
    tasks = make_hidden_rule_tasks(seed=1729)
    bank = TemporalTraceBank()
    explore_train(bank, tasks, seed=1729)
    task = next(task for task in tasks if task.split == "heldout")
    first, second = task.steps
    first_action = bank.choose_action(first.observation, ACTIONS)

    assert first_action == first.expected_action
    second_scores = bank.rank_actions(
        second.observation,
        ACTIONS,
        previous_action=first_action,
        previous_result=first.result_on_success,
    )
    assert second_scores[0].action == second.expected_action
    assert second_scores[0].transition_score > 0
