"""Tests for the FastAPI app and routes defined in main.py."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(main_module, fresh_detector):
    with TestClient(main_module.app) as test_client:
        yield test_client


def _patch_metrics(monkeypatch, main_module, **overrides):
    defaults = dict(
        cpu=10.0,
        memory={"total": 1000, "used": 200, "available": 800, "percent": 20.0},
        disk={"total": 1000, "used": 300, "free": 700, "percent": 30.0, "mount": "/"},
        network={"bytes_sent": 100, "bytes_recv": 200},
        processes=[{"pid": 1, "name": "init", "cpu_percent": 0.0, "memory_percent": 0.1}],
        process_detail={"memory_rss_bytes": 1024, "num_threads": 1, "status": "running"},
        gpus=[],
    )
    defaults.update(overrides)
    monkeypatch.setattr(main_module, "get_cpu_usage", lambda: defaults["cpu"])
    monkeypatch.setattr(main_module, "get_memory_usage", lambda: defaults["memory"])
    monkeypatch.setattr(main_module, "get_disk_usage", lambda: defaults["disk"])
    monkeypatch.setattr(main_module, "get_network_usage", lambda: defaults["network"])
    monkeypatch.setattr(main_module, "get_process_list", lambda: defaults["processes"])
    monkeypatch.setattr(main_module, "get_process_detail", lambda pid: defaults["process_detail"])
    monkeypatch.setattr(main_module, "get_gpu_usage", lambda: defaults["gpus"])


def test_health_reports_untrained_model(client, main_module, monkeypatch):
    _patch_metrics(monkeypatch, main_module)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["exporter"] == "up"
    assert body["model_trained"] is False


def test_metrics_endpoint_exposes_prometheus_text(client, main_module, monkeypatch):
    _patch_metrics(monkeypatch, main_module, cpu=42.0)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "system_cpu_usage_percent" in resp.text
    assert "system_anomaly_detected" in resp.text


def test_api_system_snapshot(client, main_module, monkeypatch):
    _patch_metrics(
        monkeypatch,
        main_module,
        cpu=5.0,
        memory={"total": 1, "used": 1, "available": 0, "percent": 55.5},
    )
    resp = client.get("/api/system")
    body = resp.json()
    assert body["cpu_percent"] == 5.0
    assert body["memory"]["percent"] == 55.5


def test_api_processes_limit_and_sort_order(client, main_module, monkeypatch):
    _patch_metrics(
        monkeypatch,
        main_module,
        processes=[
            {"pid": 1, "name": "a", "cpu_percent": 90.0, "memory_percent": 1.0},
            {"pid": 2, "name": "b", "cpu_percent": 10.0, "memory_percent": 1.0},
        ],
    )
    resp = client.get("/api/processes", params={"limit": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["pid"] == 1  # sorted descending by cpu_percent


def test_api_processes_rejects_over_max_limit(client, main_module, monkeypatch):
    _patch_metrics(monkeypatch, main_module)
    resp = client.get("/api/processes", params={"limit": 51})
    assert resp.status_code == 422


def test_api_anomaly_before_training(client, main_module, monkeypatch):
    _patch_metrics(monkeypatch, main_module)
    resp = client.get("/api/anomaly")
    body = resp.json()
    assert body["detected"] is False
    assert body["reason"] == "Model not trained yet"


def test_metrics_endpoint_survives_one_failing_collector(client, main_module, monkeypatch):
    """A single misbehaving collector (e.g. a transient psutil error) must
    not take down the whole scrape — Prometheus would then lose every other
    metric too, not just the failing one."""
    _patch_metrics(monkeypatch, main_module, cpu=42.0)

    def _boom():
        raise OSError("simulated collector failure")

    monkeypatch.setattr(main_module, "get_network_usage", _boom)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "system_cpu_usage_percent" in resp.text
    # The failed collector's gauge still gets its fallback value (0), not an error.
    assert "system_network_sent_bytes 0.0" in resp.text


def test_anomaly_model_persists_across_restarts(main_module, model_path, monkeypatch):
    """Training via repeated /metrics scrapes, then restarting the app
    (re-entering the TestClient/lifespan) should reload the trained model
    instead of starting from zero samples again — the behavior the
    persistence feature exists for."""
    model_path.unlink(missing_ok=True)
    _patch_metrics(monkeypatch, main_module)

    with TestClient(main_module.app) as c:
        for _ in range(50):
            c.get("/metrics")
        assert main_module.detector.trained is True

    assert model_path.exists()

    with TestClient(main_module.app) as c:
        resp = c.get("/health")
    assert resp.json()["model_trained"] is True
