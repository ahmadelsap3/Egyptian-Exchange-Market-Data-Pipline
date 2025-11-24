#!/usr/bin/env bash
# Owner-run helper script to create per-user IAM users with S3 upload policy attached.
# USAGE: ./create_team_users.sh <username> <bucket-name>
# Example: ./create_team_users.sh alice egx-data-bucket

set -euo pipefail

if [[ "$#" -ne 2 ]]; then
  echo "Usage: $0 <username> <bucket-name>"
  exit 2
fi

USERNAME="$1"
BUCKET="$2"
POLICY_NAME="EgxTeamUploadPolicy-${BUCKET}"
POLICY_FILE="egx_team_upload_policy.json"

# Safety: confirm intent
echo "You are about to create IAM user '$USERNAME' and attach S3 upload policy for bucket '$BUCKET'."
read -p "Continue? (y/N): " confirm
if [[ "${confirm,,}" != "y" ]]; then
  echo "Aborted by user."
  exit 0
fi

# 1) Create or update policy document with the bucket name substituted into a temp file
TMP_POLICY_JSON="/tmp/${POLICY_FILE}.${BUCKET}"
sed "s/\${BUCKET_NAME}/${BUCKET}/g" "$(dirname "$0")/${POLICY_FILE}" > "$TMP_POLICY_JSON"

# 2) Create policy (if not exists) or get existing ARN
EXISTING_POLICY_ARN=$(aws iam list-policies --scope Local --query "Policies[?PolicyName=='${POLICY_NAME}'].Arn | [0]" --output text || true)
if [[ "$EXISTING_POLICY_ARN" == "None" || -z "$EXISTING_POLICY_ARN" ]]; then
  echo "Creating IAM policy ${POLICY_NAME}..."
  CREATE_OUT=$(aws iam create-policy --policy-name "${POLICY_NAME}" --policy-document file://"${TMP_POLICY_JSON}")
  POLICY_ARN=$(echo "$CREATE_OUT" | jq -r '.Policy.Arn')
else
  POLICY_ARN="$EXISTING_POLICY_ARN"
  echo "Found existing policy ARN: $POLICY_ARN"
fi

# 3) Create IAM user (skip if exists)
if aws iam get-user --user-name "$USERNAME" >/dev/null 2>&1; then
  echo "User $USERNAME already exists. Skipping user creation."
else
  echo "Creating IAM user $USERNAME..."
  aws iam create-user --user-name "$USERNAME"
fi

# 4) Attach policy to user
echo "Attaching policy to user..."
aws iam attach-user-policy --user-name "$USERNAME" --policy-arn "$POLICY_ARN"

# 5) Create access key (prints it; store securely). If access key exists, create a new one.
# Note: AWS limits 2 access keys per user.
CREATE_KEY_OUT=$(aws iam create-access-key --user-name "$USERNAME")
ACCESS_KEY_ID=$(echo "$CREATE_KEY_OUT" | jq -r '.AccessKey.AccessKeyId')
SECRET_ACCESS_KEY=$(echo "$CREATE_KEY_OUT" | jq -r '.AccessKey.SecretAccessKey')

# 6) Print credentials and a sample aws configure command
cat <<EOF

--- CREATED CREDENTIALS ---
AWS_ACCESS_KEY_ID=${ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${SECRET_ACCESS_KEY}

IMPORTANT: Store these securely. Do NOT commit them to git.

To configure locally for $USERNAME run:

  aws configure set aws_access_key_id ${ACCESS_KEY_ID} --profile ${USERNAME}
  aws configure set aws_secret_access_key ${SECRET_ACCESS_KEY} --profile ${USERNAME}
  aws configure set region us-east-1 --profile ${USERNAME}

Or export for a session:

  export AWS_ACCESS_KEY_ID=${ACCESS_KEY_ID}
  export AWS_SECRET_ACCESS_KEY=${SECRET_ACCESS_KEY}

To test upload (example):

  echo '{"hello":"world"}' > /tmp/test.json
  aws s3 cp /tmp/test.json s3://${BUCKET}/streaming/${USERNAME}-test.json --profile ${USERNAME}

--------------------------
EOF

# Cleanup tmp file
rm -f "$TMP_POLICY_JSON"

echo "Done. Remember to share credentials securely (password manager or one-time secret)."
