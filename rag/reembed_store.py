#!/usr/bin/env python3
"""Re-embed existing Manaee chunks with another DeepInfra embedding model.

Reuses chunk texts from an existing store (default: rag/store/manaee) so both
embedding indexes share identical chunk boundaries for fair comparison.
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
from rag.deepinfra import embed_texts
from rag.models_catalog import get_embed
from rag.store import VectorStore


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--embed-model",
        default="Qwen/Qwen3-Embedding-8B",
        help="DeepInfra embedding model id",
    )
    ap.add_argument(
        "--source-store",
        default="manaee",
        help="Existing store key to copy chunk metadata from",
    )
    ap.add_argument("--batch-embed", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    embed = get_embed(args.embed_model)
    src = VectorStore(config.store_dir_for(args.source_store))
    if not src.load():
        raise SystemExit(f"source store missing: {src.dir}")

    metas = list(src.metas)
    if args.limit:
        metas = metas[: args.limit]
    texts = [m["text"] for m in metas]
    print(f"Re-embedding {len(texts)} chunks with {embed.id} → store/{embed.store_key}")

    vectors: list[list[float]] = []
    bs = args.batch_embed
    for i in range(0, len(texts), bs):
        part = texts[i : i + bs]
        vectors.extend(embed_texts(part, model=embed.id))
        print(f"  embedded {min(i + bs, len(texts))}/{len(texts)}")

    emb = np.asarray(vectors, dtype=np.float32)
    out = VectorStore(config.store_dir_for(embed.store_key))
    out.save(
        metas,
        emb,
        info={
            "lecturer": "manaee",
            "embed_model": embed.id,
            "n_chunks": len(metas),
            "dim": int(emb.shape[1]),
            "source_store": args.source_store,
        },
    )
    print(f"Saved → {out.dir} ({len(metas)} chunks, dim={emb.shape[1]})")


if __name__ == "__main__":
    main()
