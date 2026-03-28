output "web_app_id" {
  description = "Firebase Web App ID"
  value       = google_firebase_web_app.dashboard.app_id
}

output "api_key" {
  description = "Firebase API key (public, safe to expose in client code)"
  value       = data.google_firebase_web_app_config.dashboard.api_key
}

output "auth_domain" {
  description = "Firebase Auth domain"
  value       = "${var.project_id}.firebaseapp.com"
}

output "project_id" {
  description = "Firebase project ID"
  value       = var.project_id
}

output "messaging_sender_id" {
  description = "Firebase Cloud Messaging sender ID"
  value       = data.google_firebase_web_app_config.dashboard.messaging_sender_id
}

output "app_id" {
  description = "Firebase App ID"
  value       = google_firebase_web_app.dashboard.app_id
}

output "firebase_config_secret_id" {
  description = "Secret Manager secret ID containing the full Firebase web config"
  value       = google_secret_manager_secret.firebase_web_config.secret_id
}
