# Laporan Uji Integrasi API LabTrack

- Target: `http://localhost:8080`
- Waktu: 2026-10-24 10:24:43 WIB
- Dihasilkan oleh: `scripts/api_integration_check.py`
- Hasil: **9 dari 9 pemeriksaan lulus**

| No | Pemeriksaan | Permintaan | Diharapkan | Aktual | Latensi (ms) | request_id | Status |
|---|---|---|---|---|---|---|---|
| 1 | Health and database | `GET /health` | 200 | 200, database=ok | 16.9 | `47bee96d3d0f45fa` | LULUS |
| 2 | Login admin | `POST /auth/login` | 200 | 200 | 334.6 | `fb54a7f2f15b4e30` | LULUS |
| 3 | Create student | `POST /students` | 201 | 201 | 8.9 | `d9c3944fb3ab4938` | LULUS |
| 4 | Read back from database | `GET /students?q=991792812282` | 200 | 200, total=1 | 9.1 | `269b443fc4644d54` | LULUS |
| 5 | Update student | `PATCH /students/13` | 200 | 200 | 53.8 | `5d2a2e85916e41a9` | LULUS |
| 6 | Duplicate NIM rejected with request_id | `POST /students` | 409 | 409 | 50.7 | `71de42bbde8b4f00` | LULUS |
| 7 | No token rejected with request_id | `GET /students` | 401 | 401 | 3.0 | `c1d96daa0bd34e57` | LULUS |
| 8 | Delete test student | `DELETE /students/13` | 204 | 204 | 21.8 | `b35f40d84d134527` | LULUS |
| 9 | Deleted student is gone | `GET /students/13` | 404 | 404 | 8.4 | `87e62c7fc48d4139` | LULUS |
