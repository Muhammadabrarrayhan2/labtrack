"""Load test for the LabTrack API.

Models the practicum peak: lab assistants open the student list, submit attendance
for their session, and check the attendance recap. Each simulated user logs in once
in on_start and reuses the JWT for every request.

Requires seed data (scripts/seed_demo.py) so that COURSE_ID and SESSION_ID exist.

Usage (headless, 50 users, spawn 5/s, 5 minutes, CSV output):
    LABTRACK_PASSWORD=... locust -f scripts/loadtest/locustfile.py \
        --host https://labtrack-api-xxxx.a.run.app \
        --headless -u 50 -r 5 -t 5m \
        --csv docs/bukti/003/locust --html docs/bukti/003/locust-report.html

Environment:
    LABTRACK_EMAIL     login email (default admin@labtrack.dev)
    LABTRACK_PASSWORD  login password (required)
    COURSE_ID          course used for summary and attendance (default 1)
    SESSION_ID         session that receives attendance (default 1)
"""

import os

from locust import HttpUser, between, task

EMAIL = os.environ.get("LABTRACK_EMAIL", "admin@labtrack.dev")
PASSWORD = os.environ.get("LABTRACK_PASSWORD", "")
COURSE_ID = int(os.environ.get("COURSE_ID", "1"))
SESSION_ID = int(os.environ.get("SESSION_ID", "1"))
STATUSES = ("present", "present", "present", "late", "absent")


class LabAssistant(HttpUser):
    # Think time between actions of one assistant
    wait_time = between(1, 3)

    def on_start(self) -> None:
        if not PASSWORD:
            raise RuntimeError("Set LABTRACK_PASSWORD before running the load test")
        r = self.client.post(
            "/auth/login",
            data={"username": EMAIL, "password": PASSWORD},
            name="POST /auth/login",
        )
        r.raise_for_status()
        self.client.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

        r = self.client.get(f"/courses/{COURSE_ID}/students", name="GET /courses/{id}/students")
        r.raise_for_status()
        self.student_ids = [s["id"] for s in r.json()][:40]

    @task(4)
    def list_students(self) -> None:
        self.client.get("/students", params={"limit": 40}, name="GET /students")

    @task(3)
    def attendance_summary(self) -> None:
        self.client.get(
            f"/courses/{COURSE_ID}/attendance-summary",
            name="GET /courses/{id}/attendance-summary",
        )

    @task(2)
    def submit_attendance(self) -> None:
        if not self.student_ids:
            return
        # Idempotent bulk upsert, safe to repeat on the same session
        records = [
            {"student_id": sid, "status": STATUSES[i % len(STATUSES)]}
            for i, sid in enumerate(self.student_ids)
        ]
        self.client.put(
            f"/sessions/{SESSION_ID}/attendance",
            json={"records": records},
            name="PUT /sessions/{id}/attendance",
        )

    @task(1)
    def health(self) -> None:
        self.client.get("/health", name="GET /health")
