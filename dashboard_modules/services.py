"""Service/API collectors for TFT2."""

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


def _openccu_ip(cfg):
    """Return the OpenCCU address configured by the user.

    OPENCCU_IP is the preferred setting. PIVCCU_FALLBACK_IP is accepted as a
    compatibility alias for existing config.py files. No local discovery is
    performed.
    """
    configured = getattr(cfg, "OPENCCU_IP", None)
    if configured is None:
        configured = getattr(cfg, "PIVCCU_FALLBACK_IP", "")
    return str(configured or "").strip()


def _read_openccu_notifications(cfg, ip):
    token = getattr(cfg, "XML_RPC_TOKEN", "")
    if not ip:
        raise ValueError("OpenCCU IP is not configured")
    if not token:
        raise ValueError("XML_RPC_TOKEN is not configured")

    url = f"http://{ip}/addons/xmlapi/systemNotification.cgi?sid={token}"
    response = requests.get(url, timeout=getattr(cfg, "REQUEST_TIMEOUT", 5))
    response.raise_for_status()
    tree = etree.fromstring(response.content)
    return len(tree.xpath(".//notification"))


def collect_medium(state, cfg, logger):
    """Poll changing service state once per minute."""
    try:
        response = _ha_get(cfg, "/api/")
        if response.status_code in (401, 403):
            state["ha_online"] = True
            state["ha_auth_error"] = True
        else:
            response.raise_for_status()
            state["ha_online"] = True
            state["ha_auth_error"] = False
    except Exception as error:
        state["ha_online"] = False
        state["ha_auth_error"] = False
        logger.warning("MEDIUM Home Assistant unavailable: %s", error)

    state["adguard_online"] = False
    state["adguard_protection"] = None
    state["adguard_blocked_ratio"] = None
    state["adguard_detail"] = ""

    if state.get("ha_online") and not state.get("ha_auth_error"):
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
    elif state.get("ha_auth_error"):
        state["adguard_detail"] = "AUTH"

    state["openccu_ip"] = _openccu_ip(cfg)
    state["openccu_online"] = False
    state["openccu_messages"] = None

    try:
        state["openccu_messages"] = _read_openccu_notifications(
            cfg,
            state["openccu_ip"],
        )
        state["openccu_online"] = True
    except Exception as error:
        logger.warning("MEDIUM OpenCCU XML API unavailable: %s", error)

    if getattr(cfg, "LOG_MEDIUM_VALUES", True):
        logger.info(
            "MEDIUM services HA=%s AdGuard=%s protection=%s blocked=%s OpenCCU=%s messages=%s",
            "online" if state.get("ha_online") else "offline",
            "online" if state.get("adguard_online") else "offline",
            state.get("adguard_protection"),
            state.get("adguard_blocked_ratio"),
            "online" if state.get("openccu_online") else "offline",
            state.get("openccu_messages"),
        )


def collect_slow(state, cfg, logger):
    """Refresh mostly static service metadata every ten minutes."""
    state["openccu_ip"] = _openccu_ip(cfg)

    try:
        response = _ha_get(cfg, "/api/config")
        if response.status_code in (401, 403):
            state["ha_version"] = "AUTH"
        else:
            response.raise_for_status()
            data = response.json()
            state["ha_version"] = str(data.get("version") or "?")
    except Exception as error:
        if "ha_version" not in state:
            state["ha_version"] = "?"
        logger.warning("SLOW Home Assistant metadata read failed: %s", error)

    if getattr(cfg, "LOG_SLOW_VALUES", True):
        logger.info(
            "SLOW services HA_version=%s OpenCCU_ip=%s",
            state.get("ha_version") or "-",
            state.get("openccu_ip") or "-",
        )


def card_home_assistant(state):
    online = bool(state.get("ha_online"))
    if state.get("ha_auth_error"):
        detail = "AUTH"
    elif online:
        detail = f"V {state.get('ha_version', '?')}"
    else:
        detail = ""
    return {
        "title": "HOME ASST",
        "value": "ONLINE" if online else "OFFLINE",
        "detail": detail,
        "status": "warn" if state.get("ha_auth_error") else ("ok" if online else "error"),
    }


def card_adguard(state):
    online = bool(state.get("adguard_online"))
    if not online:
        detail = state.get("adguard_detail") or ""
    elif state.get("adguard_protection") is False:
        detail = "PROT OFF"
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


CARD_BUILDERS = {
    "home_assistant": card_home_assistant,
    "ha": card_home_assistant,
    "adguard": card_adguard,
    "openccu": card_openccu,
    # Compatibility alias for existing config.py layouts.
    "pivccu": card_openccu,
}
