Terraform module to provision S3 bucket for EGX pipeline

What this creates
- One S3 bucket (name provided by you) with:
  - Server-side encryption (AES256)
  - Versioning enabled
  - Public access blocked
  - Lifecycle rules:
    - `batch/` prefix: transition to Glacier after 90 days, Deep Archive after 365 days, expire after 1825 days
    - `streaming/` prefix: expire after 14 days by default
- An IAM policy allowing producers to `PutObject`, `ListBucket`, and `GetObject` within the bucket

Why a single bucket
- Simplicity: easier to configure IAM and lifecycle rules with prefixes
- Cost: S3 pricing is per storage; using prefixes keeps costs and operations manageable

How to run
1) Install Terraform (>= 1.0)
2) From this directory:

```bash
cd infrastructure/terraform/s3
terraform init
terraform plan -var='bucket_name=egx-project-data-<yourname>-2025' -var='region=us-east-1'
terraform apply -var='bucket_name=egx-project-data-<yourname>-2025' -var='region=us-east-1' -auto-approve
```

Notes
- Replace `<yourname>` with something unique; S3 bucket names are global.
- Terraform will create an IAM policy resource; you can attach it to a role or user post-creation.
- The default lifecycle rules are conservative; adjust `variables.tf` to suit retention needs.

Cost considerations
- S3 Standard storage ~ $0.023/GB-month (region-dependent). Use lifecycle rules and Parquet/compression to reduce costs.
- Glacier/Deep Archive are cheaper for long-term storage but have retrieval costs.

Outputs
- After apply you will see outputs: `bucket_name`, `bucket_arn`, `producer_policy_arn`.

Security
- Do not commit AWS secrets to source control. Use CLI profiles, environment variables or SSO.

Support
- If you'd like, I can also produce a small shell script that runs `terraform apply` with a provided profile, or add an example `aws_iam_role` resource for automatic role creation.
