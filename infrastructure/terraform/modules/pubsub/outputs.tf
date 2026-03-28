output "topic_ids" {
  description = "Map of topic short names to their full IDs"
  value = {
    for name, topic in google_pubsub_topic.events : name => topic.id
  }
}

output "dead_letter_topic_id" {
  description = "Dead letter topic ID"
  value       = google_pubsub_topic.dead_letter.id
}
