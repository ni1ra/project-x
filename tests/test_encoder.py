"""Smoke tests for organic encoders (Phase 9 Layer 2)."""

from __future__ import annotations

import numpy as np

from project_x.experiments.encoder import (
    CharNgramHashEncoder,
    cosine_bipolar,
    cosine_matrix_bipolar,
)
from project_x.hdc_infra import PACK_DTYPE, cosine_packed


def test_determinism_same_seed():
    e1 = CharNgramHashEncoder(D=512, feature_dim=256, n=3, seed=1337)
    e2 = CharNgramHashEncoder(D=512, feature_dim=256, n=3, seed=1337)
    out1 = e1.encode(["Alice prefers Python.", "the build is green."])
    out2 = e2.encode(["Alice prefers Python.", "the build is green."])
    assert np.array_equal(out1, out2), "same seed must produce identical encodings"


def test_bipolar_output():
    e = CharNgramHashEncoder(D=512, feature_dim=256, n=3, seed=1337)
    out = e.encode(["Bob likes Rust.", "Carol settled on Postgres."])
    assert out.dtype == np.int8
    assert out.shape == (2, 512)
    unique_vals = set(np.unique(out).tolist())
    assert unique_vals.issubset({-1, 1}), f"expected bipolar {{-1,1}}, got {unique_vals}"


def test_paraphrase_cosine_higher_than_unrelated():
    """Char-n-gram captures lexical overlap. Paraphrase pairs (sharing many chars)
    should have higher cosine than unrelated pairs at signal level >> 0."""
    e = CharNgramHashEncoder(D=4096, feature_dim=2048, n=3, seed=1337)
    # Heavy lexical overlap (paraphrase-like)
    pair_close = ["Alice prefers Python.", "Alice tends to pick Python."]
    # No shared content words
    pair_far = ["Alice prefers Python.", "the build is green."]

    v_close = e.encode(pair_close)
    v_far = e.encode(pair_far)

    cos_close = cosine_bipolar(v_close[0], v_close[1])
    cos_far = cosine_bipolar(v_far[0], v_far[1])

    assert cos_close > cos_far, (
        f"paraphrase cosine ({cos_close:.4f}) should exceed unrelated ({cos_far:.4f})"
    )


def test_orthogonality_random_pair_near_zero():
    """Two random distinct sentences should have near-zero cosine — HDC orthogonality property."""
    e = CharNgramHashEncoder(D=10000, feature_dim=4096, n=3, seed=1337)
    out = e.encode(
        [
            "Alice prefers Python and quiet mornings.",
            "Kafka brokers replicated under three zones.",
        ]
    )
    cos = cosine_bipolar(out[0], out[1])
    # Random projection at D=10000 → SD of cosine ≈ 1/sqrt(D) ≈ 0.01.
    # Allow generous slack for shared common chars (spaces, etc.).
    assert abs(cos) < 0.20, f"unrelated pair cosine {cos:.4f} too far from 0"


def test_encode_empty_list():
    e = CharNgramHashEncoder(D=512, feature_dim=256, n=3, seed=1337)
    out = e.encode([])
    assert out.shape == (0, 512)
    assert out.dtype == np.int8


def test_cosine_matrix_shape_and_diagonal():
    e = CharNgramHashEncoder(D=2048, feature_dim=512, n=3, seed=1337)
    out = e.encode(["one short sentence.", "another short sentence."])
    M = cosine_matrix_bipolar(out, out)
    assert M.shape == (2, 2)
    # Self-cosine = 1.0 (bipolar dotted with itself, normalized by D)
    assert M[0, 0] == 1.0
    assert M[1, 1] == 1.0
    # Symmetry
    assert M[0, 1] == M[1, 0]


def test_protocol_compliance_smoke():
    """The OrganicEncoder protocol requires .encode(list[str]) -> ndarray (n, D)
    and .name() -> str. Satisfied structurally by CharNgramHashEncoder."""
    e = CharNgramHashEncoder(D=128, feature_dim=64, n=3, seed=1337)
    out = e.encode(["test text"])
    assert out.shape == (1, 128)
    assert isinstance(e.name(), str)
    assert len(e.name()) > 0


def test_default_D_is_multiple_of_32():
    """Default D must satisfy bitpack constraint (D % 32 == 0) so encode_packed
    works without explicit override. Audit B2 caught the prior D=10000 default
    contradicting docs' D=10240 claim; this test locks the source state."""
    e = CharNgramHashEncoder()
    assert e.D == 10240, f"default D must be 10240, got {e.D}"
    assert e.D % 32 == 0, f"default D={e.D} must be divisible by 32 for bitpack"


def test_encode_packed_shape_and_dtype():
    """encode_packed returns (n, D/32) uint32; 32× memory compression vs int8."""
    e = CharNgramHashEncoder(D=10240, feature_dim=4096, n=3, seed=1337)
    packed = e.encode_packed(["one", "two", "three"])
    assert packed.shape == (3, 10240 // 32), f"shape {packed.shape}"
    assert packed.dtype == PACK_DTYPE, f"dtype {packed.dtype}"


def test_encode_packed_empty_list():
    """Empty input returns (0, D/32) uint32 — symmetric with encode([])."""
    e = CharNgramHashEncoder(D=10240, feature_dim=4096, n=3, seed=1337)
    packed = e.encode_packed([])
    assert packed.shape == (0, 10240 // 32)
    assert packed.dtype == PACK_DTYPE


def test_encode_packed_cosine_matches_bipolar():
    """cosine_packed on encode_packed output ≡ cosine_bipolar on encode output
    (mathematically exact for bipolar; floating-point equality < 1e-9 expected)."""
    e = CharNgramHashEncoder(D=10240, feature_dim=4096, n=3, seed=1337)
    texts = ["Alice prefers Python.", "Alice tends to pick Python."]
    bipolar = e.encode(texts)
    packed = e.encode_packed(texts)
    cos_bipolar = cosine_bipolar(bipolar[0], bipolar[1])
    cos_pkd = cosine_packed(packed[0], packed[1], D=10240)
    assert abs(cos_bipolar - cos_pkd) < 1e-9, (
        f"cosine equivalence broken: bipolar={cos_bipolar}, packed={cos_pkd}"
    )
