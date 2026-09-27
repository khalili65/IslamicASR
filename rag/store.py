from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class VectorStore:
    """Simple persistent cosine store (numpy + jsonl metadata)."""

    def __init__(self, dir_path: Path):
        self.dir = Path(dir_path)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.dir / "chunks.jsonl"
        self.emb_path = self.dir / "embeddings.npy"
        self.info_path = self.dir / "info.json"
        self.ids: list[str] = []
        self.metas: list[dict] = []
        self.emb: np.ndarray | None = None

    def load(self) -> bool:
        if not self.emb_path.exists() or not self.meta_path.exists():
            return False
        self.metas = []
        self.ids = []
        with self.meta_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m = json.loads(line)
                self.metas.append(m)
                self.ids.append(m["chunk_id"])
        self.emb = np.load(self.emb_path)
        if len(self.metas) != len(self.emb):
            raise RuntimeError("embeddings/metadata length mismatch")
        return True

    def save(self, metas: list[dict], embeddings: np.ndarray, info: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with self.meta_path.open("w", encoding="utf-8") as f:
            for m in metas:
                f.write(json.dumps(m, ensure_ascii=False) + "\n")
        np.save(self.emb_path, embeddings.astype(np.float32))
        self.info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        self.metas = metas
        self.ids = [m["chunk_id"] for m in metas]
        self.emb = embeddings.astype(np.float32)

    def search(self, query_vec: list[float], top_k: int = 10) -> list[tuple[dict, float]]:
        if self.emb is None or not len(self.metas):
            raise RuntimeError("store not loaded — run indexer first")
        q = np.asarray(query_vec, dtype=np.float32)
        q = q / (np.linalg.norm(q) + 1e-9)
        mat = self.emb
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        sims = (mat / norms) @ q
        k = min(top_k, len(sims))
        idx = np.argpartition(-sims, k - 1)[:k]
        idx = idx[np.argsort(-sims[idx])]
        return [(self.metas[i], float(sims[i])) for i in idx]

    def get(self, chunk_id: str) -> dict | None:
        try:
            i = self.ids.index(chunk_id)
        except ValueError:
            return None
        return self.metas[i]
