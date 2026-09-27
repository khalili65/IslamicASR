"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { LecturerMeta } from "@/lib/content";
import type { SiteId } from "@/lib/sites";
import { mediaUrl, withSite } from "@/lib/sites";
import { PublishButton } from "@/components/PublishButton";
import { LogoutButton } from "@/components/LogoutButton";

export function LecturerEditor({
  site,
  slug,
  initial,
  courses,
}: {
  site: SiteId;
  slug: string;
  initial: LecturerMeta;
  courses: string[];
}) {
  const router = useRouter();
  const [form, setForm] = useState(initial);
  const [msg, setMsg] = useState("");
  const [saving, setSaving] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg("");
    const res = await fetch(withSite(`/api/lecturers/${slug}`, site), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setSaving(false);
    setMsg(res.ok ? "ذخیره شد." : "خطا در ذخیره.");
    router.refresh();
  }

  async function uploadAvatar(file: File) {
    const fd = new FormData();
    fd.set("file", file);
    const res = await fetch(withSite(`/api/lecturers/${slug}/avatar`, site), {
      method: "POST",
      body: fd,
    });
    const data = await res.json();
    if (data.avatar) {
      setForm((f) => ({ ...f, avatar: data.avatar }));
      setMsg("تصویر به‌روز شد.");
    }
  }

  const avatarSrc = mediaUrl(site, form.avatar);

  return (
    <main className="mx-auto max-w-2xl space-y-6 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <Link href="/dashboard" className="text-sm text-ink/55 hover:text-ink">
          ← بازگشت
        </Link>
        <div className="flex gap-2">
          <PublishButton site={site} />
          <LogoutButton />
        </div>
      </header>

      <form onSubmit={save} className="card space-y-4 p-5">
        <h1 className="text-xl font-black">ویرایش استاد</h1>
        <p className="text-xs font-mono text-ink/45">{site}</p>
        <div className="flex items-center gap-4">
          {avatarSrc ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={avatarSrc}
              alt=""
              className="h-20 w-20 rounded-2xl object-cover"
            />
          ) : null}
          <label className="btn-soft cursor-pointer text-sm">
            تغییر عکس
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) uploadAvatar(f);
              }}
            />
          </label>
        </div>
        <div>
          <label className="label">نام</label>
          <input
            className="input"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        </div>
        <div>
          <label className="label">عنوان کوتاه</label>
          <input
            className="input"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
        </div>
        <div>
          <label className="label">معرفی</label>
          <textarea
            className="input min-h-32"
            value={form.bio}
            onChange={(e) => setForm({ ...form, bio: e.target.value })}
          />
        </div>
        {msg ? <p className="text-sm text-brand-deep">{msg}</p> : null}
        <button type="submit" className="btn-primary" disabled={saving}>
          ذخیره
        </button>
      </form>

      <section className="card p-5">
        <h2 className="font-bold">درس‌ها</h2>
        <ul className="mt-2 space-y-1">
          {courses.map((c) => (
            <li key={c}>
              <Link
                href={`/sites/${site}/lecturers/${slug}/courses/${c}`}
                className="block rounded-lg px-2 py-2 hover:bg-brand/20"
              >
                {c}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
