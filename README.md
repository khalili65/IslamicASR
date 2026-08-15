# IslamASR — Persian/Arabic lecture transcription toolkit

Transcribe Islamic lectures (audio or video) and turn the raw ASR output into a
readable, citation-checked study document.

```bash
python transcribe.py lecture.mp3 --language fa                        # Fish Audio
python transcribe.py lecture.mp3 --language fa --provider elevenlabs  # ElevenLabs Scribe
```

Both write the same `lecture.txt` beside the media. The LLM cleanup stage that
turns it into a study document is described in
`prompts/lecture-transcript-pipeline.md`.

There is also `compare_asr.py`, an optional side-by-side bake-off across ten
providers — useful when evaluating a new service, not needed for normal runs.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then fill in the keys you want to test
```

`ffmpeg` is required for chunking and for video input. If you don't have
Homebrew, `pip install static-ffmpeg` (already in `requirements.txt`) downloads
the binaries into the virtualenv and the toolkit finds them automatically. If
you do have ffmpeg on your `PATH`, that is used instead.

## Getting audio out of an Eitaa channel

Eitaa has no public API for channel media. The public web view lists file
names, durations and sizes but never a downloadable URL, and web.eitaa.com
fetches files over an authenticated session. So this comes in two steps:

```bash
# 1. See what audio a channel has (no login, nothing downloaded)
python scripts/eitaa_list.py shajareh --pages 20

# 2. Download it through your own logged-in session
pip install playwright && playwright install chromium
python scripts/eitaa_download.py shajareh --login          # once
python scripts/eitaa_download.py shajareh --dry-run
python scripts/eitaa_download.py shajareh --out Audios/Shajareh --name-contains سخنرانی --jobs 2
```

The download step drives the real web client with Playwright. By default it
uses the client's search API (reaches old posts), builds `/stream/` URLs, then
downloads in parallel (`--jobs`, default 2; higher often gets HTTP 408). Pass
`--via-scroll` for the older DOM-scroll path. Files already in the output
directory are skipped.

## Transcribing

```bash
python transcribe.py "Audios/.../lecture.mp3" --language fa
python transcribe.py "Audios/.../lecture.mp3" --language fa -p elevenlabs
```

Flags: `-p/--provider` (`fish` default, or `elevenlabs`), `-l/--language`,
`-o/--output`, `-m/--model`, `--no-timestamps`, `--no-cache`.

The transcript is written to `lecture.txt` next to the media, as continuous
text followed by a `--- Segments ---` block. Each chunk is cached in
`.asr_cache_<name>/`, so a re-run after a crash costs nothing.

### fish or elevenlabs?

| | `fish` (default) | `elevenlabs` |
|---|---|---|
| Price / audio hour | $0.36 | **$0.22** |
| One 67-minute lecture | $0.40 | **$0.25** |
| Persian support | undocumented, auto-detected | documented, 5–10% WER |
| Timestamps | segment only | word level |
| Diarization | no | up to 32 speakers |
| Requests for 67 min | 23 (chunked at 3 min) | **1** |

ElevenLabs is cheaper and the only one of the two that documents Persian
support; Fish is what the existing transcripts in this repo were made with.

## Comparing providers (optional)

Not needed for normal runs — this is for evaluating a service you have not used
before. You do not need every key; only configured providers run.

```bash
# Which providers exist, what they cost, and which keys you have
python compare_asr.py --list

# 5-minute bake-off across every provider you have a key for
python compare_asr.py "Audios/Tadabor_Sobohi/OstadBayat/Sample/lecture.mp3"

# Two specific providers, first 10 minutes
python compare_asr.py lecture.mp3 -p elevenlabs,fish --sample-minutes 10

# Full lecture with whichever provider won
python compare_asr.py lecture.mp3 -p elevenlabs --full
```

Output goes to `<name>_asr_compare/`:

```text
lecture_asr_compare/
  lecture.elevenlabs.txt     transcript per provider (+ timestamps)
  lecture.fish.txt
  comparison.md              side-by-side table and text previews
  .cache/                    per-chunk cache, so a re-run is free
```

Useful flags: `--language fa` (default), `--diarize` for speaker labels,
`--model` to override a provider's model, `--no-cache` to force fresh calls,
`--price-per-hour` if your plan's rate differs from the built-in estimate.

To feed the cleanup pipeline, add `--save-as` so the transcript also lands
beside the media under the name the later steps expect:

```bash
python compare_asr.py lecture.mp3 -p elevenlabs --full --save-as lecture.txt
```

### Which providers support Persian, and what they cost

Prices verified 2026-08-13; full sourcing in `research/asr-providers-2026.md`.
The last column is one 67-minute lecture.

| Provider | Model | Farsi | Timestamps | Diarization | $/hour | 67 min |
|---|---|---|---|---|---:|---:|
| groq | whisper-large-v3-turbo | yes | word+segment | no | $0.040 | $0.045 |
| groq | whisper-large-v3 | yes | word+segment | no | $0.111 | $0.124 |
| assemblyai | universal-2 | yes (lowest tier) | word+segment | +$0.02/hr | $0.150 | $0.167 |
| elevenlabs | scribe_v2 | yes (5–10% WER) | word | 32 speakers, free | $0.220 | $0.245 |
| deepgram | nova-3 | yes | word | +$0.12/hr | $0.258 | $0.288 |
| openai | gpt-transcribe | yes | **none** | no | $0.270 | $0.302 |
| azure | fast-transcription | yes | word+segment | free | $0.360 | $0.402 |
| **fish** | transcribe-1 | undocumented | segment only | no | $0.360 | $0.402 |
| speechmatics | standard | yes | word+segment | yes | $0.450 | $0.503 |
| google | chirp_2 (sync) | yes | word | no for fa | $0.960 | $1.072 |
| local-whisper | large-v3 | yes | word+segment | via pyannote | free | free |

Three things that are easy to get wrong:

- **Persian on AssemblyAI works only on `universal-2`**, not on their newer
  Universal-3 Pro. Deepgram supports Persian on `nova-3` but **not** `nova-2`.
- **OpenAI's `gpt-*` transcription models return no timestamps at all.** Only
  `whisper-1` does, and it has been dropped from the public price list.
- Azure and Google both have async batch APIs at $0.18/hour — roughly half of
  what the synchronous endpoints used here cost — but they require uploading to
  blob/GCS storage first, which this toolkit does not do.

For Persian specifically, two independent 2026 benchmarks
([code-switching](https://perle.ai/resources/asr-code-switching-benchmark-english-arabic-persian-german/),
[PSRB](https://doi.org/10.48550/arxiv.2505.21230)) put ElevenLabs Scribe and
Google Chirp ahead of Whisper-based options. Note that WER understates Persian
quality because Perso-Arabic spelling variants count as errors — read the
sample transcripts rather than trusting the numbers.

If you are working from inside Iran, most of these providers are unreachable
for sanctions reasons and payment is the harder wall than the API. In that case
`local-whisper` with a Persian fine-tune is the realistic option; see the
research file for Iranian-hosted alternatives.

**Always compare on a sample first.** A 5-minute sample costs cents; a full
67-minute lecture across eight providers does not.

### Adding another provider

Providers live in `asr/providers.py`. Subclass `Provider`, fill in the metadata
(price, env var, limits, signup URL), implement `transcribe_chunk`, and add the
class to `REGISTRY`. Chunking, offsetting, caching, retries and cost estimation
are handled by `asr/runner.py`.

## After transcription

Raw ASR Persian is not readable as-is. Follow
`prompts/lecture-transcript-pipeline.md` for the cleanup stages:

1. Scrub hallucination loops offline (no re-billing).
2. Correct Quran/hadith/dua citations — `prompts/correct-islamic-citations.md`.
3. Clarity edit into readable Persian.
4. Add Farsi translations under Arabic, labelled as model-generated.
5. Save as `name.corrected.md`.

Never overwrite the raw `.txt`; corrected files sit beside it.

## Notes

- Keep `.env` private; it is git-ignored. Rotate any key that gets committed.
- Audio and video files are git-ignored — only transcripts are versioned.
- Printed costs are estimates from audio duration; the provider dashboard is
  the source of truth.
