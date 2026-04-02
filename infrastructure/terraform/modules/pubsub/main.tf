locals {
  all_topic_names = [
    "document-received",
    "document-processed",
    "document-routed",
    "question-asked",
    "question-answered",
    "question-threshold-crossed",
    "medication-confirmed",
    "medication-missed",
    "bill-acknowledged",
    "bill-overdue",
    "trip-started",
    "trip-completed",
    "away-mode-set",
    "away-mode-extended",
    "memory-updated",
    "memory-deleted",
    "caregiver-alert-triggered",
    "caregiver-dashboard-viewed",
    "notification-delivered",
    "notification-dismissed",
    "checkin-morning-triggered",
    "checkin-morning-acknowledged",
    "config-updated",
  ]

  # Topics that use standard pull subscriptions
  pull_topic_names = setsubtract(toset(local.all_topic_names), ["document-received"])
}

# Dead letter topic
resource "google_pubsub_topic" "dead_letter" {
  name    = "companion-${var.environment}-dead-letter"
  project = var.project_id

  message_retention_duration = "604800s" # 7 days
}

# Dead letter subscription (for inspection)
resource "google_pubsub_subscription" "dead_letter" {
  name    = "companion-${var.environment}-dead-letter-sub"
  project = var.project_id
  topic   = google_pubsub_topic.dead_letter.id

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s" # 7 days
}

# Event topics
resource "google_pubsub_topic" "events" {
  for_each = toset(local.all_topic_names)

  name    = "companion-${var.environment}-${each.value}"
  project = var.project_id

  message_retention_duration = "604800s" # 7 days
}

# Default pull subscriptions for each topic (except push ones)
resource "google_pubsub_subscription" "events" {
  for_each = local.pull_topic_names

  name    = "companion-${var.environment}-${each.value}-sub"
  project = var.project_id
  topic   = google_pubsub_topic.events[each.value].id

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s" # 7 days

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  expiration_policy {
    ttl = "" # Never expires
  }
}

# Push subscription for document-received
resource "google_pubsub_subscription" "document_received_push" {
  name    = "companion-${var.environment}-document-received-push"
  project = var.project_id
  topic   = google_pubsub_topic.events["document-received"].id

  ack_deadline_seconds       = 300 # 5 mins for LLM pipeline
  message_retention_duration = "604800s"

  push_config {
    push_endpoint = "${var.backend_url}/api/pipeline/document-received"

    attributes = {
      "x-goog-version" = "v1"
    }
  }
}
