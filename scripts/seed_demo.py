"""Fill a running LabTrack API with demo data through its public endpoints.

Usage:
    BASE_URL=http://localhost:8080 ADMIN_PASSWORD=AdminPass123 python scripts/seed_demo.py
    BASE_URL=https://labtrack-api-xxxx.a.run.app ADMIN_PASSWORD=$(gcloud secrets versions access latest --secret=labtrack-admin-password) python scripts/seed_demo.py

Safe to run more than once: existing records are reused.
"""

import os
import random
import sys

import httpx

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080").rstrip("/")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@labtrack.dev")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

COURSE = {"code": "SIDM-2026", "name": "Praktikum Data Mining", "semester": "Ganjil 2026/2027"}
STUDENTS = [
    ("1032230101", "Aditya Nugroho"), ("1032230102", "Bella Safitri"), ("1032230103", "Cahyo Wibowo"),
    ("1032230104", "Dina Maharani"), ("1032230105", "Eko Saputra"), ("1032230106", "Fitri Handayani"),
    ("1032230107", "Gilang Ramadhan"), ("1032230108", "Hana Puspita"), ("1032230109", "Irfan Hakim"),
    ("1032230110", "Jihan Aulia"), ("1032230111", "Kevin Wijaya"), ("1032230112", "Laras Ayuningtyas"),
]
SESSIONS = [
    (1, "Modul 1: Data Preprocessing", "2026-09-07T08:00:00+07:00"),
    (2, "Modul 2: Klasifikasi Naive Bayes dan Decision Tree", "2026-09-14T08:00:00+07:00"),
    (3, "Modul 3: Clustering K-Means", "2026-09-21T08:00:00+07:00"),
    (4, "Modul 4: Association Rule Apriori", "2026-09-28T08:00:00+07:00"),
]
DEMO_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def main() -> None:
    if not ADMIN_PASSWORD:
        sys.exit("Set ADMIN_PASSWORD")
    rng = random.Random(42)  # reproducible demo data
    c = httpx.Client(base_url=BASE_URL, timeout=30)

    r = c.post("/auth/login", data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    r.raise_for_status()
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    # Course
    r = c.post("/courses", json=COURSE)
    if r.status_code == 409:
        course = next(x for x in c.get("/courses").json() if x["code"] == COURSE["code"])
    else:
        r.raise_for_status()
        course = r.json()

    # Students
    student_ids = []
    for nim, name in STUDENTS:
        r = c.post("/students", json={"nim": nim, "full_name": name, "class_name": "SI-47-01"})
        if r.status_code == 409:
            student_ids.append(c.get("/students", params={"q": nim}).json()["items"][0]["id"])
        else:
            r.raise_for_status()
            student_ids.append(r.json()["id"])
    c.post(f"/courses/{course['id']}/enrollments", json={"student_ids": student_ids}).raise_for_status()

    # Sessions, attendance and reports
    existing = {s["session_no"]: s for s in c.get("/sessions", params={"course_id": course["id"]}).json()}
    statuses = ["present"] * 7 + ["late", "excused", "absent"]
    for no, title, when in SESSIONS:
        session = existing.get(no)
        if session is None:
            r = c.post("/sessions", json={
                "course_id": course["id"], "session_no": no, "title": title,
                "scheduled_at": when, "room": "Lab Sistem Informasi 01",
            })
            r.raise_for_status()
            session = r.json()

        records = [{"student_id": sid, "status": rng.choice(statuses)} for sid in student_ids]
        c.put(f"/sessions/{session['id']}/attendance", json={"records": records}).raise_for_status()

        for rec in records:
            if rec["status"] in ("present", "late"):
                r = c.post(
                    f"/sessions/{session['id']}/reports",
                    data={"student_id": rec["student_id"]},
                    files={"file": (f"laporan-modul{no}.pdf", DEMO_PDF, "application/pdf")},
                )
                r.raise_for_status()
                c.patch(f"/reports/{r.json()['id']}/grade", json={"score": rng.randint(65, 98)}).raise_for_status()

    summary = c.get(f"/courses/{course['id']}/attendance-summary").json()
    at_risk = [s["full_name"] for s in summary["students"] if s["at_risk"]]
    print(f"Seeded course {course['code']}: {len(student_ids)} students, {summary['sessions_held']} sessions")
    print(f"Students below {summary['threshold']}% attendance: {', '.join(at_risk) or 'none'}")


if __name__ == "__main__":
    main()
