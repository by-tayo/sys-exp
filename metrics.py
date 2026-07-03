"""
metrics.py — Windows system metrics collector (psutil-based)
Maps to Windows Task Manager panels: CPU, Memory, Disk, Network, Processes.
"""

import psutil
import platform
import time
import socket


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
    try:
        disk = psutil.disk_usage("C:\\")
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "mount": "C:\\",
        }
    except PermissionError:
        return {"total": 0, "used": 0, "free": 0, "percent": 0.0, "mount": "C:\\"}


def get_network_usage():
    net = psutil.net_io_counters()
    return {
        "bytes_sent": net.bytes_sent,
        "bytes_recv": net.bytes_recv,
    }


def get_process_list():
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            processes.append(
                {
                    "pid": proc.info["pid"],
                    "name": proc.info.get("name", "unknown"),
                    "cpu_percent": proc.info["cpu_percent"] or 0.0,
                    "memory_percent": round(proc.info["memory_percent"] or 0.0, 3),
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return processes[:50]


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
        "hostname": "tayo",
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "uptime": time.time() - psutil.boot_time(),
        "cpu_count": psutil.cpu_count(logical=True),
        "battery": get_battery_info(),
    }