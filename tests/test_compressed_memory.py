from project_x.experiments.compressed_memory import run_experiment


def test_compressed_memory_test_mode_writes_metrics():
    result = run_experiment("test", "pytest-run")
    assert result["mode"] == "test"
    assert result["control"]["name"] == "transformer_control"
    assert result["candidate"]["name"] == "dual_rate_compressed_memory"
    assert result["candidate"]["estimated_memory_bytes"] < result["control"]["estimated_memory_bytes"]
