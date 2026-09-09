"""Network information for TFT2."""

import socket
import netifaces


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


def collect_medium(state, cfg, logger):
    interfaces = getattr(cfg, "NETWORK_INTERFACES", ["eth0", "wlan0"])
    interface, address = _find_ip(interfaces)
    state["network_interface"] = interface
    state["ip_address"] = address

    if getattr(cfg, "LOG_MEDIUM_VALUES", True):
        logger.info(
            "MEDIUM network interface=%s ip=%s",
            interface or "-",
            address or "none",
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
    return {
        "title": "NETWORK",
        "value": state.get("ip_address") or "NO IP",
        "detail": f"{state.get('hostname', '?')} · {state.get('network_interface') or '-'}",
        "status": "normal" if state.get("ip_address") else "error",
    }


CARD_BUILDERS = {
    "ip": card_ip,
    "hostname": card_hostname,
    "network": card_network,
}
