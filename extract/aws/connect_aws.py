#!/usr/bin/env python3
"""
Quick AWS connectivity tester.

Features:
- Uses boto3 if available; otherwise instructs to install it.
- Attempts STS GetCallerIdentity to verify credentials/profile.
- Optionally lists S3 buckets (requires s3:ListAllMyBuckets permission).

Usage examples:
  # Use default credentials/profile
  python extract/aws/connect_aws.py

  # Use a specific AWS CLI profile
  python extract/aws/connect_aws.py --profile egx-project

  # Test and list buckets (if allowed)
  python extract/aws/connect_aws.py --list-buckets

Notes:
- Credentials can be provided via AWS CLI profiles (~/.aws/credentials), environment variables (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY), or SSO.
- Required IAM permissions for basic test: sts:GetCallerIdentity
- Optional for S3 listing: s3:ListAllMyBuckets
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional


def main():
    parser = argparse.ArgumentParser(description="AWS connectivity test script")
    parser.add_argument("--profile", help="AWS CLI profile name to use (default: environment or default profile)")
    parser.add_argument("--region", help="AWS region to use (optional)")
    parser.add_argument("--list-buckets", action="store_true", help="List S3 buckets if allowed")
    parser.add_argument("--timeout", type=int, default=10, help="Client timeout in seconds")

    args = parser.parse_args()

    try:
        import boto3
        import botocore
    except Exception:  # ImportError or similar
        print("boto3 is not installed in your environment.")
        print("Install it into your .venv or system Python: pip install boto3")
        sys.exit(2)

    session_kwargs = {}
    if args.profile:
        session_kwargs["profile_name"] = args.profile
    if args.region:
        session_kwargs["region_name"] = args.region

    try:
        session = boto3.Session(**session_kwargs)
        sts = session.client("sts", config=botocore.config.Config(read_timeout=args.timeout, connect_timeout=args.timeout))

        # Test identity
        identity = sts.get_caller_identity()
        print("AWS STS GetCallerIdentity successful:")
        print(json.dumps(identity, indent=2))

    except botocore.exceptions.NoCredentialsError:
        print("No AWS credentials found. Configure via AWS CLI (aws configure), environment variables, or SSO.")
        sys.exit(3)
    except botocore.exceptions.PartialCredentialsError:
        print("Partial credentials found. Ensure both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set, or configure a profile.")
        sys.exit(4)
    except botocore.exceptions.ClientError as e:
        code = getattr(e, "response", {}).get("Error", {}).get("Code")
        msg = getattr(e, "response", {}).get("Error", {}).get("Message")
        print(f"AWS ClientError ({code}): {msg}")
        sys.exit(5)
    except Exception as e:
        print(f"Unexpected error when calling STS: {e}")
        sys.exit(6)

    if args.list_buckets:
        try:
            s3 = session.client("s3", config=botocore.config.Config(read_timeout=args.timeout, connect_timeout=args.timeout))
            resp = s3.list_buckets()
            buckets = resp.get("Buckets", [])
            print("S3 Buckets:")
            for b in buckets:
                print("-", b.get("Name"))
        except botocore.exceptions.ClientError as e:
            print("Failed to list S3 buckets. Ensure your IAM user/role has s3:ListAllMyBuckets permission.")
            print("ClientError:", e)
            sys.exit(7)
        except Exception as e:
            print("Unexpected error while listing buckets:", e)
            sys.exit(8)

    print("AWS connectivity test completed successfully.")


if __name__ == "__main__":
    main()
