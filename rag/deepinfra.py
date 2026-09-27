from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from openai import OpenAI

from . import config


def client() -> OpenAI:
    if not config.DEEPINFRA_API_KEY:
        raise RuntimeError("DEEPINFRA_API_KEY missing in .env")
    return OpenAI(
        api_key=config.DEEPINFRA_API_KEY,
        base_url=config.DEEPINFRA_BASE_URL,
    )


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    embed_tokens: int = 0

    def add_chat(self, usage) -> None:
        if not usage:
            return
        self.prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self.completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)

    def add_embed(self, usage) -> None:
        if not usage:
            return
        # embeddings report prompt_tokens / total_tokens
        self.embed_tokens += int(
            getattr(usage, "prompt_tokens", None)
            or getattr(usage, "total_tokens", 0)
            or 0
        )

    def merge(self, other: "TokenUsage") -> None:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.embed_tokens += other.embed_tokens


def embed_texts(
    texts: list[str],
    model: str | None = None,
    usage_out: TokenUsage | None = None,
) -> list[list[float]]:
    if not texts:
        return []
    model = model or config.DEEPINFRA_EMBED_MODEL
    c = client()
    out: list[list[float]] = []
    batch = 32
    for i in range(0, len(texts), batch):
        chunk = texts[i : i + batch]
        resp = c.embeddings.create(model=model, input=chunk, encoding_format="float")
        if usage_out is not None:
            usage_out.add_embed(resp.usage)
        ordered = sorted(resp.data, key=lambda d: d.index)
        out.extend([list(d.embedding) for d in ordered])
    return out


def chat(
    messages: list[dict],
    model: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    response_json: bool = False,
    usage_out: TokenUsage | None = None,
    reasoning_effort: str | None = None,
) -> str:
    c = client()
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_json:
        kwargs["response_format"] = {"type": "json_object"}
    # Reasoning models burn tokens on thinking first. Kimi-K2.x often exhausts
    # max_tokens with empty content unless reasoning is disabled for RAG JSON.
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    else:
        ml = model.lower()
        if "kimi-k2" in ml or "kimi-k3" in ml:
            kwargs["reasoning_effort"] = "none"
        elif any(x in ml for x in ("glm-5", "deepseek-r")):
            kwargs["reasoning_effort"] = "low"
    resp = c.chat.completions.create(**kwargs)
    if usage_out is not None:
        usage_out.add_chat(resp.usage)
    content = (resp.choices[0].message.content or "").strip()
    if not content:
        finish = getattr(resp.choices[0], "finish_reason", None)
        raise RuntimeError(
            f"Model returned empty content (finish_reason={finish}). "
            "Reasoning models may need a higher max_tokens — try again or pick GPT-OSS."
        )
    return content


def chat_stream(
    messages: list[dict],
    model: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    usage_out: TokenUsage | None = None,
    reasoning_effort: str | None = None,
):
    """Yield text deltas from a streaming chat completion."""
    c = client()
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    else:
        ml = model.lower()
        if "kimi-k2" in ml or "kimi-k3" in ml:
            kwargs["reasoning_effort"] = "none"
        elif any(x in ml for x in ("glm-5", "deepseek-r")):
            kwargs["reasoning_effort"] = "low"
    try:
        kwargs["stream_options"] = {"include_usage": True}
    except Exception:
        pass
    stream = c.chat.completions.create(**kwargs)
    for event in stream:
        if usage_out is not None and getattr(event, "usage", None):
            usage_out.add_chat(event.usage)
        if not event.choices:
            continue
        delta = event.choices[0].delta
        piece = getattr(delta, "content", None) or ""
        if piece:
            yield piece


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            # Salvage truncated JSON from reasoning models that hit length.
            blob = m.group(0)
            answer = ""
            am = re.search(r'"answer_fa"\s*:\s*"(.*?)(?:"\s*,|"\s*}|$)', blob, re.S)
            if am:
                answer = am.group(1).encode("utf-8").decode("unicode_escape", errors="ignore")
            ids = re.findall(r'"used_chunk_ids"\s*:\s*\[(.*?)\]', blob, re.S)
            used: list[str] = []
            if ids:
                used = re.findall(r'"([^"]+)"', ids[0])
            if not answer and not used:
                raise
            return {"answer_fa": answer, "used_chunk_ids": used}