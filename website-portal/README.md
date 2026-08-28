# Multi-lecturer portal site

Separate from the Bayat single-lecturer site under `website/`.  
This tree is **portal mode**: home lists lecturers; first lecturer is **قاسمیان / انسان کامل**.

| | Bayat site | This portal |
|---|---|---|
| Folder | `website/` | `website-portal/` |
| Mode | `single-lecturer` | `portal` |
| First content | `bayat/marefat_nafs` | `qasemian/insanekamel` |
| Dev port | 3000 | **3001** |
| Tools | `website/tools/` | symlink → same tools (`--site-root`) |

---

## Quick start

```bash
# 1) Remux playback files (honest duration; shared under Audios/)
.venv/bin/python website/tools/prepare_playback.py --course Audios/Qasemian/InsaneKamel

# 2) Build JSON / cues / search into this site
.venv/bin/python website/tools/build_content.py \
  --site-root website-portal \
  --course Audios/Qasemian/InsaneKamel

# 3) Local audio for the Next dev server
ln -sfn "$(pwd)/Audios" website-portal/apps/web/public/audio

# 4) Run
export PATH="$HOME/.local/node/bin:$PATH"
cd website-portal/apps/web
npm install --registry=https://registry.npmmirror.com --ignore-scripts
npm run dev
```

Open:

- http://localhost:3001/ — lecturer list  
- http://localhost:3001/qasemian/insanekamel/ — course  
- http://localhost:3001/qasemian/insanekamel/001/ — player  

---

## Add another lecturer later

1. Put files under `Audios/<Lecturer>/<Course>/NNN/` (same pipeline as Bayat/Qasemian).  
2. Edit / seed `website-portal/content/<lecturer>/lecturer.json` and `…/<course>/course.json`.  
3. Rebuild:

```bash
.venv/bin/python website/tools/build_content.py \
  --site-root website-portal \
  --course Audios/<Lecturer>/<Course>
```

(Or omit `--course` to rebuild every course under `Audios/` into this portal’s `index.json`.)

---

## Production (separate Arvan site)

Use **different buckets** from Bayat so the two sites stay independent, e.g.:

| Role | Suggested bucket |
|---|---|
| Static site | `islamic-asr-portal-web` |
| Audio | `islamic-asr-portal-media` |

1. Create buckets + static website hosting (same steps as `website/DEPLOY.md`).  
2. Copy `.env.arvan` → `.env.arvan.portal` with the new bucket names / `NEXT_PUBLIC_MEDIA_BASE`.  
3. Upload audio:

```bash
# after editing upload script env or exporting ARVAN_BUCKET=…
.venv/bin/python website/scripts/upload_arvan.py Audios/Qasemian/InsaneKamel
```

Keys: `qasemian/insanekamel/001/001_play.m4a` (folder names lowercased).

4. Add a GitHub Actions workflow that builds `website-portal/apps/web` and uploads to the portal web bucket (mirror `.github/workflows/deploy-arvan.yml`).

Until that is wired, local `npm run dev` is enough to use the player.

---

## Editable metadata

- `website-portal/site.config.json` — brand, theme, `mode: portal`  
- `website-portal/content/qasemian/lecturer.json`  
- `website-portal/content/qasemian/insanekamel/course.json`  
