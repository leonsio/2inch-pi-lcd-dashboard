"""Declarative catalog and lazy registration, without client imports.

New integrations declare their import path, option defaults and card names here.
"""

from importlib import import_module
from types import SimpleNamespace


MODULES = {
    "system": ("dashboard_modules.system", {},
               "cpu ram hdd uptime load cpu_ring ram_ring disk_ring hdd_ring temp_ring"),
    "network": ("dashboard_modules.network", {}, "ip hostname network"),
    "power": ("dashboard_modules.power", {}, "shutdown reboot"),
    "pihole": ("api.pihole", {"url": "", "password": "", "verify_ssl": True}, "pihole pi_hole"),
    "pivccu": ("api.pivccu", {"ip": "", "token": ""}, "pivccu openccu"),
    "home_assistant": ("api.home_assistant", {
        "url": "", "token": "", "verify_ssl": True, "entities": {},
    }, "home_assistant ha"),
    "adguard": ("api.adguard", {
        "protection_entity": "switch.adguard_home_protection",
        "blocked_ratio_entity": "sensor.adguard_home_dns_queries_blocked_ratio",
    }, "adguard"),
    "proxmox": ("api.proxmox", {
        "url": "", "api_token_id": "", "api_token_secret": "",
        "verify_ssl": False, "include_lxc": False,
    }, "proxmox"),
}


def available_cards(data):
    cards = set()
    for name, (_, _, names) in MODULES.items():
        if name in data:
            cards.update(names.split())
    cards.update("home_assistant." + name for name in
                 data.get("home_assistant", {}).get("entities", {}))
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
