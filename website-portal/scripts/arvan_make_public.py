#!/usr/bin/env python3
"""Ensure newly uploaded Arvan objects are publicly readable + list status.

Usage:
  .venv/bin/python website/scripts/arvan_make_public.py
  .venv/bin/python website/scripts/arvan_make_public.py bayat/marefat_nafs/001/
"""
from __future__ import annotations

import sys
from pathlib import Path

from botocore.client import Config
import boto3

REPO = Path(__file__).resolve().parents[2]


def load_env():
    env = {}
    for line in (REPO / ".env.arvan").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def main() -> int:
    prefix = sys.argv[1] if len(sys.argv) > 1 else "bayat/marefat_nafs/"
    env = load_env()
    client = boto3.client(
        "s3",
        endpoint_url=env["ARVAN_ENDPOINT"],
        aws_access_key_id=env["ARVAN_ACCESS_KEY"],
        aws_secret_access_key=env["ARVAN_SECRET_KEY"],
        region_name=env.get("ARVAN_REGION", "ir-thr-at1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    bucket = env["ARVAN_BUCKET"]
    base = env.get("NEXT_PUBLIC_MEDIA_BASE", "").rstrip("/")
    token = None
    n = 0
    while True:
        kw = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kw["ContinuationToken"] = token
        resp = client.list_objects_v2(**kw)
        for obj in resp.get("Contents") or []:
            key = obj["Key"]
            size = obj["Size"]
            if size == 0 or key.endswith("/"):
                continue
            try:
                client.put_object_acl(Bucket=bucket, Key=key, ACL="public-read")
                print(f"public  {key}  ({size/1e6:.1f} MB)  {base}/{key}")
                n += 1
            except Exception as e:
                print(f"FAIL    {key}  {e}")
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    print(f"Updated {n} object(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
