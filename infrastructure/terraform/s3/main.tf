terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.region
  # Optional profile; leave empty to use default credentials / env vars
  profile = var.aws_profile != "" ? var.aws_profile : null
}

########################
# S3 bucket (single)
########################
resource "aws_s3_bucket" "egx_project" {
  bucket = var.bucket_name
  acl    = "private"

  tags = var.tags

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  lifecycle_rule {
    id      = "batch-to-archive"
    enabled = true
    prefix  = "batch/"

    transition {
      days          = var.batch_transition_days
      storage_class = "GLACIER"
    }

    transition {
      days          = var.batch_deep_archive_days
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = var.batch_expiration_days
    }
  }

  lifecycle_rule {
    id      = "streaming-short-retention"
    enabled = true
    prefix  = "streaming/"

    expiration {
      days = var.streaming_expiration_days
    }
  }
}

resource "aws_s3_bucket_public_access_block" "egx_block" {
  bucket                  = aws_s3_bucket.egx_project.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

########################
# IAM Policy for producers
########################
data "aws_iam_policy_document" "producer_policy" {
  statement {
    sid    = "AllowPutListGet"
    effect = "Allow"

    actions = [
      "s3:PutObject",
      "s3:PutObjectAcl",
      "s3:ListBucket",
      "s3:GetObject",
      "s3:GetObjectAcl"
    ]

    resources = [
      aws_s3_bucket.egx_project.arn,
      "${aws_s3_bucket.egx_project.arn}/*"
    ]
  }

  statement {
    sid    = "AllowListBucketForPrefixes"
    effect = "Allow"
    actions = ["s3:ListBucket"]
    resources = [aws_s3_bucket.egx_project.arn]

    conditions = {
      StringLike = {
        "s3:prefix" = ["streaming/*", "batch/*"]
      }
    }
  }
}

resource "aws_iam_policy" "egx_s3_producer" {
  name        = "egx-s3-producer-policy-${replace(var.bucket_name, "-", "-") }"
  description = "Policy allowing writes to the egx project bucket (streaming & batch prefixes)"
  policy      = data.aws_iam_policy_document.producer_policy.json
}

########################
# Outputs
########################
output "bucket_name" {
  description = "S3 bucket name created for the project"
  value       = aws_s3_bucket.egx_project.id
}

output "bucket_arn" {
  value = aws_s3_bucket.egx_project.arn
}

output "producer_policy_arn" {
  description = "ARN of the IAM policy to attach to producer roles/users"
  value       = aws_iam_policy.egx_s3_producer.arn
}
