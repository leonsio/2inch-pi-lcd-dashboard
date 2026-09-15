"""Module activation and API contracts, with no GPIO or live HTTP requests."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests
import yaml

from api.registry import MODULES, available_cards, load_modules
from dashboard_config import ConfigError, ROOT, load_config


def config(data):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "config.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return load_config(path)


def response(payload=None, status=200, content=b""):
    result = Mock(status_code=status, content=content)
    result.json.return_value = payload
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(response=result)
    return result


class ModuleTests(unittest.TestCase):
    def test_absent_modules_never_import_clients(self):
        script = """
import sys
from api.registry import load_modules
from types import SimpleNamespace
registry = load_modules(SimpleNamespace())
assert not registry.cards
assert not any(registry.collectors.values())
assert not registry.power_actions
assert not any(name in sys.modules for name in
    ('requests', 'lxml', 'psutil', 'netifaces', 'api.pihole',
     'api.home_assistant', 'api.pivccu', 'api.proxmox', 'api.adguard'))
"""
        subprocess.run([sys.executable, "-c", script], cwd=ROOT, check=True)

    def test_defaults_never_activate_modules(self):
        cfg = config({})
        self.assertTrue(all(not hasattr(cfg, name) for name in MODULES))
        self.assertTrue(all(not page["layout"] for page in cfg.PAGES))
        with patch("api.registry.import_module") as importer:
            self.assertFalse(load_modules(cfg).cards)
            importer.assert_not_called()

    def test_only_requested_module_is_loaded(self):
        cfg = config({"pihole": {"url": "http://pi.hole"}})
        from importlib import import_module
        with patch("api.registry.import_module", wraps=import_module) as importer:
            registry = load_modules(cfg)
        self.assertEqual([call.args[0] for call in importer.call_args_list], ["api.pihole"])
        self.assertEqual(set(registry.cards), {"pihole", "pi_hole"})
        self.assertEqual(len(registry.collectors["medium"]), 1)
        self.assertFalse(registry.collectors["slow"])
        self.assertTrue(cfg.pihole["verify_ssl"])

    def test_catalog_matches_all_registered_cards(self):
        blocks = {"system": {}, "network": {}, "power": {},
                  "pihole": {"url": "http://pi.hole"},
                  "pivccu": {"ip": "192.168.1.30", "token": "token"},
                  "home_assistant": {"url": "http://ha:8123", "token": "token"},
                  "adguard": {}, "proxmox": {"url": "https://pve:8006",
                  "api_token_id": "lcd@pve!lcd", "api_token_secret": "token"}}
        cfg = config(blocks)
        registry = load_modules(cfg)
        self.assertEqual(set(registry.cards), available_cards(vars(cfg)))
        self.assertEqual(set(registry.power_actions), {"shutdown", "reboot"})
        self.assertEqual([f.__module__ for f in registry.collectors["medium"]],
                         ["dashboard_modules.system", "dashboard_modules.network", "api.pihole",
                          "api.pivccu", "api.home_assistant", "api.adguard", "api.proxmox"])

    def test_invalid_blocks_and_missing_card_dependencies(self):
        for data in ({"pihole": None}, {"pihole": False}, {"pihole": {}},
                     {"pihole": {"url": "ftp://pi.hole"}},
                     {"pihole": {"url": "http://pi.hole", "verify_ssl": "false"}},
                     {"pivccu": {"ip": "192.168.1.30"}}, {"adguard": {}},
                     {"system": {"typo": True}},
                     {"PAGES": [{"name": "home", "layout": {"row1cell1": "pihole"}}]}):
            with self.subTest(data=data), self.assertRaises(ConfigError):
                config(data)


class HomeAssistantTests(unittest.TestCase):
    def setUp(self):
        from api import home_assistant
        self.api = home_assistant
        self.logger = Mock()
        self.cfg = config({"home_assistant": {
            "url": "https://ha:8123/", "token": "secret", "verify_ssl": False,
            "entities": {
                "temperature": {"entity_id": "sensor.temperature", "precision": 1},
                "lamp": {"entity_id": "switch.lamp", "title": "Lamp",
                         "state_labels": {"on": "AN", "off": "AUS"}},
                "battery": {"entity_id": "sensor.temperature", "attribute": "battery", "unit": "%"},
            }}})
        self.registry = load_modules(self.cfg)

    def test_multiple_entities_and_shared_reads(self):
        state = {}
        with patch("api.home_assistant.requests.get", side_effect=[
            response({}), response({"state": "21.26", "attributes": {
                "friendly_name": "Room", "unit_of_measurement": "°C", "battery": 0}}),
            response({"state": "off", "attributes": {}}),
        ]) as get:
            self.api.collect_medium(state, self.cfg, self.logger)
        # YAML sorts names: battery is first, so sensor.temperature precedes lamp.
        self.assertEqual(get.call_count, 3)
        self.assertEqual(get.call_args_list[0].kwargs["headers"]["Authorization"], "Bearer secret")
        self.assertFalse(get.call_args_list[0].kwargs["verify"])
        self.assertEqual(get.call_args_list[0].kwargs["timeout"], 5)
        cards = self.registry.cards
        self.assertEqual(cards["home_assistant.temperature"](state)["value"], "21.3 °C")
        self.assertEqual(cards["home_assistant.temperature"](state)["title"], "Room")
        self.assertEqual(cards["home_assistant.lamp"](state)["value"], "AUS")
        self.assertEqual(cards["home_assistant.battery"](state)["value"], "0 %")

    def test_failed_poll_clears_values_and_auth_skips_entity_requests(self):
        for failure, expected in ((response(status=401), "AUTH"),
                                  (requests.ConnectionError(), "OFFLINE")):
            state = {"ha_entities": {"switch.lamp": ({"state": "on"}, "")}}
            with patch("api.home_assistant.requests.get", side_effect=[failure]) as get:
                self.api.collect_medium(state, self.cfg, self.logger)
            self.assertEqual(get.call_count, 1)
            self.assertEqual(self.registry.cards["home_assistant.lamp"](state)["value"], expected)

    def test_one_entity_failure_does_not_hide_other_entities(self):
        for failure in (response(status=404), response(status=403), response([]), requests.Timeout()):
            with self.subTest(failure=failure), patch("api.home_assistant.requests.get", side_effect=[
                response({}), failure, response({"state": "on", "attributes": {}}),
            ]):
                state = {}
                self.api.collect_medium(state, self.cfg, self.logger)
                self.assertEqual(self.registry.cards["home_assistant.lamp"](state)["value"], "AN")
                self.assertIn(self.registry.cards["home_assistant.temperature"](state)["value"],
                              ("ENTITY", "AUTH", "API"))

    def test_unavailable_unknown_and_missing_attribute(self):
        for raw in ("unavailable", "unknown"):
            state = {"ha_entities": {"sensor.temperature": ({"state": raw}, "")}}
            self.assertEqual(self.registry.cards["home_assistant.battery"](state)["value"], raw.upper())
        state = {"ha_entities": {"sensor.temperature": ({"state": "21"}, "")}}
        self.assertEqual(self.registry.cards["home_assistant.battery"](state)["value"], "ATTRIBUTE")

    def test_metadata(self):
        state = {}
        with patch("api.home_assistant.requests.get", return_value=response({"version": "2026.9.1"})):
            self.api.collect_slow(state, self.cfg, self.logger)
        self.assertEqual(state["ha_version"], "2026.9.1")

    def test_entity_cards_render_together_on_supported_displays(self):
        from dashboard_renderer import DashboardRenderer
        page = {"name": "home", "layout": {
            "row1cell1": "home_assistant.temperature",
            "row1cell2": "home_assistant.lamp",
            "row2cell1": {"module": "home_assistant.battery", "colspan": 2},
        }}
        state = {"ha_entities": {
            "sensor.temperature": ({"state": "21.26", "attributes": {
                "unit_of_measurement": "°C", "battery": 80}}, ""),
            "switch.lamp": ({"state": "on", "attributes": {}}, ""),
        }}
        for width in (320, 280):
            display = Mock(width=240, height=width)
            logger = Mock()
            renderer = DashboardRenderer(display, self.cfg, self.registry.cards, logger)
            renderer.render_page(page, state)
            self.assertEqual(display.ShowImage.call_args.args[0].size, (width, 240))
            logger.exception.assert_not_called()
            logger.warning.assert_not_called()

    def test_invalid_entity_options(self):
        for options in ({}, {"entity_id": "../config"}, {"entity_id": "switch.lamp", "precision": True},
                        {"entity_id": "sensor.temp", "state_labels": {"on": True}},
                        {"entity_id": "sensor.temp", "attribute": []}):
            block = {"url": "http://ha", "token": "secret", "entities": {"test": options}}
            with self.subTest(options=options), self.assertRaises(ConfigError):
                config({"home_assistant": block})


class ExistingIntegrationTests(unittest.TestCase):
    def test_pivccu_xml_and_error_reset(self):
        from api import pivccu
        cfg = config({"pivccu": {"ip": "192.168.1.30", "token": "secret"}})
        state = {}
        with patch("api.pivccu.requests.get", return_value=response(content=b"<root><notification/><notification/></root>")):
            pivccu.collect_medium(state, cfg, Mock())
        self.assertEqual(pivccu.card_openccu(state)["value"], "ERR 2")
        logger = Mock()
        with patch("api.pivccu.requests.get", side_effect=requests.Timeout("url?sid=secret")):
            pivccu.collect_medium(state, cfg, logger)
        self.assertIsNone(state["openccu_messages"])
        self.assertEqual(pivccu.card_openccu(state)["value"], "OFFLINE")
        self.assertNotIn("secret", str(logger.mock_calls))

    def test_pihole_session_renewal_and_summary(self):
        from api import pihole
        cfg = config({"pihole": {"url": "http://pi.hole", "password": "secret"}})
        state = {}
        with patch.dict(pihole._SESSION, {"base": "", "password": "", "sid": ""}), \
             patch("api.pihole.requests.post", side_effect=[
                 response({"session": {"valid": True, "sid": "old"}}),
                 response({"session": {"valid": True, "sid": "new"}}),
             ]) as post, patch("api.pihole.requests.get", side_effect=[
                 response(status=401), response({"blocking": True}),
                 response({"queries": {"total": 100, "blocked": 20, "percent_blocked": 20},
                           "gravity": {"domains_being_blocked": 1000}}),
             ]) as get:
            pihole.collect_medium(state, cfg, Mock())
            self.assertEqual(post.call_count, 2)
            self.assertEqual(get.call_args.kwargs["headers"], {"X-FTL-SID": "new"})
        self.assertEqual(pihole.card_pihole(state)["value"], "20.0%")

    def test_proxmox_guest_filtering_and_headers(self):
        from api import proxmox
        cfg = config({"proxmox": {"url": "https://pve:8006", "api_token_id": "lcd@pve!lcd",
                                  "api_token_secret": "secret", "include_lxc": True}})
        state = {}
        with patch("api.proxmox.requests.get", return_value=response({"data": [
            {"type": "qemu", "status": "running"}, {"type": "lxc", "status": "stopped"},
            {"type": "qemu", "status": "stopped", "template": 1},
        ]})) as get:
            proxmox.collect_medium(state, cfg, Mock())
        self.assertEqual(proxmox.card_proxmox(state)["value"], "1/2 VMs")
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "PVEAPIToken=lcd@pve!lcd=secret")

    def test_adguard_uses_home_assistant_connection(self):
        from api import adguard
        cfg = config({"home_assistant": {"url": "http://ha", "token": "secret"}, "adguard": {}})
        state = {"ha_online": True}
        with patch("api.home_assistant.requests.get", side_effect=[
            response({"state": "on"}), response({"state": "12.5"}),
        ]):
            adguard.collect_medium(state, cfg, Mock())
        self.assertEqual(adguard.card_adguard(state)["detail"], "BLOCK 12.5%")


if __name__ == "__main__":
    unittest.main()
