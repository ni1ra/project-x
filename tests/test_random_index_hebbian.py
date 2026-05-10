"""Tests for RandomIndexHebbianEncoder (Phase 9 Cycle 3, council winner)."""

from __future__ import annotations

import numpy as np

from project_x.experiments.encoder import cosine_bipolar
from project_x.experiments.random_index_hebbian import (
    RandomIndexHebbianEncoder,
    make_index_vector,
    tokenize,
)


def test_tokenize_basic():
    assert tokenize("Alice prefers Python.") == ["alice", "prefers", "python"]
    # File paths kept intact
    assert "src/project_x/experiments/foo.py" in tokenize(
        "the controller lives at src/project_x/experiments/foo.py"
    )


def test_index_vector_sparse_ternary():
    v = make_index_vector("alice", D=1000, n_active=10, seed_offset=1337)
    assert v.shape == (1000,)
    assert v.dtype == np.int8
    nonzero = np.count_nonzero(v)
    assert nonzero == 10, f"expected 10 active, got {nonzero}"
    assert int(v.sum()) == 0, f"expected balanced (5+1, 5-1) → sum=0, got {int(v.sum())}"
    # Determinism
    v2 = make_index_vector("alice", D=1000, n_active=10, seed_offset=1337)
    assert np.array_equal(v, v2)
    # Different word → different vector
    v3 = make_index_vector("bob", D=1000, n_active=10, seed_offset=1337)
    assert not np.array_equal(v, v3)


def test_fit_determinism():
    corpus = [
        "Alice prefers Python.",
        "Bob likes Rust.",
        "Alice and Bob settled on Postgres for the database.",
    ]
    e1 = RandomIndexHebbianEncoder(D=512, n_active=10, window=3, seed=1337)
    e2 = RandomIndexHebbianEncoder(D=512, n_active=10, window=3, seed=1337)
    e1.fit(corpus)
    e2.fit(corpus)
    for w in e1._trained_vecs:
        assert np.array_equal(e1._trained_vecs[w], e2._trained_vecs[w]), (
            f"determinism broken on '{w}'"
        )


def test_co_occurring_words_become_correlated():
    """Train on a corpus where 'apple' and 'fruit' always co-occur,
    'rust' and 'language' always co-occur, and apple-rust never do.
    After training: cos(apple, fruit) > cos(apple, rust)."""
    corpus = [
        "apple is a fruit.",
        "the apple fruit is red.",
        "fruit such as apple grows on trees.",
        "rust is a language.",
        "the rust language is fast.",
        "language like rust uses ownership.",
    ] * 3  # repeat to amplify the signal
    e = RandomIndexHebbianEncoder(D=4096, n_active=20, window=3,
                                   subsample_threshold=1e-1, seed=1337)
    e.fit(corpus)
    cos_apple_fruit = cosine_bipolar(e._trained_vecs["apple"], e._trained_vecs["fruit"])
    cos_apple_rust = cosine_bipolar(e._trained_vecs["apple"], e._trained_vecs["rust"])
    assert cos_apple_fruit > cos_apple_rust, (
        f"apple-fruit cos {cos_apple_fruit:.3f} should exceed "
        f"apple-rust cos {cos_apple_rust:.3f}"
    )
    # Both trained vecs should be bipolar
    assert set(np.unique(e._trained_vecs["apple"]).tolist()).issubset({-1, 1})


def test_unseen_word_orthogonal_to_trained():
    """Unseen words at query time should encode to vectors with low cosine
    against all trained turn vectors — this is the load-bearing trick that
    flips the signal-vs-noise gap positive."""
    corpus = [
        "Alice prefers Python.",
        "Bob settled on Rust.",
        "Carol picked Postgres.",
    ] * 5
    e = RandomIndexHebbianEncoder(D=8192, n_active=20, window=3,
                                   subsample_threshold=1e-1, seed=1337)
    e.fit(corpus)
    turn_vecs = e.encode(corpus)
    # Query with totally unseen tokens
    unseen_query = e.encode(["GhostXYZ12 and PhantomABC34 prefer wonky-mod-99."])
    cos_max_unseen = float(np.max(turn_vecs.astype(np.int32) @ unseen_query[0].astype(np.int32))) / float(turn_vecs.shape[1])
    # Query with trained tokens
    seen_query = e.encode(["What does Alice prefer?"])
    cos_max_seen = float(np.max(turn_vecs.astype(np.int32) @ seen_query[0].astype(np.int32))) / float(turn_vecs.shape[1])
    assert cos_max_seen > cos_max_unseen, (
        f"trained-token query cos {cos_max_seen:.3f} should exceed "
        f"unseen-token query cos {cos_max_unseen:.3f}"
    )


def test_subsampling_drops_frequent_words_more():
    """Subsampling P_drop scales with frequency: P_drop(the) > P_drop(alice).
    Dilute the corpus with many unique rare words so 'alice' has low frequency."""
    rare_filler = " ".join(f"unique_word_{i}" for i in range(200))
    # "the" repeats heavily; "alice" appears only twice; rare words appear once each
    corpus = [
        f"the alice the bob the carol {rare_filler}",
        f"the {rare_filler}",
    ] * 5
    e = RandomIndexHebbianEncoder(D=512, n_active=10, window=3,
                                   subsample_threshold=1e-3, seed=1337)
    e.fit(corpus)
    # Heavily-frequent "the" should have HIGHER drop prob than less-frequent "alice"
    assert e._drop_prob["the"] > e._drop_prob["alice"], (
        f"P_drop('the')={e._drop_prob['the']:.3f} should exceed "
        f"P_drop('alice')={e._drop_prob['alice']:.3f}"
    )
    # Truly rare words (appear once each) should have very low or zero drop prob
    rare_drops = [e._drop_prob[f"unique_word_{i}"] for i in range(5)]
    assert max(rare_drops) < e._drop_prob["the"], (
        "rare unique words should drop less than 'the'"
    )


def test_bipolar_encode_output():
    corpus = ["hello world.", "foo bar baz."]
    e = RandomIndexHebbianEncoder(D=512, n_active=10, window=3, seed=1337)
    e.fit(corpus)
    out = e.encode(["hello world", "completely different text"])
    assert out.shape == (2, 512)
    assert out.dtype == np.int8
    assert set(np.unique(out).tolist()).issubset({-1, 1})


def test_encode_empty_list():
    e = RandomIndexHebbianEncoder(D=512, n_active=10, window=3, seed=1337)
    e.fit(["some training text"])
    out = e.encode([])
    assert out.shape == (0, 512)


def test_encode_before_fit_raises():
    e = RandomIndexHebbianEncoder(D=512, n_active=10, window=3, seed=1337)
    try:
        e.encode(["x"])
    except RuntimeError:
        return
    raise AssertionError("encode() should raise before fit()")
