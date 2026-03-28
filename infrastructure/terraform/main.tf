terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    # Configured per environment via -backend-config
    # bucket = "companion-terraform-state"
    # prefix = "staging" or "prod"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

module "networking" {
  source      = "./modules/networking"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
}

module "database" {
  source            = "./modules/database"
  project_id        = var.project_id
  region            = var.region
  environment       = var.environment
  vpc_network_id    = module.networking.vpc_network_id
  db_tier           = var.db_tier
  db_disk_size      = var.db_disk_size
  redis_memory_size = var.redis_memory_size
}

module "storage" {
  source      = "./modules/storage"
  project_id  = var.project_id
  region      = var.region
  environment = var.environment
}

module "pubsub" {
  source      = "./modules/pubsub"
  project_id  = var.project_id
  environment = var.environment
}

module "secrets" {
  source                   = "./modules/secrets"
  project_id               = var.project_id
  region                   = var.region
  environment              = var.environment
  database_connection_name = module.database.connection_name
  database_name            = module.database.database_name
  database_user            = module.database.database_user
  database_password        = module.database.database_password
  redis_host               = module.database.redis_host
  redis_port               = module.database.redis_port
}

module "compute" {
  source                         = "./modules/compute"
  project_id                     = var.project_id
  region                         = var.region
  environment                    = var.environment
  vpc_connector_id               = module.networking.vpc_connector_id
  database_connection_name       = module.database.connection_name
  database_url_secret_id         = module.secrets.database_url_secret_id
  anthropic_api_key_secret_id    = module.secrets.anthropic_api_key_secret_id
  openai_api_key_secret_id       = module.secrets.openai_api_key_secret_id
  firebase_credentials_secret_id = module.secrets.firebase_credentials_secret_id
  redis_host                     = module.database.redis_host
  redis_port                     = module.database.redis_port
  documents_bucket               = module.storage.documents_bucket_name
  artifact_registry_repo         = module.storage.artifact_registry_repo
  backend_image                  = var.backend_image
  web_image                      = var.web_image
  backend_min_instances          = var.backend_min_instances
  backend_max_instances          = var.backend_max_instances
  web_min_instances              = var.web_min_instances
  backend_cpu                    = var.backend_cpu
  backend_memory                 = var.backend_memory
}

module "monitoring" {
  source               = "./modules/monitoring"
  project_id           = var.project_id
  environment          = var.environment
  backend_service_name = module.compute.backend_service_name
  web_service_name     = module.compute.web_service_name
  notification_email   = var.notification_email
}
