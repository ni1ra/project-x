"""Temporal trace learning for hidden-rule/action tasks.

This module is learning machinery, not task knowledge. It stores reward-weighted
associations between observation atoms, actions, ordered result atoms, and later
actions. The same update rule is used for every domain-shaped event.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence


Feature = str
Action = str

_TOKEN_RE = re.compile(r"[a-z0-9_:.=-]+")


def _normalize_feature(feature: object) -> Feature:
    """Convert arbitrary event features into stable lowercase atoms."""
    text = str(feature).strip().lower()
    tokens = _TOKEN_RE.findall(text)
    return " ".join(tokens) if tokens else text


def normalize_features(features: Iterable[object]) -> tuple[Feature, ...]:
    """Normalize and deduplicate features while preserving first-seen order."""
    seen: set[Feature] = set()
    out: list[Feature] = []
    for raw in features:
        feature = _normalize_feature(raw)
        if feature and feature not in seen:
            out.append(feature)
            seen.add(feature)
    return tuple(out)


@dataclass(frozen=True)
class TraceEvent:
    """One observation-action-result-reward event.

    `observation` and `result` are opaque feature atoms to the learner. `task_id`,
    `episode_id`, and `step_index` are provenance only; they are never used as
    scoring features.
    """

    observation: tuple[Feature, ...]
    action: Action
    result: tuple[Feature, ...]
    reward: float
    task_id: str
    episode_id: str
    step_index: int

    @classmethod
    def build(
        cls,
        *,
        observation: Iterable[object],
        action: Action,
        result: Iterable[object],
        reward: float,
        task_id: str,
        episode_id: str,
        step_index: int,
    ) -> "TraceEvent":
        return cls(
            observation=normalize_features(observation),
            action=action,
            result=normalize_features(result),
            reward=float(reward),
            task_id=task_id,
            episode_id=episode_id,
            step_index=int(step_index),
        )


@dataclass(frozen=True)
class ExperienceTrace:
    """Ordered event sequence from one task episode."""

    trace_id: str
    events: tuple[TraceEvent, ...]

    @property
    def reward_total(self) -> float:
        return sum(event.reward for event in self.events)


@dataclass(frozen=True)
class ActionScore:
    """Debug record for an action score."""

    action: Action
    score: float
    state_score: float
    transition_score: float
    bias_score: float


@dataclass
class TemporalTraceBank:
    """Reward-shaped temporal state-action bank.

    The bank has three sparse tables:

    - observation feature -> action weights;
    - previous action + previous result feature -> next action weights;
    - action bias as a tiny cold-start stabilizer from aggregate reward.

    No task IDs, rule IDs, or benchmark labels are used in scoring.
    """

    learning_rate: float = 0.35
    transition_rate: float = 0.8
    bias_rate: float = 0.02
    scoring_mode: str = "linear"  # "linear" | "max" | "softmax" | "competitive"
    state_action: dict[tuple[Feature, Action], float] = field(default_factory=dict)
    state_action_count: dict[tuple[Feature, Action], int] = field(default_factory=dict)
    state_action_pair: dict[tuple[Feature, Action], float] = field(default_factory=dict)
    state_action_pair_count: dict[tuple[Feature, Action], int] = field(default_factory=dict)
    state_action_triplet: dict[tuple[Feature, Action], float] = field(default_factory=dict)
    state_action_triplet_count: dict[tuple[Feature, Action], int] = field(default_factory=dict)
    transition_action: dict[tuple[Action, Feature, Action], float] = field(default_factory=dict)
    action_bias: dict[Action, float] = field(default_factory=dict)
    traces_seen: int = 0
    events_seen: int = 0
    reward_count: int = 0

    def learn_event(
        self,
        event: TraceEvent,
        previous_event: TraceEvent | None = None,
    ) -> None:
        """Update the bank from one event and optional predecessor."""
        self.events_seen += 1
        if event.reward != 0:
            self.reward_count += 1

        delta = self.learning_rate * event.reward
        obs = list(event.observation)
        for feature in obs:
            key = (feature, event.action)
            self.state_action[key] = self.state_action.get(key, 0.0) + delta
            self.state_action_count[key] = self.state_action_count.get(key, 0) + 1

        # Pair-wise feature conjunctions capture context-dependent rules
        # (e.g. focus:color + color:red -> act_a) without task-specific bias.
        for i in range(len(obs)):
            for j in range(i + 1, len(obs)):
                pair_key = (obs[i], obs[j], event.action)
                self.state_action_pair[pair_key] = self.state_action_pair.get(pair_key, 0.0) + delta
                self.state_action_pair_count[pair_key] = self.state_action_pair_count.get(pair_key, 0) + 1

        # Triplets provide even stronger context disambiguation for small
        # observation spaces (6 features -> 20 triplets).
        for i in range(len(obs)):
            for j in range(i + 1, len(obs)):
                for k in range(j + 1, len(obs)):
                    triplet_key = (obs[i], obs[j], obs[k], event.action)
                    self.state_action_triplet[triplet_key] = (
                        self.state_action_triplet.get(triplet_key, 0.0) + delta
                    )
                    self.state_action_triplet_count[triplet_key] = (
                        self.state_action_triplet_count.get(triplet_key, 0) + 1
                    )

        self.action_bias[event.action] = (
            self.action_bias.get(event.action, 0.0) + self.bias_rate * event.reward
        )

        if previous_event is not None:
            transition_delta = self.transition_rate * event.reward
            for result_feature in previous_event.result:
                key = (previous_event.action, result_feature, event.action)
                self.transition_action[key] = self.transition_action.get(key, 0.0) + transition_delta

    def learn_trace(self, trace: ExperienceTrace) -> None:
        """Update the bank from an ordered trace."""
        previous: TraceEvent | None = None
        for event in trace.events:
            self.learn_event(event, previous_event=previous)
            previous = event
        self.traces_seen += 1

    def _state_conjunction_scores(
        self,
        observation: Iterable[object],
        action: Action,
    ) -> list[float]:
        """Return individual conjunction scores (singleton/pair/triplet) for an observation+action.

        Each score is weight / count (average-weight). Used by non-linear scorers
        that need access to individual conjunction strengths.
        """
        obs = normalize_features(observation)
        obs_list = list(obs)
        scores: list[float] = []
        for feature in obs_list:
            key = (feature, action)
            weight = self.state_action.get(key, 0.0)
            count = self.state_action_count.get(key, 1)
            scores.append(weight / count)
        for i in range(len(obs_list)):
            for j in range(i + 1, len(obs_list)):
                key = (obs_list[i], obs_list[j], action)
                weight = self.state_action_pair.get(key, 0.0)
                count = self.state_action_pair_count.get(key, 1)
                scores.append(weight / count)
        for i in range(len(obs_list)):
            for j in range(i + 1, len(obs_list)):
                for k in range(j + 1, len(obs_list)):
                    key = (obs_list[i], obs_list[j], obs_list[k], action)
                    weight = self.state_action_triplet.get(key, 0.0)
                    count = self.state_action_triplet_count.get(key, 1)
                    scores.append(weight / count)
        return scores

    def score_action(
        self,
        observation: Iterable[object],
        action: Action,
        *,
        previous_action: Action | None = None,
        previous_result: Iterable[object] = (),
    ) -> ActionScore:
        """Score one candidate action from current and previous-step atoms."""
        obs = normalize_features(observation)
        prev_result = normalize_features(previous_result)

        # Average-weight scoring: features that consistently predict one action
        # dominate over features that appear in many contexts with mixed rewards.
        obs_list = list(obs)
        state_score = 0.0
        for feature in obs_list:
            key = (feature, action)
            weight = self.state_action.get(key, 0.0)
            count = self.state_action_count.get(key, 1)
            state_score += weight / count

        for i in range(len(obs_list)):
            for j in range(i + 1, len(obs_list)):
                key = (obs_list[i], obs_list[j], action)
                weight = self.state_action_pair.get(key, 0.0)
                count = self.state_action_pair_count.get(key, 1)
                state_score += weight / count

        for i in range(len(obs_list)):
            for j in range(i + 1, len(obs_list)):
                for k in range(j + 1, len(obs_list)):
                    key = (obs_list[i], obs_list[j], obs_list[k], action)
                    weight = self.state_action_triplet.get(key, 0.0)
                    count = self.state_action_triplet_count.get(key, 1)
                    state_score += weight / count

        transition_score = 0.0
        if previous_action is not None:
            transition_score = sum(
                self.transition_action.get((previous_action, feature, action), 0.0)
                for feature in prev_result
            )
        bias_score = self.action_bias.get(action, 0.0)
        return ActionScore(
            action=action,
            score=state_score + transition_score + bias_score,
            state_score=state_score,
            transition_score=transition_score,
            bias_score=bias_score,
        )

    def _apply_scoring_mode(
        self,
        raw_scores: list[ActionScore],
    ) -> list[ActionScore]:
        """Transform raw ActionScore list according to self.scoring_mode.

        Modes:
        - linear: identity (raw scores used directly; default / v0 behavior)
        - max: state_score becomes max individual conjunction score instead of sum
        - competitive: state_score = max - 0.3 * sum(rest); suppresses weak conjunctions
        - softmax: softmax over total raw scores across actions; probability becomes score
        """
        if self.scoring_mode == "linear":
            return raw_scores

        if self.scoring_mode == "max":
            out: list[ActionScore] = []
            for rs in raw_scores:
                conj = self._state_conjunction_scores(
                    rs.action, rs.action  # observation not stored; recompute below
                )
                # Re-derive observation from the action isn't possible; instead we
                # reconstruct by calling score_action with the observation. To avoid
                # this awkwardness, we store the max-mode state score inline:
                # Actually, score_action already computed the sum. We need the
                # individual conjunctions. We'll override by re-running
                # _state_conjunction_scores with the original observation.
                # But we don't have the observation here. So we handle max
                # and competitive inside rank_actions instead, where observation
                # is available. This method only handles softmax.
                out.append(rs)
            return out

        if self.scoring_mode == "softmax":
            # Softmax over total raw scores
            total_scores = [rs.state_score + rs.transition_score + rs.bias_score for rs in raw_scores]
            max_score = max(total_scores) if total_scores else 0.0
            # Numerical stability: subtract max before exp
            exps = [2.718281828459045 ** (s - max_score) for s in total_scores]
            sum_exps = sum(exps)
            probs = [e / sum_exps for e in exps] if sum_exps > 0 else [1.0 / len(exps)] * len(exps)
            out = []
            for rs, prob in zip(raw_scores, probs):
                out.append(
                    ActionScore(
                        action=rs.action,
                        score=prob,
                        state_score=rs.state_score,
                        transition_score=rs.transition_score,
                        bias_score=rs.bias_score,
                    )
                )
            return out

        # competitive and max are handled in rank_actions where observation is available
        return raw_scores

    def rank_actions(
        self,
        observation: Iterable[object],
        actions: Sequence[Action],
        *,
        previous_action: Action | None = None,
        previous_result: Iterable[object] = (),
    ) -> list[ActionScore]:
        """Return candidate actions sorted by descending learned score."""
        raw_scores = [
            self.score_action(
                observation,
                action,
                previous_action=previous_action,
                previous_result=previous_result,
            )
            for action in actions
        ]

        if self.scoring_mode in ("max", "competitive"):
            # Non-linear modes that need observation-level context
            obs = normalize_features(observation)
            out: list[ActionScore] = []
            for rs in raw_scores:
                conj = self._state_conjunction_scores(obs, rs.action)
                if not conj:
                    # No matching conjunctions — fall back to raw sum
                    new_state = rs.state_score
                elif self.scoring_mode == "max":
                    new_state = max(conj)
                else:  # competitive
                    best = max(conj)
                    rest_sum = sum(c for c in conj if c != best)
                    new_state = best - 0.3 * rest_sum
                out.append(
                    ActionScore(
                        action=rs.action,
                        score=new_state + rs.transition_score + rs.bias_score,
                        state_score=new_state,
                        transition_score=rs.transition_score,
                        bias_score=rs.bias_score,
                    )
                )
            return sorted(out, key=lambda item: (-item.score, item.action))

        # linear or softmax
        transformed = self._apply_scoring_mode(raw_scores)
        return sorted(transformed, key=lambda item: (-item.score, item.action))

    def choose_action(
        self,
        observation: Iterable[object],
        actions: Sequence[Action],
        *,
        previous_action: Action | None = None,
        previous_result: Iterable[object] = (),
    ) -> Action:
        """Choose the highest-scoring action with deterministic tie-breaking."""
        if not actions:
            raise ValueError("actions must not be empty")
        return self.rank_actions(
            observation,
            actions,
            previous_action=previous_action,
            previous_result=previous_result,
        )[0].action

    def apply_rating_to_action(self, action: Action, rating: float, *, midpoint: float = 3.0) -> None:
        """Apply an audit-style rating to an action's bias.

        Converts a [1..5] scale rating into a reward signal (rating - midpoint)
        and updates `action_bias` accordingly. This is the integration point
        between the audit-rating loop and the temporal trace bank: natural-mode
        walk ratings shape action-selection policy via the bias term.

        `midpoint` defaults to 3.0 (the HebbianBank RATING_MIDPOINT). A rating
        above midpoint strengthens the action; below weakens it.
        """
        reward = rating - midpoint
        self.action_bias[action] = (
            self.action_bias.get(action, 0.0) + self.bias_rate * reward
        )

    def entry_count(self) -> int:
        """Return the total sparse-entry count across all learned tables."""
        return (
            len(self.state_action)
            + len(self.state_action_pair)
            + len(self.state_action_triplet)
            + len(self.transition_action)
            + len(self.action_bias)
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-friendly dict."""
        return {
            "learning_rate": self.learning_rate,
            "transition_rate": self.transition_rate,
            "bias_rate": self.bias_rate,
            "state_action": [
                {
                    "feature": feature,
                    "action": action,
                    "weight": weight,
                    "count": self.state_action_count.get((feature, action), 1),
                }
                for (feature, action), weight in sorted(self.state_action.items())
            ],
            "state_action_pair": [
                {
                    "feature_a": feature_a,
                    "feature_b": feature_b,
                    "action": action,
                    "weight": weight,
                    "count": self.state_action_pair_count.get((feature_a, feature_b, action), 1),
                }
                for (feature_a, feature_b, action), weight in sorted(
                    self.state_action_pair.items()
                )
            ],
            "state_action_triplet": [
                {
                    "feature_a": feature_a,
                    "feature_b": feature_b,
                    "feature_c": feature_c,
                    "action": action,
                    "weight": weight,
                    "count": self.state_action_triplet_count.get(
                        (feature_a, feature_b, feature_c, action), 1
                    ),
                }
                for (feature_a, feature_b, feature_c, action), weight in sorted(
                    self.state_action_triplet.items()
                )
            ],
            "transition_action": [
                {
                    "previous_action": previous_action,
                    "result_feature": result_feature,
                    "action": action,
                    "weight": weight,
                }
                for (previous_action, result_feature, action), weight in sorted(
                    self.transition_action.items()
                )
            ],
            "action_bias": dict(sorted(self.action_bias.items())),
            "traces_seen": self.traces_seen,
            "events_seen": self.events_seen,
            "reward_count": self.reward_count,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "TemporalTraceBank":
        bank = cls(
            learning_rate=float(payload["learning_rate"]),
            transition_rate=float(payload["transition_rate"]),
            bias_rate=float(payload["bias_rate"]),
        )
        for row in payload.get("state_action", []):
            row = dict(row)  # type: ignore[arg-type]
            key = (str(row["feature"]), str(row["action"]))
            bank.state_action[key] = float(row["weight"])
            bank.state_action_count[key] = int(row.get("count", 1))
        for row in payload.get("state_action_pair", []):
            row = dict(row)  # type: ignore[arg-type]
            key = (str(row["feature_a"]), str(row["feature_b"]), str(row["action"]))
            bank.state_action_pair[key] = float(row["weight"])
            bank.state_action_pair_count[key] = int(row.get("count", 1))
        for row in payload.get("state_action_triplet", []):
            row = dict(row)  # type: ignore[arg-type]
            key = (
                str(row["feature_a"]),
                str(row["feature_b"]),
                str(row["feature_c"]),
                str(row["action"]),
            )
            bank.state_action_triplet[key] = float(row["weight"])
            bank.state_action_triplet_count[key] = int(row.get("count", 1))
        for row in payload.get("transition_action", []):
            row = dict(row)  # type: ignore[arg-type]
            key = (
                str(row["previous_action"]),
                str(row["result_feature"]),
                str(row["action"]),
            )
            bank.transition_action[key] = float(row["weight"])
        bank.action_bias = {
            str(action): float(weight)
            for action, weight in dict(payload.get("action_bias", {})).items()
        }
        bank.traces_seen = int(payload.get("traces_seen", 0))
        bank.events_seen = int(payload.get("events_seen", 0))
        bank.reward_count = int(payload.get("reward_count", 0))
        return bank

    def save_json(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @classmethod
    def load_json(cls, path: str | Path) -> "TemporalTraceBank":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def trace_to_dict(trace: ExperienceTrace) -> dict[str, object]:
    """Return a JSON-friendly representation of a trace."""
    return {
        "trace_id": trace.trace_id,
        "reward_total": trace.reward_total,
        "events": [asdict(event) for event in trace.events],
    }
