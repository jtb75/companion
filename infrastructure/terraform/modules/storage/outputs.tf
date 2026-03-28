output "documents_bucket_name" {
  description = "GCS bucket name for documents"
  value       = google_storage_bucket.documents.name
}

output "artifact_registry_repo" {
  description = "Full Artifact Registry repository path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}
