output "database_url_secret_id" {
  description = "Secret Manager secret ID for the database URL"
  value       = google_secret_manager_secret.database_url.secret_id
}

output "redis_url_secret_id" {
  description = "Secret Manager secret ID for the Redis URL"
  value       = google_secret_manager_secret.redis_url.secret_id
}

output "firebase_credentials_secret_id" {
  description = "Secret Manager secret ID for Firebase credentials"
  value       = google_secret_manager_secret.manual["firebase-credentials"].secret_id
}

output "anthropic_api_key_secret_id" {
  description = "Secret Manager secret ID for Anthropic API key"
  value       = google_secret_manager_secret.manual["anthropic-api-key"].secret_id
}

output "openai_api_key_secret_id" {
  description = "Secret Manager secret ID for OpenAI API key"
  value       = google_secret_manager_secret.manual["openai-api-key"].secret_id
}

output "gmail_oauth_credentials_secret_id" {
  description = "Secret Manager secret ID for Gmail OAuth credentials"
  value       = google_secret_manager_secret.manual["gmail-oauth-credentials"].secret_id
}

output "gmail_smtp_password_secret_id" {
  description = "Secret Manager secret ID for Gmail SMTP app password"
  value       = google_secret_manager_secret.manual["gmail-smtp-password"].secret_id
}

output "pipeline_api_key_secret_id" {
  description = "Secret Manager secret ID for internal pipeline API"
  value       = google_secret_manager_secret.manual["pipeline-api-key"].secret_id
}
