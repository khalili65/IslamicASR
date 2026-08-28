# Lecture website

Persian RTL lecture player with synced subtitles. Template for any lecturer/course
under `Audios/<Lecturer>/<Course>/`.

**Live site (Iran / Arvan):**
https://islamic-asr-web.s3-website.ir-thr-at1.arvanstorage.ir/

Example session:
https://islamic-asr-web.s3-website.ir-thr-at1.arvanstorage.ir/bayat/marefat_nafs/001/

---

## For collaborators: where code and audio live

We keep **code** and **audio** in two different places on purpose. Audio files are
large and change separately from the website UI.

| What | Where it lives | How it gets there |
| --- | --- | --- |
| **Website code** (pages, player, styles, session JSON/cues) | **GitHub** repo `IslamicASR` (this project) | Edit locally → `git commit` → `git push` |
| **Built website** (HTML/JS served to users) | **Arvan** bucket `islamic-asr-web` | Automatic: GitHub Actions builds after each push |
| **Lecture audio** (`.mp3` / `*_play.m4a`) | **Arvan** bucket `islamic-asr-media` | Upload with the dashboard or `scripts/upload_arvan.py` — **never commit audio to git** |

```
You edit website code          git push           GitHub Actions              Arvan: islamic-asr-web
─────────────────────  ───────────────────  ────────────────────────  ───────────────────────────
website/apps/web/…      →  GitHub            →  build + upload out/   →  live pages (s3-website URL)

You add / replace audio        upload             Arvan: islamic-asr-media
─────────────────────  ───────────────────  ───────────────────────────
Audios/…/NNN/*.m4a      →  put object         →  bayat/marefat_nafs/NNN/…
```

### How they are connected

1. Site data stores a relative path, e.g.  
   `/audio/bayat/marefat_nafs/001/001_play.m4a`
2. When the site is built, `NEXT_PUBLIC_MEDIA_BASE` is set to the audio bucket:  
   `https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir`
3. The player turns that into a full URL:  
   `https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir/bayat/marefat_nafs/001/001_play.m4a`

So the **page** comes from `islamic-asr-web`, and the **sound** comes from
`islamic-asr-media`, linked by the same folder/filename.

Use the **`s3-website…`** host for browsing the site (not the plain `s3.` host,
which lists the bucket at `/`).

### If you update the website code

1. Change files under `website/` (UI, player, etc.).
2. Commit and push to `main`:

```bash
git add …
git commit -m "Describe your change."
git push origin main
```

3. Wait for GitHub Actions (**Deploy site to Arvan**) to finish green:
   https://github.com/khalili65/IslamicASR/actions
4. Hard-refresh the live site.

You do **not** need to re-upload audio for a code-only change.

### If you only add or replace audio

1. Upload into Arvan `islamic-asr-media` with the exact key, e.g.  
   `bayat/marefat_nafs/002/<exact-filename>.mp3`  
   (or run `upload_arvan.py` for that session).
2. No `git push` is required **unless** you also changed transcripts / rebuilt
   `public/data` with `build_content.py`.

More detail: [DEPLOY.md](./DEPLOY.md).

---

## Quick start

```bash
# 1) Ensure Node is on PATH (already set up on this machine)
export PATH="$HOME/.local/node/bin:$PATH"

# 2) Rebuild content from Audios (optional if data already exists)
cd website
../.venv/bin/python tools/build_content.py --course ../Audios/Bayat/marefat_nafs

# 3) Optional but recommended — fix mp3s whose container duration is wrong
../.venv/bin/python tools/prepare_playback.py --course ../Audios/Bayat/marefat_nafs
../.venv/bin/python tools/build_content.py --course ../Audios/Bayat/marefat_nafs --skip-subtitles

# 4) Install & run the web app
cd apps/web
npm install --registry=https://registry.npmmirror.com --ignore-scripts
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

First transcribed session with subtitles:
[http://localhost:3000/bayat/marefat_nafs/001/](http://localhost:3000/bayat/marefat_nafs/001/)

Hard-refresh after content or UI changes: `Cmd+Shift+R`.

## What works now

- Home → course list → session player (Persian RTL, sage / maroon theme)
- Synced Persian subtitles (corrected text timed from ASR word clocks)
- Chapters from `##` headings in corrected markdown
- Download / share / my-list / subtitle toggle / full text view
- Search across transcribed sessions (matched phrase highlighted)
- Resume playback position (localStorage)
- Keyboard: Space play/pause, ←/→ ±15 s
- Audio served locally via `public/audio` → `Audios/` (production uses Arvan media)

## What we built / fixed (changelog)

### Content pipeline (`tools/`)

| Script | Role |
| --- | --- |
| `align_subtitles.py` | Align corrected markdown → ASR word times → `.vtt` / `.cues.json` / `.words.json` |
| `build_content.py` | Walk `Audios/`, write `apps/web/public/data/` JSON for the site |
| `prepare_playback.py` | Remux mp3 → `NNN_play.m4a` when the container duration is wrong |
| `transcript.py` / `align.py` / `cues.py` / `persian.py` | Parsers, alignment, cue grouping, normalisation |

### Sync fixes

1. **Bracketed asides** (`[صدای محیط]`, `[نفس عمیق]`, editorial clarifications) are
   stripped before alignment so they do not consume audio time. They remain in the
   full-text reading view. This was the cause of the bad stretch around ~40′ in session 001.
2. **Cue abutting** — each cue holds until the next starts (no lingering stale line).
3. **Player clock** — `requestAnimationFrame` polls `currentTime` while playing
   (`onTimeUpdate` alone is too sparse).
4. **Playback remux** — some source mp3s advertise a duration a few seconds shorter
   than the decoded length (e.g. 3216 s vs 3221 s). The browser then reports the short
   clock; seeking feels like lag that grows over the lecture. `prepare_playback.py`
   writes `NNN_play.m4a` (honest AAC duration); `build_content.py` prefers it when present.
5. Verified independently: re-ASR of clips at 1′ and 44′ with Fish matches existing
   ElevenLabs word times within ~0.1 s — the ASR timeline itself is not drifting.

### UI

- Redesigned home, course list, player, search, my-list, and full-text pages
- SVG icon set, deep-sage primary actions, maroon subtitle stage with cue fade-in
- Transcript panel can auto-follow the active line **without** scrolling the page
- Theme colours as RGB channel tokens so Tailwind opacity modifiers work
  (`src/lib/theme.ts` converts hex from `site.config.json`)

## Transcript conventions that affect sync

The aligner maps the corrected text onto the raw ASR word timestamps, so
anything in `*.corrected.md` that the teacher did **not** say must be marked,
otherwise it is handed a share of the audio and drags the nearby subtitles out
of sync.

Mark unspoken text as any of:

- `[…]` square brackets — stage directions and editorial clarifications
- `> …` blockquotes labelled as a model translation
- Markdown tables and bullet lists (correction logs / citations)
- Everything after a `پی‌نوشت` heading

```bash
.venv/bin/python website/tools/align_subtitles.py --course Audios/Bayat/marefat_nafs --report
```

## Playback audio

```bash
.venv/bin/python website/tools/prepare_playback.py --course Audios/Bayat/marefat_nafs
.venv/bin/python website/tools/build_content.py --course Audios/Bayat/marefat_nafs --skip-subtitles
```

Writes `NNN_play.m4a` next to each lecture (originals untouched). Applied for every
session whose mp3 container under-reports duration (e.g. 001, 004–008, 011, 015–020,
037, 062, 068, 071–075). Honest mp3s keep the original file.

## After you finish more sessions

```bash
.venv/bin/python website/tools/prepare_playback.py --course Audios/Bayat/marefat_nafs
.venv/bin/python website/tools/build_content.py --course Audios/Bayat/marefat_nafs
```

Then hard-refresh the browser. No code changes needed.

## Production build (static)

```bash
cd website/apps/web
# Production media host (Arvan audio bucket) — baked into the static export
export NEXT_PUBLIC_MEDIA_BASE=https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir
npm run build   # writes to out/
```

Do **not** run `npm run build` while `npm run dev` is live — they share `.next` and
the build will break the dev server until you restart it.

Remove any `public/audio` symlink before a production build/upload so large media
is never shipped with the site (audio lives on Object Storage).

## How production is deployed (Arvan + GitHub Actions)

We host **inside Iran on ArvanCloud** so the site stays reachable for local
listeners. Cloudflare Pages works as a secondary mirror but is often filtered or
slow from Iran.

| Piece | Bucket / service | Public base |
| --- | --- | --- |
| **Website** | Arvan Object Storage `islamic-asr-web` (Static Website enabled) | https://islamic-asr-web.s3-website.ir-thr-at1.arvanstorage.ir/ |
| **Audio** | Arvan Object Storage `islamic-asr-media` | https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir/ |

JSON under `apps/web/public/data/` still stores paths like
`/audio/bayat/marefat_nafs/001/001_play.m4a`. At build time,
`NEXT_PUBLIC_MEDIA_BASE` rewrites those to the Arvan media host via
`src/lib/media.ts`.

### Website updates (automatic)

1. Change code or site data, commit, `git push origin main`.
2. GitHub Actions workflow [`.github/workflows/deploy-arvan.yml`](../.github/workflows/deploy-arvan.yml):
   - builds `website/apps/web` on a GitHub runner (fast uplink),
   - uploads `out/` to `islamic-asr-web` with `website/scripts/deploy_arvan_web.py`
     (retries, skips unchanged files).
3. Required repo secrets: `ARVAN_ACCESS_KEY`, `ARVAN_SECRET_KEY`
   (GitHub → Settings → Secrets and variables → Actions).
4. You can also run the workflow manually: Actions → **Deploy site to Arvan** →
   **Run workflow**.

### Audio updates (manual / script)

Audio is **not** in git. Prefer `*_play.m4a` when present.

```bash
# credentials in gitignored .env.arvan (see .env.arvan.example)
.venv/bin/python website/scripts/upload_arvan.py --scripts-only Audios/Bayat/marefat_nafs
# or one session:
.venv/bin/python website/scripts/upload_arvan.py Audios/Bayat/marefat_nafs/001

# if a dashboard upload is private:
.venv/bin/python website/scripts/arvan_make_public.py bayat/marefat_nafs/
```

Object keys match player URLs, e.g.
`bayat/marefat_nafs/001/001_play.m4a`.

### One-time Arvan checklist (already done for this project)

1. Create buckets `islamic-asr-media` (audio) and `islamic-asr-web` (site).
2. Public access + CORS (GET/HEAD) on both.
3. Object Storage → **Static Website** → activate on `islamic-asr-web`
   (index `index.html`).
4. Add the two GitHub Actions secrets above.

Full notes (including the optional Cloudflare Pages path): **[DEPLOY.md](./DEPLOY.md)**.

## Layout

```
website/
  PLAN.md
  README.md          ← this file
  site.config.json
  content/           ← editable names / descriptions
  tools/             ← Python content pipeline
  apps/web/          ← Next.js app
```

## Mobile (later)

Capacitor wraps the same static export for Android/iOS. Not set up yet — web first.
