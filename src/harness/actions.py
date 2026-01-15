"""
Jarvis Harness Actions

Defines the action space for tool-using agent:
- run shell command (constrained grammar)
- read file chunk
- write/patch file chunk
- run unit tests
- search docs

Actions are byte-encoded for compatibility with RPJ brain.
"""

from __future__ import annotations

from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Tuple, List
import re

import torch


class ActionType(IntEnum):
    """Action types for Jarvis harness."""
    SHELL_CMD = 0      # Execute shell command
    READ_FILE = 1      # Read file chunk
    WRITE_FILE = 2     # Write/patch file
    RUN_TESTS = 3      # Run pytest/unittest
    SEARCH = 4         # Search docs/code
    SUBMIT = 5         # Submit solution (episode end)
    NO_OP = 6          # Do nothing (pass)


# Shell command grammar (constrained for safety)
ALLOWED_SHELL_COMMANDS = [
    'python',           # Run Python
    'pip',              # Package management
    'cat',              # View file (limited)
    'ls',               # List directory
    'git diff',         # View changes
    'git status',       # View status
    'grep',             # Search in files
    'head',             # View file start
    'tail',             # View file end
    'wc',               # Word/line count
]


@dataclass
class JarvisAction:
    """Decoded action from bytes."""
    action_type: ActionType
    target: str = ""          # File path or command
    content: str = ""         # Content for write, args for shell
    offset: int = 0           # Byte offset for read/write
    length: int = 256         # Read length


def encode_action(action: JarvisAction, max_bytes: int = 32) -> torch.Tensor:
    """
    Encode action to bytes for the brain.

    Format (32 bytes):
    - byte 0: action_type
    - byte 1-2: offset (uint16)
    - byte 3-4: length (uint16)
    - byte 5-31: target/content (27 bytes, null-padded)
    """
    result = torch.zeros(max_bytes, dtype=torch.uint8)

    # Action type
    result[0] = action.action_type

    # Offset (uint16 little-endian)
    result[1] = action.offset & 0xFF
    result[2] = (action.offset >> 8) & 0xFF

    # Length (uint16 little-endian)
    result[3] = action.length & 0xFF
    result[4] = (action.length >> 8) & 0xFF

    # Target/content (27 bytes)
    if action.action_type == ActionType.SHELL_CMD:
        target_content = action.content
    elif action.action_type == ActionType.READ_FILE:
        target_content = action.target
    elif action.action_type == ActionType.WRITE_FILE:
        # Jarvis Harness v0: WRITE_FILE uses bytes 5-31 as the content/patch payload.
        # The target file may be task-defined (see env.py) since the action only has
        # one payload string slot (BLUEPRINT.md 2.8.2).
        target_content = action.content
    elif action.action_type == ActionType.SEARCH:
        target_content = action.target
    else:
        target_content = ""
    target_bytes = target_content.encode('utf-8')[:27]
    for i, b in enumerate(target_bytes):
        result[5 + i] = b

    return result


def decode_action(action_bytes: torch.Tensor) -> JarvisAction:
    """
    Decode bytes to action.

    Args:
        action_bytes: Tensor of shape [32] or [N, 32]

    Returns:
        JarvisAction
    """
    if action_bytes.dim() == 2:
        action_bytes = action_bytes[0]  # Take first if batched

    # Action type
    action_type_val = int(action_bytes[0].item())
    action_type = ActionType(min(action_type_val, len(ActionType) - 1))

    # Offset
    offset = int(action_bytes[1].item()) + (int(action_bytes[2].item()) << 8)

    # Length
    length = int(action_bytes[3].item()) + (int(action_bytes[4].item()) << 8)

    # Target/content
    target_bytes = action_bytes[5:].cpu().numpy().tobytes()
    target_content = target_bytes.split(b'\x00')[0].decode('utf-8', errors='replace')

    if action_type == ActionType.READ_FILE:
        length = max(1, length)  # At least 1 byte
    else:
        length = max(0, length)

    return JarvisAction(
        action_type=action_type,
        target=target_content if action_type in [ActionType.READ_FILE, ActionType.SEARCH] else "",
        content=target_content if action_type in [ActionType.SHELL_CMD, ActionType.WRITE_FILE] else "",
        offset=offset,
        length=length,
    )


def validate_shell_command(cmd: str) -> Tuple[bool, str]:
    """
    Validate shell command against allowed grammar.

    Returns:
        (is_valid, sanitized_command or error message)
    """
    cmd = cmd.strip()

    if not cmd:
        return False, "Empty command"

    # Check against allowed commands
    for allowed in ALLOWED_SHELL_COMMANDS:
        if cmd.startswith(allowed):
            return True, cmd

    return False, f"Command not in allowed list. Allowed: {ALLOWED_SHELL_COMMANDS}"


def action_to_string(action: JarvisAction) -> str:
    """Human-readable action description."""
    if action.action_type == ActionType.SHELL_CMD:
        return f"SHELL: {action.content}"
    elif action.action_type == ActionType.READ_FILE:
        return f"READ: {action.target}[{action.offset}:{action.offset + action.length}]"
    elif action.action_type == ActionType.WRITE_FILE:
        target = action.target or "<task_target>"
        return f"WRITE: {target}[{action.offset}:{action.offset + action.length}] = '{action.content[:20]}...'"
    elif action.action_type == ActionType.RUN_TESTS:
        return "RUN_TESTS"
    elif action.action_type == ActionType.SEARCH:
        return f"SEARCH: {action.target}"
    elif action.action_type == ActionType.SUBMIT:
        return "SUBMIT"
    elif action.action_type == ActionType.NO_OP:
        return "NO_OP"
    else:
        return f"UNKNOWN({action.action_type})"


# Action space size for RL
NUM_ACTION_TYPES = len(ActionType)
ACTION_BYTES = 32  # Total bytes per action
