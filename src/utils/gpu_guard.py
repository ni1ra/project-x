"""
GPU guardrails for training runs.

Hard criteria (user-specified):
- Abort if total GPU VRAM used exceeds 10GB.
- Abort if sustained GPU utilization is below 80% (after a warmup period).

This uses `nvidia-smi` so it works across Linux/WSL/Windows environments where
CUDA is present.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from typing import Deque, List, Optional
import os
import shutil
import subprocess
import sys
import threading
import time


@dataclass(frozen=True)
class GPUSample:
    """One snapshot from nvidia-smi."""

    utilization_gpu: int  # percent
    memory_used_mib: int
    memory_total_mib: int


def _parse_nvidia_smi_csv(text: str) -> List[GPUSample]:
    samples: List[GPUSample] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Expected format (nounits):
        # util, mem_used, mem_total
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue

        try:
            util = int(float(parts[0]))
            mem_used = int(float(parts[1]))
            mem_total = int(float(parts[2]))
        except ValueError:
            continue

        samples.append(
            GPUSample(
                utilization_gpu=max(0, min(100, util)),
                memory_used_mib=max(0, mem_used),
                memory_total_mib=max(0, mem_total),
            )
        )
    return samples


def nvidia_smi_available() -> bool:
    return shutil.which("nvidia-smi") is not None


def query_gpu_sample(gpu_index: int = 0, timeout_s: float = 2.0) -> Optional[GPUSample]:
    """
    Query utilization and memory for a GPU index via nvidia-smi.

    Returns None if nvidia-smi is unavailable or parsing fails.
    """
    if not nvidia_smi_available():
        return None

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except Exception:
        return None

    samples = _parse_nvidia_smi_csv(result.stdout or "")
    if not samples:
        return None

    if gpu_index < 0 or gpu_index >= len(samples):
        gpu_index = 0
    return samples[gpu_index]


@dataclass(frozen=True)
class GPUGuardConfig:
    gpu_index: int = 0
    poll_interval_s: float = 1.0
    grace_period_s: float = 20.0
    util_window_s: float = 10.0
    low_util_patience_s: float = 30.0
    min_util_percent: int = 80
    max_memory_mib: int = 10 * 1024  # 10GB
    require_nvidia_smi: bool = True
    enforce_min_util: bool = True


class GPUGuard:
    """
    Background guard that hard-aborts the current process if constraints are violated.

    Note: this intentionally uses `os._exit(...)` for a fast, reliable kill.
    """

    def __init__(self, config: GPUGuardConfig):
        self.config = config
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread is not None:
            return

        if self.config.require_nvidia_smi and not nvidia_smi_available():
            raise RuntimeError("nvidia-smi not found; GPU guard cannot run")

        self._thread = threading.Thread(target=self._run, name="gpu-guard", daemon=True)
        self._thread.start()

    def stop(self, timeout_s: float = 2.0) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=timeout_s)
        self._thread = None

    def _abort(self, exit_code: int, message: str) -> None:
        print(message, file=sys.stderr, flush=True)
        os._exit(exit_code)

    def _run(self) -> None:
        start_t = time.time()
        util_samples: Deque[int] = deque()
        low_util_since: Optional[float] = None

        window_len = max(1, int(self.config.util_window_s / max(self.config.poll_interval_s, 1e-6)))

        while not self._stop_event.is_set():
            sample = query_gpu_sample(self.config.gpu_index)
            if sample is None:
                if self.config.require_nvidia_smi:
                    self._abort(90, "GPU_GUARD: failed to query nvidia-smi; aborting")
                time.sleep(self.config.poll_interval_s)
                continue

            # Hard VRAM cap (total GPU usage).
            if sample.memory_used_mib > self.config.max_memory_mib:
                self._abort(
                    91,
                    (
                        f"GPU_GUARD: VRAM cap exceeded: {sample.memory_used_mib} MiB used "
                        f"(cap {self.config.max_memory_mib} MiB). Aborting to protect system."
                    ),
                )

            # Sustained utilization floor.
            util_samples.append(sample.utilization_gpu)
            while len(util_samples) > window_len:
                util_samples.popleft()

            now = time.time()
            if self.config.enforce_min_util and (now - start_t) >= self.config.grace_period_s:
                if len(util_samples) == window_len:
                    avg_util = sum(util_samples) / len(util_samples)
                    if avg_util < self.config.min_util_percent:
                        if low_util_since is None:
                            low_util_since = now
                        elif (now - low_util_since) >= self.config.low_util_patience_s:
                            self._abort(
                                92,
                                (
                                    "GPU_GUARD: sustained low GPU utilization "
                                    f"(avg {avg_util:.1f}% < {self.config.min_util_percent}%) "
                                    f"for {self.config.low_util_patience_s:.0f}s. Aborting."
                                ),
                            )
                    else:
                        low_util_since = None

            time.sleep(self.config.poll_interval_s)


def default_gpu_index() -> int:
    """
    Best-effort GPU index from CUDA_VISIBLE_DEVICES.

    Note: this is heuristic; nvidia-smi uses physical indices.
    """
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    if not visible:
        return 0
    first = visible.split(",")[0].strip()
    try:
        return int(first)
    except ValueError:
        return 0

