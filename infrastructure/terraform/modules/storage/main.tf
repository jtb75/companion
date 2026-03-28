# GCS bucket for document storage
resource "google_storage_bucket" "documents" {
  name                        = "companion-${var.environment}-documents"
  project                     = var.project_id
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = var.environment == "staging" ? true : false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 365
    }
    action {
      type = "Delete"
    }
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  # Using Google-managed encryption key by default.
  # To use CMEK, uncomment and configure:
  # encryption {
  #   default_kms_key_name = google_kms_crypto_key.documents.id
  # }
}

# Artifact Registry Docker repository
resource "google_artifact_registry_repository" "docker" {
  provider      = google-beta
  project       = var.project_id
  location      = var.region
  repository_id = "companion-${var.environment}"
  format        = "DOCKER"
  description   = "Docker images for Companion ${var.environment}"

  cleanup_policies {
    id     = "keep-last-10"
    action = "KEEP"

    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policy_dry_run = false
}
