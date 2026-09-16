"""systemd service summary and configurable unit status cards."""

import shutil
import subprocess


_SERVICE_SUFFIX = ".service"


def _normalize_unit(value):
    name = str(value or "").strip()
    if name and "." not in name:
        name += _SERVICE_SUFFIX
    return name


def _unit_options(alias, raw):
    if isinstance(raw, str):
        return _normalize_unit(raw), alias.replace("_", " ").upper()
    if isinstance(raw, dict):
        name = _normalize_unit(raw.get("name"))
        title = str(raw.get("title") or alias.replace("_", " ").upper())
        return name, title
    return "", alias.replace("_", " ").upper()


def _systemctl(args, timeout):
    executable = shutil.which("systemctl")
    if not executable:
        return None
    try:
        return subprocess.run(
            [executable, *args],
            capture_output=True,
            text=True,
            timeout=max(1.0, float(timeout)),
            check=False,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _service_counts(output):
    total = active = running = failed = 0
    for raw_line in str(output or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split(None, 5)
        if fields and fields[0] == "●":
            fields = fields[1:]
        if len(fields) < 4:
            continue
        unit, _load_state, active_state, sub_state = fields[:4]
        if not unit.endswith(_SERVICE_SUFFIX):
            continue
        total += 1
        if active_state == "active":
            active += 1
        if sub_state == "running":
            running += 1
        if active_state == "failed" or sub_state == "failed":
            failed += 1
    return {
        "total": total,
        "active": active,
        "running": running,
        "failed": failed,
    }


def _parse_show_blocks(output):
    snapshots = {}
    current = {}

    def commit():
        unit_id = str(current.get("Id") or "").strip()
        if unit_id:
            snapshots[unit_id] = {
                "name": unit_id,
                "load": str(current.get("LoadState") or "unknown"),
                "active": str(current.get("ActiveState") or "unknown"),
                "sub": str(current.get("SubState") or "unknown"),
                "unit_file": str(current.get("UnitFileState") or ""),
            }

    for raw_line in str(output or "").splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                commit()
                current = {}
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        current[key] = value
    if current:
        commit()
    return snapshots


def _configured_units(cfg):
    result = []
    for alias, raw in cfg.services.get("units", {}).items():
        name, title = _unit_options(alias, raw)
        result.append((alias, name, title))
    return result


def collect_medium(state, cfg, logger):
    """Refresh systemd service counts and all configured unit states."""
    timeout = float(getattr(cfg, "REQUEST_TIMEOUT", 5))

    listing = _systemctl(
        [
            "list-units",
            "--type=service",
            "--all",
            "--no-legend",
            "--no-pager",
            "--plain",
        ],
        timeout,
    )

    summary_ok = bool(listing is not None and (listing.returncode == 0 or listing.stdout.strip()))
    counts = _service_counts(listing.stdout if summary_ok else "")
    state["services_available"] = summary_ok
    state["services_total"] = counts["total"]
    state["services_active"] = counts["active"]
    state["services_running"] = counts["running"]
    state["services_failed"] = counts["failed"]
    state["services_error"] = "" if summary_ok else "SYSTEMD"

    configured = _configured_units(cfg)
    names = []
    for _alias, name, _title in configured:
        if name and name not in names:
            names.append(name)

    snapshots = {}
    if names:
        shown = _systemctl(
            [
                "show",
                *names,
                "--property=Id",
                "--property=LoadState",
                "--property=ActiveState",
                "--property=SubState",
                "--property=UnitFileState",
                "--no-pager",
            ],
            timeout,
        )
        if shown is not None and shown.stdout.strip():
            snapshots = _parse_show_blocks(shown.stdout)

    unit_states = {}
    for alias, name, title in configured:
        if not name:
            unit_states[alias] = {
                "name": "", "title": title, "error": "CONFIG",
                "load": "unknown", "active": "unknown", "sub": "unknown", "unit_file": "",
            }
            continue
        snapshot = snapshots.get(name)
        if snapshot is None:
            unit_states[alias] = {
                "name": name, "title": title, "error": "SYSTEMD",
                "load": "unknown", "active": "unknown", "sub": "unknown", "unit_file": "",
            }
            continue
        unit_states[alias] = {**snapshot, "title": title, "error": ""}

    state["services_units"] = unit_states

    if getattr(cfg, "LOG_MEDIUM_VALUES", True):
        logger.info(
            "MEDIUM services running=%d active=%d failed=%d total=%d monitored=%d",
            counts["running"],
            counts["active"],
            counts["failed"],
            counts["total"],
            len(configured),
        )


def _summary_unavailable(title):
    return {"title": title, "value": "N/A", "detail": "SYSTEMD", "status": "error"}


def card_services(state):
    if not state.get("services_available"):
        return _summary_unavailable("SERVICES")
    running = int(state.get("services_running", 0) or 0)
    failed = int(state.get("services_failed", 0) or 0)
    active = int(state.get("services_active", 0) or 0)
    return {
        "title": "SERVICES",
        "value": f"{running} RUN",
        "detail": f"{failed} FAIL · {active} ACTIVE",
        "status": "error" if failed else "ok",
    }


def card_services_running(state):
    if not state.get("services_available"):
        return _summary_unavailable("RUNNING")
    running = int(state.get("services_running", 0) or 0)
    active = int(state.get("services_active", 0) or 0)
    total = int(state.get("services_total", 0) or 0)
    return {
        "title": "RUNNING",
        "value": str(running),
        "detail": f"{active} ACTIVE · {total} TOTAL",
        "status": "ok",
    }


def card_services_active(state):
    if not state.get("services_available"):
        return _summary_unavailable("ACTIVE")
    active = int(state.get("services_active", 0) or 0)
    total = int(state.get("services_total", 0) or 0)
    return {
        "title": "ACTIVE",
        "value": str(active),
        "detail": f"{total} TOTAL SERVICES",
        "status": "ok",
    }


def card_services_failed(state):
    if not state.get("services_available"):
        return _summary_unavailable("FAILED")
    failed = int(state.get("services_failed", 0) or 0)
    total = int(state.get("services_total", 0) or 0)
    return {
        "title": "FAILED",
        "value": str(failed),
        "detail": f"{total} TOTAL SERVICES",
        "status": "error" if failed else "ok",
    }


def card_services_total(state):
    if not state.get("services_available"):
        return _summary_unavailable("SERVICES")
    total = int(state.get("services_total", 0) or 0)
    return {
        "title": "SERVICES",
        "value": str(total),
        "detail": "LOADED UNITS",
        "status": "normal",
    }


def _unit_card(state, alias, name, title):
    snapshot = (state.get("services_units") or {}).get(alias)
    if snapshot is None:
        return {"title": title, "value": "WAIT", "detail": name, "status": "normal"}

    error = str(snapshot.get("error") or "")
    if error:
        return {"title": title, "value": error, "detail": name, "status": "error"}

    load_state = str(snapshot.get("load") or "unknown").lower()
    active_state = str(snapshot.get("active") or "unknown").lower()
    sub_state = str(snapshot.get("sub") or "unknown").lower()
    unit_file = str(snapshot.get("unit_file") or "")

    if load_state == "not-found":
        value, status = "NOT FOUND", "error"
    elif active_state == "failed" or sub_state == "failed":
        value, status = "FAILED", "error"
    elif active_state == "active":
        value = sub_state.upper() if sub_state not in ("", "unknown") else "ACTIVE"
        status = "ok"
    elif active_state in ("activating", "deactivating", "reloading"):
        value, status = active_state.upper(), "warn"
    elif active_state == "inactive":
        value, status = "INACTIVE", "warn"
    else:
        value, status = active_state.upper(), "warn"

    detail = name
    if unit_file:
        detail = f"{detail} · {unit_file.upper()}"
    return {"title": title, "value": value, "detail": detail, "status": status}


def build_cards(cfg):
    cards = {}
    for alias, raw in cfg.services.get("units", {}).items():
        name, title = _unit_options(alias, raw)
        cards[f"services.{alias}"] = (
            lambda state, alias=alias, name=name, title=title:
            _unit_card(state, alias, name, title)
        )
    return cards


CARD_BUILDERS = {
    "services": card_services,
    "services_running": card_services_running,
    "services_active": card_services_active,
    "services_failed": card_services_failed,
    "services_total": card_services_total,
}
