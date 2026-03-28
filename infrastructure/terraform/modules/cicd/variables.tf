variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository in owner/repo format (e.g., jtb75/companion)"
  type        = string
}

variable "cicd_service_account_id" {
  description = "Full resource ID of the CI/CD service account"
  type        = string
}
