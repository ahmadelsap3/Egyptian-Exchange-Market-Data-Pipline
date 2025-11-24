#!/usr/bin/env python3
"""
Bootstrap script to create an admin IAM user with access keys.
Run this ONCE using your AWS root account credentials or existing admin credentials.

Usage:
    python iam/bootstrap_admin.py <username>

Example:
    python iam/bootstrap_admin.py ahmed-admin
"""

import sys
import boto3
import json
from botocore.exceptions import ClientError

def create_admin_user(username):
    """Create an IAM user with AdministratorAccess and return access keys."""
    iam = boto3.client('iam')
    
    print(f"Creating IAM user: {username}")
    
    # 1. Create user
    try:
        iam.create_user(UserName=username)
        print(f"✓ User {username} created")
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"✓ User {username} already exists")
        else:
            raise
    
    # 2. Attach AdministratorAccess policy
    policy_arn = 'arn:aws:iam::aws:policy/AdministratorAccess'
    try:
        iam.attach_user_policy(UserName=username, PolicyArn=policy_arn)
        print(f"✓ Attached AdministratorAccess policy to {username}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"✗ Policy {policy_arn} not found")
            raise
        else:
            print(f"✓ Policy already attached (or error: {e})")
    
    # 3. Create access key
    try:
        response = iam.create_access_key(UserName=username)
        access_key = response['AccessKey']
        
        print("\n" + "="*60)
        print("SUCCESS! Save these credentials securely:")
        print("="*60)
        print(f"AWS_ACCESS_KEY_ID={access_key['AccessKeyId']}")
        print(f"AWS_SECRET_ACCESS_KEY={access_key['SecretAccessKey']}")
        print("="*60)
        print("\nTo configure AWS CLI, run:")
        print(f"  aws configure")
        print("  # then paste the keys above when prompted")
        print("\nOr export them for this session:")
        print(f"  export AWS_ACCESS_KEY_ID={access_key['AccessKeyId']}")
        print(f"  export AWS_SECRET_ACCESS_KEY={access_key['SecretAccessKey']}")
        print("="*60)
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'LimitExceeded':
            print(f"\n✗ User {username} already has 2 access keys (AWS limit).")
            print("Delete an old key first:")
            print(f"  aws iam list-access-keys --user-name {username}")
            print(f"  aws iam delete-access-key --user-name {username} --access-key-id <OLD_KEY_ID>")
        else:
            raise

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python iam/bootstrap_admin.py <username>")
        print("Example: python iam/bootstrap_admin.py ahmed-admin")
        sys.exit(1)
    
    username = sys.argv[1]
    
    print("This script will create an admin IAM user with full AWS permissions.")
    print("You must run this with existing AWS credentials (root or admin).")
    print()
    
    # Check if credentials are configured
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"Running as: {identity['Arn']}")
        print()
    except Exception as e:
        print("ERROR: No AWS credentials found.")
        print("Set credentials via environment variables:")
        print("  export AWS_ACCESS_KEY_ID=...")
        print("  export AWS_SECRET_ACCESS_KEY=...")
        print("Or configure via: aws configure")
        sys.exit(1)
    
    confirm = input(f"Create admin user '{username}'? (y/N): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        sys.exit(0)
    
    create_admin_user(username)
