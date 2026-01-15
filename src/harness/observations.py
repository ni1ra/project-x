"""
Jarvis Harness Observations

Byte-encoded observations for the tool-using agent:
- Last N lines of terminal output
- Compact filesystem snapshot (hashed directory listing)
- Current goal string
- Tool budget remaining (energy, time, actions)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict
import hashlib
import os

import torch


@dataclass
class JarvisObservation:
    """Structured observation before byte encoding."""
    terminal_output: str = ""          # Last N lines of terminal
    fs_snapshot: Dict[str, str] = None  # file -> hash mapping
    goal: str = ""                      # Current goal/task description
    energy_remaining: float = 1.0       # Energy budget [0, 1]
    time_remaining: float = 1.0         # Time budget [0, 1]
    actions_remaining: int = 100        # Action budget
    step: int = 0                       # Current step in episode
    last_reward: float = 0.0            # Previous step's reward
    tests_passing: int = 0              # Number of tests passing
    tests_total: int = 0                # Total tests

    def __post_init__(self):
        if self.fs_snapshot is None:
            self.fs_snapshot = {}


# Observation byte layout
# Total: 512 bytes (configurable)
TERMINAL_BYTES = 256      # Terminal output
GOAL_BYTES = 64           # Goal string
FS_BYTES = 128            # Filesystem snapshot
META_BYTES = 64           # Budget, step, reward, test status
OBS_TOTAL_BYTES = TERMINAL_BYTES + GOAL_BYTES + FS_BYTES + META_BYTES  # 512


def hash_file_content(content: str, max_bytes: int = 16) -> bytes:
    """Hash file content to fixed-size bytes."""
    h = hashlib.md5(content.encode('utf-8', errors='replace')).digest()
    return h[:max_bytes]


def encode_observation(obs: JarvisObservation, max_bytes: int = OBS_TOTAL_BYTES) -> torch.Tensor:
    """
    Encode observation to bytes for the brain.

    Layout (512 bytes):
    - [0:256]: Terminal output (truncated/padded)
    - [256:320]: Goal string (64 bytes)
    - [320:448]: Filesystem snapshot (128 bytes)
    - [448:512]: Metadata (64 bytes)
    """
    result = torch.zeros(max_bytes, dtype=torch.uint8)

    # Terminal output (256 bytes)
    terminal_bytes = obs.terminal_output.encode('utf-8', errors='replace')[-TERMINAL_BYTES:]
    for i, b in enumerate(terminal_bytes):
        result[i] = b

    # Goal string (64 bytes)
    goal_offset = TERMINAL_BYTES
    goal_bytes = obs.goal.encode('utf-8', errors='replace')[:GOAL_BYTES]
    for i, b in enumerate(goal_bytes):
        result[goal_offset + i] = b

    # Filesystem snapshot (128 bytes)
    # Encode as: [file_count, hash1, hash2, ...]
    fs_offset = TERMINAL_BYTES + GOAL_BYTES
    fs_items = list(obs.fs_snapshot.items())[:7]  # Max 7 files × 16 bytes + 16 bytes header
    result[fs_offset] = min(len(fs_items), 255)  # File count

    for i, (path, content_hash) in enumerate(fs_items):
        if isinstance(content_hash, str):
            h = content_hash.encode('utf-8', errors='replace')[:16]
        else:
            h = content_hash
        start = fs_offset + 16 + i * 16
        for j, b in enumerate(h[:16]):
            if isinstance(b, int):
                result[start + j] = b
            else:
                result[start + j] = ord(b) if isinstance(b, str) else b

    # Metadata (64 bytes)
    meta_offset = TERMINAL_BYTES + GOAL_BYTES + FS_BYTES

    # Energy remaining (float16 → 2 bytes)
    energy_int = int(obs.energy_remaining * 65535)
    result[meta_offset] = energy_int & 0xFF
    result[meta_offset + 1] = (energy_int >> 8) & 0xFF

    # Time remaining (float16 → 2 bytes)
    time_int = int(obs.time_remaining * 65535)
    result[meta_offset + 2] = time_int & 0xFF
    result[meta_offset + 3] = (time_int >> 8) & 0xFF

    # Actions remaining (uint16 → 2 bytes)
    result[meta_offset + 4] = obs.actions_remaining & 0xFF
    result[meta_offset + 5] = (obs.actions_remaining >> 8) & 0xFF

    # Step (uint16 → 2 bytes)
    result[meta_offset + 6] = obs.step & 0xFF
    result[meta_offset + 7] = (obs.step >> 8) & 0xFF

    # Last reward (float16 → 2 bytes, scaled)
    reward_scaled = int((obs.last_reward + 10) * 3276.8)  # Scale [-10, 10] to [0, 65535]
    reward_scaled = max(0, min(65535, reward_scaled))
    result[meta_offset + 8] = reward_scaled & 0xFF
    result[meta_offset + 9] = (reward_scaled >> 8) & 0xFF

    # Tests passing (uint8)
    result[meta_offset + 10] = min(obs.tests_passing, 255)

    # Tests total (uint8)
    result[meta_offset + 11] = min(obs.tests_total, 255)

    return result


def decode_observation(obs_bytes: torch.Tensor) -> JarvisObservation:
    """
    Decode bytes to observation.

    Args:
        obs_bytes: Tensor of shape [512] or [N, 512]

    Returns:
        JarvisObservation
    """
    if obs_bytes.dim() == 2:
        obs_bytes = obs_bytes[0]  # Take first if batched

    # Terminal output
    terminal_bytes = obs_bytes[:TERMINAL_BYTES].cpu().numpy().tobytes()
    terminal = terminal_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')

    # Goal string
    goal_offset = TERMINAL_BYTES
    goal_bytes = obs_bytes[goal_offset:goal_offset + GOAL_BYTES].cpu().numpy().tobytes()
    goal = goal_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')

    # Filesystem snapshot (simplified - just file count)
    fs_offset = TERMINAL_BYTES + GOAL_BYTES
    file_count = int(obs_bytes[fs_offset].item())
    fs_snapshot = {f"file_{i}": "hash" for i in range(file_count)}

    # Metadata
    meta_offset = TERMINAL_BYTES + GOAL_BYTES + FS_BYTES

    energy_int = int(obs_bytes[meta_offset].item()) + (int(obs_bytes[meta_offset + 1].item()) << 8)
    energy = energy_int / 65535

    time_int = int(obs_bytes[meta_offset + 2].item()) + (int(obs_bytes[meta_offset + 3].item()) << 8)
    time_remaining = time_int / 65535

    actions_remaining = int(obs_bytes[meta_offset + 4].item()) + (int(obs_bytes[meta_offset + 5].item()) << 8)

    step = int(obs_bytes[meta_offset + 6].item()) + (int(obs_bytes[meta_offset + 7].item()) << 8)

    reward_int = int(obs_bytes[meta_offset + 8].item()) + (int(obs_bytes[meta_offset + 9].item()) << 8)
    last_reward = (reward_int / 3276.8) - 10

    tests_passing = int(obs_bytes[meta_offset + 10].item())
    tests_total = int(obs_bytes[meta_offset + 11].item())

    return JarvisObservation(
        terminal_output=terminal,
        fs_snapshot=fs_snapshot,
        goal=goal,
        energy_remaining=energy,
        time_remaining=time_remaining,
        actions_remaining=actions_remaining,
        step=step,
        last_reward=last_reward,
        tests_passing=tests_passing,
        tests_total=tests_total,
    )


def scan_directory(path: str, max_files: int = 50) -> Dict[str, str]:
    """
    Scan directory and return file→hash mapping.

    Only includes Python files and key config files.
    """
    fs_snapshot = {}

    if not os.path.exists(path):
        return fs_snapshot

    allowed_extensions = {'.py', '.json', '.yaml', '.yml', '.toml', '.txt', '.md'}
    ignore_dirs = {'__pycache__', '.git', '.venv', 'node_modules', '.pytest_cache'}

    for root, dirs, files in os.walk(path):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        for fname in files:
            if len(fs_snapshot) >= max_files:
                break

            ext = os.path.splitext(fname)[1]
            if ext not in allowed_extensions:
                continue

            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, path)

            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                h = hash_file_content(content).hex()
                fs_snapshot[rel_path] = h
            except Exception:
                fs_snapshot[rel_path] = "error"

        if len(fs_snapshot) >= max_files:
            break

    return fs_snapshot
