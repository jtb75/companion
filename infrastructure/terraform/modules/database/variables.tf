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

variable "vpc_network_id" {
  description = "VPC network ID for private IP access"
  type        = string
}

variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
}

variable "redis_memory_size" {
  description = "Memorystore Redis memory size in GB"
  type        = number
}

variable "enable_redis" {
  description = "Whether to create Memorystore Redis"
  type        = bool
  default     = false
}
