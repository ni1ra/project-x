"""Sandbox I/O primitives for Project X Raphael action-taking.

Minimal first-step primitives so the agent (Project X Raphael) can
write a Python program, run it, read its output, list what files it
has produced, and reset its state to a known snapshot for benchmark
replay. NO direct internet (subprocess inherits a scrubbed env).
NO writes outside the sandbox root (every path resolves through
`_resolve(path)` which forbids escapes via `..` or absolute paths).

The sandbox lives at `<repo>/sandbox/` (the `.gitkeep`-only dir cycle 1
shipped). The agent's working directory is `sandbox/workdir/`; named
snapshots live under `sandbox/.snapshots/<name>/`. The `.gitignore`
backstop keeps generated workdir contents out of git tracking.

Strict-strict thesis status: this is **infrastructure**, not knowledge.
The agent does not gain the ability to *decide* to use these primitives
from this commit; that decision-making is owed to a later cycle's
substrate-learned routing. This commit unblocks the substrate by
giving it primitives to call.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


_SANDBOX_ROOT = Path(__file__).resolve().parent
_WORKDIR = _SANDBOX_ROOT / "workdir"
_SNAPSHOTS_DIR = _SANDBOX_ROOT / ".snapshots"


def _ensure_workdir() -> Path:
    _WORKDIR.mkdir(parents=True, exist_ok=True)
    return _WORKDIR


def _resolve(rel_path: str) -> Path:
    """Resolve a sandbox-relative path. Refuse escapes."""
    if Path(rel_path).is_absolute():
        raise ValueError(f"absolute paths are forbidden in the sandbox: {rel_path!r}")
    workdir = _ensure_workdir()
    target = (workdir / rel_path).resolve()
    if not str(target).startswith(str(workdir.resolve())):
        raise ValueError(f"path escapes sandbox workdir: {rel_path!r} -> {target}")
    return target


@dataclass
class RunResult:
    """Output of `run_python`. Captures both streams + exit code."""

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool


def write_file(rel_path: str, content: str) -> Path:
    target = _resolve(rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def read_file(rel_path: str) -> str:
    target = _resolve(rel_path)
    return target.read_text(encoding="utf-8")


def list_files() -> list[str]:
    workdir = _ensure_workdir()
    out: list[str] = []
    for p in sorted(workdir.rglob("*")):
        if p.is_file():
            out.append(str(p.relative_to(workdir)))
    return out


def run_python(rel_script_path: str, *, timeout_seconds: float = 5.0) -> RunResult:
    """Execute a Python file inside the sandbox workdir.

    Subprocess runs with the sandbox workdir as cwd and a scrubbed
    environment that excludes credentials and network helpers (no PATH
    editing — the python interpreter is supplied by sys.executable
    indirectly via `python3`). The cap is wall-clock seconds; SIGKILL
    if exceeded. NO captured stdout/stderr beyond the subprocess's own
    file descriptors.
    """
    target = _resolve(rel_script_path)
    if not target.exists():
        raise FileNotFoundError(f"sandbox script not found: {rel_script_path!r}")
    safe_env = {
        "PATH": "/usr/bin:/bin",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "PYTHONUNBUFFERED": "1",
    }
    try:
        completed = subprocess.run(
            ["python3", str(target)],
            cwd=str(_WORKDIR),
            env=safe_env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return RunResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            exit_code=completed.returncode,
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout.decode("utf-8") if exc.stdout else "")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr.decode("utf-8") if exc.stderr else "")
        return RunResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=-9,
            timed_out=True,
        )


def snapshot(name: str) -> Path:
    """Save current workdir contents to a named snapshot."""
    if not name or "/" in name or ".." in name:
        raise ValueError(f"invalid snapshot name: {name!r}")
    _ensure_workdir()
    target = _SNAPSHOTS_DIR / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(_WORKDIR, target)
    return target


def reset_snapshot(name: str) -> Path:
    """Replace workdir with a previously-saved snapshot."""
    source = _SNAPSHOTS_DIR / name
    if not source.exists():
        raise FileNotFoundError(f"snapshot not found: {name!r}")
    if _WORKDIR.exists():
        shutil.rmtree(_WORKDIR)
    shutil.copytree(source, _WORKDIR)
    return _WORKDIR


def reset_workdir() -> Path:
    """Wipe the workdir to an empty state (no snapshot required)."""
    if _WORKDIR.exists():
        shutil.rmtree(_WORKDIR)
    return _ensure_workdir()
