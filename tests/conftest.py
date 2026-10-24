import os
import tempfile

# Configure the app for tests before it is imported
_tmp = tempfile.mkdtemp(prefix="labtrack-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["LOCAL_UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["JWT_SECRET"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "admin@labtrack.dev"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "AdminPass123"
os.environ.pop("GCS_BUCKET", None)
os.environ.pop("INSTANCE_CONNECTION_NAME", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def login(client: TestClient, email: str, password: str) -> dict:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as c:  # lifespan recreates tables and the bootstrap admin
        yield c


@pytest.fixture()
def admin(client) -> dict:
    return login(client, "admin@labtrack.dev", "AdminPass123")


@pytest.fixture()
def assistant(client, admin) -> dict:
    r = client.post(
        "/auth/users",
        json={"email": "asisten@labtrack.dev", "full_name": "Asisten Praktikum", "password": "Asisten123"},
        headers=admin,
    )
    assert r.status_code == 201, r.text
    return login(client, "asisten@labtrack.dev", "Asisten123")


@pytest.fixture()
def course_setup(client, admin) -> dict:
    """One course, three enrolled students, two sessions."""
    course = client.post(
        "/courses",
        json={"code": "SIDM01", "name": "Praktikum Data Mining", "semester": "Ganjil 2026/2027"},
        headers=admin,
    ).json()
    student_ids = []
    for i, name in enumerate(["Andi Pratama", "Budi Santoso", "Citra Lestari"], start=1):
        r = client.post(
            "/students",
            json={"nim": f"10322300{i}", "full_name": name, "class_name": "SI-47-01"},
            headers=admin,
        )
        student_ids.append(r.json()["id"])
    client.post(f"/courses/{course['id']}/enrollments", json={"student_ids": student_ids}, headers=admin)
    session_ids = []
    for no in (1, 2):
        r = client.post(
            "/sessions",
            json={
                "course_id": course["id"],
                "session_no": no,
                "title": f"Modul {no}",
                "scheduled_at": f"2026-10-{20 + no}T08:00:00+07:00",
                "room": "Lab SI-01",
            },
            headers=admin,
        )
        session_ids.append(r.json()["id"])
    return {"course_id": course["id"], "student_ids": student_ids, "session_ids": session_ids}
