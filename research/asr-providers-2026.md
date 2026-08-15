# Persian (fa) Speech-to-Text API Landscape — August 13, 2026

Every price marked **VERIFIED** was read from the provider's own pricing page, official docs,
or official pricing API on 2026-08-13. Anything I could not confirm from a first-party source is
marked **UNVERIFIED**.

Reference workload: **67 minutes of audio = 1.11667 audio hours.**

---

## 1. Comparison table

| Provider | Model / endpoint | Price per audio hour (USD) | Farsi (fa) | Timestamps | Diarization | Cost for 67 min | Source |
|---|---|---|---|---|---|---|---|
| Groq | `whisper-large-v3-turbo` | **$0.04** | Yes (Whisper 99+) | word + segment | No | **$0.045** | [console.groq.com/docs/speech-to-text](https://console.groq.com/docs/speech-to-text) |
| Groq | `whisper-large-v3` | **$0.111** | Yes | word + segment | No | **$0.124** | same |
| AssemblyAI | `universal-2` (async) | **$0.15** | Yes (lowest accuracy band) | word + segment | +$0.02/hr | **$0.168** (+$0.022 diar) | [assemblyai.com/pricing](https://www.assemblyai.com/pricing) |
| OpenAI | `gpt-4o-mini-transcribe` | $0.003/min = **$0.18** | Yes (99+) | No (see §3.2) | No | **$0.201** | [developers.openai.com/api/docs/pricing](https://developers.openai.com/api/docs/pricing) |
| Google Cloud | STT v2 **dynamic batch**, Standard family | $0.003/min = **$0.18** | Yes `fa-IR` | word-level conf.; word timing | No for Chirp 2/3 fa | **$0.201** | [cloud.google.com/speech-to-text/pricing](https://cloud.google.com/speech-to-text/pricing) |
| Microsoft Azure | Speech to Text **Batch** (S1) | **$0.18** | Yes `fa-IR` | segment + word | Included (batch) | **$0.201** | Azure Retail Prices API, meter `S1 Speech to Text Batch` |
| ElevenLabs | `scribe_v2` (batch) | **$0.22** | Yes `fas` (5–10% WER band) | **word-level** | **Yes, ≤32 speakers** | **$0.246** | [elevenlabs.io/pricing/api](https://elevenlabs.io/pricing/api) |
| Speechmatics | Batch **Melia 1** (multilingual) | **$0.24** | Yes | word + segment | Yes | **$0.268** | speechmatics.com/pricing (embedded rate table) |
| Deepgram | `nova-3` pre-recorded, `language=fa` | $0.0043/min = **$0.258** | **Yes, `fa`** | word-level | +$0.0020/min | **$0.288** (+$0.134 diar) | [deepgram.com/pricing](https://deepgram.com/pricing) JSON-LD |
| Deepgram | `whisper-large` (Whisper Cloud) | $0.0048/min = **$0.288** | Yes | word/segment | +$0.0020/min | **$0.322** | same |
| OpenAI | `gpt-transcribe` (recommended) | $0.0045/min = **$0.27** | Yes | No | No | **$0.302** | OpenAI pricing page |
| Azure | Fast Transcription | **$0.36** | Yes `fa-IR` | segment + word | Yes | **$0.402** | Azure Retail Prices API |
| **Fish Audio (current)** | `transcribe-1`, `POST /v1/asr` | **$0.36** | Auto-detect; fa not documented | **segment only** | No | **$0.402** | [docs.fish.audio](https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits) |
| OpenAI | `gpt-4o-transcribe` | $0.006/min = **$0.36** | Yes | No | No | **$0.402** | OpenAI pricing page |
| OpenAI | `whisper-1` | **UNVERIFIED** (no longer on the pricing page) | Yes | **word + segment** | No | UNVERIFIED | see §3.2 |
| Speechmatics | Batch **Standard** | **$0.45** | Yes | word + segment | Yes | **$0.503** | speechmatics.com/pricing |
| Speechmatics | Batch **Enhanced** | **$0.75** | Yes | word + segment | Yes | **$0.838** | speechmatics.com/pricing |
| Google Cloud | STT v2 standard recognition (non-batch) | $0.016/min = **$0.96** | Yes `fa-IR` | word-level | No for fa | **$1.072** | cloud.google.com/speech-to-text/pricing |
| Azure | Real-time STT (S1) | **$1.00** | Yes `fa-IR` | word + segment | +$0.30/hr | **$1.117** | Azure Retail Prices API |
| Replicate | `openai/whisper` (large-v3) | Billed by GPU-second, not per hour | Yes | word + segment | No | **UNVERIFIED**, ≈$0.30–0.90 | [replicate.com/openai/whisper](https://replicate.com/openai/whisper) |
| Fireworks AI | whisper-v3-large | **Discontinued 2026-06-10** | — | — | — | N/A | [docs.fireworks.ai/updates/changelog](https://docs.fireworks.ai/updates/changelog) |
| Self-hosted | `faster-whisper` large-v3 | $0 + GPU/CPU cost | Yes | word + segment | Via pyannote | $0 + compute | §5 |
| Fars Ava (IR) | web panel + org API | ≈29,800 toman/hr | **Persian-native** | Subtitle output | Unknown | ≈33,300 toman | [amerandish.com/farsava](https://amerandish.com/farsava/) |
| Eboo (IR) | web panel | ≈14,900 toman/hr | Persian + 14 langs | Unknown | Unknown | ≈16,600 toman | [eboo.ir/audio-to-text](https://www.eboo.ir/audio-to-text) |
| Subchin (IR) | web panel + business API | ≈72,000 toman/hr | Persian-native | Subtitles | Unknown | ≈80,400 toman | [subchin.ir/pricing](https://subchin.ir/pricing) |
| Virava (IR) | web panel | 60,000 toman/hr (1,000/min) | Persian-native | Unknown | Unknown | ≈67,000 toman | [viravirast.com/virava](https://viravirast.com/virava/) |
| IOType (IR) | REST + WSS API | ≈210,000 toman/hr | Persian-native | Unknown | Unknown | ≈234,500 toman | [iotype.com/plans/api](https://iotype.com/plans/api) |
| Aipa / آیپا (IR) | REST API | "تماس بگیرید" (contact) | Persian + English | Unknown | Unknown | **UNVERIFIED** | [aipaa.ir/pricing](https://aipaa.ir/pricing) |
| Avanegar / آوانگار (IR) | inside Vira app | Free in-app; no public API price | Persian-native, all dialects | Unknown | Unknown | Free (app) | [ivira.ai/speech-to-text](https://ivira.ai/speech-to-text/) |
| Nevisa Live (IR) | web/app + API | 1 free hour, then paid | Persian-native | Unknown | Unknown | **UNVERIFIED** (site down) | [asr-gooyesh.com](https://asr-gooyesh.com/fa/portfolio/nevisalive/) |

Toman → USD conversion is **not** included because I did not verify a free-market exchange rate.
At a rough 90,000–120,000 toman/USD the Iranian figures land between ~$0.14 (Eboo) and ~$2.60 (IOType) for 67 minutes.

---

## 2. Headline findings

1. **Persian is officially supported almost everywhere now, including Deepgram.** Deepgram's Nova-3
   language list explicitly includes `Persian: fa`, which was not true of Nova-2. That removes the
   main reason people skipped Deepgram for Farsi.
2. **AssemblyAI supports Persian only on Universal-2, not Universal-3.5 Pro.** Universal-3.5 Pro covers
   18 languages and Persian is not among them; Persian sits in Universal-2's *lowest* accuracy tier.
3. **ElevenLabs Scribe v2 is the best price/feature combination for this workload.** $0.22/hr with
   word-level timestamps *and* 32-speaker diarization included in the base rate, Persian rated in the
   5–10% WER band, 3 GB / 10-hour files — no chunking needed for a 67-minute lecture.
4. **Fish Audio (what this repo uses today) is now one of the more expensive options** at $0.36/hr,
   and it is the weakest on features: segment-level timestamps only, no diarization, 20 MB / 60 min cap,
   and Persian is not in any published language list.
5. **Groq is 9× cheaper than Fish Audio** at $0.04/hr for `whisper-large-v3-turbo`, but caps files at
   25 MB (free) / 100 MB (dev) and Whisper's Persian WER is materially worse than Scribe v2's.
6. **Fireworks AI is out.** Audio inference was deprecated on 2026-06-10 and the endpoint now returns 401.

---

## 3. Per-provider integration details

### 3.1 ElevenLabs Scribe

- **Models:** `scribe_v2` (current batch SOTA, released 2026-01-12), `scribe_v2_realtime`.
  `scribe_v1` is officially listed as **deprecated** with `scribe_v2` as the recommended replacement.
- **Price:** $0.22/audio hour (batch), $0.39/hr realtime. Add-ons: entity detection +$0.07/hr,
  keyterm prompting +$0.05/hr. Billed per audio minute.
  *Scribe v1's current price is UNVERIFIED — the official pricing page only lists Scribe v2.*
- **Persian:** Yes — `Persian (fas)` is in the supported list and is classified under
  **"High Accuracy (>5% to ≤10% WER)"**, the second-best of five bands. This is the strongest
  documented Persian quality claim of any international provider.
- **Limits:** max file **3 GB**; max duration **10 hours** standard mode (1 hour multichannel).
  Audio and video accepted (MP3, WAV, FLAC, M4A, OGG, OPUS, AAC, AIFF, WebM; MP4, MKV, MOV, AVI, …).
- **Timestamps / diarization:** word-level timestamps with `speaker_id` per word; diarization up to
  **32 speakers**; also emits `audio_event` tokens for laughter/applause and `spacing` tokens.
- **Integration:** `pip install elevenlabs` — or REST:
  `POST https://api.elevenlabs.io/v1/speech-to-text` with header `xi-api-key: <API_KEY>`,
  `multipart/form-data` with `file` and `model_id=scribe_v2`.
- **Free tier:** Free/PAYG plan includes 4 h 30 m of Scribe per month.
- **Signup / keys:** https://elevenlabs.io/app/sign-up → developer dashboard at https://elevenlabs.io/app/developers

### 3.2 OpenAI

- **Current transcription rate card** (official pricing page):

  | Model | Price |
  |---|---|
  | `gpt-transcribe` | $0.0045 / minute (**recommended default**) |
  | `gpt-4o-transcribe` | $0.006 / minute ($2.50/$10.00 per 1M in/out tokens) |
  | `gpt-4o-mini-transcribe` | $0.003 / minute ($1.25/$5.00 per 1M tokens) |
  | `gpt-4o-transcribe-diarize` | token-based; the only OpenAI model with speaker labels |
  | `gpt-live-transcribe` / `gpt-realtime-whisper` | $0.017 / minute (streaming) |

- **`whisper-1` is no longer on OpenAI's published pricing table.** It is still callable and is
  still the model the docs point to for `/v1/audio/translations` and for `timestamp_granularities`,
  but I could not verify a current price from an official source. **UNVERIFIED** — do not assume $0.006/min.
- **Persian:** supported. `gpt-transcribe` takes a `languages` array; `whisper-1` takes `language`
  and covers Whisper's 98 languages, Persian included.
- **Limits:** **25 MB** per request, formats `mp3, mp4, mpeg, mpga, m4a, wav, webm`. No explicit
  duration cap — 25 MB is the binding constraint, so a 67-minute lecture needs compression or chunking.
- **Timestamps:** `timestamp_granularities[]` (`word`, `segment`) is **only supported on `whisper-1`**.
  The gpt-4o/gpt-transcribe family does **not** return timestamps. This is a real constraint if you
  need timed segments.
- **Diarization:** only via `gpt-4o-transcribe-diarize` with `response_format="diarized_json"`,
  and that model does not accept prompts.
- **Integration:** `pip install openai` — or `POST https://api.openai.com/v1/audio/transcriptions`
  with `Authorization: Bearer $OPENAI_API_KEY`, `multipart/form-data`.
- **Signup / keys:** https://platform.openai.com/api-keys
- **Accessibility:** see §6 — Iran is an unsupported country.

### 3.3 Google Cloud Speech-to-Text V2 (Chirp 2 / Chirp 3)

- **Pricing (V2):** Standard recognition **$0.016/min** for the first 500k min/month, dropping to
  $0.01 (500k–1M), $0.008 (1M–2M), $0.004 (2M+). **Dynamic batch recognition: $0.003/min** flat —
  this is the option to use for pre-recorded lectures. Billed in 1-second increments, per channel.
- **Persian:** Yes, `fa-IR`, verified in the official language matrix:
  - `chirp` and `chirp_2` in `us-central1`, `europe-west4`, `asia-southeast1`
  - `chirp_3` in the `us` and `eu` multi-regions
  - Features available for `fa-IR`: automatic punctuation, model adaptation, profanity filter.
    `chirp_3` for `fa-IR` does **not** list word-level confidence, and **diarization is not listed
    for Persian on any Chirp variant**.
- **Limits:** `BatchRecognize` accepts GCS URIs only, ≤5 files per request, **each file up to 8 hours**.
  Sync `Recognize` is capped at 10 MB / 1 minute.
- **Integration:** `pip install google-cloud-speech` — or REST
  `POST https://{region}-speech.googleapis.com/v2/projects/{PROJECT}/locations/{LOCATION}/recognizers/_:batchRecognize`
  with `Authorization: Bearer $(gcloud auth print-access-token)`.
- **Free tier:** V1 gives 60 min/month free; the V2 table shows no free tier.
- **Signup / keys:** https://console.cloud.google.com/apis/credentials
- **Caveat:** the $0.003 dynamic-batch footnote enumerates `default, command_and_search, latest_short,
  latest_long, phone_call, video, chirp` — it names `chirp` but not `chirp_2`/`chirp_3` explicitly.
  Treat Chirp 2/3 at the Standard rate as **likely but not airtight**; confirm on your first invoice.

### 3.4 Microsoft Azure AI Speech

All figures below come from Microsoft's **official Azure Retail Prices API**
(`https://prices.azure.com/api/retail/prices`, `eastus`, product `Azure Speech`) — the marketing page
renders prices client-side and shows `$-` to scrapers.

| Meter | Price |
|---|---|
| `S1 Speech to Text Batch` | **$0.18 / hour** |
| `Fast Transcription Speech To Text` | $0.36 / hour |
| `S1 Speech To Text` (real-time) | $1.00 / hour |
| `S1 Custom Speech to Text Batch` | $0.225 / hour |
| `S1 Speech to Text Enhanced Feature Audio` (diarization, cont. LID, prosody — real-time only) | $0.30 / hour |
| `Free Speech To Text` | $0.00 (5 audio hours/month, real-time only — **batch not supported on F0**) |

- **Persian:** Yes, `fa-IR`, verified in the official language-support tables for speech-to-text,
  custom speech (plain text + pronunciation), and captioning. Note `fa-IR` is marked **No** for one
  capability column in the pronunciation/assessment table.
- **Diarization:** **included at no extra charge for batch** — the $0.30/hr enhanced add-on applies to
  real-time only. That makes Azure batch the cheapest diarized option at $0.18/hr all-in.
- **Limits (third-party aggregation, **not** confirmed first-party): max audio file 1 GB, max 240 min
  with diarization, ≤1,000 files per batch request, diarization up to 35 speakers. **Treat as UNVERIFIED.**
- **Integration:** batch is REST-only —
  `POST https://{region}.api.cognitive.microsoft.com/speechtotext/v3.2/transcriptions` with header
  `Ocp-Apim-Subscription-Key: <KEY>`. (Batch pricing requires **REST API v3.2 or later**, per the
  pricing page footnote.) Real-time SDK: `pip install azure-cognitiveservices-speech`.
- **Signup / keys:** https://portal.azure.com → create an *Azure AI Speech* resource → Keys and Endpoint.

### 3.5 Fish Audio (current stack)

- **Model:** `transcribe-1`, endpoint `POST https://api.fish.audio/v1/asr`.
- **Price:** **$0.36 / audio hour**, billed on duration processed, rounded up to the nearest second.
  Pay-as-you-go, no subscription or minimum. **Confirmed still accurate** — the $0.36 figure in
  `transcribe.py` matches the current official docs.
- **Persian:** **Not documented.** The docs say `language` is optional and auto-detected, and give
  `en`, `zh`, `ja` as examples. There is **no published supported-language list**, so Persian support
  is best-effort/unverified. `language_code` comes back as ISO 639-1 in the response.
- **Limits:** **20 MB and 60 minutes** per request, minimum 1 second. Your `transcribe.py` already
  chunks at 3 minutes because word-level timestamps empirically freeze around ~239 s — that's a
  known-in-practice limitation beyond the documented ones.
- **Timestamps:** **segment-level only** (`{text, start, end}`). No word-level output, no diarization,
  no speaker IDs. Set `ignore_timestamps=false` (REST/JS) or `include_timestamps=True` (Python).
- **Rate limits:** concurrency tiers by lifetime spend — 5 concurrent (<$100), 15 (≥$100), 50 (≥$1,000).
- **Integration:** `pip install fish-audio-sdk` (imports as `fishaudio`), auth `Authorization: Bearer $FISH_API_KEY`.
- **Signup / keys:** https://fish.audio/go/api-keys (developer console at https://fish.audio/developers/)

### 3.6 AssemblyAI

- **Price:** `universal-3-pro` $0.21/hr, `universal-2` $0.15/hr (async). Async diarization +$0.02/hr
  standard or +$0.065/hr experimental. Keyterms +$0.05/hr. **$50 free credits, no card required.**
- **Persian: supported on Universal-2 only.** Universal-3.5 Pro covers 18 languages and Persian is not
  one of them; the docs recommend `speech_models: ["universal-3-5-pro", "universal-2"]` with
  `language_detection: true` to auto-fall-back. Persian (Farsi) sits in Universal-2's **lowest**
  accuracy group alongside Afrikaans, Belarusian, Welsh, Armenian.
- **Gotcha:** if you pass `language_code="fa"` explicitly and enable a feature Persian doesn't support,
  the API **rejects the request**. With `language_detection` it silently drops the unsupported feature instead.
- **Integration:** `pip install assemblyai` — or `POST https://api.assemblyai.com/v2/transcript`
  with `Authorization: <API_KEY>` (no "Bearer"). EU region: `api.eu.assemblyai.com`, same price.
- **Signup / keys:** https://www.assemblyai.com/dashboard/signup

### 3.7 Deepgram

- **Persian: YES.** `nova-3` / `nova-3-general` explicitly lists `Persian: fa` in the official
  Models & Languages table. Nova-2 does **not** include Persian, and Persian is not in the `multi`
  code-switching set — so you must pass `language=fa` explicitly, which bills at the **monolingual** rate.
- **Price (pre-recorded, pay-as-you-go, from the pricing page's structured data):**
  Nova-3 Monolingual **$0.0043/min** ($0.258/hr), Nova-3 Multilingual $0.0052/min,
  Whisper Large $0.0048/min. Growth plan: $0.0036/min monolingual.
  Add-ons: diarization +$0.0020/min, keyterm prompting +$0.0013/min, entity detection +$0.0017/min,
  smart formatting included. *(The streaming table shows promotional strike-through pricing;
  the pre-recorded rows do not.)*
- **Free tier:** $200 credit, no card required.
- **Limits:** REST concurrency up to 50. Whisper Cloud models are capped at 20 minutes of processing
  time and 5–15 concurrent requests — use `nova-3`, not Whisper Cloud.
- **Integration:** `pip install deepgram-sdk` — or
  `POST https://api.deepgram.com/v1/listen?model=nova-3&language=fa&diarize=true&punctuate=true`
  with `Authorization: Token <DEEPGRAM_API_KEY>` and the raw audio as the body.
- **Signup / keys:** https://console.deepgram.com/signup

### 3.8 Speechmatics

- **Persian: yes**, listed in the official 56+ language set with a dedicated product page
  (speechmatics.com/speech-to-text/persian).
- **Price (Pro plan, per audio hour, from the rate table embedded in the official pricing page):**
  Batch Melia 1 **$0.24**, Batch Standard **$0.45**, Batch Enhanced **$0.75**,
  Real-time Standard $0.45, Real-time Enhanced $0.80. Bolt-ons: translation $0.65/hr,
  chapters $0.40/hr, topics $0.20/hr, summaries/sentiment $0.12/hr.
  The "from $0.129/hr" headline on the pricing page is the discounted Melia rate, not the list price.
  Melia 1 is batch-only and is the multilingual/code-switching model.
- **Discounts:** 20% automatic above 500 hours/month per STT product type; **33% off** if you opt into
  the model-training programme; more above 24,000 hours/year.
- **Free tier:** $100 credit, no card required. Billed to the second, monthly in arrears.
- **Integration:** `pip install speechmatics-python` — or
  `POST https://asr.api.speechmatics.com/v2/jobs` with `Authorization: Bearer <API_KEY>`,
  multipart with `data_file` and a `config` JSON specifying `"language": "fa"`.
- **Signup / keys:** https://portal.speechmatics.com/signup/

### 3.9 Groq

- **Price:** `whisper-large-v3` **$0.111/hr**, `whisper-large-v3-turbo` **$0.04/hr**,
  `distil-whisper` $0.02/hr (English only). **Minimum 10 seconds billed per request.**
- **Persian:** yes, both models are multilingual (Whisper's 99+ languages); pass `language="fa"`.
  Turbo does **not** support translation, only transcription.
- **Limits:** max file **25 MB (free tier) / 100 MB (dev tier)**; use the `url` parameter to exceed
  the 25 MB attachment limit. Minimum 0.01 s. Audio shorter than 30 s is silence-padded.
  Free-tier rate limits: 20 RPM, 2,000 RPD, 7,200 audio-seconds/hour, 28,800 audio-seconds/day —
  a 67-minute file (4,020 s) fits inside the daily allowance.
- **Timestamps:** `response_format="verbose_json"` + `timestamp_granularities=["word","segment"]`.
  Returns `avg_logprob`, `no_speech_prob`, `compression_ratio` per segment — useful quality signals.
- **Diarization:** none.
- **Integration:** `pip install groq` — or
  `POST https://api.groq.com/openai/v1/audio/transcriptions` with `Authorization: Bearer $GROQ_API_KEY`.
  OpenAI-compatible, so it's a near drop-in.
- **Signup / keys:** https://console.groq.com/keys

### 3.10 Replicate / Fireworks

- **Fireworks AI: no longer an option.** The official changelog entry "Audio inference and image
  generation deprecation" is dated **2026-06-10**; `api.fireworks.ai/.../audio/transcriptions` returns
  401 for all requests and `whisper-v3` / `whisper-v3-turbo` are gone from their model list. The
  historical $0.0015/min serverless rate is dead. (Fireworks still markets an *enterprise* speech
  offering at fireworks.ai/speech-recognition, but with no self-serve published pricing.)
- **Replicate `openai/whisper` (large-v3):** billed by **GPU-second, not per audio hour**. The model
  page states "approximately $0.0069 to run… varies depending on your inputs", runs on Nvidia T4
  ($0.000225/sec = $0.81/hr of GPU time), typical prediction ~31 s. Extrapolating to 67 minutes of
  audio is unreliable, so the 67-minute cost is **UNVERIFIED** (rough band $0.30–$0.90 including
  cold-boot time). Word + segment timestamps are supported; no diarization.
  `pip install replicate`, `Authorization: Bearer r8_...`, keys at https://replicate.com/account/api-tokens.

---

## 4. Iranian / Persian-native providers

None of these publish USD pricing; all quote Iranian toman, all require an Iranian payment card
(شتاب), and most gate the API behind a sales conversation.

| Service | Company | Site | Pricing | API? |
|---|---|---|---|---|
| **Fars Ava / فارس‌آوا** | Amerandish / عامر اندیش | amerandish.com/farsava, store.farsava.com | 1 h **free**; 1 h 35,000 T; 5 h 166,000 T; 10 h 298,000 T; 25 h 700,000 T; 50 h 1,313,000 T (≈**29,800 T/hr** at 10 h) | Yes, but **organisations only** — manual account setup, call 021-22556400. On-prem install available (one-time licence). |
| **Aipa / آیپا** | آرمان رایان شریف | aipaa.ir | Speech-to-text priced **per uploaded minute, rounded up**; the rate cell reads **"تماس بگیرید"** (contact us). Their worked example uses 200 T/min illustratively — not a published rate. | Yes, REST/OpenAPI + Swagger |
| **Avanegar / آوانگار** | Vira / ویرا | ivira.ai/speech-to-text | **Free** in the Vira app (Android/web); a "professional/subscription" tier is mentioned without prices. No public API pricing. | Not publicly documented |
| **Nevisa Live / نویسا لایو** | عصر گویش‌پرداز (Asr Gooyesh Pardaz), Sharif University spin-off | asr-gooyesh.com, nevisalive.com | **1 hour free credit**, then user-purchased top-ups. Exact rates **UNVERIFIED** — nevisalive.com returned HTTP 504 during this research. | Yes — "با در اختیار قراردادن api سامانه به توسعه‌دهندگان" |
| **IOType / ای‌او تایپ** | iotype.com | iotype.com/api-service | Token-based: **50 tokens per minute** of file transcription. Packages: 2,000 tok 150,000 T; 10,000 tok 700,000 T; 50,000 tok 2,500,000 T; 100,000 tok 4,500,000 T. At the 10k tier ≈ **3,500 T/min ≈ 210,000 T/hr** — the most expensive Iranian option found. | Yes, REST + WSS, `Authorization: Bearer <token>` |
| **Eboo / ایبو** | eboo.ir | eboo.ir/audio-to-text | 60 s free; 120 min 39,000 T; 300 min 89,000 T; 600 min 149,000 T; 1,200 min 270,000 T (≈**225 T/min** at the top tier) | Not documented |
| **Virava / ویرآوا** | ویراویراست | viravirast.com/virava | **1,000 T/min** stated in the FAQ. Packages: 60 min 60,000 T; 330 min 313,500 T; 660 min 594,000 T; 3,300 min 2,904,000 T | Not documented |
| **Subchin / سابچین** | subchin.ir | subchin.ir/pricing | Free trial 30 min STT; پایه 288,000 T / 240 min; رشد 806,400 T / 720 min; حرفه‌ای 2,880,000 T unlimited | API only on the business plan |
| **Capzy / کپزی** | capzy.app | capzy.app/speech-to-text | 5 free minutes on signup, then bronze/silver/gold plans — **prices not rendered publicly**; UNVERIFIED | Yes, REST + JS SDK, "دریافت دسترسی API" |
| **Nova Sharif / نوا هوشمند شریف** | novasharif.com | novasharif.com | Not published | Yes, ASR + diarization + speaker ID + denoise |
| **Alavan / آلاوان** | alavan.ai | alavan.ai | "مدل‌های صوتی از **33 تومان**" — unit not specified on the page; **UNVERIFIED** | Yes, API marketplace |
| **Lemura** | lemura.ir | lemura.ir | Not published | Yes, `POST api.lemura.ir/v1/audio/transcribe` |
| **Mehranote / مهرانٌت** | مدیران هوش ربات ایلیا | mehraai.ir | Not published; claims >95% Persian accuracy | Yes, cloud or on-prem |

**Note on "Avanegar":** there is no `avanegar.ir` — the DNS does not resolve. آوانگار is the name of
the speech-to-text *feature* inside the Vira (ویرا) AI app at ivira.ai, not a standalone commercial
API vendor. If you were expecting a separate company, that expectation appears to be wrong.

---

## 5. Self-hosted options (free, needs GPU/CPU)

### faster-whisper
- `pip install faster-whisper` — CTranslate2 reimplementation of Whisper, ~4× faster than
  `openai/whisper` at equal accuracy, with much lower VRAM in int8/float16.
- Weights: **`Systran/faster-whisper-large-v3`** (auto-downloaded when you pass `"large-v3"`).
- Word-level timestamps via `word_timestamps=True`. Diarization requires bolting on `pyannote.audio`.
- Cost: $0 in licence fees. A 67-minute file on a consumer GPU (RTX 3090/4090, float16) runs in
  roughly 3–6 minutes; on CPU int8 expect closer to real time.

### Persian fine-tuned Whisper checkpoints on Hugging Face

| Model ID | Base | Reported WER | Notes |
|---|---|---|---|
| **`nezamisafa/whisper-persian-v4`** | `openai/whisper-large-v3` | **8.73%** on ASR_fa_v1 | Best reported Persian WER found; 2B params, F32. **Recommended starting point.** |
| `vhdm/whisper-large-fa-v1` | `openai/whisper-large-v3-turbo` | 14.07% on persian-voice-v1 | Faster turbo backbone; author warns it degrades on noisy/dialectal audio |
| `Alireza48/whisper-large-fa-v1` | same as above | 14.07% | Mirror of the vhdm model |
| `mohammadjavadnasri/whisper-large-v3-farsi-cv17` | `openai/whisper-large-v3` | 23.47% (Common Voice 17) | Common Voice only |
| `nezamisafa/whisper-v3-turbo-persian-v1.0` | `openai/whisper-large-v3-turbo` | 29.94% (Common Voice 17) | 0.8B params |

WER numbers are self-reported by each author on **different** eval sets, so they are not directly
comparable. `nezamisafa/whisper-persian-v4`'s 8.73% is on a private-ish `ASR_fa_v1` set; the
Common Voice numbers (23–30%) are on a harder public benchmark. Benchmark on your own lecture audio
before trusting any of them.

Practical caveat for religious/Quranic lecture audio: all of these are fine-tuned on general Persian
speech. Classical Arabic Quranic recitation embedded in Persian lectures is out of distribution for
every model here, including the commercial ones.

---

## 6. Accessibility and sanctions

This matters concretely for this project and cuts **both** ways.

**International providers blocking Iran.** OpenAI explicitly excludes Iran from its supported-country
list and enforces geographic blocks at **both the IP and the phone-verification level** — a VPN alone
is not sufficient, because an Iranian phone number cannot complete registration. AWS, Azure, Google
Cloud, and Oracle Cloud all restrict Iranian users under OFAC requirements: no account creation, no
card processing, no API access. This is a US legal requirement, not vendor preference. Practical
consequences for the providers above:

- **Hard-blocked / high risk from an Iranian IP or with Iranian billing:** OpenAI, Google Cloud, Azure.
- **Likely blocked, US-incorporated with standard OFAC terms:** ElevenLabs (New York), AssemblyAI,
  Deepgram, Groq, Replicate, Fish Audio.
- **UK-incorporated, still subject to UK/EU Iran sanctions:** Speechmatics.
- Payment is usually the harder wall than the API itself: essentially no international card processor
  will take an Iranian-issued card, and using a foreign card from an Iranian IP risks account
  termination and loss of prepaid credit.

**Iranian providers blocking the outside world.** The mirror problem is real: Fars Ava sells API
access **only to organisations** via a phone call to a Tehran number; Aipa lists no prices and says
"contact us"; every Iranian service quotes toman and accepts only Iranian bank cards (شتاب /
درگاه بانکی), which are unusable from abroad. Several of these sites (nevisalive.com, store.farsava.com)
were unreachable or returned 504 from an EU-based fetch during this research, which is consistent with
inbound geo-filtering or simply fragile hosting.

**Practical read:** if you are operating from outside Iran, the international providers are reachable
and the Iranian ones are effectively not. If you are operating from inside Iran, it's the reverse, and
the self-hosted `faster-whisper` + `nezamisafa/whisper-persian-v4` path is the only one that sidesteps
both problems entirely.

---

## 7. Recommendation for this repo

Current state: `transcribe.py` calls Fish Audio `transcribe-1` at $0.36/hr, chunks at 3 minutes because
word timestamps freeze past ~239 s, and gets segment-level timestamps with no diarization.

- **Best quality-per-dollar swap: ElevenLabs `scribe_v2`.** 39% cheaper ($0.22 vs $0.36/hr), Persian
  in the 5–10% WER band, word-level timestamps, 32-speaker diarization included, and 3 GB / 10-hour
  limits mean **you can delete the chunking logic entirely** for a 67-minute lecture. That removes the
  timestamp-freezing workaround, the ffmpeg chunk export, and the offset-stitching code.
- **Cheapest acceptable: Groq `whisper-large-v3-turbo`** at $0.04/hr — 9× cheaper than Fish Audio, and
  OpenAI-compatible so the client code is nearly identical. You keep chunking (25 MB free / 100 MB dev)
  and lose diarization, and Whisper's Persian is weaker than Scribe v2's.
- **Cheapest with diarization: Azure batch** at $0.18/hr with diarization included — but it's REST-only,
  needs a GCS-equivalent blob upload flow, and is the most sanctions-exposed of the three.
- **Zero marginal cost:** `faster-whisper` + `nezamisafa/whisper-persian-v4` on a rented or local GPU.
  Worth benchmarking against Scribe v2 on one of your existing lecture files before committing, since
  a domain-tuned Persian model may beat a general multilingual one on this specific content.

For a concrete number on the current corpus: at 67 minutes per lecture, switching from Fish Audio to
Scribe v2 saves $0.156 per file, and switching to Groq turbo saves $0.357 per file.
