"""IslamASR multi-provider speech-to-text toolkit."""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["load_dotenv", "PROJECT_ROOT"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path | None = None) -> None:
    """Minimal .env loader so python-dotenv is not a hard dependency."""
    path = path or PROJECT_ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
