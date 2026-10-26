"""Screenshots of the public evidence pages (live API and GitHub) with the installed Edge.

Usage: python scripts/evidence/screenshot_public.py <api_url> <out_dir>
Needs: pip install playwright (uses the system Microsoft Edge, no browser download).
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

API = sys.argv[1].rstrip("/")
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
REPO = "https://github.com/Muhammadabrarrayhan2/labtrack"

PAGES = [
    ("B-001-03-swagger-ui.png", f"{API}/docs", True, 4000),
    ("B-013-01-health.png", f"{API}/health", False, 0),
    ("B-015-01-error-401-request-id.png", f"{API}/students", False, 0),
    ("B-002-07-github-actions-run.png", f"{REPO}/actions/runs/40246377597", False, 2000),
    ("B-002-10-github-repo.png", REPO, True, 2000),
    ("B-015-07-issue-templates.png", f"{REPO}/issues/new/choose", False, 2000),
]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1366, "height": 860}, device_scale_factor=1)
    for name, url, full, wait_ms in PAGES:
        page.goto(url, wait_until="networkidle", timeout=60000)
        if wait_ms:
            page.wait_for_timeout(wait_ms)
        page.screenshot(path=str(OUT / name), full_page=full)
        print("saved", name, "<-", url)
    browser.close()
