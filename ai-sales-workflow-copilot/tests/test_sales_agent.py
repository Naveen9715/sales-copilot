"""Smoke tests for core routing and lead-management helpers."""
import contextlib
import importlib.util
import io
import tempfile
import unittest
import sys
import types
from pathlib import Path
from unittest.mock import patch

# Keep core smoke tests runnable on machines where Google API packages have
# not been installed yet. Real integrations still require requirements.txt.
def install_google_import_stubs_if_missing():
    try:
        import google.auth.transport.requests  # noqa: F401
        import google.oauth2.credentials  # noqa: F401
        import google_auth_oauthlib.flow  # noqa: F401
        import googleapiclient.discovery  # noqa: F401
        import googleapiclient.errors  # noqa: F401
        return
    except ImportError:
        pass

    def module(name):
        result = types.ModuleType(name)
        sys.modules[name] = result
        return result

    google = sys.modules.setdefault("google", module("google"))
    auth = module("google.auth")
    transport = module("google.auth.transport")
    requests_module = module("google.auth.transport.requests")
    requests_module.Request = type("Request", (), {})
    oauth2 = module("google.oauth2")
    credentials_module = module("google.oauth2.credentials")
    credentials_module.Credentials = type("Credentials", (), {})
    oauthlib = module("google_auth_oauthlib")
    flow_module = module("google_auth_oauthlib.flow")
    flow_module.InstalledAppFlow = type("InstalledAppFlow", (), {})
    api = module("googleapiclient")
    discovery = module("googleapiclient.discovery")
    discovery.build = lambda *args, **kwargs: None
    errors = module("googleapiclient.errors")
    errors.HttpError = type("HttpError", (Exception,), {})

install_google_import_stubs_if_missing()

MODULE_PATH = Path(__file__).resolve().parents[1] / "sales_agent_unified_v6.py"
spec = importlib.util.spec_from_file_location("sales_agent", MODULE_PATH)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


class SalesAgentTests(unittest.TestCase):
    def test_product_question_is_not_intercepted_by_calculator(self):
        self.assertFalse(agent.handle_calculation_request("Does your product integrate with Salesforce?"))

    def test_calculation_expression_is_handled(self):
        output = io.StringIO()
        with patch.object(agent, "remember", lambda *args, **kwargs: None):
            with contextlib.redirect_stdout(output):
                handled = agent.handle_calculation_request("Calculate 5 x 200")
        self.assertTrue(handled)
        self.assertIn("Total = 1000", output.getvalue())

    def test_priority_is_transparent_and_heuristic(self):
        lead = {
            "email": "prospect@example.com",
            "company": "Example Co",
            "notes": "Interested in a demo; budget approved; urgent timeline",
        }
        self.assertEqual(agent.lead_priority(lead), "High")

    def test_status_and_follow_up_updates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original = agent.LEADS_FILE
            agent.LEADS_FILE = str(Path(temp_dir) / "leads.json")
            try:
                agent.save_leads([{"id": 7, "name": "Test Lead", "status": "New"}])
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    agent.update_lead_status(7, "Qualified")
                    agent.set_lead_follow_up(7, "2026-10-20")
                saved = agent.load_leads()[0]
                self.assertEqual(saved["status"], "Qualified")
                self.assertEqual(saved["follow_up_due"], "2026-10-20")
            finally:
                agent.LEADS_FILE = original

    def test_command_router_updates_status_and_follow_up(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original = agent.LEADS_FILE
            agent.LEADS_FILE = str(Path(temp_dir) / "leads.json")
            try:
                agent.save_leads([{"id": 3, "name": "Router Test", "status": "New"}])
                with contextlib.redirect_stdout(io.StringIO()):
                    agent.handle_lead_request("update lead status 3 Meeting Scheduled")
                    agent.handle_lead_request("set follow-up 3 2026-10-20")
                saved = agent.load_leads()[0]
                self.assertEqual(saved["status"], "Meeting Scheduled")
                self.assertEqual(saved["follow_up_due"], "2026-10-20")
            finally:
                agent.LEADS_FILE = original

    def test_invalid_follow_up_date_is_rejected(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            agent.set_lead_follow_up(1, "tomorrow-ish")
        self.assertIn("YYYY-MM-DD", output.getvalue())

    def test_build_follow_up_request_uses_known_lead_details(self):
        request = agent.build_follow_up_request({
            "name": "Asha", "company": "Example Ltd", "email": "asha@example.com",
            "notes": "Asked about a demo", "source": "Website",
        })
        self.assertIn("Asha", request)
        self.assertIn("asha@example.com", request)
        self.assertIn("Asked about a demo", request)
        self.assertIn("Do not invent", request)

    def test_sales_automation_is_a_recognised_command(self):
        self.assertTrue(agent.looks_like_lead_request("sales automation"))

    def test_sales_automation_with_no_leads_exits_safely(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original = agent.LEADS_FILE
            agent.LEADS_FILE = str(Path(temp_dir) / "leads.json")
            try:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    agent.run_sales_automation()
                self.assertIn("No open leads are due", output.getvalue())
            finally:
                agent.LEADS_FILE = original

    def test_sales_automation_updates_lead_after_confirmed_send(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original = agent.LEADS_FILE
            agent.LEADS_FILE = str(Path(temp_dir) / "leads.json")
            due_today = agent.datetime.now(agent.INDIA_TIMEZONE).date().isoformat()
            try:
                agent.save_leads([{
                    "id": 9, "name": "Automation Test", "company": "Example Co",
                    "email": "automation@example.com", "notes": "Interested in a demo",
                    "status": "New", "follow_up_due": due_today,
                }])
                with patch("builtins.input", side_effect=["yes", "no"]), \
                     patch.object(agent, "handle_email_request", return_value=True), \
                     patch.object(agent, "create_calendar_appointment") as calendar_mock, \
                     contextlib.redirect_stdout(io.StringIO()):
                    agent.run_sales_automation()
                saved = agent.load_leads()[0]
                self.assertEqual(saved["status"], "Contacted")
                self.assertEqual(saved["follow_up_due"], (agent.datetime.now(agent.INDIA_TIMEZONE).date() + agent.timedelta(days=3)).isoformat())
                calendar_mock.assert_not_called()
            finally:
                agent.LEADS_FILE = original


if __name__ == "__main__":
    unittest.main()
