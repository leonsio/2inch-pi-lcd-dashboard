"""Home Assistant status and configurable, read-only entity cards."""

from functools import partial
import math

import requests


def _get(cfg, path):
    options = cfg.home_assistant
    return requests.get(
        options["url"].rstrip("/") + path,
        headers={"Authorization": "Bearer " + options["token"],
                 "Content-Type": "application/json"},
        timeout=cfg.REQUEST_TIMEOUT,
        verify=options["verify_ssl"],
    )


def get_entity(cfg, entity_id):
    response = _get(cfg, "/api/states/" + entity_id)
    if response.status_code == 404:
        return None, "ENTITY"
    if response.status_code in (401, 403):
        return None, "AUTH"
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or "state" not in data or not isinstance(data.get("attributes", {}), dict):
        raise ValueError("Invalid Home Assistant entity response")
    return data, ""


def collect_medium(state, cfg, logger):
    # Replace the snapshot on every poll, so failed reads never show stale values.
    state["ha_entities"] = {}
    state["ha_online"] = False
    state["ha_auth_error"] = False
    try:
        response = _get(cfg, "/api/")
        if response.status_code in (401, 403):
            state["ha_online"] = True
            state["ha_auth_error"] = True
        else:
            response.raise_for_status()
            state["ha_online"] = True
    except Exception:
        logger.warning("MEDIUM Home Assistant API unavailable")

    cache = {}
    for options in cfg.home_assistant["entities"].values():
        entity_id = options["entity_id"]
        if entity_id in cache:
            continue
        if state["ha_auth_error"]:
            cache[entity_id] = (None, "AUTH")
        elif not state["ha_online"]:
            cache[entity_id] = (None, "OFFLINE")
        else:
            try:
                cache[entity_id] = get_entity(cfg, entity_id)
            except Exception:
                cache[entity_id] = (None, "API")
                logger.warning("MEDIUM Home Assistant entity read failed: %s", entity_id)
    state["ha_entities"] = cache


def collect_slow(state, cfg, logger):
    state["ha_version"] = "?"
    try:
        response = _get(cfg, "/api/config")
        if response.status_code in (401, 403):
            state["ha_version"] = "AUTH"
        else:
            response.raise_for_status()
            state["ha_version"] = str(response.json().get("version") or "?")
    except Exception:
        logger.warning("SLOW Home Assistant metadata unavailable")


def card_home_assistant(state):
    online = bool(state.get("ha_online"))
    auth = bool(state.get("ha_auth_error"))
    return {"title": "HOME ASST", "value": "ONLINE" if online else "OFFLINE",
            "detail": "AUTH" if auth else (f"V {state.get('ha_version', '?')}" if online else ""),
            "status": "warn" if auth else ("ok" if online else "error")}


def card_entity(state, options):
    entity_id = options["entity_id"]
    data, error = state.get("ha_entities", {}).get(entity_id, (None, "WAIT"))
    attributes = data.get("attributes", {}) if data else {}
    title = options.get("title") or attributes.get("friendly_name") or entity_id
    card = {"title": str(title), "value": error, "detail": "", "status": "warn"}
    if data is None:
        card["status"] = "warn" if error == "WAIT" else "error"
        return card
    raw = str(data["state"])
    if raw in ("unavailable", "unknown"):
        card["value"] = raw.upper()
        return card
    value = attributes.get(options["attribute"]) if "attribute" in options else raw
    if value is None:
        card["value"] = "ATTRIBUTE"
        return card
    text = str(value)
    if "precision" in options:
        try:
            number = float(value)
            if math.isfinite(number):
                text = f"{number:.{options['precision']}f}"
        except (ValueError, TypeError):
            pass
    text = options.get("state_labels", {}).get(str(value), text)
    unit = options.get("unit", "" if "attribute" in options else attributes.get("unit_of_measurement", ""))
    card.update(value=text + (" " + str(unit) if unit else ""),
                status="normal", detail=options.get("detail", ""))
    return card


def build_cards(cfg):
    return {"home_assistant." + name: partial(card_entity, options=options)
            for name, options in cfg.home_assistant["entities"].items()}


CARD_BUILDERS = {"home_assistant": card_home_assistant, "ha": card_home_assistant}
