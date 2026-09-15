"""Configurable filesystem, disk I/O and optional SMART dashboard cards."""

import json
import os
import shutil
import subprocess
import time

import psutil


_GIB = 1024 ** 3


def _title(alias, item):
    return str(item.get("title") or alias.replace("_", " ").upper())


def _partitions():
    try:
        return list(psutil.disk_partitions(all=True))
    except Exception:
        return []


def _partition_for_mount(mount, partitions):
    mount = os.path.normpath(str(mount))
    for part in partitions:
        if os.path.normpath(str(part.mountpoint)) == mount:
            return part
    return None


def _io_key(alias, item, device_state):
    configured = str(item.get("io_device") or "").strip()
    if configured:
        return os.path.basename(configured)
    configured = str(item.get("device") or "").strip()
    if configured:
        return os.path.basename(configured)
    source = str((device_state or {}).get("source") or "").strip()
    if source.startswith("/dev/"):
        return os.path.basename(source)
    return ""


def collect_fast(state, cfg, logger):
    """Calculate per-device read/write rates from psutil disk counters."""
    devices = cfg.storage.get("devices", {})
    try:
        counters = psutil.disk_io_counters(perdisk=True) or {}
    except Exception:
        counters = {}

    now = time.monotonic()
    previous = dict(state.get("_storage_io_previous") or {})
    rates = dict(state.get("storage_io") or {})
    device_states = state.get("storage_devices") or {}

    for alias, item in devices.items():
        key = _io_key(alias, item, device_states.get(alias))
        counter = counters.get(key) if key else None
        if counter is None:
            rates[alias] = {"read_bps": None, "write_bps": None, "device": key}
            continue

        current = (int(counter.read_bytes), int(counter.write_bytes), now)
        old = previous.get(alias)
        read_bps = write_bps = None
        if old:
            elapsed = max(0.001, now - float(old[2]))
            read_bps = max(0.0, (current[0] - int(old[0])) / elapsed)
            write_bps = max(0.0, (current[1] - int(old[1])) / elapsed)
        previous[alias] = current
        rates[alias] = {"read_bps": read_bps, "write_bps": write_bps, "device": key}

    state["_storage_io_previous"] = previous
    state["storage_io"] = rates

    if getattr(cfg, "LOG_FAST_VALUES", False):
        logger.debug("FAST storage I/O devices=%d", len(devices))


def collect_medium(state, cfg, logger):
    """Refresh filesystem capacity, mount state and source device metadata."""
    partitions = _partitions()
    result = {}

    for alias, item in cfg.storage.get("devices", {}).items():
        mount = str(item.get("mount") or "/")
        part = _partition_for_mount(mount, partitions)
        entry = {
            "mount": mount,
            "mounted": False,
            "source": str(part.device) if part else "",
            "fstype": str(part.fstype) if part else "",
            "total": 0,
            "used": 0,
            "free": 0,
            "percent": 0.0,
        }
        try:
            usage = psutil.disk_usage(mount)
            entry.update({
                "mounted": True,
                "total": int(usage.total),
                "used": int(usage.used),
                "free": int(usage.free),
                "percent": float(usage.percent),
            })
        except (FileNotFoundError, PermissionError, OSError):
            pass
        result[alias] = entry

    state["storage_devices"] = result

    if getattr(cfg, "LOG_MEDIUM_VALUES", True):
        mounted = sum(1 for item in result.values() if item["mounted"])
        logger.info("MEDIUM storage mounted=%d/%d", mounted, len(result))


def _smart_temperature(payload):
    value = (payload.get("temperature") or {}).get("current")
    if value is None:
        value = (payload.get("nvme_smart_health_information_log") or {}).get("temperature")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _smart_snapshot(command, device, timeout):
    executable = shutil.which(command) if not os.path.isabs(command) else command
    if not executable or not os.path.exists(executable):
        return {"status": "UNAVAILABLE", "passed": None, "temperature": None}

    try:
        proc = subprocess.run(
            [executable, "-j", "-H", "-A", device],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {"status": "ERROR", "passed": None, "temperature": None}

    try:
        payload = json.loads(proc.stdout or "{}")
    except (TypeError, ValueError):
        return {"status": "ERROR", "passed": None, "temperature": None}

    passed = (payload.get("smart_status") or {}).get("passed")
    if passed is None:
        critical = (payload.get("nvme_smart_health_information_log") or {}).get("critical_warning")
        if critical is not None:
            try:
                passed = int(critical) == 0
            except (TypeError, ValueError):
                passed = None

    if passed is True:
        status = "PASSED"
    elif passed is False:
        status = "FAILED"
    else:
        status = "UNKNOWN"

    return {
        "status": status,
        "passed": passed,
        "temperature": _smart_temperature(payload),
    }


def collect_slow(state, cfg, logger):
    """Refresh optional SMART health information."""
    timeout = float(getattr(cfg, "REQUEST_TIMEOUT", 5))
    command = str(cfg.storage.get("smartctl") or "smartctl")
    smart = {}

    for alias, item in cfg.storage.get("devices", {}).items():
        if not bool(item.get("smart", False)):
            smart[alias] = {"status": "DISABLED", "passed": None, "temperature": None}
            continue
        device = str(item.get("device") or "").strip()
        smart[alias] = _smart_snapshot(command, device, timeout)

    state["storage_smart"] = smart
    if getattr(cfg, "LOG_SLOW_VALUES", True):
        enabled = sum(1 for item in cfg.storage.get("devices", {}).values() if item.get("smart", False))
        failed = sum(1 for item in smart.values() if item.get("passed") is False)
        logger.info("SLOW storage SMART enabled=%d failed=%d", enabled, failed)


def _severity_percent(value):
    value = float(value or 0)
    if value >= 90:
        return "error"
    if value >= 70:
        return "warn"
    return "ok"


def _format_bytes_per_second(value):
    if value is None:
        return "WAIT"
    value = float(value)
    if value >= 1024 ** 2:
        return f"{value / (1024 ** 2):.1f}MB/s"
    if value >= 1024:
        return f"{value / 1024:.0f}KB/s"
    return f"{value:.0f}B/s"


def card_storage(state):
    devices = state.get("storage_devices") or {}
    if not devices:
        return {"title": "STORAGE", "value": "WAIT", "detail": "", "status": "normal"}

    mounted = sum(1 for item in devices.values() if item.get("mounted"))
    total = len(devices)
    smart = state.get("storage_smart") or {}
    checked = [item for item in smart.values() if item.get("status") != "DISABLED"]
    failed = sum(1 for item in checked if item.get("passed") is False)
    smart_warning = any(item.get("status") not in ("PASSED", "FAILED") for item in checked)

    if failed:
        detail = f"SMART FAIL {failed}"
    elif checked and smart_warning:
        detail = "SMART WARN"
    elif checked:
        detail = "SMART OK"
    else:
        detail = ""

    if failed:
        status = "error"
    elif mounted != total or smart_warning:
        status = "warn"
    else:
        status = "ok"

    return {
        "title": "STORAGE",
        "value": f"{mounted}/{total} MOUNT",
        "detail": detail,
        "status": status,
    }


def _usage_card(alias, item, state):
    title = _title(alias, item)
    data = (state.get("storage_devices") or {}).get(alias)
    if not data:
        return {"title": title, "value": "WAIT", "detail": "", "status": "normal"}
    if not data.get("mounted"):
        return {"title": title, "value": "UNMOUNTED", "detail": data.get("mount", ""), "status": "error"}
    percent = float(data.get("percent") or 0)
    return {
        "title": title,
        "value": f"{percent:.0f}%",
        "detail": f"{data.get('used', 0) / _GIB:.1f}/{data.get('total', 0) / _GIB:.1f}GB",
        "status": _severity_percent(percent),
    }


def _ring_card(alias, item, state):
    title = _title(alias, item)
    data = (state.get("storage_devices") or {}).get(alias)
    if not data or not data.get("mounted"):
        return {
            "style": "ring", "title": title,
            "value": "WAIT" if not data else "OFF",
            "detail": "", "ratio": 0.0, "color_ratio": None,
            "status": "normal" if not data else "error",
        }
    percent = max(0.0, min(100.0, float(data.get("percent") or 0)))
    return {
        "style": "ring", "title": title, "value": f"{percent:.0f}%", "detail": "",
        "ratio": percent / 100.0, "color_ratio": percent / 100.0,
        "status": _severity_percent(percent),
    }


def _free_card(alias, item, state):
    title = f"{_title(alias, item)} FREE"
    data = (state.get("storage_devices") or {}).get(alias)
    if not data:
        return {"title": title, "value": "WAIT", "detail": "", "status": "normal"}
    if not data.get("mounted"):
        return {"title": title, "value": "UNMOUNTED", "detail": data.get("mount", ""), "status": "error"}
    return {
        "title": title,
        "value": f"{data.get('free', 0) / _GIB:.1f}GB",
        "detail": data.get("mount", ""),
        "status": _severity_percent(data.get("percent", 0)),
    }


def _io_card(alias, item, state):
    title = f"{_title(alias, item)} I/O"
    data = (state.get("storage_io") or {}).get(alias)
    if not data or data.get("read_bps") is None or data.get("write_bps") is None:
        detail = (data or {}).get("device", "")
        return {"title": title, "value": "WAIT", "detail": detail, "status": "normal"}
    return {
        "title": title,
        "value": f"R {_format_bytes_per_second(data['read_bps'])}",
        "detail": f"W {_format_bytes_per_second(data['write_bps'])}",
        "status": "ok",
    }


def _smart_card(alias, item, state):
    title = f"{_title(alias, item)} SMART"
    data = (state.get("storage_smart") or {}).get(alias)
    if not data:
        return {"title": title, "value": "WAIT", "detail": "", "status": "normal"}
    status_text = str(data.get("status") or "UNKNOWN")
    temperature = data.get("temperature")
    detail = "" if temperature is None else f"TEMP {temperature:.0f}°C"
    if status_text == "PASSED":
        status = "ok"
    elif status_text == "DISABLED":
        status = "normal"
    elif status_text in ("UNAVAILABLE", "UNKNOWN"):
        status = "warn"
    else:
        status = "error"
    return {"title": title, "value": status_text, "detail": detail, "status": status}


def build_cards(cfg):
    cards = {}
    for alias, item in cfg.storage.get("devices", {}).items():
        cards[f"storage.{alias}"] = lambda state, alias=alias, item=item: _usage_card(alias, item, state)
        cards[f"storage.{alias}_ring"] = lambda state, alias=alias, item=item: _ring_card(alias, item, state)
        cards[f"storage.{alias}_free"] = lambda state, alias=alias, item=item: _free_card(alias, item, state)
        cards[f"storage.{alias}_io"] = lambda state, alias=alias, item=item: _io_card(alias, item, state)
        cards[f"storage.{alias}_smart"] = lambda state, alias=alias, item=item: _smart_card(alias, item, state)
    return cards


CARD_BUILDERS = {
    "storage": card_storage,
}
