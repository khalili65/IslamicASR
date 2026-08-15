# Lecture website

Persian RTL lecture player with synced subtitles. Template for any lecturer/course
under `Audios/<Lecturer>/<Course>/`.

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
- Audio served locally via `public/audio` → `Audios/`
- Sessions without a transcript (011+) play as **audio only** until ASR + correction
  are done and `build_content.py` is re-run

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

Writes `NNN_play.m4a` next to each lecture (originals untouched). Already applied for
sessions whose headers were short (e.g. 001, 004–008); others keep the original mp3.

## After you finish more sessions

```bash
.venv/bin/python website/tools/prepare_playback.py --course Audios/Bayat/marefat_nafs
.venv/bin/python website/tools/build_content.py --course Audios/Bayat/marefat_nafs
```

Then hard-refresh the browser. No code changes needed.

## Production build (static)

```bash
cd website/apps/web
npm run build   # writes to out/
# serve out/ anywhere (GCS, nginx, …)
```

Do **not** run `npm run build` while `npm run dev` is live — they share `.next` and
the build will break the dev server until you restart it.

For production, upload media and set `media.baseUrl` in `website/site.config.json`.

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
