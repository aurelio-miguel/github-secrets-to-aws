#!/usr/bin/env python3
"""Upload explicitly selected environment variables to an existing AWS secret."""

import json
import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError


SECRET_FIELDS = {
    "DEMO_API_TOKEN": "api_token",
    "DEMO_DB_PASSWORD": "db_password",
}


def sync_secrets(environ, client_factory=boto3.client):
    required = ("AWS_REGION", "AWS_SECRET_ARN", *SECRET_FIELDS)
    missing = [name for name in required if not environ.get(name, "").strip()]
    if missing:
        raise ValueError("Missing or empty environment variables: " + ", ".join(missing))

    payload = json.dumps(
        {key: environ[name] for name, key in SECRET_FIELDS.items()},
        ensure_ascii=False,
    )
    if len(payload.encode("utf-8")) > 65536:
        raise ValueError("Secret JSON exceeds the 65,536-byte limit.")

    client = client_factory("secretsmanager", region_name=environ["AWS_REGION"])

    client.put_secret_value(SecretId=environ["AWS_SECRET_ARN"], SecretString=payload)


def main():
    try:
        sync_secrets(os.environ)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (BotoCoreError, ClientError):
        print("AWS synchronization failed. Check credentials, region and role permissions.", file=sys.stderr)
        return 1
    print("Secret synchronized successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
