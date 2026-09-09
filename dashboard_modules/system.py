"""System metrics for TFT2."""

import os
import time
import psutil


def _cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None
        preferred = ("cpu_thermal", "soc_thermal", "coretemp")
        for name in preferred:
            if name in temps and temps[name]:
                return temps[name][0].current
        first_group = next(iter(temps.values()))
        return first_group[0].current if first_group else None
    except Exception:
        return None


def collect_fast(state, cfg, logger):
    """Values that benefit from a one-second refresh."""
    per_core = bool(getattr(cfg, "SHOW_PER_CORE", False))
    if per_core:
        state["cpu_percent"] = sum(psutil.cpu_percent(percpu=True))
    else:
        state["cpu_percent"] = psutil.cpu_percent()

    state["cpu_temp"] = _cpu_temp()
    mem = psutil.virtual_memory()
    state["ram_percent"] = mem.percent
    state["ram_used_gb"] = (mem.total - mem.available) / (1024 ** 3)
    state["ram_total_gb"] = mem.total / (1024 ** 3)

    if getattr(cfg, "LOG_FAST_VALUES", False):
        logger.debug(
            "FAST cpu=%.1f%% temp=%s ram=%.1f%%",
            state["cpu_percent"],
            "?" if state["cpu_temp"] is None else f'{state["cpu_temp"]:.1f}C',
            state["ram_percent"],
        )


def collect_medium(state, cfg, logger):
    """System values that are useful at roughly minute resolution."""
    disk = psutil.disk_usage("/")
    state["disk_percent"] = disk.percent
    state["disk_used_gb"] = disk.used / (1024 ** 3)
    state["disk_total_gb"] = disk.total / (1024 ** 3)

    uptime_seconds = max(0, int(time.time() - psutil.boot_time()))
    state["uptime_seconds"] = uptime_seconds
    try:
        state["load_1"], state["load_5"], state["load_15"] = os.getloadavg()
    except (AttributeError, OSError):
        state["load_1"] = state["load_5"] = state["load_15"] = 0.0

    if getattr(cfg, "LOG_MEDIUM_VALUES", True):
        logger.info(
            "MEDIUM disk=%.1f%% uptime=%s load=%.2f/%.2f/%.2f",
            state["disk_percent"],
            format_uptime(uptime_seconds),
            state["load_1"], state["load_5"], state["load_15"],
        )


def collect_slow(state, cfg, logger):
    """Mostly static system information."""
    state["cpu_count"] = psutil.cpu_count(logical=True) or 1
    state["boot_time"] = psutil.boot_time()
    if getattr(cfg, "LOG_SLOW_VALUES", True):
        logger.info(
            "SLOW cpu_count=%s boot_time=%s",
            state["cpu_count"],
            int(state["boot_time"]),
        )


def format_uptime(seconds):
    days, remainder = divmod(int(seconds or 0), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    if days:
        return f"{days}d {hours:02d}h"
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def _severity_percent(value):
    value = float(value or 0)
    if value >= 90:
        return "error"
    if value >= 70:
        return "warn"
    return "ok"


def card_cpu(state):
    temp = state.get("cpu_temp")
    detail = "TEMP ?" if temp is None else f"TEMP {temp:.0f}°C"
    return {
        "title": "CPU",
        "value": f"{state.get('cpu_percent', 0):.0f}%",
        "detail": detail,
        "status": _severity_percent(state.get("cpu_percent", 0)),
    }


def card_ram(state):
    return {
        "title": "RAM",
        "value": f"{state.get('ram_percent', 0):.0f}%",
        "detail": f"{state.get('ram_used_gb', 0):.1f}/{state.get('ram_total_gb', 0):.0f}GB",
        "status": _severity_percent(state.get("ram_percent", 0)),
    }


def card_hdd(state):
    return {
        "title": "HDD",
        "value": f"{state.get('disk_percent', 0):.0f}%",
        "detail": f"{state.get('disk_used_gb', 0):.1f}/{state.get('disk_total_gb', 0):.0f}GB",
        "status": _severity_percent(state.get("disk_percent", 0)),
    }


def card_uptime(state):
    return {
        "title": "UPTIME",
        "value": format_uptime(state.get("uptime_seconds", 0)),
        "detail": f"L {state.get('load_1', 0):.1f}/{state.get('load_5', 0):.1f}/{state.get('load_15', 0):.1f}",
        "status": "normal",
    }


def card_load(state):
    return {
        "title": "LOAD",
        "value": f"{state.get('load_1', 0):.2f}",
        "detail": f"5m {state.get('load_5', 0):.2f} 15m {state.get('load_15', 0):.2f}",
        "status": "normal",
    }


CARD_BUILDERS = {
    "cpu": card_cpu,
    "ram": card_ram,
    "hdd": card_hdd,
    "uptime": card_uptime,
    "load": card_load,
}
