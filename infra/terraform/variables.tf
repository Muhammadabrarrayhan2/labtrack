variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region. asia-southeast2 is Jakarta."
  type        = string
  default     = "asia-southeast2"
}

variable "image" {
  description = "Container image for the first deploy. Later deploys come from GitHub Actions."
  type        = string
}

variable "github_repository" {
  description = "GitHub repo allowed to deploy, in owner/name form"
  type        = string
}

variable "db_tier" {
  description = "Cloud SQL machine tier. db-f1-micro is the cheapest shared-core tier."
  type        = string
  default     = "db-f1-micro"
}

variable "admin_email" {
  description = "Email of the bootstrap admin account"
  type        = string
  default     = "admin@labtrack.dev"
}

variable "alert_email" {
  description = "Email that receives uptime alerts. Leave empty to skip the notification channel."
  type        = string
  default     = ""
}

variable "deletion_protection" {
  description = "Protect Cloud SQL from terraform destroy. Keep false for a demo project."
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# Optional ops VM (iaas.tf)
# ---------------------------------------------------------------------------
variable "enable_ops_vm" {
  description = <<-EOT
    Create the labtrack-ops Compute Engine VM (e2-micro, Debian 12, no external IP) with
    Cloud NAT, IAP SSH, a nightly pg_dump to a backup bucket and daily boot disk snapshots.
    Estimated cost outside the free tier: about US$7-9/month for the VM and 10 GB standard
    disk, about US$1/month for Cloud NAT plus US$0.045/GB processed, and a few cents for
    snapshots and dumps. The e2-micro free tier only applies in us-west1, us-central1 and
    us-east1 (set ops_vm_region to one of those to use it). Stop the VM with
    scripts/ops/vm-start-stop.sh when it is not needed.
  EOT
  type        = bool
  default     = false
}

variable "ops_vm_region" {
  description = "Region for the ops VM, subnet and NAT. Empty means var.region. Use us-central1 for the e2-micro free tier."
  type        = string
  default     = ""
}

variable "ops_vm_zone" {
  description = "Zone for the ops VM. Empty means <ops region>-a."
  type        = string
  default     = ""
}

variable "ops_vm_machine_type" {
  description = "Machine type for the ops VM"
  type        = string
  default     = "e2-micro"
}

variable "backup_retention_days" {
  description = "Days to keep pg_dump files in the backup bucket before lifecycle deletion"
  type        = number
  default     = 30
}

variable "cloud_sql_proxy_version" {
  description = "Cloud SQL Auth Proxy v2 release installed on the ops VM"
  type        = string
  default     = "2.18.0"
}

# ---------------------------------------------------------------------------
# SLOs and alerting (slo.tf). No cost: built-in metrics only.
# ---------------------------------------------------------------------------
variable "slo_availability_goal" {
  description = "Availability SLO goal as a fraction of non-5xx requests over 30 days"
  type        = number
  default     = 0.995
}

variable "slo_latency_threshold_ms" {
  description = "Latency SLO threshold in ms; 95% of requests must be faster"
  type        = number
  default     = 800
}

variable "sql_connection_alert_threshold" {
  description = "Alert when PostgreSQL connections exceed this (db-f1-micro max_connections is 25)"
  type        = number
  default     = 20
}
