output "bucket_name" {
  description = "Name of created bucket"
  value       = aws_s3_bucket.egx_project.id
}

output "bucket_arn" {
  value = aws_s3_bucket.egx_project.arn
}

output "producer_policy_arn" {
  value = aws_iam_policy.egx_s3_producer.arn
}
