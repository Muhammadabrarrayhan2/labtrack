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
