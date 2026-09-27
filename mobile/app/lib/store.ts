import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import type { Lecturer } from "./types";

const SAVED_KEY = "lecture-my-list";

export type SavedItem = {
  lecturerSlug: string;
  courseSlug: string;
  sessionId: string;
  title: string;
  courseTitle: string;
  lecturerName: string;
  site: "website" | "portal";
};

type LibraryState = {
  lecturers: Lecturer[];
  loading: boolean;
  error: string | null;
  saved: SavedItem[];
  load: () => Promise<void>;
  loadSaved: () => Promise<void>;
  toggleSaved: (item: SavedItem) => Promise<void>;
  isSaved: (lecturerSlug: string, courseSlug: string, sessionId: string) => boolean;
  findLecturer: (slug: string) => Lecturer | undefined;
};

export const useLibraryStore = create<LibraryState>((set, get) => ({
  lecturers: [],
  loading: false,
  error: null,
  saved: [],
  async load() {
    set({ loading: true, error: null });
    try {
      const { loadLibrary } = await import("./api");
      const lecturers = await loadLibrary();
      set({ lecturers, loading: false });
    } catch (e) {
      set({
        loading: false,
        error: e instanceof Error ? e.message : "خطا در بارگذاری",
      });
    }
  },
  async loadSaved() {
    try {
      const raw = await AsyncStorage.getItem(SAVED_KEY);
      if (raw) set({ saved: JSON.parse(raw) as SavedItem[] });
    } catch {
      /* ignore */
    }
  },
  async toggleSaved(item) {
    const key = `${item.lecturerSlug}/${item.courseSlug}/${item.sessionId}`;
    const exists = get().saved.some(
      (s) =>
        `${s.lecturerSlug}/${s.courseSlug}/${s.sessionId}` === key,
    );
    const saved = exists
      ? get().saved.filter(
          (s) =>
            `${s.lecturerSlug}/${s.courseSlug}/${s.sessionId}` !== key,
        )
      : [item, ...get().saved];
    set({ saved });
    await AsyncStorage.setItem(SAVED_KEY, JSON.stringify(saved));
  },
  isSaved(lecturerSlug, courseSlug, sessionId) {
    return get().saved.some(
      (s) =>
        s.lecturerSlug === lecturerSlug &&
        s.courseSlug === courseSlug &&
        s.sessionId === sessionId,
    );
  },
  findLecturer(slug) {
    return get().lecturers.find((l) => l.slug === slug);
  },
}));
