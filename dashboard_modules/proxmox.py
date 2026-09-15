"""Proxmox VE API collector and dashboard cards.

The module uses the cluster-wide resources endpoint, so no node name is required.
Besides the overall Proxmox card, configured VM/LXC IDs can be exposed as
individual cards such as ``proxmox.homeassistant``.
"""

import warnings

import requests
from urllib3.exceptions import InsecureRequestWarning


STATE_KEYS = (
    "proxmox_online",
    "proxmox_auth_error",
    "proxmox_running_vms",
    "proxmox_total_vms",
    "proxmox_guests",
    "proxmox_version",
)


def _configured(cfg):
    return bool(
        str(cfg.proxmox["url"]).strip()
        and str(cfg.proxmox["api_token_id"]).strip()
        and str(cfg.proxmox["api_token_secret"]).strip()
    )


def _headers(cfg):
    token_id = str(cfg.proxmox["api_token_id"]).strip()
    token_secret = str(cfg.proxmox["api_token_secret"]).strip()
    return {
        "Authorization": f"PVEAPIToken={token_id}={token_secret}",
        "Accept": "application/json",
    }


def _get(cfg, path, params=None):
    base = str(cfg.proxmox["url"]).strip().rstrip("/")
    timeout = float(getattr(cfg, "REQUEST_TIMEOUT", 5))
    verify_ssl = bool(cfg.proxmox["verify_ssl"])

    with warnings.catch_warnings():
        if not verify_ssl:
            warnings.simplefilter("ignore", InsecureRequestWarning)
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


def _guest_snapshot(resource):
    return {
        "vmid": int(resource.get("vmid", 0) or 0),
        "name": str(resource.get("name") or ""),
        "status": str(resource.get("status") or "unknown").lower(),
        "node": str(resource.get("node") or ""),
        "type": str(resource.get("type") or "qemu").lower(),
        "cpu": float(resource.get("cpu", 0) or 0),
        "mem": int(resource.get("mem", 0) or 0),
        "maxmem": int(resource.get("maxmem", 0) or 0),
    }


def collect_medium(state, cfg, logger):
    """Refresh reachability, guest counts and individual guest status."""
    if not _configured(cfg):
        state["proxmox_online"] = False
        state["proxmox_auth_error"] = False
        state["proxmox_running_vms"] = 0
        state["proxmox_total_vms"] = 0
        state["proxmox_guests"] = {}
        state["proxmox_configured"] = False
        return

    state["proxmox_configured"] = True
    include_lxc = bool(cfg.proxmox["include_lxc"])

    try:
        response = _get(cfg, "/cluster/resources", params={"type": "vm"})
        if response.status_code in (401, 403):
            state["proxmox_online"] = True
            state["proxmox_auth_error"] = True
            state["proxmox_running_vms"] = 0
            state["proxmox_total_vms"] = 0
            state["proxmox_guests"] = {}
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
        snapshots = {}
        for guest in guests:
            vmid = guest.get("vmid")
            if vmid is None:
                continue
            snapshots[str(vmid)] = _guest_snapshot(guest)

        state["proxmox_online"] = True
        state["proxmox_auth_error"] = False
        state["proxmox_running_vms"] = running
        state["proxmox_total_vms"] = len(guests)
        state["proxmox_guests"] = snapshots

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
        state["proxmox_guests"] = {}
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

    return {
        "title": "PROXMOX",
        "value": f"{running}/{total} VMs",
        "detail": "ONLINE",
        "status": "ok",
    }


def _vm_options(alias, raw):
    if isinstance(raw, int):
        return raw, alias.replace("_", " ").upper()
    return int(raw["vmid"]), str(raw.get("title") or alias.replace("_", " ").upper())


def _vm_card(state, vmid, title):
    if not bool(state.get("proxmox_configured", True)):
        return {"title": title, "value": "CONFIG", "detail": f"VM {vmid}", "status": "warn"}
    if state.get("proxmox_auth_error"):
        return {"title": title, "value": "AUTH", "detail": f"VM {vmid}", "status": "warn"}
    if not state.get("proxmox_online"):
        return {"title": title, "value": "OFFLINE", "detail": f"VM {vmid}", "status": "error"}

    guest = (state.get("proxmox_guests") or {}).get(str(vmid))
    if not guest:
        return {"title": title, "value": "NOT FOUND", "detail": f"VM {vmid}", "status": "warn"}

    status = str(guest.get("status") or "unknown").upper()
    guest_type = "LXC" if guest.get("type") == "lxc" else "VM"
    node = guest.get("node") or "?"
    return {
        "title": title,
        "value": status,
        "detail": f"{guest_type} {vmid} · {node}",
        "status": "ok" if status == "RUNNING" else "warn",
    }


def build_cards(cfg):
    cards = {}
    for alias, raw in cfg.proxmox.get("vms", {}).items():
        vmid, title = _vm_options(alias, raw)
        cards[f"proxmox.{alias}"] = (
            lambda state, vmid=vmid, title=title: _vm_card(state, vmid, title)
        )
    return cards


CARD_BUILDERS = {
    "proxmox": card_proxmox,
}
