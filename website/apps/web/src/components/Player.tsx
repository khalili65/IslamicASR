"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import type { Cue, SessionPayload } from "@/lib/types";
import { findCueIndex, formatClock, toPersianDigits } from "@/lib/format";
import { resolveMediaUrl } from "@/lib/media";
import {
  usePlayerStore,
  loadProgress,
  saveProgress,
  toggleMyList,
  isInMyList,
} from "@/lib/store";
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  Back15Icon,
  BookmarkIcon,
  CaptionsIcon,
  ChevronIcon,
  DownloadIcon,
  Forward15Icon,
  PauseIcon,
  PlayIcon,
  ShareIcon,
  SpeedIcon,
  TextIcon,
  WaveIcon,
} from "@/components/Icons";

type Props = {
  session: SessionPayload;
  cues: Cue[];
  cuesPath: string;
};

const RATES = [0.75, 1, 1.25, 1.5, 2];

export function Player({ session, cues }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const cueListRef = useRef<HTMLDivElement>(null);
  const speedRef = useRef<HTMLDivElement>(null);
  const {
    currentTime,
    duration,
    playing,
    rate,
    subtitlesOn,
    setCurrentTime,
    setDuration,
    setPlaying,
    setRate,
    setSubtitlesOn,
  } = usePlayerStore();

  const [inList, setInList] = useState(false);
  const [showChapters, setShowChapters] = useState(true);
  const [speedOpen, setSpeedOpen] = useState(false);
  const [hideTranslations, setHideTranslations] = useState(false);
  const [autoFollow, setAutoFollow] = useState(true);

  const total = duration || session.audio?.duration || 0;

  const cueIndex = useMemo(
    () => findCueIndex(cues, currentTime),
    [cues, currentTime],
  );
  const currentCue = cueIndex >= 0 ? cues[cueIndex] : null;
  const prevCue = cueIndex > 0 ? cues[cueIndex - 1] : null;
  const nextCue =
    cueIndex >= 0 && cueIndex < cues.length - 1 ? cues[cueIndex + 1] : null;

  const seek = useCallback(
    (t: number) => {
      const audio = audioRef.current;
      if (!audio) return;
      audio.currentTime = Math.max(0, Math.min(t, audio.duration || t));
      setCurrentTime(audio.currentTime);
    },
    [setCurrentTime],
  );

  const togglePlay = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      await audio.play();
      setPlaying(true);
    } else {
      audio.pause();
      setPlaying(false);
    }
  }, [setPlaying]);

  useEffect(() => {
    setInList(isInMyList(session.lecturer, session.course, session.id));
  }, [session]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const saved = loadProgress(session.lecturer, session.course, session.id);
    if (saved > 5 && saved < (session.audio?.duration || Infinity) - 10) {
      audio.currentTime = saved;
      setCurrentTime(saved);
    }
  }, [session, setCurrentTime]);

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) audio.playbackRate = rate;
  }, [rate]);

  // Poll currentTime while playing — onTimeUpdate only fires ~4×/sec, which
  // makes the subtitle land visibly after the words.
  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    const tick = () => {
      const audio = audioRef.current;
      if (audio) setCurrentTime(audio.currentTime);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, setCurrentTime]);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      const audio = audioRef.current;
      if (!audio) return;
      saveProgress(
        session.lecturer,
        session.course,
        session.id,
        audio.currentTime,
        audio.duration || 0,
      );
    }, 4000);
    return () => window.clearInterval(id);
  }, [playing, session]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !("mediaSession" in navigator)) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: session.title,
      artist: session.lecturer,
      album: session.course,
    });
    navigator.mediaSession.setActionHandler("play", () => audio.play());
    navigator.mediaSession.setActionHandler("pause", () => audio.pause());
    navigator.mediaSession.setActionHandler("seekbackward", () => {
      audio.currentTime = Math.max(0, audio.currentTime - 15);
    });
    navigator.mediaSession.setActionHandler("seekforward", () => {
      audio.currentTime = Math.min(audio.duration || 0, audio.currentTime + 15);
    });
  }, [session]);

  // Follow the active line inside the transcript panel only. Scrolling the
  // panel's own scrollTop never moves the page itself.
  useEffect(() => {
    if (!autoFollow || cueIndex < 0) return;
    const container = cueListRef.current;
    const line = container?.querySelector<HTMLElement>(
      `[data-cue="${cueIndex}"]`,
    );
    if (!container || !line) return;
    container.scrollTo({
      top: Math.max(
        0,
        line.offsetTop - container.clientHeight / 2 + line.clientHeight / 2,
      ),
      behavior: "smooth",
    });
  }, [cueIndex, autoFollow]);

  useEffect(() => {
    if (!speedOpen) return;
    const close = (event: MouseEvent) => {
      if (!speedRef.current?.contains(event.target as Node)) setSpeedOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [speedOpen]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
      if (event.code === "Space") {
        event.preventDefault();
        void togglePlay();
      } else if (event.key === "ArrowRight") {
        seek(currentTime - 15);
      } else if (event.key === "ArrowLeft") {
        seek(currentTime + 15);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [togglePlay, seek, currentTime]);

  const progress = total > 0 ? Math.min(100, (currentTime / total) * 100) : 0;

  const share = async () => {
    const url = typeof window !== "undefined" ? window.location.href : "";
    if (navigator.share) {
      try {
        await navigator.share({ title: session.title, url });
        return;
      } catch {
        /* user dismissed — fall through to copying */
      }
    }
    await navigator.clipboard.writeText(url);
    alert("پیوند کپی شد");
  };

  const audioSrc = resolveMediaUrl(session.audio?.url);

  const download = () => {
    if (!audioSrc) return;
    const a = document.createElement("a");
    a.href = audioSrc;
    a.download = session.audio?.filename || "lecture.m4a";
    a.click();
  };

  return (
    <div className="space-y-5">
      {/* Session heading */}
      <header className="animate-rise space-y-2">
        <Link
          href={`/${session.lecturer}/${session.course}/`}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-ink/50 transition hover:text-brand-deep"
        >
          <ArrowRightIcon className="h-3.5 w-3.5" />
          بازگشت به فهرست جلسات
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip-brand">جلسه {toPersianDigits(session.index)}</span>
          <span className="chip">
            <WaveIcon className="h-3.5 w-3.5" />
            {session.hasTranscript ? "دارای متن همگام" : "فقط صوت"}
          </span>
        </div>
        <h1 className="text-2xl font-extrabold leading-9 tracking-tight">
          {session.title}
        </h1>
        {session.topic ? (
          <p className="text-sm leading-7 text-ink/60">
            {session.topic.replace(/\*\*/g, "")}
          </p>
        ) : null}
      </header>

      {/* Subtitle stage */}
      <div className="relative flex min-h-[15rem] flex-col justify-center gap-3 overflow-hidden rounded-card bg-subtitle-bg px-6 py-9 text-center text-subtitle-fg shadow-stage">
        <div
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            backgroundImage:
              "radial-gradient(38rem 18rem at 50% -20%, rgb(var(--brand) / 0.22), transparent 70%), radial-gradient(24rem 16rem at 90% 120%, rgb(var(--accent) / 0.12), transparent 70%)",
          }}
        />
        <div className="relative">
          {subtitlesOn && currentCue ? (
            <div key={cueIndex} className="animate-cue-in space-y-3">
              <p className="line-clamp-1 text-sm text-subtitle-fg/30">
                {prevCue?.text || "\u00a0"}
              </p>
              <p
                className={
                  currentCue.kind === "quote"
                    ? "ayah text-[1.45rem] font-semibold"
                    : "text-lg font-medium leading-9"
                }
              >
                {currentCue.text}
              </p>
              {!hideTranslations && currentCue.translation ? (
                <p className="text-sm leading-7 text-subtitle-fg/60">
                  {currentCue.translation}
                </p>
              ) : null}
              <p className="line-clamp-1 text-sm text-subtitle-fg/30">
                {nextCue?.text || "\u00a0"}
              </p>
            </div>
          ) : (
            <div className="space-y-3 text-subtitle-fg/45">
              <WaveIcon className="mx-auto h-8 w-8" />
              <p className="text-sm">
                {!session.hasTranscript
                  ? "متن این جلسه هنوز آماده نشده است"
                  : subtitlesOn
                    ? "در انتظار شروع گفتار…"
                    : "زیرنویس خاموش است"}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Transport */}
      <div className="card px-5 py-4">
        {/* Progress */}
        <div className="group relative flex h-6 cursor-pointer items-center">
          <div className="relative h-1.5 w-full rounded-full bg-track/50 transition-all group-hover:h-2">
            <div
              className="absolute inset-y-0 right-0 rounded-full bg-brand-deep"
              style={{ width: `${progress}%` }}
            />
            {(session.chapters || []).map((chapter) => (
              <span
                key={chapter.index}
                title={chapter.title}
                className="absolute top-1/2 h-2.5 w-px -translate-y-1/2 bg-ink/25"
                style={{ right: `${(chapter.start / (total || 1)) * 100}%` }}
              />
            ))}
            <span
              className="pointer-events-none absolute top-1/2 h-3.5 w-3.5 -translate-y-1/2 translate-x-1/2 rounded-full bg-brand-deep opacity-0 shadow ring-2 ring-white transition-opacity group-hover:opacity-100"
              style={{ right: `${progress}%` }}
            />
          </div>
          <input
            type="range"
            min={0}
            max={total || 0}
            step={0.1}
            value={currentTime}
            onChange={(e) => seek(Number(e.target.value))}
            className="absolute inset-0 w-full cursor-pointer opacity-0"
            aria-label="جابجایی"
          />
        </div>

        <div className="mt-1 flex justify-between text-[11px] tabular-nums text-ink/45">
          <span>{formatClock(currentTime)}</span>
          <span>{formatClock(total)}</span>
        </div>

        {/* Controls */}
        <div className="mt-3 flex items-center justify-between gap-2">
          <button
            type="button"
            className={`btn-soft px-3 py-2 ${subtitlesOn ? "btn-active" : ""}`}
            onClick={() => setSubtitlesOn(!subtitlesOn)}
            disabled={!session.hasTranscript}
            aria-pressed={subtitlesOn}
            title="زیرنویس"
          >
            <CaptionsIcon className="h-5 w-5" />
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => seek(currentTime - 15)}
              className="icon-btn h-11 w-11"
              aria-label="۱۵ ثانیه عقب"
            >
              <Back15Icon className="h-6 w-6" />
            </button>
            <button
              type="button"
              onClick={togglePlay}
              className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-deep text-white shadow-lift transition hover:brightness-110 active:scale-95"
              aria-label={playing ? "توقف" : "پخش"}
            >
              {playing ? (
                <PauseIcon className="h-6 w-6" />
              ) : (
                <PlayIcon className="me-[-2px] h-6 w-6" />
              )}
            </button>
            <button
              type="button"
              onClick={() => seek(currentTime + 15)}
              className="icon-btn h-11 w-11"
              aria-label="۱۵ ثانیه جلو"
            >
              <Forward15Icon className="h-6 w-6" />
            </button>
          </div>

          <div className="relative" ref={speedRef}>
            <button
              type="button"
              className={`btn-soft px-3 py-2 ${rate !== 1 ? "btn-active" : ""}`}
              onClick={() => setSpeedOpen((v) => !v)}
              aria-label="سرعت پخش"
            >
              <SpeedIcon className="h-5 w-5" />
              <span className="text-xs tabular-nums">
                {toPersianDigits(rate)}×
              </span>
            </button>
            {speedOpen ? (
              <div className="absolute bottom-full left-0 z-20 mb-2 w-32 rounded-2xl border border-ink/5 bg-surface p-1.5 shadow-lift">
                {RATES.map((r) => (
                  <button
                    key={r}
                    type="button"
                    className={`block w-full rounded-xl px-3 py-2 text-right text-sm transition hover:bg-brand/30 ${
                      rate === r ? "bg-brand/40 font-bold" : ""
                    }`}
                    onClick={() => {
                      setRate(r);
                      setSpeedOpen(false);
                    }}
                  >
                    {toPersianDigits(r)}×
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        </div>

        <audio
          ref={audioRef}
          src={audioSrc || undefined}
          preload="metadata"
          onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => setPlaying(false)}
        />
      </div>

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <button
          type="button"
          className={`btn-soft ${inList ? "btn-active" : ""}`}
          onClick={() => {
            const next = toggleMyList({
              lecturer: session.lecturer,
              course: session.course,
              session: session.id,
              title: session.title,
            });
            setInList(
              next.some(
                (x) =>
                  x.lecturer === session.lecturer &&
                  x.course === session.course &&
                  x.session === session.id,
              ),
            );
          }}
        >
          <BookmarkIcon className="h-4 w-4" filled={inList} />
          {inList ? "در فهرست" : "فهرست من"}
        </button>
        <button type="button" className="btn-soft" onClick={share}>
          <ShareIcon className="h-4 w-4" />
          اشتراک
        </button>
        <button
          type="button"
          className="btn-soft"
          onClick={download}
          disabled={!session.audio}
        >
          <DownloadIcon className="h-4 w-4" />
          دانلود
        </button>
        <Link
          href={`/${session.lecturer}/${session.course}/${session.id}/text/`}
          className="btn-soft"
        >
          <TextIcon className="h-4 w-4" />
          متن کامل
        </Link>
        {(session.hasSummary ?? Boolean(session.summary)) && (
          <Link
            href={`/${session.lecturer}/${session.course}/${session.id}/summary/`}
            className="btn-soft"
          >
            خلاصه
          </Link>
        )}
      </div>

      {/* Chapters */}
      {session.chapters?.length ? (
        <section className="card overflow-hidden">
          <button
            type="button"
            className="flex w-full items-center justify-between gap-3 px-5 py-4 text-right"
            onClick={() => setShowChapters((v) => !v)}
            aria-expanded={showChapters}
          >
            <span className="section-title">فهرست مطالب</span>
            <span className="flex items-center gap-2 text-xs text-ink/45">
              {toPersianDigits(session.chapters.length)} سرفصل
              <ChevronIcon
                className={`h-4 w-4 transition-transform ${
                  showChapters ? "" : "rotate-180"
                }`}
              />
            </span>
          </button>
          {showChapters ? (
            <ul className="space-y-0.5 px-2.5 pb-3">
              {session.chapters.map((chapter) => {
                const active =
                  currentTime >= chapter.start &&
                  (chapter.end ? currentTime < chapter.end : true);
                return (
                  <li key={chapter.index}>
                    <button
                      type="button"
                      onClick={() => seek(chapter.start)}
                      className={`flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2.5 text-right text-sm transition ${
                        active
                          ? "bg-brand/40 font-semibold"
                          : "hover:bg-ink/[0.04]"
                      }`}
                    >
                      <span className="leading-6">{chapter.title}</span>
                      <span className="shrink-0 tabular-nums text-xs text-ink/40">
                        {formatClock(chapter.start)}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </section>
      ) : null}

      {/* Transcript */}
      {cues.length ? (
        <section className="card px-5 py-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="section-title">متن جلسه</h2>
            <div className="flex flex-wrap items-center gap-3 text-xs text-ink/55">
              <label className="flex cursor-pointer items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={autoFollow}
                  onChange={(e) => setAutoFollow(e.target.checked)}
                  className="accent-[rgb(var(--brand-deep))]"
                />
                دنبال‌کردن خودکار
              </label>
              <label className="flex cursor-pointer items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={hideTranslations}
                  onChange={(e) => setHideTranslations(e.target.checked)}
                  className="accent-[rgb(var(--brand-deep))]"
                />
                بدون ترجمه
              </label>
            </div>
          </div>
          <div
            ref={cueListRef}
            className="scroll-slim relative max-h-[26rem] space-y-0.5 overflow-y-auto pe-1"
          >
            {cues.map((cue, index) => {
              const active = index === cueIndex;
              return (
                <button
                  key={cue.i}
                  type="button"
                  data-cue={index}
                  onClick={() => seek(cue.start)}
                  className={`block w-full rounded-xl border-e-2 px-3 py-2 text-right text-sm leading-7 transition ${
                    active
                      ? "border-brand-deep bg-brand/35 font-medium"
                      : "border-transparent hover:bg-ink/[0.04]"
                  } ${cue.kind === "quote" ? "ayah" : ""}`}
                >
                  {cue.text}
                  {!hideTranslations && cue.translation ? (
                    <span className="mt-1 block font-ui text-xs text-ink/50">
                      {cue.translation}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>
        </section>
      ) : null}

      {/* Prev / next */}
      <nav className="flex items-center justify-between gap-3 pt-1">
        {session.previous ? (
          <Link
            href={`/${session.lecturer}/${session.course}/${session.previous}/`}
            className="btn-soft"
          >
            <ArrowRightIcon className="h-4 w-4" />
            جلسه قبل
          </Link>
        ) : (
          <span />
        )}
        {session.next ? (
          <Link
            href={`/${session.lecturer}/${session.course}/${session.next}/`}
            className="btn-soft"
          >
            جلسه بعد
            <ArrowLeftIcon className="h-4 w-4" />
          </Link>
        ) : (
          <span />
        )}
      </nav>
    </div>
  );
}
