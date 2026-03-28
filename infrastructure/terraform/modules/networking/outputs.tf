output "vpc_network_id" {
  description = "VPC network ID"
  value       = google_compute_network.vpc.id
}

output "vpc_connector_id" {
  description = "Serverless VPC Access connector ID"
  value       = google_vpc_access_connector.connector.id
}

output "subnet_id" {
  description = "Private subnet ID"
  value       = google_compute_subnetwork.private.id
}
