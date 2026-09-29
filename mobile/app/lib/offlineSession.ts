import AsyncStorage from "@react-native-async-storage/async-storage";
import * as FileSystem from "expo-file-system/legacy";
import type { Cue, CuesFile, SessionPayload } from "@/lib/types";
import { toPersianDigits } from "@/lib/format";

const INDEX_KEY = "offline-session-index-v1";

export type OfflineSessionKey = {
  lecturerSlug: string;
  courseSlug: string;
  sessionId: string;
};

export type OfflinePackManifest = OfflineSessionKey & {
  title: string;
  courseTitle?: string;
  lecturerName?: string;
  site: "website" | "portal";
  downloadedAt: number;
  bytes: number;
  hasAudio: boolean;
  hasFull: boolean;
  hasBook: boolean;
  hasSummary: boolean;
  hasCues: boolean;
};

export type OfflineLocalPaths = {
  audioUri: string | null;
  fullUri: string | null;
  bookUri: string | null;
  summaryUri: string | null;
  sessionUri: string | null;
  cuesUri: string | null;
};

export type DownloadOfflineInput = OfflineSessionKey & {
  site: "website" | "portal";
  title: string;
  courseTitle?: string;
  lecturerName?: string;
  session: SessionPayload;
  cues: Cue[];
  audioUrl: string;
  /** Absolute HTTPS URLs for optional text assets. */
  fullUrl?: string | null;
  bookUrl?: string | null;
  summaryUrl?: string | null;
  onProgress?: (ratio: number) => void;
};

function packKey(k: OfflineSessionKey): string {
  return `${k.lecturerSlug}/${k.courseSlug}/${k.sessionId}`;
}

function rootDir(): string {
  const root = FileSystem.documentDirectory;
  if (!root) throw new Error("no document directory");
  return `${root}offline/`;
}

function sessionDir(k: OfflineSessionKey): string {
  return `${rootDir()}${k.lecturerSlug}/${k.courseSlug}/${k.sessionId}/`;
}

export function formatBytesFa(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return toPersianDigits("؟");
  const mb = bytes / (1024 * 1024);
  if (mb >= 1) {
    const rounded = mb >= 10 ? Math.round(mb) : Math.round(mb * 10) / 10;
    return `${toPersianDigits(rounded)} مگابایت`;
  }
  const kb = Math.max(1, Math.round(bytes / 1024));
  return `${toPersianDigits(kb)} کیلوبایت`;
}

/** Approximate pack size shown before download (audio dominates). */
export function estimateOfflineBytes(session: SessionPayload): number {
  const audio = session.audio?.size ?? 0;
  // Texts/cues/session JSON are tiny relative to audio.
  return audio > 0 ? audio + 256 * 1024 : 5 * 1024 * 1024;
}

async function readIndex(): Promise<OfflinePackManifest[]> {
  try {
    const raw = await AsyncStorage.getItem(INDEX_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as OfflinePackManifest[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

async function writeIndex(items: OfflinePackManifest[]): Promise<void> {
  await AsyncStorage.setItem(INDEX_KEY, JSON.stringify(items));
}

export async function listOfflinePacks(): Promise<OfflinePackManifest[]> {
  return readIndex();
}

export async function getOfflineManifest(
  key: OfflineSessionKey,
): Promise<OfflinePackManifest | null> {
  const id = packKey(key);
  const items = await readIndex();
  return items.find((i) => packKey(i) === id) ?? null;
}

export function offlinePaths(key: OfflineSessionKey): OfflineLocalPaths {
  const dir = sessionDir(key);
  return {
    audioUri: `${dir}audio.m4a`,
    fullUri: `${dir}full.txt`,
    bookUri: `${dir}book.md`,
    summaryUri: `${dir}summary.md`,
    sessionUri: `${dir}session.json`,
    cuesUri: `${dir}cues.json`,
  };
}

async function fileExists(uri: string | null | undefined): Promise<boolean> {
  if (!uri) return false;
  try {
    const info = await FileSystem.getInfoAsync(uri);
    return info.exists && !info.isDirectory;
  } catch {
    return false;
  }
}

export async function resolveOfflinePaths(
  key: OfflineSessionKey,
): Promise<OfflineLocalPaths | null> {
  const manifest = await getOfflineManifest(key);
  if (!manifest?.hasAudio) return null;
  const paths = offlinePaths(key);
  if (!(await fileExists(paths.audioUri))) return null;
  return {
    audioUri: paths.audioUri,
    fullUri: manifest.hasFull && (await fileExists(paths.fullUri)) ? paths.fullUri : null,
    bookUri: manifest.hasBook && (await fileExists(paths.bookUri)) ? paths.bookUri : null,
    summaryUri:
      manifest.hasSummary && (await fileExists(paths.summaryUri))
        ? paths.summaryUri
        : null,
    sessionUri: (await fileExists(paths.sessionUri)) ? paths.sessionUri : null,
    cuesUri:
      manifest.hasCues && (await fileExists(paths.cuesUri)) ? paths.cuesUri : null,
  };
}

export async function loadOfflineSession(
  key: OfflineSessionKey,
): Promise<{ session: SessionPayload; cues: Cue[] } | null> {
  const paths = await resolveOfflinePaths(key);
  if (!paths?.sessionUri) return null;
  try {
    const raw = await FileSystem.readAsStringAsync(paths.sessionUri);
    const session = JSON.parse(raw) as SessionPayload;
    let cues: Cue[] = [];
    if (paths.cuesUri) {
      const cuesRaw = await FileSystem.readAsStringAsync(paths.cuesUri);
      const cuesFile = JSON.parse(cuesRaw) as CuesFile;
      cues = cuesFile.cues ?? [];
    }
    return { session, cues };
  } catch {
    return null;
  }
}

async function downloadOptional(
  url: string | null | undefined,
  dest: string,
): Promise<boolean> {
  if (!url) return false;
  try {
    const result = await FileSystem.downloadAsync(url, dest);
    return result.status >= 200 && result.status < 300;
  } catch {
    return false;
  }
}

export async function downloadOfflinePack(
  input: DownloadOfflineInput,
): Promise<OfflinePackManifest> {
  if (!input.audioUrl) throw new Error("no audio");

  const dir = sessionDir(input);
  const paths = offlinePaths(input);

  // Fresh folder for this pack
  try {
    await FileSystem.deleteAsync(dir, { idempotent: true });
  } catch {
    /* ok */
  }
  await FileSystem.makeDirectoryAsync(dir, { intermediates: true });

  input.onProgress?.(0.02);

  // Persist metadata already in memory (works offline later without network).
  await FileSystem.writeAsStringAsync(
    paths.sessionUri!,
    JSON.stringify(input.session),
  );
  const cuesFile: CuesFile = {
    version: 1,
    sessionId: input.sessionId,
    lang: "fa",
    duration: input.session.audio?.duration ?? 0,
    chapters: input.session.chapters ?? [],
    cues: input.cues ?? [],
  };
  await FileSystem.writeAsStringAsync(
    paths.cuesUri!,
    JSON.stringify(cuesFile),
  );
  input.onProgress?.(0.08);

  const audioResult = await FileSystem.downloadAsync(
    input.audioUrl,
    paths.audioUri!,
  );
  if (audioResult.status < 200 || audioResult.status >= 300) {
    await FileSystem.deleteAsync(dir, { idempotent: true });
    throw new Error(`audio download failed: ${audioResult.status}`);
  }
  input.onProgress?.(0.75);

  const hasFull = await downloadOptional(input.fullUrl, paths.fullUri!);
  input.onProgress?.(0.85);
  const hasBook = await downloadOptional(input.bookUrl, paths.bookUri!);
  input.onProgress?.(0.92);
  const hasSummary = await downloadOptional(
    input.summaryUrl,
    paths.summaryUri!,
  );
  input.onProgress?.(0.97);

  let bytes = 0;
  for (const uri of [
    paths.audioUri,
    paths.sessionUri,
    paths.cuesUri,
    hasFull ? paths.fullUri : null,
    hasBook ? paths.bookUri : null,
    hasSummary ? paths.summaryUri : null,
  ]) {
    if (!uri) continue;
    try {
      const info = await FileSystem.getInfoAsync(uri);
      if (info.exists && "size" in info && typeof info.size === "number") {
        bytes += info.size;
      }
    } catch {
      /* ignore */
    }
  }

  const manifest: OfflinePackManifest = {
    lecturerSlug: input.lecturerSlug,
    courseSlug: input.courseSlug,
    sessionId: input.sessionId,
    title: input.title,
    courseTitle: input.courseTitle,
    lecturerName: input.lecturerName,
    site: input.site,
    downloadedAt: Date.now(),
    bytes,
    hasAudio: true,
    hasFull,
    hasBook,
    hasSummary,
    hasCues: (input.cues?.length ?? 0) > 0,
  };

  const index = await readIndex();
  const id = packKey(input);
  const next = [manifest, ...index.filter((i) => packKey(i) !== id)];
  await writeIndex(next);
  input.onProgress?.(1);
  return manifest;
}

export async function deleteOfflinePack(key: OfflineSessionKey): Promise<void> {
  const dir = sessionDir(key);
  try {
    await FileSystem.deleteAsync(dir, { idempotent: true });
  } catch {
    /* ok */
  }
  const id = packKey(key);
  const index = await readIndex();
  await writeIndex(index.filter((i) => packKey(i) !== id));
}
