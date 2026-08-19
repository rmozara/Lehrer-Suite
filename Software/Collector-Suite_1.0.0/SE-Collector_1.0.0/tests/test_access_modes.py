from __future__ import annotations

import io
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import qrcode
except ModuleNotFoundError:  # optionale Testabhängigkeit
    qrcode = None

from se_collector.config import normalize_base_url
if qrcode is not None:
    from se_collector.web import decode_qr_image, student_token_from_qr_payload


TOKEN = "AbCdEfghijklmnopqrstuvwxyz_0123456789-XYZ"


@unittest.skipIf(qrcode is None, "QR-Testabhängigkeit ist nicht installiert.")
class AccessModeTests(unittest.TestCase):
    def test_qr_generator_address_automatically_enables_direct_mode(self):
        from se_collector.config import _load_settings_data

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = root / "settings.json"
            generator_settings = root / "generator_settings.json"
            generator_settings.write_text(
                json.dumps({"direct_base_url": "http://192.168.50.10:8765"}),
                encoding="utf-8",
            )
            with (
                patch("se_collector.config.DATA_DIR", root),
                patch("se_collector.config.SETTINGS_FILE", settings),
                patch("se_collector.config.GENERATOR_SETTINGS_FILE", generator_settings),
                patch("se_collector.config.SHARED_TEACHER_SETTINGS_FILE", root / "teacher.json"),
            ):
                data, _ = _load_settings_data()
        self.assertEqual(data["direct_base_url"], "http://192.168.50.10:8765")

    def test_token_is_extracted_independently_of_host(self):
        self.assertEqual(
            student_token_from_qr_payload(f"http://192.168.50.10:8765/p/{TOKEN}"),
            TOKEN,
        )
        self.assertEqual(
            student_token_from_qr_payload(f"https://anderer-laptop.local/p/{TOKEN}"),
            TOKEN,
        )

    def test_non_personal_qr_is_rejected(self):
        self.assertIsNone(student_token_from_qr_payload("http://192.168.50.10:8765/status/abc"))
        self.assertIsNone(student_token_from_qr_payload("not-a-personal-code"))

    @unittest.skipIf(qrcode is None, "QR-Testabhängigkeit ist nicht installiert.")
    def test_photographed_qr_can_be_decoded(self):
        payload = f"http://192.168.50.10:8765/p/{TOKEN}"
        image = qrcode.make(payload)
        output = io.BytesIO()
        image.save(output, format="PNG")
        self.assertEqual(decode_qr_image(output.getvalue()), payload)


    def test_qr_on_photographed_sheet_can_be_decoded(self):
        from PIL import Image, ImageDraw

        payload = f"http://192.168.50.10:8765/p/{TOKEN}"
        qr = qrcode.make(payload).convert("RGB").resize((620, 620))
        sheet = Image.new("RGB", (2400, 3200), "white")
        draw = ImageDraw.Draw(sheet)
        draw.rectangle((120, 160, 2280, 3040), outline="black", width=5)
        draw.text((200, 250), "Persoenliche QR-Karte", fill="black")
        sheet.paste(qr, (890, 1250))
        output = io.BytesIO()
        sheet.save(output, format="JPEG", quality=90)
        self.assertEqual(decode_qr_image(output.getvalue()), payload)

    def test_two_qr_template_opens_phone_camera_directly(self):
        from pathlib import Path

        template = Path(__file__).resolve().parents[1] / "se_collector" / "templates" / "two_qr.html"
        text = template.read_text(encoding="utf-8")
        self.assertIn("Kamera öffnen", text)
        self.assertIn('capture="environment"', text)
        self.assertIn('name="personal_code"', text)
        self.assertEqual(text.count('name="session_code"'), 2)
        self.assertIn('/code"', text)

    def test_session_admin_uses_background_polling_without_meta_refresh(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        template = (root / "se_collector" / "templates" / "session_admin.html").read_text(encoding="utf-8")
        script = (root / "se_collector" / "static" / "session_admin.js").read_text(encoding="utf-8")
        self.assertNotIn("http-equiv=\"refresh\"", template)
        self.assertIn("/live", template)
        self.assertIn("setInterval(refresh, 3000)", script)
        self.assertIn("response.status === 404", script)
        self.assertIn("Zur Übersicht", script)
        self.assertIn("clearInterval(timer)", script)

    def test_two_qr_fallback_is_collapsed_when_direct_mode_is_available(self):
        from pathlib import Path

        template = (Path(__file__).resolve().parents[1] / "se_collector" / "templates" / "session_admin.html").read_text(encoding="utf-8")
        self.assertIn("Ausweichweg: Zwei-QR-Modus anzeigen", template)
        self.assertIn("{% if settings.direct_mode_enabled %}", template)
        self.assertIn("two-qr-open", template)

    def test_admin_direct_mode_distinguishes_saved_status_from_pending_selection(self):
        from pathlib import Path

        template = (Path(__file__).resolve().parents[1] / "se_collector" / "templates" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("Direktmodus aktiviert", template)
        self.assertIn("Verwendete Adresse:", template)
        self.assertIn("Die Auswahl gilt erst", template)
        self.assertIn("Diese Adresse für den Direktmodus verwenden", template)
        self.assertIn("aktuell verwendet", template)
        self.assertNotIn("Direktmodus bereit", template)
        self.assertIn("auf der nächsten Seite jederzeit der Zwei-QR-Modus", template)


    def test_secondary_device_status_is_renamed_and_collapsed(self):
        from pathlib import Path

        template = (Path(__file__).resolve().parents[1] / "se_collector" / "templates" / "session_admin.html").read_text(encoding="utf-8")
        self.assertIn("<section class=\"panel split-panel\">", template)
        self.assertIn("<details class=\"secondary-device-details\">", template)
        self.assertIn("Abgabestand auf Zweitgerät anzeigen", template)
        self.assertNotIn("Smartboard-Abgabestatus", template)

    def test_access_modes_use_equal_width_columns(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        template = (root / "se_collector" / "templates" / "session_admin.html").read_text(encoding="utf-8")
        css = (root / "se_collector" / "static" / "app.css").read_text(encoding="utf-8")
        self.assertIn('<div class="access-mode-grid">', template)
        self.assertIn(".access-mode-grid{display:grid;grid-template-columns:1fr 1fr", css)
        self.assertIn(".split-panel{display:grid;grid-template-columns:1fr 1fr", css)

    def test_qr_card_is_only_shown_after_student_selection(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "se_collector" / "templates" / "cards.html").read_text(encoding="utf-8")
        web = (root / "se_collector" / "web.py").read_text(encoding="utf-8")
        self.assertIn("Bitte auswählen", template)
        self.assertIn("{% if student %}", template)
        self.assertNotIn("student = students[0]", web)

    def test_pdf_output_updates_ods_automatically(self):
        web = (Path(__file__).resolve().parents[1] / "se_collector" / "web.py").read_text(encoding="utf-8")
        route = web.split('def output_pdf(session_id: int, _: str = Depends(admin)):', 1)[1]
        route = route.split('@app.get("/admin/download-ods")', 1)[0]
        self.assertIn("update_raw_data(ODS_FILE, session, rows, form, BACKUP_DIR)", route)
        self.assertLess(route.index("update_raw_data("), route.index("generate_pdf("))

    def test_session_header_is_compact_and_actions_are_grouped(self):
        template = (Path(__file__).resolve().parents[1] / "se_collector" / "templates" / "session_admin.html").read_text(encoding="utf-8")
        self.assertIn("<h1>{{ progress.session.class_id }} · {{ progress.session.period_id }}</h1>", template)
        self.assertIn("<h2>Ergebnisse sichern und ausgeben</h2>", template)
        self.assertNotIn("<h1>Sitzung geöffnet</h1>", template)

    def test_direct_base_url_validation(self):
        self.assertEqual(normalize_base_url("http://192.168.50.10:8765/"), "http://192.168.50.10:8765")
        self.assertEqual(normalize_base_url("", allow_blank=True), "")
        with self.assertRaises(ValueError):
            normalize_base_url("192.168.50.10:8765")
        with self.assertRaises(ValueError):
            normalize_base_url("http://192.168.50.10:8765/p/falsch")

@unittest.skipIf(importlib.util.find_spec("psutil") is None, "Netzwerk-Testabhängigkeit ist nicht installiert.")
class NetworkAddressDetectionTests(unittest.TestCase):
    def test_physical_address_is_preferred_and_virtual_hidden(self):
        import socket
        from types import SimpleNamespace
        from unittest.mock import patch

        from se_collector.config import detect_network_addresses

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
        with patch("psutil.net_if_addrs", return_value=fake_addrs), patch(
            "psutil.net_if_stats", return_value=fake_stats
        ), patch("se_collector.config.detect_lan_ip", return_value="192.168.50.10"):
            result = detect_network_addresses(8765)

        self.assertEqual([item.url for item in result], ["http://192.168.50.10:8765"])
        self.assertTrue(result[0].recommended)
        self.assertEqual(result[0].interface, "wlp2s0")

    def test_saved_ip_is_marked_recommended(self):
        import socket
        from types import SimpleNamespace
        from unittest.mock import patch

        from se_collector.config import detect_network_addresses

        fake_addrs = {
            "wlp2s0": [SimpleNamespace(family=socket.AF_INET, address="192.168.50.10")],
            "enp3s0": [SimpleNamespace(family=socket.AF_INET, address="10.0.0.25")],
        }
        fake_stats = {
            "wlp2s0": SimpleNamespace(isup=True),
            "enp3s0": SimpleNamespace(isup=True),
        }
        with patch("psutil.net_if_addrs", return_value=fake_addrs), patch(
            "psutil.net_if_stats", return_value=fake_stats
        ), patch("se_collector.config.detect_lan_ip", return_value="192.168.50.10"):
            result = detect_network_addresses(8765, preferred_ip="10.0.0.25")

        recommended = [item.ip for item in result if item.recommended]
        self.assertEqual(recommended, ["10.0.0.25"])

if __name__ == "__main__":
    unittest.main()
