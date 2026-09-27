#!/usr/bin/env python3
"""Parse Texts/کلیات.docx into a text-only lecturer library for the portal.

Writes:
  website-portal/apps/web/public/data/shojai/<book>/…
  website-portal/content/shojai/…
  merges lecturer into public/data/index.json
  public/data/shojai/search-index.json  (token-friendly paragraph corpus)

Usage:
  .venv/bin/python website-portal/scripts/build_text_library.py
  .venv/bin/python website-portal/scripts/build_text_library.py --docx Texts/کلیات.docx
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_ROOT = REPO_ROOT / "website-portal"
OUT_ROOT = SITE_ROOT / "apps" / "web" / "public" / "data"
CONTENT_ROOT = SITE_ROOT / "content"
DEFAULT_DOCX = REPO_ROOT / "Texts" / "کلیات.docx"

_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_END_RE = re.compile(r"^پایان\s+(.+?)\s*$")
_TITLE_NUM_RE = re.compile(r"^(.+?)\s+(\d{1,3})$")
_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# Document order of top-level / tafsir books (after normalisation).
BOOK_ORDER = [
    "اسرار فاطمی",
    "تزکیه",
    "تفسیر سوره حجرات",
    "تفسیر سوره حدید",
    "تفسیر سوره ق",
    "تفسیر سوره مرسلات",
    "تفسیر سوره نازعات",
    "تفسیر سوره نبأ",
    "تفسیر سوره هود",
    "تفسیر سوره انشقاق",
    "تفسیر سوره انفطار",
    "تفسیر سوره تکویر",
    "تفسیر سوره شمس",
    "توحید",
    "شیطان",
    "لیله القدر",
    "معاد",
    "ملائکه",
    "نماز",
]

BOOK_SLUGS = {
    "اسرار فاطمی": "asrar-fatemi",
    "تزکیه": "tazkiye",
    "تفسیر سوره حجرات": "tafsir-hujurat",
    "تفسیر سوره حدید": "tafsir-hadid",
    "تفسیر سوره ق": "tafsir-qaf",
    "تفسیر سوره مرسلات": "tafsir-mursalat",
    "تفسیر سوره نازعات": "tafsir-naziat",
    "تفسیر سوره نبأ": "tafsir-naba",
    "تفسیر سوره هود": "tafsir-hud",
    "تفسیر سوره انشقاق": "tafsir-inshiqaq",
    "تفسیر سوره انفطار": "tafsir-infitar",
    "تفسیر سوره تکویر": "tafsir-takwir",
    "تفسیر سوره شمس": "tafsir-shams",
    "توحید": "tawhid",
    "شیطان": "shaytan",
    "لیله القدر": "laylatul-qadr",
    "معاد": "maad",
    "ملائکه": "malaeka",
    "نماز": "namaz",
}

BOOK_HEADERS = {
    "اسرار فاطمی",
    "تزکیه",
    "تفسیر",
    "توحید",
    "شیطان",
    "لیله القدر",
    "لیلة القدر",
    "معاد",
    "ملائکه",
    "نماز",
}


def to_persian_digits(value: object) -> str:
    return str(value).translate(_PERSIAN_DIGITS)


def write_json(path: Path, payload, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    path.write_text(text, encoding="utf-8")


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return default


def extract_paragraphs(docx_path: Path) -> List[str]:
    with zipfile.ZipFile(docx_path) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    paragraphs: List[str] = []
    for node in root.findall(".//w:p", _NS):
        text = "".join(t.text or "" for t in node.findall(".//w:t", _NS)).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def normalize_book_name(raw: str) -> str:
    name = raw.strip().rstrip("،").strip()
    name = name.replace("لیلة", "لیله")
    name = re.sub(r"^بحث\s+", "", name)
    if name.startswith("تفسیر سوره "):
        return name
    if name.startswith("سوره "):
        return "تفسیر " + name
    # "بحث تفسیر سوره انشقاق" already stripped بحث → تفسیر سوره …
    if name.startswith("تفسیر ") and "سوره" in name:
        return name
    return name


def slug_for_book(book: str) -> str:
    if book not in BOOK_SLUGS:
        raise KeyError("Unknown book %r — add to BOOK_SLUGS" % book)
    return BOOK_SLUGS[book]


def parse_chapter_title(title: str) -> Tuple[str, Optional[int]]:
    cleaned = title.strip().rstrip("،").strip()
    match = _TITLE_NUM_RE.match(cleaned)
    if match:
        return normalize_book_name(match.group(1)), int(match.group(2))
    return normalize_book_name(cleaned), None


def is_skippable_lead(text: str) -> bool:
    if text in BOOK_HEADERS:
        return True
    if text.startswith("تفسیر سوره ") and len(text) < 40:
        return True
    if text.startswith("أَعُوذُ") or text.startswith("اعوذ"):
        return True
    if text.startswith("بِسْمِ") or text.startswith("بسم الله"):
        return True
    return False


def looks_like_subtitle(text: str) -> bool:
    if len(text) > 90 or len(text) < 2:
        return False
    if text.startswith("﴿") or text.startswith("«"):
        return False
    if is_skippable_lead(text):
        return False
    if _END_RE.match(text) or _TITLE_NUM_RE.match(text):
        return False
    return True


def split_chapters(paragraphs: List[str]) -> List[dict]:
    ends: List[Tuple[int, str]] = []
    for index, text in enumerate(paragraphs):
        match = _END_RE.match(text)
        if match:
            ends.append((index, match.group(1).strip()))

    chapters: List[dict] = []
    # Skip alphabetic TOC (ends just before first book header at index 11).
    prev_end = 10

    for end_index, raw_title in ends:
        title = raw_title.strip().rstrip("،").strip()
        book, number = parse_chapter_title(title)

        start_index = None
        for cursor in range(prev_end + 1, end_index):
            if paragraphs[cursor] == title or paragraphs[cursor].rstrip("،") == title:
                start_index = cursor
                break
        if start_index is None:
            start_index = prev_end + 1
            while start_index < end_index and is_skippable_lead(paragraphs[start_index]):
                start_index += 1

        body_start = start_index
        subtitle = None
        if paragraphs[start_index] == title or paragraphs[start_index].rstrip("،") == title:
            body_start = start_index + 1
        while body_start < end_index and is_skippable_lead(paragraphs[body_start]):
            body_start += 1
        if body_start < end_index and looks_like_subtitle(paragraphs[body_start]):
            subtitle = paragraphs[body_start]
            body_start += 1

        body = [p for p in paragraphs[body_start:end_index] if p.strip()]
        chapters.append(
            {
                "title": title,
                "book": book,
                "number": number,
                "subtitle": subtitle,
                "paragraphs": body,
            }
        )
        prev_end = end_index

    return chapters


def chapter_session_id(number: Optional[int], fallback_index: int) -> str:
    if number is not None:
        return "%03d" % number
    return "%03d" % fallback_index


def ensure_unique_session_ids(chapters: List[dict]) -> None:
    """Assign session ids; disambiguate collisions (e.g. missing numbers)."""
    used: Dict[str, set] = defaultdict(set)
    for chapter in chapters:
        book = chapter["book"]
        base = chapter_session_id(chapter["number"], len(used[book]) + 1)
        session_id = base
        suffix = 1
        while session_id in used[book]:
            session_id = "%s-%d" % (base, suffix)
            suffix += 1
        used[book].add(session_id)
        chapter["session_id"] = session_id


def seed_lecturer_meta() -> dict:
    path = CONTENT_ROOT / "shojai" / "lecturer.json"
    default = {
        "slug": "shojai",
        "name": "آیت‌الله محمد شجاعی زنجانی",
        "title": "رضوان‌الله تعالی علیه · معارف اهل‌بیت",
        "bio": "مجموعه‌ای از مباحث معرفتی و تفسیری آیت‌الله محمد شجاعی زنجانی؛ متن پیاده و دسته‌بندی‌شده در قالب کتاب‌ها و فصول، بدون صوت.",
        "avatar": "",
        "links": [],
        "format": "text",
    }
    existing = read_json(path, None)
    if existing:
        # Keep hand-edited fields; ensure format flag.
        existing.setdefault("format", "text")
        existing.setdefault("slug", "shojai")
        write_json(path, existing)
        return existing
    write_json(path, default)
    return default


def seed_course_meta(book: str, slug: str, description: str) -> dict:
    path = CONTENT_ROOT / "shojai" / slug / "course.json"
    default = {
        "slug": slug,
        "title": book,
        "description": description,
        "cover": "",
        "hidden": [],
        "format": "text",
        "titles": {},
    }
    existing = read_json(path, None)
    if existing:
        existing.setdefault("format", "text")
        existing.setdefault("slug", slug)
        existing.setdefault("title", book)
        write_json(path, existing)
        return existing
    write_json(path, default)
    return default


def write_chapter_files(
    out_dir: Path,
    lecturer_slug: str,
    course_slug: str,
    chapters: List[dict],
    course_title: str,
) -> List[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Drop previous session artifacts for this course.
    for path in out_dir.glob("*"):
        if path.name in {"course.json"}:
            continue
        if path.suffix in {".json", ".txt", ".md"} or path.name.endswith(".raw.txt"):
            path.unlink()

    sessions_meta: List[dict] = []
    sorted_chapters = sorted(
        chapters,
        key=lambda c: (
            c["number"] is None,
            c["number"] if c["number"] is not None else 10_000,
            c["session_id"],
        ),
    )

    for index, chapter in enumerate(sorted_chapters, start=1):
        session_id = chapter["session_id"]
        title_override = None
        # course.json titles map can override
        prev = None
        nxt = None
        if index > 1:
            prev = sorted_chapters[index - 2]["session_id"]
        if index < len(sorted_chapters):
            nxt = sorted_chapters[index]["session_id"]

        display_title = chapter["title"]
        if chapter["number"] is not None:
            display_title = "%s — فصل %s" % (
                course_title,
                to_persian_digits(chapter["number"]),
            )
        else:
            display_title = "%s — %s" % (course_title, chapter["title"])

        topic = chapter["subtitle"]
        paragraphs = chapter["paragraphs"]
        body = "\n\n".join(paragraphs)
        raw_path = out_dir / ("%s.raw.txt" % session_id)
        raw_path.write_text(body + "\n", encoding="utf-8")

        # Also ship a light markdown for the reader (preserves paragraphs).
        md_lines = ["# %s" % display_title, ""]
        if topic:
            md_lines.extend(["**موضوع:** %s" % topic, ""])
        md_lines.extend(paragraphs)
        (out_dir / ("%s.corrected.md" % session_id)).write_text(
            "\n\n".join(md_lines) + "\n", encoding="utf-8"
        )

        payload = {
            "id": session_id,
            "index": chapter["number"] if chapter["number"] is not None else index,
            "lecturer": lecturer_slug,
            "course": course_slug,
            "title": display_title,
            "topic": topic,
            "summary": None,
            "hasTranscript": False,
            "audio": None,
            "subtitles": None,
            "chapters": [],
            "recordedAt": None,
            "sourceName": "کلیات.docx",
            "hasFullText": True,
            "hasLegacyText": False,
            "hasSummary": False,
            "hasBook": False,
            "hasRawTranscript": True,
            "subtitleSource": "raw",
            "textPipeline": "text-library",
            "format": "text",
            "previous": prev,
            "next": nxt,
        }
        write_json(out_dir / ("%s.json" % session_id), payload)

        sessions_meta.append(
            {
                "id": session_id,
                "index": payload["index"],
                "title": display_title,
                "topic": topic,
                "hasTranscript": False,
                "duration": None,
                "durationText": None,
                "recordedAt": None,
                "chapterCount": 0,
                "format": "text",
                "hasFullText": True,
                "paraCount": len(paragraphs),
                "charCount": sum(len(p) for p in paragraphs),
            }
        )

    return sessions_meta


def build_search_index(lecturer_slug: str, books: List[dict]) -> dict:
    """Paragraph corpus for client-side token search (compact keys)."""
    docs = []
    for book in books:
        for chapter in book["chapters"]:
            paragraphs = chapter["paragraphs"]
            chunks: List[str] = []
            buf = ""
            for para in paragraphs:
                if not buf:
                    buf = para
                elif len(buf) + 1 + len(para) <= 420:
                    buf = "%s %s" % (buf, para)
                else:
                    chunks.append(buf)
                    buf = para
            if buf:
                chunks.append(buf)

            docs.append(
                {
                    "c": book["slug"],
                    "ct": book["title"],
                    "s": chapter["session_id"],
                    "t": chapter["display_title"],
                    "k": chapter["subtitle"] or "",
                    "p": chunks,
                }
            )
    return {"v": 1, "l": lecturer_slug, "docs": docs}


def merge_into_site_index(lecturer_entry: dict) -> None:
    index_path = OUT_ROOT / "index.json"
    index = read_json(index_path, None)
    if not index:
        site_config = read_json(SITE_ROOT / "site.config.json", {}) or {}
        index = {
            "version": 1,
            "mode": site_config.get("mode", "portal"),
            "defaultLecturer": site_config.get("defaultLecturer"),
            "brand": site_config.get("brand", {}),
            "theme": site_config.get("theme", {}),
            "features": site_config.get("features", {}),
            "lecturers": [],
        }

    lecturers = [
        item
        for item in index.get("lecturers", [])
        if item.get("slug") != lecturer_entry["slug"]
    ]
    lecturers.append(lecturer_entry)
    # Keep a stable-ish order: existing audio lecturers first, text last.
    index["lecturers"] = lecturers
    write_json(index_path, index)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX)
    parser.add_argument("--out", type=Path, default=OUT_ROOT)
    args = parser.parse_args()

    docx_path = args.docx.expanduser().resolve()
    out_root = args.out.expanduser().resolve()
    if not docx_path.exists():
        sys.exit("DOCX not found: %s" % docx_path)

    print("Reading %s …" % docx_path)
    paragraphs = extract_paragraphs(docx_path)
    print("  %d non-empty paragraphs" % len(paragraphs))

    chapters = split_chapters(paragraphs)
    ensure_unique_session_ids(chapters)
    print("  %d chapters from پایان markers" % len(chapters))

    by_book: Dict[str, List[dict]] = defaultdict(list)
    for chapter in chapters:
        by_book[chapter["book"]].append(chapter)

    unknown = sorted(set(by_book) - set(BOOK_SLUGS))
    if unknown:
        sys.exit("Unknown books (add to BOOK_SLUGS): %s" % ", ".join(unknown))

    lecturer_meta = seed_lecturer_meta()
    lecturer_slug = lecturer_meta["slug"]
    lecturer_out = out_root / lecturer_slug
    lecturer_out.mkdir(parents=True, exist_ok=True)

    course_entries = []
    search_books = []

    ordered_books = [b for b in BOOK_ORDER if b in by_book]
    ordered_books.extend(sorted(set(by_book) - set(ordered_books)))

    for book_title in ordered_books:
        book_chapters = by_book[book_title]
        slug = slug_for_book(book_title)
        description = "%s فصل از مباحث «%s»" % (
            to_persian_digits(len(book_chapters)),
            book_title,
        )
        course_meta = seed_course_meta(book_title, slug, description)

        for chapter in book_chapters:
            if chapter["number"] is not None:
                chapter["display_title"] = "%s — فصل %s" % (
                    book_title,
                    to_persian_digits(chapter["number"]),
                )
            else:
                chapter["display_title"] = "%s — %s" % (book_title, chapter["title"])

        sessions = write_chapter_files(
            lecturer_out / slug,
            lecturer_slug,
            slug,
            book_chapters,
            course_meta.get("title") or book_title,
        )

        course_index = {
            "lecturer": lecturer_slug,
            "slug": slug,
            "title": course_meta.get("title") or book_title,
            "description": course_meta.get("description") or description,
            "cover": course_meta.get("cover") or "",
            "sessionCount": len(sessions),
            "transcribedCount": len(sessions),
            "totalSeconds": 0,
            "totalDurationText": "متن",
            "format": "text",
            "sessions": sessions,
        }
        write_json(lecturer_out / slug / "course.json", course_index)

        course_entries.append(
            {
                "slug": slug,
                "title": course_index["title"],
                "description": course_index["description"],
                "cover": course_index["cover"],
                "sessionCount": course_index["sessionCount"],
                "transcribedCount": course_index["transcribedCount"],
                "totalDurationText": course_index["totalDurationText"],
                "format": "text",
            }
        )
        search_books.append(
            {
                "slug": slug,
                "title": course_index["title"],
                "chapters": book_chapters,
            }
        )
        print(
            "  %-18s %3d chapters → %s/%s"
            % (slug, len(book_chapters), lecturer_slug, slug)
        )

    search_index = build_search_index(lecturer_slug, search_books)
    write_json(lecturer_out / "search-index.json", search_index, compact=True)
    print(
        "  search-index: %d docs, %.1f MB"
        % (
            len(search_index["docs"]),
            (lecturer_out / "search-index.json").stat().st_size / 1e6,
        )
    )

    lecturer_entry = {
        **lecturer_meta,
        "format": "text",
        "courses": course_entries,
    }
    merge_into_site_index(lecturer_entry)
    print("Merged lecturer «%s» into %s" % (lecturer_slug, out_root / "index.json"))
    print(
        "Done: %d books, %d chapters"
        % (len(course_entries), sum(c["sessionCount"] for c in course_entries))
    )

    # Refresh portal-wide search indexes (audio + text).
    try:
        import importlib.util

        search_script = Path(__file__).resolve().parent / "build_search_indexes.py"
        spec = importlib.util.spec_from_file_location(
            "build_search_indexes", search_script
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print("\nRefreshing search indexes…")
            module.main()
    except Exception as exc:  # noqa: BLE001
        print("Search index refresh skipped: %s" % exc)


if __name__ == "__main__":
    main()
