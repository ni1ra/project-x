"""Phase 13 #00P13c1-01-sandbox tests.

Covers the sandbox primitives in semantic_memory_agent.py:
  - SANDBOX_ROOT module constant + _validate_sandbox_path primitive.
  - 4 tools (read_file_sandbox, write_file_sandbox, run_python_sandbox,
    list_dir_sandbox) registered on MemoryAgent.tools.
  - Happy paths: write→read, list_dir, run_python echo.
  - Escape attempts: absolute path, .. traversal, symlink-out.

Tests monkey-patch SANDBOX_ROOT to a tmp_path-rooted dir for isolation —
the real repo sandbox/ is not touched.
"""

from __future__ import annotations

import os

import pytest

from project_x.experiments import semantic_memory_agent as sma
from project_x.experiments.semantic_hdc_memory import SemanticHDCMemory


@pytest.fixture
def isolated_sandbox(monkeypatch, tmp_path):
    """Monkey-patch SANDBOX_ROOT to tmp_path/sandbox so tests don't pollute repo."""
    sandbox = (tmp_path / "sandbox").resolve()
    sandbox.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(sma, "SANDBOX_ROOT", sandbox)
    return sandbox


# =============================================================================
# Tool registration — all 4 sandbox tools live on default MemoryAgent
# =============================================================================


def test_memoryagent_default_registers_5_tools():
    """4 sandbox tools + 1 legacy read_file = 5 default tools."""
    agent = sma.MemoryAgent(memory=SemanticHDCMemory())
    expected = {
        "read_file",
        "read_file_sandbox",
        "write_file_sandbox",
        "run_python_sandbox",
        "list_dir_sandbox",
    }
    assert set(agent.tools.keys()) == expected


# =============================================================================
# Happy paths
# =============================================================================


def test_write_then_read(isolated_sandbox):
    write_msg = sma._tool_write_file_sandbox("notes/scratch.txt", "hello sandbox")
    assert "wrote" in write_msg and "scratch.txt" in write_msg
    read_back = sma._tool_read_file_sandbox("notes/scratch.txt")
    assert read_back == "hello sandbox"


def test_read_truncation(isolated_sandbox):
    sma._tool_write_file_sandbox("big.txt", "x" * 10_000)
    out = sma._tool_read_file_sandbox("big.txt", max_chars=100)
    assert "...[truncated]" in out
    assert len(out) <= 100 + len("...[truncated]")


def test_list_dir_after_writes(isolated_sandbox):
    sma._tool_write_file_sandbox("a.txt", "1")
    sma._tool_write_file_sandbox("b.txt", "2")
    sma._tool_write_file_sandbox("sub/c.txt", "3")
    out = sma._tool_list_dir_sandbox(".")
    # sorted listing should include a.txt, b.txt, sub
    assert "a.txt" in out and "b.txt" in out and "sub" in out


def test_list_dir_empty(isolated_sandbox):
    out = sma._tool_list_dir_sandbox(".")
    assert "empty" in out


def test_run_python_echo(isolated_sandbox):
    out = sma._tool_run_python_sandbox("print(2 + 2)")
    assert "exit=0" in out and "4" in out


def test_run_python_uses_sandbox_cwd(isolated_sandbox):
    """Subprocess cwd should be SANDBOX_ROOT — verify via os.getcwd in script."""
    out = sma._tool_run_python_sandbox("import os; print(os.getcwd())")
    assert str(isolated_sandbox) in out


def test_run_python_timeout(isolated_sandbox):
    out = sma._tool_run_python_sandbox(
        "import time; time.sleep(5)", timeout=1
    )
    assert "timeout" in out


# =============================================================================
# Escape attempts (the security boundary — each MUST be refused)
# =============================================================================


def test_escape_absolute_path_refused(isolated_sandbox):
    """Absolute paths must be refused — can't sneak via /etc/passwd."""
    out = sma._tool_read_file_sandbox("/etc/passwd")
    assert "tool error" in out
    assert "absolute" in out.lower() or "escapes" in out.lower()


def test_escape_dotdot_traversal_refused(isolated_sandbox):
    """`..` traversal out of sandbox/ must be refused."""
    out = sma._tool_read_file_sandbox("../../../../etc/passwd")
    assert "tool error" in out
    assert "escapes" in out.lower()


def test_escape_write_to_absolute_refused(isolated_sandbox):
    """Even writes can't bypass — absolute target refused."""
    out = sma._tool_write_file_sandbox("/tmp/should_not_exist_42.txt", "nope")
    assert "tool error" in out
    assert not os.path.exists("/tmp/should_not_exist_42.txt")


def test_escape_list_dir_dotdot_refused(isolated_sandbox):
    out = sma._tool_list_dir_sandbox("..")
    assert "tool error" in out


def test_escape_symlink_pointing_outside_refused(isolated_sandbox, tmp_path):
    """Symlink inside sandbox/ → /tmp/foo is caught by Path.resolve() following
    the symlink + relative_to() check failing."""
    target_outside = tmp_path / "outside_target.txt"
    target_outside.write_text("secret")
    link_path = isolated_sandbox / "evil_symlink"
    link_path.symlink_to(target_outside)
    out = sma._tool_read_file_sandbox("evil_symlink")
    assert "tool error" in out
    assert "escapes" in out.lower()


# =============================================================================
# Validator unit tests — direct surface
# =============================================================================


def test_validator_accepts_root(isolated_sandbox):
    resolved = sma._validate_sandbox_path(".")
    assert resolved == isolated_sandbox


def test_validator_accepts_nested(isolated_sandbox):
    resolved = sma._validate_sandbox_path("a/b/c.txt")
    assert str(resolved).startswith(str(isolated_sandbox))


def test_validator_refuses_absolute(isolated_sandbox):
    with pytest.raises(ValueError, match="absolute"):
        sma._validate_sandbox_path("/etc/passwd")


def test_validator_refuses_dotdot(isolated_sandbox):
    with pytest.raises(ValueError, match="escapes"):
        sma._validate_sandbox_path("../../../../etc/passwd")


# =============================================================================
# Integration: agent.run_tool dispatches sandbox tools + writes back to memory
# =============================================================================


def test_agent_run_tool_sandbox_write_then_read(isolated_sandbox):
    from project_x.experiments.semantic_hdc_memory import TurnRecord
    mem = SemanticHDCMemory()
    # SemanticHDCMemory.write_one requires write_batch to have built encoders
    # at least once. Seed with one bootstrap turn so the agent's tool-result
    # write_one (inside run_tool) doesn't fail with "call write_batch first".
    mem.write_batch([TurnRecord(turn_id=0, text="bootstrap", fact_keys=[], metadata={})])
    agent = sma.MemoryAgent(memory=mem, _next_turn_id=1)

    write_packet = agent.run_tool(
        "write_file_sandbox", path="hello.txt", content="from agent"
    )
    assert write_packet.decision == "tool"
    assert "wrote" in write_packet.answer_text

    read_packet = agent.run_tool("read_file_sandbox", path="hello.txt")
    assert read_packet.decision == "tool"
    assert "from agent" in read_packet.answer_text
