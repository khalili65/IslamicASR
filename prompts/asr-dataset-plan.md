# ASR fine-tuning dataset plan (Persian + Islamic Arabic code-switching)

Goal: build a dataset of **10–15 second audio/text pairs** from lecture recordings, to fine-tune an ASR model that handles Persian lectures mixed with Qur'anic/Islamic Arabic (the exact place where generic ASR fails).

This document is the reference design. Related files:
- `transcribe.py` — Fish Audio ASR (step 1 source of transcripts + word timestamps)
- `prompts/lecture-transcript-pipeline.md` — the transcript cleanup pipeline
- `prompts/correct-islamic-citations.md` — citation verification prompt

---

## Why this dataset is valuable

People mix Farsi and Arabic constantly in religious lectures («اعوذ بالله…», ayahs, duas, صلوات). Generic models garble exactly these parts (we observed Fish producing `کتابون انزلناهو ایلی کمبارکن` for `كِتَابٌ أَنْزَلْنَاهُ إِلَيْكَ مُبَارَكٌ…`). A fine-tuned model needs paired examples of real code-switched speech with **verbatim** correct text.

---

## Golden rule: verbatim text only

For ASR training, the transcript must match what is actually spoken — word for word.

| Source file | Verbatim? | Use for training? |
|---|---|---|
| Raw `name.txt` (Fish ASR) | Yes (with errors) | Yes — starting point |
| `name.corrected.txt` (citations fixed) | Mostly | Only where the speaker truly recited the ayah literally |
| `name.corrected.md` (clarity edit) | **No** — rewritten | **Never** for training text; use only as *context* for the LLM judge |

---

## Pipeline overview

```text
lecture.mp4 + lecture.txt (Fish ASR + word timestamps)
        │
        ▼
[1] Slice audio at silences → 5–15 s clips (ffmpeg silencedetect)
        │
        ▼
[2] Map Fish words into each clip via timestamps → fish_text per clip
        │
        ▼
[3] Second opinion: local Whisper large-v3 per clip → whisper_text
        │
        ▼
[4] Automatic agreement score (WER fish vs whisper)
        │
        ▼
[5] LLM judge (text-based) → verdict + suggested text + confidence
        │
        ▼
[6] Route: accepted / needs human review / rejected
        │
        ▼
[7] Human review of the uncertain queue (Label Studio or simple HTML)
        │
        ▼
[8] Export JSONL manifest for fine-tuning
```

---

## Stage details

### 1. Slicing (automatic)

- `ffmpeg silencedetect` (e.g. `noise=-35dB:d=0.4`) to find pauses.
- Merge/split so clips land in **5–15 s** (target ~10 s); cut only at pauses, never mid-word.
- Export mono 16 kHz WAV per clip: `clips/lec001_0042.wav`.

Note from real data: Fish word timestamps are coarse in places (zeros at chunk starts), so **slice on silence** and then assign words into slices — don't trust each word timestamp individually.

### 2. Fish text per clip

- From the raw `.txt` `--- Segments ---` section, collect words whose timestamps fall inside the clip window.
- Keep chunk offsets in mind (the transcript was produced in ~3 min chunks).

### 3. Whisper cross-check (automatic, local, free)

- Run Whisper `large-v3` (or `distil-large-v3` for speed) locally on each clip with language hint `fa`.
- Whisper is the **acoustic** second opinion — this is the only stage besides the human that actually "hears" the audio.

### 4. Agreement scoring (automatic)

- Normalize both texts (strip diacritics, unify ی/ي، ک/ك، remove punctuation).
- Compute WER between `fish_text` and `whisper_text`.
- Also auto-flag regardless of WER:
  - repeated-token storms (like the `ز ز ز…` hallucination we hit),
  - suspicious script mixing (Latin/Thai fragments inside Persian),
  - clips overlapping known ayah quotes (Arabic recitation is where both models are weakest → always review or LLM-adjudicate),
  - too-short/too-long clips, music/crowd segments.

### 5. LLM judge (text-based — this is the extra column)

For each clip, an LLM (e.g. the agent in Cursor) receives:

1. `fish_text` (the candidate label)
2. `whisper_text` (acoustic second opinion)
3. **Context**: the surrounding paragraph from the raw transcript, plus the relevant span of `corrected.txt` / `corrected.md`, plus verified ayah texts where applicable

and outputs three fields:

| Field | Meaning |
|---|---|
| `llm_verdict` | `agree` (pair looks correct) / `fix` (proposes corrected text) / `unsure` |
| `llm_text` | The LLM's best verbatim transcript for the clip (may equal `fish_text`) |
| `llm_confidence` | `high` / `medium` / `low` |

**Honest limitation:** the LLM cannot hear audio. Its verdict is based on (a) Fish–Whisper agreement, (b) context from the corrected transcripts, (c) linguistic plausibility, and (d) exact ayah matching for recitations. This makes it a strong *third vote* and a great *label improver* (especially for ayahs, where the verified Qur'anic text is authoritative), but it is **not** a substitute for a human on genuinely ambiguous audio.

Where the LLM is strongest:
- Ayah/dua clips: match garbled ASR to the verified ayah → propose exact wording with high confidence.
- Obvious ASR typos where both engines almost agree (`میخوام` vs `می‌خوام`).
- Detecting hallucinations (text that fits no plausible Persian/Arabic).

Where the LLM must say `unsure`:
- Fish and Whisper disagree substantially on ordinary Persian content and context doesn't resolve it.
- Names, numbers, unclear audio moments.

### 6. Routing rules

| Condition | Bucket |
|---|---|
| WER low **and** `llm_verdict=agree` (high conf) | `accepted/` — use as-is |
| Ayah clip, LLM matched verified Qur'an text (high conf) | `accepted/` with `llm_text` as label |
| WER moderate, LLM `fix` with high/medium confidence | `review-fast/` — human just confirms LLM suggestion |
| WER high or LLM `unsure` | `review-full/` — human transcribes/edits |
| Hallucination storm, music, no speech | `rejected/` |

### 7. Human review

- Tool: **Label Studio** (free, local, audio transcription template) or a minimal HTML page.
- Reviewer sees: audio player + `fish_text` + `whisper_text` + `llm_text` and picks/edits.
- Expected effort: 10–15 s clips verify at 3–5× real time; typically **20–40%** of clips need review.

### 8. Export format

JSONL manifest (works with Hugging Face / Whisper fine-tuning scripts):

```json
{"audio": "clips/lec001_0042.wav", "text": "…verbatim transcript…", "duration": 11.8,
 "source": "accepted|review", "fish_text": "…", "whisper_text": "…",
 "llm_verdict": "agree", "llm_confidence": "high", "wer_fish_whisper": 0.04}
```

Keep the extra columns — they let you filter dataset quality tiers later (e.g. train first on `accepted` only, then add reviewed clips).

---

## Per-clip record (full schema)

| Column | Source | Description |
|---|---|---|
| `clip_id` | slicer | `lec001_0042` |
| `audio` | slicer | path to WAV |
| `start`, `end`, `duration` | slicer | position in original lecture |
| `fish_text` | Fish ASR | candidate label from timestamps |
| `whisper_text` | Whisper | acoustic second opinion |
| `wer_fish_whisper` | scorer | normalized WER |
| `flags` | scorer | `ayah`, `halluc`, `short`, … |
| `llm_verdict` | LLM judge | `agree` / `fix` / `unsure` |
| `llm_text` | LLM judge | best verbatim proposal |
| `llm_confidence` | LLM judge | `high` / `medium` / `low` |
| `final_text` | routing/human | the training label |
| `status` | routing/human | `accepted` / `reviewed` / `rejected` |

---

## Expected volume & effort

- 105-min lecture → **~400–600 clips** (~1.5 h of speech).
- Meaningful fine-tuning (e.g. Whisper LoRA) starts around **5–10 hours** of clean pairs → roughly 5–10 lectures.
- Auto-accept rate expected **60–80%**; the LLM-judge stage should push part of the "review" pile into "review-fast" (confirm-only), cutting human time further.

## Costs

- Whisper local → free (Apple Silicon handles large-v3; use distil/turbo variants for speed).
- LLM judge → depends on the model used in Cursor; batching ~50 clips per prompt keeps it cheap.
- No extra Fish API cost (we reuse the existing transcript).

## Risks / notes

1. **Timestamps** are the weakest link → always slice on silence, spot-check 10 random clips per lecture by listening.
2. **Corrected ayah text vs actual speech**: use verified ayah wording only when the speaker recited literally; if he paraphrased or broke off mid-ayah, the human reviewer decides.
3. **Rights/consent** for using and (especially) redistributing lecture audio as a dataset.
4. Keep the raw `.txt` and original media immutable; the dataset lives in its own folder.

---

## Proposed folder layout

```text
dataset/
  lec001/                      ← جلسه اول
    clips/*.wav
    records.jsonl              ← full per-clip schema
    accepted.jsonl
    review-fast.jsonl
    review-full.jsonl
    rejected.jsonl
  manifest_train.jsonl         ← merged final labels
```

---

## Next step (pilot)

Build `make_dataset.py`:
1. Input: `lecture.mp4` + raw `lecture.txt`.
2. Slice on silence → clips + `fish_text`.
3. Run local Whisper → `whisper_text` + WER.
4. Emit `records.jsonl` with empty LLM columns.
5. Then run the LLM judge in Cursor over `records.jsonl` (batched), filling `llm_*` columns and routing buckets.
6. Inspect numbers (accept rate, review load) on جلسه اول before scaling to the whole term.
