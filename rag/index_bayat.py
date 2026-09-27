#!/usr/bin/env python3
"""Index Audios/Bayat raw .txt transcripts with Qwen3-Embedding-8B.

Full rebuild (default):
  .venv/bin/python -m rag.index_bayat

Only new / changed courses (merge into existing store):
  .venv/bin/python -m rag.index_bayat --course qalb_newcourse
  .venv/bin/python -m rag.index_bayat --course qalb_manzel --session 041 --session 042

Then check + push:
  .venv/bin/python -m rag.check_bayat_coverage --prod
  bash rag/deploy/deploy_to_vps.sh
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag import config
from rag.chunking import chunk_prose
from rag.deepinfra import embed_texts
from rag.models_catalog import get_embed
from rag.parse_transcript import parse_transcript_file
from rag.store import VectorStore

SKIP_COURSE_DIRS = {"_eitaa_tmp", "_tmp", ".git"}
STORE_KEY = "bayat_qwen3_8b"


def discover_bayat_txt(root: Path) -> list[Path]:
    files: list[Path] = []
    if not root.is_dir():
        return files
    for course_dir in sorted(root.iterdir()):
        if not course_dir.is_dir() or course_dir.name in SKIP_COURSE_DIRS:
            continue
        if course_dir.name.startswith("_"):
            continue
        for session_dir in sorted(course_dir.iterdir()):
            if not session_dir.is_dir():
                continue
            # session folders are usually numeric (001, 135, …)
            if not session_dir.name.isdigit():
                continue
            for p in session_dir.glob("*.txt"):
                name = p.name
                if name.endswith(".book.md") or name.endswith(".summary.md"):
                    continue
                if ".book." in name or ".summary." in name:
                    continue
                files.append(p)
    return files


def _course_session(path: Path) -> tuple[str, str]:
    return path.parent.parent.name.lower(), path.parent.name


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="index only first N sessions (debug)")
    ap.add_argument("--batch-embed", type=int, default=32)
    ap.add_argument(
        "--embed-model",
        default="Qwen/Qwen3-Embedding-8B",
        help="DeepInfra embedding model id",
    )
    ap.add_argument(
        "--course",
        action="append",
        default=[],
        help="Only (re)index this course slug (repeatable). Merges into existing store.",
    )
    ap.add_argument(
        "--session",
        action="append",
        default=[],
        help="Only these session ids (e.g. 041). Requires --course. Merges into store.",
    )
    ap.add_argument(
        "--full",
        action="store_true",
        help="Force full rebuild even if --course is set.",
    )
    args = ap.parse_args()

    courses_filter = {c.lower().strip() for c in args.course if c.strip()}
    sessions_filter = {s.strip() for s in args.session if s.strip()}
    if sessions_filter and not courses_filter:
        raise SystemExit("--session requires at least one --course")

    merge = bool(courses_filter) and not args.full

    embed = get_embed(args.embed_model)
    root = config.AUDIOS_BAYAT
    files = discover_bayat_txt(root)
    if courses_filter:
        files = [p for p in files if _course_session(p)[0] in courses_filter]
    if sessions_filter:
        files = [p for p in files if _course_session(p)[1] in sessions_filter]
    if args.limit:
        files = files[: args.limit]

    print(f"Found {len(files)} Bayat raw transcripts under {root}")
    if merge:
        print(f"Mode=MERGE courses={sorted(courses_filter) or '—'} sessions={sorted(sessions_filter) or 'all'}")
    else:
        print("Mode=FULL rebuild")
    print(f"Embed model={embed.id} → store/{STORE_KEY}")

    all_chunks = []
    for p in files:
        session_id = p.parent.name
        course = p.parent.parent.name.lower()
        parsed = parse_transcript_file(p)
        chunks = chunk_prose(
            parsed.prose,
            words=parsed.words,
            lecturer="bayat",
            course=course,
            session_id=session_id,
            source_path=str(p.relative_to(config.ROOT)),
        )
        all_chunks.extend(chunks)
        print(f"  {course}/{session_id}: {len(chunks)} chunks, words={len(parsed.words)}")

    if not all_chunks:
        raise SystemExit("no chunks produced")

    texts = [c.text for c in all_chunks]
    print(f"Embedding {len(texts)} chunks with {embed.id} …")
    vectors: list[list[float]] = []
    bs = args.batch_embed
    for i in range(0, len(texts), bs):
        part = texts[i : i + bs]
        vectors.extend(embed_texts(part, model=embed.id))
        print(f"  embedded {min(i + bs, len(texts))}/{len(texts)}", flush=True)

    new_emb = np.asarray(vectors, dtype=np.float32)
    new_metas = [c.to_meta() for c in all_chunks]
    out = VectorStore(config.store_dir_for(STORE_KEY))

    if merge and out.load():
        assert out.emb is not None
        drop_courses = courses_filter
        drop_sessions = sessions_filter  # empty = drop whole course(s)
        keep_idx = []
        for i, m in enumerate(out.metas):
            c = str(m.get("course", "")).lower()
            s = str(m.get("session_id", ""))
            if c not in drop_courses:
                keep_idx.append(i)
                continue
            if drop_sessions and s not in drop_sessions:
                keep_idx.append(i)
                continue
            # else: drop (will be replaced by new chunks)
        kept_metas = [out.metas[i] for i in keep_idx]
        kept_emb = out.emb[keep_idx]
        metas = kept_metas + new_metas
        emb = np.vstack([kept_emb, new_emb]) if len(kept_metas) else new_emb
        print(
            f"Merged: kept {len(kept_metas)} old + {len(new_metas)} new = {len(metas)} chunks"
        )
    else:
        if merge:
            print("No existing store — writing fresh store from selected files only")
        metas = new_metas
        emb = new_emb

    # unique session/file count in final store
    n_files = len({(m.get("course"), m.get("session_id")) for m in metas})
    out.save(
        metas,
        emb,
        info={
            "lecturer": "bayat",
            "corpus": "bayat",
            "embed_model": embed.id,
            "n_chunks": len(metas),
            "n_files": n_files,
            "dim": int(emb.shape[1]),
        },
    )
    print(f"Saved → {out.dir} ({len(metas)} chunks, dim={emb.shape[1]}, sessions={n_files})")


if __name__ == "__main__":
    main()
