"""Evidence screenshots: a live Swagger UI call, and terminal-style renders of saved command output.

Usage: ADMIN_PASSWORD=... python scripts/evidence/screenshot_evidence.py <api_url> <out_dir>
The terminal renders show the saved output files byte for byte; nothing is retyped.
"""

import html
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

API = sys.argv[1].rstrip("/")
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parents[2]

TERMINALS = [
    ("B-013-18-vm-provisioning.png", "docs/bukti/013/vm-provisioning-20261026-0116.txt", "scripts/ops/vm-report.sh"),
    ("B-013-20-restore-verification.png", "docs/bukti/013/restore-verification-20261026-0625.md", "scripts/ops/sql-restore-test.sh"),
    ("B-002-09-integration-report.png", "docs/bukti/002/integration-report.md", "scripts/api_integration_check.py"),
    ("B-015-03-incident-timeline.png", "docs/bukti/015/simulasi-insiden-gcp-ringkas.txt", "simulasi insiden Cloud SQL (ringkas)"),
    ("B-015-02-request-id-trace.png", "docs/bukti/015/request-id-trace.txt", "pelacakan request_id ke Cloud Logging"),
    ("B-014-01-monitoring-inventory.png", "docs/bukti/014/monitoring-inventory.txt", "Cloud Monitoring API: SLO, alert, uptime"),
    ("B-014-05-sla-report.png", "docs/laporan-sla/2026-10-26_2026-10-26.md", "scripts/sla_report.py"),
    ("B-013-08-pgdump-backup.png", "docs/bukti/013/log/2026-10-26-I6.txt", "backup pg_dump dari VM"),
    ("B-013-03-rollback.png", "docs/bukti/013/log/2026-10-26-P6.txt", "scripts/ops/rollback.sh"),
    ("B-013-09-patch-change-log.png", "docs/bukti/013/change-log.md", "scripts/ops/vm-patch.sh"),
    ("B-013-14-account-deactivation.png", "docs/bukti/013/log/2026-10-26-U3.txt", "penonaktifan akun dan reset password"),
    ("B-013-16-iaas-iam-config.png", "docs/bukti/013/iaas-and-iam-config.txt", "konfigurasi VM, IAM, firewall, snapshot"),
    ("B-003-01-locust-terminal.png", "docs/bukti/003/locust-terminal.txt", "Locust 50 pengguna, 5 menit"),
    ("B-003-07-stress-monitoring.png", "docs/bukti/003/stress-monitoring.txt", "metrik per tahap uji stress"),
    ("B-002-08-terraform-apply.png", "docs/bukti/001/terraform-apply.txt", "terraform apply (bagian akhir)"),
]

STYLE = (
    "body{margin:0;background:#0f1720;color:#d6e2e5;font:13px/1.45 Consolas,'Cascadia Mono',monospace}"
    ".bar{background:#1c2a33;color:#8fb3ba;padding:8px 14px;font:12px Segoe UI,sans-serif}"
    "pre{margin:0;padding:14px;white-space:pre-wrap;word-break:break-word}"
)


def tail(text: str, n: int = 70) -> str:
    lines = [ln for ln in text.splitlines() if "FutureWarning" not in ln and "warnings.warn" not in ln]
    return "\n".join(lines[-n:])


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)

    # 1. Live Swagger UI: authorize, then run the attendance summary
    page = browser.new_page(viewport={"width": 1366, "height": 900})
    page.goto(f"{API}/docs", wait_until="networkidle")
    page.click("button.authorize")
    # Type key by key: a bulk fill of the password field is not picked up by Swagger UI's form state
    page.locator("input#oauth_username").press_sequentially("admin@labtrack.dev", delay=20)
    page.locator("input#oauth_password").press_sequentially(os.environ["ADMIN_PASSWORD"], delay=20)
    page.locator(".modal-ux button", has_text="Authorize").last.click()
    # Wait until the dialog shows Logout, i.e. the token came back (bcrypt plus a cold start can take seconds)
    page.locator(".modal-ux button", has_text="Logout").wait_for(timeout=60000)
    page.click("button.btn-done")
    op = page.locator("#operations-courses-attendance_summary_courses__course_id__attendance_summary_get")
    op.locator(".opblock-summary").click()
    op.locator("button.try-out__btn").click()
    op.locator("input[placeholder='course_id']").fill("1")
    op.locator("button.execute").click()
    op.locator(".responses-wrapper .live-responses-table").wait_for(timeout=30000)
    page.wait_for_timeout(1500)
    op.scroll_into_view_if_needed()
    op.screenshot(path=str(OUT / "B-001-04-swagger-attendance-summary.png"))
    print("saved B-001-04-swagger-attendance-summary.png")

    # 2. Terminal-style renders of saved outputs
    term = browser.new_page(viewport={"width": 1100, "height": 400})
    for name, rel, label in TERMINALS:
        text = tail((ROOT / rel).read_text(encoding="utf-8", errors="replace"))
        term.set_content(
            f"<style>{STYLE}</style><div class='bar'>{html.escape(label)}  |  {html.escape(rel)}</div>"
            f"<pre>{html.escape(text)}</pre>"
        )
        term.screenshot(path=str(OUT / name), full_page=True)
        print("saved", name)
    browser.close()
