"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { CourseMeta, SessionRow } from "@/lib/content";
import type { SiteId } from "@/lib/sites";
import { withSite } from "@/lib/sites";
import { PublishButton } from "@/components/PublishButton";
import { LogoutButton } from "@/components/LogoutButton";

export function CourseEditor({
  site,
  lecturer,
  course,
  initial,
  sessions: initialSessions,
}: {
  site: SiteId;
  lecturer: string;
  course: string;
  initial: CourseMeta;
  sessions: SessionRow[];
}) {
  const router = useRouter();
  const [form, setForm] = useState(initial);
  const [sessions, setSessions] = useState(initialSessions);
  const [msg, setMsg] = useState("");

  async function saveCourse(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch(
      withSite(`/api/lecturers/${lecturer}/courses/${course}`, site),
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      },
    );
    setMsg(res.ok ? "درس ذخیره شد." : "خطا.");
    router.refresh();
  }

  async function patchSession(id: string, body: Record<string, unknown>) {
    const res = await fetch(
      withSite(
        `/api/lecturers/${lecturer}/courses/${course}/sessions/${id}`,
        site,
      ),
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    );
    if (res.ok) {
      const data = await res.json();
      setSessions(data.sessions);
    }
  }

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href={`/sites/${site}/lecturers/${lecturer}`}
          className="text-sm text-ink/55 hover:text-ink"
        >
          ← {lecturer}
        </Link>
        <div className="flex gap-2">
          <PublishButton site={site} />
          <LogoutButton />
        </div>
      </header>

      <form onSubmit={saveCourse} className="card space-y-3 p-5">
        <h1 className="text-xl font-black">ویرایش درس</h1>
        <p className="text-xs font-mono text-ink/45">{site}</p>
        <div>
          <label className="label">نام درس</label>
          <input
            className="input"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
        </div>
        <div>
          <label className="label">توضیح</label>
          <textarea
            className="input min-h-24"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </div>
        <button type="submit" className="btn-primary">
          ذخیره درس
        </button>
      </form>

      <section className="card p-5">
        <h2 className="font-bold">جلسات ({sessions.length})</h2>
        <p className="mt-1 text-xs text-ink/50">
          «مخفی» جلسه را از سایت حذف می‌کند (فایل صوتی پاک نمی‌شود). جلسات
          جدید از مسیر فنی (صوت + ASR) اضافه می‌شوند.
        </p>
        <ul className="mt-4 space-y-3">
          {sessions.map((s) => (
            <SessionRowEditor
              key={s.id}
              site={site}
              lecturer={lecturer}
              course={course}
              session={s}
              onSaveTitle={(title) => patchSession(s.id, { title })}
              onToggleHidden={(hidden) => patchSession(s.id, { hidden })}
            />
          ))}
        </ul>
      </section>

      {msg ? <p className="text-sm text-brand-deep">{msg}</p> : null}
    </main>
  );
}

function SessionRowEditor({
  site,
  lecturer,
  course,
  session,
  onSaveTitle,
  onToggleHidden,
}: {
  site: SiteId;
  lecturer: string;
  course: string;
  session: SessionRow;
  onSaveTitle: (title: string) => void;
  onToggleHidden: (hidden: boolean) => void;
}) {
  const [title, setTitle] = useState(session.title);
  const base = `/sites/${site}/lecturers/${lecturer}/courses/${course}/sessions/${session.id}/content`;

  return (
    <li
      className={`rounded-xl border p-3 ${session.hidden ? "border-ink/10 bg-ink/5 opacity-70" : "border-ink/10"}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-mono text-xs text-ink/45">{session.id}</span>
        {session.durationText ? (
          <span className="text-xs text-ink/45">{session.durationText}</span>
        ) : null}
      </div>
      <input
        className="input mt-2"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={() => {
          if (title !== session.title) onSaveTitle(title);
        }}
      />
      <div className="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          className="btn-soft text-xs"
          onClick={() => onSaveTitle(title)}
        >
          ذخیره عنوان
        </button>
        <button
          type="button"
          className="btn-soft text-xs"
          onClick={() => onToggleHidden(!session.hidden)}
        >
          {session.hidden ? "نمایش در سایت" : "مخفی کردن"}
        </button>
        {session.hasBook ? (
          <Link href={`${base}/book`} className="btn-soft text-xs">
            ویرایش کتاب
          </Link>
        ) : null}
        {session.hasSummary ? (
          <Link href={`${base}/summary`} className="btn-soft text-xs">
            ویرایش خلاصه
          </Link>
        ) : null}
      </div>
    </li>
  );
}
