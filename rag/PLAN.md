# Transparent multilingual RAG (DeepInfra)

## Locked decisions (2026-09-22)

| Item | Choice |
| --- | --- |
| Corpus v1 | `Audios/Manaee` **raw** `.txt` only |
| Embeddings | `BAAI/bge-m3` + `Qwen/Qwen3-Embedding-8B` (dual stores) |
| LLMs | User picks: `openai/gpt-oss-120b`, `zai-org/GLM-5.3`, `moonshotai/Kimi-K2.6` (cost shown in UI) |
| Access | Portal `/ask/` + API password (`RAG_ACCESS_PASSWORD`) for ~10 people |
| Hosting | Arvan VPS `bayat-admin` (`islam-asr-rag` on `:8001`, nginx `/rag/`) |

See `rag/README.md` for run commands.

---

## Goals

1. Any-language Q&A → FA retrieve → answer → back to user language
2. Show only chunks the LLM **used**
3. Click ref → full raw text highlight + audio time
4. DeepInfra for embed + LLM

## Flow

```
question → detect lang → translate to FA → embed (bge-m3)
→ top-k retrieve → LLM JSON {answer_fa, used_chunk_ids}
→ translate answer → UI refs + highlight modal
```

## Status

- [x] Plan + DeepInfra wiring
- [x] Manaee indexer + local vector store
- [x] FastAPI `/login` `/ask` `/models` `/source`
- [x] Portal `/ask` page (password + model costs + refs)
- [ ] Full Manaee index complete
- [x] Deploy API on Arvan VPS
