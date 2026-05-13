from __future__ import annotations

import pytest

from project_x.learning.temporal_trace import ExperienceTrace, TemporalTraceBank, TraceEvent


def test_trace_event_normalizes_features():
    event = TraceEvent.build(
        observation=["Color:Red", "color:red", "noise!"],
        action="act_a",
        result=["RESULT:Act_A"],
        reward=1,
        task_id="t",
        episode_id="e",
        step_index=0,
    )
    assert event.observation == ("color:red", "noise")
    assert event.result == ("result:act_a",)


def test_state_action_reward_changes_choice():
    bank = TemporalTraceBank()
    event = TraceEvent.build(
        observation=["feature:x"],
        action="act_b",
        result=["ok"],
        reward=1.0,
        task_id="t",
        episode_id="e",
        step_index=0,
    )
    bank.learn_event(event)

    assert bank.choose_action(["feature:x"], ["act_a", "act_b"]) == "act_b"
    assert bank.score_action(["feature:x"], "act_b").state_score > 0


def test_negative_reward_suppresses_wrong_action():
    bank = TemporalTraceBank()
    wrong = TraceEvent.build(
        observation=["feature:x"],
        action="act_a",
        result=["miss"],
        reward=-1.0,
        task_id="t",
        episode_id="e",
        step_index=0,
    )
    right = TraceEvent.build(
        observation=["feature:x"],
        action="act_b",
        result=["ok"],
        reward=1.0,
        task_id="t",
        episode_id="e",
        step_index=0,
    )
    bank.learn_event(wrong)
    bank.learn_event(right)

    assert bank.score_action(["feature:x"], "act_a").score < 0
    assert bank.choose_action(["feature:x"], ["act_a", "act_b"]) == "act_b"


def test_transition_reward_learns_ordered_next_action():
    bank = TemporalTraceBank()
    first = TraceEvent.build(
        observation=["phase:probe"],
        action="act_a",
        result=["result:act_a"],
        reward=1.0,
        task_id="t",
        episode_id="e",
        step_index=0,
    )
    second = TraceEvent.build(
        observation=["phase:commit"],
        action="act_c",
        result=["done"],
        reward=1.0,
        task_id="t",
        episode_id="e",
        step_index=1,
    )
    bank.learn_event(first)
    bank.learn_event(second, previous_event=first)

    scores = bank.rank_actions(
        ["phase:commit"],
        ["act_a", "act_b", "act_c"],
        previous_action="act_a",
        previous_result=["result:act_a"],
    )
    assert scores[0].action == "act_c"
    assert scores[0].transition_score > 0


def test_learn_trace_records_order_and_counts():
    bank = TemporalTraceBank()
    events = (
        TraceEvent.build(
            observation=["x"],
            action="act_a",
            result=["r"],
            reward=1.0,
            task_id="t",
            episode_id="e",
            step_index=0,
        ),
        TraceEvent.build(
            observation=["y"],
            action="act_b",
            result=["done"],
            reward=1.0,
            task_id="t",
            episode_id="e",
            step_index=1,
        ),
    )
    bank.learn_trace(ExperienceTrace(trace_id="trace", events=events))

    assert bank.traces_seen == 1
    assert bank.events_seen == 2
    assert bank.reward_count == 2
    assert bank.entry_count() > 0


def test_json_round_trip(tmp_path):
    bank = TemporalTraceBank()
    bank.learn_event(
        TraceEvent.build(
            observation=["feature:x"],
            action="act_b",
            result=["ok"],
            reward=1.0,
            task_id="t",
            episode_id="e",
            step_index=0,
        )
    )
    path = tmp_path / "bank.json"
    bank.save_json(path)
    loaded = TemporalTraceBank.load_json(path)

    assert loaded.to_dict() == bank.to_dict()
    assert loaded.choose_action(["feature:x"], ["act_a", "act_b"]) == "act_b"


def test_empty_actions_rejected():
    with pytest.raises(ValueError, match="actions must not be empty"):
        TemporalTraceBank().choose_action(["x"], [])
