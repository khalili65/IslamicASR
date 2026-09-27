# RAG (Manaee first)

Transparent Q&A over lecture **raw transcripts**, DeepInfra embeddings + LLM.

## Locked for v1

- Corpus: `Audios/Manaee` raw `.txt` only
- Embeds (selectable): `BAAI/bge-m3`, `Qwen/Qwen3-Embedding-8B`
- LLMs (user-selectable, cost shown in UI):
  - `openai/gpt-oss-120b`
  - `zai-org/GLM-5.3`
  - `moonshotai/Kimi-K2.6`
- Portal page: `/ask/` — password-gated (~10 people)
- API: FastAPI on `:8000` (portal is static export, so RAG cannot live in Next.js)

## Local setup

```bash
# deps (once)
.venv/bin/pip install --index-url https://pypi.org/simple -r rag/requirements.txt

# .env (repo root) needs:
# DEEPINFRA_API_KEY=...
# DEEPINFRA_EMBED_MODEL=BAAI/bge-m3
# RAG_ACCESS_PASSWORD=...   # share only with the 10 people

# index (full Manaee ~150 sessions)
.venv/bin/python -m rag.index_manaee

# API
.venv/bin/python -m rag.server

# portal (another terminal)
cd website-portal/apps/web && NEXT_PUBLIC_RAG_API_URL=http://127.0.0.1:8000 npm run dev
# open http://localhost:3001/ask/
```

## Flow

1. Login with `RAG_ACCESS_PASSWORD`
2. Pick LLM (cost shown next to name)
3. Ask in any language → translate to FA → retrieve → answer → translate back
4. Only **used** chunks shown; click ref → highlight in full raw text + audio time

## Bayat website RAG

- Index: `.venv/bin/python -m rag.index_bayat` → `rag/store/bayat_qwen3_8b` (Qwen3-8B)
- Coverage (disk vs store vs VPS): `.venv/bin/python -m rag.check_bayat_coverage --prod`
- Ask UI: Bayat site `/ask/` (`NEXT_PUBLIC_RAG_API_URL=https://185.204.168.239.sslip.io/rag`, `corpus=bayat`)
- API health shows both corpora: Manaee + Bayat
- **When you add new Bayat courses/lectures:** see **[`rag/BAYAT_INDEX.md`](BAYAT_INDEX.md)** (compare → embed only gaps → deploy VPS)

## Deploy later

Run the same API on the Arvan VPS; point `NEXT_PUBLIC_RAG_API_URL` at that host; keep the shared password.
See `rag/deploy/README.md` / `bash rag/deploy/deploy_to_vps.sh`.
