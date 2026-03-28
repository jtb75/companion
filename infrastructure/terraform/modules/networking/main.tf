resource "google_compute_network" "vpc" {
  name                    = "companion-${var.environment}-vpc"
  project                 = var.project_id
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "private" {
  name                     = "companion-${var.environment}-private-subnet"
  project                  = var.project_id
  region                   = var.region
  network                  = google_compute_network.vpc.id
  ip_cidr_range            = "10.0.0.0/20"
  private_ip_google_access = true
}

# Reserve an IP range for private services access (Cloud SQL, Memorystore)
resource "google_compute_global_address" "private_services_range" {
  name          = "companion-${var.environment}-private-services"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

# Enable private services access for Cloud SQL and Memorystore
resource "google_service_networking_connection" "private_services" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services_range.name]
}

# Serverless VPC connector for Cloud Run to access Cloud SQL and Redis
resource "google_vpc_access_connector" "connector" {
  name          = "companion-${var.environment}-vpc"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = "10.8.0.0/28"

  min_instances = 2
  max_instances = 3
}

# Allow internal traffic within the VPC
resource "google_compute_firewall" "allow_internal" {
  name    = "companion-${var.environment}-allow-internal"
  project = var.project_id
  network = google_compute_network.vpc.id

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/8"]
  priority      = 1000
}

# Deny all ingress from the internet to VPC resources
resource "google_compute_firewall" "deny_all_ingress" {
  name    = "companion-${var.environment}-deny-all-ingress"
  project = var.project_id
  network = google_compute_network.vpc.id

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
  priority      = 65534
}
