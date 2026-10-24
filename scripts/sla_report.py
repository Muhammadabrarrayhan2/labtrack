"""Monthly SLA report for LabTrack from Cloud Monitoring.

Queries run.googleapis.com/request_count and request_latencies for the Cloud Run
service over one calendar month (WIB, UTC+7) and writes docs/laporan-sla/YYYY-MM.md
with availability, p95 latency, request totals, 5xx count, error budget consumed and
whether the SLA was met.

Usage:
    pip install -r requirements-dev.txt
    gcloud auth application-default login
    python scripts/sla_report.py --project labtrack-123456 --month 2026-10
    python scripts/sla_report.py --project labtrack-123456 --start 2026-10-01 --end 2026-10-27

The calculation functions take plain time series objects, so tests can feed them
mocked data without GCP access (tests/test_sla_report.py).
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

WIB = timezone(timedelta(hours=7))
DEFAULT_SERVICE = "labtrack-api"
REQUEST_COUNT = "run.googleapis.com/request_count"
REQUEST_LATENCIES = "run.googleapis.com/request_latencies"


# ---------------------------------------------------------------------------
# Period handling
# ---------------------------------------------------------------------------
def month_range(month: str) -> tuple[datetime, datetime]:
    """'2026-10' -> [2026-10-01 00:00 WIB, 2026-11-01 00:00 WIB)."""
    year, mon = (int(x) for x in month.split("-"))
    start = datetime(year, mon, 1, tzinfo=WIB)
    end = datetime(year + (mon == 12), mon % 12 + 1, 1, tzinfo=WIB)
    return start, end


def date_range(start: str, end: str) -> tuple[datetime, datetime]:
    """Inclusive dates in WIB: '2026-10-01'..'2026-10-27' -> [10-01 00:00, 10-28 00:00)."""
    s = datetime.combine(date.fromisoformat(start), datetime.min.time(), WIB)
    e = datetime.combine(date.fromisoformat(end) + timedelta(days=1), datetime.min.time(), WIB)
    if e <= s:
        raise ValueError("end must not be before start")
    return s, e


def previous_month(today: date) -> str:
    first = today.replace(day=1)
    last_month = first - timedelta(days=1)
    return f"{last_month.year:04d}-{last_month.month:02d}"


# ---------------------------------------------------------------------------
# Calculation (pure, unit tested)
# ---------------------------------------------------------------------------
def count_requests(series) -> tuple[int, int]:
    """Sum request_count points grouped by response_code_class. Returns (total, 5xx)."""
    total = bad = 0
    for ts in series:
        n = sum(int(p.value.int64_value) for p in ts.points)
        total += n
        if ts.metric.labels.get("response_code_class") == "5xx":
            bad += n
    return total, bad


def bucket_bounds(options, n_buckets: int) -> list[tuple[float, float]]:
    """[lower, upper) bounds for each bucket, including underflow and overflow buckets."""
    exp, lin = options.exponential_buckets, options.linear_buckets
    if exp.num_finite_buckets:
        edges = [exp.scale * exp.growth_factor**i for i in range(exp.num_finite_buckets + 1)]
    elif lin.num_finite_buckets:
        edges = [lin.offset + lin.width * i for i in range(lin.num_finite_buckets + 1)]
    else:
        edges = list(options.explicit_buckets.bounds)
    lowers = [0.0, *edges]
    uppers = [*edges, math.inf]
    return list(zip(lowers, uppers))[:n_buckets]


def merge_distributions(series) -> tuple[object | None, list[int]]:
    """Add up bucket counts of every distribution point. All points share bucket options."""
    options, counts = None, []
    for ts in series:
        for p in ts.points:
            dist = p.value.distribution_value
            if options is None:
                options = dist.bucket_options
            bc = list(dist.bucket_counts)
            if len(bc) > len(counts):
                counts.extend([0] * (len(bc) - len(counts)))
            for i, c in enumerate(bc):
                counts[i] += int(c)
    return options, counts


def percentile(options, counts: list[int], q: float) -> float | None:
    """q-th percentile (0..100) from bucket counts, linear interpolation inside a bucket."""
    total = sum(counts)
    if not total or options is None:
        return None
    rank = q / 100 * total
    seen = 0
    for (lo, hi), c in zip(bucket_bounds(options, len(counts)), counts):
        if c and seen + c >= rank:
            if math.isinf(hi):
                return lo
            return lo + (hi - lo) * (rank - seen) / c
        seen += c
    return None


def fraction_below(options, counts: list[int], threshold: float) -> float | None:
    """Share of requests faster than threshold, assuming uniform spread inside a bucket."""
    total = sum(counts)
    if not total or options is None:
        return None
    fast = 0.0
    for (lo, hi), c in zip(bucket_bounds(options, len(counts)), counts):
        if hi <= threshold:
            fast += c
        elif lo < threshold and not math.isinf(hi):
            fast += c * (threshold - lo) / (hi - lo)
    return fast / total


@dataclass
class SlaResult:
    start: datetime
    end: datetime
    total_requests: int
    errors_5xx: int
    availability: float | None
    p95_ms: float | None
    fast_fraction: float | None
    availability_target: float
    latency_target_ms: float
    budget_requests: float
    budget_consumed: float | None
    allowed_downtime_min: float

    @property
    def availability_met(self) -> bool | None:
        return None if self.availability is None else self.availability >= self.availability_target

    @property
    def latency_met(self) -> bool | None:
        return None if self.p95_ms is None else self.p95_ms < self.latency_target_ms

    @property
    def sla_met(self) -> bool | None:
        if self.availability_met is None or self.latency_met is None:
            return None
        return self.availability_met and self.latency_met


def evaluate(
    count_series,
    latency_series,
    start: datetime,
    end: datetime,
    availability_target: float = 0.995,
    latency_target_ms: float = 800.0,
) -> SlaResult:
    total, bad = count_requests(count_series)
    options, counts = merge_distributions(latency_series)
    allowed_fraction = 1 - availability_target
    budget = total * allowed_fraction
    return SlaResult(
        start=start,
        end=end,
        total_requests=total,
        errors_5xx=bad,
        availability=(1 - bad / total) if total else None,
        p95_ms=percentile(options, counts, 95),
        fast_fraction=fraction_below(options, counts, latency_target_ms),
        availability_target=availability_target,
        latency_target_ms=latency_target_ms,
        budget_requests=budget,
        budget_consumed=(bad / budget) if budget else None,
        allowed_downtime_min=(end - start).total_seconds() / 60 * allowed_fraction,
    )


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def _pct(x: float | None, digits: int = 3) -> str:
    return "tidak ada data" if x is None else f"{x * 100:.{digits}f}%"


def _verdict(ok: bool | None) -> str:
    return {True: "Tercapai", False: "Tidak tercapai", None: "Tidak dapat dinilai (tidak ada trafik)"}[ok]


def render_markdown(r: SlaResult, project: str, service: str) -> str:
    period_end = r.end - timedelta(seconds=1)
    p95 = "tidak ada data" if r.p95_ms is None else f"{r.p95_ms:.0f} ms"
    lines = [
        f"# Laporan SLA LabTrack {r.start:%Y-%m}",
        "",
        f"- Proyek: `{project}`, layanan Cloud Run `{service}`",
        f"- Periode: {r.start:%Y-%m-%d %H:%M} sampai {period_end:%Y-%m-%d %H:%M} WIB",
        f"- Dibuat: {datetime.now(WIB):%Y-%m-%d %H:%M} WIB oleh `scripts/sla_report.py` dari Cloud Monitoring",
        "",
        "## Ringkasan",
        "",
        "| Indikator | Target | Realisasi | Status |",
        "|---|---|---|---|",
        f"| Ketersediaan (permintaan non-5xx) | {_pct(r.availability_target, 1)} | {_pct(r.availability)} | {_verdict(r.availability_met)} |",
        f"| Latensi p95 | < {r.latency_target_ms:.0f} ms | {p95} | {_verdict(r.latency_met)} |",
        f"| Permintaan di bawah {r.latency_target_ms:.0f} ms | 95% | {_pct(r.fast_fraction, 2)} | |",
        "",
        f"**Status SLA bulan ini: {_verdict(r.sla_met)}**",
        "",
        "## Rincian",
        "",
        "| Besaran | Nilai |",
        "|---|---|",
        f"| Total permintaan | {r.total_requests:,} |",
        f"| Permintaan 5xx | {r.errors_5xx:,} |",
        f"| Anggaran galat (permintaan) | {r.budget_requests:,.1f} |",
        f"| Anggaran galat terpakai | {_pct(r.budget_consumed, 1)} |",
        f"| Batas waktu henti setara (berbasis waktu) | {r.allowed_downtime_min:.1f} menit |",
        "",
        "## Insiden pada periode ini",
        "",
        "> [ISI MANUAL: daftar insiden dari GitHub Issues berlabel `insiden`, dengan durasi dan dampak terhadap SLI]",
        "",
        "## Tindak lanjut",
        "",
        "> [ISI MANUAL: rencana perbaikan bila SLA tidak tercapai atau anggaran galat terpakai di atas 50%]",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cloud Monitoring access
# ---------------------------------------------------------------------------
def fetch_series(client, project: str, metric: str, service: str, start: datetime, end: datetime, group_by: list[str]):
    from google.cloud import monitoring_v3

    interval = monitoring_v3.TimeInterval(
        start_time={"seconds": int(start.timestamp())},
        end_time={"seconds": int(end.timestamp())},
    )
    aggregation = monitoring_v3.Aggregation(
        alignment_period={"seconds": 3600},
        per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_DELTA,
        cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
        group_by_fields=group_by,
    )
    return list(
        client.list_time_series(
            request={
                "name": f"projects/{project}",
                "filter": (
                    f'metric.type="{metric}" AND resource.type="cloud_run_revision" '
                    f'AND resource.label."service_name"="{service}"'
                ),
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": aggregation,
            }
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", default=os.environ.get("PROJECT_ID"), help="GCP project (default $PROJECT_ID)")
    parser.add_argument("--service", default=DEFAULT_SERVICE)
    parser.add_argument("--month", help="YYYY-MM in WIB (default: previous month)")
    parser.add_argument("--start", help="YYYY-MM-DD, inclusive, use with --end instead of --month")
    parser.add_argument("--end", help="YYYY-MM-DD, inclusive")
    parser.add_argument("--availability-target", type=float, default=0.995)
    parser.add_argument("--latency-target-ms", type=float, default=800.0)
    parser.add_argument("--out-dir", default="docs/laporan-sla")
    args = parser.parse_args(argv)

    if not args.project:
        parser.error("--project or PROJECT_ID is required")
    if bool(args.start) != bool(args.end):
        parser.error("--start and --end go together")
    if args.start:
        start, end = date_range(args.start, args.end)
        name = f"{args.start}_{args.end}"
    else:
        month = args.month or previous_month(datetime.now(WIB).date())
        start, end = month_range(month)
        name = month

    from google.cloud import monitoring_v3

    client = monitoring_v3.MetricServiceClient()
    counts = fetch_series(client, args.project, REQUEST_COUNT, args.service, start, end, ["metric.label.response_code_class"])
    latencies = fetch_series(client, args.project, REQUEST_LATENCIES, args.service, start, end, [])
    result = evaluate(counts, latencies, start, end, args.availability_target, args.latency_target_ms)

    out = Path(args.out_dir) / f"{name}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(result, args.project, args.service), encoding="utf-8")
    print(f"Wrote {out}: availability={_pct(result.availability)} p95={result.p95_ms} SLA={_verdict(result.sla_met)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
