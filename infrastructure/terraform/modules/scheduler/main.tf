# Cloud Scheduler jobs for periodic workers
# Calls internal API endpoints authenticated via X-Pipeline-Key header.

data "google_secret_manager_secret_version" "pipeline_api_key" {
  secret  = var.pipeline_api_key_secret_id
  project = var.project_id
}

resource "google_cloud_scheduler_job" "morning_checkin" {
  name      = "companion-${var.environment}-morning-checkin"
  project   = var.project_id
  region    = var.region
  schedule  = "* * * * *"
  time_zone = "UTC"

  description = "Trigger morning check-in worker every minute"

  http_target {
    uri         = "${var.backend_url}/api/internal/workers/morning-checkin"
    http_method = "POST"
    headers = {
      "X-Pipeline-Key" = data.google_secret_manager_secret_version.pipeline_api_key.secret_data
      "Content-Type"   = "application/json"
    }
  }

  retry_config {
    retry_count          = 1
    max_retry_duration   = "60s"
    min_backoff_duration = "5s"
    max_backoff_duration = "30s"
  }
}

resource "google_cloud_scheduler_job" "medication_reminders" {
  name      = "companion-${var.environment}-medication-reminders"
  project   = var.project_id
  region    = var.region
  schedule  = "* * * * *"
  time_zone = "UTC"

  description = "Trigger medication reminder worker every minute"

  http_target {
    uri         = "${var.backend_url}/api/internal/workers/medication-reminders"
    http_method = "POST"
    headers = {
      "X-Pipeline-Key" = data.google_secret_manager_secret_version.pipeline_api_key.secret_data
      "Content-Type"   = "application/json"
    }
  }

  retry_config {
    retry_count          = 1
    max_retry_duration   = "60s"
    min_backoff_duration = "5s"
    max_backoff_duration = "30s"
  }
}
