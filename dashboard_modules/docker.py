"""Docker Engine status collector using the local Unix socket.

No docker Python package is required. The module talks directly to the Docker
Engine HTTP API exposed by the configured Unix socket.
"""

import http.client
import json
import socket


class _UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path, timeout):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


def _get_json(cfg, path):
    connection = _UnixHTTPConnection(
        str(cfg.docker["socket"]),
        float(getattr(cfg, "REQUEST_TIMEOUT", 5)),
    )
    try:
        connection.request("GET", path, headers={"Accept": "application/json"})
        response = connection.getresponse()
        body = response.read()
        if response.status >= 400:
            raise RuntimeError(f"Docker API HTTP {response.status}")
        return json.loads(body.decode("utf-8"))
    finally:
        connection.close()


def _container_names(item):
    return [str(name).lstrip("/") for name in item.get("Names", []) if name]


def _container_snapshot(item):
    names = _container_names(item)
    return {
        "id": str(item.get("Id") or ""),
        "name": names[0] if names else str(item.get("Id") or "")[:12],
        "names": names,
        "image": str(item.get("Image") or ""),
        "state": str(item.get("State") or "unknown").lower(),
        "status": str(item.get("Status") or ""),
    }


def collect_medium(state, cfg, logger):
    """Refresh daemon availability and container states."""
    try:
        payload = _get_json(cfg, "/containers/json?all=1")
        if not isinstance(payload, list):
            raise ValueError("Docker containers response is not a list")

        containers = {}
        running = 0
        for item in payload:
            snapshot = _container_snapshot(item)
            if snapshot["state"] == "running":
                running += 1
            keys = set(snapshot["names"])
            if snapshot["id"]:
                keys.add(snapshot["id"])
                keys.add(snapshot["id"][:12])
            for key in keys:
                containers[key] = snapshot

        state["docker_online"] = True
        state["docker_running"] = running
        state["docker_total"] = len(payload)
        state["docker_containers"] = containers

        if getattr(cfg, "LOG_MEDIUM_VALUES", True):
            logger.info("MEDIUM Docker online containers=%d/%d running", running, len(payload))
    except Exception as error:
        state["docker_online"] = False
        state["docker_running"] = 0
        state["docker_total"] = 0
        state["docker_containers"] = {}
        logger.warning("MEDIUM Docker unavailable: %s", error)


def collect_slow(state, cfg, logger):
    """Refresh Docker Engine version metadata."""
    try:
        payload = _get_json(cfg, "/version")
        state["docker_version"] = str(payload.get("Version") or "?")
        if getattr(cfg, "LOG_SLOW_VALUES", True):
            logger.info("SLOW Docker version=%s", state["docker_version"])
    except Exception as error:
        state.setdefault("docker_version", "?")
        logger.warning("SLOW Docker metadata read failed: %s", error)


def card_docker(state):
    if not state.get("docker_online"):
        return {
            "title": "DOCKER",
            "value": "OFFLINE",
            "detail": "",
            "status": "error",
        }
    running = int(state.get("docker_running", 0) or 0)
    total = int(state.get("docker_total", 0) or 0)
    return {
        "title": "DOCKER",
        "value": f"{running}/{total}",
        "detail": "CONTAINERS RUNNING",
        "status": "ok" if running == total else "warn",
    }


def card_docker_ring(state):
    online = bool(state.get("docker_online"))
    running = int(state.get("docker_running", 0) or 0)
    total = int(state.get("docker_total", 0) or 0)
    ratio = running / total if total > 0 else 0.0
    return {
        "style": "ring",
        "title": "DOCKER",
        "value": "OFF" if not online else f"{running}/{total}",
        "detail": "",
        "ratio": ratio,
        # Full/all-running should be green; missing/stopped containers move toward red.
        "color_ratio": None if not online else 1.0 - ratio,
        "status": "error" if not online else ("ok" if running == total else "warn"),
    }


def _container_options(alias, raw):
    if isinstance(raw, str):
        return raw, alias.replace("_", " ").upper()
    return str(raw["name"]), str(raw.get("title") or alias.replace("_", " ").upper())


def _container_card(state, container_name, title):
    if not state.get("docker_online"):
        return {"title": title, "value": "OFFLINE", "detail": container_name, "status": "error"}

    container = (state.get("docker_containers") or {}).get(container_name)
    if not container:
        return {"title": title, "value": "NOT FOUND", "detail": container_name, "status": "warn"}

    raw_state = str(container.get("state") or "unknown").lower()
    value = raw_state.upper()
    if raw_state == "running":
        status = "ok"
    elif raw_state in ("restarting", "paused", "created"):
        status = "warn"
    else:
        status = "error"

    detail = container.get("name") or container_name
    if container.get("image"):
        detail = f"{detail} · {container['image']}"
    return {
        "title": title,
        "value": value,
        "detail": detail,
        "status": status,
    }


def build_cards(cfg):
    cards = {}
    for alias, raw in cfg.docker.get("containers", {}).items():
        container_name, title = _container_options(alias, raw)
        cards[f"docker.{alias}"] = (
            lambda state, container_name=container_name, title=title:
            _container_card(state, container_name, title)
        )
    return cards


CARD_BUILDERS = {
    "docker": card_docker,
    "docker_ring": card_docker_ring,
}
