#!/usr/bin/env python3
"""FastAPI RAG backend for portal /ask and Bayat website /ask."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag import config
from rag.ask import answer_question, answer_question_stream, get_store
from rag.models_catalog import (
    CORPUS_OPTIONS,
    DEFAULT_CORPUS,
    DEFAULT_LLM_ID,
    catalog_public,
    corpus_catalog_public,
    embed_catalog_public,
    resolve_corpus_embed,
)

app = FastAPI(title="IslamASR RAG", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_access(authorization: str | None = Header(default=None)) -> None:
    if not config.rag_users():
        raise HTTPException(503, "RAG users not configured on server")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "login required")
    token = authorization.split(" ", 1)[1].strip()
    if not config.valid_token(token):
        raise HTTPException(401, "invalid credentials")


class LoginBody(BaseModel):
    password: str
    username: str | None = None


class AskBody(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    model: str = DEFAULT_LLM_ID
    embed_model: str | None = None
    corpus: str = DEFAULT_CORPUS
    top_k: int = Field(default=10, ge=3, le=20)


@app.get("/health")
def health():
    stores = {}
    for cid, info in CORPUS_OPTIONS.items():
        key = info.get("force_store") or info["default_embed_id"]
        # resolve store key for default embed
        try:
            _, _, store_key = resolve_corpus_embed(cid, info["default_embed_id"])
            s = get_store(store_key)
            stores[cid] = {"ok": True, "chunks": len(s.metas), "store": store_key}
        except Exception as e:
            stores[cid] = {"ok": False, "error": str(e)}
    ok = any(v.get("ok") for v in stores.values())
    return {"ok": ok, "stores": stores}


@app.get("/models")
def models(
    corpus: str = Query(default=DEFAULT_CORPUS),
    _: None = Depends(require_access),
):
    cid = corpus.lower().strip()
    info = CORPUS_OPTIONS.get(cid, CORPUS_OPTIONS[DEFAULT_CORPUS])
    return {
        "models": catalog_public(),
        "default": DEFAULT_LLM_ID,
        "corpus": cid,
        "corpora": corpus_catalog_public(),
        "embed_models": embed_catalog_public(cid),
        "default_embed": info["default_embed_id"],
    }


@app.post("/login")
def login(body: LoginBody):
    users = config.rag_users()
    if not users:
        raise HTTPException(503, "RAG users not configured")
    username = (body.username or "access").strip()
    password = body.password or ""
    if not config.valid_credentials(username, password):
        raise HTTPException(401, "invalid username or password")
    token = config.make_access_token(username, password)
    return {"token": token, "ok": True, "username": username}


@app.post("/ask")
def ask(body: AskBody, _: None = Depends(require_access)):
    try:
        return answer_question(
            body.question,
            model_id=body.model,
            embed_model_id=body.embed_model,
            corpus=body.corpus,
            top_k=body.top_k,
        )
    except KeyError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@app.post("/ask/stream")
def ask_stream(body: AskBody, _: None = Depends(require_access)):
    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        answer_question_stream(
            body.question,
            model_id=body.model,
            embed_model_id=body.embed_model,
            corpus=body.corpus,
            top_k=body.top_k,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/source")
def source(
    lecturer: str,
    course: str,
    session_id: str,
    corpus: str = Query(default=DEFAULT_CORPUS),
    _: None = Depends(require_access),
):
    """Return full raw prose for highlight modal (from indexed source paths)."""
    try:
        _, _, store_key = resolve_corpus_embed(corpus, None)
    except KeyError as e:
        raise HTTPException(400, str(e)) from e
    store = get_store(store_key)
    meta = next(
        (
            m
            for m in store.metas
            if m["lecturer"] == lecturer
            and m["course"] == course
            and m["session_id"] == session_id
        ),
        None,
    )
    if not meta:
        raise HTTPException(404, "session not in index")
    path = ROOT / meta["source_path"]
    if not path.exists():
        raise HTTPException(404, "source file missing")
    from rag.parse_transcript import parse_transcript_file

    parsed = parse_transcript_file(path)
    return {
        "lecturer": lecturer,
        "course": course,
        "session_id": session_id,
        "corpus": corpus,
        "prose": parsed.prose,
        "portal_path": meta.get("portal_path"),
        "source_path": meta.get("source_path"),
    }


def main():
    import uvicorn

    uvicorn.run("rag.server:app", host="127.0.0.1", port=8001, reload=False)


if __name__ == "__main__":
    main()
