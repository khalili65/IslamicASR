#!/usr/bin/env python3
"""Build per-lecturer compact search indexes for the Bayat website.

Audio courses → cue text (timed ASR / raw pipeline), so hits can seek.
Text library (format=text) → paragraph corpus from search-index.json / chapter files.

Writes:
  website/apps/web/public/data/search/catalog.json
  website/apps/web/public/data/search/<lecturer>.json

Usage:
  .venv/bin/python website/scripts/build_search_indexes.py
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_ROOT = REPO_ROOT / "website"
DATA_ROOT = SITE_ROOT / "apps" / "web" / "public" / "data"
OUT_ROOT = DATA_ROOT / "search"


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return default


def write_json(path: Path, payload, *, compact: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    path.write_text(text, encoding="utf-8")


def discover_courses_on_disk(lecturer_slug: str, listed: List[dict]) -> List[dict]:
    """Merge index.json courses with any course.json folders under the lecturer."""
    by_slug: Dict[str, dict] = {}
    for course in listed:
        slug = course.get("slug")
        if slug:
            by_slug[slug] = dict(course)

    lecturer_dir = DATA_ROOT / lecturer_slug
    if lecturer_dir.is_dir():
        for course_dir in sorted(lecturer_dir.iterdir()):
            if not course_dir.is_dir():
                continue
            course_index = read_json(course_dir / "course.json", {}) or {}
            slug = course_index.get("slug") or course_dir.name
            if slug in by_slug:
                # Prefer live course.json titles/counts when present.
                merged = {**by_slug[slug]}
                for key in (
                    "title",
                    "description",
                    "cover",
                    "sessionCount",
                    "transcribedCount",
                    "totalDurationText",
                    "format",
                ):
                    if course_index.get(key) is not None:
                        merged[key] = course_index[key]
                by_slug[slug] = merged
            else:
                by_slug[slug] = {
                    "slug": slug,
                    "title": course_index.get("title") or slug,
                    "description": course_index.get("description") or "",
                    "cover": course_index.get("cover") or "",
                    "sessionCount": course_index.get("sessionCount") or 0,
                    "transcribedCount": course_index.get("transcribedCount") or 0,
                    "totalDurationText": course_index.get("totalDurationText") or "",
                    "format": course_index.get("format") or "audio",
                }

    return list(by_slug.values())


def build_audio_lecturer(lecturer_slug: str, lecturer_name: str, courses: List[dict]) -> dict:
    docs: List[dict] = []
    for course in courses:
        course_slug = course["slug"]
        course_title = course.get("title") or course_slug
        course_dir = DATA_ROOT / lecturer_slug / course_slug
        course_index = read_json(course_dir / "course.json", {}) or {}
        sessions = course_index.get("sessions") or []
        for session in sessions:
            session_id = session["id"]
            cues_path = course_dir / ("%s.cues.json" % session_id)
            if not cues_path.exists():
                continue
            cues_file = read_json(cues_path, {}) or {}
            chunks = []
            for cue in cues_file.get("cues") or []:
                text = (cue.get("text") or "").strip()
                if not text:
                    continue
                chunks.append(
                    {
                        "i": cue.get("i", len(chunks)),
                        "t": text,
                        "start": cue.get("start"),
                    }
                )
            if not chunks:
                continue
            docs.append(
                {
                    "c": course_slug,
                    "ct": course_title,
                    "s": session_id,
                    "t": session.get("title") or session_id,
                    "k": session.get("topic") or "",
                    "kind": "cue",
                    "p": chunks,
                }
            )
    return {
        "v": 1,
        "l": lecturer_slug,
        "ln": lecturer_name,
        "format": "audio",
        "source": "cues-raw-asr",
        "docs": docs,
    }


def build_text_lecturer(lecturer_slug: str, lecturer_name: str) -> dict:
    """Prefer existing search-index.json; else scan chapter raw.txt."""
    existing = read_json(DATA_ROOT / lecturer_slug / "search-index.json")
    if existing and existing.get("docs"):
        docs = []
        for doc in existing["docs"]:
            paras = doc.get("p") or doc.get("paras") or []
            chunks = []
            for i, para in enumerate(paras):
                if isinstance(para, dict):
                    text = (para.get("t") or para.get("text") or "").strip()
                    if text:
                        chunks.append({"i": para.get("i", i), "t": text})
                else:
                    text = str(para).strip()
                    if text:
                        chunks.append({"i": i, "t": text})
            if not chunks:
                continue
            docs.append(
                {
                    "c": doc.get("c") or doc.get("course"),
                    "ct": doc.get("ct") or doc.get("courseTitle") or "",
                    "s": doc.get("s") or doc.get("sessionId"),
                    "t": doc.get("t") or doc.get("title") or "",
                    "k": doc.get("k") or doc.get("topic") or "",
                    "kind": "text",
                    "p": chunks,
                }
            )
        return {
            "v": 1,
            "l": lecturer_slug,
            "ln": lecturer_name,
            "format": "text",
            "source": "text-library",
            "docs": docs,
        }

    docs = []
    lecturer_dir = DATA_ROOT / lecturer_slug
    if not lecturer_dir.exists():
        return {
            "v": 1,
            "l": lecturer_slug,
            "ln": lecturer_name,
            "format": "text",
            "source": "text-library",
            "docs": [],
        }
    for course_dir in sorted(lecturer_dir.iterdir()):
        if not course_dir.is_dir():
            continue
        course_index = read_json(course_dir / "course.json", {}) or {}
        course_title = course_index.get("title") or course_dir.name
        for session in course_index.get("sessions") or []:
            session_id = session["id"]
            raw = course_dir / ("%s.raw.txt" % session_id)
            if not raw.exists():
                continue
            body = raw.read_text(encoding="utf-8")
            parts = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
            chunks = []
            buf = ""
            for para in parts:
                if not buf:
                    buf = para
                elif len(buf) + 1 + len(para) <= 420:
                    buf = "%s %s" % (buf, para)
                else:
                    chunks.append({"i": len(chunks), "t": buf})
                    buf = para
            if buf:
                chunks.append({"i": len(chunks), "t": buf})
            docs.append(
                {
                    "c": course_dir.name,
                    "ct": course_title,
                    "s": session_id,
                    "t": session.get("title") or session_id,
                    "k": session.get("topic") or "",
                    "kind": "text",
                    "p": chunks,
                }
            )
    return {
        "v": 1,
        "l": lecturer_slug,
        "ln": lecturer_name,
        "format": "text",
        "source": "text-library",
        "docs": docs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA_ROOT)
    args = parser.parse_args()
    data_root = args.data.expanduser().resolve()
    out_root = data_root / "search"

    site = read_json(data_root / "index.json", {}) or {}
    lecturers = site.get("lecturers") or []
    if not lecturers:
        raise SystemExit("No lecturers in %s" % (data_root / "index.json"))

    catalog = {"v": 1, "lecturers": []}
    for lecturer in lecturers:
        slug = lecturer["slug"]
        name = lecturer.get("name") or slug
        courses = discover_courses_on_disk(slug, lecturer.get("courses") or [])
        if lecturer.get("format") == "text":
            payload = build_text_lecturer(slug, name)
        else:
            payload = build_audio_lecturer(slug, name, courses)
        write_json(out_root / ("%s.json" % slug), payload, compact=True)
        size_mb = (out_root / ("%s.json" % slug)).stat().st_size / 1e6
        print(
            "  %-12s %4d docs  %.1f MB  source=%s"
            % (slug, len(payload["docs"]), size_mb, payload.get("source"))
        )
        catalog["lecturers"].append(
            {
                "slug": slug,
                "name": name,
                "format": lecturer.get("format") or "audio",
                "source": payload.get("source"),
                "courses": [
                    {
                        "slug": c["slug"],
                        "title": c.get("title") or c["slug"],
                        "format": c.get("format") or lecturer.get("format") or "audio",
                    }
                    for c in courses
                ],
            }
        )

        # Keep site index course list in sync with discovered folders.
        lecturer["courses"] = [
            {
                "slug": c["slug"],
                "title": c.get("title") or c["slug"],
                "description": c.get("description") or "",
                "cover": c.get("cover") or "",
                "sessionCount": c.get("sessionCount") or 0,
                "transcribedCount": c.get("transcribedCount") or 0,
                "totalDurationText": c.get("totalDurationText") or "",
                **(
                    {"format": c["format"]}
                    if c.get("format") and c.get("format") != "audio"
                    else {}
                ),
            }
            for c in courses
        ]

    write_json(out_root / "catalog.json", catalog, compact=False)
    write_json(data_root / "index.json", site, compact=False)
    print("Wrote %s (%d lecturers)" % (out_root / "catalog.json", len(catalog["lecturers"])))
    print("Updated %s course lists from disk" % (data_root / "index.json"))


if __name__ == "__main__":
    main()
