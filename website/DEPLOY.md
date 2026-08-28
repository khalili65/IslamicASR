# Deploy — Arvan Object Storage + GitHub Actions

Production hosting for listeners **inside Iran**. The static lecture site and
the audio live on **ArvanCloud Object Storage**. GitHub Actions builds and
uploads the site so you do not push hundreds of files over a slow home uplink.

| Piece | Service | Updates when… |
| --- | --- | --- |
| Website (HTML/JS/JSON) | Arvan bucket **`islamic-asr-web`** (Static Website) | **`git push`** → Actions build + sync |
| Audio (mp3 / `_play.m4a`) | Arvan bucket **`islamic-asr-media`** | Upload script or Arvan dashboard (not in git) |

**Live URLs**

- Site: https://islamic-asr-web.s3-website.ir-thr-at1.arvanstorage.ir/
- Example session: https://islamic-asr-web.s3-website.ir-thr-at1.arvanstorage.ir/bayat/marefat_nafs/001/
- Audio base: `https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir`

Use the **`s3-website…`** host for the site (directory indexes). The plain
`s3.…arvanstorage.ir` host lists the bucket at `/` and is not the player entry.

Local listening still uses `public/audio` → `Audios/`. Production sets
`NEXT_PUBLIC_MEDIA_BASE` at build time so the same JSON paths work.

---

## Architecture

```
┌─────────────────┐   git push    ┌──────────────────┐   upload out/   ┌─────────────────────┐
│ Code + site     │ ────────────► │ GitHub Actions   │ ───────────────► │ islamic-asr-web     │
│ data (no audio) │               │ build Next export│                  │ (static website)    │
└─────────────────┘               └──────────────────┘                  └─────────────────────┘

┌─────────────────┐  upload_arvan ┌─────────────────────┐
│ Local Audios/   │ ────────────► │ islamic-asr-media   │ ← player fetches audio here
│ *_play.m4a/mp3  │   or dashboard│ (public objects)    │
└─────────────────┘               └─────────────────────┘
```

Workflow file: `.github/workflows/deploy-arvan.yml`  
Uploader: `website/scripts/deploy_arvan_web.py`

---

## One-time setup

### A. Arvan buckets

1. [Arvan Object Storage](https://panel.arvancloud.ir/) → create:
   - `islamic-asr-media` — lecture audio  
   - `islamic-asr-web` — static site  
2. Region: Iran Central 1 (`ir-thr-at1`).
3. Enable **public access** on both; set CORS for GET/HEAD if the browser blocks media.
4. **Static Website** → select `islamic-asr-web` → Activate (index: `index.html`).
5. Create an Access Key + Secret under Access Management.

Local credentials (gitignored):

```bash
cp .env.arvan.example .env.arvan
# fill ARVAN_ACCESS_KEY, ARVAN_SECRET_KEY, endpoints/buckets
```

### B. GitHub Actions secrets

Repo → **Settings → Secrets and variables → Actions**:

| Secret | Value |
| --- | --- |
| `ARVAN_ACCESS_KEY` | Arvan access key |
| `ARVAN_SECRET_KEY` | Arvan secret key |

### C. First audio upload

```bash
.venv/bin/python website/tools/prepare_playback.py --course Audios/Bayat/marefat_nafs
.venv/bin/python website/scripts/upload_arvan.py --scripts-only Audios/Bayat/marefat_nafs
# or upload via Arvan dashboard into bayat/marefat_nafs/NNN/ with exact filenames
.venv/bin/python website/scripts/arvan_make_public.py   # if needed
```

Keys look like: `bayat/marefat_nafs/001/001_play.m4a`.

### D. First site deploy

Push to `main` (or Actions → **Deploy site to Arvan** → **Run workflow**).
The job builds with:

`NEXT_PUBLIC_MEDIA_BASE=https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir`

and syncs `website/apps/web/out/` to `islamic-asr-web`.

---

## Day-to-day updates

### Site / transcripts / UI

```bash
# rebuild content JSON if sessions changed
.venv/bin/python website/tools/build_content.py --course Audios/Bayat/marefat_nafs

git add website/apps/web/public/data/ Audios/.../corrected.* …
git commit -m "Update session content."
git push origin main
```

Watch: https://github.com/khalili65/IslamicASR/actions

### New audio only

```bash
.venv/bin/python website/scripts/upload_arvan.py Audios/Bayat/marefat_nafs/011
```

No site rebuild needed if `public/data` already points at that file name.

---

## Optional: Cloudflare Pages (outside Iran / backup)

A Pages project `islamic-asr` may still exist
(`https://islamic-asr.pages.dev`) with the same
`NEXT_PUBLIC_MEDIA_BASE` pointing at **Arvan media**. Prefer Arvan for Iranian
users.

If you use Pages again:

| Field | Value |
| --- | --- |
| Root directory | `website/apps/web` |
| Build command | `npm ci --ignore-scripts && npm run build` |
| Output | `out` |
| `NEXT_PUBLIC_MEDIA_BASE` | `https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir` |
| `NODE_VERSION` | `20` |

Do **not** deploy `public/audio` or any `*.mp3`/`*.m4a` to Pages (25 MiB limit
and huge uploads). R2 upload via `upload_r2.sh` remains available but is slow
from Iran; Arvan media is the primary audio store.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Actions fails on upload | Check `ARVAN_*` secrets; re-run workflow |
| Site root shows XML bucket listing | Use the **`s3-website`** URL, not plain `s3.` |
| Audio 403 | Object/bucket not public → `arvan_make_public.py` |
| Audio missing | Upload to `islamic-asr-media` with the key in session JSON |
| Build includes huge audio | Ensure `public/audio` symlink is absent in CI (gitignored) |
