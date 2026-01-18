"""
Expert Trajectory Generator for Behavioral Cloning

Generates expert (correct) action sequences for known bugs.
Used to bootstrap the agent with behavioral cloning before RL fine-tuning.

The key insight is that for TRIVIAL bugs, we can compute the exact correct action:
- offset: position within the focus window where the fix should be applied
- vocab_idx: index into TRIVIAL_VOCAB (e.g., 0 for ':\n')
- length: usually 0 for insert operations

This allows supervised pre-training on expert demonstrations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import torch

from src.harness.actions import (
    ActionType, JarvisAction, ACTION_BYTES_V2,
    encode_action_v2, decode_action_v2,
    TRIVIAL_VOCAB, EASY_VOCAB, COMBINED_VOCAB,  # Vocab definitions
)
from src.harness.bug_templates import BugDifficulty, BugCategory
from src.harness.repo_generator import (
    GeneratedRepo, generate_task_batch, RepoGenerator,
    inject_missing_colon, inject_wrong_quote, inject_missing_paren, inject_typo_keyword,
    inject_wrong_operator, inject_off_by_one,  # EASY bug injectors
)
from src.harness.observations import OBS_TOTAL_BYTES, encode_observation, JarvisObservation


@dataclass
class ExpertAction:
    """A single expert action with ground truth labels."""
    offset: int           # Position within focus window
    vocab_idx: int        # Index into TRIVIAL_VOCAB
    length: int           # Replacement length (0 = insert)
    action_bytes: torch.Tensor  # Encoded action bytes

    @property
    def content(self) -> str:
        return TRIVIAL_VOCAB[self.vocab_idx]


@dataclass
class ExpertTrajectory:
    """An expert trajectory for a single bug fix."""
    repo_name: str
    bug_type: str
    original_code: str
    buggy_code: str
    fix_description: str

    # Focus window info
    focus_file: str
    focus_offset: int     # Byte offset in file where focus starts
    focus_text: str       # Text in focus window

    # The correct fix action
    correct_action: ExpertAction

    # Observation that would be seen
    observation: torch.Tensor


def find_diff_position(original: str, buggy: str) -> int:
    """Find the global position of the first difference between original and buggy."""
    min_len = min(len(original), len(buggy))
    for i in range(min_len):
        if original[i] != buggy[i]:
            return i
    # Difference is at the end (one string is longer)
    return min_len


def compute_focus_start_centered(diff_pos: int, file_length: int, target_offset: int = 16) -> int:
    """
    DEPRECATED: Use compute_focus_start_line_based instead to match env behavior.

    Compute focus_start so that the diff is centered within the 0-31 offset range.

    Args:
        diff_pos: Global position of the diff/bug in the file
        file_length: Total length of the file
        target_offset: Where in the focus window we want the bug (default 16 = center of 0-31)

    Returns:
        focus_start: Position to start the focus window
    """
    # We want: diff_pos - focus_start = target_offset
    # So: focus_start = diff_pos - target_offset
    focus_start = diff_pos - target_offset
    # Clamp to valid range
    focus_start = max(0, focus_start)
    return focus_start


def compute_focus_start_line_based(content: str, bug_line: int, jitter: int = 0) -> int:
    """
    Compute focus_start matching how the env does it (line-start based).

    This matches env.py's _set_focus_from_location behavior:
    - Split content into lines
    - Sum lengths of lines before bug_line
    - Focus starts at the beginning of the bug line

    Args:
        content: The file content
        bug_line: 1-indexed line number of the bug
        jitter: If > 0, add random jitter +/- this value (for curriculum robustness)

    Returns:
        focus_start: Position to start the focus window (start of bug line)
    """
    lines = content.splitlines(True)
    if not lines:
        return 0

    line_idx = max(0, min(bug_line - 1, len(lines) - 1))

    offset = 0
    for i in range(line_idx):
        offset += len(lines[i])

    # Apply jitter if configured (for curriculum robustness)
    if jitter > 0:
        import random
        jitter_val = random.randint(-jitter, jitter)
        offset = max(0, min(len(content) - 1, offset + jitter_val))

    return offset


def compute_fix_offset_in_focus(
    original: str,
    buggy: str,
    focus_start: int,
    focus_length: int = 256,
) -> Tuple[int, str, str]:
    """
    Find where the bug is within the focus window.

    Returns:
        (offset_in_focus, removed_char, needed_char)
        - offset_in_focus: position in focus window where fix should go
        - removed_char: what was removed (for debugging)
        - needed_char: what needs to be inserted
    """
    # Find first difference
    diff_pos = find_diff_position(original, buggy)

    # What was removed?
    if len(original) > len(buggy):
        removed = original[diff_pos]
    else:
        removed = ""

    # What needs to be inserted?
    if len(original) > len(buggy):
        needed = original[diff_pos]
    else:
        needed = ""

    # Compute offset relative to focus start
    offset_in_focus = diff_pos - focus_start

    return offset_in_focus, removed, needed


def get_vocab_idx_for_fix(fix_char: str) -> int:
    """Map fix character(s) to TRIVIAL_VOCAB index."""
    # Try exact match first
    for idx, vocab in enumerate(TRIVIAL_VOCAB):
        if vocab == fix_char:
            return idx

    # Try with newline appended (common for colon fixes)
    fix_with_newline = fix_char + '\n'
    for idx, vocab in enumerate(TRIVIAL_VOCAB):
        if vocab == fix_with_newline:
            return idx

    # Try partial match
    for idx, vocab in enumerate(TRIVIAL_VOCAB):
        if vocab.startswith(fix_char) or fix_char.startswith(vocab):
            return idx

    # No match found - return -1 to indicate unfixable with current vocab
    # Caller should reject this sample (curriculum closure filter)
    return -1


def compute_correct_action_for_missing_colon(
    original: str,
    buggy: str,
    focus_start: int,
) -> ExpertAction:
    """
    Compute the exact correct action for a missing colon bug.

    The bug removes ':' from 'def foo():' -> 'def foo()'
    The fix is to insert ':\n' at the position right after ')'.
    """
    # Find where colon was removed
    offset_in_focus, removed, needed = compute_fix_offset_in_focus(
        original, buggy, focus_start
    )

    # For missing colon, we need ':\n' (vocab index 0)
    vocab_idx = 0  # ':\n'

    # Insert mode (length = 0)
    length = 0

    # Create action bytes
    # CRITICAL FIX (2026-01-17): Use full byte range for offset, not % 32
    action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
    action_bytes[0] = ActionType.WRITE_FOCUS.value
    action_bytes[1] = max(0, min(255, offset_in_focus))  # Full 8-bit offset (clamped to 0-255)
    action_bytes[3] = length % 4            # Constrained length
    action_bytes[25] = vocab_idx            # Content vocab index

    return ExpertAction(
        offset=offset_in_focus,
        vocab_idx=vocab_idx,
        length=length,
        action_bytes=action_bytes,
    )


def compute_correct_action_for_wrong_quote(
    original: str,
    buggy: str,
    focus_start: int,
) -> Optional[ExpertAction]:
    """
    Compute correct action for mismatched quote bug.

    The bug changes a quote type (e.g., closing ' to " or vice versa).
    The fix is to replace the wrong quote with the correct one.

    TRIVIAL++ now supports quotes: vocab_idx=3 for ', vocab_idx=4 for "
    """
    offset_in_focus, removed, needed = compute_fix_offset_in_focus(
        original, buggy, focus_start
    )

    # Find the diff position in the original to see what quote was there
    diff_pos = find_diff_position(original, buggy)
    if diff_pos >= len(original):
        return None

    correct_char = original[diff_pos]

    # Map to vocab index
    if correct_char == "'":
        vocab_idx = 3  # single quote
    elif correct_char == '"':
        vocab_idx = 4  # double quote
    else:
        # Not a quote fix - can't handle
        return None

    # Replace mode (length = 1) since we're replacing the wrong quote
    length = 1

    action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
    action_bytes[0] = ActionType.WRITE_FOCUS.value
    action_bytes[1] = max(0, min(255, offset_in_focus))  # Full 8-bit offset
    action_bytes[3] = length % 4
    action_bytes[25] = vocab_idx

    return ExpertAction(
        offset=offset_in_focus,
        vocab_idx=vocab_idx,
        length=length,
        action_bytes=action_bytes,
    )


def compute_correct_action_for_missing_paren(
    original: str,
    buggy: str,
    focus_start: int,
) -> ExpertAction:
    """
    Compute correct action for missing closing parenthesis.

    The fix is to insert ')' (vocab index 1 in reduced vocab).
    """
    offset_in_focus, removed, needed = compute_fix_offset_in_focus(
        original, buggy, focus_start
    )

    vocab_idx = 1  # ')' in reduced TRIVIAL_VOCAB [':\n', ')', ',', '']
    length = 0     # Insert mode

    # CRITICAL FIX (2026-01-17): Use full byte range for offset, not % 32
    action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
    action_bytes[0] = ActionType.WRITE_FOCUS.value
    action_bytes[1] = max(0, min(255, offset_in_focus))  # Full 8-bit offset (clamped to 0-255)
    action_bytes[3] = length % 4
    action_bytes[25] = vocab_idx

    return ExpertAction(
        offset=offset_in_focus,
        vocab_idx=vocab_idx,
        length=length,
        action_bytes=action_bytes,
    )


def compute_correct_action_generic(
    original: str,
    buggy: str,
    focus_start: int,
    fix_hint: str = "",
) -> Optional[ExpertAction]:
    """
    Generic correct action computation.

    Tries to infer the correct vocab index from the difference.
    Returns None if the fix is not in TRIVIAL_VOCAB (curriculum closure).

    TRIVIAL++ VOCAB: [':\n', ')', ',', "'", '"']  # 5 items
    """
    offset_in_focus, removed, needed = compute_fix_offset_in_focus(
        original, buggy, focus_start
    )

    # Find the diff position to detect the character that was changed/removed
    diff_pos = find_diff_position(original, buggy)
    correct_char = original[diff_pos] if diff_pos < len(original) else ""

    # Determine what needs to be inserted/replaced (using 5-item vocab)
    # TRIVIAL_VOCAB = [':\n', ')', ',', "'", '"']
    vocab_idx = -1  # Invalid until matched
    length = 0      # Default: insert mode

    # Check hints first
    if "colon" in fix_hint.lower() or ":" in fix_hint:
        vocab_idx = 0  # ':\n'
    elif "paren" in fix_hint.lower() or ")" in fix_hint:
        vocab_idx = 1  # ')'
    elif "comma" in fix_hint.lower() or "," in fix_hint:
        vocab_idx = 2  # ','
    elif "quote" in fix_hint.lower():
        # Quote fix - need to check which quote
        if correct_char == "'":
            vocab_idx = 3  # single quote
            length = 1     # replace mode
        elif correct_char == '"':
            vocab_idx = 4  # double quote
            length = 1     # replace mode

    # Fallback to character-based detection
    if vocab_idx < 0:
        if correct_char == ":":
            vocab_idx = 0  # ':\n'
        elif correct_char == ")":
            vocab_idx = 1  # ')'
        elif correct_char == ",":
            vocab_idx = 2  # ','
        elif correct_char == "'":
            vocab_idx = 3  # single quote
            length = 1     # replace mode for quotes
        elif correct_char == '"':
            vocab_idx = 4  # double quote
            length = 1     # replace mode for quotes

    # CURRICULUM CLOSURE: Reject samples that can't be fixed with vocab
    if vocab_idx < 0:
        return None

    action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
    action_bytes[0] = ActionType.WRITE_FOCUS.value
    action_bytes[1] = max(0, min(255, offset_in_focus))  # Full 8-bit offset (clamped to 0-255)
    action_bytes[3] = length % 4
    action_bytes[25] = vocab_idx

    return ExpertAction(
        offset=offset_in_focus,
        vocab_idx=vocab_idx,
        length=length,
        action_bytes=action_bytes,
    )


def compute_correct_action_for_wrong_operator(
    original: str,
    buggy: str,
    focus_start: int,
) -> Optional[ExpertAction]:
    """
    Compute correct action for wrong operator bug.

    Handles BOTH directions of operator swaps:
    - >= → > in original (buggy has >, need to replace with >=)
    - > → >= in original (buggy has >=, need to replace with >)

    The fix is to replace the wrong operator in buggy with the correct one from original.

    EASY_VOCAB indices (in COMBINED_VOCAB):
        5: '<=', 6: '>=', 7: '!=', 8: '==', 9: '<', 10: '>'
    """
    # Map operators to vocab indices
    op_to_idx = {
        '<=': 5, '>=': 6, '!=': 7, '==': 8,
        '<': 9, '>': 10, '+': 11, '-': 12, '*': 13, '/': 14,
    }

    # Define operator swap pairs (both directions)
    # Format: (original_op, buggy_op, vocab_idx_for_fix, replace_length)
    swap_pairs = [
        # Two-char to one-char: original has 2-char, buggy has 1-char
        ('>=', '>', 6, 1),   # Fix: replace '>' with '>=' (vocab 6)
        ('<=', '<', 5, 1),   # Fix: replace '<' with '<=' (vocab 5)
        ('==', '=', 8, 1),   # Fix: replace '=' with '==' (vocab 8)
        ('!=', '!', 7, 1),   # Fix: replace '!' with '!=' (vocab 7)

        # One-char to two-char: original has 1-char, buggy has 2-char
        ('>', '>=', 10, 2),  # Fix: replace '>=' with '>' (vocab 10)
        ('<', '<=', 9, 2),   # Fix: replace '<=' with '<' (vocab 9)

        # Same-length swaps: both are 2-char
        ('==', '!=', 8, 2),  # Fix: replace '!=' with '==' (vocab 8)
        ('!=', '==', 7, 2),  # Fix: replace '==' with '!=' (vocab 7)
    ]

    # Find the diff position
    diff_pos = find_diff_position(original, buggy)

    # Check each swap pair
    for orig_op, buggy_op, vocab_idx, replace_len in swap_pairs:
        # Check if this swap pattern matches
        # We need to check around the diff position

        # For 2-char → 1-char (e.g., >= → >)
        # The diff_pos will be at the position of the removed char
        # Look backwards to find the operator
        if len(orig_op) > len(buggy_op):
            # Search for the pattern in both strings
            # The buggy_op should be at diff_pos - 1 or nearby
            for search_start in range(max(0, diff_pos - 3), min(len(buggy), diff_pos + 2)):
                buggy_slice = buggy[search_start:search_start + len(buggy_op)]
                orig_slice = original[search_start:search_start + len(orig_op)]
                if buggy_slice == buggy_op and orig_slice == orig_op:
                    # Found the swap!
                    offset_in_focus = search_start - focus_start
                    if offset_in_focus < 0 or offset_in_focus >= 256:
                        continue

                    action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
                    action_bytes[0] = ActionType.WRITE_FOCUS.value
                    action_bytes[1] = max(0, min(255, offset_in_focus))
                    action_bytes[3] = replace_len % 4
                    action_bytes[25] = vocab_idx

                    return ExpertAction(
                        offset=offset_in_focus,
                        vocab_idx=vocab_idx,
                        length=replace_len,
                        action_bytes=action_bytes,
                    )

        # For 1-char → 2-char (e.g., > → >=)
        # The diff_pos will be at the position of the inserted char
        elif len(orig_op) < len(buggy_op):
            for search_start in range(max(0, diff_pos - 2), min(len(buggy), diff_pos + 2)):
                buggy_slice = buggy[search_start:search_start + len(buggy_op)]
                orig_slice = original[search_start:search_start + len(orig_op)]
                if buggy_slice == buggy_op and orig_slice == orig_op:
                    # Found the swap!
                    offset_in_focus = search_start - focus_start
                    if offset_in_focus < 0 or offset_in_focus >= 256:
                        continue

                    action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
                    action_bytes[0] = ActionType.WRITE_FOCUS.value
                    action_bytes[1] = max(0, min(255, offset_in_focus))
                    action_bytes[3] = replace_len % 4
                    action_bytes[25] = vocab_idx

                    return ExpertAction(
                        offset=offset_in_focus,
                        vocab_idx=vocab_idx,
                        length=replace_len,
                        action_bytes=action_bytes,
                    )

        # Same-length swaps (e.g., == → !=)
        else:
            for search_start in range(max(0, diff_pos - 2), min(len(buggy), diff_pos + 2)):
                buggy_slice = buggy[search_start:search_start + len(buggy_op)]
                orig_slice = original[search_start:search_start + len(orig_op)]
                if buggy_slice == buggy_op and orig_slice == orig_op:
                    offset_in_focus = search_start - focus_start
                    if offset_in_focus < 0 or offset_in_focus >= 256:
                        continue

                    action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
                    action_bytes[0] = ActionType.WRITE_FOCUS.value
                    action_bytes[1] = max(0, min(255, offset_in_focus))
                    action_bytes[3] = replace_len % 4
                    action_bytes[25] = vocab_idx

                    return ExpertAction(
                        offset=offset_in_focus,
                        vocab_idx=vocab_idx,
                        length=replace_len,
                        action_bytes=action_bytes,
                    )

    return None  # No matching operator swap found


def compute_correct_action_for_off_by_one(
    original: str,
    buggy: str,
    focus_start: int,
) -> Optional[ExpertAction]:
    """
    Compute correct action for off-by-one bug.

    Handles BOTH directions:
    1. <= -> < (original has <=, fix: replace < with <=)
    2. < -> <= (original has <, fix: replace <= with <)
    3. >= -> > (original has >=, fix: replace > with >=)
    4. > -> >= (original has >, fix: replace >= with >)
    5. var + 1 -> var (fix: insert ' + 1')

    EASY_VOCAB indices (in COMBINED_VOCAB):
        5: '<=', 6: '>=', 9: '<', 10: '>', 15: ' + 1', 16: ' - 1', 17: '+1'
    """
    diff_pos = find_diff_position(original, buggy)
    offset_in_focus, removed, needed = compute_fix_offset_in_focus(
        original, buggy, focus_start
    )

    # Case 1: <= was replaced with < (original has <=)
    # Count occurrences to detect the swap
    orig_le_count = original.count('<=')
    buggy_le_count = buggy.count('<=')
    orig_lt_count = original.count('<') - orig_le_count  # standalone <
    buggy_lt_count = buggy.count('<') - buggy_le_count

    if orig_le_count > buggy_le_count and buggy_lt_count > orig_lt_count:
        # <= was replaced with < - fix by replacing < with <=
        vocab_idx = 5  # '<=' in COMBINED_VOCAB
        length = 1     # Replace 1 char '<' with 2-char '<='
        action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
        action_bytes[0] = ActionType.WRITE_FOCUS.value
        action_bytes[1] = max(0, min(255, offset_in_focus))
        action_bytes[3] = length % 4
        action_bytes[25] = vocab_idx
        return ExpertAction(offset=offset_in_focus, vocab_idx=vocab_idx, length=length, action_bytes=action_bytes)

    if orig_lt_count > buggy_lt_count and buggy_le_count > orig_le_count:
        # < was replaced with <= - fix by replacing <= with <
        vocab_idx = 9  # '<' in COMBINED_VOCAB
        length = 2     # Replace 2 char '<=' with 1-char '<'
        action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
        action_bytes[0] = ActionType.WRITE_FOCUS.value
        action_bytes[1] = max(0, min(255, offset_in_focus))
        action_bytes[3] = length % 4
        action_bytes[25] = vocab_idx
        return ExpertAction(offset=offset_in_focus, vocab_idx=vocab_idx, length=length, action_bytes=action_bytes)

    # Case 2: >= and > swaps
    orig_ge_count = original.count('>=')
    buggy_ge_count = buggy.count('>=')
    orig_gt_count = original.count('>') - orig_ge_count
    buggy_gt_count = buggy.count('>') - buggy_ge_count

    if orig_ge_count > buggy_ge_count and buggy_gt_count > orig_gt_count:
        # >= was replaced with > - fix by replacing > with >=
        vocab_idx = 6  # '>=' in COMBINED_VOCAB
        length = 1
        action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
        action_bytes[0] = ActionType.WRITE_FOCUS.value
        action_bytes[1] = max(0, min(255, offset_in_focus))
        action_bytes[3] = length % 4
        action_bytes[25] = vocab_idx
        return ExpertAction(offset=offset_in_focus, vocab_idx=vocab_idx, length=length, action_bytes=action_bytes)

    if orig_gt_count > buggy_gt_count and buggy_ge_count > orig_ge_count:
        # > was replaced with >= - fix by replacing >= with >
        vocab_idx = 10  # '>' in COMBINED_VOCAB
        length = 2
        action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
        action_bytes[0] = ActionType.WRITE_FOCUS.value
        action_bytes[1] = max(0, min(255, offset_in_focus))
        action_bytes[3] = length % 4
        action_bytes[25] = vocab_idx
        return ExpertAction(offset=offset_in_focus, vocab_idx=vocab_idx, length=length, action_bytes=action_bytes)

    # Case 3: ' + 1' was removed (insert it back)
    if ' + 1' in original and ' + 1' not in buggy:
        vocab_idx = 15  # ' + 1' in COMBINED_VOCAB
        length = 0      # Insert mode
        action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
        action_bytes[0] = ActionType.WRITE_FOCUS.value
        action_bytes[1] = max(0, min(255, offset_in_focus))
        action_bytes[3] = length % 4
        action_bytes[25] = vocab_idx
        return ExpertAction(offset=offset_in_focus, vocab_idx=vocab_idx, length=length, action_bytes=action_bytes)

    # Case 4: '+1' was removed (insert it back)
    if '+1' in original and '+1' not in buggy:
        vocab_idx = 17  # '+1' in COMBINED_VOCAB
        length = 0      # Insert mode
        action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
        action_bytes[0] = ActionType.WRITE_FOCUS.value
        action_bytes[1] = max(0, min(255, offset_in_focus))
        action_bytes[3] = length % 4
        action_bytes[25] = vocab_idx
        return ExpertAction(offset=offset_in_focus, vocab_idx=vocab_idx, length=length, action_bytes=action_bytes)

    return None  # Can't compute fix for this off-by-one pattern


def generate_expert_trajectory(
    repo: GeneratedRepo,
    focus_length: int = 256,
    jitter: int = 0,
) -> Optional[ExpertTrajectory]:
    """
    Generate an expert trajectory for a single repo/bug.

    Args:
        repo: Generated repo with bugs
        focus_length: Size of focus window
        jitter: If > 0, add random jitter +/- this value to focus offset (for robustness)

    Returns None if the bug type isn't supported or can't compute fix.
    """
    if not repo.bugs:
        return None

    bug = repo.bugs[0]

    # Get original and buggy code
    original = repo.original_files.get(bug.file_path, "")
    buggy = repo.files.get(bug.file_path)
    if buggy is None:
        return None
    buggy_content = buggy.content

    # FIX: Use line-based focus to match env.py behavior.
    # The env sets focus_offset to the start of the bug line (not centered).
    # This ensures BC training matches eval conditions.
    diff_pos = find_diff_position(original, buggy_content)
    focus_start = compute_focus_start_line_based(buggy_content, bug.line_number, jitter=jitter)

    # Get focus text
    focus_text = buggy_content[focus_start:focus_start + focus_length]

    # Compute correct action based on bug type
    # Strategy: First try to detect from the actual diff, then fall back to hints
    fix_hint = repo.fix_description or bug.hint
    fix_hint_lower = fix_hint.lower()

    # Detect from actual code diff (more reliable than hints)
    diff_pos = find_diff_position(original, buggy_content)
    correct_char = original[diff_pos] if diff_pos < len(original) else ""
    correct_two = original[diff_pos:diff_pos+2] if diff_pos+1 < len(original) else correct_char

    # Operator detection: check if diff position has operator-like chars
    operator_chars = {'<', '>', '=', '!', '+', '-', '*', '/'}
    is_operator_fix = correct_char in operator_chars or any(c in correct_two for c in operator_chars)

    action = None

    # TRIVIAL bugs (syntax) - detect from hints first
    if "colon" in fix_hint_lower or correct_char == ":":
        action = compute_correct_action_for_missing_colon(
            original, buggy_content, focus_start
        )
    elif ("paren" in fix_hint_lower and ")" in fix_hint) or correct_char == ")":
        action = compute_correct_action_for_missing_paren(
            original, buggy_content, focus_start
        )
    elif "quote" in fix_hint_lower or correct_char in ("'", '"'):
        action = compute_correct_action_for_wrong_quote(
            original, buggy_content, focus_start
        )

    # EASY bugs (logic) - detect from diff
    if action is None and is_operator_fix:
        # Try wrong_operator first (handles ==, !=, <=, >=, <, >, +, -, etc.)
        action = compute_correct_action_for_wrong_operator(
            original, buggy_content, focus_start
        )
        if action is None:
            # Try off_by_one (handles <= -> <, + 1 insertion, etc.)
            action = compute_correct_action_for_off_by_one(
                original, buggy_content, focus_start
            )

    # Fallback to hint-based detection
    if action is None:
        if "operator" in fix_hint_lower or "change" in fix_hint_lower:
            action = compute_correct_action_for_wrong_operator(
                original, buggy_content, focus_start
            )
        elif "off" in fix_hint_lower or "bounds" in fix_hint_lower or "boundary" in fix_hint_lower or "+ 1" in fix_hint_lower:
            action = compute_correct_action_for_off_by_one(
                original, buggy_content, focus_start
            )

    # Final fallback to generic
    if action is None:
        action = compute_correct_action_generic(
            original, buggy_content, focus_start, fix_hint
        )

    # CURRICULUM CLOSURE: Reject samples that can't be fixed with vocab
    if action is None:
        return None

    # Validate: offset should be in valid range
    if action.offset < 0 or action.offset >= 64:
        # Bug is outside focus window, skip
        return None

    # FIX: Create COMPLETE observation matching RL environment
    # Previously only filled focus_text (320-448) and preview (480-512)
    # Now we fill ALL fields to match what RL sees
    jarvis_obs = JarvisObservation(
        # Terminal: show the buggy code context (like RL would see after a command)
        terminal_output=f"$ cat {bug.file_path}\n{buggy_content[:200]}",
        # Goal: task description
        goal=f"Fix bug: {fix_hint[:60]}",
        # Focus text: the actual code to edit
        focus_text=focus_text,
        focus_preview=focus_text[:32],
        focus_offset=focus_start,
        focus_length=len(focus_text),
        # File hash for identification
        focus_file_hash=bug.file_path.encode('utf-8')[:16],
        # Default values for other fields
        energy_remaining=1.0,
        time_remaining=1.0,
        actions_remaining=100,
        step=0,
        last_reward=0.0,
        tests_passing=0,
        tests_total=1,
    )
    observation = encode_observation(jarvis_obs)

    return ExpertTrajectory(
        repo_name=repo.name,
        bug_type=bug.template.name if bug.template else "unknown",
        original_code=original,
        buggy_code=buggy_content,
        fix_description=fix_hint,
        focus_file=bug.file_path,
        focus_offset=focus_start,
        focus_text=focus_text,
        correct_action=action,
        observation=observation,
    )


def generate_expert_demos(
    num_tasks: int = 1000,
    difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
    seed: int = 42,
    jitter: int = 0,
) -> List[ExpertTrajectory]:
    """
    Generate a batch of expert demonstrations for behavioral cloning.

    Args:
        num_tasks: Number of demonstrations to generate
        difficulty: Bug difficulty level
        seed: Random seed
        jitter: If > 0, add random jitter +/- this value to focus offset (for robustness)

    Returns:
        List of ExpertTrajectory objects with correct actions
    """
    # Generate repos with bugs
    repos = generate_task_batch(
        num_tasks=num_tasks,
        difficulty_range=(difficulty, difficulty),
        seed=seed,
    )

    trajectories = []
    for repo in repos:
        traj = generate_expert_trajectory(repo, jitter=jitter)
        if traj is not None:
            trajectories.append(traj)

    return trajectories


def trajectories_to_tensors(
    trajectories: List[ExpertTrajectory],
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Convert trajectories to tensors for training.

    Returns:
        observations: [N, 512] - observation bytes
        offsets: [N] - correct offset labels
        vocab_idxs: [N] - correct vocab labels
        lengths: [N] - correct length labels
    """
    n = len(trajectories)

    observations = torch.stack([t.observation for t in trajectories])
    offsets = torch.tensor([t.correct_action.offset for t in trajectories], dtype=torch.long)
    vocab_idxs = torch.tensor([t.correct_action.vocab_idx for t in trajectories], dtype=torch.long)
    lengths = torch.tensor([t.correct_action.length for t in trajectories], dtype=torch.long)

    return observations, offsets, vocab_idxs, lengths


def create_bc_dataset(
    num_tasks: int = 1000,
    difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
    seed: int = 42,
    jitter: int = 0,
) -> Dict[str, torch.Tensor]:
    """
    Create a complete behavioral cloning dataset.

    Args:
        num_tasks: Number of demonstrations to generate
        difficulty: Bug difficulty level
        seed: Random seed
        jitter: If > 0, add random jitter +/- this value to focus offset (for robustness)

    Returns dict with:
        - observations: [N, 512]
        - action_bytes: [N, 64] - full action byte sequences
        - offsets: [N] - offset labels for softmax head
        - vocab_idxs: [N] - vocab labels for softmax head
        - lengths: [N] - length labels for softmax head
    """
    trajectories = generate_expert_demos(num_tasks, difficulty, seed, jitter=jitter)

    if not trajectories:
        raise ValueError("No valid trajectories generated")

    observations, offsets, vocab_idxs, lengths = trajectories_to_tensors(trajectories)

    # Also collect full action bytes
    action_bytes = torch.stack([t.correct_action.action_bytes for t in trajectories])

    return {
        "observations": observations,
        "action_bytes": action_bytes,
        "offsets": offsets,
        "vocab_idxs": vocab_idxs,
        "lengths": lengths,
        "num_samples": len(trajectories),
    }


if __name__ == "__main__":
    # Test expert trajectory generation
    print("Generating expert demonstrations...")

    demos = generate_expert_demos(num_tasks=10, difficulty=BugDifficulty.TRIVIAL, seed=42)
    print(f"Generated {len(demos)} expert trajectories")

    for i, demo in enumerate(demos[:3]):
        print(f"\n--- Demo {i+1} ---")
        print(f"Bug type: {demo.bug_type}")
        print(f"Fix: {demo.fix_description}")
        print(f"Correct offset: {demo.correct_action.offset}")
        print(f"Correct vocab: {demo.correct_action.vocab_idx} ({demo.correct_action.content!r})")
        print(f"Focus text preview: {demo.focus_text[:60]!r}...")

    # Test dataset creation
    print("\n\nCreating BC dataset...")
    dataset = create_bc_dataset(num_tasks=100, seed=42)
    print(f"Dataset size: {dataset['num_samples']}")
    print(f"Observations shape: {dataset['observations'].shape}")
    print(f"Offset distribution: {dataset['offsets'].float().mean():.1f} +/- {dataset['offsets'].float().std():.1f}")
    print(f"Vocab distribution: {[(v, (dataset['vocab_idxs'] == v).sum().item()) for v in range(8)]}")
