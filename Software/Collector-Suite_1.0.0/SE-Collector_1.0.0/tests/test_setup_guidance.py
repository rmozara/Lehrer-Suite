from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SetupGuidanceTests(unittest.TestCase):
    def test_header_tools_are_right_aligned_and_collector_can_shutdown(self):
        template = (ROOT / "se_collector/templates/admin.html").read_text(encoding="utf-8")
        css = (ROOT / "se_collector/static/app.css").read_text(encoding="utf-8")
        web = (ROOT / "se_collector/web.py").read_text(encoding="utf-8")
        launcher = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('class="header-tools"', template)
        self.assertIn("SE beenden", template)
        self.assertIn("align-items:flex-end", css)
        self.assertIn('@app.post("/admin/shutdown"', web)
        self.assertIn("application.state.server = server", launcher)

    def test_closed_session_is_a_clearly_labelled_results_view(self):
        template = (ROOT / "se_collector" / "templates" / "session_admin.html").read_text(encoding="utf-8")
        overview = (ROOT / "se_collector" / "templates" / "admin.html").read_text(encoding="utf-8")
        web = (ROOT / "se_collector" / "web.py").read_text(encoding="utf-8")
        self.assertIn("Diese Sitzung ist geschlossen.", template)
        self.assertIn("Sitzung erneut öffnen", template)
        self.assertIn("{% if progress.session.active %}\n<section class=\"panel access-modes\">", template)
        self.assertIn("Ergebnisse ansehen", overview)
        self.assertIn("Zur Sitzung", overview)
        self.assertIn('/archive', overview)
        self.assertIn('>Archivieren</button>', overview)
        self.assertIn('/admin/session/{session_id}/reopen', web)

    def test_empty_roster_is_explained_in_teacher_page(self):
        text = (ROOT / "se_collector/templates/admin.html").read_text(encoding="utf-8")
        self.assertIn("Arbeitsordner noch nicht vorbereitet", text)
        self.assertIn("Blatt „Namensliste“", text)
        self.assertIn("Namensliste neu laden", text)
        self.assertIn("Datei erneut prüfen", text)
        self.assertIn('class="path-block"', text)

    def test_missing_shared_password_is_explained_in_browser(self):
        text = (ROOT / "se_collector/web.py").read_text(encoding="utf-8")
        self.assertIn("Lehrerpasswort noch nicht eingerichtet", text)
        self.assertIn("Bitte zuerst QR starten", text)
        self.assertIn("lehrkraft", text)

    def test_expected_setup_state_does_not_log_traceback(self):
        text = (ROOT / "se_collector/web.py").read_text(encoding="utf-8")
        self.assertIn("Namensliste aus ODS noch nicht bereit", text)
        self.assertNotIn('logger.exception("Namensliste aus ODS konnte nicht geladen werden")', text)

    def test_program_folder_is_rejected_as_work_folder(self):
        linux = (ROOT / "run_on_linux.sh").read_text(encoding="utf-8")
        windows = (ROOT / "run_on_windows.bat").read_text(encoding="utf-8")
        self.assertIn('if [ "$work_dir" = "$software_dir" ]', linux)
        self.assertIn("Der Programmordner kann nicht als Unterrichtsordner", linux)
        self.assertIn("Der Programmordner kann nicht als Unterrichtsordner", windows)

    def test_teacher_page_opens_automatically(self):
        text = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("webbrowser.open(teacher_url)", text)
        self.assertIn("Die Lehreroberfläche wird jetzt im Browser geöffnet.", text)

    def test_normal_lesson_flow_is_explained_before_session_start(self):
        text = (ROOT / "se_collector/templates/admin.html").read_text(encoding="utf-8")
        self.assertIn("sechsstellige Sitzungscode", text)
        self.assertIn("persönliche QR-Karte", text)


if __name__ == "__main__":
    unittest.main()
