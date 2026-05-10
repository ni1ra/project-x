"""Smoke entry-point for the Phase 1-6 legacy transformer scaffolding (ProjectXModel).

QUARANTINED — torch-dependent. Torch is an OPTIONAL `[legacy]` extra in
pyproject.toml (audit-C2); install via `pip install -e .[legacy]` to run this.
The live Phase 9-10 organic stack does NOT need this entry-point — it has its
own benchmarks under `experiments/` and `gpt-codex/benchmark/`.
"""

from __future__ import annotations

import json
import random

import numpy as np
import torch
from torch.nn import functional as F

from project_x.config import ModelConfig, RunConfig
from project_x.legacy.transformer_scaffolding import ProjectXModel


def main() -> None:
    run = RunConfig()
    random.seed(run.seed)
    np.random.seed(run.seed)
    torch.manual_seed(run.seed)

    config = ModelConfig()
    model = ProjectXModel(config)
    optim = torch.optim.AdamW(model.parameters(), lr=3e-4)

    losses: list[float] = []
    for _ in range(run.steps):
        tokens = torch.randint(0, config.vocab_size, (run.batch_size, run.seq_len + 1))
        x = tokens[:, :-1]
        y = tokens[:, 1:]
        logits, router_logits = model(x)
        lm_loss = F.cross_entropy(logits.reshape(-1, config.vocab_size), y.reshape(-1))
        router_loss = sum(t.float().var(dim=-1).mean() for t in router_logits) * 1e-4
        loss = lm_loss + router_loss
        optim.zero_grad(set_to_none=True)
        loss.backward()
        optim.step()
        losses.append(float(loss.detach()))

    print(json.dumps({"status": "ok", "losses": losses}, indent=2))


if __name__ == "__main__":
    main()

