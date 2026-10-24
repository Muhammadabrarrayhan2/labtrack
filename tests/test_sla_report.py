"""SLA report calculations with mocked Cloud Monitoring time series (no GCP access)."""

import importlib.util
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

_path = Path(__file__).resolve().parent.parent / "scripts" / "sla_report.py"
_spec = importlib.util.spec_from_file_location("sla_report", _path)
sla = importlib.util.module_from_spec(_spec)
sys.modules["sla_report"] = sla
_spec.loader.exec_module(sla)

OCT_START, OCT_END = sla.month_range("2026-10")


def count_ts(code_class: str, *values: int):
    return NS(
        metric=NS(labels={"response_code_class": code_class}),
        points=[NS(value=NS(int64_value=v)) for v in values],
    )


def explicit(bounds):
    """Bucket options with explicit bounds, shaped like the monitoring_v3 message."""
    return NS(
        exponential_buckets=NS(num_finite_buckets=0, growth_factor=0, scale=0),
        linear_buckets=NS(num_finite_buckets=0, offset=0, width=0),
        explicit_buckets=NS(bounds=bounds),
    )


def latency_ts(options, *bucket_counts):
    return NS(
        metric=NS(labels={}),
        points=[NS(value=NS(distribution_value=NS(bucket_options=options, bucket_counts=bc))) for bc in bucket_counts],
    )


# Buckets: [0,100) [100,200) [200,400) [400,800) [800,1600) [1600,inf)
BOUNDS = explicit([100, 200, 400, 800, 1600])


def test_month_range_wraps_december_and_uses_wib():
    start, end = sla.month_range("2026-12")
    assert start.isoformat() == "2026-12-01T00:00:00+07:00"
    assert end.isoformat() == "2027-01-01T00:00:00+07:00"


def test_date_range_is_inclusive_and_rejects_reversed():
    start, end = sla.date_range("2026-10-01", "2026-10-27")
    assert (end - start).days == 27
    with pytest.raises(ValueError):
        sla.date_range("2026-10-05", "2026-10-01")


def test_previous_month():
    assert sla.previous_month(datetime(2026, 1, 15).date()) == "2025-12"


def test_count_requests_sums_points_and_separates_5xx():
    series = [count_ts("2xx", 600, 300), count_ts("4xx", 80), count_ts("5xx", 15, 5)]
    assert sla.count_requests(series) == (1000, 20)


def test_exponential_bucket_bounds():
    opts = NS(
        exponential_buckets=NS(num_finite_buckets=3, growth_factor=2.0, scale=1.0),
        linear_buckets=NS(num_finite_buckets=0),
        explicit_buckets=NS(bounds=[]),
    )
    bounds = sla.bucket_bounds(opts, 5)
    assert bounds[0] == (0.0, 1.0)  # underflow
    assert bounds[1:4] == [(1.0, 2.0), (2.0, 4.0), (4.0, 8.0)]
    assert bounds[4][0] == 8.0 and bounds[4][1] == float("inf")  # overflow


def test_percentile_merges_points_and_interpolates():
    # 100 requests over two hourly points; the 95th falls inside [400, 800)
    ts = latency_ts(BOUNDS, [0, 40, 30, 10, 0, 0], [0, 5, 5, 10, 0, 0])
    options, counts = sla.merge_distributions([ts])
    assert counts == [0, 45, 35, 20, 0, 0]
    # rank 95: 80 below 400 ms, so 15 of 20 into the [400, 800) bucket -> 400 + 400 * 0.75
    assert sla.percentile(options, counts, 95) == pytest.approx(700.0)
    assert sla.percentile(options, counts, 50) == pytest.approx(200 + 200 * (5 / 35))


def test_fraction_below_threshold():
    options, counts = sla.merge_distributions([latency_ts(BOUNDS, [0, 50, 30, 10, 10, 0])])
    assert sla.fraction_below(options, counts, 800) == pytest.approx(0.9)
    assert sla.fraction_below(options, counts, 1200) == pytest.approx(0.95)


def test_evaluate_sla_met():
    counts = [count_ts("2xx", 9_950), count_ts("4xx", 40), count_ts("5xx", 10)]
    latencies = [latency_ts(BOUNDS, [0, 6000, 3000, 900, 100, 0])]
    r = sla.evaluate(counts, latencies, OCT_START, OCT_END)
    assert r.total_requests == 10_000 and r.errors_5xx == 10
    assert r.availability == pytest.approx(0.999)
    assert r.budget_requests == pytest.approx(50.0)  # 0.5% of 10,000
    assert r.budget_consumed == pytest.approx(0.2)  # 10 of 50
    assert r.allowed_downtime_min == pytest.approx(31 * 24 * 60 * 0.005)  # 223.2 minutes in October
    assert r.p95_ms < 800
    assert r.sla_met is True


def test_evaluate_sla_not_met_on_availability():
    counts = [count_ts("2xx", 980), count_ts("5xx", 20)]
    r = sla.evaluate(counts, [latency_ts(BOUNDS, [0, 1000, 0, 0, 0, 0])], OCT_START, OCT_END)
    assert r.availability == pytest.approx(0.98)
    assert r.budget_consumed == pytest.approx(4.0)  # 400% of the budget
    assert r.availability_met is False and r.latency_met is True
    assert r.sla_met is False


def test_evaluate_sla_not_met_on_latency():
    counts = [count_ts("2xx", 1000)]
    r = sla.evaluate(counts, [latency_ts(BOUNDS, [0, 100, 100, 100, 600, 100])], OCT_START, OCT_END)
    assert r.p95_ms >= 800
    assert r.latency_met is False and r.sla_met is False


def test_no_traffic_cannot_be_judged():
    r = sla.evaluate([], [], OCT_START, OCT_END)
    assert r.availability is None and r.p95_ms is None and r.sla_met is None
    assert "Tidak dapat dinilai" in sla.render_markdown(r, "p", "labtrack-api")


def test_render_markdown_contains_report_fields():
    counts = [count_ts("2xx", 9_990), count_ts("5xx", 10)]
    r = sla.evaluate(counts, [latency_ts(BOUNDS, [0, 9000, 1000, 0, 0, 0])], OCT_START, OCT_END)
    md = sla.render_markdown(r, "labtrack-123", "labtrack-api")
    assert md.startswith("# Laporan SLA LabTrack 2026-10")
    assert "2026-10-31 23:59 WIB" in md
    assert "| Total permintaan | 10,000 |" in md
    assert "| Permintaan 5xx | 10 |" in md
    assert "99.900%" in md
    assert "Status SLA bulan ini: Tercapai" in md
    assert "\u2014" not in md  # no em dashes in generated docs


def test_main_writes_report_with_mocked_client(tmp_path, monkeypatch):
    monitoring_v3 = pytest.importorskip("google.cloud.monitoring_v3")
    calls = []

    class FakeClient:
        def list_time_series(self, request):
            calls.append(request)
            if "request_count" in request["filter"]:
                return [count_ts("2xx", 500), count_ts("5xx", 1)]
            return [latency_ts(BOUNDS, [0, 400, 100, 0, 0, 0])]

    monkeypatch.setattr(monitoring_v3, "MetricServiceClient", FakeClient)
    assert sla.main(["--project", "labtrack-123", "--month", "2026-10", "--out-dir", str(tmp_path)]) == 0

    report = (tmp_path / "2026-10.md").read_text(encoding="utf-8")
    assert "| Total permintaan | 501 |" in report
    assert calls[0]["name"] == "projects/labtrack-123"
    assert 'resource.label."service_name"="labtrack-api"' in calls[0]["filter"]
    assert calls[0]["interval"].start_time.timestamp() == OCT_START.timestamp()


def uptime_ts(*fractions: float):
    return NS(metric=NS(labels={}), points=[NS(value=NS(double_value=f)) for f in fractions])


def test_uptime_windows_counts_down_when_most_regions_fail():
    # 1.0 all regions pass, 0.67 one of three failed (still up), 0.0 and 0.33 are down
    assert sla.uptime_windows([uptime_ts(1.0, 0.67, 0.0, 0.33, 1.0)]) == (5, 2)


def test_time_based_availability_and_downtime_minutes():
    # 30 days of 5 minute windows = 8,640 windows; 9 down windows = 45 minutes
    # gives 99.8958%, the worked example in the training module (slide 28)
    fractions = [1.0] * 8631 + [0.0] * 9
    r = sla.evaluate([], [], OCT_START, OCT_END, uptime_series=[uptime_ts(*fractions)])
    assert r.uptime_windows == 8640 and r.downtime_windows == 9
    assert r.downtime_min == 45
    assert r.uptime_availability == pytest.approx(0.998958, abs=1e-6)
    md = sla.render_markdown(r, "p", "labtrack-api")
    assert "| Waktu henti | 45 menit |" in md
    assert "99.896%" in md


def test_uptime_section_without_check_id_reports_no_data():
    r = sla.evaluate([count_ts("2xx", 10)], [], OCT_START, OCT_END)
    assert r.uptime_availability is None
    assert "| Jendela teramati | 0 |" in sla.render_markdown(r, "p", "labtrack-api")


def test_main_queries_uptime_check_when_id_given(tmp_path, monkeypatch):
    monitoring_v3 = pytest.importorskip("google.cloud.monitoring_v3")
    filters = []

    class FakeClient:
        def list_time_series(self, request):
            filters.append(request["filter"])
            if "check_passed" in request["filter"]:
                assert request["aggregation"].alignment_period.seconds == 300
                return [uptime_ts(1.0, 1.0, 0.0, 1.0)]
            if "request_count" in request["filter"]:
                return [count_ts("2xx", 100)]
            return []

    monkeypatch.setattr(monitoring_v3, "MetricServiceClient", FakeClient)
    args = ["--project", "p", "--month", "2026-10", "--out-dir", str(tmp_path), "--uptime-check-id", "labtrack-xyz"]
    assert sla.main(args) == 0
    assert any('metric.label."check_id"="labtrack-xyz"' in f for f in filters)
    report = (tmp_path / "2026-10.md").read_text(encoding="utf-8")
    assert "| Waktu henti | 5 menit |" in report
