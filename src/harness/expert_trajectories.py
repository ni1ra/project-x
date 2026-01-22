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

import random
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


@dataclass
class MultiStepTrajectory:
    """A multi-step trajectory for navigation + fix.

    Step 1: RUN_TESTS - triggers stacktrace, env updates focus to bug location
    Step 2: WRITE_FOCUS - applies the fix at the correct position

    This teaches the agent a "first move" pattern for navigation.
    """
    repo_name: str
    bug_type: str
    fix_description: str

    # List of (observation, action) pairs
    steps: List[Tuple[torch.Tensor, torch.Tensor]]  # [(obs, action), ...]

    # Final state info
    solved: bool  # Would this trajectory solve the bug?


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


def compute_correct_action_for_typo(
    original: str,
    buggy: str,
    focus_start: int,
) -> Optional[ExpertAction]:
    """
    Compute correct action for typo keyword bugs.

    Requires MICRO_VOCAB to fix (vocab_mode=1) since the correct keywords
    like 'return', 'import', etc. are multi-character tokens.

    Examples:
    - 'retrun' -> 'return' (MICRO_VOCAB index for 'return')
    - 'improt' -> 'import' (MICRO_VOCAB index for 'import')
    """
    from src.harness.actions import MICRO_VOCAB

    # Known typo pairs (buggy -> correct)
    typo_pairs = [
        ('retrun', 'return'),
        ('improt', 'import'),
        ('form', 'from'),
        ('calss', 'class'),
        ('elfi', 'elif'),
        ('Ture', 'True'),
        ('Flase', 'False'),
        ('Nonee', 'None'),
        ('slef', 'self'),
        ('defitn', 'define'),
    ]

    # Find which typo is present
    for typo, correct in typo_pairs:
        if typo in buggy and correct in original:
            # Find the typo position in buggy code
            typo_pos = buggy.find(typo)
            if typo_pos < 0:
                continue

            # Compute offset relative to focus start
            offset_in_focus = typo_pos - focus_start
            if offset_in_focus < 0 or offset_in_focus >= 256:
                continue

            # Find the correct token in MICRO_VOCAB
            if correct not in MICRO_VOCAB:
                continue

            vocab_idx = MICRO_VOCAB.index(correct)

            # Replace the typo with correct token
            # Length = len(typo) to replace the entire typo
            length = min(len(typo), 3)  # Constrained to 0-3

            action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
            action_bytes[0] = ActionType.WRITE_FOCUS.value
            action_bytes[1] = max(0, min(255, offset_in_focus))
            action_bytes[3] = length % 4
            action_bytes[25] = vocab_idx
            action_bytes[26] = 1  # MICRO_VOCAB mode

            return ExpertAction(
                offset=offset_in_focus,
                vocab_idx=vocab_idx,
                length=length,
                action_bytes=action_bytes,
            )

    return None


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
        elif "typo" in fix_hint_lower:
            # Typo bugs require MICRO_VOCAB (vocab_mode=1)
            action = compute_correct_action_for_typo(
                original, buggy_content, focus_start
            )

    # Try typo detection as fallback (for EASY bugs with typo injector)
    if action is None:
        action = compute_correct_action_for_typo(
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


def create_run_tests_action() -> torch.Tensor:
    """
    Create a RUN_TESTS action as the first move.

    This teaches the agent to call RUN_TESTS first, which:
    1. Triggers pytest/unittest
    2. Produces a stacktrace (if there are bugs)
    3. The env's auto_focus_from_stacktrace updates focus to bug location

    Returns:
        action_bytes: [ACTION_BYTES_V2] tensor with RUN_TESTS action
    """
    action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
    action_bytes[0] = ActionType.RUN_TESTS.value  # ActionType.RUN_TESTS = 3
    # Other bytes can stay 0 - RUN_TESTS doesn't need offset/length/target/content
    return action_bytes


def create_initial_observation(
    repo_name: str,
    goal: str,
    focus_text: str = "",
    tests_passing: int = 0,
    tests_total: int = 1,
) -> torch.Tensor:
    """
    Create an initial observation for a task (before RUN_TESTS is called).

    The focus_text is intentionally empty or minimal to simulate:
    - Agent starts with no knowledge of where the bug is
    - Must run tests first to discover bug location

    Args:
        repo_name: Name of the repo
        goal: Task description
        focus_text: Initial focus text (can be empty)
        tests_passing: Number of passing tests
        tests_total: Total tests

    Returns:
        observation: [OBS_TOTAL_BYTES] tensor
    """
    jarvis_obs = JarvisObservation(
        # Terminal: match eval env format exactly
        # The eval env (with run_tests_on_reset=False) initializes terminal_buffer to:
        # "Task: {desc}\nRepo ready at {path}\nInitial tests: (skipped)\n"
        terminal_output=f"Task: {goal[:60]}\nRepo ready.\nInitial tests: (skipped)\n",
        # Goal: task description
        goal=f"{goal[:60]}",
        # Focus text: empty or minimal (don't know where bug is yet)
        focus_text=focus_text[:256] if focus_text else "",
        focus_preview=focus_text[:32] if focus_text else "",
        focus_offset=0,
        focus_length=len(focus_text) if focus_text else 0,
        # File hash for identification
        focus_file_hash=repo_name.encode('utf-8')[:16],
        # Default values
        energy_remaining=1.0,
        time_remaining=1.0,
        actions_remaining=100,
        step=0,
        last_reward=0.0,
        tests_passing=tests_passing,
        tests_total=tests_total,
    )
    return encode_observation(jarvis_obs)


def generate_multistep_trajectory(
    repo: GeneratedRepo,
    focus_length: int = 256,
) -> Optional[MultiStepTrajectory]:
    """
    Generate a multi-step trajectory with RUN_TESTS as first action.

    Step 1: RUN_TESTS - triggers stacktrace, env updates focus
    Step 2: WRITE_FOCUS - applies the fix

    Args:
        repo: Generated repo with bugs
        focus_length: Size of focus window

    Returns:
        MultiStepTrajectory with 2 steps, or None if can't generate
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

    # Generate the single-step trajectory to get the correct WRITE_FOCUS action
    single_step = generate_expert_trajectory(repo, focus_length)
    if single_step is None:
        return None

    # Use EXACT same goal format as eval env
    goal = f"Fix the bugs and make tests pass. Hint: {repo.fix_description[:40]}"

    # Step 1: Initial observation (tests not run yet)
    # Agent should call RUN_TESTS to discover where the bug is
    # FIX: Include focus_text to match eval env behavior (auto_focus_target)
    initial_obs = create_initial_observation(
        repo_name=repo.name,
        goal=goal,
        focus_text=buggy_content[:256],  # Match eval env: focus_text is set from start
        tests_passing=0,
        tests_total=0,  # FIX: Match eval env when run_tests_on_reset=False
    )
    run_tests_action = create_run_tests_action()

    # Step 2: After RUN_TESTS, focus is set to bug location by env
    # Agent should call WRITE_FOCUS with the correct fix
    # Use the observation and action from the single-step trajectory
    post_tests_obs = single_step.observation
    write_focus_action = single_step.correct_action.action_bytes

    steps = [
        (initial_obs, run_tests_action),
        (post_tests_obs, write_focus_action),
    ]

    return MultiStepTrajectory(
        repo_name=repo.name,
        bug_type=single_step.bug_type,
        fix_description=single_step.fix_description,
        steps=steps,
        solved=True,
    )


def generate_multistep_demos(
    num_tasks: int = 1000,
    difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
    seed: int = 42,
) -> List[MultiStepTrajectory]:
    """
    Generate multi-step expert demonstrations for navigation + fix.

    Args:
        num_tasks: Number of demonstrations to generate
        difficulty: Bug difficulty level
        seed: Random seed

    Returns:
        List of MultiStepTrajectory objects
    """
    repos = generate_task_batch(
        num_tasks=num_tasks,
        difficulty_range=(difficulty, difficulty),
        seed=seed,
    )

    trajectories = []
    for repo in repos:
        traj = generate_multistep_trajectory(repo)
        if traj is not None:
            trajectories.append(traj)

    return trajectories


def create_multistep_bc_dataset(
    num_tasks: int = 1000,
    difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
    seed: int = 42,
    include_single_step: bool = True,
) -> Dict[str, torch.Tensor]:
    """
    Create a behavioral cloning dataset with multi-step trajectories.

    This flattens all steps into a single dataset, mixing:
    - RUN_TESTS first moves (initial obs -> RUN_TESTS action)
    - WRITE_FOCUS fix moves (post-tests obs -> WRITE_FOCUS action)

    Args:
        num_tasks: Number of demonstrations to generate
        difficulty: Bug difficulty level
        seed: Random seed
        include_single_step: If True, also include single-step demos (for diversity)

    Returns dict with:
        - observations: [N, 512]
        - action_bytes: [N, 64] - full action byte sequences
        - num_samples: int
    """
    multistep_trajs = generate_multistep_demos(num_tasks, difficulty, seed)

    all_obs = []
    all_actions = []

    for traj in multistep_trajs:
        for obs, action in traj.steps:
            all_obs.append(obs)
            all_actions.append(action)

    # Optionally add single-step demos for diversity
    if include_single_step:
        single_trajs = generate_expert_demos(num_tasks // 2, difficulty, seed + 1000)
        for traj in single_trajs:
            all_obs.append(traj.observation)
            all_actions.append(traj.correct_action.action_bytes)

    if not all_obs:
        raise ValueError("No valid trajectories generated")

    observations = torch.stack(all_obs)
    action_bytes = torch.stack(all_actions)

    return {
        "observations": observations,
        "action_bytes": action_bytes,
        "num_samples": len(all_obs),
        "num_run_tests": sum(1 for a in all_actions if a[0] == ActionType.RUN_TESTS.value),
        "num_write_focus": sum(1 for a in all_actions if a[0] == ActionType.WRITE_FOCUS.value),
    }


def create_complete_task_action() -> torch.Tensor:
    """
    Create a COMPLETE_TASK action for signaling task completion.

    This is used after the fix is verified (RUN_TESTS shows all pass).
    The env requires last_test_result.passed=True before COMPLETE_TASK is accepted.

    Returns:
        action_bytes: [ACTION_BYTES_V2] tensor with COMPLETE_TASK action
    """
    action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
    action_bytes[0] = ActionType.COMPLETE_TASK.value  # ActionType.COMPLETE_TASK = 18
    return action_bytes


def create_post_run_tests_observation(
    repo_name: str,
    goal: str,
    focus_text: str,
    focus_offset: int,
    file_path: str,
    tests_passing: int,
    tests_total: int,
    step: int = 1,
) -> torch.Tensor:
    """
    Create an observation for AFTER RUN_TESTS is called.

    This simulates what the eval env shows after running tests:
    - Terminal shows test results (failures with stacktrace)
    - Focus is set to bug location
    - step is incremented

    The agent should emit WRITE_FOCUS in this state.
    """
    # Simulate test failure output (what eval env would show)
    failed = tests_total - tests_passing
    terminal = (
        f"Task: {goal[:60]}\nRepo ready.\nInitial tests: (skipped)\n"
        f"[Step {step - 1}] RUN_TESTS\n"
        f"[Tests completed: fast] {tests_passing}/{tests_total} passing\n"
        f"FAILED - {failed} tests failed\n"
        f"[Focus] {file_path}\n"
    )
    jarvis_obs = JarvisObservation(
        terminal_output=terminal,
        goal=f"{goal[:60]}",
        focus_text=focus_text[:256] if focus_text else "",
        focus_preview=focus_text[:32] if focus_text else "",
        focus_offset=focus_offset,
        focus_length=len(focus_text) if focus_text else 0,
        focus_file_hash=file_path.encode('utf-8')[:16] if file_path else repo_name.encode('utf-8')[:16],
        energy_remaining=0.98,  # Slightly used after 1 action
        time_remaining=0.95,
        actions_remaining=99,  # 1 action taken
        step=step,  # step=1 after first action
        last_reward=-0.1,  # Tests failed
        tests_passing=tests_passing,
        tests_total=tests_total,
    )
    return encode_observation(jarvis_obs)


def create_post_fix_observation(
    repo_name: str,
    goal: str,
    focus_text: str,
    tests_passing: int,
    tests_total: int,
    step: int = 2,
) -> torch.Tensor:
    """
    Create an observation for after WRITE_FOCUS is applied (before verify RUN_TESTS).

    This simulates the state after:
    1. RUN_TESTS (step 0) - discovered bug
    2. WRITE_FOCUS (step 1) - applied fix

    The agent should emit RUN_TESTS in this state to verify.
    """
    terminal = (
        f"Task: {goal[:60]}\nRepo ready.\n"
        f"[Step 1] WRITE_FOCUS\n"
        f"Write OK: Syntax OK\n"
    )
    jarvis_obs = JarvisObservation(
        terminal_output=terminal,
        goal=f"{goal[:60]}",
        focus_text=focus_text[:256] if focus_text else "",
        focus_preview=focus_text[:32] if focus_text else "",
        focus_offset=0,
        focus_length=len(focus_text) if focus_text else 0,
        focus_file_hash=repo_name.encode('utf-8')[:16],
        energy_remaining=0.95,
        time_remaining=0.9,
        actions_remaining=98,  # 2 actions taken
        step=step,
        last_reward=0.5,  # Small reward for valid write
        tests_passing=tests_passing,
        tests_total=tests_total,
    )
    return encode_observation(jarvis_obs)


def create_post_verify_observation(
    repo_name: str,
    goal: str,
    focus_text: str,
    tests_passing: int,
    tests_total: int,
    step: int = 3,
) -> torch.Tensor:
    """
    Create an observation for after verification RUN_TESTS passes.

    This simulates the state after:
    1. RUN_TESTS (step 0) - discovered bug
    2. WRITE_FOCUS (step 1) - applied fix
    3. RUN_TESTS (step 2) - verified fix works

    The agent should emit COMPLETE_TASK in this state.
    """
    terminal = (
        f"Task: {goal[:60]}\nRepo ready.\n"
        f"[Step 2] RUN_TESTS\n"
        f"[Tests completed: fast] {tests_passing}/{tests_total} passing\n"
        f"ALL PASSED\n"
    )
    jarvis_obs = JarvisObservation(
        terminal_output=terminal,
        goal=f"{goal[:60]}",
        focus_text=focus_text[:256] if focus_text else "",
        focus_preview=focus_text[:32] if focus_text else "",
        focus_offset=0,
        focus_length=len(focus_text) if focus_text else 0,
        focus_file_hash=repo_name.encode('utf-8')[:16],
        energy_remaining=0.9,
        time_remaining=0.8,
        actions_remaining=97,  # 3 actions taken
        step=step,
        last_reward=10.0,  # Tests passed!
        tests_passing=tests_passing,
        tests_total=tests_total,
    )
    return encode_observation(jarvis_obs)


@dataclass
class PersistentTrajectory:
    """A 4-step trajectory for the persistent developer loop.

    Step 1: RUN_TESTS - discover bug (triggers stacktrace)
    Step 2: WRITE_FOCUS - apply the fix
    Step 3: RUN_TESTS - verify fix works (tests pass)
    Step 4: COMPLETE_TASK - mark task as done

    This teaches the agent the full persistent mode loop.
    """
    repo_name: str
    bug_type: str
    fix_description: str

    # List of (observation, action) pairs
    steps: List[Tuple[torch.Tensor, torch.Tensor]]  # [(obs, action), ...]

    # Final state info
    solved: bool  # Would this trajectory solve the bug?


def generate_persistent_trajectory(
    repo: GeneratedRepo,
    focus_length: int = 256,
) -> Optional[PersistentTrajectory]:
    """
    Generate a 4-step trajectory for the persistent developer loop.

    Step 1: RUN_TESTS - discover bug
    Step 2: WRITE_FOCUS - apply fix
    Step 3: RUN_TESTS - verify fix
    Step 4: COMPLETE_TASK - mark done

    Args:
        repo: Generated repo with bugs
        focus_length: Size of focus window

    Returns:
        PersistentTrajectory with 4 steps, or None if can't generate
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

    # Generate the single-step trajectory to get the correct WRITE_FOCUS action
    single_step = generate_expert_trajectory(repo, focus_length)
    if single_step is None:
        return None

    # Step 1: Initial observation (tests not run yet)
    # Agent should call RUN_TESTS to discover where the bug is
    # FIX: Include focus_text to match eval env behavior
    # The eval env sets focus_text from the start (auto_focus_target)
    # Model must learn: tests_passing==0 → RUN_TESTS (not empty focus_text → RUN_TESTS)
    # Use EXACT same goal format as eval env
    # Eval uses: f"Fix the bugs and make tests pass. Hint: {repo.fix_description}"
    goal = f"Fix the bugs and make tests pass. Hint: {repo.fix_description[:40]}"

    initial_obs = create_initial_observation(
        repo_name=repo.name,
        goal=goal,
        focus_text=buggy_content[:256],  # Match eval env: focus_text is set from start
        tests_passing=0,
        tests_total=0,  # FIX: Match eval env when run_tests_on_reset=False
    )
    run_tests_action = create_run_tests_action()

    # Step 2: After RUN_TESTS, focus is set to bug location by env
    # Agent should call WRITE_FOCUS with the correct fix
    # FIX: Use proper observation with step=1, not step=0 from single_step
    post_discovery_obs = create_post_run_tests_observation(
        repo_name=repo.name,
        goal=goal,
        focus_text=single_step.focus_text,  # Focus on bug location
        focus_offset=single_step.focus_offset,
        file_path=single_step.focus_file,
        tests_passing=7,  # Some tests pass, but not all
        tests_total=11,
        step=1,  # CRITICAL: After RUN_TESTS, step=1
    )
    write_focus_action = single_step.correct_action.action_bytes

    # Step 3: After WRITE_FOCUS, run tests again to verify
    # Create observation showing code context (post-fix)
    # The agent should call RUN_TESTS again to verify
    post_fix_obs = create_post_fix_observation(
        repo_name=repo.name,
        goal=goal,  # Use consistent goal
        focus_text=original[:focus_length],  # Now shows the fixed code
        tests_passing=7,  # Same as before (haven't run tests yet)
        tests_total=11,
        step=2,  # After WRITE_FOCUS, step=2
    )
    verify_tests_action = create_run_tests_action()

    # Step 4: After verification RUN_TESTS, tests pass
    # Agent should call COMPLETE_TASK
    post_verify_obs = create_post_verify_observation(
        repo_name=repo.name,
        goal=goal,  # Use consistent goal
        focus_text=original[:focus_length],  # Fixed code
        tests_passing=11,  # All tests pass now
        tests_total=11,
        step=3,  # After verify RUN_TESTS, step=3
    )
    complete_task_action = create_complete_task_action()

    steps = [
        (initial_obs, run_tests_action),        # Step 1: RUN_TESTS
        (post_discovery_obs, write_focus_action),  # Step 2: WRITE_FOCUS
        (post_fix_obs, verify_tests_action),     # Step 3: RUN_TESTS (verify)
        (post_verify_obs, complete_task_action),  # Step 4: COMPLETE_TASK
    ]

    return PersistentTrajectory(
        repo_name=repo.name,
        bug_type=single_step.bug_type,
        fix_description=single_step.fix_description,
        steps=steps,
        solved=True,
    )


def generate_persistent_demos(
    num_tasks: int = 1000,
    difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
    seed: int = 42,
) -> List[PersistentTrajectory]:
    """
    Generate persistent mode expert demonstrations.

    Each demo is a 4-step trajectory:
    RUN_TESTS → WRITE_FOCUS → RUN_TESTS → COMPLETE_TASK

    Args:
        num_tasks: Number of demonstrations to generate
        difficulty: Bug difficulty level
        seed: Random seed

    Returns:
        List of PersistentTrajectory objects
    """
    repos = generate_task_batch(
        num_tasks=num_tasks,
        difficulty_range=(difficulty, difficulty),
        seed=seed,
    )

    trajectories = []
    for repo in repos:
        traj = generate_persistent_trajectory(repo)
        if traj is not None:
            trajectories.append(traj)

    return trajectories


def create_sequential_bc_dataset(
    num_tasks: int = 1000,
    difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
    seed: int = 42,
    seq_len: int = 4,
    include_closer_demos: bool = True,
    closer_ratio: float = 0.05,
) -> Dict[str, torch.Tensor]:
    """
    Create a behavioral cloning dataset that preserves trajectory structure.

    This is critical for training RNNs: the model must learn to use its hidden
    state to track where it is in the 4-step loop:
    RUN_TESTS -> WRITE_FOCUS -> RUN_TESTS -> COMPLETE_TASK

    Unlike create_persistent_bc_dataset which flattens to individual samples,
    this returns padded sequences grouped by trajectory.

    ORACLE FIX (420 score): Includes "Closer Demos" - 1-step trajectories where
    OBS[tests_passing=tests_total] -> COMPLETE_TASK. This teaches the model to
    recognize the completion condition from fresh hidden state (h_0), decoupling
    it from sequence position. Without this, COMPLETE_TASK only appears at step 4
    and the model learns it as "what to do after long sequence" rather than
    "what to do when tests pass".

    Args:
        num_tasks: Number of trajectories to generate
        difficulty: Bug difficulty level
        seed: Random seed
        seq_len: Sequence length (default 4 for persistent loop)
        include_closer_demos: If True, add 2-step (RUN_TESTS→COMPLETE_TASK) demos
            Phase 7.5 fix: 2-step avoids h=0 toxic attractor from original 1-step demos
        closer_ratio: Ratio of closer demos to add (default 0.05 = 1:20 ratio)

    Returns dict with:
        - observations: [num_traj, seq_len, 512] - padded sequences
        - action_bytes: [num_traj, seq_len, 64] - padded action sequences
        - masks: [num_traj, seq_len] - boolean mask (True = valid step)
        - num_trajectories: int
        - num_run_tests: int
        - num_write_focus: int
        - num_complete_task: int
    """
    persistent_trajs = generate_persistent_demos(num_tasks, difficulty, seed)

    if not persistent_trajs:
        raise ValueError("No valid trajectories generated")

    # Calculate total trajectories including closer demos
    num_full_traj = len(persistent_trajs)
    num_closer_traj = int(num_full_traj * closer_ratio) if include_closer_demos else 0
    num_traj = num_full_traj + num_closer_traj

    # Pre-allocate tensors
    observations = torch.zeros(num_traj, seq_len, OBS_TOTAL_BYTES, dtype=torch.uint8)
    action_bytes = torch.zeros(num_traj, seq_len, ACTION_BYTES_V2, dtype=torch.long)
    masks = torch.zeros(num_traj, seq_len, dtype=torch.bool)

    num_run_tests = 0
    num_write_focus = 0
    num_complete_task = 0

    # Add full 4-step trajectories
    for i, traj in enumerate(persistent_trajs):
        for step_idx, (obs, action) in enumerate(traj.steps):
            if step_idx >= seq_len:
                break
            observations[i, step_idx] = obs
            action_bytes[i, step_idx] = action
            masks[i, step_idx] = True

            # Count action types
            action_type = action[0].item()
            if action_type == ActionType.RUN_TESTS.value:
                num_run_tests += 1
            elif action_type == ActionType.WRITE_FOCUS.value:
                num_write_focus += 1
            elif action_type == ActionType.COMPLETE_TASK.value:
                num_complete_task += 1

    # Add "Closer Demos" - 2-step (RUN_TESTS → COMPLETE_TASK) trajectories
    # Phase 7.5 fix: Use 2-step instead of 1-step to avoid h=0 toxic attractor.
    # This forces COMPLETE_TASK to be conditioned on post-RUN_TESTS hidden state,
    # not fresh h=0. Keeps the benefit (learning completion reflex) without
    # poisoning the episode start state.
    if include_closer_demos and num_closer_traj > 0:
        # Extract steps 3 and 4 (RUN_TESTS → COMPLETE_TASK) from full trajectories
        # In a 4-step loop: step 2 is RUN_TESTS (verify), step 3 is COMPLETE_TASK
        closer_run_tests_list = []  # Step 2: RUN_TESTS after fix
        closer_complete_task_list = []  # Step 3: COMPLETE_TASK
        for traj in persistent_trajs:
            if len(traj.steps) >= 4:
                # Step 2 (index 2): RUN_TESTS to verify fix
                obs_rt, action_rt = traj.steps[2]
                # Step 3 (index 3): COMPLETE_TASK
                obs_ct, action_ct = traj.steps[3]
                closer_run_tests_list.append((obs_rt, action_rt))
                closer_complete_task_list.append((obs_ct, action_ct))

        # Add 2-step closer demos (sample with replacement if needed)
        random.seed(seed + 9999)  # Different seed for closer sampling
        for i in range(num_closer_traj):
            traj_idx = num_full_traj + i
            # Sample from available closer demos
            src_idx = i % len(closer_run_tests_list)

            # 2-step trajectory: step 0 = RUN_TESTS, step 1 = COMPLETE_TASK
            obs_rt, action_rt = closer_run_tests_list[src_idx]
            obs_ct, action_ct = closer_complete_task_list[src_idx]

            observations[traj_idx, 0] = obs_rt
            action_bytes[traj_idx, 0] = action_rt
            masks[traj_idx, 0] = True

            observations[traj_idx, 1] = obs_ct
            action_bytes[traj_idx, 1] = action_ct
            masks[traj_idx, 1] = True

            num_run_tests += 1  # Count the RUN_TESTS step
            num_complete_task += 1  # Count the COMPLETE_TASK step

    return {
        "observations": observations,  # [N, seq_len, 512]
        "action_bytes": action_bytes,  # [N, seq_len, 64]
        "masks": masks,                # [N, seq_len]
        "num_trajectories": num_traj,
        "num_full_trajectories": num_full_traj,
        "num_closer_demos": num_closer_traj,
        "num_samples": masks.sum().item(),  # Total valid steps
        "num_run_tests": num_run_tests,
        "num_write_focus": num_write_focus,
        "num_complete_task": num_complete_task,
    }


def create_persistent_bc_dataset(
    num_tasks: int = 1000,
    difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
    seed: int = 42,
    include_single_step: bool = False,
) -> Dict[str, torch.Tensor]:
    """
    Create a behavioral cloning dataset with persistent mode trajectories.

    This flattens all steps into a single dataset, mixing:
    - RUN_TESTS first moves (initial obs -> RUN_TESTS action)
    - WRITE_FOCUS fix moves (post-discovery obs -> WRITE_FOCUS action)
    - RUN_TESTS verify moves (post-fix obs -> RUN_TESTS action)
    - COMPLETE_TASK moves (post-verify obs -> COMPLETE_TASK action)

    Args:
        num_tasks: Number of demonstrations to generate
        difficulty: Bug difficulty level
        seed: Random seed
        include_single_step: If True, also include single-step demos (for diversity)

    Returns dict with:
        - observations: [N, 512]
        - action_bytes: [N, 64] - full action byte sequences
        - num_samples: int
        - num_run_tests: int - count of RUN_TESTS actions
        - num_write_focus: int - count of WRITE_FOCUS actions
        - num_complete_task: int - count of COMPLETE_TASK actions
    """
    persistent_trajs = generate_persistent_demos(num_tasks, difficulty, seed)

    all_obs = []
    all_actions = []

    for traj in persistent_trajs:
        for obs, action in traj.steps:
            all_obs.append(obs)
            all_actions.append(action)

    # Optionally add single-step demos for diversity
    if include_single_step:
        single_trajs = generate_expert_demos(num_tasks // 4, difficulty, seed + 1000)
        for traj in single_trajs:
            all_obs.append(traj.observation)
            all_actions.append(traj.correct_action.action_bytes)

    if not all_obs:
        raise ValueError("No valid trajectories generated")

    observations = torch.stack(all_obs)
    action_bytes = torch.stack(all_actions)

    return {
        "observations": observations,
        "action_bytes": action_bytes,
        "num_samples": len(all_obs),
        "num_run_tests": sum(1 for a in all_actions if a[0] == ActionType.RUN_TESTS.value),
        "num_write_focus": sum(1 for a in all_actions if a[0] == ActionType.WRITE_FOCUS.value),
        "num_complete_task": sum(1 for a in all_actions if a[0] == ActionType.COMPLETE_TASK.value),
    }


@dataclass
class OracleAction:
    """Result from the oracle function.

    For on-policy corrective imitation, we need:
    - action_type: What action the expert recommends
    - offset: For WRITE_FOCUS, where to edit (in focus window)
    - vocab_idx: For WRITE_FOCUS, what character to insert
    - action_bytes: Full encoded action for loss computation
    - confidence: How confident the oracle is (1.0 = perfect knowledge)
    """
    action_type: ActionType
    offset: int = 0
    vocab_idx: int = 0
    length: int = 0
    action_bytes: torch.Tensor = None
    confidence: float = 1.0

    def __post_init__(self):
        if self.action_bytes is None:
            self.action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
            self.action_bytes[0] = self.action_type.value
            if self.action_type == ActionType.WRITE_FOCUS:
                self.action_bytes[1] = max(0, min(255, self.offset))
                self.action_bytes[3] = self.length % 4
                self.action_bytes[25] = self.vocab_idx


def get_oracle_action(
    obs_bytes: torch.Tensor,
    original_code: str = None,
    buggy_code: str = None,
    bug_line: int = None,
    difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
) -> OracleAction:
    """
    Compute the expert action for a given observation.

    This is the core function for on-policy corrective imitation (Fix 10).
    Unlike teacher forcing which overrides actions, this provides a supervised
    signal that the model learns from while following its own h_t trajectory.

    Decision logic:
    1. If tests_passing == tests_total > 0: COMPLETE_TASK
    2. If focus_text is empty or no bug visible: RUN_TESTS
    3. If bug is visible in focus_text: WRITE_FOCUS with correct (offset, vocab_idx)

    Args:
        obs_bytes: [512] observation tensor
        original_code: The correct/fixed code (for computing the fix)
        buggy_code: The buggy code (for computing the fix)
        bug_line: Line number where bug is located (1-indexed)
        difficulty: Bug difficulty level (for vocab selection)

    Returns:
        OracleAction with recommended action and parameters
    """
    from src.harness.observations import (
        TERMINAL_BYTES, GOAL_BYTES, FS_BYTES,
        decode_observation,
    )

    # Decode observation to extract key fields
    if obs_bytes.dim() == 2:
        obs_bytes = obs_bytes[0]

    # Extract metadata directly
    meta_offset = TERMINAL_BYTES + GOAL_BYTES + FS_BYTES  # 448
    tests_passing = int(obs_bytes[meta_offset + 10].item())
    tests_total = int(obs_bytes[meta_offset + 11].item())

    # Extract focus text
    fs_offset = TERMINAL_BYTES + GOAL_BYTES  # 320
    focus_bytes = obs_bytes[fs_offset:fs_offset + FS_BYTES].cpu().numpy().tobytes()
    focus_text = focus_bytes.rstrip(b'\x00').decode('utf-8', errors='replace')

    # Case 1: Tests pass -> COMPLETE_TASK
    if tests_passing > 0 and tests_passing == tests_total:
        action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
        action_bytes[0] = ActionType.COMPLETE_TASK.value
        return OracleAction(
            action_type=ActionType.COMPLETE_TASK,
            action_bytes=action_bytes,
            confidence=1.0,
        )

    # Case 2: No focus text or no code context -> RUN_TESTS to discover bug
    if not focus_text or len(focus_text.strip()) < 5:
        action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
        action_bytes[0] = ActionType.RUN_TESTS.value
        return OracleAction(
            action_type=ActionType.RUN_TESTS,
            action_bytes=action_bytes,
            confidence=1.0,
        )

    # Case 3: Bug visible - compute WRITE_FOCUS action
    # We need original_code and buggy_code to compute the fix
    if original_code is not None and buggy_code is not None:
        # Compute where the bug is in the focus window
        diff_pos = find_diff_position(original_code, buggy_code)

        # Compute focus_start from bug_line if provided
        if bug_line is not None:
            focus_start = compute_focus_start_line_based(buggy_code, bug_line)
        else:
            # Estimate focus_start - assume focus_text starts at diff position
            focus_start = max(0, diff_pos - 16)

        # Try to compute the correct action
        action = compute_correct_action_generic(
            original_code, buggy_code, focus_start
        )

        if action is not None:
            return OracleAction(
                action_type=ActionType.WRITE_FOCUS,
                offset=action.offset,
                vocab_idx=action.vocab_idx,
                length=action.length,
                action_bytes=action.action_bytes,
                confidence=1.0,
            )

    # Case 4: Focus text present but can't compute fix
    # Heuristic: Look for common TRIVIAL bug patterns in focus_text
    expert_action = _detect_bug_from_focus_text(focus_text, difficulty)
    if expert_action is not None:
        return expert_action

    # Fallback: RUN_TESTS if we can't figure out what to do
    action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
    action_bytes[0] = ActionType.RUN_TESTS.value
    return OracleAction(
        action_type=ActionType.RUN_TESTS,
        action_bytes=action_bytes,
        confidence=0.5,  # Low confidence fallback
    )


def _detect_bug_from_focus_text(
    focus_text: str,
    difficulty: BugDifficulty = BugDifficulty.TRIVIAL,
) -> Optional[OracleAction]:
    """
    Heuristic bug detection from focus text alone.

    For TRIVIAL bugs, we look for patterns like:
    - 'def foo()' without colon -> need ':'
    - Mismatched quotes
    - Missing closing parens

    This is used when we don't have ground truth original_code/buggy_code,
    such as during on-policy rollouts where we only have the observation.

    Returns OracleAction if a bug pattern is detected, None otherwise.
    """
    if difficulty not in (BugDifficulty.TRIVIAL,):
        # For now, only handle TRIVIAL bugs
        return None

    # Pattern 1: Missing colon after 'def' or 'if' or 'for' etc.
    # Look for 'def foo()' or 'if x' without ':'
    import re

    # Match 'def name(...)'  without colon at end of line
    def_pattern = r'def\s+\w+\s*\([^)]*\)\s*(?!\s*:)'
    for match in re.finditer(def_pattern, focus_text):
        # Found a 'def foo()' without colon
        offset = match.end()
        if offset < len(focus_text) and focus_text[offset] != ':':
            action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
            action_bytes[0] = ActionType.WRITE_FOCUS.value
            action_bytes[1] = max(0, min(255, offset))
            action_bytes[3] = 0  # Insert mode
            action_bytes[25] = 0  # ':\n' in TRIVIAL_VOCAB
            return OracleAction(
                action_type=ActionType.WRITE_FOCUS,
                offset=offset,
                vocab_idx=0,  # ':\n'
                length=0,
                action_bytes=action_bytes,
                confidence=0.8,
            )

    # Pattern 2: Missing closing paren
    open_parens = focus_text.count('(')
    close_parens = focus_text.count(')')
    if open_parens > close_parens:
        # Find where to insert the missing ')'
        # Simple heuristic: look for 'foo(x' patterns
        paren_pattern = r'\([^)]*$'  # Open paren without close at end
        match = re.search(paren_pattern, focus_text)
        if match:
            offset = match.end()
            action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
            action_bytes[0] = ActionType.WRITE_FOCUS.value
            action_bytes[1] = max(0, min(255, offset))
            action_bytes[3] = 0  # Insert mode
            action_bytes[25] = 1  # ')' in TRIVIAL_VOCAB
            return OracleAction(
                action_type=ActionType.WRITE_FOCUS,
                offset=offset,
                vocab_idx=1,  # ')'
                length=0,
                action_bytes=action_bytes,
                confidence=0.7,
            )

    return None


def get_oracle_action_from_env(
    env,
    obs_bytes: torch.Tensor,
) -> OracleAction:
    """
    Get oracle action using full environment context.

    This is the preferred method during training rollouts where we have
    access to the environment's internal state.

    Args:
        env: JarvisHarnessEnv instance with current_task, etc.
        obs_bytes: Current observation

    Returns:
        OracleAction with expert recommendation
    """
    # Extract env state
    original_code = None
    buggy_code = None
    bug_line = None
    difficulty = BugDifficulty.TRIVIAL

    # Try to get ground truth from env
    if hasattr(env, 'current_task') and env.current_task is not None:
        task = env.current_task
        if hasattr(task, 'original_files'):
            # Get the buggy file
            if hasattr(task, 'bugs') and task.bugs:
                bug = task.bugs[0]
                original_code = task.original_files.get(bug.file_path, "")
                if hasattr(task, 'files') and bug.file_path in task.files:
                    buggy_code = task.files[bug.file_path].content
                bug_line = bug.line_number

        if hasattr(task, 'difficulty'):
            difficulty = task.difficulty

    # Also check last_test_result for test status
    if hasattr(env, 'last_test_result') and env.last_test_result is not None:
        result = env.last_test_result
        if result.passed:
            # Tests pass - COMPLETE_TASK
            action_bytes = torch.zeros(ACTION_BYTES_V2, dtype=torch.uint8)
            action_bytes[0] = ActionType.COMPLETE_TASK.value
            return OracleAction(
                action_type=ActionType.COMPLETE_TASK,
                action_bytes=action_bytes,
                confidence=1.0,
            )

    return get_oracle_action(
        obs_bytes,
        original_code=original_code,
        buggy_code=buggy_code,
        bug_line=bug_line,
        difficulty=difficulty,
    )


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

    # Test multi-step trajectory generation
    print("\n\n=== Testing Multi-Step Trajectories ===")
    multistep_demos = generate_multistep_demos(num_tasks=10, difficulty=BugDifficulty.EASY, seed=42)
    print(f"Generated {len(multistep_demos)} multi-step trajectories")

    for i, demo in enumerate(multistep_demos[:3]):
        print(f"\n--- MultiStep Demo {i+1} ---")
        print(f"Bug type: {demo.bug_type}")
        print(f"Fix: {demo.fix_description[:50]}...")
        print(f"Steps: {len(demo.steps)}")
        for j, (obs, action) in enumerate(demo.steps):
            action_type = ActionType(action[0].item())
            print(f"  Step {j+1}: {action_type.name} (obs shape: {obs.shape})")

    # Test multi-step BC dataset
    print("\n\nCreating multi-step BC dataset...")
    ms_dataset = create_multistep_bc_dataset(num_tasks=100, difficulty=BugDifficulty.EASY, seed=42)
    print(f"Dataset size: {ms_dataset['num_samples']}")
    print(f"RUN_TESTS actions: {ms_dataset['num_run_tests']}")
    print(f"WRITE_FOCUS actions: {ms_dataset['num_write_focus']}")
    print(f"Observations shape: {ms_dataset['observations'].shape}")

    # Test persistent trajectory generation (Phase 7.4a)
    print("\n\n=== Testing Persistent Trajectories (Phase 7.4a) ===")
    persistent_demos = generate_persistent_demos(num_tasks=10, difficulty=BugDifficulty.TRIVIAL, seed=42)
    print(f"Generated {len(persistent_demos)} persistent trajectories")

    for i, demo in enumerate(persistent_demos[:2]):
        print(f"\n--- Persistent Demo {i+1} ---")
        print(f"Bug type: {demo.bug_type}")
        print(f"Fix: {demo.fix_description[:50]}...")
        print(f"Steps: {len(demo.steps)}")
        for j, (obs, action) in enumerate(demo.steps):
            action_type = ActionType(action[0].item())
            print(f"  Step {j+1}: {action_type.name} (obs shape: {obs.shape})")

    # Test persistent BC dataset
    print("\n\nCreating persistent BC dataset...")
    p_dataset = create_persistent_bc_dataset(num_tasks=100, difficulty=BugDifficulty.TRIVIAL, seed=42)
    print(f"Dataset size: {p_dataset['num_samples']}")
    print(f"RUN_TESTS actions: {p_dataset['num_run_tests']}")
    print(f"WRITE_FOCUS actions: {p_dataset['num_write_focus']}")
    print(f"COMPLETE_TASK actions: {p_dataset['num_complete_task']}")
    print(f"Observations shape: {p_dataset['observations'].shape}")
