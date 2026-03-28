# Service account for the backend
resource "google_service_account" "backend" {
  account_id   = "companion-${var.environment}-backend"
  display_name = "Companion ${var.environment} Backend Service Account"
  project      = var.project_id
}

locals {
  backend_roles = [
    "roles/cloudsql.client",
    "roles/storage.objectAdmin",
    "roles/pubsub.publisher",
    "roles/pubsub.subscriber",
    "roles/secretmanager.secretAccessor",
    "roles/documentai.apiUser",
  ]
}

resource "google_project_iam_member" "backend_roles" {
  for_each = toset(local.backend_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Backend Cloud Run service
resource "google_cloud_run_v2_service" "backend" {
  name     = "companion-${var.environment}-backend"
  project  = var.project_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.backend.email

    scaling {
      min_instance_count = var.backend_min_instances
      max_instance_count = var.backend_max_instances
    }

    timeout = "300s"

    max_instance_request_concurrency = 80

    vpc_access {
      connector = var.vpc_connector_id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [var.database_connection_name]
      }
    }

    containers {
      image = var.backend_image

      resources {
        limits = {
          cpu    = var.backend_cpu
          memory = var.backend_memory
        }
        cpu_idle          = var.backend_min_instances == 0 ? true : false
        startup_cpu_boost = true
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      # Environment variables
      env {
        name  = "COMPANION_ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "COMPANION_GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "COMPANION_GCS_BUCKET_DOCUMENTS"
        value = var.documents_bucket
      }

      # Secret environment variables
      env {
        name = "COMPANION_REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = var.redis_url_secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "COMPANION_DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = var.database_url_secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "COMPANION_ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.anthropic_api_key_secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "COMPANION_OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.openai_api_key_secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "COMPANION_FIREBASE_CREDENTIALS"
        value_source {
          secret_key_ref {
            secret  = var.firebase_credentials_secret_id
            version = "latest"
          }
        }
      }

      ports {
        container_port = 8080
      }

      # Health check
      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 0
        period_seconds        = 10
        failure_threshold     = 5
        timeout_seconds       = 5
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        period_seconds    = 30
        failure_threshold = 3
        timeout_seconds   = 5
      }
    }
  }

  depends_on = [
    google_project_iam_member.backend_roles,
  ]
}

# Allow unauthenticated access to backend (auth handled at app level)
resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Web dashboard Cloud Run service
resource "google_cloud_run_v2_service" "web" {
  name     = "companion-${var.environment}-web"
  project  = var.project_id
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = var.web_min_instances
      max_instance_count = 5
    }

    timeout = "60s"

    containers {
      image = var.web_image

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      ports {
        container_port = 80
      }

      # Pass backend URL so the web app knows where to send API requests
      env {
        name  = "COMPANION_BACKEND_URL"
        value = google_cloud_run_v2_service.backend.uri
      }

      env {
        name  = "COMPANION_ENVIRONMENT"
        value = var.environment
      }

      startup_probe {
        http_get {
          path = "/"
          port = 80
        }
        initial_delay_seconds = 0
        period_seconds        = 5
        failure_threshold     = 3
        timeout_seconds       = 3
      }
    }
  }
}

# Allow unauthenticated access to web dashboard
resource "google_cloud_run_v2_service_iam_member" "web_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.web.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

data "google_project" "current" {
  project_id = var.project_id
}
