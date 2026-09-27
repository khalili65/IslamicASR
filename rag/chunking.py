from __future__ import annotations

from dataclasses import asdict, dataclass

from .parse_transcript import WordTime, times_for_span


@dataclass
class Chunk:
    chunk_id: str
    lecturer: str
    course: str  # term1
    session_id: str  # 024
    text: str
    char_start: int
    char_end: int
    t_start: float | None
    t_end: float | None
    source_path: str
    portal_path: str  # /manaee/term1/024/

    def to_meta(self) -> dict:
        return asdict(self)


def chunk_prose(
    prose: str,
    *,
    words: list[WordTime],
    lecturer: str,
    course: str,
    session_id: str,
    source_path: str,
    target_chars: int = 700,
    overlap: int = 120,
) -> list[Chunk]:
    prose = prose.strip()
    if not prose:
        return []
    chunks: list[Chunk] = []
    n = len(prose)
    start = 0
    idx = 0
    while start < n:
        end = min(n, start + target_chars)
        if end < n:
            # Prefer break at whitespace / sentence end
            window = prose[start:end]
            for sep in ("\n", "۔", ".", "؟", "!", " ", "،"):
                pos = window.rfind(sep)
                if pos >= target_chars // 3:
                    end = start + pos + 1
                    break
        text = prose[start:end].strip()
        if len(text) < 40:
            break
        t0, t1 = times_for_span(words, start, end)
        chunk_id = f"{lecturer}:{course}:{session_id}:{idx:04d}"
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                lecturer=lecturer,
                course=course,
                session_id=session_id,
                text=text,
                char_start=start,
                char_end=end,
                t_start=t0,
                t_end=t1,
                source_path=source_path,
                portal_path=f"/{lecturer}/{course}/{session_id}/",
            )
        )
        idx += 1
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks
