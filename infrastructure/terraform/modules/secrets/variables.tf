variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "environment" {
  description = "Deployment environment (staging or prod)"
  type        = string
}

variable "database_connection_name" {
  description = "Cloud SQL instance connection name"
  type        = string
}

variable "database_name" {
  description = "Database name"
  type        = string
}

variable "database_user" {
  description = "Database user name"
  type        = string
}

variable "database_password" {
  description = "Database user password"
  type        = string
  sensitive   = true
}

variable "redis_host" {
  description = "Memorystore Redis host IP"
  type        = string
}

variable "redis_port" {
  description = "Memorystore Redis port"
  type        = number
}
