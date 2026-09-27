from __future__ import annotations

import hmac
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
load_dotenv(ROOT / "rag" / ".env", override=False)

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY", "")
DEEPINFRA_BASE_URL = os.getenv(
    "DEEPINFRA_BASE_URL", "https://api.deepinfra.com/v1/openai"
).rstrip("/")
DEEPINFRA_EMBED_MODEL = os.getenv("DEEPINFRA_EMBED_MODEL", "BAAI/bge-m3")
RAG_ACCESS_PASSWORD = os.getenv("RAG_ACCESS_PASSWORD", "")

# Multi-user logins: "user1:pass1,user2:pass2"
# Bayat site: username + password. Manaee can keep password-only via RAG_ACCESS_PASSWORD.
_RAG_USERS_RAW = os.getenv("RAG_USERS", "")

AUDIOS_MANAEE = ROOT / "Audios" / "Manaee"
AUDIOS_BAYAT = ROOT / "Audios" / "Bayat"
STORE_ROOT = Path(os.getenv("RAG_STORE_ROOT", str(ROOT / "rag" / "store")))
# Default store (bge-m3) — keep backward-compatible path
STORE_DIR = Path(os.getenv("RAG_STORE_DIR", str(STORE_ROOT / "manaee")))
PORTAL_DATA = ROOT / "website-portal" / "apps" / "web" / "public" / "data"


def store_dir_for(store_key: str) -> Path:
    return STORE_ROOT / store_key


def rag_users() -> dict[str, str]:
    """username → password."""
    out: dict[str, str] = {}
    raw = _RAG_USERS_RAW.strip()
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if not part or ":" not in part:
                continue
            user, pw = part.split(":", 1)
            user, pw = user.strip(), pw.strip()
            if user and pw:
                out[user] = pw
    # Backward compat: shared password-only login as username "access"
    if RAG_ACCESS_PASSWORD and "access" not in out:
        out["access"] = RAG_ACCESS_PASSWORD
    return out


def make_access_token(username: str, password: str) -> str:
    return f"{username}:{password}"


def valid_credentials(username: str, password: str) -> bool:
    expected = rag_users().get(username)
    if expected is None or not password:
        return False
    return hmac.compare_digest(expected, password)


def valid_token(token: str) -> bool:
    token = (token or "").strip()
    if not token:
        return False
    # Legacy: token was the shared password alone
    if ":" not in token:
        if RAG_ACCESS_PASSWORD and hmac.compare_digest(token, RAG_ACCESS_PASSWORD):
            return True
        return False
    user, pw = token.split(":", 1)
    return valid_credentials(user, pw)
