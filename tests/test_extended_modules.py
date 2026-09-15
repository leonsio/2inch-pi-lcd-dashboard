"""Tests for extended metric and dynamic service cards."""

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


def response(payload):
    result = Mock(status_code=200)
    result.json.return_value = payload
    return result


class ExtendedCardTests(unittest.TestCase):
    def test_system_cards(self):
        from dashboard_modules import system
        state = {
            "swap_percent": 25.0, "swap_used_gb": 0.5, "swap_total_gb": 2.0,
            "disk_free_gb": 42.5, "disk_total_gb": 128.0,
            "cpu_freq_mhz": 1800.0, "cpu_freq_max_mhz": 2400.0,
            "process_count": 123, "cpu_count": 4,
        }
        self.assertEqual(system.card_swap(state)["value"], "25%")
        self.assertEqual(system.card_disk_free(state)["value"], "42.5GB")
        self.assertEqual(system.card_cpu_freq(state)["value"], "1.80GHz")
        self.assertEqual(system.card_processes(state)["value"], "123")
        self.assertAlmostEqual(system.card_swap_ring(state)["ratio"], 0.25)
        self.assertAlmostEqual(system.card_freq_ring(state)["ratio"], 0.75)

    def test_network_cards(self):
        from dashboard_modules import network
        state = {
            "network_interface": "wlan0", "network_is_up": True,
            "network_speed_mbps": 300, "network_mtu": 1500,
            "network_rx_rate": 1024 * 1024, "network_tx_rate": 512 * 1024,
            "wifi_quality_percent": 80.0, "wifi_signal_dbm": -48.0,
        }
        self.assertIn("1.0M/s", network.card_traffic(state)["value"])
        self.assertEqual(network.card_link(state)["value"], "300 Mbps")
        ring = network.card_wifi_ring(state)
        self.assertAlmostEqual(ring["ratio"], 0.8)
        self.assertAlmostEqual(ring["color_ratio"], 0.2)

    def test_proxmox_dynamic_guest_cards(self):
        from dashboard_modules import proxmox
        cfg = config({"proxmox": {
            "url": "https://pve:8006", "api_token_id": "lcd@pve!lcd",
            "api_token_secret": "test-token", "include_lxc": True,
            "vms": {"homeassistant": {"vmid": 100, "title": "Home Assistant"}, "dockerhost": 101},
        }})
        state = {}
        with patch("dashboard_modules.proxmox.requests.get", return_value=response({"data": [
            {"type": "qemu", "vmid": 100, "status": "running", "node": "pve1"},
            {"type": "qemu", "vmid": 101, "status": "stopped", "node": "pve1"},
        ]})):
            proxmox.collect_medium(state, cfg, Mock())
        cards = load_modules(cfg).cards
        self.assertEqual(cards["proxmox.homeassistant"](state)["value"], "RUNNING")
        self.assertEqual(cards["proxmox.dockerhost"](state)["value"], "STOPPED")
        self.assertEqual(cards["proxmox"](state)["value"], "1/2 VMs")

    def test_docker_dynamic_container_cards(self):
        from dashboard_modules import docker
        cfg = config({"docker": {
            "socket": "/var/run/docker.sock",
            "containers": {"homeassistant": {"name": "homeassistant", "title": "Home Assistant"}, "mqtt": "mosquitto"},
        }})
        state = {}
        payload = [
            {"Id": "a" * 64, "Names": ["/homeassistant"], "Image": "ha-image", "State": "running", "Status": "Up"},
            {"Id": "b" * 64, "Names": ["/mosquitto"], "Image": "mqtt-image", "State": "exited", "Status": "Exited"},
        ]
        with patch("dashboard_modules.docker._get_json", return_value=payload):
            docker.collect_medium(state, cfg, Mock())
        cards = load_modules(cfg).cards
        self.assertEqual(cards["docker"](state)["value"], "1/2")
        self.assertAlmostEqual(cards["docker_ring"](state)["ratio"], 0.5)
        self.assertEqual(cards["docker.homeassistant"](state)["value"], "RUNNING")
        self.assertEqual(cards["docker.mqtt"](state)["value"], "EXITED")
        self.assertIn("docker.homeassistant", available_cards(vars(cfg)))


if __name__ == "__main__":
    unittest.main()
