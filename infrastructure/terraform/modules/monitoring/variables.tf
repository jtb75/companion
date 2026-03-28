variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "environment" {
  description = "Deployment environment (staging or prod)"
  type        = string
}

variable "backend_service_name" {
  description = "Backend Cloud Run service name"
  type        = string
}

variable "web_service_name" {
  description = "Web dashboard Cloud Run service name"
  type        = string
}

variable "notification_email" {
  description = "Email address for alert notifications"
  type        = string
}

