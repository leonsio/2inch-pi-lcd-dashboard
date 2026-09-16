"""Tests for systemd service summary and dynamic unit cards."""

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from api.registry import available_cards, load_modules
from dashboard_modules import services


class ServicesModuleTests(unittest.TestCase):
    def config(self):
        return SimpleNamespace(
            services={
                "units": {
                    "ssh": "ssh.service",
                    "dashboard": {
                        "name": "dashboard.service",
                        "title": "LCD Dashboard",
                    },
                }
            },
            REQUEST_TIMEOUT=5,
            LOG_MEDIUM_VALUES=False,
        )

    def test_collects_counts_and_unit_states(self):
        listing = Mock(
            returncode=0,
            stdout=(
                "ssh.service loaded active running OpenSSH server\n"
                "oneshot.service loaded active exited One-shot helper\n"
                "● broken.service loaded failed failed Broken service\n"
            ),
        )
        shown = Mock(
            returncode=0,
            stdout=(
                "Id=ssh.service\n"
                "LoadState=loaded\n"
                "ActiveState=active\n"
                "SubState=running\n"
                "UnitFileState=enabled\n\n"
                "Id=dashboard.service\n"
                "LoadState=loaded\n"
                "ActiveState=inactive\n"
                "SubState=dead\n"
                "UnitFileState=enabled\n"
            ),
        )
        state = {}
        with patch("dashboard_modules.services._systemctl", side_effect=[listing, shown]) as call:
            services.collect_medium(state, self.config(), Mock())

        self.assertEqual(call.call_count, 2)
        self.assertEqual(state["services_total"], 3)
        self.assertEqual(state["services_active"], 2)
        self.assertEqual(state["services_running"], 1)
        self.assertEqual(state["services_failed"], 1)
        self.assertTrue(state["services_available"])
        self.assertEqual(state["services_units"]["ssh"]["sub"], "running")
        self.assertEqual(state["services_units"]["dashboard"]["active"], "inactive")

    def test_cards_expose_summary_and_specific_units(self):
        cfg = self.config()
        state = {
            "services_available": True,
            "services_total": 8,
            "services_active": 6,
            "services_running": 5,
            "services_failed": 1,
            "services_units": {
                "ssh": {
                    "name": "ssh.service", "title": "SSH", "error": "",
                    "load": "loaded", "active": "active", "sub": "running",
                    "unit_file": "enabled",
                },
                "dashboard": {
                    "name": "dashboard.service", "title": "LCD Dashboard", "error": "",
                    "load": "loaded", "active": "inactive", "sub": "dead",
                    "unit_file": "enabled",
                },
            },
        }
        cards = load_modules(cfg).cards

        self.assertEqual(cards["services"](state)["value"], "5 RUN")
        self.assertEqual(cards["services_failed"](state)["value"], "1")
        self.assertEqual(cards["services_failed"](state)["status"], "error")
        self.assertEqual(cards["services.ssh"](state)["value"], "RUNNING")
        self.assertEqual(cards["services.ssh"](state)["status"], "ok")
        self.assertEqual(cards["services.dashboard"](state)["value"], "INACTIVE")
        self.assertEqual(cards["services.dashboard"](state)["status"], "warn")

    def test_dynamic_cards_are_registered(self):
        data = {
            "services": {
                "units": {
                    "ssh": "ssh.service",
                    "dashboard": {"name": "dashboard.service", "title": "LCD Dashboard"},
                }
            }
        }
        cards = available_cards(data)
        self.assertIn("services", cards)
        self.assertIn("services_running", cards)
        self.assertIn("services_failed", cards)
        self.assertIn("services.ssh", cards)
        self.assertIn("services.dashboard", cards)

    def test_not_found_unit_is_error(self):
        card = services._unit_card(
            {
                "services_units": {
                    "missing": {
                        "name": "missing.service", "title": "Missing", "error": "",
                        "load": "not-found", "active": "inactive", "sub": "dead",
                        "unit_file": "",
                    }
                }
            },
            "missing",
            "missing.service",
            "Missing",
        )
        self.assertEqual(card["value"], "NOT FOUND")
        self.assertEqual(card["status"], "error")

    def test_summary_without_systemd_is_unavailable(self):
        card = services.card_services({"services_available": False})
        self.assertEqual(card["value"], "N/A")
        self.assertEqual(card["detail"], "SYSTEMD")
        self.assertEqual(card["status"], "error")


if __name__ == "__main__":
    unittest.main()
