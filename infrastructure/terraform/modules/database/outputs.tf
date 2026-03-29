output "connection_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.companion.name
}

output "database_user" {
  description = "Database user name"
  value       = google_sql_user.companion.name
}

output "database_password" {
  description = "Database user password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "redis_host" {
  description = "Memorystore Redis host IP (empty if Redis disabled)"
  value       = var.enable_redis ? google_redis_instance.redis[0].host : ""
}

output "redis_port" {
  description = "Memorystore Redis port (0 if Redis disabled)"
  value       = var.enable_redis ? google_redis_instance.redis[0].port : 0
}
