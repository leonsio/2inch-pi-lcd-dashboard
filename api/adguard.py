"""Optional AdGuard summary using Home Assistant entities."""

from .home_assistant import get_entity as _ha_entity


def collect_medium(state, cfg, logger):
    state["adguard_online"] = False
    state["adguard_protection"] = None
    state["adguard_blocked_ratio"] = None
    state["adguard_detail"] = ""

    if state.get("ha_online") and not state.get("ha_auth_error"):
        try:
            protection_entity = cfg.adguard["protection_entity"]
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

            blocked_entity = cfg.adguard["blocked_ratio_entity"]
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


CARD_BUILDERS = {"adguard": card_adguard}
