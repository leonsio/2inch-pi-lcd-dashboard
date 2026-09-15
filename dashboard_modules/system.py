"""System metrics and dashboard cards."""

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


def _cpu_frequency():
    try:
        freq = psutil.cpu_freq()
        if freq is None:
            return None, None
        current = float(freq.current or 0)
        maximum = float(freq.max or 0)
        return current or None, maximum or None
    except Exception:
        return None, None


def collect_fast(state, cfg, logger):
    """Values that benefit from a one-second refresh."""
    per_core = bool(getattr(cfg, "SHOW_PER_CORE", False))
    if per_core:
        state["cpu_percent"] = sum(psutil.cpu_percent(percpu=True))
    else:
        state["cpu_percent"] = psutil.cpu_percent()

    state["cpu_temp"] = _cpu_temp()
    current_freq, max_freq = _cpu_frequency()
    state["cpu_freq_mhz"] = current_freq
    state["cpu_freq_max_mhz"] = max_freq

    mem = psutil.virtual_memory()
    state["ram_percent"] = mem.percent
    state["ram_used_gb"] = (mem.total - mem.available) / (1024 ** 3)
    state["ram_total_gb"] = mem.total / (1024 ** 3)

    swap = psutil.swap_memory()
    state["swap_percent"] = swap.percent
    state["swap_used_gb"] = swap.used / (1024 ** 3)
    state["swap_total_gb"] = swap.total / (1024 ** 3)

    if getattr(cfg, "LOG_FAST_VALUES", False):
        logger.debug(
            "FAST cpu=%.1f%% temp=%s freq=%s ram=%.1f%% swap=%.1f%%",
            state["cpu_percent"],
            "?" if state["cpu_temp"] is None else f'{state["cpu_temp"]:.1f}C',
            "?" if current_freq is None else f"{current_freq:.0f}MHz",
            state["ram_percent"],
            state["swap_percent"],
        )


def collect_medium(state, cfg, logger):
    """System values that are useful at roughly minute resolution."""
    disk = psutil.disk_usage("/")
    state["disk_percent"] = disk.percent
    state["disk_used_gb"] = disk.used / (1024 ** 3)
    state["disk_free_gb"] = disk.free / (1024 ** 3)
    state["disk_total_gb"] = disk.total / (1024 ** 3)
    state["process_count"] = len(psutil.pids())

    uptime_seconds = max(0, int(time.time() - psutil.boot_time()))
    state["uptime_seconds"] = uptime_seconds
    try:
        state["load_1"], state["load_5"], state["load_15"] = os.getloadavg()
    except (AttributeError, OSError):
        state["load_1"] = state["load_5"] = state["load_15"] = 0.0

    if getattr(cfg, "LOG_MEDIUM_VALUES", True):
        logger.info(
            "MEDIUM disk=%.1f%% free=%.1fGB processes=%d uptime=%s load=%.2f/%.2f/%.2f",
            state["disk_percent"],
            state["disk_free_gb"],
            state["process_count"],
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


def _clamp_percent(value):
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _ring_percent_card(title, percent):
    """Create a generic percentage ring card without changing collectors."""
    percent = _clamp_percent(percent)
    return {
        "style": "ring",
        "title": title,
        "value": f"{percent:.0f}%",
        "detail": "",
        "ratio": percent / 100.0,
        "color_ratio": percent / 100.0,
        "status": _severity_percent(percent),
    }


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


def card_swap(state):
    total = float(state.get("swap_total_gb", 0) or 0)
    if total <= 0:
        return {"title": "SWAP", "value": "OFF", "detail": "NOT CONFIGURED", "status": "normal"}
    return {
        "title": "SWAP",
        "value": f"{state.get('swap_percent', 0):.0f}%",
        "detail": f"{state.get('swap_used_gb', 0):.1f}/{total:.1f}GB",
        "status": _severity_percent(state.get("swap_percent", 0)),
    }


def card_hdd(state):
    return {
        "title": "HDD",
        "value": f"{state.get('disk_percent', 0):.0f}%",
        "detail": f"{state.get('disk_used_gb', 0):.1f}/{state.get('disk_total_gb', 0):.0f}GB",
        "status": _severity_percent(state.get("disk_percent", 0)),
    }


def card_disk_free(state):
    return {
        "title": "DISK FREE",
        "value": f"{state.get('disk_free_gb', 0):.1f}GB",
        "detail": f"TOTAL {state.get('disk_total_gb', 0):.0f}GB",
        "status": "normal",
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


def card_cpu_freq(state):
    current = state.get("cpu_freq_mhz")
    maximum = state.get("cpu_freq_max_mhz")
    if current is None:
        return {"title": "CPU FREQ", "value": "?", "detail": "", "status": "normal"}
    detail = ""
    if maximum:
        detail = f"MAX {maximum / 1000.0:.2f}GHz"
    return {
        "title": "CPU FREQ",
        "value": f"{float(current) / 1000.0:.2f}GHz",
        "detail": detail,
        "status": "normal",
    }


def card_processes(state):
    return {
        "title": "PROCESSES",
        "value": str(int(state.get("process_count", 0) or 0)),
        "detail": f"CPU {int(state.get('cpu_count', 1) or 1)} THREADS",
        "status": "normal",
    }


# -----------------------------------------------------------------------------
# Ring/donut variants.
# -----------------------------------------------------------------------------
def card_cpu_ring(state):
    return _ring_percent_card("CPU", state.get("cpu_percent", 0))


def card_ram_ring(state):
    return _ring_percent_card("RAM", state.get("ram_percent", 0))


def card_swap_ring(state):
    if float(state.get("swap_total_gb", 0) or 0) <= 0:
        return {
            "style": "ring", "title": "SWAP", "value": "OFF", "detail": "",
            "ratio": 0.0, "color_ratio": None, "status": "normal",
        }
    return _ring_percent_card("SWAP", state.get("swap_percent", 0))


def card_disk_ring(state):
    return _ring_percent_card("DISK", state.get("disk_percent", 0))


def card_freq_ring(state):
    current = float(state.get("cpu_freq_mhz", 0) or 0)
    maximum = float(state.get("cpu_freq_max_mhz", 0) or 0)
    ratio = current / maximum if maximum > 0 else 0.0
    value = "?" if current <= 0 else f"{current / 1000.0:.1f}G"
    return {
        "style": "ring",
        "title": "CPU FREQ",
        "value": value,
        "detail": "",
        "ratio": max(0.0, min(1.0, ratio)),
        # Frequency itself is not an error condition; keep the ring on the low/green color stop.
        "color_ratio": 0.0 if current > 0 else None,
        "status": "normal",
    }


def card_temp_ring(state):
    temp = state.get("cpu_temp")
    if temp is None:
        return {
            "style": "ring",
            "title": "TEMP",
            "value": "?°C",
            "detail": "",
            "ring_metric": "temperature",
            "raw_value": None,
            "ratio": 0.0,
            "color_ratio": None,
            "status": "normal",
        }

    return {
        "style": "ring",
        "title": "TEMP",
        "value": f"{float(temp):.0f}°C",
        "detail": "",
        "ring_metric": "temperature",
        "raw_value": float(temp),
        "ratio": 0.0,
        "color_ratio": None,
        "status": "normal",
    }


CARD_BUILDERS = {
    "cpu": card_cpu,
    "ram": card_ram,
    "swap": card_swap,
    "hdd": card_hdd,
    "disk_free": card_disk_free,
    "uptime": card_uptime,
    "load": card_load,
    "cpu_freq": card_cpu_freq,
    "processes": card_processes,
    "cpu_ring": card_cpu_ring,
    "ram_ring": card_ram_ring,
    "swap_ring": card_swap_ring,
    "disk_ring": card_disk_ring,
    "hdd_ring": card_disk_ring,
    "freq_ring": card_freq_ring,
    "temp_ring": card_temp_ring,
}
