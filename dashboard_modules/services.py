"""Service/API collectors for TFT2."""

import os
import requests
from lxml import etree


def _ha_headers(cfg):
    return {
        "Authorization": f"Bearer {getattr(cfg, 'HOME_ASSISTANT_TOKEN', '')}",
        "Content-Type": "application/json",
    }


def _ha_get(cfg, path):
    base = getattr(cfg, "HOME_ASSISTANT_URL", "").rstrip("/")
    timeout = getattr(cfg, "REQUEST_TIMEOUT", 5)
    response = requests.get(
        f"{base}{path}",
        headers=_ha_headers(cfg),
        timeout=timeout,
    )
    return response


def _ha_entity(cfg, entity_id):
    if not entity_id:
        return None, "NOT CONFIGURED"
    response = _ha_get(cfg, f"/api/states/{entity_id}")
    if response.status_code == 404:
        return None, "ENTITY"
    if response.status_code in (401, 403):
        return None, "AUTH"
    response.raise_for_status()
    return response.json(), ""


def _read_pivccu_ip(cfg):
    ip = os.popen(
        "pivccu-info | grep ^IP | cut -d\":\" -f2 | tr -d ' '"
    ).read().strip()
    return ip or getattr(cfg, "PIVCCU_FALLBACK_IP", "")


def _read_pivccu_version():
    return os.popen(
        "pivccu-info | grep version | cut -d\":\" -f2 | tr -d ' '"
    ).read().strip()


def _read_pivccu_notifications(cfg, ip):
    token = getattr(cfg, "XML_RPC_TOKEN", "")
    if not ip or not token:
        return None
    url = f"http://{ip}/addons/xmlapi/systemNotification.cgi?sid={token}"
    response = requests.get(url, timeout=getattr(cfg, "REQUEST_TIMEOUT", 5))
    response.raise_for_status()
    tree = etree.fromstring(response.content)
    return len(tree.xpath(".//notification"))


def collect_medium(state, cfg, logger):
    """Poll online/service state once per minute."""
    # Home Assistant basic health + current version.
    try:
        response = _ha_get(cfg, "/api/config")
        if response.status_code in (401, 403):
            state["ha_online"] = True
            state["ha_version"] = "AUTH"
        else:
            response.raise_for_status()
            data = response.json()
            state["ha_online"] = True
            state["ha_version"] = str(data.get("version") or "?")
    except Exception as error:
        state["ha_online"] = False
        state["ha_version"] = ""
        logger.warning("MEDIUM Home Assistant unavailable: %s", error)

    # AdGuard Home via Home Assistant entities.
    state["adguard_online"] = False
    state["adguard_protection"] = None
    state["adguard_blocked_ratio"] = None
    state["adguard_detail"] = ""

    if state.get("ha_online"):
        try:
            protection_entity = getattr(cfg, "ADGUARD_PROTECTION_ENTITY", "")
            protection, detail = _ha_entity(cfg, protection_entity)
            if protection is None:
                state["adguard_detail"] = detail
            else:
                protection_state = str(protection.get("state", "")).lower()
                if protection_state in ("unavailable", "unknown"):
                    state["adguard_detail"] = "UNAVAIL"
                else:
                    state["adguard_online"] = True
                    state["adguard_protection"] = protection_state == "on"

            blocked_entity = getattr(cfg, "ADGUARD_BLOCKED_RATIO_ENTITY", "")
            blocked, blocked_detail = _ha_entity(cfg, blocked_entity)
            if blocked is not None:
                try:
                    state["adguard_blocked_ratio"] = float(blocked.get("state"))
                except (TypeError, ValueError):
                    pass
            elif not state["adguard_detail"]:
                state["adguard_detail"] = blocked_detail
        except Exception as error:
            state["adguard_detail"] = "API"
            logger.warning("MEDIUM AdGuard entity read failed: %s", error)

    # piVCCU service state + notifications. Version/IP are refreshed in slow loop.
    state["pivccu_online"] = os.system("systemctl is-active --quiet pivccu.service") == 0
    if state["pivccu_online"]:
        try:
            ip = state.get("pivccu_ip") or _read_pivccu_ip(cfg)
            state["pivccu_messages"] = _read_pivccu_notifications(cfg, ip)
        except Exception as error:
            state["pivccu_messages"] = None
            logger.warning("MEDIUM piVCCU notification read failed: %s", error)
    else:
        state["pivccu_messages"] = None

    if getattr(cfg, "LOG_MEDIUM_VALUES", True):
        logger.info(
            "MEDIUM services HA=%s v=%s AdGuard=%s protection=%s blocked=%s piVCCU=%s messages=%s",
            "online" if state.get("ha_online") else "offline",
            state.get("ha_version") or "-",
            "online" if state.get("adguard_online") else "offline",
            state.get("adguard_protection"),
            state.get("adguard_blocked_ratio"),
            "online" if state.get("pivccu_online") else "offline",
            state.get("pivccu_messages"),
        )


def collect_slow(state, cfg, logger):
    """Refresh mostly static service metadata every ten minutes."""
    state["pivccu_ip"] = _read_pivccu_ip(cfg)
    state["pivccu_version"] = _read_pivccu_version()

    if getattr(cfg, "LOG_SLOW_VALUES", True):
        logger.info(
            "SLOW services piVCCU_ip=%s piVCCU_version=%s",
            state.get("pivccu_ip") or "-",
            state.get("pivccu_version") or "-",
        )


def card_home_assistant(state):
    online = bool(state.get("ha_online"))
    return {
        "title": "HOME ASSISTANT",
        "value": "ONLINE" if online else "OFFLINE",
        "detail": f"V {state.get('ha_version', '?')}" if online else "",
        "status": "ok" if online else "error",
    }


def card_adguard(state):
    online = bool(state.get("adguard_online"))
    if not online:
        detail = state.get("adguard_detail") or ""
    elif state.get("adguard_protection") is False:
        detail = "PROTECTION OFF"
    elif state.get("adguard_blocked_ratio") is not None:
        detail = f"BLOCK {state['adguard_blocked_ratio']:.1f}%"
    else:
        detail = ""
    return {
        "title": "ADGUARD",
        "value": "ONLINE" if online else "OFFLINE",
        "detail": detail,
        "status": "ok" if online else "error",
    }


def card_pivccu(state):
    online = bool(state.get("pivccu_online"))
    messages = state.get("pivccu_messages")
    if online:
        value = "ERR ?" if messages is None else f"ERR {messages}"
        detail = f"V {state.get('pivccu_version') or '?'}"
        status = "error" if messages not in (0, None) else "ok"
    else:
        value = "OFFLINE"
        detail = ""
        status = "error"
    return {
        "title": "piVCCU",
        "value": value,
        "detail": detail,
        "status": status,
    }


CARD_BUILDERS = {
    "home_assistant": card_home_assistant,
    "ha": card_home_assistant,
    "adguard": card_adguard,
    "pivccu": card_pivccu,
}
