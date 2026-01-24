"""
Jarvis Harness Actions

Defines the action space for tool-using agent:
- run shell command (constrained grammar)
- read file chunk
- write/patch file chunk
- run unit tests
- search docs
- git operations (checkout, add, commit, etc.)

Actions are byte-encoded for compatibility with RPJ brain.

v2: Extended action space with git operations for multi-file debugging.
"""

from __future__ import annotations

from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Tuple, List
import re

import torch


class ActionType(IntEnum):
    """Action types for Jarvis harness."""
    # Core operations
    SHELL_CMD = 0      # Execute shell command
    READ_FILE = 1      # Read file chunk
    WRITE_FILE = 2     # Write/patch file
    RUN_TESTS = 3      # Run pytest/unittest
    SEARCH = 4         # Search docs/code
    SUBMIT = 5         # Submit solution (episode end)
    NO_OP = 6          # Do nothing (pass)

    # Git operations (v2)
    GIT_STATUS = 7     # Show git status
    GIT_DIFF = 8       # Show diff for file
    GIT_ADD = 9        # Stage file
    GIT_RESET = 10     # Unstage file
    GIT_CHECKOUT = 11  # Discard changes to file
    GIT_LOG = 12       # Show recent commits

    # Multi-file operations (v2)
    LIST_FILES = 13    # List files in directory
    NAVIGATE = 14      # Change focus to different file
    STACKTRACE = 15    # Parse last error stacktrace
    WRITE_FOCUS = 16   # Write/patch relative to current focus buffer
    REPLACE_FOCUS = 17 # Find/replace within the current focus buffer

    # Persistent mode operations (v3)
    COMPLETE_TASK = 18 # Mark current task complete, move to next task in queue
                       # In persistent mode, this doesn't end episode - just advances the task

    # Phase 11: Tool Diversity - Git commit action
    GIT_COMMIT = 19    # Commit staged changes with vocab-based message


# Shell command grammar (constrained for safety)
ALLOWED_SHELL_COMMANDS = [
    'python',           # Run Python
    'python3',          # Run Python (common on Linux/WSL)
    'pip',              # Package management
    'cat',              # View file (limited)
    'ls',               # List directory
    'rg',               # Fast search (ripgrep)
    'grep',             # Search in files
    'head',             # View file start
    'tail',             # View file end
    'wc',               # Word/line count
    'find',             # Find files
    'tree',             # Directory tree
]

# Git commands are now separate action types, not shell commands
# This prevents arbitrary git commands while allowing structured git ops

# Vocabulary definitions for different difficulty levels
# TRIVIAL: Syntax bugs (missing colon, paren, wrong quotes)
TRIVIAL_VOCAB = [':\n', ')', ',', "'", '"']  # 5 items

# EASY: Logic bugs (wrong operators, off-by-one, numeric literals)
# These tokens allow fixing wrong_operator, off_by_one, and numeric literal bugs
EASY_VOCAB = [
    '<=', '>=', '!=', '==',   # comparison operators (4)
    '<', '>',                  # single char comparisons (2)
    '+', '-', '*', '/',        # arithmetic operators (4)
    ' + 1', ' - 1',            # off-by-one fixes with spaces (2)
    '+1', '-1',                # compact off-by-one (2)
    '+ 1', '- 1',              # alternate spacing (2)
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',  # numeric digits (10) - for literal fixes
    # HARD multi-file bug tokens (added 2026-01-23)
    'upper',                   # for data_pipeline secondary fix (lower→upper)
    'del self._users[user_id]',  # for rest_api secondary fix (pass→del)
]  # 28 items

# Phase 9: Python keywords for real repo typo fixes (e.g., retrun→return)
# These are the most common keywords that might have typos
REAL_REPO_VOCAB = [
    'return', 'def', 'class', 'if', 'elif', 'else', 'for', 'while',
    'try', 'except', 'finally', 'with', 'import', 'from', 'True', 'False',
    'None', 'self', 'pass', 'in', 'not', 'and', 'or', 'is', 'as',
    'raise', 'assert', 'yield', 'break', 'continue', 'lambda',
    # Python builtins (common typo targets like 'pritn' -> 'print')
    'print', 'len', 'int', 'str', 'list', 'dict', 'range', 'type',
    'open', 'bool', 'float', 'tuple', 'set', 'enumerate', 'zip', 'map',
]  # 47 items (31 keywords + 16 builtins)

# Combined vocab for training that can handle TRIVIAL, EASY, HARD, and REAL repos
COMBINED_VOCAB = TRIVIAL_VOCAB + EASY_VOCAB + REAL_REPO_VOCAB  # 80 items total (5+28+47)

# Phase 11: Git commit message vocabulary (vocab-based to avoid raw text generation)
GIT_COMMIT_VOCAB = [
    'Fix bug',
    'Fix test',
    'Update logic',
    'Fix comparison',
    'Fix off-by-one',
    'Fix typo',
    'Refactor code',
    'Add feature',
]  # 8 items - model learns to select appropriate message

# MICRO_VOCAB: Comprehensive vocabulary for byte-level edits
# Designed based on frequency analysis of generated Python repos
# Total: ~256 tokens for efficient byte prediction

# ASCII printable characters (32-126 = 95 chars)
ASCII_PRINTABLE = [chr(i) for i in range(32, 127)]  # 95 items

# Common 2-character operators and sequences
COMMON_DIGRAPHS = [
    # Comparison operators
    '==', '!=', '<=', '>=', '<>',
    # Assignment operators
    '+=', '-=', '*=', '/=', '%=', '//=', '**=', '&=', '|=', '^=',
    # Arrow operators
    '->', ':=',
    # Double punctuation
    '""', "''", '()', '[]', '{}', '::', '..', '//',
    # Newline combinations
    ':\n', ')\n', ']\n', '}\n', ',\n', '\n\n',
    # Common spacing patterns
    '  ', '\n ', ' =', '= ', ', ', ': ',
]  # ~32 items

# Common Python keywords and builtins
PYTHON_KEYWORDS = [
    'def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try', 'except',
    'finally', 'with', 'return', 'yield', 'import', 'from', 'as', 'is',
    'in', 'not', 'and', 'or', 'True', 'False', 'None', 'self', 'pass',
    'break', 'continue', 'raise', 'assert', 'lambda', 'async', 'await',
]  # 35 items

# Common Python builtins
PYTHON_BUILTINS = [
    'int', 'str', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
    'len', 'range', 'print', 'type', 'open', 'isinstance', 'hasattr',
    'getattr', 'setattr', 'enumerate', 'zip', 'map', 'filter', 'sorted',
]  # 23 items

# Common identifier fragments (for completion/typo fixes)
COMMON_FRAGMENTS = [
    'self.', 'cls.', '__init__', '__name__', '__main__',
    'def ', 'class ', 'import ', 'from ', 'return ',
    'if ', 'for ', 'while ', 'with ', 'try:', 'except:',
    '(self', ', self', 'self)', 'self,',
    '    ', '        ',  # 4 and 8 space indents
]  # ~20 items

# Numeric literals
COMMON_NUMBERS = [
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    '10', '100', '1000', '0.0', '1.0', '0.5',
    ' + 1', ' - 1', ' * 2', ' / 2',
]  # 20 items

# Common typo fixes (pairs: wrong -> correct)
TYPO_FIXES = [
    # Common Python typos
    'retrun', 'return',  # These are separate - use position
    'improt', 'import',
    'defitn', 'define',
    'fucntion', 'function',
    'calss', 'class',
    'slef', 'self',
    'treu', 'true',
    'fasle', 'false',
    'nonee', 'None',
]  # These are examples - vocab just contains the correct versions

# Build MICRO_VOCAB from components (deduplicated)
_micro_vocab_set = set()
_micro_vocab_set.update(ASCII_PRINTABLE)
_micro_vocab_set.update(COMMON_DIGRAPHS)
_micro_vocab_set.update(PYTHON_KEYWORDS)
_micro_vocab_set.update(PYTHON_BUILTINS)
_micro_vocab_set.update(COMMON_FRAGMENTS)
_micro_vocab_set.update(COMMON_NUMBERS)

# Sort by length (shorter first) then alphabetically for determinism
MICRO_VOCAB = sorted(list(_micro_vocab_set), key=lambda x: (len(x), x))  # ~230 items


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
    elif action.action_type == ActionType.NAVIGATE:
        # NAVIGATE uses target for file path (HARD multi-file bugs)
        target_content = action.target
    elif action.action_type in (ActionType.WRITE_FILE, ActionType.WRITE_FOCUS, ActionType.REPLACE_FOCUS):
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

    Note:
        Supports vocab-based content decoding for WRITE_FOCUS/WRITE_FILE actions.
        If bytes 5-24 are zeros and byte 25 contains a vocab index, the content
        is looked up from COMBINED_VOCAB. This enables BC training with vocab
        indices in 32-byte action format.
    """
    # Convert numpy to tensor if needed
    if not isinstance(action_bytes, torch.Tensor):
        action_bytes = torch.tensor(action_bytes, dtype=torch.uint8)

    if action_bytes.dim() == 2:
        action_bytes = action_bytes[0]  # Take first if batched

    # Action type
    action_type_val = int(action_bytes[0].item())
    action_type = ActionType(action_type_val % len(ActionType))

    # Offset - use full byte range for focus windows up to 256 chars
    offset = int(action_bytes[1].item())

    # Length - expanded to 0-15 for Phase 9 typo fixes (matches v2 decoder)
    length = int(action_bytes[3].item()) % 16

    # Target/content
    target_bytes = action_bytes[5:].cpu().numpy().tobytes()
    target_content = target_bytes.split(b'\x00')[0].decode('utf-8', errors='replace')

    # Vocab-based content decoding for WRITE actions
    # If raw content is empty but byte 25 has a value, use vocab lookup
    # This supports BC training with vocab_idx in byte 25
    if action_type in [ActionType.WRITE_FILE, ActionType.WRITE_FOCUS, ActionType.REPLACE_FOCUS]:
        if not target_content and len(action_bytes) > 25:
            vocab_idx = int(action_bytes[25].item())
            vocab_mode = int(action_bytes[26].item()) if len(action_bytes) > 26 else 0

            if vocab_mode == 1 and vocab_idx > 0:
                # MICRO_VOCAB mode
                vocab_idx = vocab_idx % len(MICRO_VOCAB)
                target_content = MICRO_VOCAB[vocab_idx]
            elif vocab_idx > 0 or (vocab_idx == 0 and action_bytes[25].item() == 0):
                # COMBINED_VOCAB mode (default)
                # Check if byte 25 was intentionally set (even if 0)
                vocab_idx = vocab_idx % len(COMBINED_VOCAB)
                target_content = COMBINED_VOCAB[vocab_idx]

    if action_type == ActionType.READ_FILE:
        length = max(1, length)  # At least 1 byte
    else:
        length = max(0, length)

    return JarvisAction(
        action_type=action_type,
        target=target_content if action_type in [ActionType.READ_FILE, ActionType.SEARCH] else "",
        content=target_content if action_type in [ActionType.SHELL_CMD, ActionType.WRITE_FILE, ActionType.WRITE_FOCUS, ActionType.REPLACE_FOCUS] else "",
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
    elif action.action_type == ActionType.WRITE_FOCUS:
        # WRITE_FOCUS ignores absolute file offsets and instead applies the edit relative
        # to the environment's current focus buffer (see env.py).
        return f"WRITE_FOCUS[{action.offset}:{action.offset + action.length}] = '{action.content[:20]}...'"
    elif action.action_type == ActionType.REPLACE_FOCUS:
        return f"REPLACE_FOCUS find='{action.target[:20]}' replace='{action.content[:20]}'"
    elif action.action_type == ActionType.RUN_TESTS:
        return "RUN_TESTS"
    elif action.action_type == ActionType.SEARCH:
        return f"SEARCH: {action.target}"
    elif action.action_type == ActionType.SUBMIT:
        return "SUBMIT"
    elif action.action_type == ActionType.NO_OP:
        return "NO_OP"
    # Git operations
    elif action.action_type == ActionType.GIT_STATUS:
        return "GIT_STATUS"
    elif action.action_type == ActionType.GIT_DIFF:
        return f"GIT_DIFF: {action.target or 'all'}"
    elif action.action_type == ActionType.GIT_ADD:
        return f"GIT_ADD: {action.target}"
    elif action.action_type == ActionType.GIT_RESET:
        return f"GIT_RESET: {action.target}"
    elif action.action_type == ActionType.GIT_CHECKOUT:
        return f"GIT_CHECKOUT: {action.target}"
    elif action.action_type == ActionType.GIT_LOG:
        return "GIT_LOG"
    # Multi-file operations
    elif action.action_type == ActionType.LIST_FILES:
        return f"LIST_FILES: {action.target or '.'}"
    elif action.action_type == ActionType.NAVIGATE:
        return f"NAVIGATE: {action.target}"
    elif action.action_type == ActionType.STACKTRACE:
        return "STACKTRACE"
    # Persistent mode operations (v3)
    elif action.action_type == ActionType.COMPLETE_TASK:
        return "COMPLETE_TASK"
    # Phase 11: Git commit
    elif action.action_type == ActionType.GIT_COMMIT:
        return f"GIT_COMMIT: '{action.content[:30]}...'"
    else:
        return f"UNKNOWN({action.action_type})"


# Action space size for RL
NUM_ACTION_TYPES = len(ActionType)
ACTION_BYTES = 32  # Total bytes per action


# =============================================================================
# Extended Action Encoding (v2) - 64-byte actions for richer content
# =============================================================================

ACTION_BYTES_V2 = 64  # Extended action size for v2


def encode_action_v2(action: JarvisAction, max_bytes: int = ACTION_BYTES_V2) -> torch.Tensor:
    """
    Encode action to bytes (v2 format with 64 bytes).

    Format (64 bytes):
    - byte 0: action_type
    - byte 1-2: offset (uint16)
    - byte 3-4: length (uint16)
    - byte 5-24: target path (20 bytes, null-padded)
    - byte 25-63: content (39 bytes, null-padded)

    This format allows specifying BOTH target and content simultaneously,
    enabling multi-file operations.
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

    # Target path (20 bytes)
    target_bytes = action.target.encode('utf-8')[:20]
    for i, b in enumerate(target_bytes):
        result[5 + i] = b

    # Content (39 bytes)
    content_bytes = action.content.encode('utf-8')[:39]
    for i, b in enumerate(content_bytes):
        result[25 + i] = b

    return result


def encode_action_v2_vocab(
    action_type: ActionType,
    offset: int,
    length: int,
    vocab_idx: int,
    vocab_mode: int = 0,
    max_bytes: int = ACTION_BYTES_V2,
) -> torch.Tensor:
    """
    Encode action using vocabulary index (for BC training).

    Args:
        action_type: ActionType enum value
        offset: Byte offset for edit (0-255)
        length: Replacement length (0-3)
        vocab_idx: Index into vocabulary
        vocab_mode: 0=COMBINED_VOCAB, 1=MICRO_VOCAB
        max_bytes: Action byte size (default 64)

    Returns:
        Tensor of shape [max_bytes]
    """
    result = torch.zeros(max_bytes, dtype=torch.uint8)

    result[0] = action_type.value
    result[1] = offset & 0xFF
    result[2] = (offset >> 8) & 0xFF
    result[3] = length & 0xFF
    result[4] = (length >> 8) & 0xFF

    # Vocab index and mode
    result[25] = vocab_idx & 0xFF
    result[26] = vocab_mode & 0xFF

    return result


def decode_action_v2(action_bytes: torch.Tensor) -> JarvisAction:
    """
    Decode v2 action bytes.

    Args:
        action_bytes: Tensor of shape [64] or [N, 64], or numpy array

    Returns:
        JarvisAction
    """
    # Convert numpy to tensor if needed
    if not isinstance(action_bytes, torch.Tensor):
        action_bytes = torch.tensor(action_bytes, dtype=torch.uint8)

    if action_bytes.dim() == 2:
        action_bytes = action_bytes[0]

    # Action type
    action_type_val = int(action_bytes[0].item())
    action_type = ActionType(action_type_val % len(ActionType))

    # Offset - use full byte range (0-255) to support focus windows up to 256 chars.
    # CRITICAL FIX (2026-01-17): % 32 was causing offset aliasing - bugs at position 45
    # would be encoded as 13, causing incorrect edits. Now using full byte.
    offset = int(action_bytes[1].item())  # Full 8-bit offset (0-255)

    # Length - expanded to 0-15 for Phase 9 typo fixes (was 0-3)
    # 0 = insert, 1-15 = replace up to 15 chars (covers most keyword typos)
    length = int(action_bytes[3].item()) % 16  # 4-bit length

    # Target (bytes 5-24)
    target_bytes = action_bytes[5:25].cpu().numpy().tobytes()
    target = target_bytes.split(b'\x00')[0].decode('utf-8', errors='replace')

    # Content (bytes 25-63)
    # Vocabulary-based content: Map first content byte to a fix vocabulary.
    # This lets the model learn "which fix to apply" instead of raw bytes.
    #
    # Vocabulary selection strategy:
    #   - Byte 25: vocab index (primary token selector)
    #   - Byte 26: vocab mode (0=COMBINED_VOCAB/legacy, 1=MICRO_VOCAB)
    #
    # For backwards compatibility:
    #   - If byte 26 is 0 or unset, use COMBINED_VOCAB (21 items)
    #   - If byte 26 is 1, use MICRO_VOCAB (219 items)
    content_raw = action_bytes[25:].cpu().numpy()
    if len(content_raw) > 0:
        vocab_idx = int(content_raw[0])
        vocab_mode = int(content_raw[1]) if len(content_raw) > 1 else 0

        # Phase 11: GIT_COMMIT uses GIT_COMMIT_VOCAB for commit messages
        if action_type == ActionType.GIT_COMMIT:
            vocab_idx = vocab_idx % len(GIT_COMMIT_VOCAB)
            content = GIT_COMMIT_VOCAB[vocab_idx]
        else:
            # FIX (2026-01-23): Force COMBINED_VOCAB mode for EASY curriculum.
            # The model outputs garbage in byte[26] (vocab_mode) due to insufficient supervision.
            # Since all EASY tasks use COMBINED_VOCAB, forcing mode=0 fixes the content lookup.
            # TODO: Improve BC training to supervise vocab_mode byte properly.
            vocab_mode = 0  # Force COMBINED_VOCAB

            if vocab_mode == 1:
                # MICRO_VOCAB mode: 219 tokens for byte-level edits
                vocab_idx = vocab_idx % len(MICRO_VOCAB)
                content = MICRO_VOCAB[vocab_idx]
            else:
                # COMBINED_VOCAB mode (31 items: TRIVIAL + EASY + digits)
                vocab_idx = vocab_idx % len(COMBINED_VOCAB)
                content = COMBINED_VOCAB[vocab_idx]
    else:
        content = ''

    if action_type == ActionType.READ_FILE:
        length = max(1, length)
    else:
        length = max(0, length)

    return JarvisAction(
        action_type=action_type,
        target=target,
        content=content,
        offset=offset,
        length=length,
    )


def is_git_action(action_type: ActionType) -> bool:
    """Check if action type is a git operation."""
    return action_type in [
        ActionType.GIT_STATUS,
        ActionType.GIT_DIFF,
        ActionType.GIT_ADD,
        ActionType.GIT_RESET,
        ActionType.GIT_CHECKOUT,
        ActionType.GIT_LOG,
        ActionType.GIT_COMMIT,  # Phase 11
    ]


def is_multi_file_action(action_type: ActionType) -> bool:
    """Check if action type relates to multi-file operations."""
    return action_type in [
        ActionType.LIST_FILES,
        ActionType.NAVIGATE,
        ActionType.STACKTRACE,
    ]
