"use client";

import { useCallback, useEffect, useState } from "react";
import type { SiteId } from "@/lib/sites";

type Step = {
  name: string;
  status: "pending" | "running" | "done" | "error";
  ok?: boolean;
  output?: string;
};

type PublishStatus = {
  state: "idle" | "running" | "ok" | "error";
  site?: string;
  deploy?: boolean;
  startedAt?: string;
  updatedAt: string;
  finishedAt?: string;
  phase: string;
  detail?: string;
  progress?: { current: number; total: number };
  steps: Step[];
  logTail: string;
  ok?: boolean;
};

function stepIcon(s: Step["status"]) {
  if (s === "done") return "✓";
  if (s === "error") return "✗";
  if (s === "running") return "…";
  return "·";
}

function elapsedLabel(startedAt?: string, finishedAt?: string) {
  if (!startedAt) return "";
  const end = finishedAt ? Date.parse(finishedAt) : Date.now();
  const ms = Math.max(0, end - Date.parse(startedAt));
  const sec = Math.floor(ms / 1000);
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m > 0 ? `${m} دقیقه و ${s} ثانیه` : `${s} ثانیه`;
}

export function PublishButton({ site }: { site: SiteId }) {
  const [deploy, setDeploy] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [status, setStatus] = useState<PublishStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/publish", { cache: "no-store" });
      if (!res.ok) return;
      const data = (await res.json()) as PublishStatus;
      setStatus(data);
      if (data.state === "running") setPanelOpen(true);
      return data;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (status?.state !== "running") return;
    const id = window.setInterval(() => {
      void refresh();
    }, 1500);
    return () => window.clearInterval(id);
  }, [status?.state, refresh]);

  async function run() {
    setError(null);
    setStarting(true);
    setPanelOpen(true);
    try {
      const res = await fetch("/api/publish", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ deploy, site }),
      });
      const data = await res.json();
      if (res.status === 409) {
        setError("یک انتشار دیگر در حال اجراست — وضعیت همان را نشان می‌دهیم.");
      } else if (!res.ok && !data?.started) {
        setError("شروع انتشار ناموفق بود.");
      }
      setStatus(data.status || (await refresh()));
    } catch {
      setError("ارتباط با سرور برقرار نشد.");
    } finally {
      setStarting(false);
    }
  }

  const running = status?.state === "running" || starting;
  const pct =
    status?.progress && status.progress.total > 0
      ? Math.min(
          100,
          Math.round((100 * status.progress.current) / status.progress.total),
        )
      : null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="flex items-center gap-1.5 text-xs text-ink/55">
        <input
          type="checkbox"
          checked={deploy}
          onChange={(e) => setDeploy(e.target.checked)}
          disabled={running}
        />
        آپلود Arvan
      </label>
      <button
        type="button"
        className="btn-primary text-sm"
        onClick={run}
        disabled={running}
      >
        {running ? "در حال انتشار…" : "انتشار"}
      </button>
      {status && status.state !== "idle" ? (
        <button
          type="button"
          className="btn-soft text-xs"
          onClick={() => setPanelOpen(true)}
        >
          وضعیت
        </button>
      ) : null}

      {panelOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="card max-h-[85vh] w-full max-w-lg overflow-auto p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-bold">وضعیت انتشار</h2>
                <p className="mt-1 text-xs text-ink/55">
                  {status?.site || site}
                  {status?.deploy ? " · با آپلود Arvan" : ""}
                  {status?.startedAt
                    ? ` · ${elapsedLabel(status.startedAt, status.finishedAt)}`
                    : ""}
                </p>
              </div>
              <span
                className={
                  status?.state === "running"
                    ? "rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800"
                    : status?.state === "ok"
                      ? "rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800"
                      : status?.state === "error"
                        ? "rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-800"
                        : "rounded-full bg-ink/10 px-2 py-0.5 text-xs"
                }
              >
                {status?.state === "running"
                  ? "در حال اجرا"
                  : status?.state === "ok"
                    ? "موفق"
                    : status?.state === "error"
                      ? "خطا"
                      : "—"}
              </span>
            </div>

            {error ? (
              <p className="mt-3 text-sm text-amber-800">{error}</p>
            ) : null}

            <p className="mt-3 text-sm font-medium">{status?.phase || "…"}</p>
            {status?.detail ? (
              <p className="mt-1 text-xs leading-5 text-ink/55" dir="ltr">
                {status.detail}
              </p>
            ) : null}

            {pct != null && status?.progress ? (
              <div className="mt-3">
                <div className="mb-1 flex justify-between text-xs text-ink/55">
                  <span>
                    {status.progress.current} / {status.progress.total}
                  </span>
                  <span>{pct}٪</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-ink/10">
                  <div
                    className="h-full rounded-full bg-ink transition-[width] duration-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            ) : running ? (
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-ink/10">
                <div className="h-full w-1/3 animate-pulse rounded-full bg-ink/40" />
              </div>
            ) : null}

            {status?.steps?.length ? (
              <ul className="mt-4 space-y-1.5 text-sm">
                {status.steps.map((s) => (
                  <li key={s.name} className="flex items-center gap-2">
                    <span className="w-4 text-center text-xs">
                      {stepIcon(s.status)}
                    </span>
                    <span
                      className={
                        s.status === "running"
                          ? "font-medium"
                          : s.status === "error"
                            ? "text-red-700"
                            : s.status === "pending"
                              ? "text-ink/40"
                              : ""
                      }
                    >
                      {s.name}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}

            <p className="mt-4 text-[11px] leading-5 text-ink/45">
              فقط همین سایت ساخته می‌شود (نه هر دو). با این حال کل صفحات همان
              سایت دوباره تولید می‌شوند. آپلود Arvan همگام‌سازی فضای ابری است و
              معمولاً طولانی‌ترین مرحله است.
            </p>

            {status?.logTail ? (
              <pre
                className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-xl bg-ink/5 p-3 text-[11px] leading-5"
                dir="ltr"
              >
                {status.logTail}
              </pre>
            ) : null}

            <button
              type="button"
              className="btn-soft mt-3 w-full"
              onClick={() => setPanelOpen(false)}
              disabled={false}
            >
              {running ? "ادامه در پس‌زمینه" : "بستن"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
