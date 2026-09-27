#!/usr/bin/env python3
"""Compare Bayat raw .txt on disk vs local vector store (and optionally VPS health).

Usage (from repo root):
  .venv/bin/python -m rag.check_bayat_coverage
  .venv/bin/python -m rag.check_bayat_coverage --prod
  .venv/bin/python -m rag.check_bayat_coverage --json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag import config
from rag.index_bayat import discover_bayat_txt

PROD_HEALTH = "https://185.204.168.239.sslip.io/rag/health"
STORE_KEY = "bayat_qwen3_8b"


def disk_sessions(root: Path) -> dict[str, set[str]]:
    """course → set of session ids that have a raw .txt."""
    out: dict[str, set[str]] = defaultdict(set)
    for p in discover_bayat_txt(root):
        course = p.parent.parent.name.lower()
        session = p.parent.name
        out[course].add(session)
    return dict(out)


def store_sessions(store_dir: Path) -> tuple[dict[str, set[str]], dict, int]:
    """course → sessions in chunks.jsonl, plus info.json and chunk count."""
    meta_path = store_dir / "chunks.jsonl"
    info_path = store_dir / "info.json"
    info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
    by_course: dict[str, set[str]] = defaultdict(set)
    n = 0
    if not meta_path.exists():
        return {}, info, 0
    with meta_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = json.loads(line)
            by_course[str(m.get("course", "?")).lower()].add(str(m.get("session_id", "?")))
            n += 1
    return dict(by_course), info, n


def fetch_prod_health(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Bayat disk ↔ store ↔ production coverage")
    ap.add_argument("--prod", action="store_true", help="also hit VPS /rag/health")
    ap.add_argument("--health-url", default=PROD_HEALTH)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    root = config.AUDIOS_BAYAT
    store_dir = config.store_dir_for(STORE_KEY)
    on_disk = disk_sessions(root)
    in_store, info, n_chunks = store_sessions(store_dir)

    disk_keys = {(c, s) for c, ss in on_disk.items() for s in ss}
    store_keys = {(c, s) for c, ss in in_store.items() for s in ss}
    missing = sorted(disk_keys - store_keys)  # on disk, not embedded
    orphan = sorted(store_keys - disk_keys)  # embedded, txt file gone
    ok = sorted(disk_keys & store_keys)

    report = {
        "audios_root": str(root),
        "store_dir": str(store_dir),
        "disk_courses": len(on_disk),
        "disk_sessions": len(disk_keys),
        "store_courses": len(in_store),
        "store_sessions": len(store_keys),
        "store_chunks": n_chunks,
        "store_info": info,
        "matched_sessions": len(ok),
        "missing_sessions": [{"course": c, "session": s} for c, s in missing],
        "orphan_sessions": [{"course": c, "session": s} for c, s in orphan],
        "missing_courses": sorted(set(on_disk) - set(in_store)),
        "orphan_courses": sorted(set(in_store) - set(on_disk)),
        "coverage_ok": len(missing) == 0 and len(orphan) == 0,
    }

    if args.prod:
        try:
            health = fetch_prod_health(args.health_url)
            bayat = (health.get("stores") or {}).get("bayat") or {}
            report["prod_health"] = health
            report["prod_bayat_chunks"] = bayat.get("chunks")
            report["prod_matches_local"] = bayat.get("chunks") == n_chunks
        except Exception as e:
            report["prod_health_error"] = str(e)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Bayat RAG coverage")
        print(f"  disk:  {report['disk_courses']} courses · {report['disk_sessions']} sessions")
        print(
            f"  store: {report['store_courses']} courses · {report['store_sessions']} sessions · "
            f"{report['store_chunks']} chunks"
        )
        if info:
            print(
                f"  info:  embed={info.get('embed_model')} · n_files={info.get('n_files')} · "
                f"dim={info.get('dim')}"
            )
        print(f"  match: {report['matched_sessions']} sessions")
        if report["missing_courses"]:
            print(f"  NEW courses (not in store): {', '.join(report['missing_courses'])}")
        if missing:
            print(f"  MISSING sessions (embed these): {len(missing)}")
            by = Counter(c for c, _ in missing)
            for course, n in sorted(by.items()):
                sess = sorted(s for c, s in missing if c == course)
                preview = ", ".join(sess[:8]) + ("…" if len(sess) > 8 else "")
                print(f"    {course}: {n}  [{preview}]")
        if orphan:
            print(f"  ORPHAN in store (no .txt on disk): {len(orphan)}")
            for c, s in orphan[:20]:
                print(f"    {c}/{s}")
            if len(orphan) > 20:
                print(f"    … +{len(orphan) - 20} more")
        if args.prod:
            if "prod_health_error" in report:
                print(f"  prod: ERROR {report['prod_health_error']}")
            else:
                pc = report.get("prod_bayat_chunks")
                same = report.get("prod_matches_local")
                print(f"  prod: bayat chunks={pc} · matches local={'yes' if same else 'NO'}")
        print()
        if report["coverage_ok"]:
            print("OK — every on-disk session is in the local store.")
        else:
            print("GAP — run indexing for missing sessions, then deploy (see rag/BAYAT_INDEX.md).")
            raise SystemExit(2)


if __name__ == "__main__":
    main()
