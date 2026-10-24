"""End-to-end integration check against a running LabTrack API (Cloud Run + Cloud SQL).

Creates a throwaway student, reads it back from PostgreSQL through the API, updates it,
checks the error paths (409, 401, 404 with request_id) and deletes it again. Writes a
Markdown report with one row per check.

Usage:
    BASE_URL=https://labtrack-api-xxxx.a.run.app \
    ADMIN_PASSWORD=$(gcloud secrets versions access latest --secret=labtrack-admin-password) \
    python scripts/api_integration_check.py --out docs/bukti/002/integration-report.md

Exit code is 0 only when every check passes.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

WIB = timezone(timedelta(hours=7))


@dataclass
class Check:
    name: str
    request: str
    expected: str
    actual: str
    ok: bool
    request_id: str
    latency_ms: float


def _call(client: httpx.Client, method: str, path: str, **kwargs) -> tuple[httpx.Response, float]:
    start = time.perf_counter()
    r = client.request(method, path, **kwargs)
    return r, round((time.perf_counter() - start) * 1000, 1)


def run_checks(client: httpx.Client, email: str, password: str, nim: str | None = None) -> list[Check]:
    """Run the scenario. Stops early only when login fails, since every later step needs a token."""
    checks: list[Check] = []
    nim = nim or f"99{int(time.time()) % 10**10:010d}"

    def record(name, method, path, expected_status, r, ms, extra_ok=True, actual=None):
        checks.append(
            Check(
                name=name,
                request=f"{method} {path}",
                expected=str(expected_status),
                actual=actual or str(r.status_code),
                ok=r.status_code == expected_status and extra_ok,
                request_id=r.headers.get("X-Request-ID", ""),
                latency_ms=ms,
            )
        )
        return r

    r, ms = _call(client, "GET", "/health")
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    record("Health and database", "GET", "/health", 200, r, ms, body.get("database") == "ok",
           f"{r.status_code}, database={body.get('database')}")

    r, ms = _call(client, "POST", "/auth/login", data={"username": email, "password": password})
    record("Login admin", "POST", "/auth/login", 200, r, ms)
    if r.status_code != 200:
        return checks
    auth = {"Authorization": f"Bearer {r.json()['access_token']}"}

    payload = {"nim": nim, "full_name": "Uji Integrasi", "class_name": "UJI-01"}
    r, ms = _call(client, "POST", "/students", json=payload, headers=auth)
    record("Create student", "POST", "/students", 201, r, ms)
    sid = r.json().get("id") if r.status_code == 201 else None

    r, ms = _call(client, "GET", "/students", params={"q": nim}, headers=auth)
    found = r.status_code == 200 and r.json().get("total") == 1
    record("Read back from database", "GET", f"/students?q={nim}", 200, r, ms, found,
           f"{r.status_code}, total={r.json().get('total') if r.status_code == 200 else '-'}")

    if sid is not None:
        r, ms = _call(client, "PATCH", f"/students/{sid}", json={"class_name": "UJI-02"}, headers=auth)
        updated = r.status_code == 200 and r.json().get("class_name") == "UJI-02"
        record("Update student", "PATCH", f"/students/{sid}", 200, r, ms, updated)

    r, ms = _call(client, "POST", "/students", json=payload, headers=auth)
    record("Duplicate NIM rejected with request_id", "POST", "/students", 409, r, ms,
           bool(r.json().get("request_id")))

    r, ms = _call(client, "GET", "/students")
    record("No token rejected with request_id", "GET", "/students", 401, r, ms,
           r.json().get("request_id") == r.headers.get("X-Request-ID"))

    if sid is not None:
        r, ms = _call(client, "DELETE", f"/students/{sid}", headers=auth)
        record("Delete test student", "DELETE", f"/students/{sid}", 204, r, ms)
        r, ms = _call(client, "GET", f"/students/{sid}", headers=auth)
        record("Deleted student is gone", "GET", f"/students/{sid}", 404, r, ms)

    return checks


def render_report(checks: list[Check], base_url: str) -> str:
    passed = sum(c.ok for c in checks)
    lines = [
        "# Laporan Uji Integrasi API LabTrack",
        "",
        f"- Target: `{base_url}`",
        f"- Waktu: {datetime.now(WIB):%Y-%m-%d %H:%M:%S} WIB",
        "- Dihasilkan oleh: `scripts/api_integration_check.py`",
        f"- Hasil: **{passed} dari {len(checks)} pemeriksaan lulus**",
        "",
        "| No | Pemeriksaan | Permintaan | Diharapkan | Aktual | Latensi (ms) | request_id | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, c in enumerate(checks, 1):
        lines.append(
            f"| {i} | {c.name} | `{c.request}` | {c.expected} | {c.actual} | {c.latency_ms} "
            f"| `{c.request_id}` | {'LULUS' if c.ok else 'GAGAL'} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LabTrack end-to-end integration check")
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://localhost:8080"))
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL", "admin@labtrack.dev"))
    parser.add_argument("--out", help="Write the Markdown report here")
    args = parser.parse_args(argv)
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        parser.error("Set ADMIN_PASSWORD")

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=30) as client:
        checks = run_checks(client, args.email, password)
    report = render_report(checks, args.base_url)
    print(report)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(report, encoding="utf-8")
    return 0 if all(c.ok for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
