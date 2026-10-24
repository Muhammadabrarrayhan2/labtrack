# Bukti Unit J.631120.015.01

| Kode | Yang ditangkap | Perintah atau halaman | Sudah |
|---|---|---|---|
| B-015-01 | Respons galat dengan `request_id` di badan JSON dan header `X-Request-ID` yang sama | Swagger: `GET /students/99999` dengan token valid (404), atau `curl -i $API/students` (401) | [ ] |
| B-015-02 | Pencarian log dengan `request_id` dari B-015-01 | Logs Explorer, kueri `jsonPayload.request_id="<id>"` | [ ] |
| B-015-03 | Terminal simulasi insiden: perintah stop, rangkaian 503, perintah start, 200 | `docs/06-sop-dukungan-teknis.md` bagian 6.2 | [ ] |
| B-015-04 | Email alert yang diterima saat simulasi | Kotak masuk `alert_email` | [ ] |
| B-015-05 | Log respons 503 berdasarkan `request_id` | Logs Explorer | [ ] |
| B-015-06 | Insiden terbuka lalu tertutup | Monitoring > Alerting > Incidents | [ ] |
| B-015-07 | Issue dari templat "Laporan masalah pengguna" yang terisi | GitHub > Issues > New issue | [ ] |
| B-015-08 | Issue "Laporan insiden" simulasi yang terisi lengkap dan ditutup | GitHub > Issues | [ ] |
