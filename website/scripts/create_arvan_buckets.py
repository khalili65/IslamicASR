#!/usr/bin/env python3
"""Create Arvan Object Storage buckets for a lecture site (S3-compatible API).

Loads credentials from repo-root `.env.arvan` (or path in ARVAN_ENV_FILE).

Usage:
  .venv/bin/python website/scripts/create_arvan_buckets.py
  .venv/bin/python website/scripts/create_arvan_buckets.py \\
      --media islamic-asr-portal-media --web islamic-asr-portal-web

After create:
  - Panel → Object Storage → each bucket → Public read (if not set by ACL below)
  - Panel → Static Website → activate on the WEB bucket (index: index.html)
  - CORS GET/HEAD on the MEDIA bucket for browser audio
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_env(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        raise SystemExit(f"Missing {path}. Copy .env.arvan.example → .env.arvan and fill keys.")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def s3_client(env: Dict[str, str]):
    access = env.get("ARVAN_ACCESS_KEY", "").strip()
    secret = env.get("ARVAN_SECRET_KEY", "").strip()
    if not access or not secret:
        raise SystemExit("ARVAN_ACCESS_KEY / ARVAN_SECRET_KEY are empty in env file.")
    return boto3.client(
        "s3",
        endpoint_url=env.get("ARVAN_ENDPOINT", "https://s3.ir-thr-at1.arvanstorage.ir"),
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name=env.get("ARVAN_REGION", "ir-thr-at1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket(client, name: str, *, public_read: bool) -> str:
    try:
        client.head_bucket(Bucket=name)
        status = "exists"
    except ClientError as exc:
        code = (exc.response.get("Error") or {}).get("Code", "")
        if code not in {"404", "NoSuchBucket", "NotFound", "403"}:
            # 403 can mean exists but no permission — try create anyway
            pass
        try:
            client.create_bucket(Bucket=name)
            status = "created"
        except ClientError as create_exc:
            err = create_exc.response.get("Error") or {}
            if err.get("Code") in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                status = "exists"
            else:
                raise

    if public_read:
        try:
            client.put_bucket_acl(Bucket=name, ACL="public-read")
        except ClientError as exc:
            print(f"  warning: could not set public-read ACL on {name}: {exc}")

    # CORS so the player can fetch audio from the media host
    try:
        client.put_bucket_cors(
            Bucket=name,
            CORSConfiguration={
                "CORSRules": [
                    {
                        "AllowedHeaders": ["*"],
                        "AllowedMethods": ["GET", "HEAD"],
                        "AllowedOrigins": ["*"],
                        "ExposeHeaders": ["ETag", "Content-Length", "Content-Type"],
                        "MaxAgeSeconds": 86400,
                    }
                ]
            },
        )
    except ClientError as exc:
        print(f"  warning: could not set CORS on {name}: {exc}")

    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(os.environ.get("ARVAN_ENV_FILE", REPO_ROOT / ".env.arvan")),
        help="Path to env file (default: .env.arvan)",
    )
    parser.add_argument(
        "--media",
        default=None,
        help="Media bucket name (default: ARVAN_BUCKET from env)",
    )
    parser.add_argument(
        "--web",
        default=None,
        help="Static website bucket name (default: ARVAN_WEB_BUCKET from env)",
    )
    args = parser.parse_args()

    env = load_env(args.env_file.expanduser().resolve())
    media = (args.media or env.get("ARVAN_BUCKET") or "").strip()
    web = (args.web or env.get("ARVAN_WEB_BUCKET") or "").strip()
    if not media or not web:
        raise SystemExit("Need --media/--web or ARVAN_BUCKET + ARVAN_WEB_BUCKET in env.")

    client = s3_client(env)
    print(f"Endpoint: {env.get('ARVAN_ENDPOINT')}")
    print(f"Media   : {media}")
    print(f"Web     : {web}")

    for name, public in ((media, True), (web, True)):
        status = ensure_bucket(client, name, public_read=public)
        print(f"  {name}: {status}")

    print(
        "\nNext (panel):\n"
        f"  1) Object Storage → {web} → Static Website → Activate (index: index.html)\n"
        f"  2) Confirm public read on both buckets\n"
        f"  3) Upload audio → {media}; deploy site out/ → {web}\n"
    )
    print("Buckets ready.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClientError as exc:
        print(json.dumps(exc.response.get("Error", {}), ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
