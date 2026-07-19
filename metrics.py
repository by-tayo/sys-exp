"""
metrics.py — cross-platform system metrics collector (psutil-based)
Maps to OS Task Manager / Activity Monitor panels: CPU, Memory, Disk, Network,
Processes, GPU. Works on Windows, Linux, and macOS.
"""

import os
import psutil
import platform
import time
import socket

try:
    import GPUtil
    _GPU_AVAILABLE = True
except ImportError:
    _GPU_AVAILABLE = False


def get_cpu_usage():
    # interval=1 blocks for 1 second and returns an accurate CPU reading.
    # interval=None returns instantly but gives 0.0 on the very first call
    # per process — a known psutil behavior on Windows.
    return psutil.cpu_percent(interval=1)


def get_memory_usage():
    mem = psutil.virtual_memory()
    return {
        "total": mem.total,
        "used": mem.used,
        "available": mem.available,
        "percent": mem.percent,
    }


def get_disk_usage():
    # os.path.abspath(os.sep) resolves to the system drive root on every OS:
    # "C:\\" on Windows, "/" on Linux/macOS.
    mount = os.path.abspath(os.sep)
    try:
        disk = psutil.disk_usage(mount)
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "mount": mount,
        }
    except PermissionError:
        return {"total": 0, "used": 0, "free": 0, "percent": 0.0, "mount": mount}


def get_network_usage():
    net = psutil.net_io_counters()
    return {
        "bytes_sent": net.bytes_sent,
        "bytes_recv": net.bytes_recv,
    }


def get_process_list():
    # Deliberately minimal fields. On Windows, adding num_threads/status/
    # memory_info to process_iter() here forces a syscall per process for
    # *every* process on the system — measured at ~19s for 450 processes
    # vs ~2.5s for just these four fields, which blows past Prometheus's
    # scrape timeout. Get per-process detail via get_process_detail()
    # instead, only for the handful of processes actually displayed.
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info.get("name", "unknown"),
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_percent": round(info["memory_percent"] or 0.0, 3),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return processes[:50]


def get_process_detail(pid):
    """RSS memory, thread count, and status for a single process.

    Only call this for a small, already-selected set of processes (e.g.
    the top N by CPU) — see get_process_list()'s docstring for why doing
    this for every process on the system is too slow.
    """
    try:
        proc = psutil.Process(pid)
        with proc.oneshot():
            return {
                "memory_rss_bytes": proc.memory_info().rss,
                "num_threads": proc.num_threads(),
                "status": proc.status(),
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {"memory_rss_bytes": 0, "num_threads": 0, "status": "unknown"}


def get_gpu_usage():
    """Returns per-GPU load/memory stats, or [] if no GPU or GPUtil unavailable."""
    if not _GPU_AVAILABLE:
        return []
    try:
        gpus = GPUtil.getGPUs()
    except Exception:
        return []
    return [
        {
            "id": gpu.id,
            "name": gpu.name,
            "load_percent": round(gpu.load * 100, 2),
            "memory_used_mb": gpu.memoryUsed,
            "memory_total_mb": gpu.memoryTotal,
            "temperature_c": gpu.temperature,
        }
        for gpu in gpus
    ]


def get_battery_info():
    battery = psutil.sensors_battery()
    if battery is None:
        return None
    return {
        "percent": battery.percent,
        "plugged_in": battery.power_plugged,
        "seconds_left": (
            battery.secsleft
            if battery.secsleft not in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN)
            else None
        ),
    }


def get_system_info():
    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "uptime": time.time() - psutil.boot_time(),
        "cpu_count": psutil.cpu_count(logical=True),
        "battery": get_battery_info(),
    }
