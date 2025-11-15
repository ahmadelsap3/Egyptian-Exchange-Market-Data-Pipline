variable "bucket_name" {
  description = "Name of the S3 bucket to create (must be globally unique)"
  type        = string
}

variable "region" {
  description = "AWS region to create resources in"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Optional AWS CLI profile name to use for Terraform provider"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = { "project" = "egx-project" }
}

# Lifecycle controls
variable "batch_transition_days" {
  description = "Days until transition to Glacier for batch prefix"
  type        = number
  default     = 90
}

variable "batch_deep_archive_days" {
  description = "Days until transition to Deep Archive for batch prefix"
  type        = number
  default     = 365
}

variable "batch_expiration_days" {
  description = "Days until objects under batch/ expire"
  type        = number
  default     = 1825
}

variable "streaming_expiration_days" {
  description = "Retention days for streaming/ prefix (short-term)"
  type        = number
  default     = 14
}
