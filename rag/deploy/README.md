# Deploy Manaee RAG to Arvan VPS

Target: `ubuntu@185.204.168.239` (`bayat-admin`)

```bash
bash rag/deploy/deploy_to_vps.sh
```

## Endpoints

| What | URL |
| --- | --- |
| Health | http://185.204.168.239/rag/health |
| API base (portal) | `NEXT_PUBLIC_RAG_API_URL=http://185.204.168.239/rag` |
| Local bind on VPS | `127.0.0.1:8001` (8000 is LangNest) |

## Services

- `islam-asr-rag.service` — FastAPI + both stores (`manaee`, `manaee_qwen3_8b`)
- nginx snippet: `/etc/nginx/snippets/islam-asr-rag.conf` → `/rag/`
- Secrets: `/opt/islam-asr-rag.env` (+ mirrored `IslamASR/.env`)

## Portal rebuild

```bash
cd website-portal/apps/web
NEXT_PUBLIC_RAG_API_URL=http://185.204.168.239/rag \
NEXT_PUBLIC_MEDIA_BASE=https://islamic-asr-portal-media.s3.ir-thr-at1.arvanstorage.ir \
  npm run build
# then upload out/ → islamic-asr-portal-web
```
