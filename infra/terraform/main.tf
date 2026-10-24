locals {
  service_name = "labtrack-api"
  run_sa       = "serviceAccount:${google_service_account.run.email}"

  apis = [
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
    "storage.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
  ]
}

resource "random_id" "suffix" {
  byte_length = 2
}

# ---------------------------------------------------------------------------
# APIs
# ---------------------------------------------------------------------------
resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# Artifact Registry: container images
# ---------------------------------------------------------------------------
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "labtrack"
  format        = "DOCKER"
  description   = "LabTrack container images"

  cleanup_policies {
    id     = "keep-recent"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------------------------
# Runtime identity (least privilege)
# ---------------------------------------------------------------------------
resource "google_service_account" "run" {
  account_id   = "labtrack-run"
  display_name = "LabTrack Cloud Run runtime"
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "run_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])
  project = var.project_id
  role    = each.value
  member  = local.run_sa
}

# Lets the runtime SA sign V4 URLs through the IAM signBlob API (it has no private key)
resource "google_service_account_iam_member" "run_self_sign" {
  service_account_id = google_service_account.run.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = local.run_sa
}

# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------
resource "random_password" "db" {
  length  = 24
  special = false
}

resource "random_password" "jwt" {
  length  = 48
  special = false
}

resource "random_password" "admin" {
  length  = 16
  special = false
}

locals {
  secret_values = {
    "db-password"    = random_password.db.result
    "jwt-secret"     = random_password.jwt.result
    "admin-password" = random_password.admin.result
  }
}

resource "google_secret_manager_secret" "s" {
  for_each  = toset(["db-password", "jwt-secret", "admin-password"])
  secret_id = "labtrack-${each.key}"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "s" {
  for_each    = google_secret_manager_secret.s
  secret      = each.value.id
  secret_data = local.secret_values[each.key]
}

resource "google_secret_manager_secret_iam_member" "run_access" {
  for_each  = google_secret_manager_secret.s
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = local.run_sa
}

# ---------------------------------------------------------------------------
# Cloud SQL for PostgreSQL
# ---------------------------------------------------------------------------
resource "google_sql_database_instance" "db" {
  # Suffix because Cloud SQL instance names cannot be reused for a week after deletion
  name                = "labtrack-db-${random_id.suffix.hex}"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = var.deletion_protection

  settings {
    edition           = "ENTERPRISE" # shared-core tiers are not available on Enterprise Plus
    tier              = var.db_tier
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 10
    disk_autoresize   = true

    backup_configuration {
      enabled    = true
      start_time = "18:00" # UTC, i.e. 01:00 WIB
      backup_retention_settings {
        retained_backups = 7
      }
    }

    # Public IP with no authorized networks: only the Cloud SQL Auth Proxy (IAM + TLS) can connect
    ip_configuration {
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }

    maintenance_window {
      day  = 7  # Sunday
      hour = 19 # UTC, i.e. 02:00 WIB Monday
    }

    insights_config {
      query_insights_enabled = true
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "app" {
  name     = "labtrack"
  instance = google_sql_database_instance.db.name
}

resource "google_sql_user" "app" {
  name     = "labtrack"
  instance = google_sql_database_instance.db.name
  password = random_password.db.result
}

# ---------------------------------------------------------------------------
# Cloud Storage: lab report PDFs (private, accessed through signed URLs)
# ---------------------------------------------------------------------------
resource "google_storage_bucket" "reports" {
  name                        = "${var.project_id}-labtrack-reports"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket_iam_member" "run_objects" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectAdmin"
  member = local.run_sa
}

# ---------------------------------------------------------------------------
# Cloud Run service
# ---------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "api" {
  name                = local.service_name
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account                  = google_service_account.run.email
    max_instance_request_concurrency = 40
    timeout                          = "30s"

    scaling {
      min_instance_count = 0 # scale to zero to stay inside the free tier
      max_instance_count = 3 # caps Cloud SQL connections at 3 x 7
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.db.connection_name]
      }
    }

    containers {
      image = var.image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "APP_ENV"
        value = "production"
      }
      env {
        name  = "INSTANCE_CONNECTION_NAME"
        value = google_sql_database_instance.db.connection_name
      }
      env {
        name  = "DB_USER"
        value = google_sql_user.app.name
      }
      env {
        name  = "DB_NAME"
        value = google_sql_database.app.name
      }
      env {
        name  = "GCS_BUCKET"
        value = google_storage_bucket.reports.name
      }
      env {
        name  = "BOOTSTRAP_ADMIN_EMAIL"
        value = var.admin_email
      }
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.s["db-password"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "JWT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.s["jwt-secret"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "BOOTSTRAP_ADMIN_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.s["admin-password"].secret_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        period_seconds    = 5
        timeout_seconds   = 3
        failure_threshold = 12
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        period_seconds  = 30
        timeout_seconds = 5
      }
    }
  }

  # GitHub Actions rolls out new images, so Terraform must not revert them
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_project_iam_member.run_roles,
    google_secret_manager_secret_iam_member.run_access,
    google_secret_manager_secret_version.s,
    google_sql_user.app,
  ]
}

# Public API endpoint. Authorization is enforced by the app (JWT).
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
