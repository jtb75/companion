# KMS keyring and key for document encryption (CMEK)
resource "google_kms_key_ring" "companion" {
  name     = "companion-${var.environment}"
  project  = var.project_id
  location = var.region
}

resource "google_kms_crypto_key" "documents" {
  name            = "companion-${var.environment}-documents"
  key_ring        = google_kms_key_ring.companion.id
  rotation_period = "7776000s" # 90 days

  lifecycle {
    prevent_destroy = true
  }
}

# Grant GCS service agent permission to use the KMS key
data "google_storage_project_service_account" "gcs" {
  project = var.project_id
}

resource "google_kms_crypto_key_iam_member" "gcs_encrypt" {
  crypto_key_id = google_kms_crypto_key.documents.id
  role          = "roles/cloudkms.cryptoKeyEncrypterDecrypter"
  member        = "serviceAccount:${data.google_storage_project_service_account.gcs.email_address}"
}

# GCS bucket for document storage — encrypted with CMEK
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

  encryption {
    default_kms_key_name = google_kms_crypto_key.documents.id
  }

  depends_on = [google_kms_crypto_key_iam_member.gcs_encrypt]
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
