# Email notification channel
resource "google_monitoring_notification_channel" "email" {
  display_name = "Companion ${var.environment} Alerts"
  project      = var.project_id
  type         = "email"

  labels = {
    email_address = var.notification_email
  }
}

# 1. Backend error rate > 5% over 5 minutes
resource "google_monitoring_alert_policy" "backend_error_rate" {
  display_name = "Companion ${var.environment} - Backend Error Rate > 5%"
  project      = var.project_id
  combiner     = "OR"

  notification_channels = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "Backend 5xx error rate"

    condition_threshold {
      filter = <<-EOT
        resource.type = "cloud_run_revision"
        AND resource.labels.service_name = "${var.backend_service_name}"
        AND metric.type = "run.googleapis.com/request_count"
        AND metric.labels.response_code_class = "5xx"
      EOT

      comparison      = "COMPARISON_GT"
      threshold_value = 5
      duration        = "300s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }

      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

# 2. Backend P95 latency > 2 seconds over 5 minutes
resource "google_monitoring_alert_policy" "backend_latency" {
  display_name = "Companion ${var.environment} - Backend P95 Latency > 2s"
  project      = var.project_id
  combiner     = "OR"

  notification_channels = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "Backend P95 latency"

    condition_threshold {
      filter = <<-EOT
        resource.type = "cloud_run_revision"
        AND resource.labels.service_name = "${var.backend_service_name}"
        AND metric.type = "run.googleapis.com/request_latencies"
      EOT

      comparison      = "COMPARISON_GT"
      threshold_value = 2000
      duration        = "300s"

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_PERCENTILE_95"
        cross_series_reducer = "REDUCE_MAX"
        group_by_fields      = ["resource.labels.service_name"]
      }

      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

# 3. Cloud SQL CPU > 80% over 10 minutes
resource "google_monitoring_alert_policy" "cloudsql_cpu" {
  display_name = "Companion ${var.environment} - Cloud SQL CPU > 80%"
  project      = var.project_id
  combiner     = "OR"

  notification_channels = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "Cloud SQL CPU utilization"

    condition_threshold {
      filter = <<-EOT
        resource.type = "cloudsql_database"
        AND metric.type = "cloudsql.googleapis.com/database/cpu/utilization"
      EOT

      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "600s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }

      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

# 4. Cloud SQL disk usage > 80%
resource "google_monitoring_alert_policy" "cloudsql_disk" {
  display_name = "Companion ${var.environment} - Cloud SQL Disk > 80%"
  project      = var.project_id
  combiner     = "OR"

  notification_channels = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "Cloud SQL disk utilization"

    condition_threshold {
      filter = <<-EOT
        resource.type = "cloudsql_database"
        AND metric.type = "cloudsql.googleapis.com/database/disk/utilization"
      EOT

      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "300s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }

      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

# 5. Cloud Run instance count at max
resource "google_monitoring_alert_policy" "backend_max_instances" {
  display_name = "Companion ${var.environment} - Backend at Max Instances"
  project      = var.project_id
  combiner     = "OR"

  notification_channels = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "Backend instance count at scaling limit"

    condition_threshold {
      filter = <<-EOT
        resource.type = "cloud_run_revision"
        AND resource.labels.service_name = "${var.backend_service_name}"
        AND metric.type = "run.googleapis.com/container/instance_count"
      EOT

      comparison      = "COMPARISON_GT"
      threshold_value = var.environment == "prod" ? 45 : 8
      duration        = "300s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MAX"
      }

      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

# 6. Redis memory usage > 80%
resource "google_monitoring_alert_policy" "redis_memory" {
  display_name = "Companion ${var.environment} - Redis Memory > 80%"
  project      = var.project_id
  combiner     = "OR"

  notification_channels = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "Redis memory utilization"

    condition_threshold {
      filter = <<-EOT
        resource.type = "redis_instance"
        AND metric.type = "redis.googleapis.com/stats/memory/usage_ratio"
      EOT

      comparison      = "COMPARISON_GT"
      threshold_value = 0.8
      duration        = "300s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }

      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}
