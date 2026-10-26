"""Seed example data through the API, then drive the web front end and screenshot each view.

The seeded course is labelled "contoh" so it is never mistaken for real practicum data.

Usage:
  BASE_URL=https://... ADMIN_EMAIL=... ADMIN_PASSWORD=... python scripts/evidence/screenshot_webapp.py docs/bukti/screenshots
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
EMAIL = os.environ["ADMIN_EMAIL"]
PASSWORD = os.environ["ADMIN_PASSWORD"]
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "screenshots")
COURSE = {"code": "CC-CONTOH", "name": "Komputasi Awan (contoh)", "semester": "Ganjil 2026/2027"}
STUDENTS = [
    ("2026010101", "Ayu Lestari"), ("2026010102", "Bima Pratama"), ("2026010103", "Citra Maharani"),
    ("2026010104", "Dimas Saputra"), ("2026010105", "Eka Wulandari"), ("2026010106", "Fajar Nugroho"),
    ("2026010107", "Gita Permata"), ("2026010108", "Hendra Wijaya"),
]
# status per student for sessions 1 and 2; two students fall under the 75% threshold
PATTERN = [
    ["present", "present"], ["present", "late"], ["present", "present"], ["absent", "absent"],
    ["present", "excused"], ["present", "present"], ["late", "absent"], ["present", "present"],
]
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def seed(c: httpx.Client) -> None:
    course = next((x for x in c.get("/courses").json() if x["code"] == COURSE["code"]), None)
    if course is None:
        course = c.post("/courses", json=COURSE).raise_for_status().json()
    cid = course["id"]

    ids = []
    for nim, name in STUDENTS:
        found = c.get("/students", params={"q": nim}).json()["items"]
        s = found[0] if found else c.post("/students", json={"nim": nim, "full_name": name, "class_name": "CC-47-01"}).raise_for_status().json()
        ids.append(s["id"])
    c.post(f"/courses/{cid}/enrollments", json={"student_ids": ids}).raise_for_status()

    sessions = {s["session_no"]: s for s in c.get("/sessions", params={"course_id": cid}).json()}
    start = datetime(2026, 10, 5, 2, 0, tzinfo=timezone.utc)  # 09:00 WIB
    titles = ["Pengenalan Google Cloud Console", "Deploy container ke Cloud Run", "Cloud SQL dan Secret Manager"]
    for no, title in enumerate(titles, start=1):
        if no not in sessions:
            sessions[no] = c.post("/sessions", json={
                "course_id": cid, "session_no": no, "title": title,
                "scheduled_at": (start + timedelta(weeks=no - 1)).isoformat(), "room": "Lab 3.2",
            }).raise_for_status().json()

    for col in (0, 1):
        sid = sessions[col + 1]["id"]
        items = [{"student_id": i, "status": PATTERN[k][col]} for k, i in enumerate(ids)]
        c.put(f"/sessions/{sid}/attendance", json={"records": items}).raise_for_status()

    sid = sessions[1]["id"]
    existing = {r["student_id"] for r in c.get(f"/sessions/{sid}/reports").json()}
    for k in (0, 1, 2):
        if ids[k] not in existing:
            c.post(f"/sessions/{sid}/reports", data={"student_id": str(ids[k])},
                   files={"file": (f"laporan-modul1-{STUDENTS[k][0]}.pdf", PDF, "application/pdf")}).raise_for_status()
    first = next(r for r in c.get(f"/sessions/{sid}/reports").json() if r["student_id"] == ids[0])
    c.patch(f"/reports/{first['id']}/grade", json={"score": 88, "feedback": "Konfigurasi IAM sudah tepat."}).raise_for_status()
    return cid


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=BASE, timeout=60) as c:
        tok = c.post("/auth/login", data={"username": EMAIL, "password": PASSWORD}).raise_for_status().json()["access_token"]
        c.headers["Authorization"] = f"Bearer {tok}"
        cid = seed(c)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 860}, color_scheme="light")
        shot = lambda name: page.screenshot(path=OUT / f"web-{name}.png", full_page=True)  # noqa: E731

        page.goto(BASE + "/", wait_until="networkidle")  # browser root redirects to /app/
        expect(page.locator("#login-form")).to_be_visible()
        shot("01-login")
        page.fill("#login-email", EMAIL)
        page.fill("#login-password", "salah-sandi-123")
        page.click("#login-submit")
        expect(page.locator("#login-error")).to_be_visible()
        shot("02-login-gagal")

        page.fill("#login-password", PASSWORD)
        page.click("#login-submit")
        expect(page.locator("#app-view")).to_be_visible()
        page.select_option("#course-select", str(cid))
        expect(page.locator(".stats")).to_be_visible()
        page.wait_for_load_state("networkidle")
        shot("03-rekap")

        page.click(".tabs button[data-view=kehadiran]")
        page.select_option("#session-select", label=page.locator("#session-select option").nth(2).inner_text())
        page.get_by_role("button", name="Tandai semua hadir").click()
        page.locator("tbody tr").nth(3).get_by_text("Terlambat").click()
        page.get_by_role("button", name="Simpan kehadiran").click()
        expect(page.locator("#flash")).to_be_visible()
        shot("04-input-kehadiran")

        page.click(".tabs button[data-view=mahasiswa]")
        expect(page.locator("#q")).to_be_visible()
        page.wait_for_load_state("networkidle")
        shot("05-mahasiswa")

        page.click(".tabs button[data-view=laporan]")
        expect(page.locator("#report-student")).to_be_visible()
        page.select_option("#session-select", index=0)  # module 1 holds the seeded reports
        expect(page.get_by_text("Laporan masuk (3 dari")).to_be_visible()
        shot("06-laporan")

        page.click(".tabs button[data-view=admin]")
        expect(page.locator("#c-code")).to_be_visible()
        page.wait_for_load_state("networkidle")
        shot("07-kelola")

        page.click(".tabs button[data-view=rekap]")
        expect(page.locator(".stats")).to_be_visible()
        page.wait_for_load_state("networkidle")
        shot("08-rekap-setelah-input")

        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        mobile.goto(BASE + "/app/", wait_until="networkidle")
        mobile.screenshot(path=OUT / "web-09-login-ponsel.png")
        browser.close()
    print(f"saved web screenshots to {OUT}")


if __name__ == "__main__":
    main()
