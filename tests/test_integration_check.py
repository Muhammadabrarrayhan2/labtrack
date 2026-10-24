"""scripts/api_integration_check.py run in-process against the app (TestClient is an httpx.Client)."""

import importlib.util
import sys
from pathlib import Path

_path = Path(__file__).resolve().parent.parent / "scripts" / "api_integration_check.py"
_spec = importlib.util.spec_from_file_location("api_integration_check", _path)
check = importlib.util.module_from_spec(_spec)
sys.modules["api_integration_check"] = check  # dataclasses need the module registered
_spec.loader.exec_module(check)


def test_all_checks_pass_against_the_app(client):
    results = check.run_checks(client, "admin@labtrack.dev", "AdminPass123", nim="9900000001")
    assert [c.name for c in results if not c.ok] == []
    assert len(results) == 9
    assert all(c.request_id for c in results)


def test_wrong_password_stops_after_login(client):
    results = check.run_checks(client, "admin@labtrack.dev", "wrong-password")
    assert [c.name for c in results] == ["Health and database", "Login admin"]
    assert results[1].ok is False and results[1].actual == "401"


def test_report_lists_every_check(client):
    results = check.run_checks(client, "admin@labtrack.dev", "AdminPass123", nim="9900000002")
    report = check.render_report(results, "http://testserver")
    assert "**9 dari 9 pemeriksaan lulus**" in report
    assert report.count("| LULUS |") == 9
