"""Cross-platform system metric collection using psutil."""

import os
import platform
import socket
import time

import psutil

try:
    import GPUtil

    _GPU_AVAILABLE = True
except ImportError:
    GPUtil = None
    _GPU_AVAILABLE = False


def get_cpu_usage() -> float:
    """Return CPU usage since the previous call; prime once at startup."""
    return psutil.cpu_percent(interval=None)


def get_memory_usage() -> dict:
    mem = psutil.virtual_memory()
    return {
        "total": mem.total,
        "used": mem.used,
        "available": mem.available,
        "percent": mem.percent,
    }


def get_disk_usage() -> dict:
    mount = os.path.abspath(os.sep)
    try:
        disk = psutil.disk_usage(mount)
    except OSError:
        return {
            "total": 0,
            "used": 0,
            "free": 0,
            "percent": 0.0,
            "mount": mount,
        }

    return {
        "total": disk.total,
        "used": disk.used,
        "free": disk.free,
        "percent": disk.percent,
        "mount": mount,
    }


def get_network_usage() -> dict:
    """Return cumulative network byte counters from the operating system."""
    net = psutil.net_io_counters()
    return {
        "bytes_sent": net.bytes_sent if net else 0,
        "bytes_recv": net.bytes_recv if net else 0,
    }


def get_process_count() -> int:
    """Count processes without collecting per-process details."""
    return len(psutil.pids())


def get_process_list(limit: int = 50) -> list:
    """Return a limited process list for the interactive API, not Prometheus."""
    limit = max(1, min(int(limit), 50))
    processes = []

    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info.get("name") or "unknown",
                    "cpu_percent": info.get("cpu_percent") or 0.0,
                    "memory_percent": round(info.get("memory_percent") or 0.0, 3),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return sorted(
        processes,
        key=lambda process: process["cpu_percent"],
        reverse=True,
    )[:limit]


def get_process_detail(pid: int) -> dict:
    """Return additional information for one process."""
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            return {
                "memory_rss_bytes": proc.memory_info().rss,
                "num_threads": proc.num_threads(),
                "status": proc.status(),
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return {
            "memory_rss_bytes": 0,
            "num_threads": 0,
            "status": "unknown",
        }


def get_gpu_usage() -> list:
    """Return NVIDIA GPU metrics when GPUtil and a supported GPU are available."""
    if not _GPU_AVAILABLE:
        return []

    try:
        return [
            {
                "id": gpu.id,
                "name": gpu.name,
                "load_percent": round(gpu.load * 100, 2),
                "memory_used_mb": gpu.memoryUsed,
                "memory_total_mb": gpu.memoryTotal,
                "temperature_c": gpu.temperature,
            }
            for gpu in GPUtil.getGPUs()
        ]
    except Exception:
        # GPU availability varies by host and driver; it must not break scraping.
        return []


def get_battery_info() -> dict | None:
    try:
        battery = psutil.sensors_battery()
    except (AttributeError, OSError, NotImplementedError):
        return None

    if battery is None:
        return None

    seconds_left: int | None = battery.secsleft
    if seconds_left in (
        psutil.POWER_TIME_UNLIMITED,
        psutil.POWER_TIME_UNKNOWN,
    ):
        seconds_left = None

    return {
        "percent": battery.percent,
        "plugged_in": battery.power_plugged,
        "seconds_left": seconds_left,
    }


def get_system_info() -> dict:
    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "uptime": max(0.0, time.time() - psutil.boot_time()),
        "cpu_count": psutil.cpu_count(logical=True) or 1,
        "battery": get_battery_info(),
    }
