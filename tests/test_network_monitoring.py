"""Tests for WAN status, external IPv4 and configurable IP reachability checks."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

from api.registry import available_cards, load_modules
from dashboard_config import load_config


def config(data):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "config.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return load_config(path)


class NetworkMonitoringTests(unittest.TestCase):
    def setUp(self):
        self.cfg = config({
            "network": {
                "wan": {
                    "enabled": True,
                    "target": "1.1.1.1",
                    "interval": "fast",
                    "timeout": 1.0,
                },
                "external_ipv4": {
                    "enabled": True,
                    "url": "https://api.ipify.org",
                    "interval": "slow",
                    "verify_ssl": True,
                },
                "checks": {
                    "cloudflare": {
                        "ip": "1.1.1.1",
                        "title": "Cloudflare",
                        "interval": "fast",
                        "timeout": 1.0,
                    },
                    "router": {
                        "ip": "192.168.1.1",
                        "title": "Router",
                        "interval": "medium",
                        "timeout": 1.0,
                    },
                },
            },
        })

    def test_dynamic_cards_are_registered(self):
        cards = load_modules(self.cfg).cards
        self.assertIn("wan", cards)
        self.assertIn("wan_ip", cards)
        self.assertIn("external_ipv4", cards)
        self.assertIn("network.cloudflare", cards)
        self.assertIn("network.router", cards)
        self.assertEqual(set(cards), available_cards(vars(self.cfg)))

    def test_fast_medium_slow_assignment_and_ping_deduplication(self):
        from dashboard_modules import network

        state = {}
        online = {
            "target": "1.1.1.1", "online": True,
            "latency_ms": 12.0, "error": "",
        }
        with patch("dashboard_modules.network._ping_ipv4", return_value=online) as ping:
            network._collect_monitoring(state, self.cfg, Mock(), "fast")
            # WAN and cloudflare use the same target/timeout and share one ping.
            self.assertEqual(ping.call_count, 1)
            self.assertTrue(state["wan_status"]["online"])
            self.assertTrue(state["network_checks"]["cloudflare"]["online"])
            self.assertNotIn("router", state["network_checks"])

            network._collect_monitoring(state, self.cfg, Mock(), "medium")
            self.assertEqual(ping.call_count, 2)
            self.assertIn("router", state["network_checks"])

        with patch(
            "dashboard_modules.network._fetch_external_ipv4",
            return_value={"ip": "203.0.113.20", "error": ""},
        ) as external:
            network._collect_monitoring(state, self.cfg, Mock(), "slow")
            external.assert_called_once()
            self.assertEqual(state["external_ipv4"]["ip"], "203.0.113.20")

    def test_status_cards(self):
        cards = load_modules(self.cfg).cards
        state = {
            "wan_status": {
                "target": "1.1.1.1", "online": True,
                "latency_ms": 8.4, "error": "",
            },
            "external_ipv4": {"ip": "203.0.113.20", "error": ""},
            "network_checks": {
                "cloudflare": {
                    "target": "1.1.1.1", "online": True,
                    "latency_ms": 9.1, "error": "",
                },
                "router": {
                    "target": "192.168.1.1", "online": False,
                    "latency_ms": None, "error": "",
                },
            },
        }
        self.assertEqual(cards["wan"](state)["value"], "ONLINE")
        self.assertEqual(cards["wan_ip"](state)["value"], "203.0.113.20")
        self.assertEqual(cards["network.cloudflare"](state)["value"], "ONLINE")
        self.assertEqual(cards["network.router"](state)["value"], "OFFLINE")
        self.assertEqual(cards["network.router"](state)["status"], "error")

    def test_external_ipv4_response_is_validated(self):
        from dashboard_modules import network

        response = Mock(status_code=200, text="203.0.113.25\n")
        with patch("dashboard_modules.network.requests.get", return_value=response):
            result = network._fetch_external_ipv4(
                {"url": "https://api.ipify.org", "verify_ssl": True}, self.cfg
            )
        self.assertEqual(result, {"ip": "203.0.113.25", "error": ""})

        response = Mock(status_code=200, text="not-an-ip")
        with patch("dashboard_modules.network.requests.get", return_value=response):
            result = network._fetch_external_ipv4(
                {"url": "https://api.ipify.org", "verify_ssl": True}, self.cfg
            )
        self.assertEqual(result["error"], "INVALID")


if __name__ == "__main__":
    unittest.main()
