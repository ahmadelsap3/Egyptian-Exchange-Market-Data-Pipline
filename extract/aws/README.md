AWS connection helper

This folder contains a small helper to verify connectivity to AWS.

Prerequisites
- Python 3.8+ (project uses 3.12)
- Install the AWS CLI v2 (optional but useful)
- Install boto3 in your virtualenv: `pip install boto3`

How to provide credentials
1) AWS CLI profile (recommended for local dev)
   - `aws configure --profile egx-project` (interactive)
   - Or set up SSO with `aws configure sso` and create a named profile
   - The profile is stored in `~/.aws/credentials` and `~/.aws/config`

2) Environment variables (programmatic)
   - Export in your shell or CI runner:
     ```bash
     export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
     export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
     # optional session token
     export AWS_SESSION_TOKEN=YOUR_SESSION_TOKEN
     ```

3) IAM Role / AssumeRole
   - Use `aws sts assume-role` or configure your runtime to assume a role.

Quick test with AWS CLI
```bash
# Show who you are
aws sts get-caller-identity --profile egx-project

# List S3 buckets (if allowed)
aws s3 ls --profile egx-project
```

Run the python helper

```bash
# From project root (recommended virtualenv active)
.venv/bin/python extract/aws/connect_aws.py --profile egx-project --list-buckets

# Use default profile / env credentials
.venv/bin/python extract/aws/connect_aws.py --list-buckets
```

Interpreting results
- `get-caller-identity` returns Account, ARN and UserId
- If you see a `NoCredentialsError`, follow the "How to provide credentials" section above
- If `list_buckets` fails, ensure your IAM user/role has `s3:ListAllMyBuckets` permission

Security notes
- Do NOT commit credentials into the repository. Use CLI profiles, environment variables, or a secrets manager.
- Prefer temporary credentials (roles or session tokens) for CI/CD.
