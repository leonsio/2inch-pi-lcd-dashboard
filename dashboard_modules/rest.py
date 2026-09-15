"""Generic read-only REST/JSON dashboard integration.

Each configured endpoint creates one card named ``rest.<alias>``. Endpoints may
choose a polling interval of 1, 60 or 600 seconds, mapped to the dashboard's
fast, medium and slow collector groups. Identical GET requests in one collector
cycle are de-duplicated so several cards can read different JSON paths from one
response without additional HTTP requests.
"""

import json
import warnings

import requests
from urllib3.exceptions import InsecureRequestWarning


_INTERVAL_GROUPS = {1: "fast", 60: "medium", 600: "slow"}
_MISSING = object()


def _request_key(item):
    """Hashable identity used to share equal requests within one poll cycle."""
    headers = tuple(sorted((str(k), str(v)) for k, v in item.get("headers", {}).items()))
    return (
        str(item["url"]),
        headers,
        bool(item.get("verify_ssl", True)),
    )


def _get_json(item, timeout):
    verify_ssl = bool(item.get("verify_ssl", True))
    with warnings.catch_warnings():
        if not verify_ssl:
            warnings.simplefilter("ignore", InsecureRequestWarning)
        response = requests.get(
            str(item["url"]),
            headers=dict(item.get("headers", {})),
            timeout=timeout,
            verify=verify_ssl,
        )
    if response.status_code in (401, 403):
        return None, "AUTH"
    if response.status_code >= 400:
        return None, f"HTTP {response.status_code}"
    try:
        return response.json(), ""
    except (ValueError, json.JSONDecodeError):
        return None, "JSON"


def _tokenize_path(path):
    """Parse dotted paths with numeric list indexes, e.g. data.items.0.value."""
    if path in (None, ""):
        return []
    return str(path).split(".")


def _extract(payload, path):
    value = payload
    for token in _tokenize_path(path):
        if isinstance(value, dict):
            if token not in value:
                return _MISSING
            value = value[token]
            continue
        if isinstance(value, list):
            try:
                index = int(token)
            except (TypeError, ValueError):
                return _MISSING
            if index < 0 or index >= len(value):
                return _MISSING
            value = value[index]
            continue
        return _MISSING
    return value


def _poll_interval(state, cfg, logger, interval):
    endpoints = cfg.rest.get("endpoints", {})
    selected = {
        alias: item
        for alias, item in endpoints.items()
        if int(item.get("interval", 60)) == interval
    }
    if not selected:
        return

    timeout = float(getattr(cfg, "REQUEST_TIMEOUT", 5))
    cache = {}
    results = dict(state.get("rest_results") or {})

    for alias, item in selected.items():
        key = _request_key(item)
        if key not in cache:
            try:
                cache[key] = _get_json(item, timeout)
            except Exception:
                cache[key] = (None, "OFFLINE")

        payload, error = cache[key]
        if error:
            results[alias] = {"error": error, "value": None, "detail": None}
            continue

        value = _extract(payload, item.get("path", ""))
        if value is _MISSING:
            results[alias] = {"error": "PATH", "value": None, "detail": None}
            continue

        detail = None
        detail_path = item.get("detail_path", "")
        if detail_path:
            detail = _extract(payload, detail_path)
            if detail is _MISSING:
                detail = None

        results[alias] = {"error": "", "value": value, "detail": detail}

    state["rest_results"] = results
    if getattr(cfg, "LOG_MEDIUM_VALUES", True):
        ok = sum(1 for alias in selected if not results.get(alias, {}).get("error"))
        logger.info("REST interval=%ss cards=%d/%d ok", interval, ok, len(selected))


def collect_fast(state, cfg, logger):
    _poll_interval(state, cfg, logger, 1)


def collect_medium(state, cfg, logger):
    _poll_interval(state, cfg, logger, 60)


def collect_slow(state, cfg, logger):
    _poll_interval(state, cfg, logger, 600)


def _format_value(value, precision):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if precision is None:
            return str(value)
        return f"{float(value):.{int(precision)}f}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    return str(value)


def _card_for(alias, item, state):
    title = str(item.get("title") or alias.replace("_", " ").upper())
    result = (state.get("rest_results") or {}).get(alias)
    if result is None:
        return {"title": title, "value": "WAIT", "detail": "", "status": "normal"}

    error = str(result.get("error") or "")
    if error:
        status = "warn" if error in ("PATH", "JSON") or error.startswith("HTTP 4") else "error"
        if error == "AUTH":
            status = "warn"
        return {"title": title, "value": error, "detail": "", "status": status}

    value = _format_value(result.get("value"), item.get("precision"))
    unit = str(item.get("unit") or "")
    if unit:
        value = f"{value} {unit}"

    detail = item.get("detail", "")
    if result.get("detail") is not None:
        detail = _format_value(result.get("detail"), None)

    return {
        "title": title,
        "value": value,
        "detail": str(detail or ""),
        "status": "ok",
    }


def build_cards(cfg):
    cards = {}
    for alias, item in cfg.rest.get("endpoints", {}).items():
        cards[f"rest.{alias}"] = (
            lambda state, alias=alias, item=item: _card_for(alias, item, state)
        )
    return cards


CARD_BUILDERS = {}
