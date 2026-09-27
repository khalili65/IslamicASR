#!/usr/bin/env python3
"""Offline RAG bake-off: 2 embedding models × 3 LLMs × 20 questions.

Writes:
  rag/eval/runs/<timestamp>/results.jsonl
  rag/eval/runs/<timestamp>/summary.md
  rag/eval/runs/<timestamp>/answers/<qid>__<embed>__<llm>.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.ask import answer_question
from rag.models_catalog import EMBED_OPTIONS, LLM_OPTIONS, get_embed

EVAL_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = EVAL_DIR / "questions.json"


def slug(s: str) -> str:
    return (
        s.replace("/", "_")
        .replace(" ", "_")
        .replace(":", "_")
        .replace(".", "_")
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--limit-questions", type=int, default=0)
    ap.add_argument(
        "--questions-file",
        type=Path,
        default=QUESTIONS_PATH,
        help="JSON list of questions (default: questions.json)",
    )
    ap.add_argument(
        "--embeds",
        nargs="*",
        default=[e.id for e in EMBED_OPTIONS],
        help="Embedding model ids",
    )
    ap.add_argument(
        "--llms",
        nargs="*",
        default=[m.id for m in LLM_OPTIONS],
        help="LLM model ids",
    )
    ap.add_argument("--sleep", type=float, default=0.5, help="pause between calls")
    args = ap.parse_args()

    questions = json.loads(args.questions_file.read_text(encoding="utf-8"))
    if args.limit_questions:
        questions = questions[: args.limit_questions]

    # Ensure embed stores exist
    for eid in args.embeds:
        emb = get_embed(eid)
        store_path = ROOT / "rag" / "store" / emb.store_key
        if not (store_path / "embeddings.npy").exists():
            raise SystemExit(
                f"Missing store for {eid} at {store_path}. "
                f"Run: python -m rag.reembed_store --embed-model {eid}"
            )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = EVAL_DIR / "runs" / stamp
    ans_dir = out_dir / "answers"
    ans_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.jsonl"

    combos = [(e, m) for e in args.embeds for m in args.llms]
    total = len(questions) * len(combos)
    print(f"Eval {len(questions)} questions × {len(combos)} combos = {total} runs")
    print(f"Output → {out_dir}")

    n_ok = 0
    n_err = 0
    costs = 0.0

    with results_path.open("w", encoding="utf-8") as fout:
        i = 0
        for q in questions:
            for embed_id, llm_id in combos:
                i += 1
                tag = f"{q['id']} | {embed_id.split('/')[-1]} | {llm_id.split('/')[-1]}"
                print(f"[{i}/{total}] {tag} …", flush=True)
                row = {
                    "question_id": q["id"],
                    "level": q["level"],
                    "lang": q["lang"],
                    "question": q["question"],
                    "embed_model": embed_id,
                    "llm_model": llm_id,
                    "ok": False,
                }
                t0 = time.time()
                try:
                    resp = answer_question(
                        q["question"],
                        model_id=llm_id,
                        embed_model_id=embed_id,
                        top_k=args.top_k,
                    )
                    elapsed = time.time() - t0
                    row.update(
                        {
                            "ok": True,
                            "elapsed_sec": round(elapsed, 2),
                            "answer": resp.get("answer"),
                            "answer_fa": resp.get("answer_fa"),
                            "question_fa": resp.get("question_fa"),
                            "used_count": resp.get("used_count"),
                            "retrieved_count": resp.get("retrieved_count"),
                            "retrieved_ids": resp.get("retrieved_ids"),
                            "used_chunk_ids": [c["chunk_id"] for c in resp.get("used_chunks") or []],
                            "used_chunks_brief": [
                                {
                                    "ref": c["ref"],
                                    "chunk_id": c["chunk_id"],
                                    "course": c["course"],
                                    "session_id": c["session_id"],
                                    "t_start": c.get("t_start"),
                                    "score": c.get("score"),
                                    "text_preview": (c.get("text") or "")[:220],
                                }
                                for c in resp.get("used_chunks") or []
                            ],
                            "cost": resp.get("cost"),
                        }
                    )
                    n_ok += 1
                    costs += float((resp.get("cost") or {}).get("total_usd") or 0)

                    md_name = f"{q['id']}__{slug(embed_id)}__{slug(llm_id)}.md"
                    md = ans_dir / md_name
                    md.write_text(
                        "\n".join(
                            [
                                f"# {q['id']} · {q['level']} · {q['lang']}",
                                "",
                                f"**Embed:** `{embed_id}`  ",
                                f"**LLM:** `{llm_id}`  ",
                                f"**Cost:** {(resp.get('cost') or {}).get('label')}  ",
                                f"**Elapsed:** {elapsed:.1f}s  ",
                                f"**Used chunks:** {resp.get('used_count')} / retrieved {resp.get('retrieved_count')}",
                                "",
                                "## Question",
                                q["question"],
                                "",
                                "## Answer",
                                resp.get("answer") or "",
                                "",
                                "## Used passages",
                                *[
                                    f"### [{c['ref']}] {c['course']}/{c['session_id']} · t={c.get('t_start')}\n\n{c.get('text')}\n"
                                    for c in resp.get("used_chunks") or []
                                ],
                            ]
                        ),
                        encoding="utf-8",
                    )
                    print(
                        f"    ok used={resp.get('used_count')} "
                        f"cost={(resp.get('cost') or {}).get('label')} "
                        f"{elapsed:.1f}s",
                        flush=True,
                    )
                except Exception as e:
                    row["ok"] = False
                    row["error"] = str(e)
                    row["traceback"] = traceback.format_exc()[-1500:]
                    row["elapsed_sec"] = round(time.time() - t0, 2)
                    n_err += 1
                    print(f"    ERROR: {e}", flush=True)

                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                fout.flush()
                if args.sleep:
                    time.sleep(args.sleep)

    # Summary markdown
    rows = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_combo: dict[str, list] = {}
    for r in rows:
        key = f"{r['embed_model']} × {r['llm_model']}"
        by_combo.setdefault(key, []).append(r)

    lines = [
        f"# RAG bake-off {stamp}",
        "",
        f"- Questions: {len(questions)} (easy/medium/hard mix)",
        f"- Combos: {len(combos)}",
        f"- OK: {n_ok} · errors: {n_err}",
        f"- Approx total API cost (reported): **${costs:.4f}**",
        "",
        "## Combinations",
        "",
        "| Embed | LLM | OK | Errors | Avg used chunks | Approx $ |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for key, rs in by_combo.items():
        emb, llm = key.split(" × ", 1)
        oks = [r for r in rs if r.get("ok")]
        errs = len(rs) - len(oks)
        avg_used = (
            sum(r.get("used_count") or 0 for r in oks) / len(oks) if oks else 0
        )
        csum = sum(float((r.get("cost") or {}).get("total_usd") or 0) for r in oks)
        lines.append(
            f"| `{emb}` | `{llm}` | {len(oks)} | {errs} | {avg_used:.1f} | ${csum:.4f} |"
        )

    lines += [
        "",
        "## How to compare",
        "",
        "1. Open `answers/` — same question id, different embed/LLM filenames.",
        "2. Check whether used passages are on-topic (retrieval quality → embedding).",
        "3. Check answer faithfulness and citation quality (generation → LLM).",
        "4. Prefer cheaper combo if quality is similar.",
        "",
        f"Raw rows: `{results_path.name}`",
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines))
    print(f"\nDone. Study: {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
