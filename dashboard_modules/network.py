"""Network information and traffic metrics for the dashboard."""

import socket
import time

import netifaces
import psutil


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
                # Linux wireless quality is traditionally reported on a 0..70 scale.
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


def collect_fast(state, cfg, logger):
    """Calculate per-interface receive/transmit rates from counter deltas."""
    interface = state.get("network_interface")
    if not interface:
        state["network_rx_rate"] = 0.0
        state["network_tx_rate"] = 0.0
        return

    counters = psutil.net_io_counters(pernic=True).get(interface)
    if counters is None:
        state["network_rx_rate"] = 0.0
        state["network_tx_rate"] = 0.0
        return

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


def collect_slow(state, cfg, logger):
    state["hostname"] = socket.gethostname()
    if getattr(cfg, "LOG_SLOW_VALUES", True):
        logger.info("SLOW hostname=%s", state["hostname"])


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
        # Ring fill grows with quality, while the color scale is inverted so strong signal is green.
        "color_ratio": 1.0 - ratio,
        "status": _wifi_status(float(quality)),
    }


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
