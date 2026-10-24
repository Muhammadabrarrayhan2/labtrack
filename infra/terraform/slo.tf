# Service Level Objectives and SLA alerting for labtrack-api.
# SLO definitions match docs/05-sla-dan-pemantauan.md. Everything here uses built-in
# Cloud Run and Cloud SQL metrics, so it adds no cost.

locals {
  run_filter = "resource.type=\"cloud_run_revision\" AND resource.label.\"service_name\"=\"${local.service_name}\""
  sql_filter = "resource.type=\"cloudsql_database\" AND resource.label.\"database_id\"=\"${var.project_id}:${google_sql_database_instance.db.name}\""

  request_count_filter = "metric.type=\"run.googleapis.com/request_count\" AND ${local.run_filter}"
  request_5xx_filter   = "${local.request_count_filter} AND metric.label.\"response_code_class\"=\"5xx\""

  sla_alert_count = var.enable_sla_alerts ? 1 : 0
}

resource "google_monitoring_custom_service" "api" {
  service_id   = local.service_name
  display_name = "LabTrack API"

  telemetry {
    resource_name = "//run.googleapis.com/projects/${var.project_id}/locations/${var.region}/services/${local.service_name}"
  }

  depends_on = [google_project_service.apis]
}

# Availability: 99.5% of requests over a rolling 30 days are not 5xx.
# good = 2xx/3xx/4xx is expressed as total minus bad (5xx); 4xx are client errors
# (bad token, validation) and do not count against the service.
resource "google_monitoring_slo" "availability" {
  service             = google_monitoring_custom_service.api.service_id
  slo_id              = "availability-30d"
  display_name        = "Availability 99.5% (non-5xx requests, 30 day rolling)"
  goal                = var.slo_availability_goal
  rolling_period_days = 30

  request_based_sli {
    good_total_ratio {
      total_service_filter = local.request_count_filter
      bad_service_filter   = local.request_5xx_filter
    }
  }
}

# Latency: 95% of requests complete in under 800 ms over a rolling 30 days
resource "google_monitoring_slo" "latency" {
  service             = google_monitoring_custom_service.api.service_id
  slo_id              = "latency-800ms-30d"
  display_name        = "Latency 95% of requests < ${var.slo_latency_threshold_ms} ms (30 day rolling)"
  goal                = 0.95
  rolling_period_days = 30

  request_based_sli {
    distribution_cut {
      distribution_filter = "metric.type=\"run.googleapis.com/request_latencies\" AND ${local.run_filter}"
      range {
        max = var.slo_latency_threshold_ms # request_latencies is in milliseconds
      }
    }
  }
}

# ---------------------------------------------------------------------------
# Alert policies, gated by var.enable_sla_alerts (alert conditions may be billed)
# ---------------------------------------------------------------------------

# Fast burn: at 10x the budget is gone in 3 days (30 days / 10). For a 99.5% goal this
# fires when more than 5% of requests in the last hour were 5xx.
resource "google_monitoring_alert_policy" "slo_fast_burn" {
  count        = local.sla_alert_count
  display_name = "LabTrack SLO: availability fast burn (10x over 1h)"
  combiner     = "OR"
  severity     = "CRITICAL"

  conditions {
    display_name = "Error budget burn rate > 10 over 1 hour"
    condition_threshold {
      filter          = "select_slo_burn_rate(\"${google_monitoring_slo.availability.name}\", \"3600s\")"
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      duration        = "0s"
    }
  }

  notification_channels = google_monitoring_notification_channel.email[*].id

  documentation {
    content   = "The availability SLO is burning error budget 10x faster than allowed. Follow docs/06-sop-dukungan-teknis.md, severity P1/P2. Check Cloud Run revisions, recent deploys and /health."
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_alert_policy" "error_ratio" {
  count        = local.sla_alert_count
  display_name = "LabTrack API: 5xx ratio > 5% for 5 minutes"
  combiner     = "OR"
  severity     = "ERROR"

  conditions {
    display_name = "5xx / all requests > 0.05"
    condition_threshold {
      filter             = local.request_5xx_filter
      denominator_filter = local.request_count_filter
      comparison         = "COMPARISON_GT"
      threshold_value    = 0.05
      duration           = "300s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
      denominator_aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = google_monitoring_notification_channel.email[*].id

  documentation {
    content   = "More than 5% of LabTrack requests returned 5xx for 5 minutes. Query Logs Explorer for severity>=ERROR and the request_id values. See docs/06-sop-dukungan-teknis.md."
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_alert_policy" "sql_cpu" {
  count        = local.sla_alert_count
  display_name = "LabTrack Cloud SQL: CPU > 80% for 10 minutes"
  combiner     = "OR"
  severity     = "WARNING"

  conditions {
    display_name = "cpu/utilization > 0.8"
    condition_threshold {
      filter          = "metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\" AND ${local.sql_filter}"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "600s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = google_monitoring_notification_channel.email[*].id

  documentation {
    content   = "Cloud SQL CPU has been above 80% for 10 minutes. Check Query Insights for slow queries; db-f1-micro has a shared vCPU. See docs/03-kebutuhan-perangkat-keras.md for sizing."
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_alert_policy" "sql_disk" {
  count        = local.sla_alert_count
  display_name = "LabTrack Cloud SQL: disk utilization > 80%"
  combiner     = "OR"
  severity     = "WARNING"

  conditions {
    display_name = "disk/utilization > 0.8"
    condition_threshold {
      filter          = "metric.type=\"cloudsql.googleapis.com/database/disk/utilization\" AND ${local.sql_filter}"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "300s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = google_monitoring_notification_channel.email[*].id

  documentation {
    content   = "Cloud SQL disk is above 80%. Storage auto-resize is on, so this mostly signals unexpected growth. Check table sizes before the disk grows further."
    mime_type = "text/markdown"
  }
}

resource "google_monitoring_alert_policy" "sql_connections" {
  count        = local.sla_alert_count
  display_name = "LabTrack Cloud SQL: connections near limit"
  combiner     = "OR"
  severity     = "WARNING"

  conditions {
    display_name = "num_backends > ${var.sql_connection_alert_threshold}"
    condition_threshold {
      filter          = "metric.type=\"cloudsql.googleapis.com/database/postgresql/num_backends\" AND ${local.sql_filter}"
      comparison      = "COMPARISON_GT"
      threshold_value = var.sql_connection_alert_threshold
      duration        = "120s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MAX"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields      = ["resource.label.database_id"]
      }
    }
  }

  notification_channels = google_monitoring_notification_channel.email[*].id

  documentation {
    content   = "PostgreSQL connections are close to max_connections (25 on db-f1-micro). Budget: max_instances x (pool_size + max_overflow) = 3 x 7 = 21. Check for a revision rollout overlap or a raised max instances."
    mime_type = "text/markdown"
  }
}
