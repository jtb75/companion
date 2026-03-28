output "workload_identity_provider" {
  description = "Full resource name of the WIF provider (used in GitHub Actions auth step)"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "service_account_email" {
  description = "CI/CD service account email (used in GitHub Actions auth step)"
  value       = var.cicd_service_account_id
}
