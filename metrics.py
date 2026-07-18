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
    fields = ["pid", "name", "cpu_percent", "memory_percent", "memory_info", "num_threads", "status"]
    processes = []
    for proc in psutil.process_iter(fields):
        try:
            info = proc.info
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info.get("name", "unknown"),
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_percent": round(info["memory_percent"] or 0.0, 3),
                    "memory_rss_bytes": info["memory_info"].rss if info["memory_info"] else 0,
                    "num_threads": info.get("num_threads", 0),
                    "status": info.get("status", "unknown"),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return processes[:50]


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
