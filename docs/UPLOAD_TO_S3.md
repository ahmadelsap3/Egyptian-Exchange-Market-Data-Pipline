# Uploading Data to the Team S3 Bucket

This guide shows how the repository owner creates per-user IAM users and how teammates upload files into the approved prefixes (`streaming/` and `batch/`).

Owner steps (run from a machine with administrator IAM privileges):

1. Ensure `aws` CLI and `jq` are installed.
   - Install on Debian/Ubuntu: `sudo apt update && sudo apt install -y awscli jq`
2. Place the policy template at `iam/egx_team_upload_policy.json` and the helper script `iam/create_team_users.sh` in the repo.
3. Run the helper script to create a user and policy (example):

   ./iam/create_team_users.sh alice egx-data-bucket

   This will:
   - Substitute the bucket name in the policy template and create a policy named `EgxTeamUploadPolicy-<bucket>` (if not already present).
   - Create IAM user `alice` (if not present).
   - Attach the policy to `alice`.
   - Create and print an access key/secret for `alice` (capture securely).

4. Share the credentials securely with the teammate (use a password manager or one-time secret sharing).

Teammate steps (after receiving credentials):

1. Configure the AWS CLI profile locally:

   aws configure --profile alice

   When prompted, paste the `AWS Access Key ID` and `AWS Secret Access Key`.

2. Test upload (the policy only allows uploads under `streaming/` and `batch/`):

   echo '{"test":"ok"}' > /tmp/test.json
   aws s3 cp /tmp/test.json s3://egx-data-bucket/streaming/alice-test.json --profile alice

3. If you need to upload many files, use the `aws s3 cp` or `aws s3 sync` commands. Ensure you only write under `streaming/` or `batch/` prefixes.

Security notes:

- Do NOT share access keys in email or chat. Use a password manager or a secure one-time secret sharing tool.
- Rotate keys periodically and remove unused keys.
- The owner can delete a user or revoke access keys via the AWS Console or `aws iam delete-access-key` / `aws iam delete-user`.

If you want the owner to run these steps for all teammates, provide the desired usernames and bucket name and they can run the script repeatedly.
