# Lecture transcript pipeline (ASR → corrected Markdown)

This document describes the **end-to-end procedure** used for IslamASR lecture videos (example: *دوره تخصصی سطح یک مهارت تدبر — جلسه اول*).  
Use it as a checklist when processing a new MP3/MP4.

Related files:
- `transcribe.py` — Fish Audio ASR CLI
- `prompts/correct-islamic-citations.md` — prompt for fixing Quran / hadith / dua citations
- Output naming: `name.txt` → `name.corrected.md` (readable study file)

---

## Overview (high level)

```text
Video/Audio (mp4/mp3/…)
        │
        ▼
[1] Fish Audio ASR  (transcribe.py)
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
Final study file:  *.corrected.md
```

Do **not** overwrite the raw `.txt` from ASR. Always write new corrected files beside it.

---

## Prerequisites

1. **Python venv** with Fish Audio SDK:
   ```bash
   cd /path/to/IslamASR
   source .venv/bin/activate   # or: python3 -m venv .venv && pip install -r requirements.txt
   ```
2. **API key** in `.env`:
   ```bash
   FISH_API_KEY=your_key_here
   ```
3. **ffmpeg** installed (needed for video and for chunking long audio):
   ```bash
   brew install ffmpeg   # macOS
   ```
4. Cursor (or another agent) for citation correction + clarity edit, using the prompts below.

---

## Step 1 — Transcribe with Fish Audio ASR

### Command

```bash
source .venv/bin/activate
python transcribe.py "/path/to/lecture.mp4" --language fa
# optional:
#   -o "/path/to/lecture.txt"
#   --no-timestamps
```

Language tips:
- Persian lecture → `--language fa`
- Mostly Arabic → `--language ar`
- Mixed / unknown → omit `--language` (auto-detect)

### What `transcribe.py` already handles

| Issue | Behavior |
|---|---|
| Video input | Extracts mono 16 kHz audio via ffmpeg |
| Long files | Splits into **~3 minute** chunks (important — see below) |
| Cost | Prints estimated cost at **$0.36 / audio hour** (rounded up per second) |
| Output | Continuous text + optional `--- Segments ---` word timestamps |

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

Omit `--- Segments ---` in the corrected file unless asked to keep them. Add a short Corrections log (ref + what fixed + verification source).

### Deliverable

`lecture.corrected.txt` (citation-accurate Arabic/Persian religious text).

---

## Step 4 — Clarity edit (ideas must be readable)

Raw ASR Persian stays broken even after ayahs are correct. Do a **second pass**:

- Keep the **teacher’s ideas and argument structure**
- Fix heavy ASR garble so a student can follow
- Use light headings by topic (e.g. four tadabbur ayahs, Nisa 82 context, Muhammad 24)
- Do **not** invent new scholarly claims not present in the lecture
- Prefer saying “ASR cleaned for clarity” in a footer note

### Deliverable

Readable continuous prose (still may be `.txt` or already `.md`).

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

### Deliverable (final)

`*.corrected.md` — the study-ready file.

---

## File naming convention

| File | Role |
|---|---|
| `name.mp4` / `name.mp3` | Source media |
| `name.txt` | Raw Fish Audio ASR (+ optional Segments) |
| `name.corrected.txt` | Optional intermediate (citations fixed) |
| `name.corrected.md` | **Final** readable Markdown (+ model Farsi under Arabic) |

Keep all next to the media under `Audios/...` when possible.

---

## Suggested Cursor workflow (copy-paste)

**A) Transcribe (terminal)**

```bash
source .venv/bin/activate
python transcribe.py "Audios/.../lecture.mp4" --language fa
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

**D) Optional cleanup only**

```text
Do NOT re-call the ASR API. Scrub hallucination loops (e.g. repeated «ز») in the saved transcript only.
```

---

## Quality checklist (before you stop)

- [ ] Raw `.txt` preserved  
- [ ] Full duration covered (no multi-minute systematic timestamp holes if Segments kept)  
- [ ] Sacred quotes web-verified; surah/ayah names correct  
- [ ] Persian prose readable; ideas of the session clear  
- [ ] Every Arabic block has Farsi underneath with **model (not teacher)** label  
- [ ] Arabic visually large enough in Markdown preview  
- [ ] Footer explains what the model did vs what the teacher said  
- [ ] Cost of ASR noted if relevant (optional)

---

## Known pitfalls

1. **Sending one long file to Fish ASR** → `Maximum file size exceeded` (PCM limit) or incomplete timestamps. Use `transcribe.py` chunking (~3 min).  
2. **Trusting Segments alone** → text can be complete while timestamps look truncated. Check continuous text first.  
3. **Hallucinated token storms** in noisy/hard passages → clean offline; don’t assume the lecturer said that.  
4. **Over-polishing Persian** in the citation-only pass → do clarity as a **separate** step after citations.  
5. **Unlabeled translations** → students may think the teacher translated the ayah in class. Always label model translations.  
6. **API key in `.env`** → keep gitignored; rotate if exposed.

---

## Example completed run

Path pattern from the first lecture:

```text
Audios/Tadabor_Sobohi/Term1/
  …جلسه اول….mp4
  …جلسه اول….txt                 ← ASR
  …جلسه اول….corrected.md        ← final study file
```

Approximate cost for ~1h45m: **~$0.63** on Fish Audio `transcribe-1`.

---

## Maintenance

When Fish Audio limits, pricing, or SDK usage change, update:

- `transcribe.py` (chunk size / pricing constants)
- this pipeline doc
- `README.md` if the CLI interface changes

When citation rules change, update only `prompts/correct-islamic-citations.md` and keep this file pointing to it.
