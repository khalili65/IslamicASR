# Deploy — Cloudflare Pages + R2 (auto-update on git push)

Minimum-cost setup for this static lecture site:

| Piece | Service | Updates when… |
| --- | --- | --- |
| Website (HTML/JS/JSON) | **Cloudflare Pages** | You **push to GitHub** → auto rebuild |
| Audio (mp3 / `_play.m4a`) | **Cloudflare R2** | You run the **upload script** (media is not in git) |

Local listening still uses `public/audio` → `Audios/`. Production uses
`NEXT_PUBLIC_MEDIA_BASE` so the same committed JSON keeps working.

---

## One-time setup

### A. Push this repo to GitHub

Your remote is already `https://github.com/khalili65/IslamicASR`.

```bash
cd "/path/to/IslamicASR"
git status
# commit any pending work, then:
git push -u origin main
```

If the push asks you to log in, use a GitHub personal access token or `gh auth login`.

### B. Cloudflare account

1. Open [https://dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up) and create an account (free).
2. On your machine:

```bash
export PATH="$HOME/.local/node/bin:$PATH"
npx wrangler login
```

Complete the browser login.

### C. Create an R2 bucket (audio)

1. Cloudflare dashboard → **R2** → **Create bucket**
2. Name it e.g. `islamic-asr-media` (same as the default in the upload script)
3. Open the bucket → **Settings** → **Public access**
   - Enable **R2.dev subdomain** (easiest), or attach a custom domain later
4. Copy the public base URL, e.g.

   `https://pub-0123456789abcdef.r2.dev`

   You will paste this into Pages as `NEXT_PUBLIC_MEDIA_BASE` (no trailing slash).

5. Optional CORS (if the browser blocks audio): bucket **Settings** → CORS policy:

```json
[
  {
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["Content-Length", "Content-Range", "Accept-Ranges"],
    "MaxAgeSeconds": 86400
  }
]
```

### D. Upload audio once

From the **repo root**:

```bash
export PATH="$HOME/.local/node/bin:$PATH"
export R2_BUCKET=islamic-asr-media

# Remux any mp3s with wrong duration (recommended)
.venv/bin/python website/tools/prepare_playback.py --course Audios/Bayat/marefat_nafs

# Upload Bayat course audio (prefers *_play.m4a when present)
./website/scripts/upload_r2.sh Audios/Bayat/marefat_nafs
```

Objects land at keys like:

`bayat/marefat_nafs/001/001_play.m4a`

which match player URLs:

`{NEXT_PUBLIC_MEDIA_BASE}/bayat/marefat_nafs/001/001_play.m4a`

### E. Create the Pages project (website auto-deploy)

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. Authorize GitHub and select **`khalili65/IslamicASR`**
3. Build settings:

   | Field | Value |
   | --- | --- |
   | Production branch | `main` |
   | Root directory | `website/apps/web` |
   | Build command | `npm ci --ignore-scripts && npm run build` |
   | Build output directory | `out` |

4. **Environment variables** (Production + Preview):

   | Name | Value |
   | --- | --- |
   | `NEXT_PUBLIC_MEDIA_BASE` | `https://pub-….r2.dev` (from step C, no trailing `/`) |
   | `NODE_VERSION` | `20` |

5. Save and deploy. First build takes a few minutes.

6. When it finishes, open the `*.pages.dev` URL. Play a session and confirm audio starts.

Custom domain (optional): Pages → **Custom domains** → add e.g. `doroos.example.com`.

---

## How updates work after setup

```
┌─────────────────┐     git push      ┌──────────────────┐
│  You edit code  │ ───────────────►  │ Cloudflare Pages │ → new site live
│  or transcripts │                   │ (auto build)     │
└─────────────────┘                   └──────────────────┘

┌─────────────────┐   upload_r2.sh    ┌──────────────────┐
│  New .mp3 /     │ ───────────────►  │ Cloudflare R2    │ → audio live
│  _play.m4a      │                   │                  │
└─────────────────┘                   └──────────────────┘
```

### Adding a new **session** (same course)

```bash
# 1) Put files under Audios/Bayat/marefat_nafs/011/  (mp3 + txt + corrected.md …)
# 2) Fix playback file if needed
.venv/bin/python website/tools/prepare_playback.py --course Audios/Bayat/marefat_nafs

# 3) Rebuild site JSON + cues
.venv/bin/python website/tools/build_content.py --course Audios/Bayat/marefat_nafs

# 4) Upload only the new session audio
./website/scripts/upload_r2.sh Audios/Bayat/marefat_nafs/011

# 5) Commit generated data + transcripts (not the mp3/m4a — gitignored)
git add Audios/Bayat/marefat_nafs/011/*.txt Audios/Bayat/marefat_nafs/011/*.md \
        website/apps/web/public/data/
git commit -m "Add session 011 transcripts and site data."
git push origin main
```

Pages rebuilds from the push. Audio is already on R2 from step 4.

### Adding a new **course** or lecturer

1. Create `Audios/<Lecturer>/<course>/…` as usual  
2. Edit `website/content/…` metadata (title, cover, …)  
3. `prepare_playback.py` + `build_content.py`  
4. `./website/scripts/upload_r2.sh Audios/<Lecturer>/<course>`  
5. Commit + `git push`  

### Changing only UI / player code

```bash
git add website/apps/web
git commit -m "Fix player UI."
git push origin main
```

No R2 upload needed.

---

## Local vs production checklist

| | Local | Production |
| --- | --- | --- |
| Site | `npm run dev` | Pages URL |
| Audio | symlink `public/audio` → `Audios/` | R2 via `NEXT_PUBLIC_MEDIA_BASE` |
| Data JSON | `public/data/` (same files) | built into `out/` on Pages |

Never commit `.env` or API keys. `NEXT_PUBLIC_MEDIA_BASE` is a public URL (safe in Pages env).

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Site OK, no sound | Check `NEXT_PUBLIC_MEDIA_BASE`, and that the object key exists in R2 (`bayat/marefat_nafs/001/…`) |
| CORS error in browser console | Add the CORS policy in §C |
| Pages build fails on `npm ci` | Confirm Root directory is `website/apps/web` and `NODE_VERSION=20` |
| Old site after push | Wait for the Pages deployment to finish; hard-refresh (`Cmd+Shift+R`) |
| Wrong duration / seek drift | Run `prepare_playback.py` and re-upload `*_play.m4a` |

---

## Cost reminder

At tens or hundreds of listeners, Pages + R2 is typically **dollars per month or less** (R2 has no egress fee). See the chat / PLAN notes for the 10 vs 100 concurrent estimates.
