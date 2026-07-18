# IslamASR — Fish Audio Transcription CLI

Transcribe any audio **or video** file (MP4, MP3, WAV, M4A, MOV, etc.) using the
[Fish Audio](https://fish.audio) `transcribe-1` ASR model, and see exactly how
much the run cost.

## How it works

1. If you pass a video (or an unusual audio format), the audio track is
   extracted to a compact mono 16 kHz MP3 with `ffmpeg`.
2. The audio is sent to Fish Audio's ASR API.
3. The transcript (with optional per-segment timestamps) is saved next to the
   input file, and a cost summary is printed.

**Pricing:** Fish Audio ASR is `$0.36 per audio hour`, billed on the audio
duration processed and rounded up to the nearest second.

## Setup

```bash
# 1. (optional but recommended) create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. install dependencies
pip install -r requirements.txt

# 3. ffmpeg is required for video / non-standard audio input
brew install ffmpeg   # macOS
```

Your API key is read from `FISH_API_KEY`. A `.env` file in this folder is loaded
automatically (one is already created for you).

## Usage

```bash
# Basic — auto-detect language
python transcribe.py lecture.mp4

# Specify a language for better accuracy (e.g. Arabic, English, Chinese)
python transcribe.py khutbah.mp3 --language ar

# Custom output path
python transcribe.py interview.wav --output interview_transcript.txt

# Skip timestamps in the saved file
python transcribe.py talk.m4a --no-timestamps
```

### Example output

```
============================================================
SUMMARY
============================================================
Input file      : lecture.mp4
Audio duration  : 12:34 (754.20 s)
Billed duration : 755 s (rounded up to nearest second)
Rate            : $0.36 / audio hour
Estimated cost  : $0.075500 USD
Transcript saved: lecture.txt
============================================================
```

## Notes

- Keep your `.env` private — it holds your API key and is git-ignored.
- The printed cost is an estimate based on the reported audio duration; your
  Fish Audio dashboard is the source of truth for actual billing.
