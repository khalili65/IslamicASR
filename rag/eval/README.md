# Offline RAG bake-off

## Quick bake-off (recommended)

3 **hard** Term1 questions × 2 embeds × 3 LLMs = **18 runs**:

```bash
.venv/bin/python -m rag.eval.run_bakeoff \
  --questions-file rag/eval/questions_quick.json
```

Latest study write-up: `rag/eval/runs/20260923_065001/STUDY.md`

## Full question bank (`questions.json`)

20 questions scoped mostly to **Manaee Term1 sessions 001–040**:

| Level | Count | Coverage |
| --- | ---: | --- |
| easy | 3 | intro + Inshiqaq + Qadr |
| medium | 7 | Inshiqaq, Buruj, Tariq, A‘la, Fajr, Shams, Layl |
| hard | 10 | mabani, Buruj, A‘la, Ghashiyah, Balad, Shams, Duha/Sharh, Tin, ‘Alaq, Qadr/Bayyinah |

## Full run

```bash
.venv/bin/python -m rag.eval.run_bakeoff
```

Results land in `rag/eval/runs/<timestamp>/` (`summary.md`, `STUDY.md` when written, `results.jsonl`, `answers/`).
