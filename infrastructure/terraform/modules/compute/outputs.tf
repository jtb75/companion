output "backend_service_name" {
  description = "Backend Cloud Run service name"
  value       = google_cloud_run_v2_service.backend.name
}

output "backend_url" {
  description = "Backend Cloud Run service URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "web_service_name" {
  description = "Web dashboard Cloud Run service name"
  value       = google_cloud_run_v2_service.web.name
}

output "web_url" {
  description = "Web dashboard Cloud Run service URL"
  value       = google_cloud_run_v2_service.web.uri
}
