"""Render evidence charts from real Cloud Monitoring data (no console access needed).

Usage: python scripts/evidence/monitoring_charts.py <project> <out_dir> <start_utc> <end_utc>
       times as 2026-10-25T18:00:00
Each PNG states its metric and source, so it can stand in for a console screenshot.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from google.cloud import monitoring_v3  # noqa: E402

PROJECT, OUT = sys.argv[1], Path(sys.argv[2])
START = datetime.fromisoformat(sys.argv[3]).replace(tzinfo=timezone.utc)
END = datetime.fromisoformat(sys.argv[4]).replace(tzinfo=timezone.utc)
WIB = timezone(timedelta(hours=7))
OUT.mkdir(parents=True, exist_ok=True)
client = monitoring_v3.MetricServiceClient()
A = monitoring_v3.Aggregation

# Marked moments, UTC (laptop clock, about 2 minutes ahead of Google time)
EVENTS = [
    (datetime(2026, 10, 25, 18, 16, 36, tzinfo=timezone.utc), "uji beban 50 VU"),
    (datetime(2026, 10, 25, 18, 22, 3, tzinfo=timezone.utc), "uji stress 100-300 VU"),
    (datetime(2026, 10, 25, 23, 54, 36, tzinfo=timezone.utc), "Cloud SQL dihentikan"),
    (datetime(2026, 10, 26, 0, 4, 11, tzinfo=timezone.utc), "Cloud SQL dinyalakan"),
]


def series(filter_, aligner, reducer=None, group_by=(), period=60):
    agg = {"alignment_period": {"seconds": period}, "per_series_aligner": aligner}
    if reducer is not None:
        agg["cross_series_reducer"] = reducer
        agg["group_by_fields"] = list(group_by)
    res = client.list_time_series(
        request={
            "name": f"projects/{PROJECT}",
            "filter": filter_,
            "interval": {"start_time": {"seconds": int(START.timestamp())}, "end_time": {"seconds": int(END.timestamp())}},
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            "aggregation": agg,
        }
    )
    out = []
    for ts in res:
        label = dict(ts.metric.labels)
        pts = sorted(
            (p.interval.end_time.astimezone(WIB), p.value.double_value or p.value.int64_value or (p.value.distribution_value.mean if p.value.distribution_value else 0))
            for p in ts.points
        )
        out.append((label, pts))
    return out


def chart(name, title, ylabel, lines, note, ylim=None, hline=None):
    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=120)
    for label, pts in lines:
        if pts:
            ax.plot([t for t, _ in pts], [v for _, v in pts], label=label, linewidth=1.6)
    for t, text in EVENTS:
        tw = t.astimezone(WIB)
        if START.astimezone(WIB) <= tw <= END.astimezone(WIB):
            ax.axvline(tw, color="#888", linestyle="--", linewidth=0.8)
            ax.text(tw, ax.get_ylim()[1], " " + text, fontsize=8, color="#555", va="top", rotation=90)
    if hline is not None:
        ax.axhline(hline[0], color="#c2410c", linestyle=":", linewidth=1.2)
        ax.text(ax.get_xlim()[0], hline[0], " " + hline[1], fontsize=8, color="#c2410c", va="bottom")
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_title(title, fontsize=12, loc="left")
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M", tz=WIB))
    ax.grid(alpha=0.25)
    if len(lines) > 1:
        ax.legend(fontsize=8, loc="upper right")
    fig.text(0.01, 0.01, f"Sumber: Cloud Monitoring API, proyek {PROJECT}. Waktu WIB. {note}", fontsize=7.5, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / name)
    plt.close(fig)
    print("saved", name)


RUN = 'resource.type="cloud_run_revision" AND resource.label."service_name"="labtrack-api"'
SQL = 'resource.type="cloudsql_database"'

inst = series(f'metric.type="run.googleapis.com/container/instance_count" AND {RUN}', A.Aligner.ALIGN_MAX, A.Reducer.REDUCE_SUM)
chart("B-003-02-cloud-run-instances.png", "Jumlah instans Cloud Run (naik saat beban, kembali ke 0 saat idle)", "instans",
      [("instans", inst[0][1] if inst else [])], "Metrik run.googleapis.com/container/instance_count, maks per menit.", ylim=(0, 3.5), hline=(3, "max_instance_count = 3"))

reqs = series(f'metric.type="run.googleapis.com/request_count" AND {RUN}', A.Aligner.ALIGN_RATE, A.Reducer.REDUCE_SUM, ["metric.label.response_code_class"])
chart("B-014-07-requests-by-class.png", "Permintaan per detik menurut kelas kode respons", "permintaan/detik",
      [(lbl.get("response_code_class", "?"), pts) for lbl, pts in reqs], "Metrik run.googleapis.com/request_count, rate per menit.")

lat = series(f'metric.type="run.googleapis.com/request_latencies" AND {RUN}', A.Aligner.ALIGN_PERCENTILE_95, A.Reducer.REDUCE_MAX)
chart("B-003-03-latency-p95.png", "Latensi p95 Cloud Run per menit", "ms",
      [("p95", lat[0][1] if lat else [])], "Metrik run.googleapis.com/request_latencies, persentil 95 per menit.", hline=(800, "target SLO 800 ms"))

cpu = series(f'metric.type="cloudsql.googleapis.com/database/cpu/utilization" AND {SQL}', A.Aligner.ALIGN_MAX, A.Reducer.REDUCE_MAX)
chart("B-003-08-cloudsql-cpu.png", "CPU Cloud SQL (db-f1-micro)", "utilisasi (0-1)",
      [("cpu", cpu[0][1] if cpu else [])], "Metrik cloudsql.googleapis.com/database/cpu/utilization, maks per menit.", ylim=(0, 1), hline=(0.8, "ambang alert 80%"))

conn = series(f'metric.type="cloudsql.googleapis.com/database/postgresql/num_backends" AND {SQL}', A.Aligner.ALIGN_MAX, A.Reducer.REDUCE_SUM)
chart("B-014-08-cloudsql-connections.png", "Koneksi PostgreSQL (batas db-f1-micro 25)", "koneksi",
      [("koneksi", conn[0][1] if conn else [])], "Metrik cloudsql.googleapis.com/database/postgresql/num_backends.", ylim=(0, 27), hline=(20, "ambang alert 20"))

up = series('metric.type="monitoring.googleapis.com/uptime_check/check_passed" AND resource.type="uptime_url"',
            A.Aligner.ALIGN_FRACTION_TRUE, A.Reducer.REDUCE_MEAN, period=300)
chart("B-014-04-uptime-check.png", "Uptime check /health: porsi region pemeriksa yang lulus", "porsi lulus",
      [("lulus", up[0][1] if up else [])], "Metrik uptime_check/check_passed, per 5 menit, rata-rata seluruh region.", ylim=(-0.05, 1.1))
