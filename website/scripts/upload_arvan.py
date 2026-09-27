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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    """Audios/Bayat/... -> bayat/... (lecturer + course lowercased to match site URLs).

    Prefer the logical path under Audios/ so lecturer symlinks (e.g. Shojai →
    AyatollahShojaee) keep the portal slug in the object key.
    """
    audio_root = (REPO_ROOT / "Audios").absolute()
    path = file_path if file_path.is_absolute() else (Path.cwd() / file_path)
    path = path.absolute()
    try:
        rel = path.relative_to(audio_root)
    except ValueError:
        rel = path.resolve().relative_to(audio_root.resolve())
    parts = list(rel.parts)
    # Match build_content.py: lecturer/course slugs are folder names lowercased.
    if len(parts) >= 1:
        parts[0] = parts[0].lower()
    if len(parts) >= 2:
        parts[1] = parts[1].lower()
    # Physical folder remaps when a path was resolved through a symlink.
    remap = {"ayatollahshojaee": "shojai"}
    if parts and parts[0] in remap:
        parts[0] = remap[parts[0]]
    # Nested Tadabor_Sobohi/Manaee/... → manaee/...
    if len(parts) >= 2 and parts[0] == "tadabor_sobohi" and parts[1] == "manaee":
        parts = parts[1:]
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


# 5 MiB parts (S3 minimum for non-final parts). Smaller = more resume checkpoints.
PART_SIZE = 5 * 1024 * 1024
PART_RETRIES = 8
# Concurrent part uploads per file (helps high-latency links).
PART_CONCURRENCY = int(os.environ.get("ARVAN_PART_CONCURRENCY", "2"))


def already_uploaded(client, bucket: str, key: str, size: int) -> bool:
    try:
        head = client.head_object(Bucket=bucket, Key=key)
        return int(head.get("ContentLength", -1)) == size
    except ClientError:
        return False


def _find_multipart(client, bucket: str, key: str) -> Optional[str]:
    """Return an in-progress UploadId for key, if any."""
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Prefix": key}
        if token:
            kwargs["KeyMarker"] = token
        resp = client.list_multipart_uploads(**kwargs)
        for upload in resp.get("Uploads") or []:
            if upload.get("Key") == key:
                return upload["UploadId"]
        if not resp.get("IsTruncated"):
            return None
        token = resp.get("NextKeyMarker") or resp.get("UploadIdMarker")


def _list_completed_parts(client, bucket: str, key: str, upload_id: str) -> Dict[int, str]:
    done: Dict[int, str] = {}
    token = None
    while True:
        kwargs = {"Bucket": bucket, "Key": key, "UploadId": upload_id}
        if token:
            kwargs["PartNumberMarker"] = token
        resp = client.list_parts(**kwargs)
        for part in resp.get("Parts") or []:
            done[int(part["PartNumber"])] = part["ETag"]
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextPartNumberMarker")
    return done


def _put_part_with_retries(
    client,
    bucket: str,
    key: str,
    upload_id: str,
    part_number: int,
    body: bytes,
) -> str:
    last: Optional[Exception] = None
    for attempt in range(1, PART_RETRIES + 1):
        try:
            resp = client.upload_part(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id,
                PartNumber=part_number,
                Body=body,
            )
            return resp["ETag"]
        except Exception as exc:  # noqa: BLE001 — retry any transient failure
            last = exc
            time.sleep(min(2**attempt, 30))
    raise RuntimeError(
        "part %s failed after %s tries: %s" % (part_number, PART_RETRIES, last)
    )


def resumable_multipart_upload(
    client, bucket: str, file_path: Path, key: str, content_type: str
) -> None:
    """Upload with multipart parts so a dropped connection can resume.

    Completed parts stay on the server (same UploadId). Re-running this function
    skips parts that already have an ETag and only sends the rest.
    """
    size = file_path.stat().st_size
    upload_id = _find_multipart(client, bucket, key)
    if upload_id:
        print(f"      resume multipart UploadId={upload_id[:20]}…", flush=True)
    else:
        create_kwargs = {
            "Bucket": bucket,
            "Key": key,
            "ContentType": content_type,
        }
        try:
            create_kwargs["ACL"] = "public-read"
            upload_id = client.create_multipart_upload(**create_kwargs)["UploadId"]
        except ClientError:
            create_kwargs.pop("ACL", None)
            upload_id = client.create_multipart_upload(**create_kwargs)["UploadId"]
        print(f"      new multipart UploadId={upload_id[:20]}…", flush=True)

    done = _list_completed_parts(client, bucket, key, upload_id)
    if done:
        print(f"      already have {len(done)} part(s) on server", flush=True)

    plan: List[Tuple[int, int, int]] = []
    offset = 0
    part_number = 1
    while offset < size:
        length = min(PART_SIZE, size - offset)
        plan.append((part_number, offset, length))
        offset += length
        part_number += 1

    etags: Dict[int, str] = dict(done)
    pending = [(n, off, ln) for n, off, ln in plan if n not in done]
    uploaded_bytes = sum(ln for n, off, ln in plan if n in done)

    def _send(item: Tuple[int, int, int]) -> Tuple[int, str, int]:
        n, off, ln = item
        with file_path.open("rb") as handle:
            handle.seek(off)
            body = handle.read(ln)
        etag = _put_part_with_retries(client, bucket, key, upload_id, n, body)
        return n, etag, ln

    if pending:
        workers = min(PART_CONCURRENCY, len(pending))
        print(
            f"      uploading {len(pending)} part(s) with {workers} streams",
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_send, item) for item in pending]
            for fut in as_completed(futures):
                n, etag, ln = fut.result()
                etags[n] = etag
                uploaded_bytes += ln
                pct = 100.0 * uploaded_bytes / max(size, 1)
                print(
                    f"      part {n} ok  ({uploaded_bytes/1e6:.1f}/{size/1e6:.1f} MB, {pct:.0f}%)",
                    flush=True,
                )

    parts_out = [{"ETag": etags[n], "PartNumber": n} for n, _, _ in plan]

    client.complete_multipart_upload(
        Bucket=bucket,
        Key=key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts_out},
    )
    try:
        client.put_object_acl(Bucket=bucket, Key=key, ACL="public-read")
    except ClientError:
        pass


def upload_one(client, bucket: str, file_path: Path, key: str) -> None:
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    # Prefer resumable multipart for anything larger than one part.
    if file_path.stat().st_size > PART_SIZE:
        resumable_multipart_upload(client, bucket, file_path, key, content_type)
        return

    extra = {"ContentType": content_type}
    last: Optional[Exception] = None
    for attempt in range(1, PART_RETRIES + 1):
        try:
            try:
                client.upload_file(
                    str(file_path),
                    bucket,
                    key,
                    ExtraArgs={**extra, "ACL": "public-read"},
                )
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in {
                    "AccessControlListNotSupported",
                    "InvalidArgument",
                    "AccessDenied",
                }:
                    client.upload_file(str(file_path), bucket, key, ExtraArgs=extra)
                else:
                    raise
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(min(2**attempt, 30))
    raise RuntimeError("upload failed after retries: %s" % last)


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
    env_file = Path(
        os.environ.get("ARVAN_ENV_FILE", str(REPO_ROOT / ".env.arvan"))
    )
    env = load_env(env_file)
    bucket = os.environ.get("ARVAN_BUCKET", env["ARVAN_BUCKET"]).strip() or env[
        "ARVAN_BUCKET"
    ]
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
