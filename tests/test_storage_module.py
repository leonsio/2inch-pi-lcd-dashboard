"""Storage module tests without real disks or smartctl access."""

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

from api.registry import available_cards, load_modules
from dashboard_config import load_config
from dashboard_modules import storage


def config(data):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "config.yaml"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        return load_config(path)


class StorageModuleTests(unittest.TestCase):
    def test_empty_block_enables_root_device_and_dynamic_cards(self):
        cfg = config({"storage": {}})
        self.assertIn("root", cfg.storage["devices"])
        cards = available_cards(vars(cfg))
        self.assertIn("storage", cards)
        self.assertIn("storage.root", cards)
        self.assertIn("storage.root_ring", cards)
        self.assertIn("storage.root_free", cards)
        self.assertIn("storage.root_io", cards)
        self.assertIn("storage.root_smart", cards)
        registry = load_modules(cfg)
        self.assertEqual(set(registry.cards), cards)

    def test_capacity_cards_and_unmounted_state(self):
        cfg = config({"storage": {"devices": {
            "ssd": {"mount": "/mnt/ssd", "title": "SSD", "device": "", "io_device": "", "smart": False},
            "missing": {"mount": "/mnt/missing", "title": "MISSING", "device": "", "io_device": "", "smart": False},
        }, "smartctl": "smartctl"}})
        partitions = [SimpleNamespace(mountpoint="/mnt/ssd", device="/dev/sda1", fstype="ext4")]

        def usage(path):
            if path == "/mnt/missing":
                raise FileNotFoundError(path)
            return SimpleNamespace(total=100 * 1024**3, used=75 * 1024**3,
                                   free=25 * 1024**3, percent=75.0)

        state = {}
        with patch("dashboard_modules.storage.psutil.disk_partitions", return_value=partitions), \
             patch("dashboard_modules.storage.psutil.disk_usage", side_effect=usage):
            storage.collect_medium(state, cfg, Mock())

        registry = load_modules(cfg)
        self.assertEqual(registry.cards["storage.ssd"](state)["value"], "75%")
        self.assertEqual(registry.cards["storage.ssd_free"](state)["value"], "25.0GB")
        self.assertAlmostEqual(registry.cards["storage.ssd_ring"](state)["ratio"], 0.75)
        self.assertEqual(registry.cards["storage.missing"](state)["value"], "UNMOUNTED")

    def test_io_rate_uses_configured_diskstats_device(self):
        cfg = config({"storage": {"devices": {
            "ssd": {"mount": "/mnt/ssd", "title": "SSD", "device": "/dev/sda", "io_device": "sda", "smart": False},
        }, "smartctl": "smartctl"}})
        first = {"sda": SimpleNamespace(read_bytes=1000, write_bytes=2000)}
        second = {"sda": SimpleNamespace(read_bytes=3048, write_bytes=6096)}
        state = {}
        with patch("dashboard_modules.storage.time.monotonic", side_effect=[10.0, 12.0]), \
             patch("dashboard_modules.storage.psutil.disk_io_counters", side_effect=[first, second]):
            storage.collect_fast(state, cfg, Mock())
            self.assertEqual(load_modules(cfg).cards["storage.ssd_io"](state)["value"], "WAIT")
            storage.collect_fast(state, cfg, Mock())

        card = load_modules(cfg).cards["storage.ssd_io"](state)
        self.assertEqual(card["value"], "R 1KB/s")
        self.assertEqual(card["detail"], "W 2KB/s")

    def test_smart_json_health_and_temperature(self):
        cfg = config({"storage": {"smartctl": "smartctl", "devices": {
            "ssd": {"mount": "/mnt/ssd", "title": "SSD", "device": "/dev/sda", "io_device": "sda", "smart": True},
        }}})
        proc = SimpleNamespace(
            stdout='{"smart_status":{"passed":true},"temperature":{"current":34}}',
            returncode=0,
        )
        state = {}
        with patch("dashboard_modules.storage.shutil.which", return_value="/usr/sbin/smartctl"), \
             patch("dashboard_modules.storage.os.path.exists", return_value=True), \
             patch("dashboard_modules.storage.subprocess.run", return_value=proc) as run:
            storage.collect_slow(state, cfg, Mock())

        run.assert_called_once()
        card = load_modules(cfg).cards["storage.ssd_smart"](state)
        self.assertEqual(card["value"], "PASSED")
        self.assertEqual(card["detail"], "TEMP 34°C")
        self.assertEqual(card["status"], "ok")

    def test_smart_failure_marks_summary_error(self):
        state = {
            "storage_devices": {"ssd": {"mounted": True}},
            "storage_smart": {"ssd": {"status": "FAILED", "passed": False, "temperature": 50}},
        }
        card = storage.card_storage(state)
        self.assertEqual(card["detail"], "SMART FAIL 1")
        self.assertEqual(card["status"], "error")


if __name__ == "__main__":
    unittest.main()
