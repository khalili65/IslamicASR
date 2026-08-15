"""Pluggable ASR backends.

Every provider is talked to over plain HTTP (except Fish, which uses its SDK)
so that adding a new one only means adding a class here, and so the toolkit
does not need a different vendor SDK per provider.

To add a provider: subclass `Provider`, fill in the metadata class attributes,
implement `transcribe_chunk`, and add it to `REGISTRY` at the bottom.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

DEFAULT_TIMEOUT = 600


@dataclass
class Segment:
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


@dataclass
class ChunkResult:
    text: str
    segments: List[Segment] = field(default_factory=list)
    raw: Any = None


class ProviderError(RuntimeError):
    pass


class Provider:
    """Base class. Subclasses describe one ASR service."""

    name = "base"
    label = "Base"
    default_model = ""
    env_var = ""
    extra_env: List[str] = []

    # USD per audio hour for `default_model`, verified 2026-08-13.
    # None means "not a simple per-hour rate" (see notes).
    price_per_hour_usd: Optional[float] = None
    # Per-model overrides, so --model also corrects the cost estimate.
    model_prices: Dict[str, float] = {}
    # "yes" = officially documented, "partial" = works but not advertised,
    # "no" = unsupported, "unverified" = could not confirm.
    farsi_support = "unverified"
    signup_url = ""
    notes = ""

    # Request limits. 0 means "no limit we need to work around".
    max_chunk_seconds: float = 0
    max_upload_bytes: int = 0

    def __init__(self, model: Optional[str] = None, language: Optional[str] = "fa",
                 diarize: bool = False, price_per_hour: Optional[float] = None,
                 **options: Any) -> None:
        self.model = model or self.default_model
        self.language = language
        self.diarize = diarize
        self.options = options
        self.api_key = os.environ.get(self.env_var, "") if self.env_var else ""
        # Rates differ per plan, so allow callers to substitute their own.
        self.price_per_hour = (
            price_per_hour if price_per_hour is not None
            else self.model_prices.get(self.model, self.price_per_hour_usd)
        )

    # -- helpers ---------------------------------------------------------
    def require_key(self) -> str:
        if self.env_var and not self.api_key:
            raise ProviderError(
                f"Missing API key: set {self.env_var} in your .env file. "
                f"Get one at {self.signup_url}"
            )
        return self.api_key

    def language_code(self) -> Optional[str]:
        """Providers use different codes for Persian; override as needed."""
        return self.language

    def estimate_cost(self, seconds: float) -> Optional[float]:
        if self.price_per_hour is None:
            return None
        return seconds / 3600.0 * self.price_per_hour

    def _post(self, url: str, *, retries: int = 4, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        last: Optional[Exception] = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.post(url, **kwargs)
            except requests.RequestException as exc:
                last = exc
                if attempt == retries:
                    raise ProviderError(f"{self.label}: network error: {exc}") from exc
                time.sleep(min(2 ** attempt, 20))
                continue

            if resp.status_code < 400:
                return resp
            if resp.status_code in (408, 429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(min(2 ** attempt, 30))
                continue
            raise ProviderError(
                f"{self.label}: HTTP {resp.status_code}: {resp.text[:500]}"
            )
        raise ProviderError(f"{self.label}: request failed: {last}")

    # -- interface -------------------------------------------------------
    def transcribe_chunk(self, audio_path: Path) -> ChunkResult:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Fish Audio (the backend this repo started with)
# ---------------------------------------------------------------------------
class FishProvider(Provider):
    name = "fish"
    label = "Fish Audio (transcribe-1)"
    default_model = "transcribe-1"
    env_var = "FISH_API_KEY"
    price_per_hour_usd = 0.36
    farsi_support = "undocumented"
    signup_url = "https://fish.audio/developers/"
    notes = (
        "Fish publishes no supported-language list, so Persian is auto-detected "
        "rather than guaranteed. Segment timestamps only, no diarization. Word "
        "timestamps freeze around ~4 min per request and decoded PCM must stay "
        "under ~20 MB, hence the 3-minute chunks."
    )
    max_chunk_seconds = 180

    def transcribe_chunk(self, audio_path: Path) -> ChunkResult:
        key = self.require_key()
        try:
            from fishaudio import FishAudio
        except ImportError as exc:
            raise ProviderError(
                "fish-audio-sdk is not installed: pip install 'fish-audio-sdk>=1.0.0'"
            ) from exc

        client = FishAudio(api_key=key)
        kwargs: Dict[str, Any] = {
            "audio": audio_path.read_bytes(),
            "include_timestamps": True,
        }
        if self.language_code():
            kwargs["language"] = self.language_code()

        result = client.asr.transcribe(**kwargs)
        segments = []
        for seg in getattr(result, "segments", None) or []:
            start = float(getattr(seg, "start", 0) or 0)
            end = float(getattr(seg, "end", 0) or 0)
            # Fish sometimes reports milliseconds.
            if start > 10_000 or end > 10_000:
                start, end = start / 1000.0, end / 1000.0
            segments.append(Segment(start, end, getattr(seg, "text", "") or ""))
        return ChunkResult(text=(getattr(result, "text", "") or "").strip(),
                           segments=segments, raw=None)


# ---------------------------------------------------------------------------
# ElevenLabs Scribe
# ---------------------------------------------------------------------------
class ElevenLabsProvider(Provider):
    name = "elevenlabs"
    label = "ElevenLabs Scribe"
    default_model = "scribe_v2"
    env_var = "ELEVENLABS_API_KEY"
    price_per_hour_usd = 0.22
    model_prices = {"scribe_v2": 0.22, "scribe_v2_realtime": 0.39}
    farsi_support = "yes"
    signup_url = "https://elevenlabs.io/app/developers"
    notes = (
        "Persian is in the documented 5-10% WER band, the strongest Persian "
        "claim of any international vendor. Word timestamps and up to 32-speaker "
        "diarization are in the base rate. 3 GB / 10 h per request means no "
        "chunking. scribe_v1 is deprecated."
    )
    # 3 GB / 10 hours per request, so a whole lecture goes in one call.
    max_upload_bytes = 3_000_000_000

    ENDPOINT = "https://api.elevenlabs.io/v1/speech-to-text"

    def language_code(self) -> Optional[str]:
        # ElevenLabs expects ISO-639-3 / BCP-47; Persian is "fas".
        if self.language in ("fa", "fas", "per"):
            return "fas"
        return self.language

    def transcribe_chunk(self, audio_path: Path) -> ChunkResult:
        key = self.require_key()
        data: Dict[str, Any] = {
            "model_id": self.model,
            "timestamps_granularity": "word",
            "diarize": "true" if self.diarize else "false",
        }
        if self.language_code():
            data["language_code"] = self.language_code()

        with audio_path.open("rb") as fh:
            resp = self._post(
                self.ENDPOINT,
                headers={"xi-api-key": key},
                data=data,
                files={"file": (audio_path.name, fh, "audio/mpeg")},
            )
        payload = resp.json()
        segments = []
        for word in payload.get("words") or []:
            if word.get("type") not in (None, "word"):
                continue
            segments.append(Segment(
                start=float(word.get("start") or 0),
                end=float(word.get("end") or 0),
                text=word.get("text") or "",
                speaker=word.get("speaker_id"),
            ))
        return ChunkResult(text=(payload.get("text") or "").strip(),
                           segments=segments, raw=payload)


# ---------------------------------------------------------------------------
# OpenAI-compatible endpoints (OpenAI, Groq, and anything mirroring the API)
# ---------------------------------------------------------------------------
class OpenAICompatibleProvider(Provider):
    endpoint = ""
    supports_verbose_json = True

    def language_code(self) -> Optional[str]:
        return "fa" if self.language in ("fa", "fas", "per") else self.language

    def transcribe_chunk(self, audio_path: Path) -> ChunkResult:
        key = self.require_key()
        verbose = self.supports_verbose_json and not self.model.startswith("gpt-4o")
        data: Dict[str, Any] = {
            "model": self.model,
            "response_format": "verbose_json" if verbose else "json",
        }
        if self.language_code():
            data["language"] = self.language_code()
        if verbose:
            data["timestamp_granularities[]"] = "segment"

        with audio_path.open("rb") as fh:
            resp = self._post(
                self.endpoint,
                headers={"Authorization": f"Bearer {key}"},
                data=data,
                files={"file": (audio_path.name, fh, "audio/mpeg")},
            )
        payload = resp.json()
        segments = [
            Segment(float(s.get("start") or 0), float(s.get("end") or 0),
                    (s.get("text") or "").strip())
            for s in payload.get("segments") or []
        ]
        return ChunkResult(text=(payload.get("text") or "").strip(),
                           segments=segments, raw=payload)


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    label = "OpenAI gpt-transcribe"
    default_model = "gpt-transcribe"
    env_var = "OPENAI_API_KEY"
    price_per_hour_usd = 0.27
    model_prices = {
        "gpt-transcribe": 0.27,
        "gpt-4o-transcribe": 0.36,
        "gpt-4o-mini-transcribe": 0.18,
    }
    farsi_support = "yes"
    signup_url = "https://platform.openai.com/api-keys"
    notes = (
        "25 MB per request. The gpt-* models return NO timestamps at all; "
        "only --model whisper-1 does, and whisper-1 is no longer on the public "
        "price list so its cost estimate here is a guess."
    )
    endpoint = "https://api.openai.com/v1/audio/transcriptions"
    max_upload_bytes = 25 * 1024 * 1024
    max_chunk_seconds = 900


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    label = "Groq Whisper large-v3"
    default_model = "whisper-large-v3"
    env_var = "GROQ_API_KEY"
    price_per_hour_usd = 0.111
    model_prices = {"whisper-large-v3": 0.111, "whisper-large-v3-turbo": 0.04}
    farsi_support = "yes"
    signup_url = "https://console.groq.com/keys"
    notes = (
        "Cheapest hosted Whisper by a wide margin; --model whisper-large-v3-turbo "
        "is $0.04/hr. No diarization. Minimum 10 s billed per request."
    )
    endpoint = "https://api.groq.com/openai/v1/audio/transcriptions"
    max_upload_bytes = 25 * 1024 * 1024
    max_chunk_seconds = 900


# ---------------------------------------------------------------------------
# Deepgram
# ---------------------------------------------------------------------------
class DeepgramProvider(Provider):
    name = "deepgram"
    label = "Deepgram Nova"
    default_model = "nova-3"
    env_var = "DEEPGRAM_API_KEY"
    price_per_hour_usd = 0.258
    model_prices = {"nova-3": 0.258, "whisper-large": 0.288}
    farsi_support = "yes"
    signup_url = "https://console.deepgram.com/signup"
    notes = (
        "Persian (fa) is supported on nova-3 but NOT on nova-2. Diarization is "
        "an extra $0.12/hr. $200 free credit."
    )

    ENDPOINT = "https://api.deepgram.com/v1/listen"

    def language_code(self) -> Optional[str]:
        return "fa" if self.language in ("fa", "fas", "per") else self.language

    def transcribe_chunk(self, audio_path: Path) -> ChunkResult:
        key = self.require_key()
        params = {"model": self.model, "smart_format": "true", "punctuate": "true"}
        if self.language_code():
            params["language"] = self.language_code()
        if self.diarize:
            params["diarize"] = "true"

        resp = self._post(
            self.ENDPOINT,
            headers={"Authorization": f"Token {key}", "Content-Type": "audio/mpeg"},
            params=params,
            data=audio_path.read_bytes(),
        )
        payload = resp.json()
        channels = payload.get("results", {}).get("channels") or []
        alt = (channels[0].get("alternatives") or [{}])[0] if channels else {}
        segments = [
            Segment(float(w.get("start") or 0), float(w.get("end") or 0),
                    w.get("punctuated_word") or w.get("word") or "",
                    str(w.get("speaker")) if w.get("speaker") is not None else None)
            for w in alt.get("words") or []
        ]
        return ChunkResult(text=(alt.get("transcript") or "").strip(),
                           segments=segments, raw=payload)


# ---------------------------------------------------------------------------
# AssemblyAI (async: upload, then poll)
# ---------------------------------------------------------------------------
class AssemblyAIProvider(Provider):
    name = "assemblyai"
    label = "AssemblyAI Universal-2"
    default_model = "universal-2"
    env_var = "ASSEMBLYAI_API_KEY"
    price_per_hour_usd = 0.15
    model_prices = {"universal-2": 0.15, "universal-3-pro": 0.21}
    farsi_support = "yes"
    signup_url = "https://www.assemblyai.com/dashboard/signup"
    notes = (
        "Persian works on universal-2 only (it is in their lowest accuracy tier); "
        "universal-3-pro does not support Persian. Async: upload then poll. "
        "$50 free credit, no card."
    )

    BASE = "https://api.assemblyai.com/v2"

    def language_code(self) -> Optional[str]:
        return "fa" if self.language in ("fa", "fas", "per") else self.language

    def transcribe_chunk(self, audio_path: Path) -> ChunkResult:
        key = self.require_key()
        headers = {"authorization": key}

        upload = self._post(f"{self.BASE}/upload", headers=headers,
                            data=audio_path.read_bytes())
        body: Dict[str, Any] = {
            "audio_url": upload.json()["upload_url"],
            "speech_model": self.model,
        }
        if self.language_code():
            body["language_code"] = self.language_code()
        if self.diarize:
            body["speaker_labels"] = True

        job = self._post(f"{self.BASE}/transcript", headers=headers, json=body).json()
        job_id = job["id"]

        while True:
            time.sleep(3)
            status = requests.get(f"{self.BASE}/transcript/{job_id}", headers=headers,
                                  timeout=DEFAULT_TIMEOUT).json()
            state = status.get("status")
            if state == "completed":
                break
            if state == "error":
                raise ProviderError(f"AssemblyAI: {status.get('error')}")

        segments = [
            Segment(float(w.get("start") or 0) / 1000.0, float(w.get("end") or 0) / 1000.0,
                    w.get("text") or "",
                    str(w.get("speaker")) if w.get("speaker") is not None else None)
            for w in status.get("words") or []
        ]
        return ChunkResult(text=(status.get("text") or "").strip(),
                           segments=segments, raw=status)


# ---------------------------------------------------------------------------
# Azure AI Speech - fast (synchronous) transcription
# ---------------------------------------------------------------------------
class AzureProvider(Provider):
    name = "azure"
    label = "Azure AI Speech (fast transcription)"
    default_model = "fast-transcription"
    env_var = "AZURE_SPEECH_KEY"
    extra_env = ["AZURE_SPEECH_REGION"]
    price_per_hour_usd = 0.36
    farsi_support = "yes"
    signup_url = "https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices"
    notes = (
        "Needs AZURE_SPEECH_REGION too (e.g. westeurope). Persian is fa-IR, "
        "diarization included. This uses the synchronous fast-transcription "
        "endpoint at $0.36/hr; Azure's async batch API is cheaper at $0.18/hr "
        "but needs a blob-upload flow."
    )

    API_VERSION = "2024-11-15"

    def language_code(self) -> Optional[str]:
        return "fa-IR" if self.language in ("fa", "fas", "per") else self.language

    def transcribe_chunk(self, audio_path: Path) -> ChunkResult:
        key = self.require_key()
        region = os.environ.get("AZURE_SPEECH_REGION", "")
        if not region:
            raise ProviderError("Set AZURE_SPEECH_REGION (e.g. westeurope) in your .env")

        url = (f"https://{region}.api.cognitive.microsoft.com/speechtotext/"
               f"transcriptions:transcribe?api-version={self.API_VERSION}")
        definition: Dict[str, Any] = {"locales": [self.language_code()]}
        if self.diarize:
            definition["diarization"] = {"maxSpeakers": 4, "enabled": True}

        with audio_path.open("rb") as fh:
            resp = self._post(
                url,
                headers={"Ocp-Apim-Subscription-Key": key},
                files={
                    "audio": (audio_path.name, fh, "audio/mpeg"),
                    "definition": (None, json.dumps(definition), "application/json"),
                },
            )
        payload = resp.json()
        segments = [
            Segment(float(p.get("offsetMilliseconds") or 0) / 1000.0,
                    (float(p.get("offsetMilliseconds") or 0)
                     + float(p.get("durationMilliseconds") or 0)) / 1000.0,
                    p.get("text") or "",
                    str(p.get("speaker")) if p.get("speaker") is not None else None)
            for p in payload.get("phrases") or []
        ]
        combined = payload.get("combinedPhrases") or []
        text = combined[0].get("text", "") if combined else " ".join(s.text for s in segments)
        return ChunkResult(text=text.strip(), segments=segments, raw=payload)


# ---------------------------------------------------------------------------
# Google Cloud Speech-to-Text v2 (Chirp)
# ---------------------------------------------------------------------------
class GoogleProvider(Provider):
    name = "google"
    label = "Google Speech-to-Text v2 (Chirp)"
    default_model = "chirp_2"
    env_var = "GOOGLE_ACCESS_TOKEN"
    extra_env = ["GOOGLE_PROJECT_ID", "GOOGLE_STT_LOCATION"]
    price_per_hour_usd = 0.96
    farsi_support = "yes"
    signup_url = "https://console.cloud.google.com/apis/library/speech.googleapis.com"
    notes = (
        "Set GOOGLE_PROJECT_ID and get a token with "
        "`gcloud auth print-access-token`. Persian is fa-IR on chirp/chirp_2 in "
        "us-central1, europe-west4, asia-southeast1; no diarization for Persian. "
        "This uses synchronous recognize at $0.96/hr and is capped at ~1 min per "
        "call, hence the chunking; Google's async batch API costs $0.18/hr but "
        "requires uploading to a GCS bucket first."
    )
    max_chunk_seconds = 55

    def language_code(self) -> Optional[str]:
        return "fa-IR" if self.language in ("fa", "fas", "per") else self.language

    def transcribe_chunk(self, audio_path: Path) -> ChunkResult:
        import base64

        token = self.require_key()
        project = os.environ.get("GOOGLE_PROJECT_ID", "")
        if not project:
            raise ProviderError("Set GOOGLE_PROJECT_ID in your .env")
        location = os.environ.get("GOOGLE_STT_LOCATION", "us-central1")

        host = ("speech.googleapis.com" if location == "global"
                else f"{location}-speech.googleapis.com")
        url = (f"https://{host}/v2/projects/{project}/locations/{location}"
               f"/recognizers/_:recognize")

        body = {
            "config": {
                "autoDecodingConfig": {},
                "model": self.model,
                "languageCodes": [self.language_code()],
                "features": {"enableWordTimeOffsets": True},
            },
            "content": base64.b64encode(audio_path.read_bytes()).decode(),
        }
        resp = self._post(url, headers={"Authorization": f"Bearer {token}"}, json=body)
        payload = resp.json()

        texts, segments = [], []
        for result in payload.get("results") or []:
            alts = result.get("alternatives") or []
            if not alts:
                continue
            texts.append(alts[0].get("transcript", ""))
            for word in alts[0].get("words") or []:
                segments.append(Segment(
                    _gduration(word.get("startOffset")),
                    _gduration(word.get("endOffset")),
                    word.get("word") or "",
                ))
        return ChunkResult(text=" ".join(texts).strip(), segments=segments, raw=payload)


def _gduration(value: Optional[str]) -> float:
    """Google returns durations as strings like '1.500s'."""
    if not value:
        return 0.0
    try:
        return float(str(value).rstrip("s"))
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Speechmatics (async: create job, then poll)
# ---------------------------------------------------------------------------
class SpeechmaticsProvider(Provider):
    name = "speechmatics"
    label = "Speechmatics"
    default_model = "standard"
    env_var = "SPEECHMATICS_API_KEY"
    price_per_hour_usd = 0.45
    model_prices = {"standard": 0.45, "enhanced": 0.75}
    farsi_support = "yes"
    signup_url = "https://portal.speechmatics.com/signup"
    notes = (
        "Async batch API; the model name is the operating point "
        "('standard' or 'enhanced'). $100 free credit, and 33% off if you opt "
        "into model training."
    )

    BASE = "https://asr.api.speechmatics.com/v2"

    def language_code(self) -> Optional[str]:
        return "fa" if self.language in ("fa", "fas", "per") else self.language

    def transcribe_chunk(self, audio_path: Path) -> ChunkResult:
        key = self.require_key()
        headers = {"Authorization": f"Bearer {key}"}
        config = {
            "type": "transcription",
            "transcription_config": {
                "language": self.language_code(),
                "operating_point": self.model,
                **({"diarization": "speaker"} if self.diarize else {}),
            },
        }
        with audio_path.open("rb") as fh:
            job = self._post(
                f"{self.BASE}/jobs/", headers=headers,
                data={"config": json.dumps(config)},
                files={"data_file": (audio_path.name, fh, "audio/mpeg")},
            ).json()
        job_id = job["id"]

        while True:
            time.sleep(5)
            status = requests.get(f"{self.BASE}/jobs/{job_id}", headers=headers,
                                  timeout=DEFAULT_TIMEOUT).json()
            state = status.get("job", {}).get("status")
            if state == "done":
                break
            if state in ("rejected", "expired"):
                raise ProviderError(f"Speechmatics job {state}: {status}")

        result = requests.get(f"{self.BASE}/jobs/{job_id}/transcript",
                              headers=headers, params={"format": "json-v2"},
                              timeout=DEFAULT_TIMEOUT).json()
        segments, words = [], []
        for item in result.get("results") or []:
            alts = item.get("alternatives") or []
            if not alts:
                continue
            content = alts[0].get("content", "")
            words.append(content)
            segments.append(Segment(float(item.get("start_time") or 0),
                                    float(item.get("end_time") or 0),
                                    content, alts[0].get("speaker")))
        return ChunkResult(text=" ".join(words).strip(), segments=segments, raw=result)


# ---------------------------------------------------------------------------
# Local faster-whisper (free, runs on this machine)
# ---------------------------------------------------------------------------
class LocalWhisperProvider(Provider):
    name = "local-whisper"
    label = "faster-whisper (local, free)"
    default_model = "large-v3"
    env_var = ""
    price_per_hour_usd = 0.0
    farsi_support = "yes"
    signup_url = "https://github.com/SYSTRAN/faster-whisper"
    notes = (
        "Runs offline, no API key, no per-hour cost, no sanctions exposure. "
        "Needs `pip install faster-whisper`; large-v3 is slow on CPU. Persian "
        "fine-tunes such as nezamisafa/whisper-persian-v4 report much better "
        "Persian WER but must be converted to CTranslate2 format first."
    )

    _model_cache: Dict[str, Any] = {}

    def transcribe_chunk(self, audio_path: Path) -> ChunkResult:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ProviderError(
                "faster-whisper is not installed: pip install faster-whisper"
            ) from exc

        if self.model not in self._model_cache:
            compute = self.options.get("compute_type", "int8")
            self._model_cache[self.model] = WhisperModel(
                self.model, device=self.options.get("device", "auto"),
                compute_type=compute,
            )
        model = self._model_cache[self.model]

        lang = "fa" if self.language in ("fa", "fas", "per") else self.language
        seg_iter, _info = model.transcribe(str(audio_path), language=lang,
                                           vad_filter=True, beam_size=5)
        segments, texts = [], []
        for seg in seg_iter:
            texts.append(seg.text.strip())
            segments.append(Segment(float(seg.start), float(seg.end), seg.text.strip()))
        return ChunkResult(text=" ".join(texts).strip(), segments=segments, raw=None)


REGISTRY: Dict[str, type] = {
    cls.name: cls
    for cls in (
        FishProvider,
        ElevenLabsProvider,
        OpenAIProvider,
        GroqProvider,
        AssemblyAIProvider,
        AzureProvider,
        GoogleProvider,
        SpeechmaticsProvider,
        DeepgramProvider,
        LocalWhisperProvider,
    )
}


def get_provider(name: str, **kwargs: Any) -> Provider:
    try:
        cls = REGISTRY[name]
    except KeyError:
        raise ProviderError(
            f"Unknown provider '{name}'. Available: {', '.join(sorted(REGISTRY))}"
        ) from None
    return cls(**kwargs)
