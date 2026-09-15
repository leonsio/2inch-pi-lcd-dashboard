"""Declarative catalog and lazy registration, without client imports.

Integrations declare their import path, option defaults and card names here.
The integration implementations themselves live in dashboard_modules/.
"""

from importlib import import_module
from types import SimpleNamespace


MODULES = {
    "system": ("dashboard_modules.system", {},
               "cpu ram swap hdd disk_free uptime load cpu_freq processes "
               "cpu_ring ram_ring swap_ring disk_ring hdd_ring freq_ring temp_ring"),
    "network": ("dashboard_modules.network", {
        "wan": {
            "enabled": False, "target": "1.1.1.1",
            "interval": "medium", "timeout": 1.0,
        },
        "external_ipv4": {
            "enabled": False, "url": "https://api.ipify.org",
            "interval": "slow", "verify_ssl": True,
        },
        "checks": {},
    }, "ip hostname network traffic network_rx network_tx network_link wifi wifi_ring"),
    "storage": ("dashboard_modules.storage", {
        "devices": {
            "root": {
                "mount": "/", "title": "ROOT", "device": "",
                "io_device": "", "smart": False,
            },
        },
        "smartctl": "smartctl",
    }, "storage"),
    "power": ("dashboard_modules.power", {}, "shutdown reboot"),
    "pihole": ("dashboard_modules.pihole", {"url": "", "password": "", "verify_ssl": True}, "pihole pi_hole"),
    "pivccu": ("dashboard_modules.pivccu", {"ip": "", "token": ""}, "pivccu openccu"),
    "home_assistant": ("dashboard_modules.home_assistant", {
        "url": "", "token": "", "verify_ssl": True, "entities": {},
    }, "home_assistant ha"),
    "adguard": ("dashboard_modules.adguard", {
        "protection_entity": "switch.adguard_home_protection",
        "blocked_ratio_entity": "sensor.adguard_home_dns_queries_blocked_ratio",
    }, "adguard"),
    "proxmox": ("dashboard_modules.proxmox", {
        "url": "", "api_token_id": "", "api_token_secret": "",
        "verify_ssl": False, "include_lxc": False, "vms": {},
    }, "proxmox"),
    "docker": ("dashboard_modules.docker", {
        "socket": "/var/run/docker.sock", "containers": {},
    }, "docker docker_ring"),
    "rest": ("dashboard_modules.rest", {
        "endpoints": {},
    }, ""),
}


def available_cards(data):
    cards = set()
    for name, (_, _, names) in MODULES.items():
        if name in data:
            cards.update(names.split())

    cards.update("home_assistant." + name for name in
                 data.get("home_assistant", {}).get("entities", {}))
    cards.update("proxmox." + name for name in
                 data.get("proxmox", {}).get("vms", {}))
    cards.update("docker." + name for name in
                 data.get("docker", {}).get("containers", {}))
    cards.update("rest." + name for name in
                 data.get("rest", {}).get("endpoints", {}))

    network = data.get("network", {}) or {}
    if bool((network.get("wan", {}) or {}).get("enabled", False)):
        cards.add("wan")
    if bool((network.get("external_ipv4", {}) or {}).get("enabled", False)):
        cards.update({"wan_ip", "external_ipv4"})
    cards.update("network." + name for name in (network.get("checks", {}) or {}))

    for name in data.get("storage", {}).get("devices", {}):
        cards.update({
            f"storage.{name}",
            f"storage.{name}_ring",
            f"storage.{name}_free",
            f"storage.{name}_io",
            f"storage.{name}_smart",
        })
    return cards


def load_modules(cfg):
    """Build fresh registries; absent blocks never import or poll their module."""
    collectors = {group: [] for group in ("fast", "medium", "slow")}
    cards, actions = {}, {}
    execute = None
    for name, (path, _, _) in MODULES.items():
        if not hasattr(cfg, name):
            continue
        module = import_module(path)
        for group in collectors:
            collector = getattr(module, "collect_" + group, None)
            if collector:
                collectors[group].append(collector)
        cards.update(getattr(module, "CARD_BUILDERS", {}))
        if hasattr(module, "build_cards"):
            cards.update(module.build_cards(cfg))
        actions.update(getattr(module, "POWER_ACTIONS", {}))
        if hasattr(module, "execute_power_action"):
            execute = module.execute_power_action
    return SimpleNamespace(collectors=collectors, cards=cards,
                           power_actions=actions, execute_power_action=execute)
