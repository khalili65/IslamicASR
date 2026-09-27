#!/usr/bin/env python3
"""Index Audios/Manaee raw .txt transcripts with DeepInfra BAAI/bge-m3."""

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
from rag.parse_transcript import parse_transcript_file
from rag.store import VectorStore


def discover_manaee_txt(root: Path) -> list[Path]:
    files: list[Path] = []
    for term_dir in sorted(root.glob("Term*")):
        if not term_dir.is_dir():
            continue
        for session_dir in sorted(term_dir.iterdir()):
            if not session_dir.is_dir() or not session_dir.name.isdigit():
                continue
            for p in session_dir.glob("*.txt"):
                name = p.name
                if name.endswith(".book.md") or name.endswith(".summary.md"):
                    continue
                if ".book." in name or ".summary." in name:
                    continue
                files.append(p)
    return files


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="index only first N sessions (smoke test)")
    ap.add_argument("--batch-embed", type=int, default=64)
    args = ap.parse_args()

    root = config.AUDIOS_MANAEE
    files = discover_manaee_txt(root)
    if args.limit:
        files = files[: args.limit]
    print(f"Found {len(files)} Manaee raw transcripts under {root}")

    all_chunks = []
    for p in files:
        # Audios/Manaee/Term1/024/file.txt
        session_id = p.parent.name
        course = p.parent.parent.name.lower()  # term1
        parsed = parse_transcript_file(p)
        chunks = chunk_prose(
            parsed.prose,
            words=parsed.words,
            lecturer="manaee",
            course=course,
            session_id=session_id,
            source_path=str(p.relative_to(config.ROOT)),
        )
        all_chunks.extend(chunks)
        print(f"  {course}/{session_id}: {len(chunks)} chunks, words={len(parsed.words)}")

    if not all_chunks:
        raise SystemExit("no chunks produced")

    texts = [c.text for c in all_chunks]
    print(f"Embedding {len(texts)} chunks with {config.DEEPINFRA_EMBED_MODEL} …")
    vectors: list[list[float]] = []
    bs = args.batch_embed
    for i in range(0, len(texts), bs):
        part = texts[i : i + bs]
        vectors.extend(embed_texts(part))
        print(f"  embedded {min(i + bs, len(texts))}/{len(texts)}")

    emb = np.asarray(vectors, dtype=np.float32)
    metas = [c.to_meta() for c in all_chunks]
    store = VectorStore(config.STORE_DIR)
    store.save(
        metas,
        emb,
        info={
            "lecturer": "manaee",
            "embed_model": config.DEEPINFRA_EMBED_MODEL,
            "n_chunks": len(metas),
            "n_files": len(files),
            "dim": int(emb.shape[1]),
        },
    )
    print(f"Saved → {config.STORE_DIR} ({len(metas)} chunks, dim={emb.shape[1]})")


if __name__ == "__main__":
    main()
