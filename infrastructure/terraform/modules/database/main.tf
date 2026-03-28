resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "google_sql_database_instance" "postgres" {
  name                = "companion-${var.environment}-db"
  project             = var.project_id
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = var.environment == "prod" ? true : false

  depends_on = [var.vpc_network_id]

  settings {
    tier              = var.db_tier
    disk_size         = var.db_disk_size
    disk_type         = "PD_SSD"
    disk_autoresize   = true
    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = var.vpc_network_id
      enable_private_path_for_google_cloud_services = true
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7 # Sunday
      hour         = 3
      update_track = "stable"
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = false
    }
  }
}

resource "google_sql_database" "companion" {
  name     = "companion"
  project  = var.project_id
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "companion" {
  name     = "companion"
  project  = var.project_id
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
}

# Memorystore Redis instance
resource "google_redis_instance" "redis" {
  name               = "companion-${var.environment}-redis"
  project            = var.project_id
  region             = var.region
  tier               = "BASIC"
  memory_size_gb     = var.redis_memory_size
  redis_version      = "REDIS_7_0"
  authorized_network = var.vpc_network_id

  redis_configs = {
    maxmemory-policy = "allkeys-lru"
  }
}
