"""Tests for the generic read-only REST dashboard module."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

from api.registry import load_modules
from dashboard_config import ConfigError, load_config


def config(data):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "config.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return load_config(path)


def response(payload=None, status=200):
    result = Mock(status_code=status)
    result.json.return_value = payload
    return result


class RestConfigurationTests(unittest.TestCase):
    def test_dynamic_cards_and_supported_intervals(self):
        cfg = config({"rest": {"endpoints": {
            "fast": {"url": "http://device/api", "interval": 1, "path": "fast"},
            "normal": {"url": "http://device/api", "interval": 60, "path": "normal"},
            "slow": {"url": "http://device/api", "interval": 600, "path": "slow"},
        }}})
        registry = load_modules(cfg)
        self.assertEqual(set(registry.cards), {"rest.fast", "rest.normal", "rest.slow"})
        self.assertEqual(len(registry.collectors["fast"]), 1)
        self.assertEqual(len(registry.collectors["medium"]), 1)
        self.assertEqual(len(registry.collectors["slow"]), 1)

    def test_invalid_rest_configuration(self):
        invalid = (
            {"rest": {"endpoints": {"bad": {"url": "http://device", "interval": 30}}}},
            {"rest": {"endpoints": {"bad-name": {"url": "http://device"}}}},
            {"rest": {"endpoints": {"bad": {"url": "ftp://device"}}}},
            {"rest": {"endpoints": {"bad": {"url": "http://user:pass@device/api"}}}},
            {"rest": {"endpoints": {"bad": {"url": "http://device", "headers": {"X": 1}}}}},
            {"rest": {"endpoints": {"bad": {"url": "http://device", "precision": 11}}}},
        )
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ConfigError):
                config(data)


class RestPollingTests(unittest.TestCase):
    def setUp(self):
        self.cfg = config({"rest": {"endpoints": {
            "temperature": {
                "url": "https://device/api/status",
                "interval": 60,
                "path": "sensors.temperature",
                "title": "Temperature",
                "unit": "°C",
                "precision": 1,
                "detail_path": "device.name",
                "verify_ssl": False,
                "headers": {"Authorization": "Bearer secret"},
            },
            "humidity": {
                "url": "https://device/api/status",
                "interval": 60,
                "path": "sensors.humidity",
                "unit": "%",
                "headers": {"Authorization": "Bearer secret"},
                "verify_ssl": False,
            },
            "fast": {
                "url": "http://fast/api",
                "interval": 1,
                "path": "value",
            },
            "slow": {
                "url": "http://slow/api",
                "interval": 600,
                "path": "value",
            },
        }}})
        self.registry = load_modules(self.cfg)
        self.logger = Mock()

    def test_shared_request_and_json_paths(self):
        from dashboard_modules import rest

        payload = {
            "device": {"name": "Boiler"},
            "sensors": {"temperature": 54.27, "humidity": 42},
        }
        state = {}
        with patch("dashboard_modules.rest.requests.get", return_value=response(payload)) as get:
            rest.collect_medium(state, self.cfg, self.logger)

        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer secret"})
        self.assertFalse(get.call_args.kwargs["verify"])
        self.assertEqual(get.call_args.kwargs["timeout"], 5)
        self.assertEqual(self.registry.cards["rest.temperature"](state)["value"], "54.3 °C")
        self.assertEqual(self.registry.cards["rest.temperature"](state)["detail"], "Boiler")
        self.assertEqual(self.registry.cards["rest.humidity"](state)["value"], "42 %")

    def test_interval_collectors_only_poll_their_group(self):
        from dashboard_modules import rest

        state = {}
        with patch("dashboard_modules.rest.requests.get", return_value=response({"value": 1})) as get:
            rest.collect_fast(state, self.cfg, self.logger)
            self.assertEqual(get.call_count, 1)
            self.assertIn("fast", state["rest_results"])
            self.assertNotIn("slow", state["rest_results"])

            rest.collect_slow(state, self.cfg, self.logger)
            self.assertEqual(get.call_count, 2)
            self.assertIn("slow", state["rest_results"])

    def test_errors_are_card_states(self):
        from dashboard_modules import rest

        state = {}
        with patch("dashboard_modules.rest.requests.get", return_value=response({}, status=401)):
            rest.collect_medium(state, self.cfg, self.logger)
        self.assertEqual(self.registry.cards["rest.temperature"](state)["value"], "AUTH")

        with patch("dashboard_modules.rest.requests.get", return_value=response({"other": 1})):
            rest.collect_medium(state, self.cfg, self.logger)
        self.assertEqual(self.registry.cards["rest.temperature"](state)["value"], "PATH")


if __name__ == "__main__":
    unittest.main()
