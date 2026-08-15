#!/usr/bin/env python3
"""Turn the Audios/ tree into the JSON the player reads.

Walks `Audios/<Lecturer>/<Course>/<NNN>/`, runs subtitle alignment where a
transcript exists, and writes one payload per session plus the course and
top-level indexes.

Metadata you would want to edit by hand (display names, descriptions, cover
images) lives in `website/content/` and is created with defaults on first run,
then never overwritten.

Usage:
    python3 build_content.py                       # everything under Audios/
    python3 build_content.py --course Audios/Bayat/marefat_nafs
    python3 build_content.py --skip-subtitles      # metadata only, much faster
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from align_subtitles import (                        # noqa: E402
    SessionFiles,
    align_session,
    write_cues_json,
    write_vtt,
    write_words_json,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIO_ROOT = REPO_ROOT / "Audios"
CONTENT_ROOT = REPO_ROOT / "website" / "content"
DEFAULT_OUT = REPO_ROOT / "website" / "apps" / "web" / "public" / "data"
SITE_CONFIG = REPO_ROOT / "website" / "site.config.json"

_H1_RE = re.compile(r"^#\s+(.*)$", re.MULTILINE)
_TOPIC_RE = re.compile(r"^\*\*موضوع:\*\*\s*(.*)$", re.MULTILINE)
_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return default


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def human_size(num_bytes: int) -> str:
    megabytes = num_bytes / (1024 * 1024)
    if megabytes >= 1024:
        return "%.1f GB" % (megabytes / 1024)
    return "%.1f MB" % megabytes


def format_duration(seconds: float) -> str:
    hours, remainder = divmod(int(round(seconds)), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return "%d:%02d:%02d" % (hours, minutes, secs)
    return "%d:%02d" % (minutes, secs)


def probe_duration(path: Path) -> Optional[float]:
    """Audio length via ffprobe, when it is available."""
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from asr.audio import ffmpeg_paths

        _ffmpeg, ffprobe = ffmpeg_paths()
    except Exception:  # noqa: BLE001 - ffprobe is optional
        return None
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, OSError):
        return None


def extract_titles(files: SessionFiles) -> Dict[str, Optional[str]]:
    """Pull a human title and topic line out of the corrected Markdown."""
    title = topic = summary = None
    if files.corrected and files.corrected.exists():
        text = files.corrected.read_text(encoding="utf-8")
        heading = _H1_RE.search(text)
        if heading:
            title = heading.group(1).strip()
        subject = _TOPIC_RE.search(text)
        if subject:
            topic = subject.group(1).strip()

    summary_path = None
    for candidate in files.folder.iterdir():
        if candidate.name.endswith(".summary.md"):
            summary_path = candidate
            break
    if summary_path:
        body = summary_path.read_text(encoding="utf-8")
        match = re.search(r"##\s*[۰-۹\d)\s]*خلاصهٔ? کوتاه\s*\n+(.+?)(?:\n\n|\n---)", body, re.DOTALL)
        if match:
            summary = " ".join(match.group(1).split())
    return {"title": title, "topic": topic, "summary": summary}


def default_lecturer_meta(slug: str) -> dict:
    return {
        "slug": slug,
        "name": slug.replace("_", " ").title(),
        "title": "",
        "bio": "",
        "avatar": "",
        "links": [],
    }


def default_course_meta(slug: str) -> dict:
    return {
        "slug": slug,
        "title": slug.replace("_", " ").title(),
        "description": "",
        "cover": "",
        "hidden": [],
        "titles": {},
    }


def ensure_metadata(lecturer: str, course: str) -> tuple:
    """Load hand-editable metadata, seeding defaults the first time."""
    lecturer_path = CONTENT_ROOT / lecturer / "lecturer.json"
    course_path = CONTENT_ROOT / lecturer / course / "course.json"

    lecturer_meta = read_json(lecturer_path)
    if lecturer_meta is None:
        lecturer_meta = default_lecturer_meta(lecturer)
        write_json(lecturer_path, lecturer_meta)

    course_meta = read_json(course_path)
    if course_meta is None:
        course_meta = default_course_meta(course)
        write_json(course_path, course_meta)

    return lecturer_meta, course_meta


def load_catalog(course_dir: Path) -> Dict[int, dict]:
    """Index catalog.json by session number, when the download log exists."""
    catalog = read_json(course_dir / "catalog.json", {}) or {}
    by_index = {}
    for item in catalog.get("items", []):
        index = item.get("index")
        if index is not None:
            by_index[int(index)] = item
    return by_index


def media_url(
    config: dict, lecturer: str, course: str, session_id: str, filename: str
) -> str:
    base = (config.get("media", {}) or {}).get("baseUrl", "")
    fallback = (config.get("media", {}) or {}).get("localFallback", "/audio")
    root = base.rstrip("/") if base else fallback.rstrip("/")
    from urllib.parse import quote

    # Keep the numbered session folder so the path matches Audios/.../NNN/file.mp3
    return "%s/%s/%s/%s/%s" % (
        root,
        lecturer,
        course,
        session_id,
        quote(filename),
    )


def build_session(
    files: SessionFiles,
    lecturer: str,
    course: str,
    catalog_item: Optional[dict],
    config: dict,
    out_dir: Path,
    skip_subtitles: bool,
) -> Optional[dict]:
    try:
        index = int(files.session_id)
    except ValueError:
        index = 0

    meta = extract_titles(files)
    payload = {
        "id": files.session_id,
        "index": index,
        "lecturer": lecturer,
        "course": course,
        "title": meta["title"] or ("جلسه %s" % str(index).translate(_PERSIAN_DIGITS)),
        "topic": meta["topic"],
        "summary": meta["summary"],
        "hasTranscript": False,
        "audio": None,
        "subtitles": None,
        "chapters": [],
        "recordedAt": (catalog_item or {}).get("date"),
        "sourceName": (catalog_item or {}).get("original_name"),
    }

    if files.audio and files.audio.exists():
        size = files.audio.stat().st_size
        payload["audio"] = {
            "url": media_url(
                config, lecturer, course, files.session_id, files.audio.name
            ),
            "filename": files.audio.name,
            "size": size,
            "display": human_size(size),
            "duration": None,
            "durationText": None,
        }

    if not skip_subtitles and files.is_alignable():
        result = align_session(files)
        if result is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            write_vtt(out_dir / ("%s.vtt" % files.session_id), result["cues"])
            write_cues_json(
                out_dir / ("%s.cues.json" % files.session_id), result, files.session_id
            )
            write_words_json(out_dir / ("%s.words.json" % files.session_id), result)

            payload["hasTranscript"] = True
            payload["subtitles"] = {
                "fa": {
                    "vtt": "%s.vtt" % files.session_id,
                    "cues": "%s.cues.json" % files.session_id,
                    "words": "%s.words.json" % files.session_id,
                }
            }
            payload["chapters"] = [
                {
                    "index": c.index,
                    "title": c.title,
                    "start": round(c.start, 3),
                    "end": round(c.end, 3),
                }
                for c in result["chapters"]
            ]
            payload["alignment"] = {
                "verbatim": round(result["stats"].ratio, 4),
                "driftFraction": round(result["stats"].drift_fraction, 4),
            }
            if payload["audio"]:
                payload["audio"]["duration"] = round(result["duration"], 2)
                payload["audio"]["durationText"] = format_duration(result["duration"])
    elif (out_dir / ("%s.cues.json" % files.session_id)).exists():
        # Reuse previously generated subtitle files without realigning.
        cues_path = out_dir / ("%s.cues.json" % files.session_id)
        try:
            cues_data = read_json(cues_path, {}) or {}
        except Exception:  # noqa: BLE001
            cues_data = {}
        payload["hasTranscript"] = True
        payload["subtitles"] = {
            "fa": {
                "vtt": "%s.vtt" % files.session_id,
                "cues": "%s.cues.json" % files.session_id,
                "words": "%s.words.json" % files.session_id,
            }
        }
        payload["chapters"] = cues_data.get("chapters") or []
        if payload["audio"] and cues_data.get("duration"):
            payload["audio"]["duration"] = cues_data["duration"]
            payload["audio"]["durationText"] = format_duration(cues_data["duration"])
        if cues_data.get("alignment"):
            payload["alignment"] = cues_data["alignment"]

    # Sessions without a transcript still need a length for the course list.
    if payload["audio"] and payload["audio"]["duration"] is None:
        probed = probe_duration(files.audio)
        if probed:
            payload["audio"]["duration"] = round(probed, 2)
            payload["audio"]["durationText"] = format_duration(probed)

    return payload


def build_course(
    course_dir: Path, out_root: Path, config: dict, skip_subtitles: bool
) -> Optional[dict]:
    lecturer = course_dir.parent.name.lower()
    course = course_dir.name.lower()
    lecturer_meta, course_meta = ensure_metadata(lecturer, course)
    catalog = load_catalog(course_dir)
    out_dir = out_root / lecturer / course

    hidden = set(str(h) for h in course_meta.get("hidden", []))
    overrides = course_meta.get("titles", {}) or {}

    sessions: List[dict] = []
    for child in sorted(course_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name in hidden:
            continue
        files = SessionFiles(child)
        if files.audio is None and files.raw is None:
            continue

        try:
            catalog_item = catalog.get(int(child.name))
        except ValueError:
            catalog_item = None

        payload = build_session(
            files, lecturer, course, catalog_item, config, out_dir, skip_subtitles
        )
        if payload is None:
            continue
        if child.name in overrides:
            payload["title"] = overrides[child.name]
        sessions.append(payload)

    if not sessions:
        return None

    # Neighbour links so the player can offer previous/next.
    for position, session in enumerate(sessions):
        session["previous"] = sessions[position - 1]["id"] if position else None
        session["next"] = (
            sessions[position + 1]["id"] if position + 1 < len(sessions) else None
        )
        write_json(out_dir / ("%s.json" % session["id"]), session)

    transcribed = [s for s in sessions if s["hasTranscript"]]
    total_seconds = sum(
        (s["audio"] or {}).get("duration") or 0 for s in sessions
    )

    course_index = {
        "lecturer": lecturer,
        "slug": course,
        "title": course_meta.get("title") or course,
        "description": course_meta.get("description", ""),
        "cover": course_meta.get("cover", ""),
        "sessionCount": len(sessions),
        "transcribedCount": len(transcribed),
        "totalSeconds": round(total_seconds),
        "totalDurationText": format_duration(total_seconds),
        "sessions": [
            {
                "id": s["id"],
                "index": s["index"],
                "title": s["title"],
                "topic": s["topic"],
                "hasTranscript": s["hasTranscript"],
                "duration": (s["audio"] or {}).get("duration"),
                "durationText": (s["audio"] or {}).get("durationText"),
                "recordedAt": s["recordedAt"],
                "chapterCount": len(s["chapters"]),
            }
            for s in sessions
        ],
    }
    write_json(out_dir / "course.json", course_index)

    return {
        "lecturer": lecturer_meta,
        "course": {
            key: course_index[key]
            for key in (
                "slug", "title", "description", "cover",
                "sessionCount", "transcribedCount", "totalDurationText",
            )
        },
    }


def discover_courses(root: Path) -> List[Path]:
    courses = []
    for lecturer_dir in sorted(root.iterdir()):
        if not lecturer_dir.is_dir() or lecturer_dir.name.startswith("."):
            continue
        for course_dir in sorted(lecturer_dir.iterdir()):
            if not course_dir.is_dir() or course_dir.name.startswith("."):
                continue
            # A course folder holds numbered session folders.
            if any(c.is_dir() and c.name.isdigit() for c in course_dir.iterdir()):
                courses.append(course_dir)
    return courses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course", help="Build only this course folder")
    parser.add_argument("--out", default=None, help="Output root (default: public/data)")
    parser.add_argument(
        "--skip-subtitles",
        action="store_true",
        help="Write metadata only, without realigning subtitles",
    )
    args = parser.parse_args()

    config = read_json(SITE_CONFIG, {}) or {}
    out_root = Path(args.out).expanduser() if args.out else DEFAULT_OUT

    if args.course:
        course_dirs = [Path(args.course).expanduser().resolve()]
    else:
        course_dirs = discover_courses(AUDIO_ROOT)

    if not course_dirs:
        sys.exit("No course folders found under %s" % AUDIO_ROOT)

    print("Output: %s\n" % out_root)
    lecturers: Dict[str, dict] = {}

    for course_dir in course_dirs:
        result = build_course(course_dir, out_root, config, args.skip_subtitles)
        if result is None:
            print("  skipped %s (no sessions)" % course_dir.name)
            continue
        lecturer_meta = result["lecturer"]
        entry = lecturers.setdefault(
            lecturer_meta["slug"], {**lecturer_meta, "courses": []}
        )
        entry["courses"].append(result["course"])
        course = result["course"]
        print(
            "  %-10s / %-16s %3d sessions, %3d transcribed, %s"
            % (
                lecturer_meta["slug"],
                course["slug"],
                course["sessionCount"],
                course["transcribedCount"],
                course["totalDurationText"],
            )
        )

    index = {
        "version": 1,
        "mode": config.get("mode", "single-lecturer"),
        "defaultLecturer": config.get("defaultLecturer"),
        "brand": config.get("brand", {}),
        "theme": config.get("theme", {}),
        "features": config.get("features", {}),
        "lecturers": list(lecturers.values()),
    }
    write_json(out_root / "index.json", index)
    print("\nWrote %s" % (out_root / "index.json"))


if __name__ == "__main__":
    main()
