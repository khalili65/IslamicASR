import fs from "fs";
import path from "path";
import { paths, pathsFor } from "./paths";
import type { SiteId } from "./sites";

export type LecturerMeta = {
  slug: string;
  name: string;
  title: string;
  bio: string;
  avatar: string;
  links: { label: string; url: string }[];
};

export type CourseMeta = {
  slug: string;
  title: string;
  description: string;
  cover: string;
  hidden: string[];
  subtitles?: string;
  titles: Record<string, string>;
};

export type SessionRow = {
  id: string;
  index: number;
  title: string;
  topic?: string;
  hidden: boolean;
  durationText?: string;
  hasTranscript?: boolean;
  hasBook?: boolean;
  hasSummary?: boolean;
};

export type SessionDocKind = "book" | "summary";

const DOC_SUFFIX: Record<SessionDocKind, string> = {
  book: ".book.md",
  summary: ".summary.md",
};

function readJson<T>(file: string): T | null {
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

function writeJson(file: string, data: unknown) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 1) + "\n", "utf8");
}

export function listLecturers(siteId: SiteId): string[] {
  const root = pathsFor(siteId).content();
  if (!fs.existsSync(root)) return [];
  return fs
    .readdirSync(root)
    .filter((n) => {
      const p = path.join(root, n);
      return fs.statSync(p).isDirectory() && fs.existsSync(path.join(p, "lecturer.json"));
    })
    .sort();
}

export function listCourses(siteId: SiteId, lecturer: string): string[] {
  const root = path.join(pathsFor(siteId).content(), lecturer);
  if (!fs.existsSync(root)) return [];
  return fs
    .readdirSync(root)
    .filter((n) => {
      const p = path.join(root, n);
      return (
        fs.statSync(p).isDirectory() &&
        fs.existsSync(path.join(p, "course.json"))
      );
    })
    .sort();
}

export function readLecturer(siteId: SiteId, slug: string): LecturerMeta {
  const file = path.join(pathsFor(siteId).content(), slug, "lecturer.json");
  const data = readJson<LecturerMeta>(file);
  if (!data) throw new Error(`Missing lecturer: ${slug}`);
  return data;
}

export function writeLecturer(siteId: SiteId, slug: string, data: LecturerMeta) {
  writeJson(path.join(pathsFor(siteId).content(), slug, "lecturer.json"), {
    ...data,
    slug,
  });
}

export function readCourse(
  siteId: SiteId,
  lecturer: string,
  course: string,
): CourseMeta {
  const file = path.join(
    pathsFor(siteId).content(),
    lecturer,
    course,
    "course.json",
  );
  const data = readJson<CourseMeta>(file);
  if (!data) throw new Error(`Missing course: ${lecturer}/${course}`);
  return {
    ...data,
    slug: course,
    hidden: data.hidden || [],
    titles: data.titles || {},
  };
}

export function writeCourse(
  siteId: SiteId,
  lecturer: string,
  course: string,
  data: CourseMeta,
) {
  writeJson(
    path.join(pathsFor(siteId).content(), lecturer, course, "course.json"),
    {
      ...data,
      slug: course,
    },
  );
}

/** Find Audios/.../<Course> from slug e.g. qasemian/insanekamel or manaee/term1 */
export function findAudiosCourseDir(
  lecturer: string,
  course: string,
): string | null {
  const audios = paths.audios();
  if (!fs.existsSync(audios)) return null;

  const lec = lecturer.toLowerCase();
  const crs = course.toLowerCase();

  for (const lecName of fs.readdirSync(audios)) {
    if (lecName.startsWith(".") || lecName.toLowerCase() !== lec) continue;
    const lecPath = path.join(audios, lecName);
    if (!fs.statSync(lecPath).isDirectory()) continue;
    for (const crsName of fs.readdirSync(lecPath)) {
      if (crsName.startsWith(".") || crsName.toLowerCase() !== crs) continue;
      const crsPath = path.join(lecPath, crsName);
      if (fs.statSync(crsPath).isDirectory()) return crsPath;
    }
  }

  const matches: string[] = [];
  function walk(dir: string, depth: number) {
    if (depth > 6) return;
    let entries: string[];
    try {
      entries = fs.readdirSync(dir);
    } catch {
      return;
    }
    const base = path.basename(dir).toLowerCase();
    const hasSessions = entries.some((n) => /^\d{3}$/.test(n));
    if (hasSessions && base === crs) {
      const rel = path.relative(audios, dir).toLowerCase();
      if (rel.includes(lec)) matches.push(dir);
    }
    for (const name of entries) {
      if (
        name.startsWith(".") ||
        name === "_legacy" ||
        name === "_course_maps" ||
        /^\d{3}$/.test(name)
      ) {
        continue;
      }
      const child = path.join(dir, name);
      try {
        if (fs.statSync(child).isDirectory()) walk(child, depth + 1);
      } catch {
        /* skip */
      }
    }
  }
  walk(audios, 0);
  return matches[0] || null;
}

function sessionHasDoc(
  sessionFolder: string | null,
  dataDir: string,
  sessionId: string,
  kind: SessionDocKind,
): boolean {
  const suffix = DOC_SUFFIX[kind];
  if (sessionFolder && fs.existsSync(sessionFolder)) {
    if (fs.readdirSync(sessionFolder).some((n) => n.endsWith(suffix))) {
      return true;
    }
  }
  return fs.existsSync(path.join(dataDir, `${sessionId}${suffix}`));
}

export function findSessionDocPath(
  siteId: SiteId,
  lecturer: string,
  course: string,
  sessionId: string,
  kind: SessionDocKind,
): string | null {
  const suffix = DOC_SUFFIX[kind];
  const audiosDir = findAudiosCourseDir(lecturer, course);
  if (audiosDir) {
    const sessionDir = path.join(audiosDir, sessionId);
    if (fs.existsSync(sessionDir)) {
      const match = fs.readdirSync(sessionDir).find((n) => n.endsWith(suffix));
      if (match) return path.join(sessionDir, match);
    }
  }
  const shipped = path.join(
    pathsFor(siteId).data(),
    lecturer,
    course,
    `${sessionId}${suffix}`,
  );
  if (fs.existsSync(shipped)) return shipped;
  return null;
}

export function readSessionDoc(
  siteId: SiteId,
  lecturer: string,
  course: string,
  sessionId: string,
  kind: SessionDocKind,
): { content: string; path: string | null; writable: boolean } {
  const filePath = findSessionDocPath(siteId, lecturer, course, sessionId, kind);
  if (!filePath) {
    return { content: "", path: null, writable: false };
  }
  const audiosRoot = paths.audios();
  const writable = filePath.startsWith(audiosRoot);
  return {
    content: fs.readFileSync(filePath, "utf8"),
    path: filePath,
    writable,
  };
}

export function writeSessionDoc(
  siteId: SiteId,
  lecturer: string,
  course: string,
  sessionId: string,
  kind: SessionDocKind,
  content: string,
): string {
  const suffix = DOC_SUFFIX[kind];
  const audiosDir = findAudiosCourseDir(lecturer, course);
  if (!audiosDir) {
    throw new Error("پوشه Audios برای این درس پیدا نشد.");
  }
  const sessionDir = path.join(audiosDir, sessionId);
  if (!fs.existsSync(sessionDir)) {
    throw new Error(`پوشه جلسه ${sessionId} در Audios وجود ندارد.`);
  }

  let filePath = findSessionDocPath(siteId, lecturer, course, sessionId, kind);
  if (!filePath || !filePath.startsWith(paths.audios())) {
    const existing = fs
      .readdirSync(sessionDir)
      .find((n) => n.endsWith(suffix));
    if (existing) {
      filePath = path.join(sessionDir, existing);
    } else {
      const prefix =
        fs.readdirSync(sessionDir).find((n) => n.endsWith(".txt"))?.replace(/\.txt$/, "") ||
        `${sessionId}`;
      filePath = path.join(sessionDir, `${prefix}${suffix}`);
    }
  }

  if (fs.existsSync(filePath)) {
    const backup = filePath.replace(/\.(book|summary)\.md$/, ".$1.prev.md");
    fs.copyFileSync(filePath, backup);
  }

  fs.writeFileSync(filePath, content, "utf8");
  return filePath;
}

export function listSessions(
  siteId: SiteId,
  lecturer: string,
  course: string,
): SessionRow[] {
  const courseMeta = readCourse(siteId, lecturer, course);
  const hidden = new Set((courseMeta.hidden || []).map(String));
  const overrides = courseMeta.titles || {};

  const ids = new Set<string>();

  const audiosDir = findAudiosCourseDir(lecturer, course);
  if (audiosDir) {
    for (const name of fs.readdirSync(audiosDir)) {
      if (/^\d{3}$/.test(name)) ids.add(name);
    }
  }

  const dataDir = path.join(pathsFor(siteId).data(), lecturer, course);
  if (fs.existsSync(dataDir)) {
    for (const f of fs.readdirSync(dataDir)) {
      const m = f.match(/^(\d{3})\.json$/);
      if (m) ids.add(m[1]);
    }
  }

  for (const id of hidden) ids.add(id);
  for (const id of Object.keys(overrides)) ids.add(id);

  const rows: SessionRow[] = [];
  for (const id of [...ids].sort()) {
    const sessionFile = path.join(dataDir, `${id}.json`);
    const built = readJson<{
      title?: string;
      topic?: string;
      durationText?: string;
      hasTranscript?: boolean;
      hasBook?: boolean;
      hasSummary?: boolean;
      audio?: { durationText?: string };
    }>(sessionFile);

    const sessionAudiosDir = audiosDir ? path.join(audiosDir, id) : null;

    rows.push({
      id,
      index: parseInt(id, 10) || 0,
      title: overrides[id] || built?.title || `جلسه ${id}`,
      topic: built?.topic,
      hidden: hidden.has(id),
      durationText: built?.audio?.durationText,
      hasTranscript: built?.hasTranscript,
      hasBook:
        built?.hasBook ??
        sessionHasDoc(sessionAudiosDir, dataDir, id, "book"),
      hasSummary:
        built?.hasSummary ??
        sessionHasDoc(sessionAudiosDir, dataDir, id, "summary"),
    });
  }

  return rows.sort((a, b) => a.index - b.index);
}

export function setSessionTitle(
  siteId: SiteId,
  lecturer: string,
  course: string,
  sessionId: string,
  title: string,
) {
  const meta = readCourse(siteId, lecturer, course);
  meta.titles = { ...meta.titles, [sessionId]: title.trim() };
  writeCourse(siteId, lecturer, course, meta);
}

export function setSessionHidden(
  siteId: SiteId,
  lecturer: string,
  course: string,
  sessionId: string,
  hidden: boolean,
) {
  const meta = readCourse(siteId, lecturer, course);
  const set = new Set((meta.hidden || []).map(String));
  if (hidden) set.add(sessionId);
  else set.delete(sessionId);
  meta.hidden = [...set].sort();
  writeCourse(siteId, lecturer, course, meta);
}

export function saveLecturerAvatar(
  siteId: SiteId,
  slug: string,
  buffer: Buffer,
  ext: string,
) {
  const dir = pathsFor(siteId).lecturerImages();
  fs.mkdirSync(dir, { recursive: true });
  const filename = `${slug}${ext}`;
  const dest = path.join(dir, filename);
  fs.writeFileSync(dest, buffer);
  const avatarPath = `/images/lecturers/${filename}`;
  const lec = readLecturer(siteId, slug);
  lec.avatar = avatarPath;
  writeLecturer(siteId, slug, lec);
  return avatarPath;
}

