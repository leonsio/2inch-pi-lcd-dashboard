"""Pi-hole v6 REST API collector and dashboard card."""

import requests


_SESSION = {
    "base": "",
    "password": "",
    "sid": "",
}


def _base_url(cfg):
    return str(cfg.pihole["url"] or "").strip().rstrip("/")


def _verify_ssl(cfg):
    return bool(cfg.pihole["verify_ssl"])


def _authenticate(cfg, force=False):
    """Return a reusable Pi-hole v6 API session ID."""
    base = _base_url(cfg)
    password = str(cfg.pihole["password"] or "")

    if not base:
        raise ValueError("pihole.url is not configured")

    # Pi-hole without an API password does not require a SID.
    if not password:
        return ""

    if (
        not force
        and _SESSION["sid"]
        and _SESSION["base"] == base
        and _SESSION["password"] == password
    ):
        return _SESSION["sid"]

    response = requests.post(
        f"{base}/api/auth",
        json={"password": password},
        timeout=getattr(cfg, "REQUEST_TIMEOUT", 5),
        verify=_verify_ssl(cfg),
    )
    response.raise_for_status()

    session = response.json().get("session") or {}
    sid = str(session.get("sid") or "")
    if not session.get("valid") or not sid:
        raise RuntimeError("Pi-hole authentication did not return a valid SID")

    _SESSION.update({"base": base, "password": password, "sid": sid})
    return sid


def _get(cfg, path):
    base = _base_url(cfg)
    if not base:
        raise ValueError("pihole.url is not configured")

    sid = _authenticate(cfg)
    headers = {"X-FTL-SID": sid} if sid else {}
    response = requests.get(
        f"{base}{path}",
        headers=headers,
        timeout=getattr(cfg, "REQUEST_TIMEOUT", 5),
        verify=_verify_ssl(cfg),
    )

    # Cached Pi-hole sessions expire. Re-authenticate once on HTTP 401.
    if response.status_code == 401 and cfg.pihole["password"]:
        sid = _authenticate(cfg, force=True)
        response = requests.get(
            f"{base}{path}",
            headers={"X-FTL-SID": sid},
            timeout=getattr(cfg, "REQUEST_TIMEOUT", 5),
            verify=_verify_ssl(cfg),
        )

    return response


def _compact_count(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "?"

    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return str(number)


def collect_medium(state, cfg, logger):
    """Refresh Pi-hole status and query statistics once per medium interval."""
    state["pihole_online"] = False
    state["pihole_blocking"] = None
    state["pihole_queries"] = None
    state["pihole_blocked"] = None
    state["pihole_blocked_percent"] = None
    state["pihole_gravity_domains"] = None
    state["pihole_detail"] = ""

    if not _base_url(cfg):
        state["pihole_detail"] = "CONFIG"
        return

    try:
        blocking_response = _get(cfg, "/api/dns/blocking")
        if blocking_response.status_code in (401, 403):
            state["pihole_detail"] = "AUTH"
            return
        blocking_response.raise_for_status()
        state["pihole_blocking"] = bool(blocking_response.json().get("blocking"))

        summary_response = _get(cfg, "/api/stats/summary")
        if summary_response.status_code in (401, 403):
            state["pihole_detail"] = "AUTH"
            return
        summary_response.raise_for_status()

        summary = summary_response.json()
        queries = summary.get("queries") or {}
        gravity = summary.get("gravity") or {}

        state["pihole_queries"] = queries.get("total")
        state["pihole_blocked"] = queries.get("blocked")
        state["pihole_blocked_percent"] = queries.get("percent_blocked")
        state["pihole_gravity_domains"] = gravity.get("domains_being_blocked")
        state["pihole_online"] = True
    except requests.HTTPError as error:
        if getattr(error.response, "status_code", None) in (401, 403):
            state["pihole_detail"] = "AUTH"
        else:
            state["pihole_detail"] = "API"
        logger.warning("MEDIUM Pi-hole API unavailable: %s", error)
    except Exception as error:
        state["pihole_detail"] = "API"
        logger.warning("MEDIUM Pi-hole API unavailable: %s", error)

    if getattr(cfg, "LOG_MEDIUM_VALUES", True):
        logger.info(
            "MEDIUM Pi-hole=%s blocking=%s queries=%s blocked=%s percent=%s gravity=%s",
            "online" if state.get("pihole_online") else "offline",
            state.get("pihole_blocking"),
            state.get("pihole_queries"),
            state.get("pihole_blocked"),
            state.get("pihole_blocked_percent"),
            state.get("pihole_gravity_domains"),
        )


def card_pihole(state):
    online = bool(state.get("pihole_online"))
    blocking = state.get("pihole_blocking")
    percent = state.get("pihole_blocked_percent")

    if not online:
        value = "OFFLINE"
        detail = state.get("pihole_detail") or ""
        status = "error"
    elif blocking is False:
        value = "DISABLED"
        detail = "BLOCK OFF"
        status = "warn"
    else:
        try:
            value = f"{float(percent):.1f}%"
        except (TypeError, ValueError):
            value = "ONLINE"

        blocked = _compact_count(state.get("pihole_blocked"))
        total = _compact_count(state.get("pihole_queries"))
        detail = f"{blocked}/{total} BLOCK"
        status = "ok"

    return {
        "title": "PI-HOLE",
        "value": value,
        "detail": detail,
        "status": status,
    }


CARD_BUILDERS = {
    "pihole": card_pihole,
    "pi_hole": card_pihole,
}
