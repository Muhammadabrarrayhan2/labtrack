output "api_url" {
  description = "Public URL of the LabTrack API"
  value       = google_cloud_run_v2_service.api.uri
}

output "image_repository" {
  description = "Push images here"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}"
}

output "sql_connection_name" {
  value = google_sql_database_instance.db.connection_name
}

output "reports_bucket" {
  value = google_storage_bucket.reports.name
}

output "runtime_service_account" {
  value = google_service_account.run.email
}

# Values for GitHub repository variables (Settings > Secrets and variables > Actions > Variables)
output "github_vars" {
  value = {
    GCP_PROJECT_ID   = var.project_id
    GCP_REGION       = var.region
    GCP_WIF_PROVIDER = google_iam_workload_identity_pool_provider.github.name
    GCP_DEPLOYER_SA  = google_service_account.deployer.email
  }
}

output "admin_login" {
  description = "Admin email and the command that prints its password"
  value = {
    email            = var.admin_email
    password_command = "gcloud secrets versions access latest --secret=labtrack-admin-password --project=${var.project_id}"
  }
}
