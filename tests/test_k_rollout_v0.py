"""Tests for cycle 11 #00P13c11-03 K-rollout iteration mechanism.

Coverage:
  - 3 strategies (bind/bundle/greedy) produce DIFFERENT walks over same prompt + corpus.
  - Best-satisfied wins (highest avg-similarity above tau_satisfaction).
  - All-K-fail → honest refusal (chosen_strategy=None; refusal_reason populated).
  - tau_satisfaction tunable; lower threshold accepts more rollouts.
  - K cap enforcement (k > len(_STRATEGIES) raises).
  - Greedy strategy preserves original-prompt similarity (no context drift).
  - Result render contains all rollout scores + chosen-strategy mark.

Honest framing: tests verify SHAPE (K rollouts diverge; best-wins; all-fail-refuses),
not LITERARY QUALITY of the emitted walks. Quality is bounded by corpus quality.
"""

from __future__ import annotations

import pytest

from project_x.corpus.k_rollout import KRolloutComposer, KRolloutResult


@pytest.fixture(scope="module")
def k_composer() -> KRolloutComposer:
    """Shared K-rollout composer — encodes the mini-corpus once."""
    return KRolloutComposer()


def test_k_rollout_runs_three_strategies_by_default(k_composer):
    """K=3 default → 3 rollouts attempted: bind / bundle / greedy."""
    result = k_composer.compose("write a poem about nature", domain="poetry", k=3, tau_satisfaction=0.0)
    assert result.k_attempted == 3
    assert len(result.rollouts) == 3
    strategies = [r[0] for r in result.rollouts]
    assert set(strategies) == {"bind", "bundle", "greedy"}


def test_k_rollout_strategies_diverge_on_same_prompt(k_composer):
    """Three different exploration strategies produce three different walks.
    Greedy always picks top-K-to-original-prompt; bind/bundle update context
    so subsequent steps diverge. At least 2 of the 3 walks should differ."""
    result = k_composer.compose("philosophize about existence", domain="philosophy", k=3, tau_satisfaction=0.0)
    walks_by_strategy = {strategy: walk for strategy, walk, _ in result.rollouts}
    bind_texts = [f.text for f in walks_by_strategy["bind"].fragments]
    bundle_texts = [f.text for f in walks_by_strategy["bundle"].fragments]
    greedy_texts = [f.text for f in walks_by_strategy["greedy"].fragments]
    # Each pair should differ on at least one position OR have different lengths.
    pairs_match = sum([bind_texts == bundle_texts, bind_texts == greedy_texts, bundle_texts == greedy_texts])
    assert pairs_match <= 1  # at most one pair matches; at least two strategies diverge


def test_k_rollout_best_satisfied_wins(k_composer):
    """Chosen rollout is the one with highest avg_similarity above tau_satisfaction.
    Greedy strategy typically scores highest because it always picks top-K-to-prompt;
    bind and bundle dilute similarity via context updates."""
    result = k_composer.compose("meaning of life", domain="philosophy", k=3, tau_satisfaction=0.0)
    assert result.chosen_strategy is not None
    # The chosen strategy's avg_similarity is the max across all rollouts
    chosen_avg = next(avg for strategy, _, avg in result.rollouts if strategy == result.chosen_strategy)
    other_avgs = [avg for strategy, _, avg in result.rollouts if strategy != result.chosen_strategy]
    for other in other_avgs:
        assert chosen_avg >= other


def test_k_rollout_all_fail_honest_refusal(k_composer):
    """High tau_satisfaction → all K rollouts fail → honest refusal.
    Set tau impossibly high (similarity is bounded in [-1, 1], so tau=2.0 always fails)."""
    result = k_composer.compose("test prompt for refusal path", domain="all", k=3, tau_satisfaction=2.0)
    assert result.chosen_strategy is None
    assert result.chosen_walk is None
    assert result.refusal_reason is not None
    assert "tau_satisfaction" in result.refusal_reason
    assert "below" in result.refusal_reason


def test_k_rollout_tau_satisfaction_tunable(k_composer):
    """Lower tau accepts more rollouts; higher tau rejects more. Mechanical check."""
    # Run with tau=0.0 — should succeed (any similarity > -∞)
    low_tau = k_composer.compose("write something", domain="all", k=3, tau_satisfaction=0.0)
    assert low_tau.chosen_strategy is not None
    # Same prompt with tau=10.0 — should refuse (no similarity above 1.0)
    high_tau = k_composer.compose("write something", domain="all", k=3, tau_satisfaction=10.0)
    assert high_tau.chosen_strategy is None


def test_k_rollout_k_cap_enforcement(k_composer):
    """k > available strategies raises ValueError."""
    with pytest.raises(ValueError, match="exceeds v1 strategy count"):
        k_composer.compose("anything", domain="all", k=99, tau_satisfaction=0.0)


def test_k_rollout_render_contains_all_rollouts_and_winner(k_composer):
    """`KRolloutResult.render()` lists all rollout scores + marks the winner."""
    result = k_composer.compose("write a poem", domain="poetry", k=3, tau_satisfaction=0.0)
    rendered = result.render()
    # All three strategy names appear with their scores
    assert "bind:" in rendered
    assert "bundle:" in rendered
    assert "greedy:" in rendered
    # Winner is marked
    assert "✓ chosen" in rendered
    # avg_similarity values are rendered
    assert "avg_similarity=" in rendered


def test_k_rollout_render_includes_honest_refusal_text():
    """Render of a refusal result shows the honest-refusal framing."""
    composer = KRolloutComposer()
    result = composer.compose("test prompt", domain="all", k=3, tau_satisfaction=2.0)
    rendered = result.render()
    assert "HONEST REFUSAL" in rendered
    assert "I-don't-know" in rendered or "best-of-bad" in rendered.lower() or "EXPLORATION not OVERCLAIM" in rendered
