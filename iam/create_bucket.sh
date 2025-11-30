#!/usr/bin/env bash
# Create S3 bucket for the team

set -e

BUCKET_NAME="egx-data-bucket"
REGION="us-east-1"

echo "=== Creating S3 Bucket for EGX Data Pipeline ==="
echo ""
echo "Bucket: ${BUCKET_NAME}"
echo "Region: ${REGION}"
echo ""

# Create bucket
echo "Creating bucket..."
if aws s3 mb s3://${BUCKET_NAME} --region ${REGION}; then
    echo "✅ Bucket created successfully"
else
    echo "⚠️  Bucket may already exist or error occurred"
fi

# Enable versioning (recommended for data safety)
echo ""
echo "Enabling versioning..."
aws s3api put-bucket-versioning \
    --bucket ${BUCKET_NAME} \
    --versioning-configuration Status=Enabled

echo "✅ Versioning enabled"

# Create folder structure
echo ""
echo "Creating folder structure..."
echo '{}' | aws s3 cp - s3://${BUCKET_NAME}/streaming/.placeholder
echo '{}' | aws s3 cp - s3://${BUCKET_NAME}/batch/.placeholder

echo "✅ Folder structure created"

# Verify bucket
echo ""
echo "Verifying bucket..."
aws s3 ls s3://${BUCKET_NAME}/

echo ""
echo "✅ Bucket setup complete!"
echo ""
echo "Teammates can now upload to:"
echo "  - s3://${BUCKET_NAME}/streaming/"
echo "  - s3://${BUCKET_NAME}/batch/"
