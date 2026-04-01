variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (staging or prod)"
  type        = string
  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "Environment must be 'staging' or 'prod'."
  }
}

variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_disk_size" {
  description = "Cloud SQL disk size in GB"
  type        = number
  default     = 10
}

variable "redis_memory_size" {
  description = "Memorystore Redis memory size in GB"
  type        = number
  default     = 1
}

variable "enable_redis" {
  description = "Whether to create Memorystore Redis (set false to save cost)"
  type        = bool
  default     = false
}

variable "backend_image" {
  description = "Full Artifact Registry path for the backend Docker image"
  type        = string
}

variable "web_image" {
  description = "Full Artifact Registry path for the web dashboard Docker image"
  type        = string
}

variable "backend_min_instances" {
  description = "Minimum number of backend Cloud Run instances"
  type        = number
  default     = 0
}

variable "backend_max_instances" {
  description = "Maximum number of backend Cloud Run instances"
  type        = number
  default     = 10
}

variable "web_min_instances" {
  description = "Minimum number of web dashboard Cloud Run instances"
  type        = number
  default     = 0
}

variable "backend_cpu" {
  description = "CPU allocation for backend Cloud Run service"
  type        = string
  default     = "1"
}

variable "backend_memory" {
  description = "Memory allocation for backend Cloud Run service"
  type        = string
  default     = "512Mi"
}

variable "notification_email" {
  description = "Email address for monitoring alert notifications"
  type        = string
}

variable "app_url" {
  description = "Frontend URL for email links (invitation, account actions)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository in owner/repo format"
  type        = string
  default     = "jtb75/companion"
}
