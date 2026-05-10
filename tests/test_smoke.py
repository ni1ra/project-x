from project_x.config import ModelConfig
from project_x.legacy.transformer_scaffolding import ProjectXModel


def test_forward_shape():
    import torch

    config = ModelConfig(vocab_size=32, dim=32, depth=2, heads=4, memory_slots=4, max_seq_len=16)
    model = ProjectXModel(config)
    tokens = torch.randint(0, config.vocab_size, (2, 8))
    logits, router_logits = model(tokens)
    assert logits.shape == (2, 8, config.vocab_size)
    assert len(router_logits) == config.depth

