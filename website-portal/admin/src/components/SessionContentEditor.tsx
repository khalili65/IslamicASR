"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import type { SessionDocKind } from "@/lib/content";
import type { SiteId } from "@/lib/sites";
import { withSite } from "@/lib/sites";
import { PublishButton } from "@/components/PublishButton";
import { LogoutButton } from "@/components/LogoutButton";

const LABELS: Record<SessionDocKind, { title: string; hint: string }> = {
  book: {
    title: "ویرایش نسخه کتابی",
    hint: "متن markdown — سرفصل‌ها با # و ##",
  },
  summary: {
    title: "ویرایش خلاصه",
    hint: "متن markdown خلاصهٔ جلسه",
  },
};

export function SessionContentEditor({
  site,
  lecturer,
  course,
  sessionId,
  sessionTitle,
  kind,
}: {
  site: SiteId;
  lecturer: string;
  course: string;
  sessionId: string;
  sessionTitle: string;
  kind: SessionDocKind;
}) {
  const router = useRouter();
  const labels = LABELS[kind];
  const [content, setContent] = useState("");
  const [saved, setSaved] = useState("");
  const [filePath, setFilePath] = useState<string | null>(null);
  const [writable, setWritable] = useState(true);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  const apiUrl = withSite(
    `/api/lecturers/${lecturer}/courses/${course}/sessions/${sessionId}/content/${kind}`,
    site,
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const res = await fetch(apiUrl);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.error || "بارگذاری ناموفق بود.");
      setLoading(false);
      return;
    }
    const data = await res.json();
    setContent(data.content);
    setSaved(data.content);
    setFilePath(data.path);
    setWritable(data.writable !== false);
    setLoading(false);
  }, [apiUrl]);

  useEffect(() => {
    load();
  }, [load]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setMsg("");
    setError("");
    const res = await fetch(apiUrl, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(data.error || "ذخیره ناموفق بود.");
      return;
    }
    setSaved(content);
    setFilePath(data.path || filePath);
    setMsg("ذخیره شد. برای دیدن در سایت «انتشار» بزنید.");
    router.refresh();
  }

  const dirty = content !== saved;

  return (
    <main className="mx-auto max-w-4xl space-y-4 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href={`/sites/${site}/lecturers/${lecturer}/courses/${course}`}
          className="text-sm text-ink/55 hover:text-ink"
        >
          ← بازگشت به جلسات
        </Link>
        <div className="flex gap-2">
          <PublishButton site={site} />
          <LogoutButton />
        </div>
      </header>

      <div className="card space-y-2 p-5">
        <p className="text-xs font-mono text-ink/45">
          {site} · {sessionId}
        </p>
        <h1 className="text-xl font-black">{labels.title}</h1>
        <p className="text-sm text-ink/60">{sessionTitle}</p>
        {filePath ? (
          <p className="break-all text-xs text-ink/40">{filePath}</p>
        ) : null}
        {!writable && !loading ? (
          <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-900">
            فقط خواندنی — فایل در Audios نیست. ویرایش روی سرور با دسترسی به
            Audios ممکن است.
          </p>
        ) : null}
      </div>

      {loading ? (
        <p className="text-sm text-ink/50">در حال بارگذاری…</p>
      ) : error && !content ? (
        <p className="text-sm text-red-700">{error}</p>
      ) : (
        <form onSubmit={save} className="card space-y-3 p-5">
          <p className="text-xs text-ink/50">{labels.hint}</p>
          <textarea
            className="input min-h-[28rem] font-mono text-[13px] leading-7"
            dir="rtl"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            disabled={!writable}
          />
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="submit"
              className="btn-primary"
              disabled={!writable || !dirty}
            >
              ذخیره
            </button>
            <button
              type="button"
              className="btn-soft"
              disabled={!dirty}
              onClick={() => setContent(saved)}
            >
              بازگردانی
            </button>
            <span className="text-xs text-ink/45">
              {content.length.toLocaleString("fa-IR")} نویسه
              {dirty ? " · تغییر ذخیره‌نشده" : ""}
            </span>
          </div>
          <p className="text-xs text-ink/45">
            قبل از ذخیره، نسخهٔ قبلی در همان پوشه با پسوند{" "}
            <span className="font-mono">.book.prev.md</span> /{" "}
            <span className="font-mono">.summary.prev.md</span> پشتیبان می‌شود.
          </p>
        </form>
      )}

      {msg ? <p className="text-sm text-brand-deep">{msg}</p> : null}
      {error && content ? (
        <p className="text-sm text-red-700">{error}</p>
      ) : null}
    </main>
  );
}
