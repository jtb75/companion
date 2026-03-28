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

variable "vpc_connector_id" {
  description = "Serverless VPC Access connector ID"
  type        = string
}

variable "database_connection_name" {
  description = "Cloud SQL instance connection name for Cloud Run"
  type        = string
}

variable "database_url_secret_id" {
  description = "Secret Manager secret ID for database URL"
  type        = string
}

variable "anthropic_api_key_secret_id" {
  description = "Secret Manager secret ID for Anthropic API key"
  type        = string
}

variable "openai_api_key_secret_id" {
  description = "Secret Manager secret ID for OpenAI API key"
  type        = string
}

variable "firebase_credentials_secret_id" {
  description = "Secret Manager secret ID for Firebase credentials"
  type        = string
}

variable "redis_url_secret_id" {
  description = "Secret Manager secret ID for Redis URL"
  type        = string
}

variable "documents_bucket" {
  description = "GCS bucket name for documents"
  type        = string
}

variable "artifact_registry_repo" {
  description = "Artifact Registry repository path"
  type        = string
}

variable "backend_image" {
  description = "Full Docker image path for the backend"
  type        = string
}

variable "web_image" {
  description = "Full Docker image path for the web dashboard"
  type        = string
}

variable "backend_min_instances" {
  description = "Minimum number of backend Cloud Run instances"
  type        = number
}

variable "backend_max_instances" {
  description = "Maximum number of backend Cloud Run instances"
  type        = number
}

variable "web_min_instances" {
  description = "Minimum number of web Cloud Run instances"
  type        = number
}

variable "backend_cpu" {
  description = "CPU allocation for backend Cloud Run service"
  type        = string
}

variable "backend_memory" {
  description = "Memory allocation for backend Cloud Run service"
  type        = string
}
