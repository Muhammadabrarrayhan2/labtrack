"""Every error response carries request_id in the body, equal to the X-Request-ID header.

Users quote this ID when they report a problem; support searches Cloud Logging for it.
"""

import logging

import pytest

from app.database import get_db
from app.main import app


def assert_request_id(r):
    body = r.json()
    assert "request_id" in body, body
    assert body["request_id"] == r.headers["X-Request-ID"]
    assert body["request_id"]
    return body


def test_401_has_request_id(client):
    body = assert_request_id(client.get("/students"))
    assert body["detail"] == "Not authenticated"


def test_401_expired_or_invalid_token_keeps_www_authenticate(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
    assert r.headers["WWW-Authenticate"] == "Bearer"
    assert_request_id(r)


def test_403_has_request_id(client, assistant):
    r = client.post("/courses", json={"code": "XX01", "name": "Forbidden", "semester": "Ganjil"}, headers=assistant)
    assert r.status_code == 403
    assert assert_request_id(r)["detail"] == "Admin role required"


def test_404_from_handler_has_request_id(client, admin):
    r = client.get("/students/99999", headers=admin)
    assert r.status_code == 404
    assert assert_request_id(r)["detail"] == "Student 99999 not found"


def test_404_unknown_route_has_request_id(client):
    r = client.get("/does-not-exist")
    assert r.status_code == 404
    assert_request_id(r)


def test_409_has_request_id(client, admin):
    body = {"nim": "1032230001", "full_name": "Andi Pratama"}
    client.post("/students", json=body, headers=admin)
    r = client.post("/students", json=body, headers=admin)
    assert r.status_code == 409
    assert_request_id(r)


def test_422_validation_error_has_request_id_and_details(client, admin):
    r = client.post("/students", json={"nim": "ABC", "full_name": "Invalid"}, headers=admin)
    assert r.status_code == 422
    body = assert_request_id(r)
    assert isinstance(body["detail"], list) and body["detail"][0]["loc"][-1] == "nim"


def test_trace_header_is_reused_as_request_id(client):
    r = client.get("/students", headers={"X-Cloud-Trace-Context": "abc123def456/1;o=1"})
    assert r.json()["request_id"] == "abc123def456"
    assert r.headers["X-Request-ID"] == "abc123def456"


@pytest.fixture()
def broken_db():
    def boom():
        raise RuntimeError("simulated database outage")
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = boom
    yield
    app.dependency_overrides.pop(get_db, None)


def test_500_has_request_id_and_matches_log(client, admin, broken_db, caplog):
    with caplog.at_level(logging.ERROR, logger="labtrack"):
        r = client.get("/students", headers=admin)
    assert r.status_code == 500
    body = assert_request_id(r)
    assert body["detail"] == "Internal server error"
    # The same ID is on the ERROR log line that support will search for
    logged = [rec for rec in caplog.records if rec.levelno == logging.ERROR]
    assert any(getattr(rec, "request_id", None) == body["request_id"] for rec in logged)


def test_health_503_has_request_id(client, monkeypatch):
    import app.main as main

    class DownEngine:
        def connect(self):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(main, "engine", DownEngine())
    r = client.get("/health")
    assert r.status_code == 503
    body = assert_request_id(r)
    assert body["database"] == "unreachable"


def test_success_responses_are_unchanged(client, admin):
    r = client.get("/auth/me", headers=admin)
    assert r.status_code == 200
    assert "request_id" not in r.json()
    assert r.headers["X-Request-ID"]
