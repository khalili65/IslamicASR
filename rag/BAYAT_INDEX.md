# Bayat RAG — coverage, embedding & production push

This is the Bayat **website** corpus (`Audios/Bayat` → Ask page on `islamic-asr-web`), **not** the Manaee portal.

## Current production snapshot (checked 2026-09-26)

| Item | Value |
| --- | --- |
| VPS API | `https://185.204.168.239.sslip.io/rag` |
| Health | `GET /rag/health` → `stores.bayat.ok: true` |
| Store key | `bayat_qwen3_8b` (`rag/store/bayat_qwen3_8b/`) |
| Embed model | `Qwen/Qwen3-Embedding-8B` (DeepInfra) |
| Indexed | **33 830** chunks · **1 336** sessions · **44** courses |
| Website | **44** Bayat courses under `website/apps/web/public/data/bayat/` — **exact match** |
| Ask UI | Bayat site `/ask/` · `corpus=bayat` · default API URL above |

How that coverage was verified:

1. `GET https://185.204.168.239.sslip.io/rag/health` → chunk count for `bayat`
2. Local `rag/store/bayat_qwen3_8b/chunks.jsonl` → unique `(course, session_id)` set
3. `Audios/Bayat/*/<digits>/*.txt` discovery (same rules as the indexer)
4. Compare sets: **0 missing**, **0 orphan**
5. Live `/ask` queries returned chunks from both old (`leghaallah`) and new (`qalb_manzel`) courses

Re-run the same check anytime:

```bash
.venv/bin/python -m rag.check_bayat_coverage --prod
```

Exit code `0` = disk and local store match. Exit `2` = gaps (print lists what to embed).

---

## What gets indexed

Only **raw session `.txt`** files under:

```text
Audios/Bayat/<course_slug>/<NNN>/*.txt
```

Rules (see `rag/index_bayat.py`):

- Course dirs starting with `_` are skipped
- Session dirs must be numeric (`001`, `041`, …)
- `.book.md` / `.summary.md` are **not** embedded (player/search use those separately)
- Course slug in the store is **lowercased** (`Leghaallah` → `leghaallah`)

Website deploy (HTML/audio/search tokens) is a **separate** pipeline. RAG only cares about these `.txt` transcripts.

---

## When you add new courses or new lectures

### 1. Put transcripts on disk

```text
Audios/Bayat/<new_or_existing_course>/041/041_….txt
```

(Use the same folder layout as existing courses.)

### 2. See what is missing vs already embedded

```bash
.venv/bin/python -m rag.check_bayat_coverage
# optional: also compare chunk count on the VPS
.venv/bin/python -m rag.check_bayat_coverage --prod
```

Look for:

- **NEW courses (not in store)** — whole course missing
- **MISSING sessions** — new lectures of an existing course
- **ORPHAN** — store still has a session whose `.txt` was removed (rare)

### 3. Embed only what is new (recommended)

Merge into the existing store (does **not** re-bill embeddings for untouched courses):

```bash
# whole new course
.venv/bin/python -m rag.index_bayat --course my_new_course

# several courses
.venv/bin/python -m rag.index_bayat --course course_a --course course_b

# only new sessions of an existing course
.venv/bin/python -m rag.index_bayat --course qalb_manzel --session 041 --session 042
```

Needs `DEEPINFRA_API_KEY` in repo-root `.env`.

Full rebuild (all 1k+ sessions — slow / costly; use after big cleanups):

```bash
.venv/bin/python -m rag.index_bayat
# or force full even with --course:
.venv/bin/python -m rag.index_bayat --full
```

### 4. Confirm local coverage is clean

```bash
.venv/bin/python -m rag.check_bayat_coverage
```

You want: `OK — every on-disk session is in the local store.`

### 5. Push store + source `.txt` to the VPS

```bash
bash rag/deploy/deploy_to_vps.sh
```

That rsyncs:

- `rag/` code
- `rag/store/bayat_qwen3_8b/` (embeddings + `chunks.jsonl`)
- `Audios/Bayat/**/*.txt` (needed for `/source` highlight in Ask)
- restarts `islam-asr-rag`

### 6. Verify production

```bash
.venv/bin/python -m rag.check_bayat_coverage --prod
# or:
curl -s https://185.204.168.239.sslip.io/rag/health | python3 -m json.tool
```

`stores.bayat.chunks` should equal local `n_chunks`. Then ask a question on the live site `/ask/` that only the new lecture can answer.

---

## Website vs RAG checklist

| Step | Website (player / search) | RAG (Ask) |
| --- | --- | --- |
| Transcripts | `Audios/Bayat/...` | same `.txt` |
| Build site data | `website/tools/build_content.py` | — |
| Token search index | site build / search scripts | — |
| Embeddings | — | `python -m rag.index_bayat …` |
| Audio to Arvan media | `website/scripts/upload_arvan.py` | — |
| Static site to Arvan web | deploy `out/` → `islamic-asr-web` | — |
| Vectors to VPS | — | `bash rag/deploy/deploy_to_vps.sh` |

Adding a lecture to the **website** does **not** auto-update RAG. Always run coverage → embed → deploy VPS when transcripts change.

---

## Quick reference

```bash
# What am I missing?
.venv/bin/python -m rag.check_bayat_coverage --prod

# Embed gaps for one course
.venv/bin/python -m rag.index_bayat --course <slug>

# Ship to Arvan VPS
bash rag/deploy/deploy_to_vps.sh

# Smoke Ask (after login token)
# POST https://185.204.168.239.sslip.io/rag/ask
# body: {"question":"…","corpus":"bayat","model":"openai/gpt-oss-120b"}
```

Related files: `rag/index_bayat.py`, `rag/check_bayat_coverage.py`, `rag/deploy/deploy_to_vps.sh`, `rag/README.md`.
