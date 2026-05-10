"""Smoke test for the Phase 1-6 legacy transformer scaffolding.

Skipped when torch is not installed (audit-C2 — torch is now an OPTIONAL
[legacy] extra in pyproject.toml; the live organic stack doesn't need it).
Install with `pip install -e .[legacy]` to exercise this test alongside the
organic suite. The pytest.importorskip at module top means the test gracefully
no-ops in a torch-free install rather than ImportError-ing the whole pytest run.
"""
import pytest

torch = pytest.importorskip("torch")  # audit-C2 quarantine: torch optional via [legacy] extra

from project_x.config import ModelConfig
from project_x.legacy.transformer_scaffolding import ProjectXModel


def test_forward_shape():
    config = ModelConfig(vocab_size=32, dim=32, depth=2, heads=4, memory_slots=4, max_seq_len=16)
    model = ProjectXModel(config)
    tokens = torch.randint(0, config.vocab_size, (2, 8))
    logits, router_logits = model(tokens)
    assert logits.shape == (2, 8, config.vocab_size)
    assert len(router_logits) == config.depth
