locals {
  # Build the database URL for Cloud SQL via Unix socket
  database_url = "postgresql+asyncpg://${var.database_user}:${var.database_password}@/${var.database_name}?host=/cloudsql/${var.database_connection_name}"

  # Build the Redis URL (placeholder if Redis disabled — app handles gracefully)
  redis_url = var.redis_host != "" ? "redis://${var.redis_host}:${var.redis_port}/0" : "redis://disabled:6379/0"

  # Secrets that are created empty (values set manually or via CI)
  manual_secrets = {
    "firebase-credentials"    = "Firebase service account credentials JSON"
    "anthropic-api-key"       = "Anthropic API key for Claude"
    "openai-api-key"          = "OpenAI API key for embeddings"
    "gmail-oauth-credentials" = "Gmail OAuth credentials for email processing"
  }
}

# Database URL secret (automatically populated)
resource "google_secret_manager_secret" "database_url" {
  secret_id = "companion-${var.environment}-database-url"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.database_url
}

# Redis URL secret (automatically populated)
resource "google_secret_manager_secret" "redis_url" {
  secret_id = "companion-${var.environment}-redis-url"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "redis_url" {
  secret      = google_secret_manager_secret.redis_url.id
  secret_data = local.redis_url
}

# Manually managed secrets (created empty, values set via CI or console)
resource "google_secret_manager_secret" "manual" {
  for_each  = local.manual_secrets
  secret_id = "companion-${var.environment}-${each.key}"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}
