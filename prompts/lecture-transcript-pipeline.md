# Lecture transcript pipeline (ASR → corrected Markdown)

This document describes the **end-to-end procedure** used for IslamASR lecture videos (example: *دوره تخصصی سطح یک مهارت تدبر — جلسه اول*).  
Use it as a checklist when processing a new MP3/MP4.

Related files:
- `transcribe.py` — ASR CLI; `--provider fish` (default) or `--provider elevenlabs`
- `prompts/correct-islamic-citations.md` — prompt for fixing Quran / hadith / dua citations
- `research/asr-providers-2026.md` — provider prices, Persian support, limits
- Output naming: `name.txt` → `name.corrected.md` + `name.summary.md`

**Steps 2–6 do not depend on which provider you used.** Only Step 1 differs, and
its deliverable is always the same file: `name.txt` beside the media.

---

## Overview (high level)

```text
Video/Audio (mp4/mp3/…)
        │
        ▼
[1] ASR  (transcribe.py — fish or elevenlabs)
        │
        ▼
Raw transcript (.txt)  + optional Segments
        │
        ▼
[2] Offline cleanup  (hallucination loops, noise tokens)
        │
        ▼
[3] Islamic citation correction  (@ correct-islamic-citations.md)
        │
        ▼
[4] Clarity edit  (readable Persian; keep ideas, fix ASR garble)
        │
        ▼
[5] Add Farsi translations under Arabic  (label: model, not teacher)
        │
        ▼
[6] Polish Markdown  (larger Arabic font, structure, notes)
        │
        ▼
[7] Summarize  (short + outline + key takeaways; separate .summary.md)
        │
        ▼
Final study files:  *.corrected.md  +  *.summary.md
```

Do **not** overwrite the raw `.txt` from ASR. Always write new corrected files beside it.

---

## Prerequisites

1. **Python venv**:
   ```bash
   cd /path/to/IslamASR
   source .venv/bin/activate   # or: python3 -m venv .venv && pip install -r requirements.txt
   ```
2. **API key(s)** in `.env` — copy `.env.example` and fill in only the providers
   you intend to use. `python compare_asr.py --list` shows which are configured.
   ```bash
   FISH_API_KEY=your_key_here
   ELEVENLABS_API_KEY=your_key_here
   ```
3. **ffmpeg** (needed for video and for chunking long audio). Either is fine —
   the code finds whichever exists:
   ```bash
   pip install static-ffmpeg   # no Homebrew / admin rights needed; in requirements.txt
   brew install ffmpeg         # if you already use Homebrew
   ```
4. Cursor (or another agent) for citation correction + clarity edit, using the prompts below.

---

## Step 1 — Transcribe

### Command

```bash
source .venv/bin/activate

# Fish Audio (default — unchanged from before)
python transcribe.py "/path/to/lecture.mp4" --language fa

# ElevenLabs Scribe
python transcribe.py "/path/to/lecture.mp3" --provider elevenlabs --language fa

# optional:
#   -o "/path/to/lecture.txt"
#   --no-timestamps
#   --no-cache
```

Everything else is identical either way: same `lecture.txt` beside the media,
same `--- Segments ---` format, same cost summary. Only `--provider` changes.

Language tips:
- Persian lecture → `--language fa`
- Mostly Arabic → `--language ar`
- Mixed / unknown → omit `--language` (auto-detect)

### Choosing between the two

| | `fish` (default) | `elevenlabs` |
|---|---|---|
| Price / audio hour | $0.36 | **$0.22** |
| One 67-min lecture | $0.40 | **$0.25** |
| Persian support | undocumented, auto-detected | documented, 5–10% WER |
| Timestamps | segment only | word level |
| Diarization | no | up to 32 speakers |
| Requests for 67 min | 23 (chunked at 3 min) | **1** |

ElevenLabs is cheaper and better documented for Persian; Fish is what your
existing transcripts were made with. Both are wired up — use whichever you
prefer per lecture.

### What `transcribe.py` already handles

| Issue | Behavior |
|---|---|
| Video input | Extracts mono 16 kHz audio via ffmpeg |
| Long files | Splits into chunks sized to the provider's limit, then re-stitches timestamps |
| Cost | Prints an estimate from audio duration at the provider's rate |
| Output | Continuous text + optional `--- Segments ---` timestamps |
| Re-runs | Each chunk is cached in `.asr_cache_<name>/`, so resuming after a crash is free |

### Hard Fish Audio limits (why chunking exists)

Learned from real runs:

1. **Decoded PCM size** — API ~20 MB uncompressed. At 16 kHz mono 16-bit ≈ **~10–11 minutes** max per request (compressed MP3 size is misleading).
2. **Word timestamps freeze** — even when full text returns for a longer chunk, timestamps often stop around **~239 seconds (~4 min)**. That made earlier transcripts look “incomplete” in the Segments section.
3. **Safe chunk length** — keep chunks at **~3 minutes** so both **text** and **timestamps** stay complete.

### Cost example

~105 minutes ≈ **~$0.63** (`6278 s × $0.36 / 3600`).

### Deliverable

`lecture.txt` next to the media (or path from `-o`).

---

## Step 2 — Offline cleanup of ASR glitches (no re-submit)

Before or after citation work, scan for **decode hallucinations**, especially:

- Long loops: `ز ز ز ز …` or repeating phrases like `و القرآن، و القرآن، …`
- Random Latin / other-script leaks mid-Persian
- Empty or tiny middle chunks with nonsense tokens

**Do this locally** (regex / small script). Do **not** re-call the API just to fix loops unless a whole chunk failed.

Check coverage:
- Continuous text length vs lecture duration (rough speech density)
- Segment timestamps from `0` to end of audio
- Gaps of many minutes usually mean chunk/timestamp bugs, not silence

### Deliverable

Same `.txt` cleaned, or a temporary cleaned copy — still keep raw backup if possible.

---

## Step 3 — Correct Islamic citations

Use prompt: `prompts/correct-islamic-citations.md`

In Cursor, roughly:

```text
Follow @prompts/correct-islamic-citations.md
Source: @Audios/.../lecture.txt
(Optional) Audio/video: @Audios/.../lecture.mp4
```

### Rules (summary)

| Do | Don’t |
|---|---|
| Fix Quran, Nahj, hadith, dua when identifiable | Rewrite the whole lecture style |
| **Verify every sacred quote on the web** (e.g. alquran.cloud / tanzil / quran.com) | Trust memory alone for ayah wording |
| Fix mangled surah names, ayah numbers, صلوات / علیه السلام near quotes | Fix every casual Persian ASR error yet |
| Write `lecture.corrected.txt` (or later `.md`) — **never overwrite** raw ASR | Invent ayahs the speaker did not cite |
| **Keep full lecture length** — same speech, cleaned | **Condense, outline, or “digest” the talk** |

### Full-length rule (hard)

`*.corrected.txt` and `*.corrected.md` must cover the **entire lecture**, not a short
study digest.

- Target size: continuous corrected prose should stay in the same ballpark as the
  raw continuous ASR block (typically **≳70–100%** of its character count after
  removing `--- Segments ---`). Light tightening of filler is fine; dropping
  whole stories, asides, or middle sections is **not**.
- If the corrected file is roughly **under half** the raw continuous text, it is
  too short — go back and restore the missing speech.
- **Short form belongs only in `*.summary.md` (Step 7).** Never put the short
  version in `corrected.txt` / `corrected.md`.

Omit `--- Segments ---` in the corrected file unless asked to keep them. Add a short Corrections log (ref + what fixed + verification source).

### Deliverable

`lecture.corrected.txt` — **full-length**, citation-accurate continuous lecture text.

---

## Step 4 — Clarity edit (ideas must be readable)

Raw ASR Persian stays broken even after ayahs are correct. Do a **second pass**:

- Keep the **teacher’s ideas and argument structure**
- Keep **full coverage of the session** (same rule as Step 3: not a digest)
- Fix heavy ASR garble so a student can follow
- Use light headings by topic (e.g. four tadabbur ayahs, Nisa 82 context, Muhammad 24)
- Do **not** invent new scholarly claims not present in the lecture
- Prefer saying “ASR cleaned for clarity” in a footer note
- You may remove pure noise tokens (`[مکث]`, cough markers) and fix broken sentences;
  you may **not** delete anecdotes, Q&A asides, or whole topical stretches to “make it neat”

### Deliverable

Readable continuous prose covering the **whole** lecture (still may be `.txt` or already `.md`).

---

## Step 5 — Farsi translations under Arabic

For every Arabic block (opening formula, ayahs, short classical phrases):

1. Keep the **verified Arabic** as-is  
2. Under it, add a Persian translation  

**Required label (every time):**

```markdown
> **ترجمهٔ فارسی (توسط مدل، نه استاد):** …
```

Also put a banner note at the top and in the file footer:

> ترجمه‌های فارسیِ زیرِ متونِ عربی توسط **مدل** افزوده شده‌اند و گفته‌ی استاد در جلسه نیستند.

### Deliverable

Same file, now bilingual for Arabic passages.

---

## Step 6 — Final Markdown polish

Create / save:

```text
lecture.corrected.md
```

Recommended extras:

1. **Structure** — `##` / `###` sections matching the lecture flow  
2. **Larger Arabic** — wrap ayahs so preview is readable, e.g.:

```html
<p class="ayah-ar" dir="rtl" style="font-size:1.5em; line-height:2.1; font-family: Amiri, 'Scheherazade New', 'Noto Naskh Arabic', 'Geeza Pro', serif;">
«…الآية…» <span class="ayah-ref">(نساء/۴:۸۲)</span>
</p>
```

3. **Footer notes** — ASR cleanup, citation verification source, “model translations ≠ teacher”, Segments omitted  
4. Open with Markdown preview (`Cmd+Shift+V` in Cursor) to check Arabic size

### Deliverable (final study file)

`*.corrected.md` — the **full-length** study-ready file (not the summary).

---

## Step 7 — Summarize (separate file)

The polished transcript is for **study / reading along**. A summary is for
**review, sharing, and finding a section later**. Keep them as **two files**.

**Only this step is allowed to be short.** If you need a digest, write
`*.summary.md` — do not replace or shrink `*.corrected.md`.

### When to summarize

Only after Steps 4–6. Never summarize the raw ASR `.txt` — garbled names and
broken citations will pollute the summary. Base the summary on
`name.corrected.md` (or the clarity-edited text).

### What to produce

Write `name.summary.md` next to the media, with three layers in one file:

| Layer | Length | Purpose |
|---|---|---|
| **خلاصهٔ کوتاه** | ~5–10 sentences | What this session was about; shareable |
| **فهرست مطالب / نقشهٔ جلسه** | bullet outline of sections | Jump to a topic in the full `.corrected.md` |
| **نکات کلیدی** | 8–15 bullets | Claims, practices, warnings the teacher stressed |

Optional fourth block when useful:

| Layer | Purpose |
|---|---|
| **اصطلاحات و منابع** | Technical terms (وهم، خیال، انسان کامل، …) + books/refs named in the session |

### Rules

| Do | Don’t |
|---|---|
| Capture the teacher’s **structure and claims** | Invent conclusions the speaker did not reach |
| Keep Quran/hadith refs accurate (same as Step 3) | Quote long Arabic blocks again (link/point to `.corrected.md`) |
| Note practices (e.g. a recommended dhikr) clearly | Turn the summary into another full rewrite of the lecture |
| Label model work in a short footer | Pretend the summary was spoken by the teacher |
| Keep summary short on purpose | Use summary length as the target for `corrected.*` |

### Suggested Cursor prompt

```text
Using @Audios/.../lecture.corrected.md, write lecture.summary.md next to it.
Include: (1) short Persian summary, (2) section outline matching the MD headings,
(3) key takeaways / practices / warnings, (4) glossary of terms + sources named.
Do not invent claims. Footer: summary by model from the corrected transcript.
```

### Deliverable

`*.summary.md` beside the media (and beside `*.corrected.md`).

---

## File naming convention

| File | Role |
|---|---|
| `name.mp4` / `name.mp3` | Source media |
| `name.txt` | Raw ASR (+ optional Segments) |
| `name.corrected.txt` | Optional intermediate (citations fixed) |
| `name.corrected.md` | **Study** Markdown (+ model Farsi under Arabic) |
| `name.summary.md` | **Summary** (short + outline + takeaways) |

Keep all next to the media under `Audios/...` when possible.

---

## Suggested Cursor workflow (copy-paste)

**A) Transcribe (terminal)**

```bash
source .venv/bin/activate
python transcribe.py "Audios/.../lecture.mp3" --language fa
# or: --provider elevenlabs
```

**B) Citation pass (chat)**

```text
Follow @prompts/correct-islamic-citations.md on @Audios/.../lecture.txt
Verify every Quran/hadith quote online. Write lecture.corrected.txt next to it.
Omit Segments. Add a corrections log.
```

**C) Clarity + MD (chat)**

```text
Edit @Audios/.../lecture.corrected.txt into a clear study document.
Keep the teacher’s ideas; clean ASR Persian.
Save as lecture.corrected.md with headings.
Under every Arabic quote, add Farsi translation labeled:
«ترجمهٔ فارسی (توسط مدل، نه استاد)».
Make Arabic ayahs larger in Markdown preview (HTML style ~1.5em).
Add footer notes about ASR / model translations / omitted Segments.
```

**D) Summary (chat)**

```text
Using @Audios/.../lecture.corrected.md, write lecture.summary.md
with short summary + outline + key takeaways (+ optional glossary).
Do not invent claims. Footer: model summary from corrected transcript.
```

**E) Optional cleanup only**

```text
Do NOT re-call the ASR API. Scrub hallucination loops (e.g. repeated «ز») in the saved transcript only.
```

---

## Quality checklist (before you stop)

- [ ] Raw `.txt` preserved  
- [ ] Full duration covered (no multi-minute systematic timestamp holes if Segments kept)  
- [ ] **`corrected.txt` / `corrected.md` are full-length** (≳70% of raw continuous chars; not a digest)  
- [ ] Sacred quotes web-verified; surah/ayah names correct  
- [ ] Persian prose readable; ideas of the session clear  
- [ ] Every Arabic block has Farsi underneath with **model (not teacher)** label  
- [ ] Arabic visually large enough in Markdown preview  
- [ ] Footer explains what the model did vs what the teacher said  
- [ ] `*.summary.md` exists with short summary + outline + takeaways  
- [ ] Cost of ASR noted if relevant (optional)

---

## Known pitfalls

1. **Sending one long file to Fish ASR** → `Maximum file size exceeded` (PCM limit) or incomplete timestamps. Use `transcribe.py` chunking (~3 min).  
2. **Trusting Segments alone** → text can be complete while timestamps look truncated. Check continuous text first.  
3. **Hallucinated token storms** in noisy/hard passages → clean offline; don’t assume the lecturer said that.  
4. **Over-polishing Persian** in the citation-only pass → do clarity as a **separate** step after citations.  
5. **Unlabeled translations** → students may think the teacher translated the ayah in class. Always label model translations.  
6. **API key in `.env`** → keep gitignored; rotate if exposed.  
7. **Switching provider mid-lecture** → the chunk cache is keyed per provider, so a re-run with a different `--provider` re-bills the whole file.  
8. **Writing a short “study digest” into `corrected.txt` / `corrected.md`** → that belongs in `summary.md` only. Corrected files must stay full-length.

---

## Example completed run

Path pattern from the first lecture:

```text
Audios/Tadabor_Sobohi/Term1/
  …جلسه اول….mp4
  …جلسه اول….txt                 ← ASR
  …جلسه اول….corrected.md        ← study file
  …جلسه اول….summary.md          ← short + outline + takeaways
```

Approximate cost for ~1h45m: **~$0.63** on Fish Audio `transcribe-1`.

### Next lecture in the queue

`Audios/Tadabor_Sobohi/OstadBayat/Sample/` — a **1 h 06 m** سخنرانی (19.7 MB
mp3, mono 16 kHz). Note this is a *sermon / درس سیر و سلوک*, not a structured
tadabbur lesson: denser Arabic quotation and more rhetorical delivery than the
Term1 files. Cost for the full hour: **~$0.25 on ElevenLabs, ~$0.40 on Fish**.
Expected outputs in that folder: `…1405.txt`, `…1405.corrected.md`,
`…1405.summary.md`.

---

## Maintenance

When provider limits, pricing, or SDK usage change, update:

- `asr/providers.py` (price constants, model names, chunk/upload limits)
- `transcribe.py` (Fish chunk size / pricing constants)
- `research/asr-providers-2026.md` (dated price research)
- this pipeline doc
- `README.md` if the CLI interface changes

When citation rules change, update only `prompts/correct-islamic-citations.md` and keep this file pointing to it.
