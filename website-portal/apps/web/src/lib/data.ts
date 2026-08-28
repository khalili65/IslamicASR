import fs from "fs";
import path from "path";
import type { CourseIndex, CuesFile, SessionPayload, SiteIndex } from "./types";

export { toPersianDigits, formatClock, findCueIndex } from "./format";

const DATA_ROOT = path.join(process.cwd(), "public", "data");

function readJson<T>(filePath: string): T {
  return JSON.parse(fs.readFileSync(filePath, "utf8")) as T;
}

export function getSiteIndex(): SiteIndex {
  return readJson(path.join(DATA_ROOT, "index.json"));
}

export function getCourse(lecturer: string, course: string): CourseIndex {
  return readJson(path.join(DATA_ROOT, lecturer, course, "course.json"));
}

export function getSession(
  lecturer: string,
  course: string,
  session: string,
): SessionPayload {
  return readJson(path.join(DATA_ROOT, lecturer, course, `${session}.json`));
}

export function getCues(
  lecturer: string,
  course: string,
  session: string,
): CuesFile | null {
  const file = path.join(DATA_ROOT, lecturer, course, `${session}.cues.json`);
  if (!fs.existsSync(file)) return null;
  return readJson(file);
}

export function listSessions(lecturer: string, course: string): string[] {
  const dir = path.join(DATA_ROOT, lecturer, course);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((name) => /^\d+\.json$/.test(name))
    .map((name) => name.replace(/\.json$/, ""))
    .sort();
}

export function dataUrl(
  lecturer: string,
  course: string,
  filename: string,
): string {
  return `/data/${lecturer}/${course}/${filename}`;
}
