import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from qr_generator.network_settings import (
    connection_label,
    detect_network_addresses,
    load_preferred_url,
    normalize_base_url,
    save_preferred_url,
)


class NetworkSettingsTests(unittest.TestCase):
    def test_url_is_validated_and_persisted(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings_file = Path(temporary) / "settings.json"
            result = save_preferred_url(settings_file, "http://192.168.50.10:8765/")
            self.assertEqual(result, "http://192.168.50.10:8765")
            self.assertEqual(load_preferred_url(settings_file), result)
            self.assertEqual(
                json.loads(settings_file.read_text(encoding="utf-8")),
                {"direct_base_url": result},
            )
        with self.assertRaises(ValueError):
            normalize_base_url("192.168.50.10:8765")

    def test_physical_address_is_preferred_and_virtual_hidden(self):
        fake_addrs = {
            "wlp2s0": [SimpleNamespace(family=socket.AF_INET, address="192.168.50.10")],
            "docker0": [SimpleNamespace(family=socket.AF_INET, address="172.17.0.1")],
            "lo": [SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")],
        }
        fake_stats = {
            "wlp2s0": SimpleNamespace(isup=True),
            "docker0": SimpleNamespace(isup=True),
            "lo": SimpleNamespace(isup=True),
        }
        fake_psutil = SimpleNamespace(
            net_if_addrs=lambda: fake_addrs,
            net_if_stats=lambda: fake_stats,
        )
        with (
            patch.dict(sys.modules, {"psutil": fake_psutil}),
            patch("qr_generator.network_settings.detect_lan_ip", return_value="192.168.50.10"),
        ):
            result = detect_network_addresses(8765)
        self.assertEqual([item.url for item in result], ["http://192.168.50.10:8765"])
        self.assertTrue(result[0].recommended)
        self.assertEqual(connection_label(result[0].interface), "WLAN")


if __name__ == "__main__":
    unittest.main()
