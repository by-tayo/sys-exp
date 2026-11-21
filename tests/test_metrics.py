"""Tests for metrics.py's psutil-based collectors."""

from types import SimpleNamespace

import metrics


def test_get_memory_usage_shapes_psutil_output(monkeypatch):
    monkeypatch.setattr(
        metrics.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(total=100, used=40, available=60, percent=40.0),
    )
    result = metrics.get_memory_usage()
    assert result == {"total": 100, "used": 40, "available": 60, "percent": 40.0}


def test_get_disk_usage_handles_permission_error(monkeypatch):
    def _raise(_mount):
        raise PermissionError

    monkeypatch.setattr(metrics.psutil, "disk_usage", _raise)
    result = metrics.get_disk_usage()
    assert result["percent"] == 0.0
    assert result["total"] == 0


def test_get_network_usage_shapes_psutil_output(monkeypatch):
    monkeypatch.setattr(
        metrics.psutil,
        "net_io_counters",
        lambda: SimpleNamespace(bytes_sent=111, bytes_recv=222),
    )
    result = metrics.get_network_usage()
    assert result == {"bytes_sent": 111, "bytes_recv": 222}


def test_get_process_list_skips_inaccessible_processes(monkeypatch):
    class FakeProc:
        def __init__(self, info):
            self.info = info

    good = FakeProc({"pid": 1, "name": "good", "cpu_percent": 5.0, "memory_percent": 1.234})

    class BadProc:
        @property
        def info(self):
            raise metrics.psutil.AccessDenied(pid=2)

    monkeypatch.setattr(metrics.psutil, "process_iter", lambda fields: [good, BadProc()])
    result = metrics.get_process_list()
    assert result == [{"pid": 1, "name": "good", "cpu_percent": 5.0, "memory_percent": 1.234}]


def test_get_gpu_usage_returns_empty_without_gputil(monkeypatch):
    monkeypatch.setattr(metrics, "_GPU_AVAILABLE", False)
    assert metrics.get_gpu_usage() == []


def test_get_battery_info_returns_none_when_no_battery(monkeypatch):
    monkeypatch.setattr(metrics.psutil, "sensors_battery", lambda: None)
    assert metrics.get_battery_info() is None
