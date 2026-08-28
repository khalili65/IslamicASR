# Deploy — portal site (Arvan)

This is the **multi-lecturer portal** under `website-portal/`.  
Keep it on **separate buckets** from the Bayat site in `website/` so the two deploys never overwrite each other.

| Piece | Suggested bucket | Updates when… |
| --- | --- | --- |
| Website (HTML/JS/JSON) | `islamic-asr-portal-web` (Static Website) | git push → Actions (or local `deploy_arvan_web.py`) |
| Audio (`_play.m4a` / mp3) | `islamic-asr-portal-media` | `upload_arvan.py` / Arvan dashboard (not in git) |

Bayat still uses `islamic-asr-web` + `islamic-asr-media`. Do not point this portal at those unless you intentionally want one shared media bucket.

---

## One-time setup

### A. Arvan buckets

1. Create `islamic-asr-portal-media` and `islamic-asr-portal-web` (Iran Central 1).
2. Public read + CORS GET/HEAD on media (and web if needed).
3. Enable **Static Website** on `islamic-asr-portal-web` (index: `index.html`).
4. Access key + secret (can reuse the same keys as Bayat if policy allows both buckets).

Local env (gitignored), e.g. copy from Bayat and rename buckets:

```bash
cp website/.env.arvan.example website-portal/.env.arvan
# set ARVAN_WEB_BUCKET=islamic-asr-portal-web
# set ARVAN_MEDIA_BUCKET=islamic-asr-portal-media
# set NEXT_PUBLIC_MEDIA_BASE=https://islamic-asr-portal-media.s3.ir-thr-at1.arvanstorage.ir
```

### B. Build content + playback

```bash
.venv/bin/python website/tools/prepare_playback.py --course Audios/Qasemian/InsaneKamel
.venv/bin/python website/tools/build_content.py \
  --site-root website-portal \
  --course Audios/Qasemian/InsaneKamel
```

### C. Upload audio

```bash
# Point the uploader at the portal media bucket (env or flags — see website/scripts/upload_arvan.py)
.venv/bin/python website/scripts/upload_arvan.py Audios/Qasemian/InsaneKamel
```

Object keys: `qasemian/insanekamel/001/001_play.m4a` (folder names lowercased).

### D. Build & upload the static site

```bash
export PATH="$HOME/.local/node/bin:$PATH"
cd website-portal/apps/web
NEXT_PUBLIC_MEDIA_BASE=https://islamic-asr-portal-media.s3.ir-thr-at1.arvanstorage.ir \
  npm run build
# then sync apps/web/out/ → islamic-asr-portal-web
# (reuse website/scripts/deploy_arvan_web.py with portal paths/buckets, or mirror a portal workflow)
```

Optional: add `.github/workflows/deploy-arvan-portal.yml` mirroring Bayat’s `deploy-arvan.yml` but with `website-portal/` and the portal bucket names / secrets.

---

## Local preview

```bash
ln -sfn "$(pwd)/Audios" website-portal/apps/web/public/audio
cd website-portal/apps/web && npm run dev   # port 3001
```

See `README.md` for URLs and adding more lecturers.
