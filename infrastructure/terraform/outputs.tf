output "backend_url" {
  description = "URL of the backend Cloud Run service"
  value       = module.compute.backend_url
}

output "web_url" {
  description = "URL of the web dashboard Cloud Run service"
  value       = module.compute.web_url
}

output "database_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = module.database.connection_name
}

output "redis_host" {
  description = "Memorystore Redis host"
  value       = module.database.redis_host
}

output "documents_bucket_name" {
  description = "GCS bucket name for document storage"
  value       = module.storage.documents_bucket_name
}

output "artifact_registry_repo" {
  description = "Artifact Registry Docker repository path"
  value       = module.storage.artifact_registry_repo
}

output "wif_provider" {
  description = "Workload Identity Federation provider (for GitHub Actions auth)"
  value       = module.cicd.workload_identity_provider
}

output "cicd_service_account_email" {
  description = "CI/CD service account email (for GitHub Actions auth)"
  value       = data.google_service_account.cicd.email
}
