variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "environment" {
  description = "Deployment environment (staging or prod)"
  type        = string
}

variable "backend_url" {
  description = "URL of the backend Cloud Run service"
  type        = string
}

variable "pipeline_api_key_secret_id" {
  description = "Secret ID for pipeline API key"
  type        = string
}
