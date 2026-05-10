"""Task registry for compressed_memory experiments.

Each task is a callable `(cfg, device) -> (input_tensor, target_tensor)` that produces
a batch where the model's last-position prediction tests a specific retrieval property.

Tasks
-----
- `long-range-copy` (default, phase 1-7 baseline): plant a key at position 0, marker
  (token=1) at a random position in the back half, and require the model to predict
  the key at the final position. Tests basic delayed associative recall.

- `key-noise`: same as long-range-copy, but with `noise_frac` of probe positions having
  the original key replaced by a random non-marker token at the marker location. Tests
  selector robustness when the retrieval cue is corrupted.

- `multi-key`: plant 2-3 keys at distinct random positions in the first half of the
  sequence, with markers at distinct positions in the second half. The truth is the
  value associated with the FIRST key. Tests multi-pattern Hopfield retrieval — does
  the selector commit to the right pattern when multiple are available?

Adding a new task: add an entry to TASK_REGISTRY with a callable matching the
`(cfg, device) -> (Tensor, Tensor)` signature.
"""
from __future__ import annotations

from typing import Callable

import torch


def _make_batch_long_range_copy(cfg, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    """Phase 1-7 baseline. Key at pos 0, marker (token=1) at random back-half pos,
    truth = same key at final position."""
    tokens = torch.randint(4, cfg.vocab_size, (cfg.batch_size, cfg.seq_len + 1), device=device)
    key = torch.randint(4, cfg.vocab_size, (cfg.batch_size,), device=device)
    tokens[:, 0] = key
    marker_pos = torch.randint(cfg.seq_len // 4, cfg.seq_len - 1, (cfg.batch_size,), device=device)
    batch_idx = torch.arange(cfg.batch_size, device=device)
    tokens[batch_idx, marker_pos] = 1
    tokens[:, -1] = key
    return tokens[:, :-1], tokens[:, 1:]


def _make_batch_key_noise(cfg, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    """Like long-range-copy but with `cfg.task_noise_frac` (default 0.10) of batch
    samples having the key at pos 0 replaced by a random non-marker token. The truth
    at the final position remains the ORIGINAL key — model must still produce the
    correct answer despite a corrupted retrieval cue."""
    noise_frac = getattr(cfg, "task_noise_frac", 0.10)
    tokens = torch.randint(4, cfg.vocab_size, (cfg.batch_size, cfg.seq_len + 1), device=device)
    key = torch.randint(4, cfg.vocab_size, (cfg.batch_size,), device=device)
    tokens[:, 0] = key
    # Corrupt the cue (pos 0) for a fraction of samples — replace with a random non-marker token
    n_noise = int(cfg.batch_size * noise_frac)
    if n_noise > 0:
        noise_idx = torch.randperm(cfg.batch_size, device=device)[:n_noise]
        noisy_keys = torch.randint(4, cfg.vocab_size, (n_noise,), device=device)
        tokens[noise_idx, 0] = noisy_keys
    marker_pos = torch.randint(cfg.seq_len // 4, cfg.seq_len - 1, (cfg.batch_size,), device=device)
    batch_idx = torch.arange(cfg.batch_size, device=device)
    tokens[batch_idx, marker_pos] = 1
    tokens[:, -1] = key  # truth remains the ORIGINAL uncorrupted key
    return tokens[:, :-1], tokens[:, 1:]


def _make_batch_multi_key(cfg, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    """Plant `n_keys` (default 2) keys at distinct positions in the first half, with
    markers at distinct positions in the second half. Truth = value associated with
    the FIRST key (pos 0). Tests multi-pattern retrieval — model must select the
    correct pattern despite competing planted keys."""
    n_keys = getattr(cfg, "task_n_keys", 2)
    n_keys = max(2, min(n_keys, cfg.seq_len // 4))  # bound between 2 and seq_len/4
    tokens = torch.randint(4, cfg.vocab_size, (cfg.batch_size, cfg.seq_len + 1), device=device)
    batch_idx = torch.arange(cfg.batch_size, device=device)
    # First key is the truth-key at pos 0
    truth_key = torch.randint(4, cfg.vocab_size, (cfg.batch_size,), device=device)
    tokens[:, 0] = truth_key
    # Additional decoy keys at random first-half positions
    half = cfg.seq_len // 2
    for k_idx in range(1, n_keys):
        pos = torch.randint(1, max(2, half), (cfg.batch_size,), device=device)
        decoy_key = torch.randint(4, cfg.vocab_size, (cfg.batch_size,), device=device)
        tokens[batch_idx, pos] = decoy_key
    # Marker at random back-half position
    marker_pos = torch.randint(half, cfg.seq_len - 1, (cfg.batch_size,), device=device)
    tokens[batch_idx, marker_pos] = 1
    # Truth at final position is the FIRST key
    tokens[:, -1] = truth_key
    return tokens[:, :-1], tokens[:, 1:]


TASK_REGISTRY: dict[str, Callable] = {
    "long-range-copy": _make_batch_long_range_copy,
    "key-noise": _make_batch_key_noise,
    "multi-key": _make_batch_multi_key,
}


def make_batch(cfg, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    """Dispatch to the task implementation based on `cfg.task`. Default 'long-range-copy'
    preserves backward-compat for all phase 1-7 cells."""
    task_name = getattr(cfg, "task", "long-range-copy")
    impl = TASK_REGISTRY.get(task_name)
    if impl is None:
        raise ValueError(f"Unknown task '{task_name}'. Available: {list(TASK_REGISTRY.keys())}")
    return impl(cfg, device)
