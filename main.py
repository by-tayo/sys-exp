"""
main.py — FastAPI Prometheus exporter agent
Runs on Windows, Linux, or macOS.
- Exposes /metrics for Prometheus scraping
- Exposes /api/* REST endpoints for direct inspection
- Interactive Swagger UI available at /docs
"""

import argparse
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

from config import get_settings
from metrics import (
    get_cpu_usage,
    get_disk_usage,
    get_gpu_usage,
    get_memory_usage,
    get_network_usage,
    get_process_detail,
    get_process_list,
    get_system_info,
)
from net_observer import NetworkObserver

# Resolved on first call (and cached) rather than at import time, so env
# vars set just before importing this module (e.g. by test fixtures) are
# picked up reliably. See config.get_settings for details.
settings = get_settings()

logging.basicConfig(
    # settings.log_level is validated/normalized to a real logging level name.
    level=getattr(logging, settings.log_level),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

detector = NetworkObserver(training_samples=settings.anomaly_training_samples)

SYSTEM_INFO = get_system_info()
HOST = SYSTEM_INFO["hostname"]
OS_NAME = SYSTEM_INFO["os"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load a persisted anomaly model on startup, save it back on shutdown."""
    global detector
    detector = NetworkObserver.load(settings.model_path)
    detector.training_samples = settings.anomaly_training_samples
    logger.info("Exporter starting up (host=%s os=%s)", HOST, OS_NAME)
    yield
    detector.save(settings.model_path)
    logger.info("Exporter shutting down")


app = FastAPI(
    title="System Metric Exporter",
    description="Cross-platform metrics exporter — CPU, Memory, Disk, Network, Processes, GPU.",
    version="1.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Prometheus Gauges — mirrors OS Task Manager / Activity Monitor panels
# ---------------------------------------------------------------------------
CPU_USAGE = Gauge("system_cpu_usage_percent", "CPU usage %", ["host", "os"])
MEMORY_USAGE = Gauge("system_memory_usage", "Memory usage %")
DISK_USAGE = Gauge("system_disk_usage", "Disk usage %")
NETWORK_SENT = Gauge("system_network_sent_bytes", "Network bytes sent")
NETWORK_RECV = Gauge("system_network_received_bytes", "Network bytes received")
PROCESS_COUNT = Gauge("system_process_count", "Number of running processes")
MEMORY_TOTAL = Gauge("system_memory_total_bytes", "Total physical memory in bytes")
MEMORY_USED = Gauge("system_memory_used_bytes", "Used physical memory in bytes")
DISK_TOTAL = Gauge("system_disk_total_bytes", "Total disk space in bytes")
DISK_USED = Gauge("system_disk_used_bytes", "Used disk space in bytes")
BATTERY_PCT = Gauge("system_battery_percent", "Battery % (laptops only)", ["host"])
GPU_LOAD = Gauge("system_gpu_usage_percent", "GPU load %", ["host", "gpu_id", "gpu_name"])
GPU_MEMORY_USED = Gauge("system_gpu_memory_used_mb", "GPU memory used in MB", ["host", "gpu_id", "gpu_name"])
GPU_MEMORY_TOTAL = Gauge(
    "system_gpu_memory_total_mb", "GPU memory total in MB", ["host", "gpu_id", "gpu_name"]
)
ANOMALY_DETECTED = Gauge(
    "system_anomaly_detected", "1 if the anomaly model flags current behavior as anomalous, else 0", ["host"]
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect(name: str, func, default):
    """Run a single metrics collector defensively.

    psutil/GPUtil calls are generally reliable, but a transient OS-level
    error (e.g. a restricted container, a vanished /proc entry) must not
    take down the whole /metrics scrape — Prometheus would then lose every
    other metric too. Log and fall back to a safe default instead.
    """
    try:
        return func()
    except Exception:
        logger.exception("Failed to collect %s metrics; using fallback value", name)
        return default


def _update_gauges() -> dict:
    """Collect system metrics, push to Prometheus gauges, return raw values."""
    cpu = _collect("cpu", get_cpu_usage, 0.0)
    memory = _collect("memory", get_memory_usage, {"total": 0, "used": 0, "available": 0, "percent": 0.0})
    disk = _collect("disk", get_disk_usage, {"total": 0, "used": 0, "free": 0, "percent": 0.0, "mount": ""})
    network = _collect("network", get_network_usage, {"bytes_sent": 0, "bytes_recv": 0})
    processes = _collect("processes", get_process_list, [])
    gpus = _collect("gpu", get_gpu_usage, [])
    info = _collect("system info", get_system_info, SYSTEM_INFO)

    CPU_USAGE.labels(host=info["hostname"], os=info["os"]).set(cpu)
    MEMORY_USAGE.set(memory["percent"])
    DISK_USAGE.set(disk["percent"])
    NETWORK_SENT.set(network["bytes_sent"])
    NETWORK_RECV.set(network["bytes_recv"])
    PROCESS_COUNT.set(len(processes))
    MEMORY_TOTAL.set(memory["total"])
    MEMORY_USED.set(memory["used"])
    DISK_TOTAL.set(disk["total"])
    DISK_USED.set(disk["used"])

    for gpu in gpus:
        labels = dict(host=info["hostname"], gpu_id=str(gpu["id"]), gpu_name=gpu["name"])
        GPU_LOAD.labels(**labels).set(gpu["load_percent"])
        GPU_MEMORY_USED.labels(**labels).set(gpu["memory_used_mb"])
        GPU_MEMORY_TOTAL.labels(**labels).set(gpu["memory_total_mb"])

    battery = info.get("battery")
    if battery:
        BATTERY_PCT.labels(host=info["hostname"]).set(battery["percent"])

    return {
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "network": network,
        "processes": processes,
        "gpus": gpus,
        "info": info,
    }


def _check_anomaly(vals: dict, train: bool) -> dict:
    """Run the IsolationForest detector against the latest sample.

    When `train` is True (the Prometheus scrape path), the sample is also
    added to the training set, matching the original scrape-cadence
    training behavior — ad-hoc /api calls only score, they don't train.
    """
    network_total = vals["network"]["bytes_sent"] + vals["network"]["bytes_recv"]
    if train:
        detector.add_training_sample(vals["cpu"], vals["memory"]["percent"], network_total)
    is_anomaly, reason = detector.detect(vals["cpu"], vals["memory"]["percent"], network_total)
    ANOMALY_DETECTED.labels(host=vals["info"]["hostname"]).set(1 if is_anomaly else 0)
    return {"detected": is_anomaly, "reason": reason}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def metrics():
    """Prometheus scrape endpoint. Scraped by Prometheus every 15 seconds."""
    vals = _update_gauges()
    _check_anomaly(vals, train=True)
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/api/system", summary="Full system snapshot", tags=["System"])
def api_system():
    """Returns current CPU, memory, disk, network, and system info."""
    vals = _update_gauges()
    return {
        "cpu_percent": vals["cpu"],
        "memory": vals["memory"],
        "disk": vals["disk"],
        "network": vals["network"],
        "system": vals["info"],
    }


@app.get("/api/processes", summary="Top N processes by CPU", tags=["Processes"])
def api_processes(limit: int = Query(default=10, le=50, description="Number of processes to return")):
    """Returns processes sorted by CPU usage descending, with memory/thread/status detail."""
    procs = sorted(get_process_list(), key=lambda p: p["cpu_percent"], reverse=True)[:limit]
    for proc in procs:
        proc.update(get_process_detail(proc["pid"]))
    return procs


@app.get("/api/gpu", summary="GPU usage snapshot", tags=["System"])
def api_gpu():
    """Returns per-GPU load and memory stats. Empty list if no GPU or GPUtil is unavailable."""
    return get_gpu_usage()


@app.get("/api/anomaly", summary="Anomaly detection status", tags=["System"])
def api_anomaly():
    """Returns whether current CPU/memory/network behavior looks anomalous.

    Backed by an IsolationForest trained on samples collected during
    Prometheus scrapes; returns 'Model not trained yet' until enough
    samples (50) have been observed.
    """
    vals = _update_gauges()
    return _check_anomaly(vals, train=False)


@app.get("/health", summary="Health check", tags=["Status"])
def health():
    return {
        "status": "healthy",
        "exporter": "up",
        "host": HOST,
        "os": OS_NAME,
        "model_trained": detector.trained,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Cross-platform Prometheus exporter")
    parser.add_argument("--port", type=int, default=settings.port, help="Port to run the agent on")
    parser.add_argument("--host", type=str, default=settings.host, help="Host/address to bind the agent on")
    args = parser.parse_args()

    logger.info("agent running | host=%s os=%s bind=%s:%d", HOST, OS_NAME, args.host, args.port)
    logger.info("Swagger UI:        http://localhost:%d/docs", args.port)
    logger.info("Prometheus scrape: http://localhost:%d/metrics", args.port)
    uvicorn.run(app, host=args.host, port=args.port, reload=False)
