from __future__ import annotations

import json
import re
from typing import Any, Iterator

from . import config
from .deepinfra import TokenUsage, chat, chat_stream, embed_texts, extract_json
from .models_catalog import (
    DEFAULT_LLM_ID,
    estimate_cost_usd,
    format_query_for_embed,
    resolve_corpus_embed,
    get_llm,
)
from .store import VectorStore

_stores: dict[str, VectorStore] = {}


def get_store(store_key: str | None = None) -> VectorStore:
    key = store_key or "manaee"
    if key not in _stores:
        path = config.store_dir_for(key)
        s = VectorStore(path)
        if not s.load():
            raise RuntimeError(
                f"RAG store missing at {path}. Run indexer / reembed_store for '{key}'."
            )
        _stores[key] = s
    return _stores[key]


def detect_lang_hint(text: str) -> str:
    arabic = len(re.findall(r"[\u0600-\u06FF]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if arabic >= latin:
        return "fa"
    return "en"


def translate(
    text: str,
    *,
    to_lang: str,
    model: str,
    usage: TokenUsage | None = None,
) -> str:
    if to_lang == "fa":
        system = "You are a precise translator. Translate the user text into clear Persian (Farsi). Return only the translation."
    else:
        system = f"You are a precise translator. Translate the user text into {to_lang}. Return only the translation."
    return chat(
        [{"role": "system", "content": system}, {"role": "user", "content": text}],
        model=model,
        temperature=0.0,
        max_tokens=1024,
        usage_out=usage,
    )


def _build_candidates(hits: list) -> tuple[list[str], dict[str, dict]]:
    cand_lines = []
    by_id: dict[str, dict] = {}
    for meta, score in hits:
        cid = meta["chunk_id"]
        by_id[cid] = {**meta, "score": score}
        cand_lines.append(
            f"[{cid}] (score={score:.3f}, {meta.get('course')}/{meta.get('session_id')}, "
            f"t={meta.get('t_start')}-{meta.get('t_end')})\n{meta['text']}"
        )
    return cand_lines, by_id


def _select_used(
    q_fa: str,
    cand_lines: list[str],
    by_id: dict,
    model: str,
    usage: TokenUsage | None = None,
    *,
    corpus: str = "manaee",
) -> tuple[list[str], str]:
    if corpus == "bayat":
        teacher = "استاد بیات (Bayat lecture corpus)"
    else:
        teacher = "استاد علی صبوحی (Manaee / تدبر در قرآن)"
    system = (
        f"You answer questions using ONLY the provided Persian lecture transcript chunks "
        f"from {teacher}.\n"
        "Return a JSON object with keys:\n"
        '- "answer_fa": string answer in Persian, cite sources inline as [1], [2] matching used_chunk_ids order\n'
        '- "used_chunk_ids": array of chunk_id strings you actually relied on (subset of candidates; omit irrelevant)\n'
        '- "citations": array of {"chunk_id": "...", "quote": "short supporting quote from that chunk"}\n'
        "If nothing is relevant, used_chunk_ids=[] and say you could not find it in the corpus.\n"
        "Keep answer_fa concise (at most ~400 words). Prefer fewer, clearly relevant chunks."
    )
    user = f"سؤال:\n{q_fa}\n\nقطعات نامزد:\n\n" + "\n\n".join(cand_lines)
    # Kimi: disable reasoning + larger budget (see deepinfra.chat defaults).
    # GLM: keep low effort + large budget so thinking does not eat the JSON.
    ml = model.lower()
    if "kimi-k" in ml:
        max_tokens, effort = 16384, "none"
    elif "glm-5" in ml:
        max_tokens, effort = 16384, "low"
    else:
        max_tokens, effort = 8192, None
    raw = chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=model,
        temperature=0.2,
        max_tokens=max_tokens,
        response_json=True,
        usage_out=usage,
        reasoning_effort=effort,
    )
    data = extract_json(raw)
    used_ids = [x for x in (data.get("used_chunk_ids") or []) if x in by_id]
    seen: set[str] = set()
    used_ids = [x for x in used_ids if not (x in seen or seen.add(x))]
    answer_fa = data.get("answer_fa") or ""
    return used_ids, answer_fa


def _pack_used(used_ids: list[str], by_id: dict) -> list[dict]:
    used = []
    for i, cid in enumerate(used_ids, start=1):
        m = by_id[cid]
        used.append(
            {
                "ref": i,
                "chunk_id": cid,
                "text": m["text"],
                "char_start": m["char_start"],
                "char_end": m["char_end"],
                "t_start": m.get("t_start"),
                "t_end": m.get("t_end"),
                "lecturer": m["lecturer"],
                "course": m["course"],
                "session_id": m["session_id"],
                "portal_path": m.get("portal_path"),
                "source_path": m.get("source_path"),
                "score": m.get("score"),
            }
        )
    return used


def _cost_payload(llm, usage: TokenUsage, embed_cost_per_mtok: float) -> dict:
    return estimate_cost_usd(
        llm=llm,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        embed_tokens=usage.embed_tokens,
        embed_cost_per_mtok=embed_cost_per_mtok,
    )


def answer_question(
    question: str,
    *,
    model_id: str | None = None,
    embed_model_id: str | None = None,
    corpus: str | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    model_id = model_id or DEFAULT_LLM_ID
    corpus_id, embed, store_key = resolve_corpus_embed(corpus, embed_model_id)
    llm = get_llm(model_id)
    store = get_store(store_key)
    usage = TokenUsage()

    src_lang = detect_lang_hint(question)
    q_fa = question
    if src_lang != "fa":
        q_fa = translate(question, to_lang="fa", model=llm.id, usage=usage)

    q_for_embed = format_query_for_embed(q_fa, embed)
    q_vec = embed_texts([q_for_embed], model=embed.id, usage_out=usage)[0]
    hits = store.search(q_vec, top_k=top_k)
    cand_lines, by_id = _build_candidates(hits)
    used_ids, answer_fa = _select_used(
        q_fa, cand_lines, by_id, llm.id, usage=usage, corpus=corpus_id
    )
    used = _pack_used(used_ids, by_id)

    answer_out = answer_fa
    if src_lang != "fa" and answer_fa:
        answer_out = translate(answer_fa, to_lang=src_lang, model=llm.id, usage=usage)

    return {
        "question": question,
        "question_fa": q_fa,
        "detected_lang": src_lang,
        "answer": answer_out,
        "answer_fa": answer_fa,
        "corpus": corpus_id,
        "model": {"id": llm.id, "label": llm.label, "cost_label": llm.cost_label},
        "embed_model": {"id": embed.id, "label": embed.label},
        "used_chunks": used,
        "retrieved_count": len(hits),
        "used_count": len(used),
        "retrieved_ids": [m["chunk_id"] for m, _ in hits],
        "cost": _cost_payload(llm, usage, embed.cost_per_mtok),
    }


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def answer_question_stream(
    question: str,
    *,
    model_id: str | None = None,
    embed_model_id: str | None = None,
    corpus: str | None = None,
    top_k: int = 10,
) -> Iterator[str]:
    try:
        model_id = model_id or DEFAULT_LLM_ID
        corpus_id, embed, store_key = resolve_corpus_embed(corpus, embed_model_id)
        llm = get_llm(model_id)
        store = get_store(store_key)
        usage = TokenUsage()

        yield _sse({"type": "status", "stage": "detect", "message": "detecting language"})
        src_lang = detect_lang_hint(question)
        q_fa = question
        if src_lang != "fa":
            yield _sse(
                {
                    "type": "status",
                    "stage": "translate_in",
                    "message": "translating question to Farsi",
                }
            )
            q_fa = translate(question, to_lang="fa", model=llm.id, usage=usage)

        yield _sse({"type": "status", "stage": "retrieve", "message": "searching lectures"})
        q_for_embed = format_query_for_embed(q_fa, embed)
        q_vec = embed_texts([q_for_embed], model=embed.id, usage_out=usage)[0]
        hits = store.search(q_vec, top_k=top_k)
        cand_lines, by_id = _build_candidates(hits)

        yield _sse({"type": "status", "stage": "select", "message": "selecting relevant passages"})
        used_ids, answer_fa = _select_used(
            q_fa, cand_lines, by_id, llm.id, usage=usage, corpus=corpus_id
        )
        used = _pack_used(used_ids, by_id)

        yield _sse(
            {
                "type": "meta",
                "question_fa": q_fa,
                "detected_lang": src_lang,
                "corpus": corpus_id,
                "model": {"id": llm.id, "label": llm.label, "cost_label": llm.cost_label},
                "embed_model": {"id": embed.id, "label": embed.label},
                "used_chunks": used,
                "retrieved_count": len(hits),
                "used_count": len(used),
            }
        )

        yield _sse({"type": "status", "stage": "generate", "message": "writing answer"})

        if src_lang == "fa":
            used_block = "\n\n".join(
                f"[{c['ref']}] {c['text']}" for c in used
            ) or "(no passages)"
            system = (
                "پاسخ را به فارسی روان بنویس. فقط از قطعات داده‌شده استفاده کن. "
                "ارجاع‌ها را به صورت [1] و [2] داخل متن بگذار. فقط متن پاسخ را برگردان."
            )
            user = f"سؤال: {q_fa}\n\nقطعات:\n{used_block}\n\nپاسخ پیش‌نویس (اختیاری):\n{answer_fa}"
            answer_parts: list[str] = []
            for piece in chat_stream(
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                model=llm.id,
                temperature=0.2,
                max_tokens=8192 if "kimi-k" not in llm.id.lower() else 16384,
                usage_out=usage,
                reasoning_effort=("none" if "kimi-k" in llm.id.lower() else "low"),
            ):
                answer_parts.append(piece)
                yield _sse({"type": "token", "text": piece})
            answer_out = "".join(answer_parts).strip() or answer_fa
            answer_fa_final = answer_out
        else:
            if not answer_fa:
                answer_fa = "No relevant passage was found in the corpus."
            system = (
                f"Translate the following Persian answer into {src_lang}. "
                "Keep citation markers like [1] and [2] unchanged. Return only the translation."
            )
            answer_parts = []
            for piece in chat_stream(
                [{"role": "system", "content": system}, {"role": "user", "content": answer_fa}],
                model=llm.id,
                temperature=0.0,
                max_tokens=4096 if "kimi-k" not in llm.id.lower() else 8192,
                usage_out=usage,
                reasoning_effort=("none" if "kimi-k" in llm.id.lower() else "low"),
            ):
                answer_parts.append(piece)
                yield _sse({"type": "token", "text": piece})
            answer_out = "".join(answer_parts).strip() or answer_fa
            answer_fa_final = answer_fa

        if usage.completion_tokens == 0 and answer_out:
            usage.completion_tokens = max(1, len(answer_out) // 3)

        cost = _cost_payload(llm, usage, embed.cost_per_mtok)
        yield _sse(
            {
                "type": "done",
                "answer": answer_out,
                "answer_fa": answer_fa_final,
                "question": question,
                "question_fa": q_fa,
                "detected_lang": src_lang,
                "corpus": corpus_id,
                "model": {"id": llm.id, "label": llm.label, "cost_label": llm.cost_label},
                "embed_model": {"id": embed.id, "label": embed.label},
                "used_chunks": used,
                "retrieved_count": len(hits),
                "used_count": len(used),
                "cost": cost,
            }
        )
    except Exception as e:
        yield _sse({"type": "error", "message": str(e)})
