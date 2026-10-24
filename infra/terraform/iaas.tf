# Optional IaaS component: a small ops VM that takes a nightly logical backup (pg_dump)
# of Cloud SQL and uploads it to a private bucket. Everything here is gated by
# var.enable_ops_vm so the default stack stays PaaS only and free of VM costs.

locals {
  ops_count  = var.enable_ops_vm ? 1 : 0
  ops_region = var.ops_vm_region == "" ? var.region : var.ops_vm_region
  ops_zone   = var.ops_vm_zone == "" ? "${local.ops_region}-a" : var.ops_vm_zone
  ops_name   = "labtrack-ops"
}

resource "google_project_service" "ops_apis" {
  for_each           = var.enable_ops_vm ? toset(["compute.googleapis.com", "iap.googleapis.com"]) : toset([])
  service            = each.value
  disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# Network: dedicated VPC, no external IPs, egress through Cloud NAT
# ---------------------------------------------------------------------------
resource "google_compute_network" "ops" {
  count                   = local.ops_count
  name                    = "labtrack-ops-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.ops_apis]
}

resource "google_compute_subnetwork" "ops" {
  count         = local.ops_count
  name          = "labtrack-ops-subnet"
  region        = local.ops_region
  network       = google_compute_network.ops[0].id
  ip_cidr_range = "10.10.0.0/24"
  # Reach Google APIs (Cloud Storage, Secret Manager, Logging) over internal routing
  private_ip_google_access = true
}

resource "google_compute_router" "ops" {
  count   = local.ops_count
  name    = "labtrack-ops-router"
  region  = local.ops_region
  network = google_compute_network.ops[0].id
}

# Outbound internet for apt, the Ops Agent repo and the Cloud SQL public IP
resource "google_compute_router_nat" "ops" {
  count                              = local.ops_count
  name                               = "labtrack-ops-nat"
  router                             = google_compute_router.ops[0].name
  region                             = local.ops_region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# SSH only from Google's IAP TCP forwarding range, never from the internet
resource "google_compute_firewall" "ops_iap_ssh" {
  count         = local.ops_count
  name          = "labtrack-ops-allow-iap-ssh"
  network       = google_compute_network.ops[0].id
  direction     = "INGRESS"
  source_ranges = ["35.235.240.0/20"]
  target_tags   = [local.ops_name]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

# ---------------------------------------------------------------------------
# Identity: dedicated service account with only what the backup job needs
# ---------------------------------------------------------------------------
resource "google_service_account" "ops" {
  count        = local.ops_count
  account_id   = local.ops_name
  display_name = "LabTrack ops VM (nightly pg_dump)"
  depends_on   = [google_project_service.apis]
}

resource "google_project_iam_member" "ops_roles" {
  for_each = var.enable_ops_vm ? toset([
    "roles/cloudsql.client",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ]) : toset([])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.ops[0].email}"
}

# pg_dump logs in as the app's database user, so the VM reads that one secret only
resource "google_secret_manager_secret_iam_member" "ops_db_password" {
  count     = local.ops_count
  secret_id = google_secret_manager_secret.s["db-password"].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.ops[0].email}"
}

# ---------------------------------------------------------------------------
# Backup bucket: write-only for the VM, old dumps expire automatically
# ---------------------------------------------------------------------------
resource "google_storage_bucket" "backups" {
  count                       = local.ops_count
  name                        = "${var.project_id}-labtrack-backups"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  lifecycle_rule {
    condition {
      age = var.backup_retention_days
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.apis]
}

# objectCreator can add new dumps but cannot read, overwrite or delete existing ones
resource "google_storage_bucket_iam_member" "ops_backup_writer" {
  count  = local.ops_count
  bucket = google_storage_bucket.backups[0].name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.ops[0].email}"
}

# ---------------------------------------------------------------------------
# Boot disk with a daily snapshot schedule (7 day retention)
# ---------------------------------------------------------------------------
resource "google_compute_resource_policy" "ops_daily_snapshot" {
  count  = local.ops_count
  name   = "labtrack-ops-daily-snapshot"
  region = local.ops_region

  snapshot_schedule_policy {
    schedule {
      daily_schedule {
        days_in_cycle = 1
        start_time    = "20:00" # UTC, i.e. 03:00 WIB, after the 02:30 WIB pg_dump
      }
    }
    retention_policy {
      max_retention_days    = 7
      on_source_disk_delete = "KEEP_AUTO_SNAPSHOTS"
    }
    snapshot_properties {
      storage_locations = [local.ops_region]
      labels = {
        app = "labtrack"
      }
    }
  }

  depends_on = [google_project_service.ops_apis]
}

resource "google_compute_disk" "ops_boot" {
  count = local.ops_count
  name  = "${local.ops_name}-boot"
  zone  = local.ops_zone
  type  = "pd-standard"
  size  = 10
  image = "debian-cloud/debian-12"
  labels = {
    app = "labtrack"
  }
  depends_on = [google_project_service.ops_apis]
}

resource "google_compute_disk_resource_policy_attachment" "ops_boot_snapshot" {
  count = local.ops_count
  name  = google_compute_resource_policy.ops_daily_snapshot[0].name
  disk  = google_compute_disk.ops_boot[0].name
  zone  = local.ops_zone
}

# ---------------------------------------------------------------------------
# The VM
# ---------------------------------------------------------------------------
resource "google_compute_instance" "ops" {
  count                     = local.ops_count
  name                      = local.ops_name
  zone                      = local.ops_zone
  machine_type              = var.ops_vm_machine_type
  tags                      = [local.ops_name]
  allow_stopping_for_update = true

  labels = {
    app = "labtrack"
  }

  boot_disk {
    source      = google_compute_disk.ops_boot[0].id
    auto_delete = false # the disk and its snapshots outlive a VM rebuild
  }

  # No access_config block, so the VM has no external IP
  network_interface {
    subnetwork = google_compute_subnetwork.ops[0].id
  }

  service_account {
    email  = google_service_account.ops[0].email
    scopes = ["cloud-platform"] # actual permissions come from the IAM roles above
  }

  shielded_instance_config {
    enable_secure_boot          = true
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }

  metadata = {
    enable-oslogin = "TRUE"
  }

  metadata_startup_script = templatefile("${path.module}/templates/ops-startup.sh.tftpl", {
    connection_name = google_sql_database_instance.db.connection_name
    db_user         = google_sql_user.app.name
    db_name         = google_sql_database.app.name
    db_secret       = google_secret_manager_secret.s["db-password"].secret_id
    backup_bucket   = google_storage_bucket.backups[0].name
    proxy_version   = var.cloud_sql_proxy_version
  })

  depends_on = [
    google_project_iam_member.ops_roles,
    google_compute_router_nat.ops,
  ]
}
