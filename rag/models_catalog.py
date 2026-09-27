"""Selectable DeepInfra chat + embedding models (USD / 1M tokens)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LlmOption:
    id: str
    label: str
    input_per_mtok: float
    output_per_mtok: float
    note: str = ""

    @property
    def cost_label(self) -> str:
        return f"${self.input_per_mtok:g} in / ${self.output_per_mtok:g} out · per 1M tok"


@dataclass(frozen=True)
class EmbedOption:
    id: str
    label: str
    cost_per_mtok: float
    store_key: str
    # If set, wrap queries with this instruct template (Qwen3-style). Docs stay plain.
    query_instruct: str | None = None


# Prices from DeepInfra public pages (approximate).
LLM_OPTIONS: list[LlmOption] = [
    LlmOption(
        id="openai/gpt-oss-120b",
        label="GPT-OSS 120B",
        input_per_mtok=0.037,
        output_per_mtok=0.17,
        note="ارزان‌تر · سریع برای پرسش‌های روزمره",
    ),
    LlmOption(
        id="zai-org/GLM-5.3",
        label="GLM-5.3",
        input_per_mtok=0.90,
        output_per_mtok=4.00,
        note="قوی در استدلال · گران‌تر",
    ),
    LlmOption(
        id="moonshotai/Kimi-K2.6",
        label="Kimi-K2.6",
        input_per_mtok=0.75,
        output_per_mtok=3.50,
        note="جایگزین K3 · ارزان‌تر و مناسب RAG",
    ),
]

EMBED_OPTIONS: list[EmbedOption] = [
    EmbedOption(
        id="BAAI/bge-m3",
        label="bge-m3",
        cost_per_mtok=0.01,
        store_key="manaee",  # existing index
    ),
    EmbedOption(
        id="Qwen/Qwen3-Embedding-8B",
        label="Qwen3-Embedding-8B",
        cost_per_mtok=0.01,
        store_key="manaee_qwen3_8b",
        query_instruct=(
            "Given a question about Islamic lectures / Quranic tadabbur, "
            "retrieve relevant lecture transcript passages."
        ),
    ),
]

DEFAULT_LLM_ID = LLM_OPTIONS[0].id
DEFAULT_EMBED_ID = EMBED_OPTIONS[0].id
EMBED_MODEL = DEFAULT_EMBED_ID  # backward compat
EMBED_COST_PER_MTOK = 0.01

# Corpus → store + default embedding (Bayat is Qwen-only).
CORPUS_OPTIONS: dict[str, dict] = {
    "manaee": {
        "label": "Manaee / صبوحی",
        "default_embed_id": "BAAI/bge-m3",
        "allowed_embed_ids": ["BAAI/bge-m3", "Qwen/Qwen3-Embedding-8B"],
        "store_overrides": {
            "Qwen/Qwen3-Embedding-8B": "manaee_qwen3_8b",
        },
    },
    "bayat": {
        "label": "Bayat / بیات",
        "default_embed_id": "Qwen/Qwen3-Embedding-8B",
        "allowed_embed_ids": ["Qwen/Qwen3-Embedding-8B"],
        "store_overrides": {
            "Qwen/Qwen3-Embedding-8B": "bayat_qwen3_8b",
        },
        "force_store": "bayat_qwen3_8b",
    },
}
DEFAULT_CORPUS = "manaee"


def get_llm(model_id: str) -> LlmOption:
    for m in LLM_OPTIONS:
        if m.id == model_id:
            return m
    raise KeyError(f"unknown model: {model_id}")


def get_embed(model_id: str) -> EmbedOption:
    for m in EMBED_OPTIONS:
        if m.id == model_id:
            return m
    raise KeyError(f"unknown embed model: {model_id}")


def resolve_corpus_embed(
    corpus: str | None = None,
    embed_model_id: str | None = None,
) -> tuple[str, EmbedOption, str]:
    """Return (corpus_id, embed_option, store_key)."""
    cid = (corpus or DEFAULT_CORPUS).lower().strip()
    if cid not in CORPUS_OPTIONS:
        raise KeyError(f"unknown corpus: {corpus}")
    info = CORPUS_OPTIONS[cid]
    eid = embed_model_id or info["default_embed_id"]
    allowed = info["allowed_embed_ids"]
    if eid not in allowed:
        eid = info["default_embed_id"]
    emb = get_embed(eid)
    store_key = info.get("force_store") or info.get("store_overrides", {}).get(
        eid, emb.store_key
    )
    return cid, emb, store_key


def format_query_for_embed(text: str, embed: EmbedOption) -> str:
    if not embed.query_instruct:
        return text
    return f"Instruct: {embed.query_instruct}\nQuery: {text}"


def estimate_cost_usd(
    *,
    llm: LlmOption,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    embed_tokens: int = 0,
    embed_cost_per_mtok: float | None = None,
) -> dict:
    emb_rate = EMBED_COST_PER_MTOK if embed_cost_per_mtok is None else embed_cost_per_mtok
    llm_in = (prompt_tokens / 1_000_000.0) * llm.input_per_mtok
    llm_out = (completion_tokens / 1_000_000.0) * llm.output_per_mtok
    embed = (embed_tokens / 1_000_000.0) * emb_rate
    total = llm_in + llm_out + embed
    return {
        "currency": "USD",
        "total_usd": round(total, 6),
        "llm_input_usd": round(llm_in, 6),
        "llm_output_usd": round(llm_out, 6),
        "embed_usd": round(embed, 6),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "embed_tokens": embed_tokens,
        "label": f"≈ ${total:.4f}",
        "detail": (
            f"LLM in {prompt_tokens} tok (${llm_in:.4f}) · "
            f"out {completion_tokens} tok (${llm_out:.4f}) · "
            f"embed {embed_tokens} tok (${embed:.4f})"
        ),
    }


def catalog_public() -> list[dict]:
    return [
        {
            "id": m.id,
            "label": m.label,
            "cost_label": m.cost_label,
            "input_per_mtok": m.input_per_mtok,
            "output_per_mtok": m.output_per_mtok,
            "note": m.note,
        }
        for m in LLM_OPTIONS
    ]


def embed_catalog_public(corpus: str | None = None) -> list[dict]:
    cid = (corpus or DEFAULT_CORPUS).lower()
    info = CORPUS_OPTIONS.get(cid, CORPUS_OPTIONS[DEFAULT_CORPUS])
    allowed = set(info["allowed_embed_ids"])
    out = []
    for m in EMBED_OPTIONS:
        if m.id not in allowed:
            continue
        store_key = info.get("force_store") or info.get("store_overrides", {}).get(
            m.id, m.store_key
        )
        out.append(
            {
                "id": m.id,
                "label": m.label,
                "cost_per_mtok": m.cost_per_mtok,
                "store_key": store_key,
            }
        )
    return out


def corpus_catalog_public() -> list[dict]:
    return [
        {
            "id": cid,
            "label": info["label"],
            "default_embed": info["default_embed_id"],
        }
        for cid, info in CORPUS_OPTIONS.items()
    ]
