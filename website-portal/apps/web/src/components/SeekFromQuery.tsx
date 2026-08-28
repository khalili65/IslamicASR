"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { usePlayerStore } from "@/lib/store";

/** Seeks the audio when opened with ?t=seconds */
export function SeekFromQuery({ audioSelector = "audio" }: { audioSelector?: string }) {
  const search = useSearchParams();
  const setCurrentTime = usePlayerStore((s) => s.setCurrentTime);

  useEffect(() => {
    const raw = search.get("t");
    if (!raw) return;
    const t = Number(raw);
    if (!Number.isFinite(t) || t < 0) return;
    const trySeek = () => {
      const audio = document.querySelector(audioSelector) as HTMLAudioElement | null;
      if (!audio) return false;
      const apply = () => {
        audio.currentTime = t;
        setCurrentTime(t);
      };
      if (audio.readyState >= 1) apply();
      else audio.addEventListener("loadedmetadata", apply, { once: true });
      return true;
    };
    if (!trySeek()) {
      const id = window.setInterval(() => {
        if (trySeek()) window.clearInterval(id);
      }, 200);
      return () => window.clearInterval(id);
    }
  }, [search, audioSelector, setCurrentTime]);

  return null;
}
