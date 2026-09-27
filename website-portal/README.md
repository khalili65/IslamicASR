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

### Portal-wide search

Search covers **all** lecturers. Audio courses search timed **ASR cues** (raw pipeline), not book-style markdown.

```bash
.venv/bin/python website-portal/scripts/build_search_indexes.py
```

- http://localhost:3001/search/ — all lecturers  
- http://localhost:3001/search/?lecturer=qasemian&course=insanekamel — filtered  
 

### Simple admin UI (for non-technical editors)

See **`website-portal/admin/README.md`**. Password-protected panel: edit names, photos, hide sessions, **Publish**.

```bash
cd website-portal/admin && cp .env.example .env.local   # set ADMIN_PASSWORD
npm install && npm run dev   # http://localhost:3002
```

**Hosting:** the public portal stays on Arvan **static buckets**; the admin must run on a **small Arvan VPS** (or your PC for testing) — object storage cannot run login/save/publish.

### Raw ASR subtitles (new pipeline courses)

For courses that only have `*.txt` + `*.book.md` (no legacy `corrected.md`), set
in `content/<lecturer>/<course>/course.json`:

```json
"subtitles": "raw"
```

Then rebuild (see `website/README.md` → **Subtitle source: edited vs raw**):

```bash
.venv/bin/python website/tools/prepare_playback.py --course Audios/.../Term1
.venv/bin/python website/tools/build_content.py \
  --site-root website-portal \
  --course Audios/.../Term1
```

Player shows verbatim ASR in the subtitle stage and **متن جلسه**; **متن کامل**
serves `NNN.raw.txt`; **نسخه کتابی** / **خلاصه** still use ChatGPT outputs.

Example: `content/manaee/term1/course.json` (Term1 / صبوحی). Local dev needs
audio under `public/audio/<lecturer>/<course>/NNN/` (symlink or copy); prefer
`NNN_play.m4a` when present.

Full sync notes (pause-aware raw cues, mp3 remux, edited vs raw pitfalls):
`website/README.md` § Sync fixes items 4–6 and **Subtitle source**.
