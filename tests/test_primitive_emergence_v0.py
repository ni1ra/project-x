"""Tests for cycle 11 #00P13c11-06 primitive emergence clustering MVP.

Coverage:
  - discover_primitives runs end-to-end on the default mini_seed corpus.
  - Trigram extraction dedupes correctly.
  - Density threshold rejects below-min-density clusters.
  - All discovered primitives carry centroid + member count + samples + sim.
  - Reproducibility via fixed seed.
  - Render produces a readable report.
  - Empirical signal: at least some discovered primitives contain "is" /
    "and" / structural patterns (canonical doc Layer 5 prediction).

Honest framing per M-PROJECTX-013: tests verify SHAPE (clustering runs;
density threshold works; centroids picked correctly). The empirical
question of whether discovered primitives are MEANINGFUL STRUCTURAL
PATTERNS vs FREQUENCY RANKINGS is answered by reading the render output,
not by these tests.
"""

from __future__ import annotations

import pytest

from project_x.corpus.primitive_emergence import (
    DiscoveredPrimitive,
    EmergenceResult,
    _extract_trigrams,
    _tokenize_words,
    discover_primitives,
)


def test_tokenize_extracts_alphanumeric_words():
    """Tokenizer drops punctuation; preserves alphanumeric + apostrophe."""
    tokens = _tokenize_words("Hello, world! It's 2026 — pure signal code.")
    assert tokens == ["hello", "world", "it's", "2026", "pure", "signal", "code"]


def test_extract_trigrams_dedupes():
    """Trigram extraction is set-deduplicated; same trigram appearing in
    multiple fragments contributes once."""
    fragments = [
        ("hello world foo bar baz", "source1"),
        ("hello world foo qux", "source2"),
    ]
    trigrams = _extract_trigrams(fragments)
    # "hello world foo" appears in both; should be present exactly once
    assert trigrams.count("hello world foo") == 1
    # "world foo bar", "foo bar baz", "world foo qux" all distinct
    assert "world foo bar" in trigrams
    assert "foo bar baz" in trigrams
    assert "world foo qux" in trigrams


def test_discover_primitives_runs_on_default_corpus():
    """End-to-end: clustering runs over the mini_seed corpus (~240 fragments;
    ~3000+ unique trigrams) and produces a discoverable EmergenceResult."""
    result = discover_primitives(max_iters=10, k=15, min_density=4, seed=42)
    assert isinstance(result, EmergenceResult)
    assert result.n_trigrams > 1000  # mini-corpus produces thousands of trigrams
    assert result.k == 15
    assert result.seed == 42
    # At least some clusters survive the density threshold
    assert len(result.primitives) >= 5


def test_discovered_primitives_have_required_shape():
    """Each DiscoveredPrimitive carries centroid + member_count + samples + sim."""
    result = discover_primitives(max_iters=10, k=15, min_density=4, seed=42)
    for p in result.primitives:
        assert isinstance(p, DiscoveredPrimitive)
        assert p.centroid_text  # non-empty
        assert p.member_count >= 4  # respects min_density
        assert len(p.sample_members) > 0
        assert len(p.sample_members) <= 5  # samples_per_primitive default
        # Centroid is among sample_members
        assert p.centroid_text == p.sample_members[0]
        # Cohesion metric in valid cosine range [-1, 1]
        assert -1.0 <= p.avg_intra_cluster_similarity <= 1.0


def test_density_threshold_rejects_small_clusters():
    """High min_density should produce fewer primitives + more rejected clusters."""
    low = discover_primitives(max_iters=10, k=15, min_density=4, seed=42)
    high = discover_primitives(max_iters=10, k=15, min_density=20, seed=42)
    # At higher threshold, fewer primitives surface (more rejected)
    assert len(high.primitives) <= len(low.primitives)
    assert high.rejected_clusters >= low.rejected_clusters


def test_seed_reproducibility():
    """Fixed seed produces deterministic clustering output."""
    r1 = discover_primitives(max_iters=10, k=15, min_density=4, seed=42)
    r2 = discover_primitives(max_iters=10, k=15, min_density=4, seed=42)
    # Number of primitives + centroids should be identical
    assert len(r1.primitives) == len(r2.primitives)
    centroids1 = sorted(p.centroid_text for p in r1.primitives)
    centroids2 = sorted(p.centroid_text for p in r2.primitives)
    assert centroids1 == centroids2


def test_empirical_signal_meaningful_patterns_emerge():
    """Empirical canonical-doc Layer 5 prediction: clustering should surface
    at least SOME meaningful structural patterns ("X is Y", "X and Y", etc.)
    rather than only frequency-ranked common short phrases.

    Loose check: at least one discovered primitive contains the canonical
    'is' copula pattern OR 'and' coordination pattern OR another structural
    shell. Verifies that clustering produces structural-shape signal at all,
    not the strength of that signal."""
    result = discover_primitives(max_iters=10, k=15, min_density=4, seed=42)
    # Look at all sample members across all primitives
    all_samples = []
    for p in result.primitives:
        all_samples.extend(p.sample_members)
    # At least one trigram should contain "is" (the canonical doc Layer 5's
    # first example pattern: "X is Y because Z")
    is_patterns = [s for s in all_samples if " is " in f" {s} "]
    assert len(is_patterns) > 0, "no 'X is Y' shell patterns found in any cluster"
    # At least one trigram should contain "and" (coordination shell)
    and_patterns = [s for s in all_samples if " and " in f" {s} "]
    assert len(and_patterns) > 0, "no 'X and Y' coordination patterns found"


def test_render_produces_readable_report():
    """`EmergenceResult.render()` produces human-readable text with primitive details."""
    result = discover_primitives(max_iters=10, k=15, min_density=4, seed=42)
    rendered = result.render()
    assert "PRIMITIVE EMERGENCE RESULT" in rendered
    assert "CENTROID:" in rendered
    assert "SAMPLE MEMBERS:" in rendered
    # All primitives surfaced in render
    for p in result.primitives:
        assert p.centroid_text in rendered


def test_discover_primitives_rejects_too_small_corpus():
    """Corpus with too few trigrams for k * min_density raises ValueError."""
    tiny_corpus = [("hello world", "src1"), ("foo bar baz", "src2")]
    with pytest.raises(ValueError, match="corpus too small"):
        discover_primitives(max_iters=10, fragments=tiny_corpus, k=15, min_density=4, seed=42)
