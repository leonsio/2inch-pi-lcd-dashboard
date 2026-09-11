"""Proxmox VE API collector and dashboard card.

The module is intentionally independent from the generic service collector.
It uses the cluster-wide resources endpoint, so no node name is required and
it also works when the configured Proxmox endpoint later becomes a cluster.
"""

import requests


STATE_KEYS = (
    "proxmox_online",
    "proxmox_auth_error",
    "proxmox_running_vms",
    "proxmox_total_vms",
    "proxmox_version",
)


def _configured(cfg):
    return bool(
        str(getattr(cfg, "PROXMOX_URL", "")).strip()
        and str(getattr(cfg, "PROXMOX_API_TOKEN_ID", "")).strip()
        and str(getattr(cfg, "PROXMOX_API_TOKEN_SECRET", "")).strip()
    )


def _headers(cfg):
    token_id = str(getattr(cfg, "PROXMOX_API_TOKEN_ID", "")).strip()
    token_secret = str(getattr(cfg, "PROXMOX_API_TOKEN_SECRET", "")).strip()
    return {
        "Authorization": f"PVEAPIToken={token_id}={token_secret}",
        "Accept": "application/json",
    }


def _get(cfg, path, params=None):
    base = str(getattr(cfg, "PROXMOX_URL", "")).strip().rstrip("/")
    timeout = float(getattr(cfg, "REQUEST_TIMEOUT", 5))
    verify_ssl = bool(getattr(cfg, "PROXMOX_VERIFY_SSL", False))
    return requests.get(
        f"{base}/api2/json{path}",
        headers=_headers(cfg),
        params=params,
        timeout=timeout,
        verify=verify_ssl,
    )


def _guest_is_counted(resource, include_lxc):
    resource_type = str(resource.get("type", "")).lower()
    if resource_type == "qemu":
        return True
    return include_lxc and resource_type == "lxc"


def collect_medium(state, cfg, logger):
    """Refresh reachability and running/total VM counts."""
    if not _configured(cfg):
        state["proxmox_online"] = False
        state["proxmox_auth_error"] = False
        state["proxmox_running_vms"] = 0
        state["proxmox_total_vms"] = 0
        state["proxmox_configured"] = False
        return

    state["proxmox_configured"] = True
    include_lxc = bool(getattr(cfg, "PROXMOX_INCLUDE_LXC", False))

    try:
        response = _get(cfg, "/cluster/resources", params={"type": "vm"})
        if response.status_code in (401, 403):
            state["proxmox_online"] = True
            state["proxmox_auth_error"] = True
            state["proxmox_running_vms"] = 0
            state["proxmox_total_vms"] = 0
            logger.warning("MEDIUM Proxmox authentication failed: HTTP %s", response.status_code)
            return

        response.raise_for_status()
        payload = response.json()
        resources = payload.get("data") or []
        guests = [
            resource
            for resource in resources
            if _guest_is_counted(resource, include_lxc)
            and not bool(resource.get("template"))
        ]

        running = sum(
            1
            for guest in guests
            if str(guest.get("status", "")).lower() == "running"
        )

        state["proxmox_online"] = True
        state["proxmox_auth_error"] = False
        state["proxmox_running_vms"] = running
        state["proxmox_total_vms"] = len(guests)

        if getattr(cfg, "LOG_MEDIUM_VALUES", True):
            guest_label = "VM+LXC" if include_lxc else "VM"
            logger.info(
                "MEDIUM Proxmox online %s=%d/%d running",
                guest_label,
                running,
                len(guests),
            )
    except Exception as error:
        state["proxmox_online"] = False
        state["proxmox_auth_error"] = False
        logger.warning("MEDIUM Proxmox unavailable: %s", error)


def collect_slow(state, cfg, logger):
    """Refresh the mostly static Proxmox VE version."""
    if not _configured(cfg):
        state["proxmox_version"] = ""
        return

    try:
        response = _get(cfg, "/version")
        if response.status_code in (401, 403):
            state["proxmox_version"] = "AUTH"
            return
        response.raise_for_status()
        data = response.json().get("data") or {}
        state["proxmox_version"] = str(data.get("version") or "?")

        if getattr(cfg, "LOG_SLOW_VALUES", True):
            logger.info("SLOW Proxmox version=%s", state["proxmox_version"])
    except Exception as error:
        state.setdefault("proxmox_version", "?")
        logger.warning("SLOW Proxmox metadata read failed: %s", error)


def card_proxmox(state):
    """Classic rectangular Proxmox card."""
    configured = bool(state.get("proxmox_configured", True))
    online = bool(state.get("proxmox_online"))
    auth_error = bool(state.get("proxmox_auth_error"))

    if not configured:
        return {
            "title": "PROXMOX",
            "value": "CONFIG",
            "detail": "NOT SET",
            "status": "warn",
        }

    if auth_error:
        return {
            "title": "PROXMOX",
            "value": "ONLINE",
            "detail": "AUTH",
            "status": "warn",
        }

    if not online:
        return {
            "title": "PROXMOX",
            "value": "OFFLINE",
            "detail": "",
            "status": "error",
        }

    running = int(state.get("proxmox_running_vms", 0) or 0)
    total = int(state.get("proxmox_total_vms", 0) or 0)
    version = str(state.get("proxmox_version") or "?")

    return {
        "title": "PROXMOX",
        "value": f"{running}/{total} VMs",
        "detail": f"ONLINE V {version}",
        "status": "ok",
    }


CARD_BUILDERS = {
    "proxmox": card_proxmox,
}
