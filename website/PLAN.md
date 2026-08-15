# Lecture Platform — Plan

A reusable ("one size fits all") web + mobile application for publishing lecture audio
with time-synced Persian subtitles, modelled closely on [monibapp.com](https://monibapp.com/fa).

Everything in this `website/` folder is self-contained and shareable.

**Status:** Phase 0–2 largely done for Bayat / معرفت نفس (web player + content
pipeline live locally). Phase 3 (Capacitor) and Phase 4 (second lecturer) not started.
See **§12 Progress log** for what shipped and what we learned about sync.

---

## 1. Goal

Turn the existing `Audios/<Lecturer>/<Course>/<NNN>/` output of the ASR pipeline into a
polished, published product:

- A **web app** (Persian, RTL) that looks and feels like monibapp.
- A **player** that shows the transcript under the audio, highlighted in sync as it plays.
- **Android + iOS apps** from the same codebase.
- A **template**: point it at a different lecturer's folder, change a config file, and you have a new site. No code changes.

Non-goals for v1: user accounts, comments, payments, live streaming, video.

---

## 2. What the reference site actually does

I inspected `monibapp.com/fa` and the player page `/fa/player/19159`. Findings that
directly shape our design:

**Stack.** Next.js (App Router, RTL, `dir="rtl"`, `lang="fa"`), server-rendered, installable
PWA (`manifest.webmanifest`). Media is served from a separate domain
(`stream.monibapp.com`), downloads from a third (`bundles.monibapp.ir`).

**Subtitles are real SRT files, and yes, they are synced.** The page embeds a parsed
array alongside the SRT URL:

```json
"srt": { "fileName": "10_edited.srt", "serverSrc": "https://bundles.monibapp.ir/srt/1/13061/srt/10_edited.srt" },
"srtEnArr": { "subtitlesData": [{ "start": 0, "end": 19.309, "text": "…" }] }
```

Cue granularity in the real file is **one sentence per cue, ~15–20 seconds**, roughly 265
cues for an 82-minute lecture. They ship **Persian and English** subtitle tracks.

**Chapters.** A `tags` array of `{ title, start_time, end_time }` in seconds drives the
topic index (22 chapters for that 82-minute session).

**Per-lecture payload** (this is a good schema to copy):

```json
{
  "lectureId": 19159, "previousId": 19158, "nextId": null, "rowNumber": 10,
  "seriesId": 13061, "contextName": "نجم",
  "title": "نجم، جلسه دهم", "description": "تفسیر شده در ۱۴۰۵/۰۵/۲۱",
  "sound": { "url": "…/10.mp3", "size": 40053857, "display": "38.2 MB", "duration": "01:22:21" },
  "video": { "url": "…/10.mp4", "…": "…" },
  "srt": { "…": "…" }, "srt_en": { "…": "…" },
  "tags": [{ "title": "…", "start_time": 190, "end_time": 316 }],
  "download": { "sound": "…", "video": "…" }
}
```

**Player UI** (from the screenshot): dark card showing the current subtitle line, audio
transport bar, a صوتی/تصویری (audio/video) toggle, then action buttons —
دانلود (download), اشتراک (share), فهرست من (add to my list), زیرنویس (CC toggle),
متن (full text view).

**Home page sections:** hero slider, category tiles with lecture counts
(قرآن کریم ۲۱۲۳ جلسه, نهج البلاغه ۵۸۲ جلسه, …), تقویم برگزاری جلسات, پخش زنده,
نکته و حکمت‌ها, فهرست من, جستجو, and آخرین سخنرانی‌ها.

### 2.1 Design tokens (sampled from the screenshot + their CSS)

| Token | Value | Used for |
| --- | --- | --- |
| `--bg` | `#F7F8FC` | Page background |
| `--brand` | `#BBCAC5` | Header band, buttons, active toggle (sage) |
| `--brand-ink` | `#B4BFBB` | Button pressed / secondary sage |
| `--surface` | `#F2F3F5` | Player bar, cards |
| `--subtitle-bg` | `#24030A` | Dark maroon subtitle stage |
| `--subtitle-fg` | `#FFFFFF` | Subtitle text |
| `--muted` | `#EEEEEE` | Toggle group background |
| `--track` | `#C2C2C2` | Progress track |
| `--track-fill` | `#595959` | Progress fill |
| `--accent` | `#FE4A23` | Loading bar (nprogress) |

Radii are large and soft (~16–20px on cards, fully rounded pill buttons).

### 2.2 Fonts

Their CSS exposes three families:

| CSS var | Family | Weights | Purpose |
| --- | --- | --- | --- |
| `--global-font` | **IRANYekanX** (variable) | 100–1000 | Primary UI |
| `--global-font` | **IRANSansWeb** | 200/300/400/500/700/900 | Primary UI (alt) |
| `--arabic-font` | **Traditional Arabic** | 400 | Quran / Arabic quotations |

**Agreed: use these same fonts.** Self-host IRANYekanX + IRANSansWeb (both distributed
free by Fontiran) and Traditional Arabic, exposing the same two CSS variables
`--global-font` and `--arabic-font`. **Vazirmatn** and **Amiri** (both SIL OFL) are
bundled as a config-switchable pair, purely as insurance if a licence ever needs
changing — not as the default.

No name, logo, wordmark or other branding is copied. Only the typography and colour
palette are reused; all identity is left blank for the lecturer to fill in.

---

## 3. Content model

### 3.1 Source of truth stays where it is

Your existing layout already encodes lecturer → course → session, so we do **not**
restructure it. The build script reads it as-is:

```
Audios/
  Bayat/                      ← lecturer slug
    marefat_nafs/             ← course slug
      catalog.json            ← already exists (order, sizes, original names)
      001/
        001_….mp3             ← original audio
        001_play.m4a          ← optional browser-safe remux (honest duration)
        001_….txt             ← raw ASR + word-level timestamps
        001_….cleaned.txt     ← de-hallucinated paragraphs
        001_….corrected.md    ← final readable text (Arabic + translations)
        001_….summary.md      ← summary + outline
```

### 3.2 Human-authored metadata (small, versioned, editable)

Display names, ordering and blurbs shouldn't be guessed from filenames, so each level
gets a tiny JSON you edit by hand. The build script creates these with sensible
defaults on first run.

```
website/content/
  bayat/
    lecturer.json             { slug, name: "حجت‌الاسلام بیات", title, bio, avatar, links }
    marefat_nafs/
      course.json             { slug, title: "دروس معرفت نفس", description, cover,
                                order: "catalog" | "numeric", hidden: [], aliases: {} }
```

### 3.3 Generated output (gitignored, rebuilt on demand)

```
website/apps/web/public/data/
  index.json                          ← all lecturers + courses, counts
  bayat/marefat_nafs/course.json      ← session list with durations
  bayat/marefat_nafs/001.json         ← full lecture payload (schema from §2)
  bayat/marefat_nafs/001.cues.json    ← rich cues for the transcript UI
  bayat/marefat_nafs/001.vtt          ← WebVTT for the native <track> element
  bayat/marefat_nafs/001.words.json   ← optional word-level, for karaoke highlight
  search-index.json                   ← client-side full-text index
```

---

## 4. Subtitle synchronisation — the core technical question

**Yes, we can sync, and we can do it better than the reference site.** Your raw ASR
output already contains **word-level** timestamps. Checking session 001:

```
--- Segments ---
[    0.24s -     0.72s] دوستانی
[    0.74s -     0.86s] که
…
[ 3220.78s -  3220.79s] علیکم
```

That is 6,238 timed words across 53 minutes. monibapp only has sentence-level cues; we
can highlight the **exact word** being spoken.

### 4.1 The problem

The timed words come from the *raw* ASR. The text we actually want to display is
`.corrected.md` — cleaned, punctuated, with Arabic quotations restored and Farsi
translations added by the model. The word sequences differ, so we must map one onto the
other.

### 4.2 The algorithm (`tools/align_subtitles.py`)

1. **Parse** word timestamps from the `--- Segments ---` block of `NNN_….txt`.
2. **Parse** `.corrected.md` into typed blocks: heading, paragraph, `ayah-ar` Arabic
   quote, model-added translation, note. Strip the `<style>` block and the front matter.
3. **Normalise** both token streams for matching only: unify `ي→ی` and `ك→ک`, strip
   tashkeel and ZWNJ, fold Arabic-Indic digits, drop punctuation.
4. **Align** with `difflib.SequenceMatcher` over the normalised tokens:
   - `equal` / `replace` → corrected token inherits the raw word's start/end directly.
   - `insert` (added translations, restored words) → linearly interpolate between the
     nearest timed neighbours and flag `synthetic: true`.
   - `delete` (fillers removed during cleanup) → skipped, its time absorbed by neighbours.
5. **Group into cues**: break on sentence punctuation (`.` `؟` `!`, falling back to `،`),
   target 12–20 s and ≤ ~140 characters, and never split an Arabic quotation across cues.
   Cues **abut** (each cue's end = next cue's start) so a finished line never lingers.
6. **Emit** `.vtt`, `.cues.json` (with `kind: speech | quote` so the UI can style Arabic
   in the Arabic font), and `.words.json`.
7. **Report** alignment quality per session using **anchor gaps** (max / p95 seconds
   between exact matches, plus drift fraction), not only verbatim word-match %. Verbatim
   match is a poor signal when the editor rewrites colloquial speech into formal Persian.

### 4.2.1 Unspoken text must not consume audio time

Anything in `.corrected.md` that was never spoken — stage directions, editorial
clarifications in `[…]`, model translations, tables, lists, and everything after
`پی‌نوشت` — is stripped or classified as non-spoken **before** alignment. If left in,
the interpolator stretches those tokens across real audio and nearby cues drift
(session 001 around ~40′ was a concrete case).

Corrected vs ASR divergence causes **local** mismatches only: every exact word match
resets to the true ASR clock. It does **not** produce growing lag across a lecture.

### 4.2.2 Browser audio duration vs ASR clock

Some source mp3s advertise a **container** duration a few seconds shorter than the
decoded sample length (e.g. 3216 s vs 3221 s). `HTMLMediaElement.duration` then reports
the short value; seeking (and some players' clocks) drift against the subtitle timeline
in a way that **feels worse the further into the lecture you go**.

Mitigation: `tools/prepare_playback.py` remuxes to `NNN_play.m4a` (AAC, honest duration).
`build_content.py` / `SessionFiles` prefer that file when present. Originals stay untouched.

Independent check: re-ASR of windows at 1′ and 44′ with Fish matched existing ElevenLabs
word times within ~0.1 s — the ASR timeline itself is not drifting against the audio.

### 4.3 Fallbacks

- Corrected text missing → align against `.cleaned.txt` (much closer to raw, near-perfect match).
- Both missing → emit cues straight from the raw ASR words.
- `--- Segments ---` missing → fall back to forced alignment (WhisperX or `aeneas`) as an opt-in step.

### 4.4 Chapters

The `.summary.md` already contains an outline (فهرست مطالب). Two-step approach:
first try to locate each outline heading in the aligned cue stream by keyword match; where
that is ambiguous, `tools/gen_chapters.py` sends the timestamped cue list to an LLM (reusing
the existing `.env` keys) and asks for `{title, start_time, end_time}` — the same shape as
monibapp's `tags`. Results are cached into `course.json` so they are reviewable and
editable by hand, and never regenerated unless asked.

---

## 5. Tech stack

**Decision: TypeScript + React everywhere, Next.js for web, Capacitor for the stores.**

| Layer | Choice | Why |
| --- | --- | --- |
| Web | **Next.js 15** (App Router, `output: 'export'`) | Same as the reference site; static export means it can be hosted anywhere cheaply, and it stays fast on slow connections |
| Styling | **Tailwind CSS** + CSS variables for the tokens in §2.1 | Theming per lecturer is then a single variables file |
| State | Zustand (player) + TanStack Query (data) | Small, no boilerplate |
| Audio | Native `<audio>` + **Media Session API** | Gives lock-screen controls and background playback on both Android and iOS |
| Search | FlexSearch over a prebuilt index | Works fully client-side, no server |
| Offline | PWA with Workbox | Matches monibapp; lets people cache a lecture for the commute |
| iOS / Android | **Capacitor** wrapping the same build | One codebase, real store listings, native download + background audio plugins |
| Build tools | **Python 3** scripts in `tools/` | Reuses the venv, `catalog.json` and conventions you already have |

**Why Capacitor rather than Expo / React Native?** Expo would give more genuinely native
audio handling, but it means a second UI implementation and a weaker web result — and the
web is the primary deliverable here. Capacitor reaches both stores from the exact same
build we already need to produce: one codebase, one UI, one set of bugs. It is the
simpler option for shipping Android and iOS together, which is what was asked for.
Shared logic still lives in `packages/core`, so if native ever becomes the priority an
Expo app can be added beside it without a rewrite.

> Note: Node 20+ is installed under `~/.local/node` on the development machine
> (`export PATH="$HOME/.local/node/bin:$PATH"`).

---

## 6. Repository layout

```
website/
  PLAN.md                    ← this file
  README.md                  ← setup + changelog + conventions
  site.config.json           ← brand, theme, fonts, mode, media base URL
  content/                   ← human-authored metadata (§3.2)
  tools/
    build_content.py         ← walks Audios/, writes public/data/
    align_subtitles.py       ← §4 alignment → .vtt / .cues.json / .words.json
    prepare_playback.py      ← mp3 → NNN_play.m4a when container duration is wrong
    transcript.py / align.py / cues.py / persian.py
    requirements.txt
  apps/
    web/                     ← Next.js app (live)
    mobile/                  ← Capacitor shell (Phase 3, not started)
```

> Note: packages/core and packages/ui from the original sketch were folded into
> `apps/web/src` for speed; extract later if a second app needs them.

### `site.config.json` — what makes it a template

```json
{
  "brand": { "name": "", "logo": "", "locale": "fa", "dir": "rtl" },
  "mode": "single-lecturer",
  "defaultLecturer": "bayat",
  "theme": { "brand": "#BBCAC5", "subtitleBg": "#24030A", "bg": "#F7F8FC" },
  "fonts": { "ui": "iranyekanx", "arabic": "tarabic" },
  "media": { "baseUrl": "", "localFallback": "../../Audios" },
  "features": { "video": false, "english": false, "myList": true, "search": true }
}
```

`mode: "single-lecturer"` hides the lecturer level and makes courses the top level;
`"portal"` gives the full multi-lecturer home. Same code, different config.

**Agreed: launch in `single-lecturer` mode with Bayat, but build for `portal` from day
one.** Concretely, this means the routes, the data files and the URL structure always
carry the lecturer segment even while it is hidden from the UI. Switching to a
multi-lecturer portal later is then a config change plus a new home page — never a
migration of content or a change to any existing link.

---

## 7. Screens

| Route | Contents |
| --- | --- |
| `/` | Hero, course tiles with session counts, latest sessions list, search entry |
| `/[lecturer]` | Lecturer profile, their courses (portal mode only) |
| `/[lecturer]/[course]` | Course header, numbered session list with durations and progress ticks |
| `/[lecturer]/[course]/[session]` | **Player** — the main screen |
| `/[lecturer]/[course]/[session]/text` | Full reading view of `corrected.md`, click a paragraph to seek |
| `/search` | Cross-transcript search, results deep-link to a timestamp |
| `/my-list` | Bookmarks and "continue listening" (localStorage) |

### The player screen, in order down the page

1. Dark maroon subtitle stage (`#24030A`) showing the current cue, previous/next lines
   dimmed above and below, Arabic rendered in the Arabic font.
2. Transport bar: play/pause, elapsed / total, seek bar with chapter tick marks, volume,
   overflow menu (speed 0.75×–2×, sleep timer, jump ±15 s).
3. صوتی / تصویری toggle — rendered only when a video file exists.
4. Action row: دانلود · اشتراک · فهرست من · زیرنویس · متن.
5. Collapsible chapter list — tap a title to seek.
6. Scrollable full transcript that auto-scrolls with playback; tap any line to seek;
   toggle for "hide model-added translations".
7. Previous / next session navigation.

Player state (position, speed, subtitle on/off) persists in localStorage so a lecture
resumes where it was left.

---

## 8. Media hosting

75 sessions × ~35 MB is roughly 2.6 GB for this one course, which cannot live in git.

**Agreed: local first, Google Cloud later.** Two deployment targets, one codebase.

**Local (development and first review).** `media.baseUrl` is empty, so the dev server
streams audio straight from `../../Audios`. Nothing is uploaded, nothing is configured,
`npm run dev` just works. The static export can also be served locally over plain HTTP
to preview exactly what will be deployed.

**Google Cloud (production).** The static export goes to a **Cloud Storage** bucket
behind **Cloud CDN** with an HTTPS load balancer; audio goes to a second bucket with the
same treatment. Cloud Storage supports HTTP range requests natively, which is what makes
seeking work without downloading the whole file. `tools/upload_media.py` syncs the mp3s
(`gsutil rsync`) and rewrites `media.baseUrl` to the bucket's CDN host.

- `Audios/` stays the local master. `.gitignore` keeps audio out of the repo.
- Firebase Hosting is a simpler alternative to the load-balancer setup for the site
  itself, and can sit in front of the same GCS media bucket if preferred.
- Generate a 32 kbps mono variant with ffmpeg alongside the original so mobile users on
  slow connections have a cheaper stream.

---

## 9. Phased roadmap

**Phase 0 — Foundations** ✅
Node 20+, Next.js + Tailwind, `site.config.json`, RTL, theme tokens (RGB channels for
opacity modifiers), Vazirmatn + Amiri fonts.

**Phase 1 — Content pipeline** ✅
`build_content.py` + `align_subtitles.py` (+ helpers). Cues for the 10 transcribed
Bayat sessions, alignment report, bracket stripping, playback remux.

**Phase 2 — Web app** ✅ (local)
Home, course, player, text view, search, my-list. Synced transcript (panel auto-follow
optional; page itself does not scroll). Static export via `npm run build`.
Graphical pass: icons, subtitle stage, transport, cards. PWA / offline not yet.

**Phase 3 — Mobile** (not started)
Capacitor shell, native background audio, store assets.

**Phase 4 — Template hardening** (not started)
Second lecturer (`Audios/Shajareh`) via config only; “add a new lecturer” guide.

**Later, if wanted:** English subtitle track, chapter LLM generation for the whole
back catalogue, calendar, “notes & wisdom” clips, live streaming, word-level karaoke.

---

## 10. Risks

| Risk | Mitigation |
| --- | --- |
| Corrected text drifts too far from raw ASR to align | Anchor-gap report; strip `[…]` / translations / appendix; fallback to `.cleaned.txt` |
| Unspoken editorial text steals audio time | Bracket + translation + list/table stripping in `transcript.py` (see §4.2.1) |
| Mp3 container duration ≠ decoded length → seek / clock drift | `prepare_playback.py` → `NNN_play.m4a`; prefer in `SessionFiles` |
| Persian font licensing for a commercial/public site | Vazirmatn + Amiri (SIL OFL) in use; IRANYekanX still optional via config |
| Audio bandwidth costs | Object storage with range requests; optional lower-bitrate variant later |
| iOS background audio limits in a webview | Capacitor native audio plugin in Phase 3; Media Session already covers most of it |
| Transcription is incremental (first 10 done; rest later) | Site lists all 75 sessions; only transcribed ones get subtitles. Re-run build after each batch |
| `npm run build` while `npm run dev` is running | They share `.next` — stop one before the other, or restart dev after a production build |

---

## 11. Decisions (agreed)

| # | Question | Decision | Consequence |
| --- | --- | --- | --- |
| 1 | Site mode | **Single-lecturer (Bayat) now, portal later** | Lecturer segment stays in every route and data path from day one, just hidden in the UI. Expanding is a config flip, not a migration. |
| 2 | Branding | **Reuse the fonts and palette; no branding of any kind** | IRANYekanX / IRANSansWeb / Traditional Arabic intended; currently shipping Vazirmatn + Amiri. Brand name set to «دروس معرفت نفس». |
| 3 | Mobile | **Capacitor** | One codebase and one UI for web, Android and iOS. Not scaffolded yet. |
| 4 | Hosting | **Local first, then Google Cloud** | Dev streams from `Audios/` via symlink. Production: Cloud Storage + CDN. |
| 5 | English subtitles | **Not now, Persian only** | Pipeline still emits a `lang` field per track. |

---

## 12. Progress log

### Done

- **Content pipeline** for Bayat / `marefat_nafs`: alignment, cue generation, course/session JSON, search data for the 10 transcribed sessions.
- **Web app** at `apps/web`: home, course, player, full text, search, my-list; static export.
- **Sync hardening:** strip bracketed asides; cue abutting; rAF time polling; no page auto-scroll (transcript panel follow is optional).
- **Playback remux** for sessions whose mp3 headers under-report duration (001, 004–008 so far).
- **UI pass:** icons, subtitle stage, transport, cards, theme token pipeline.
- **Docs:** `README.md` quick start + conventions + changelog.

### Still open

- Capacitor / store builds (Phase 3)
- PWA offline caching
- Word-level karaoke highlight (data exists; UI not wired)
- `gen_chapters.py` / LLM chapter pass (chapters currently from `##` headings only)
- GCS upload helper
- Onboard a second lecturer to prove the template
- Finish ASR + correction for sessions 011+

### How to verify sync on a machine

```bash
# Alignment quality
.venv/bin/python website/tools/align_subtitles.py --course Audios/Bayat/marefat_nafs --report

# Honest playback files + refresh JSON URLs
.venv/bin/python website/tools/prepare_playback.py --course Audios/Bayat/marefat_nafs
.venv/bin/python website/tools/build_content.py --course Audios/Bayat/marefat_nafs --skip-subtitles

# Dev server
export PATH="$HOME/.local/node/bin:$PATH"
cd website/apps/web && npm run dev
# then Cmd+Shift+R on /bayat/marefat_nafs/001/ — check start and ~44′
```
