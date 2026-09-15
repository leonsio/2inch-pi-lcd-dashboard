"""OpenCCU/piVCCU XML API integration."""

import requests
from lxml import etree


def _read_openccu_notifications(cfg, ip):
    token = cfg.pivccu["token"]
    if not ip:
        raise ValueError("OpenCCU IP is not configured")
    if not token:
        raise ValueError("pivccu.token is not configured")

    url = f"http://{ip}/addons/xmlapi/systemNotification.cgi"
    response = requests.get(url, params={"sid": token}, timeout=getattr(cfg, "REQUEST_TIMEOUT", 5))
    response.raise_for_status()
    tree = etree.fromstring(response.content)
    return len(tree.xpath(".//notification"))


def collect_medium(state, cfg, logger):
    state["openccu_ip"] = cfg.pivccu["ip"]
    state["openccu_online"] = False
    state["openccu_messages"] = None

    try:
        state["openccu_messages"] = _read_openccu_notifications(
            cfg,
            state["openccu_ip"],
        )
        state["openccu_online"] = True
    except Exception:
        logger.warning("MEDIUM OpenCCU XML API unavailable")


def card_openccu(state):
    online = bool(state.get("openccu_online"))
    messages = state.get("openccu_messages")
    if online:
        value = "ERR ?" if messages is None else f"ERR {messages}"
        status = "error" if messages not in (0, None) else "ok"
    else:
        value = "OFFLINE"
        status = "error"

    return {
        "title": "OpenCCU",
        "value": value,
        "detail": state.get("openccu_ip") or "",
        "status": status,
    }


CARD_BUILDERS = {"pivccu": card_openccu, "openccu": card_openccu}
