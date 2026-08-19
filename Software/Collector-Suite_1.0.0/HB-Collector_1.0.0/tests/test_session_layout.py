from pathlib import Path
import unittest


WEB = (Path(__file__).resolve().parents[1] / "hefter_collector" / "web.py").read_text(encoding="utf-8")


class SessionLayoutTests(unittest.TestCase):
    def test_direct_mode_precedes_workflow_and_assignment(self):
        body = WEB.split('body = f"""', 1)[1].split('return page("Bewertung steuern"', 1)[0]
        self.assertLess(body.index("{access_section}"), body.index("Ablauf steuern"))
        self.assertLess(body.index("Ablauf steuern"), body.index("Zufällige Zuordnung"))

    def test_personal_links_are_not_exposed(self):
        self.assertNotIn("Sonderwerkzeug: Persönliche Schüleransichten öffnen", WEB)

    def test_session_and_success_page_offer_ods_download(self):
        self.assertGreaterEqual(WEB.count("href='/admin/download-ods'"), 3)

    def test_phase_and_assignment_actions_keep_scroll_position(self):
        self.assertIn("id='workflow'", WEB)
        self.assertIn("id='assignment'", WEB)
        self.assertIn("sessionStorage.setItem(scrollKey, String(window.scrollY))", WEB)
        self.assertIn("window.scrollTo(0, Number(saved) || 0)", WEB)
        self.assertNotIn('return redirect(f"/admin/session/{session_id}#assignment")', WEB)

    def test_mobile_access_spacing_and_peer_polling(self):
        self.assertIn(".student-access-form input", WEB)
        self.assertIn(".criterion>.scale{margin-top:12px}", WEB)
        self.assertIn("setInterval(check,2000)", WEB)
        self.assertIn("window.location.replace", WEB)

    def test_student_scale_runs_from_four_to_one(self):
        rating_form = WEB.split("def rating_form", 1)[1].split("def create_app", 1)[0]
        self.assertIn("for value in range(4, 0, -1)", rating_form)

    def test_archived_delete_uses_readable_button_and_confirmation_dialog(self):
        self.assertIn("class='small danger-button'>Endgültig löschen", WEB)
        self.assertIn("type='hidden' name='confirmation'", WEB)
        self.assertIn('onsubmit=\\"return confirm(', WEB)

    def test_assignment_is_allowed_during_self_assessment(self):
        route = WEB.split("def assign(session_id: int", 1)[1].split("def swap", 1)[0]
        self.assertIn('{"setup", "self", "self_closed"}', route)

    def test_exclusions_have_visible_spacing(self):
        self.assertIn(".subsection .exclusions-title{margin-top:var(--space-4)}", WEB)
        self.assertIn(".exclusion-form{margin-bottom:var(--space-2)}", WEB)
        self.assertIn("class='exclusions-title'", WEB)

    def test_no_automatic_test_value_insertion_remains(self):
        self.assertNotIn("demo-fill", WEB)
        self.assertNotIn("Fehlende Testwerte", WEB)


if __name__ == "__main__":
    unittest.main()
