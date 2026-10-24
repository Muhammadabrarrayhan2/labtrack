from tests.conftest import MINIMAL_PDF


# ---------- Ops & auth ----------
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"
    assert "X-Request-ID" in r.headers


def test_protected_endpoint_requires_token(client):
    assert client.get("/students").status_code == 401


def test_login_wrong_password(client):
    r = client.post("/auth/login", data={"username": "admin@labtrack.dev", "password": "wrong-pass"})
    assert r.status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_me_returns_admin(client, admin):
    r = client.get("/auth/me", headers=admin)
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_assistant_cannot_create_course(client, assistant):
    r = client.post("/courses", json={"code": "XX01", "name": "Forbidden", "semester": "Ganjil"}, headers=assistant)
    assert r.status_code == 403


# ---------- Students ----------
def test_student_crud_and_search(client, assistant):
    r = client.post(
        "/students",
        json={"nim": "1032230099", "full_name": "Dewi Anggraini", "email": "dewi@student.telkomuniversity.ac.id"},
        headers=assistant,
    )
    assert r.status_code == 201
    sid = r.json()["id"]

    r = client.get("/students", params={"q": "dewi"}, headers=assistant)
    assert r.json()["total"] == 1

    r = client.patch(f"/students/{sid}", json={"class_name": "SI-47-02"}, headers=assistant)
    assert r.json()["class_name"] == "SI-47-02"


def test_duplicate_nim_conflict(client, admin):
    body = {"nim": "1032230001", "full_name": "Andi Pratama"}
    assert client.post("/students", json=body, headers=admin).status_code == 201
    assert client.post("/students", json=body, headers=admin).status_code == 409


def test_invalid_nim_rejected(client, admin):
    r = client.post("/students", json={"nim": "ABC", "full_name": "Invalid"}, headers=admin)
    assert r.status_code == 422


def test_only_admin_can_delete_student(client, admin, assistant):
    sid = client.post("/students", json={"nim": "1032230077", "full_name": "Eka"}, headers=admin).json()["id"]
    assert client.delete(f"/students/{sid}", headers=assistant).status_code == 403
    assert client.delete(f"/students/{sid}", headers=admin).status_code == 204
    assert client.get(f"/students/{sid}", headers=admin).status_code == 404


# ---------- Enrollment & sessions ----------
def test_enrollment_is_idempotent(client, admin, course_setup):
    cid = course_setup["course_id"]
    r = client.post(f"/courses/{cid}/enrollments", json={"student_ids": course_setup["student_ids"]}, headers=admin)
    assert r.json() == {"enrolled": 0, "already_enrolled": 3}
    assert len(client.get(f"/courses/{cid}/students", headers=admin).json()) == 3


def test_duplicate_session_number_conflict(client, admin, course_setup):
    r = client.post(
        "/sessions",
        json={"course_id": course_setup["course_id"], "session_no": 1, "title": "Dup", "scheduled_at": "2026-10-30T08:00:00+07:00"},
        headers=admin,
    )
    assert r.status_code == 409


# ---------- Attendance ----------
def test_attendance_upsert_and_summary(client, assistant, course_setup):
    s1, s2 = course_setup["session_ids"]
    a, b, c = course_setup["student_ids"]

    r = client.put(
        f"/sessions/{s1}/attendance",
        json={"records": [
            {"student_id": a, "status": "present"},
            {"student_id": b, "status": "late"},
            {"student_id": c, "status": "absent"},
        ]},
        headers=assistant,
    )
    assert r.status_code == 200 and len(r.json()) == 3

    # Session 2: student c has no record at all and must count as absent
    client.put(
        f"/sessions/{s2}/attendance",
        json={"records": [{"student_id": a, "status": "present"}, {"student_id": b, "status": "excused"}]},
        headers=assistant,
    )
    # Upsert: correcting a record must not create a duplicate
    client.put(f"/sessions/{s2}/attendance", json={"records": [{"student_id": b, "status": "present"}]}, headers=assistant)
    assert len(client.get(f"/sessions/{s2}/attendance", headers=assistant).json()) == 2

    summary = client.get(f"/courses/{course_setup['course_id']}/attendance-summary", headers=assistant).json()
    assert summary["sessions_held"] == 2
    rows = {row["student_id"]: row for row in summary["students"]}
    assert rows[a]["attendance_rate"] == 100.0 and rows[a]["at_risk"] is False
    assert rows[b]["late"] == 1 and rows[b]["present"] == 1
    assert rows[c]["absent"] == 2 and rows[c]["attendance_rate"] == 0.0 and rows[c]["at_risk"] is True


def test_attendance_rejects_unenrolled_student(client, admin, course_setup):
    outsider = client.post("/students", json={"nim": "1032239999", "full_name": "Luar Kelas"}, headers=admin).json()["id"]
    r = client.put(
        f"/sessions/{course_setup['session_ids'][0]}/attendance",
        json={"records": [{"student_id": outsider, "status": "present"}]},
        headers=admin,
    )
    assert r.status_code == 422


def test_attendance_rejects_duplicate_records(client, admin, course_setup):
    sid = course_setup["student_ids"][0]
    r = client.put(
        f"/sessions/{course_setup['session_ids'][0]}/attendance",
        json={"records": [{"student_id": sid, "status": "present"}, {"student_id": sid, "status": "late"}]},
        headers=admin,
    )
    assert r.status_code == 422


# ---------- Lab reports ----------
def test_report_upload_download_and_grade(client, assistant, course_setup):
    session_id = course_setup["session_ids"][0]
    student_id = course_setup["student_ids"][0]
    r = client.post(
        f"/sessions/{session_id}/reports",
        data={"student_id": student_id},
        files={"file": ("laporan-modul1.pdf", MINIMAL_PDF, "application/pdf")},
        headers=assistant,
    )
    assert r.status_code == 201, r.text
    report = r.json()
    assert report["size_bytes"] == len(MINIMAL_PDF)

    url = client.get(f"/reports/{report['id']}/download-url", headers=assistant).json()["url"]
    assert client.get(url).content == MINIMAL_PDF

    r = client.patch(f"/reports/{report['id']}/grade", json={"score": 88.5, "feedback": "Analisis baik"}, headers=assistant)
    assert r.json()["score"] == 88.5 and r.json()["graded_at"] is not None


def test_reupload_resets_grade(client, assistant, course_setup):
    session_id, student_id = course_setup["session_ids"][0], course_setup["student_ids"][0]
    upload = lambda: client.post(  # noqa: E731
        f"/sessions/{session_id}/reports",
        data={"student_id": student_id},
        files={"file": ("r.pdf", MINIMAL_PDF, "application/pdf")},
        headers=assistant,
    ).json()
    first = upload()
    client.patch(f"/reports/{first['id']}/grade", json={"score": 70}, headers=assistant)
    second = upload()
    assert second["id"] == first["id"] and second["score"] is None


def test_non_pdf_upload_rejected(client, assistant, course_setup):
    r = client.post(
        f"/sessions/{course_setup['session_ids'][0]}/reports",
        data={"student_id": course_setup["student_ids"][0]},
        files={"file": ("fake.pdf", b"MZ\x90\x00 not a pdf", "application/pdf")},
        headers=assistant,
    )
    assert r.status_code == 415


def test_grade_out_of_range_rejected(client, assistant, course_setup):
    r = client.post(
        f"/sessions/{course_setup['session_ids'][0]}/reports",
        data={"student_id": course_setup["student_ids"][0]},
        files={"file": ("r.pdf", MINIMAL_PDF, "application/pdf")},
        headers=assistant,
    )
    r = client.patch(f"/reports/{r.json()['id']}/grade", json={"score": 120}, headers=assistant)
    assert r.status_code == 422
