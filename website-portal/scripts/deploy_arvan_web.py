#!/usr/bin/env python3
"""Upload website/apps/web/out to Arvan Object Storage (static site bucket).

Used by GitHub Actions. Requires env:
  ARVAN_ACCESS_KEY, ARVAN_SECRET_KEY
  ARVAN_ENDPOINT (default https://s3.ir-thr-at1.arvanstorage.ir)
  ARVAN_REGION (default ir-thr-at1)
  ARVAN_WEB_BUCKET (default islamic-asr-web)

Optional:
  OUT_DIR — path to static export (default: website/apps/web/out relative to repo root)
"""

from __future__ import annotations

import mimetypes
import os
import sys
import time
from pathlib import Path

from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from boto3.s3.transfer import TransferConfig
import boto3

REPO_ROOT = Path(__file__).resolve().parents[2]


def content_type_for(path: Path) -> str:
    if path.suffix == ".html":
        return "text/html; charset=utf-8"
    if path.suffix == ".js":
        return "application/javascript; charset=utf-8"
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".json":
        return "application/json; charset=utf-8"
    if path.suffix == ".txt":
        return "text/plain; charset=utf-8"
    if path.suffix == ".svg":
        return "image/svg+xml"
    if path.suffix == ".xml":
        return "application/xml"
    guessed = mimetypes.guess_type(path.name)[0]
    return guessed or "application/octet-stream"


def main() -> int:
    access = os.environ.get("ARVAN_ACCESS_KEY", "").strip()
    secret = os.environ.get("ARVAN_SECRET_KEY", "").strip()
    if not access or not secret:
        print("Missing ARVAN_ACCESS_KEY / ARVAN_SECRET_KEY", file=sys.stderr)
        return 1

    endpoint = os.environ.get(
        "ARVAN_ENDPOINT", "https://s3.ir-thr-at1.arvanstorage.ir"
    ).strip()
    region = os.environ.get("ARVAN_REGION", "ir-thr-at1").strip()
    bucket = os.environ.get("ARVAN_WEB_BUCKET", "islamic-asr-web").strip()
    out = Path(os.environ.get("OUT_DIR", str(REPO_ROOT / "website/apps/web/out")))

    if not out.is_dir():
        print(f"Missing export directory: {out}", file=sys.stderr)
        return 1

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name=region,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 10, "mode": "standard"},
        ),
    )
    transfer = TransferConfig(
        multipart_threshold=8 * 1024 * 1024,
        max_concurrency=4,
        use_threads=True,
    )

    files = sorted(p for p in out.rglob("*") if p.is_file())
    print(f"Uploading {len(files)} files → s3://{bucket}/ via {endpoint}")

    uploaded = skipped = failed = 0
    t0 = time.time()
    for index, path in enumerate(files, 1):
        key = str(path.relative_to(out)).replace("\\", "/")
        size = path.stat().st_size
        try:
            head = client.head_object(Bucket=bucket, Key=key)
            if int(head.get("ContentLength", -1)) == size:
                skipped += 1
                continue
        except ClientError:
            pass

        extra = {"ContentType": content_type_for(path), "ACL": "public-read"}
        last_error = None
        ok = False
        for attempt in range(1, 6):
            try:
                client.upload_file(
                    str(path), bucket, key, ExtraArgs=extra, Config=transfer
                )
                ok = True
                break
            except ClientError as exc:
                last_error = exc
                code = exc.response.get("Error", {}).get("Code", "")
                if code in {
                    "AccessControlListNotSupported",
                    "InvalidArgument",
                    "AccessDenied",
                } and "ACL" in extra:
                    extra = {k: v for k, v in extra.items() if k != "ACL"}
                    continue
                time.sleep(min(2**attempt, 20))
            except (BotoCoreError, OSError) as exc:
                last_error = exc
                time.sleep(min(2**attempt, 20))

        if ok:
            uploaded += 1
            if uploaded % 50 == 0 or index == len(files):
                elapsed = time.time() - t0
                print(
                    f"[{index}/{len(files)}] uploaded={uploaded} "
                    f"skipped={skipped} failed={failed} ({elapsed/60:.1f} min)"
                )
        else:
            failed += 1
            print(f"FAIL {key}: {last_error}", file=sys.stderr)

    elapsed = time.time() - t0
    print(
        f"Done: uploaded={uploaded} skipped={skipped} failed={failed} "
        f"in {elapsed/60:.1f} min"
    )
    print(f"Site (object URL): https://{bucket}.s3.{region}.arvanstorage.ir/")
    return 1 if failed else 0


if __name__ == "__main__":
    # Python 3.9 compat for Actions + local
    if sys.version_info < (3, 10):
        # rewrite union used only in annotation above for 3.9 — already from __future__
        pass
    raise SystemExit(main())
