#!/usr/bin/env python3
"""Upload lecture audio to Arvan Object Storage (S3-compatible).

Loads credentials from repo-root .env.arvan (gitignored).

Usage (from repo root):
  .venv/bin/python website/scripts/upload_arvan.py
  .venv/bin/python website/scripts/upload_arvan.py Audios/Bayat/marefat_nafs
  .venv/bin/python website/scripts/upload_arvan.py Audios/Bayat/marefat_nafs/001
  .venv/bin/python website/scripts/upload_arvan.py --scripts-only Audios/Bayat/marefat_nafs
"""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from botocore.client import Config
from botocore.exceptions import ClientError
import boto3

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_env(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        raise SystemExit(f"Missing {path}. Copy .env.arvan.example to .env.arvan")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def s3_client(env: Dict[str, str]):
    return boto3.client(
        "s3",
        endpoint_url=env["ARVAN_ENDPOINT"],
        aws_access_key_id=env["ARVAN_ACCESS_KEY"],
        aws_secret_access_key=env["ARVAN_SECRET_KEY"],
        region_name=env.get("ARVAN_REGION", "ir-thr-at1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def session_has_script(session_dir: Path) -> bool:
    return bool(
        list(session_dir.glob("*.corrected.txt"))
        or list(session_dir.glob("*.corrected.md"))
    )


def pick_audio(session_dir: Path) -> Optional[Path]:
    play = sorted(session_dir.glob("*_play.m4a"))
    if play:
        return play[0]
    mp3s = sorted(session_dir.glob("*.mp3"))
    return mp3s[0] if mp3s else None


def object_key(file_path: Path) -> str:
    """Audios/Bayat/... -> bayat/..."""
    rel = file_path.resolve().relative_to((REPO_ROOT / "Audios").resolve())
    parts = list(rel.parts)
    parts[0] = parts[0].lower()
    return "/".join(parts)


def iter_targets(src: Path, scripts_only: bool) -> List[Path]:
    if src.is_file():
        return [src]

    if (src / "Audios").exists():
        raise SystemExit("Pass a path under Audios/, not the repo root")

    # Session dir: .../NNN
    if src.name.isdigit() and src.is_dir():
        candidates = [src]
    else:
        candidates = sorted(
            p for p in src.iterdir() if p.is_dir() and p.name.isdigit()
        )
        if not candidates:
            files: List[Path] = []
            for pat in ("*_play.m4a", "*.mp3"):
                files.extend(src.glob(pat))
            return sorted(files)

    out: List[Path] = []
    for session in candidates:
        if scripts_only and not session_has_script(session):
            continue
        audio = pick_audio(session)
        if audio:
            out.append(audio)
    return out


def already_uploaded(client, bucket: str, key: str, size: int) -> bool:
    try:
        head = client.head_object(Bucket=bucket, Key=key)
        return int(head.get("ContentLength", -1)) == size
    except ClientError:
        return False


def upload_one(client, bucket: str, file_path: Path, key: str) -> None:
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    extra = {"ContentType": content_type}
    try:
        client.upload_file(
            str(file_path), bucket, key, ExtraArgs={**extra, "ACL": "public-read"}
        )
    except ClientError as exc:
        # Some Arvan buckets reject object ACLs when public access is bucket-level.
        code = exc.response.get("Error", {}).get("Code", "")
        if code in {"AccessControlListNotSupported", "InvalidArgument", "AccessDenied"}:
            client.upload_file(str(file_path), bucket, key, ExtraArgs=extra)
        else:
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "src",
        nargs="?",
        default="Audios/Bayat/marefat_nafs",
        help="File or directory under Audios/",
    )
    parser.add_argument(
        "--scripts-only",
        action="store_true",
        help="Only sessions that have a .corrected.txt/.md",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-upload even if same-sized object exists",
    )
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    env = load_env(REPO_ROOT / ".env.arvan")
    bucket = env["ARVAN_BUCKET"]
    client = s3_client(env)

    src = Path(args.src)
    if not src.exists():
        raise SystemExit(f"Not found: {src}")

    targets = iter_targets(src, scripts_only=args.scripts_only)
    if not targets:
        print("Nothing to upload.")
        return 0

    print(f"Bucket : {bucket}")
    print(f"Endpoint: {env['ARVAN_ENDPOINT']}")
    print(f"Files  : {len(targets)}")
    print()

    uploaded = skipped = failed = 0
    t0 = time.time()
    for file_path in targets:
        key = object_key(file_path)
        size = file_path.stat().st_size
        if not args.force and already_uploaded(client, bucket, key, size):
            print(f"skip  s3://{bucket}/{key} ({size/1e6:.1f} MB)")
            skipped += 1
            continue

        print(f"→     s3://{bucket}/{key} ({size/1e6:.1f} MB) …", flush=True)
        start = time.time()
        try:
            upload_one(client, bucket, file_path, key)
            elapsed = time.time() - start
            mbps = (size / 1e6) / max(elapsed, 0.001)
            print(f"ok    {elapsed:.1f}s  ({mbps:.2f} MB/s)")
            uploaded += 1
        except Exception as exc:
            print(f"FAIL  {exc}")
            failed += 1

    total = time.time() - t0
    print()
    print(f"Uploaded {uploaded}, skipped {skipped}, failed {failed} in {total/60:.1f} min")
    base = env.get("NEXT_PUBLIC_MEDIA_BASE", "").rstrip("/")
    if base:
        print(f"Public base: {base}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
