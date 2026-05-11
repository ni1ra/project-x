"""K-rollout iteration for natural-mode HDC walks — cycle 11 #00P13c11-03.

Per the canonical synthesis doc Layer 4 § K-rollout iteration: run K parallel
rollouts with different exploration strategies, score each, emit the first
satisfied rollout; if all K fail → honest refusal (M-PROJECTX-013 preserved).

The canonical doc's curiosity-signal formulation: each step's curiosity =
1 - cos(predicted, actual). Average across a walk gives a satisfaction score.
Lower curiosity = walk hangs together = satisfied. The K rollouts use
different exploration strategies so they actually diverge over the same
corpus + same prompt:

  - 'bind' (default): near-orthogonal context update via HDC bind. Each step
    picks the fragment most-similar to (prompt ⊗ emitted-so-far). The
    cycle-11 #00P13c11-DEMO natural-mode walk's default.
  - 'bundle' (additive): context updated by HDC bundle (signed-sum-then-sign)
    rather than bind. Bundling preserves similarity to BOTH prompt and emitted-
    so-far; produces same-theme continuation rather than orthogonal exploration.
  - 'greedy' (no context update): every step picks the fragment most-similar
    to the ORIGINAL prompt; emits top-K without bind/bundle dynamics. Tightest
    similarity to prompt; least diverse walk.

Honest framing per M-PROJECTX-013:
  - Satisfaction threshold is empirical-tuning territory (open question per
    canonical doc Layer 4). v1 floor at 0.05 is honest; cycle-11+ calibration.
  - "All K fail" honestly refuses rather than picking the best-of-bad. The
    curiosity drives EXPLORATION not OVERCLAIM (canonical doc § Layer 4
    M-PROJECTX-013 preservation note).
  - K=3 is the v1 cap; canonical doc spec doesn't pin K (hormone-modulated).

Organic-thesis: no LLM, no learning. HDC primitives + cosine retrieval +
binary bipolar arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from project_x.corpus.natural_mode import (
    EmittedFragment,
    NaturalModeComposer,
    NaturalWalkResult,
)
from project_x.experiments.encoder import cosine_bipolar


@dataclass
class KRolloutResult:
    """Output of `KRolloutComposer.compose()`."""

    prompt: str
    domain_filter: str
    k_attempted: int
    rollouts: list[tuple[str, NaturalWalkResult, float]]  # (strategy, walk, avg_similarity)
    chosen_strategy: str | None  # which rollout won, or None if all K failed
    chosen_walk: NaturalWalkResult | None  # the winning walk, or None
    refusal_reason: str | None  # populated if all K failed
    tau_satisfaction: float

    def render(self) -> str:
        """Render the K-rollout result with honest framing."""
        lines = []
        lines.append(
            f"K-ROLLOUT NATURAL-MODE WALK v0 — {self.k_attempted} exploration strategies attempted "
            f"on prompt '{self.prompt}' (domain={self.domain_filter}, tau_satisfaction="
            f"{self.tau_satisfaction:.3f}). Per canonical synthesis doc Layer 4 § K-rollout."
        )
        lines.append("")
        lines.append("Rollouts (strategy → average per-step similarity, higher = walk more coherent):")
        for strategy, walk, avg_sim in self.rollouts:
            mark = "✓ chosen" if strategy == self.chosen_strategy else "  "
            lines.append(f"  {mark} {strategy}: avg_similarity={avg_sim:.4f}")
        lines.append("")
        if self.chosen_strategy is None:
            lines.append(f"HONEST REFUSAL — {self.refusal_reason}")
            lines.append("Per M-PROJECTX-013: curiosity drives EXPLORATION not OVERCLAIM. "
                         "When no rollout converges below threshold, the agent says I-don't-know "
                         "rather than emitting the best-of-bad.")
        else:
            lines.append(f"Chosen rollout (strategy={self.chosen_strategy}):")
            lines.append("")
            lines.append(self.chosen_walk.render())
        return "\n".join(lines)


class KRolloutComposer:
    """V1 K-rollout composer over `NaturalModeComposer`. Cycle 11 #00P13c11-03.

    Public API:
      - `compose(prompt, domain, max_fragments=5, k=3, tau_satisfaction=0.05)`:
        run K rollouts with strategies ['bind', 'bundle', 'greedy'][:k]; score
        each by average similarity; emit best if > tau_satisfaction else
        honest refusal.

    Internal note: shares the underlying NaturalModeComposer's encoder +
    fragment hypervectors. The K-rollout wraps composition with different
    context-update operators; the corpus + encoder are identical across
    rollouts.
    """

    # V1 strategy list — additional strategies (permutation, intent-vector,
    # hormone-modulated) are cycle-11+ extensions per canonical doc.
    _STRATEGIES: tuple[str, ...] = ("bind", "bundle", "greedy")

    def __init__(self, composer: NaturalModeComposer | None = None) -> None:
        self._composer = composer or NaturalModeComposer()

    def compose(
        self,
        prompt: str,
        domain: str = "all",
        max_fragments: int = 5,
        k: int = 3,
        tau_satisfaction: float = 0.05,
    ) -> KRolloutResult:
        """Run K rollouts with different exploration strategies.

        Each rollout produces a `NaturalWalkResult` via the strategy-specific
        context update. Satisfaction score = average per-step similarity
        (higher = walk coheres better). Winning rollout's score must exceed
        `tau_satisfaction` to dispatch; else honest refusal.

        Args:
            prompt: free-text query.
            domain: 'all' / 'poetry' / 'philosophy' / 'math' / 'lain_voice'.
            max_fragments: walk length cap per rollout.
            k: number of rollouts (capped at len(_STRATEGIES); v1 K=3).
            tau_satisfaction: minimum avg-similarity to emit a rollout. v1
                              floor 0.05 is honest; calibration is cycle-11+.
        """
        if k > len(self._STRATEGIES):
            raise ValueError(
                f"k={k} exceeds v1 strategy count {len(self._STRATEGIES)}; "
                f"available strategies: {self._STRATEGIES}"
            )
        strategies = self._STRATEGIES[:k]
        rollouts: list[tuple[str, NaturalWalkResult, float]] = []
        for strategy in strategies:
            walk = self._run_strategy(prompt, domain, max_fragments, strategy)
            avg_sim = (
                sum(f.similarity for f in walk.fragments) / len(walk.fragments)
                if walk.fragments
                else 0.0
            )
            rollouts.append((strategy, walk, avg_sim))

        # Pick the rollout with highest avg_similarity above tau_satisfaction.
        rollouts_sorted = sorted(rollouts, key=lambda r: -r[2])
        best_strategy, best_walk, best_sim = rollouts_sorted[0]

        if best_sim < tau_satisfaction:
            return KRolloutResult(
                prompt=prompt,
                domain_filter=domain,
                k_attempted=k,
                rollouts=rollouts,
                chosen_strategy=None,
                chosen_walk=None,
                refusal_reason=(
                    f"all {k} rollouts produced avg_similarity below "
                    f"tau_satisfaction={tau_satisfaction:.3f}; best was "
                    f"'{best_strategy}' at {best_sim:.4f}."
                ),
                tau_satisfaction=tau_satisfaction,
            )

        return KRolloutResult(
            prompt=prompt,
            domain_filter=domain,
            k_attempted=k,
            rollouts=rollouts,
            chosen_strategy=best_strategy,
            chosen_walk=best_walk,
            refusal_reason=None,
            tau_satisfaction=tau_satisfaction,
        )

    def _run_strategy(
        self,
        prompt: str,
        domain: str,
        max_fragments: int,
        strategy: str,
    ) -> NaturalWalkResult:
        """Run one rollout with the named strategy. Reuses the composer's encoder
        and fragment hypervectors; only the context-update operator changes."""
        c = self._composer
        prompt_hv: np.ndarray = c._encoder.encode([prompt])[0]
        original_prompt_hv = prompt_hv.copy()  # greedy strategy needs the unchanged prompt-hv
        candidate_indices = set(c._filtered_indices(domain))
        emitted: list[EmittedFragment] = []
        context_hv = prompt_hv

        for step in range(max_fragments):
            if not candidate_indices:
                break
            # For 'greedy' strategy, always score against the ORIGINAL prompt-hv,
            # never the running context. The other strategies use the running
            # context_hv which gets updated by the strategy's operator.
            score_against = original_prompt_hv if strategy == "greedy" else context_hv
            best_idx = -1
            best_sim = -2.0
            for idx in candidate_indices:
                sim = cosine_bipolar(score_against, c._fragment_hvs[idx])
                if sim > best_sim:
                    best_sim = sim
                    best_idx = idx
            if best_idx < 0:
                break
            domain_tag, text, source = c._tagged[best_idx]
            emitted.append(EmittedFragment(
                text=text, source=source,
                similarity=float(best_sim), step=step,
            ))
            # Strategy-specific context update.
            if strategy == "bind":
                context_hv = (context_hv * c._fragment_hvs[best_idx]).astype(np.int8)
            elif strategy == "bundle":
                # HDC bundle: elementwise sum then sign (preserve bipolar invariant)
                summed = context_hv.astype(np.int16) + c._fragment_hvs[best_idx].astype(np.int16)
                context_hv = np.sign(summed).astype(np.int8)
                # sign(0) → 0; per CharNgramHashEncoder convention, treat 0 as +1
                context_hv = np.where(context_hv == 0, 1, context_hv).astype(np.int8)
            # 'greedy' strategy: no context update (always score against original prompt)
            candidate_indices.discard(best_idx)

        note = (
            f"NATURAL-MODE WALK (strategy={strategy}) — {max_fragments}-step HDC retrieval "
            f"over hand-seeded mini-corpus (~{len(c._tagged)} fragments). "
            f"Strategy '{strategy}' updates the retrieval context "
            f"{'by HDC bind (near-orthogonal divergence)' if strategy == 'bind' else 'by HDC bundle (same-theme continuation)' if strategy == 'bundle' else 'NOT AT ALL (greedy top-K to original prompt)'}."
        )
        return NaturalWalkResult(
            prompt=prompt, domain_filter=domain,
            fragments=emitted, note=note,
        )
