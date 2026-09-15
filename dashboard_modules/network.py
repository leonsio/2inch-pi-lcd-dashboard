"""Network information, traffic metrics and optional WAN reachability checks."""

import ipaddress
import math
import shutil
import socket
import subprocess
import time
import warnings

import netifaces
import psutil
import requests
from urllib3.exceptions import InsecureRequestWarning


_INTERVALS = {"fast", "medium", "slow"}


def _find_ip(preferred_interfaces):
    for interface in preferred_interfaces:
        try:
            addresses = netifaces.ifaddresses(interface)
        except ValueError:
            continue
        ip_info = addresses.get(netifaces.AF_INET)
        if not ip_info:
            continue
        for entry in ip_info:
            address = entry.get("addr")
            if address and not address.startswith("127."):
                return interface, address
    return "", None


def _wireless_info(interface):
    """Return (quality_percent, signal_dbm) from Linux /proc/net/wireless."""
    if not interface:
        return None, None
    try:
        with open("/proc/net/wireless", "r", encoding="utf-8") as handle:
            for line in handle:
                if ":" not in line:
                    continue
                name, values = line.split(":", 1)
                if name.strip() != interface:
                    continue
                fields = values.split()
                if len(fields) < 3:
                    return None, None
                quality = float(fields[1].rstrip("."))
                signal = float(fields[2].rstrip("."))
                quality_percent = max(0.0, min(100.0, quality / 70.0 * 100.0))
                return quality_percent, signal
    except (OSError, ValueError):
        pass
    return None, None


def _format_rate(value):
    value = max(0.0, float(value or 0))
    if value >= 1024 ** 3:
        return f"{value / (1024 ** 3):.1f}G/s"
    if value >= 1024 ** 2:
        return f"{value / (1024 ** 2):.1f}M/s"
    if value >= 1024:
        return f"{value / 1024:.1f}K/s"
    return f"{value:.0f}B/s"


def _format_bytes(value):
    value = max(0.0, float(value or 0))
    if value >= 1024 ** 3:
        return f"{value / (1024 ** 3):.1f}GB"
    if value >= 1024 ** 2:
        return f"{value / (1024 ** 2):.1f}MB"
    if value >= 1024:
        return f"{value / 1024:.1f}KB"
    return f"{value:.0f}B"


def _interval(item, default="medium"):
    value = str((item or {}).get("interval", default)).lower()
    return value if value in _INTERVALS else default


def _timeout(item, default=1.0):
    try:
        value = float((item or {}).get("timeout", default))
    except (TypeError, ValueError):
        value = default
    return max(0.1, min(30.0, value))


def _ipv4(value):
    try:
        return str(ipaddress.IPv4Address(str(value).strip()))
    except (ipaddress.AddressValueError, ValueError):
        return None


def _ping_ipv4(target, timeout):
    """Return a reachability snapshot using one ICMP echo request."""
    target = _ipv4(target)
    if not target:
        return {"target": str(target or ""), "online": None, "latency_ms": None, "error": "CONFIG"}

    executable = shutil.which("ping")
    if not executable:
        return {"target": target, "online": None, "latency_ms": None, "error": "PING"}

    started = time.monotonic()
    wait_seconds = max(1, int(math.ceil(timeout)))
    try:
        result = subprocess.run(
            [executable, "-n", "-c", "1", "-W", str(wait_seconds), target],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + 1.0,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"target": target, "online": False, "latency_ms": None, "error": "TIMEOUT"}
    except OSError:
        return {"target": target, "online": None, "latency_ms": None, "error": "PING"}

    elapsed_ms = (time.monotonic() - started) * 1000.0
    return {
        "target": target,
        "online": result.returncode == 0,
        "latency_ms": elapsed_ms if result.returncode == 0 else None,
        "error": "" if result.returncode == 0 else "",
    }


def _fetch_external_ipv4(item, cfg):
    url = str((item or {}).get("url") or "https://api.ipify.org").strip()
    verify_ssl = bool((item or {}).get("verify_ssl", True))
    timeout = float(getattr(cfg, "REQUEST_TIMEOUT", 5))
    try:
        with warnings.catch_warnings():
            if not verify_ssl:
                warnings.simplefilter("ignore", InsecureRequestWarning)
            response = requests.get(
                url,
                headers={"Accept": "text/plain"},
                timeout=timeout,
                verify=verify_ssl,
            )
        if response.status_code in (401, 403):
            return {"ip": None, "error": "AUTH"}
        if response.status_code >= 400:
            return {"ip": None, "error": f"HTTP {response.status_code}"}
        address = _ipv4(response.text)
        if not address:
            return {"ip": None, "error": "INVALID"}
        return {"ip": address, "error": ""}
    except requests.RequestException:
        return {"ip": None, "error": "OFFLINE"}


def _ping_cached(target, timeout, cache):
    normalized = _ipv4(target)
    key = (normalized or str(target), float(timeout))
    if key not in cache:
        cache[key] = _ping_ipv4(target, timeout)
    return dict(cache[key])


def _collect_monitoring(state, cfg, logger, group):
    block = getattr(cfg, "network", {}) or {}
    cache = {}
    polled = 0

    wan = block.get("wan", {}) or {}
    if bool(wan.get("enabled", False)) and _interval(wan) == group:
        state["wan_status"] = _ping_cached(
            wan.get("target", "1.1.1.1"), _timeout(wan), cache
        )
        polled += 1

    external = block.get("external_ipv4", {}) or {}
    if bool(external.get("enabled", False)) and _interval(external, "slow") == group:
        state["external_ipv4"] = _fetch_external_ipv4(external, cfg)
        polled += 1

    results = dict(state.get("network_checks") or {})
    for alias, item in (block.get("checks", {}) or {}).items():
        if not isinstance(item, dict) or _interval(item) != group:
            continue
        results[alias] = _ping_cached(item.get("ip", ""), _timeout(item), cache)
        polled += 1
    state["network_checks"] = results

    setting = {
        "fast": "LOG_FAST_VALUES",
        "medium": "LOG_MEDIUM_VALUES",
        "slow": "LOG_SLOW_VALUES",
    }[group]
    if polled and getattr(cfg, setting, group != "fast"):
        online = 0
        if group == _interval(wan) and state.get("wan_status", {}).get("online") is True:
            online += 1
        online += sum(
            1 for alias, item in (block.get("checks", {}) or {}).items()
            if isinstance(item, dict)
            and _interval(item) == group
            and results.get(alias, {}).get("online") is True
        )
        log = logger.debug if group == "fast" else logger.info
        log("%s network monitoring checks=%d online=%d", group.upper(), polled, online)


def collect_fast(state, cfg, logger):
    """Calculate traffic rates and run optional fast WAN/IP checks."""
    interface = state.get("network_interface")
    counters = psutil.net_io_counters(pernic=True).get(interface) if interface else None

    if counters is None:
        state["network_rx_rate"] = 0.0
        state["network_tx_rate"] = 0.0
    else:
        now = time.monotonic()
        previous_interface = state.get("_network_prev_interface")
        previous_time = state.get("_network_prev_time")
        previous_recv = state.get("_network_prev_recv")
        previous_sent = state.get("_network_prev_sent")

        rx_rate = tx_rate = 0.0
        if (
            previous_interface == interface
            and previous_time is not None
            and previous_recv is not None
            and previous_sent is not None
            and now > previous_time
        ):
            elapsed = now - previous_time
            rx_rate = max(0.0, (counters.bytes_recv - previous_recv) / elapsed)
            tx_rate = max(0.0, (counters.bytes_sent - previous_sent) / elapsed)

        state["network_rx_rate"] = rx_rate
        state["network_tx_rate"] = tx_rate
        state["network_rx_bytes"] = counters.bytes_recv
        state["network_tx_bytes"] = counters.bytes_sent
        state["_network_prev_interface"] = interface
        state["_network_prev_time"] = now
        state["_network_prev_recv"] = counters.bytes_recv
        state["_network_prev_sent"] = counters.bytes_sent

        if getattr(cfg, "LOG_FAST_VALUES", False):
            logger.debug(
                "FAST network interface=%s rx=%s tx=%s",
                interface,
                _format_rate(rx_rate),
                _format_rate(tx_rate),
            )

    _collect_monitoring(state, cfg, logger, "fast")


def collect_medium(state, cfg, logger):
    interfaces = getattr(cfg, "NETWORK_INTERFACES", ["eth0", "wlan0"])
    interface, address = _find_ip(interfaces)
    state["network_interface"] = interface
    state["ip_address"] = address

    stats = psutil.net_if_stats().get(interface) if interface else None
    state["network_is_up"] = bool(stats and stats.isup)
    state["network_speed_mbps"] = int(stats.speed) if stats and stats.speed and stats.speed > 0 else 0
    state["network_mtu"] = int(stats.mtu) if stats else 0

    counters = psutil.net_io_counters(pernic=True).get(interface) if interface else None
    if counters:
        state["network_rx_bytes"] = counters.bytes_recv
        state["network_tx_bytes"] = counters.bytes_sent
        state["network_errors"] = counters.errin + counters.errout
        state["network_drops"] = counters.dropin + counters.dropout
    else:
        state["network_errors"] = 0
        state["network_drops"] = 0

    wifi_quality, wifi_signal = _wireless_info(interface)
    state["wifi_quality_percent"] = wifi_quality
    state["wifi_signal_dbm"] = wifi_signal

    if getattr(cfg, "LOG_MEDIUM_VALUES", True):
        logger.info(
            "MEDIUM network interface=%s ip=%s up=%s speed=%sMbps wifi=%s",
            interface or "-",
            address or "none",
            state["network_is_up"],
            state["network_speed_mbps"] or "?",
            "-" if wifi_quality is None else f"{wifi_quality:.0f}%",
        )

    _collect_monitoring(state, cfg, logger, "medium")


def collect_slow(state, cfg, logger):
    state["hostname"] = socket.gethostname()
    if getattr(cfg, "LOG_SLOW_VALUES", True):
        logger.info("SLOW hostname=%s", state["hostname"])
    _collect_monitoring(state, cfg, logger, "slow")


def card_ip(state):
    value = state.get("ip_address") or "NO IP"
    detail = state.get("network_interface") or "NO IFACE"
    return {
        "title": "IP",
        "value": value,
        "detail": detail,
        "status": "normal" if state.get("ip_address") else "error",
    }


def card_hostname(state):
    return {
        "title": "HOSTNAME",
        "value": state.get("hostname") or "?",
        "detail": state.get("ip_address") or "NO IP",
        "status": "normal",
    }


def card_network(state):
    interface = state.get("network_interface") or "-"
    speed = int(state.get("network_speed_mbps", 0) or 0)
    speed_text = f" · {speed}M" if speed else ""
    return {
        "title": "NETWORK",
        "value": state.get("ip_address") or "NO IP",
        "detail": f"{state.get('hostname', '?')} · {interface}{speed_text}",
        "status": "normal" if state.get("ip_address") else "error",
    }


def card_traffic(state):
    return {
        "title": "TRAFFIC",
        "value": f"↓{_format_rate(state.get('network_rx_rate'))}",
        "detail": f"↑{_format_rate(state.get('network_tx_rate'))} · {state.get('network_interface') or '-'}",
        "status": "normal" if state.get("network_is_up") else "warn",
    }


def card_rx(state):
    return {
        "title": "DOWNLOAD",
        "value": _format_rate(state.get("network_rx_rate")),
        "detail": f"TOTAL {_format_bytes(state.get('network_rx_bytes'))}",
        "status": "normal",
    }


def card_tx(state):
    return {
        "title": "UPLOAD",
        "value": _format_rate(state.get("network_tx_rate")),
        "detail": f"TOTAL {_format_bytes(state.get('network_tx_bytes'))}",
        "status": "normal",
    }


def card_link(state):
    is_up = bool(state.get("network_is_up"))
    speed = int(state.get("network_speed_mbps", 0) or 0)
    value = f"{speed} Mbps" if speed else ("UP" if is_up else "DOWN")
    detail = f"{state.get('network_interface') or '-'} · MTU {int(state.get('network_mtu', 0) or 0)}"
    return {
        "title": "LINK",
        "value": value,
        "detail": detail,
        "status": "ok" if is_up else "error",
    }


def _wifi_status(quality):
    if quality is None:
        return "normal"
    if quality < 25:
        return "error"
    if quality < 50:
        return "warn"
    return "ok"


def card_wifi(state):
    quality = state.get("wifi_quality_percent")
    signal = state.get("wifi_signal_dbm")
    if quality is None:
        return {
            "title": "WIFI",
            "value": "N/A",
            "detail": state.get("network_interface") or "NO IFACE",
            "status": "normal",
        }
    signal_text = "? dBm" if signal is None else f"{float(signal):.0f} dBm"
    return {
        "title": "WIFI",
        "value": signal_text,
        "detail": f"{float(quality):.0f}% · {state.get('network_interface') or '-'}",
        "status": _wifi_status(float(quality)),
    }


def card_wifi_ring(state):
    quality = state.get("wifi_quality_percent")
    if quality is None:
        return {
            "style": "ring", "title": "WIFI", "value": "N/A", "detail": "",
            "ratio": 0.0, "color_ratio": None, "status": "normal",
        }
    ratio = max(0.0, min(1.0, float(quality) / 100.0))
    return {
        "style": "ring",
        "title": "WIFI",
        "value": f"{float(quality):.0f}%",
        "detail": "",
        "ratio": ratio,
        "color_ratio": 1.0 - ratio,
        "status": _wifi_status(float(quality)),
    }


def _latency_detail(result, fallback):
    if not result:
        return fallback
    latency = result.get("latency_ms")
    target = result.get("target") or fallback
    return f"{target} · {latency:.0f}ms" if latency is not None else str(target)


def card_wan(state):
    result = state.get("wan_status")
    if result is None:
        return {"title": "WAN", "value": "WAIT", "detail": "", "status": "normal"}
    error = result.get("error")
    if error in ("PING", "CONFIG"):
        return {"title": "WAN", "value": "N/A", "detail": error, "status": "warn"}
    online = result.get("online") is True
    return {
        "title": "WAN",
        "value": "ONLINE" if online else "OFFLINE",
        "detail": _latency_detail(result, ""),
        "status": "ok" if online else "error",
    }


def card_external_ipv4(state):
    result = state.get("external_ipv4")
    if result is None:
        return {"title": "WAN IP", "value": "WAIT", "detail": "", "status": "normal"}
    error = str(result.get("error") or "")
    if error:
        return {
            "title": "WAN IP",
            "value": error,
            "detail": "EXTERNAL IPv4",
            "status": "warn" if error in ("AUTH", "INVALID") else "error",
        }
    return {
        "title": "WAN IP",
        "value": result.get("ip") or "?",
        "detail": "EXTERNAL IPv4",
        "status": "ok",
    }


def _check_card(state, alias, item):
    title = str(item.get("title") or alias.replace("_", " ").upper())
    result = (state.get("network_checks") or {}).get(alias)
    if result is None:
        return {"title": title, "value": "WAIT", "detail": str(item.get("ip") or ""), "status": "normal"}
    error = result.get("error")
    if error in ("PING", "CONFIG"):
        return {"title": title, "value": "N/A", "detail": error, "status": "warn"}
    online = result.get("online") is True
    return {
        "title": title,
        "value": "ONLINE" if online else "OFFLINE",
        "detail": _latency_detail(result, str(item.get("ip") or "")),
        "status": "ok" if online else "error",
    }


def build_cards(cfg):
    cards = {}
    block = getattr(cfg, "network", {}) or {}
    if bool((block.get("wan", {}) or {}).get("enabled", False)):
        cards["wan"] = card_wan
    if bool((block.get("external_ipv4", {}) or {}).get("enabled", False)):
        cards["wan_ip"] = card_external_ipv4
        cards["external_ipv4"] = card_external_ipv4
    for alias, item in (block.get("checks", {}) or {}).items():
        if isinstance(item, dict):
            cards[f"network.{alias}"] = (
                lambda state, alias=alias, item=item: _check_card(state, alias, item)
            )
    return cards


CARD_BUILDERS = {
    "ip": card_ip,
    "hostname": card_hostname,
    "network": card_network,
    "traffic": card_traffic,
    "network_rx": card_rx,
    "network_tx": card_tx,
    "network_link": card_link,
    "wifi": card_wifi,
    "wifi_ring": card_wifi_ring,
}
