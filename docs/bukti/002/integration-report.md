# Laporan Uji Integrasi API LabTrack

- Target: `https://labtrack-api-b26757zszq-et.a.run.app`
- Waktu: 2026-10-26 01:10:06 WIB
- Dihasilkan oleh: `scripts/api_integration_check.py`
- Hasil: **9 dari 9 pemeriksaan lulus**

| No | Pemeriksaan | Permintaan | Diharapkan | Aktual | Latensi (ms) | request_id | Status |
|---|---|---|---|---|---|---|---|
| 1 | Health and database | `GET /health` | 200 | 200, database=ok | 344.0 | `70a6243f939e0e9edc5adad199e2a6d3` | LULUS |
| 2 | Login admin | `POST /auth/login` | 200 | 200 | 372.2 | `24e553fa81f9e64cdc5adad199e2a69e` | LULUS |
| 3 | Create student | `POST /students` | 201 | 201 | 108.5 | `cbb33c1aebc87ff2dc5adad199e2ae7c` | LULUS |
| 4 | Read back from database | `GET /students?q=991792951805` | 200 | 200, total=1 | 44.4 | `9b79eb6d8a0b7a15dc5adad199e2af60` | LULUS |
| 5 | Update student | `PATCH /students/1` | 200 | 200 | 48.5 | `76bd140a9dd88149dc5adad199e2a961` | LULUS |
| 6 | Duplicate NIM rejected with request_id | `POST /students` | 409 | 409 | 50.2 | `c683667eb879aceedc5adad199e2a362` | LULUS |
| 7 | No token rejected with request_id | `GET /students` | 401 | 401 | 20.5 | `3ae88a4cc9106448dc5adad199e2ac33` | LULUS |
| 8 | Delete test student | `DELETE /students/1` | 204 | 204 | 59.8 | `8244d17931442632dc5adad199e2a550` | LULUS |
| 9 | Deleted student is gone | `GET /students/1` | 404 | 404 | 41.4 | `e9b4e2277de8a404dc5adad199e2a680` | LULUS |
