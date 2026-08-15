"use client";

import { create } from "zustand";

type PlayerState = {
  currentTime: number;
  duration: number;
  playing: boolean;
  rate: number;
  subtitlesOn: boolean;
  volume: number;
  setCurrentTime: (t: number) => void;
  setDuration: (d: number) => void;
  setPlaying: (p: boolean) => void;
  setRate: (r: number) => void;
  setSubtitlesOn: (v: boolean) => void;
  setVolume: (v: number) => void;
};

export const usePlayerStore = create<PlayerState>((set) => ({
  currentTime: 0,
  duration: 0,
  playing: false,
  rate: 1,
  subtitlesOn: true,
  volume: 1,
  setCurrentTime: (currentTime) => set({ currentTime }),
  setDuration: (duration) => set({ duration }),
  setPlaying: (playing) => set({ playing }),
  setRate: (rate) => set({ rate }),
  setSubtitlesOn: (subtitlesOn) => set({ subtitlesOn }),
  setVolume: (volume) => set({ volume }),
}));

const LIST_KEY = "lecture-my-list";
const PROGRESS_KEY = "lecture-progress";

export type ListItem = {
  lecturer: string;
  course: string;
  session: string;
  title: string;
  addedAt: number;
};

export function loadMyList(): ListItem[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(LIST_KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveMyList(items: ListItem[]) {
  localStorage.setItem(LIST_KEY, JSON.stringify(items));
}

export function toggleMyList(item: Omit<ListItem, "addedAt">): ListItem[] {
  const list = loadMyList();
  const key = `${item.lecturer}/${item.course}/${item.session}`;
  const exists = list.findIndex(
    (x) => `${x.lecturer}/${x.course}/${x.session}` === key,
  );
  let next: ListItem[];
  if (exists >= 0) next = list.filter((_, i) => i !== exists);
  else next = [{ ...item, addedAt: Date.now() }, ...list];
  saveMyList(next);
  return next;
}

export function isInMyList(
  lecturer: string,
  course: string,
  session: string,
): boolean {
  return loadMyList().some(
    (x) =>
      x.lecturer === lecturer && x.course === course && x.session === session,
  );
}

export function saveProgress(
  lecturer: string,
  course: string,
  session: string,
  time: number,
  duration: number,
) {
  if (typeof window === "undefined") return;
  try {
    const all = JSON.parse(localStorage.getItem(PROGRESS_KEY) || "{}");
    all[`${lecturer}/${course}/${session}`] = {
      time,
      duration,
      updatedAt: Date.now(),
    };
    localStorage.setItem(PROGRESS_KEY, JSON.stringify(all));
  } catch {
    /* ignore */
  }
}

export function loadProgress(
  lecturer: string,
  course: string,
  session: string,
): number {
  if (typeof window === "undefined") return 0;
  try {
    const all = JSON.parse(localStorage.getItem(PROGRESS_KEY) || "{}");
    return Number(all[`${lecturer}/${course}/${session}`]?.time || 0);
  } catch {
    return 0;
  }
}
