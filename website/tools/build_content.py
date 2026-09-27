#!/usr/bin/env python3
"""Turn the Audios/ tree into the JSON the player reads.

Walks `Audios/<Lecturer>/<Course>/<NNN>/`, runs subtitle alignment where a
transcript exists, and writes one payload per session plus the course and
top-level indexes.

Metadata you would want to edit by hand (display names, descriptions, cover
images) lives in `website/content/` and is created with defaults on first run,
then never overwritten.

Usage:
    python3 build_content.py                       # site sources.audioDirs (or content/)
    python3 build_content.py --course Audios/Bayat/marefat_nafs
    python3 build_content.py --site-root website-portal --skip-subtitles
    python3 build_content.py --skip-subtitles      # metadata only, much faster

Each site.config.json should set sources.audioDirs so Bayat publish does not
pull Qasemian (and vice versa), e.g. ["Bayat"] or ["Qasemian", "Tadabor_Sobohi/Manaee"].
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from align_subtitles import (                        # noqa: E402
    SessionFiles,
    align_raw_session,
    align_session,
    is_raw_alignable,
    write_cues_json,
    write_vtt,
    write_words_json,
)
from transcript import parse_raw_text                 # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIO_ROOT = REPO_ROOT / "Audios"
# Defaults target the Bayat site under website/. Pass --site-root for
# another site tree (e.g. website-portal).
DEFAULT_SITE_ROOT = REPO_ROOT / "website"
CONTENT_ROOT = DEFAULT_SITE_ROOT / "content"
DEFAULT_OUT = DEFAULT_SITE_ROOT / "apps" / "web" / "public" / "data"
SITE_CONFIG = DEFAULT_SITE_ROOT / "site.config.json"


def configure_site_root(site_root: Path) -> None:
    """Point content / config / default output at a site tree."""
    global CONTENT_ROOT, DEFAULT_OUT, SITE_CONFIG
    site_root = site_root.expanduser().resolve()
    CONTENT_ROOT = site_root / "content"
    DEFAULT_OUT = site_root / "apps" / "web" / "public" / "data"
    SITE_CONFIG = site_root / "site.config.json"

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


_H2_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)


def _read_study_markdown(path: Path) -> Dict[str, Optional[str]]:
    """Title/topic from legacy corrected.md or new-pipeline book.md."""
    text = path.read_text(encoding="utf-8")
    title = topic = None
    heading = _H1_RE.search(text)
    if heading:
        title = heading.group(1).strip()
    else:
        section = _H2_RE.search(text)
        if section:
            title = section.group(1).strip()
    subject = _TOPIC_RE.search(text)
    if subject:
        topic = subject.group(1).strip()
    return {"title": title, "topic": topic}


def find_session_markdown(files: SessionFiles, suffix: str) -> Optional[Path]:
    for candidate in files.folder.iterdir():
        if candidate.is_file() and candidate.name.endswith(suffix):
            return candidate
    return None


def extract_titles(files: SessionFiles) -> Dict[str, Optional[str]]:
    """Pull a human title and topic line from study Markdown (legacy or pipeline)."""
    title = topic = summary = None
    study = None
    if files.corrected and files.corrected.exists():
        study = files.corrected
    else:
        study = find_session_markdown(files, ".book.md")
    if study:
        meta = _read_study_markdown(study)
        title = meta["title"]
        topic = meta["topic"]

    summary_path = find_session_markdown(files, ".summary.md")
    if summary_path:
        body = summary_path.read_text(encoding="utf-8")
        match = re.search(
            r"(?:^##\s*[۰-۹\d)\s]*)?خلاصهٔ? کوتاه\s*\n+(.+?)(?:\n\n|\n---|\nفهرست)",
            body,
            re.DOTALL | re.MULTILINE,
        )
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
    subtitle_source: str = "edited",
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
    else:
        # Keep previously published audio metadata when media is only on the CDN.
        prev = read_json(out_dir / ("%s.json" % files.session_id), {}) or {}
        if isinstance(prev.get("audio"), dict):
            payload["audio"] = prev["audio"]

    if not skip_subtitles:
        result = None
        if subtitle_source == "raw" and is_raw_alignable(files):
            result = align_raw_session(files)
        elif files.is_alignable():
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

    # Ship readable markdown with the site (CI has no Audios/ symlink).
    out_dir.mkdir(parents=True, exist_ok=True)
    has_legacy = False
    if files.corrected and files.corrected.exists():
        dest = out_dir / ("%s.corrected.md" % files.session_id)
        dest.write_text(files.corrected.read_text(encoding="utf-8"), encoding="utf-8")
        has_legacy = True
    has_summary_md = False
    has_book = False
    for candidate in files.folder.iterdir():
        name = candidate.name
        if name.endswith(".summary.md"):
            dest = out_dir / ("%s.summary.md" % files.session_id)
            dest.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
            has_summary_md = True
        elif name.endswith(".book.md"):
            dest = out_dir / ("%s.book.md" % files.session_id)
            dest.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
            has_book = True
    has_raw = bool(files.raw and files.raw.exists())
    if has_raw:
        prose = parse_raw_text(files.raw)
        dest = out_dir / ("%s.raw.txt" % files.session_id)
        dest.write_text(prose + "\n", encoding="utf-8")
    if has_legacy and has_book:
        text_pipeline = "both"
    elif has_book:
        text_pipeline = "book"
    elif has_legacy:
        text_pipeline = "legacy"
    else:
        text_pipeline = None
    # متن کامل prefers raw ASR when the course is on the new pipeline.
    payload["hasFullText"] = has_raw or has_legacy
    payload["hasLegacyText"] = has_legacy
    payload["hasSummary"] = has_summary_md or bool(payload.get("summary"))
    payload["hasBook"] = has_book
    payload["hasRawTranscript"] = has_raw
    payload["subtitleSource"] = subtitle_source if payload.get("hasTranscript") else None
    payload["textPipeline"] = text_pipeline

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
    subtitle_source = course_meta.get("subtitles", "edited")

    sessions: List[dict] = []
    for child in sorted(course_dir.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name == "_legacy":
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
            files,
            lecturer,
            course,
            catalog_item,
            config,
            out_dir,
            skip_subtitles,
            subtitle_source=subtitle_source,
        )
        if payload is None:
            continue
        if child.name in overrides:
            payload["title"] = overrides[child.name]
        sessions.append(payload)

    if not sessions:
        return None

    # Visible-session order: sequential display numbers + prev/next links.
    for position, session in enumerate(sessions):
        session["index"] = position + 1
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
    """Find course dirs under a lecturer root (…/Lecturer/Course/NNN)."""
    courses = []
    if not root.is_dir():
        return courses
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


def audio_roots_for_site(config: dict) -> List[Path]:
    """Which Audios/ subtrees belong to this site.

    Prefer site.config.json → sources.audioDirs (paths relative to Audios/).
    Fallback: lecturer folders already present under content/.
    """
    sources = config.get("sources") or {}
    dirs = sources.get("audioDirs")
    if isinstance(dirs, list) and dirs:
        roots: List[Path] = []
        for rel in dirs:
            # Keep logical names (Shojai symlink → slug shojai); do not resolve.
            root = (AUDIO_ROOT / str(rel)).absolute()
            if not root.is_dir():
                print("  warn: audioDirs entry missing: %s" % root)
                continue
            roots.append(root)
        return roots

    # content/<slug>/ → Audios/<matching folder>
    if CONTENT_ROOT.is_dir():
        wanted = {
            p.name.lower()
            for p in CONTENT_ROOT.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        }
        if wanted:
            roots = []
            for child in sorted(AUDIO_ROOT.iterdir()):
                if child.is_dir() and child.name.lower() in wanted:
                    roots.append(child.resolve())
            if roots:
                return roots

    # Legacy: entire Audios/ tree (cross-site pollution — avoid when possible)
    print(
        "  warn: no sources.audioDirs / content lecturers — scanning all of Audios/"
    )
    return [AUDIO_ROOT]


def discover_site_courses(config: dict) -> List[Path]:
    """Courses for this site only (not every lecturer under Audios/)."""
    courses: List[Path] = []
    for root in audio_roots_for_site(config):
        # root may be Audios/Bayat (lecturer) or Audios/ (legacy full tree)
        if root == AUDIO_ROOT.resolve():
            courses.extend(discover_courses(root))
            continue
        # Treat path as a lecturer folder: children are courses.
        if any(
            c.is_dir() and c.name.isdigit()
            for c in root.iterdir()
            if not c.name.startswith(".")
        ):
            # Unusual: audioDirs pointed at a course folder itself
            courses.append(root)
            continue
        for course_dir in sorted(root.iterdir()):
            if not course_dir.is_dir() or course_dir.name.startswith("."):
                continue
            if any(
                c.is_dir() and c.name.isdigit() for c in course_dir.iterdir()
            ):
                courses.append(course_dir)
    return courses


def prune_stale_lecturers(out_root: Path, keep: set) -> None:
    """Remove public/data/<lecturer> dirs not in this site's build."""
    reserved = {"search"}
    if not out_root.is_dir():
        return
    for child in sorted(out_root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        name = child.name.lower()
        if name in keep or name in reserved:
            continue
        print("  prune stale data/%s" % child.name)
        shutil.rmtree(child)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course", help="Build only this course folder")
    parser.add_argument("--out", default=None, help="Output root (default: public/data)")
    parser.add_argument(
        "--site-root",
        default=None,
        help="Site tree containing content/, site.config.json, apps/web/ "
        "(default: website/). Use website-portal for the multi-lecturer site.",
    )
    parser.add_argument(
        "--skip-subtitles",
        action="store_true",
        help="Write metadata only, without realigning subtitles",
    )
    args = parser.parse_args()

    if args.site_root:
        configure_site_root(Path(args.site_root))

    config = read_json(SITE_CONFIG, {}) or {}
    out_root = Path(args.out).expanduser() if args.out else DEFAULT_OUT

    if args.course:
        # absolute() keeps lecturer symlinks (Shojai → AyatollahShojaee) so the
        # portal slug matches content/<lecturer>/ rather than the physical folder.
        course_path = Path(args.course).expanduser()
        if not course_path.is_absolute():
            course_path = (Path.cwd() / course_path).absolute()
        else:
            course_path = course_path.absolute()
        course_dirs = [course_path]
    else:
        course_dirs = discover_site_courses(config)

    if not course_dirs:
        sys.exit(
            "No course folders found for this site. "
            "Set sources.audioDirs in site.config.json "
            "(e.g. [\"Bayat\"]) or pass --course."
        )

    print("Output: %s" % out_root)
    if args.course:
        print("Courses: 1 (--course)\n")
    else:
        root_labels = []
        for p in audio_roots_for_site(config):
            try:
                root_labels.append(str(p.relative_to(AUDIO_ROOT)))
            except ValueError:
                root_labels.append(str(p))
        print("Courses: %d from %s\n" % (len(course_dirs), ", ".join(root_labels)))
    lecturers: Dict[str, dict] = {}

    # Partial --course builds must keep sibling courses + other lecturers.
    existing_index = read_json(out_root / "index.json", {}) or {}
    if args.course:
        for prior in existing_index.get("lecturers") or []:
            slug = (prior.get("slug") or "").lower()
            if not slug:
                continue
            lecturers[slug] = {
                **prior,
                "courses": list(prior.get("courses") or []),
            }

    for course_dir in course_dirs:
        result = build_course(course_dir, out_root, config, args.skip_subtitles)
        if result is None:
            print("  skipped %s (no sessions)" % course_dir.name)
            continue
        lecturer_meta = result["lecturer"]
        slug = lecturer_meta["slug"]
        entry = lecturers.setdefault(slug, {**lecturer_meta, "courses": []})
        # Refresh lecturer fields from content/, keep course list.
        for key, value in lecturer_meta.items():
            if key != "courses":
                entry[key] = value
        course = result["course"]
        courses = entry.setdefault("courses", [])
        replaced = False
        for i, existing in enumerate(courses):
            if existing.get("slug") == course["slug"]:
                courses[i] = course
                replaced = True
                break
        if not replaced:
            courses.append(course)
        print(
            "  %-10s / %-16s %3d sessions, %3d transcribed, %s"
            % (
                slug,
                course["slug"],
                course["sessionCount"],
                course["transcribedCount"],
                course["totalDurationText"],
            )
        )

    if not args.course:
        # Full rebuild: keep text-library lecturers (e.g. Shojai کلیات).
        for prior in existing_index.get("lecturers") or []:
            slug = (prior.get("slug") or "").lower()
            if not slug or slug in lecturers:
                continue
            if prior.get("format") == "text":
                lecturers[slug] = prior

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

    if not args.course:
        prune_stale_lecturers(out_root, {slug.lower() for slug in lecturers})

    # Rebuild compact client search indexes when available (prefer this site's script).
    search_script = CONTENT_ROOT.parent / "scripts" / "build_search_indexes.py"
    if not search_script.exists():
        search_script = (
            Path(__file__).resolve().parents[1] / "scripts" / "build_search_indexes.py"
        )
    if search_script.exists():
        print("\nBuilding search indexes…")
        result = subprocess.run(
            [sys.executable, str(search_script)],
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            print("  warn: build_search_indexes exited with %s" % result.returncode)


if __name__ == "__main__":
    main()
