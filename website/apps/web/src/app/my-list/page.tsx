"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { loadMyList, type ListItem } from "@/lib/store";
import { BookmarkIcon, PlayIcon } from "@/components/Icons";

export default function MyListPage() {
  const [items, setItems] = useState<ListItem[]>([]);

  useEffect(() => {
    setItems(loadMyList());
  }, []);

  return (
    <main className="space-y-5">
      <h1 className="text-2xl font-black tracking-tight">فهرست من</h1>
      {!items.length ? (
        <div className="card space-y-3 px-6 py-14 text-center">
          <BookmarkIcon className="mx-auto h-8 w-8 text-ink/25" />
          <p className="text-sm text-ink/55">
            هنوز جلسه‌ای به فهرست اضافه نکرده‌اید.
          </p>
          <p className="text-xs text-ink/40">
            در صفحه پخش روی «فهرست من» بزنید تا جلسه اینجا ذخیره شود.
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={`${item.lecturer}-${item.course}-${item.session}`}>
              <Link
                href={`/${item.lecturer}/${item.course}/${item.session}/`}
                className="card-link group flex items-center gap-3 px-4 py-3.5"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-brand/45 text-brand-deep transition group-hover:bg-brand-deep group-hover:text-white">
                  <PlayIcon className="h-4 w-4" />
                </span>
                <div className="min-w-0">
                  <p className="truncate font-semibold">{item.title}</p>
                  <p className="mt-0.5 text-xs text-ink/45">
                    {item.course} · جلسه {item.session}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
