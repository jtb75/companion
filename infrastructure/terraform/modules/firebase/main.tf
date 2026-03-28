# Enable Firebase on the existing GCP project
resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id
}

# Create a Firebase Web App for the dashboard
resource "google_firebase_web_app" "dashboard" {
  provider     = google-beta
  project      = var.project_id
  display_name = "Companion ${var.environment} Dashboard"

  depends_on = [google_firebase_project.default]
}

# Retrieve the auto-generated Firebase config (apiKey, authDomain, etc.)
data "google_firebase_web_app_config" "dashboard" {
  provider   = google-beta
  project    = var.project_id
  web_app_id = google_firebase_web_app.dashboard.app_id
}

# Enable Identity Platform (powers Firebase Auth)
resource "google_identity_platform_config" "default" {
  provider = google-beta
  project  = var.project_id

  sign_in {
    allow_duplicate_emails = false

    email {
      enabled           = true
      password_required = true
    }
  }

  depends_on = [google_firebase_project.default]
}

# Store the Firebase web config in Secret Manager so Cloud Run can
# pass it to the web dashboard at build time
resource "google_secret_manager_secret" "firebase_web_config" {
  secret_id = "companion-${var.environment}-firebase-web-config"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "firebase_web_config" {
  secret = google_secret_manager_secret.firebase_web_config.id
  secret_data = jsonencode({
    apiKey            = data.google_firebase_web_app_config.dashboard.api_key
    authDomain        = "${var.project_id}.firebaseapp.com"
    projectId         = var.project_id
    storageBucket     = lookup(data.google_firebase_web_app_config.dashboard, "storage_bucket", "${var.project_id}.appspot.com")
    messagingSenderId = data.google_firebase_web_app_config.dashboard.messaging_sender_id
    appId             = google_firebase_web_app.dashboard.app_id
  })
}
# Firebase module added
