import os

import pytest

from src.utils import gpu_guard


def test_parse_nvidia_smi_csv_basic():
    text = "85, 9000, 12288\n0, 100, 12288\n"
    samples = gpu_guard._parse_nvidia_smi_csv(text)
    assert len(samples) == 2
    assert samples[0].utilization_gpu == 85
    assert samples[0].memory_used_mib == 9000
    assert samples[0].memory_total_mib == 12288


def test_default_gpu_index_from_cuda_visible_devices(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "1,2")
    assert gpu_guard.default_gpu_index() == 1

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    assert gpu_guard.default_gpu_index() == 0

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "not-an-int")
    assert gpu_guard.default_gpu_index() == 0


def test_query_gpu_sample_uses_nvidia_smi(monkeypatch: pytest.MonkeyPatch):
    class DummyResult:
        def __init__(self, stdout: str):
            self.stdout = stdout

    monkeypatch.setattr(gpu_guard, "nvidia_smi_available", lambda: True)

    def fake_run(*args, **kwargs):
        return DummyResult("50, 123, 10000\n")

    monkeypatch.setattr(gpu_guard.subprocess, "run", fake_run)
    sample = gpu_guard.query_gpu_sample(gpu_index=0)

    assert sample is not None
    assert sample.utilization_gpu == 50
    assert sample.memory_used_mib == 123
    assert sample.memory_total_mib == 10000

