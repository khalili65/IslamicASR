"use client";

import Link from "next/link";
import type { SessionPayload } from "@/lib/types";
import { toPersianDigits } from "@/lib/format";
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  BookIcon,
  ShareIcon,
  TextIcon,
} from "@/components/Icons";

type Props = {
  session: SessionPayload;
  html: string;
  articleClassName: string;
};

export function TextReader({ session, html, articleClassName }: Props) {
  const share = async () => {
    const url = typeof window !== "undefined" ? window.location.href : "";
    if (navigator.share) {
      try {
        await navigator.share({ title: session.title, url });
        return;
      } catch {
        /* dismissed */
      }
    }
    await navigator.clipboard.writeText(url);
    alert("پیوند کپی شد");
  };

  return (
    <div className="space-y-5">
      <header className="animate-rise space-y-2">
        <Link
          href={`/${session.lecturer}/${session.course}/`}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-ink/50 transition hover:text-brand-deep"
        >
          <ArrowRightIcon className="h-3.5 w-3.5" />
          بازگشت به فهرست فصول
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <span className="chip-brand">
            فصل {toPersianDigits(session.index)}
          </span>
          <span className="chip">
            <BookIcon className="h-3.5 w-3.5" />
            متن‌خوانی
          </span>
        </div>
        <h1 className="text-2xl font-extrabold leading-9 tracking-tight">
          {session.title}
        </h1>
        {session.topic ? (
          <p className="text-sm leading-7 text-ink/60">{session.topic}</p>
        ) : null}
      </header>

      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={share} className="btn-soft">
          <ShareIcon className="h-4 w-4" />
          اشتراک
        </button>
        <a
          href={`/data/${session.lecturer}/${session.course}/${session.id}.raw.txt`}
          download={`${session.id}.txt`}
          className="btn-soft"
        >
          <TextIcon className="h-4 w-4" />
          دانلود متن
        </a>
      </div>

      <article
        className={`${articleClassName} animate-rise`}
        dangerouslySetInnerHTML={{ __html: html }}
      />

      <nav className="flex flex-wrap items-center justify-between gap-3 pt-2">
        {session.previous ? (
          <Link
            href={`/${session.lecturer}/${session.course}/${session.previous}/`}
            className="btn-soft"
          >
            <ArrowRightIcon className="h-4 w-4" />
            فصل قبل
          </Link>
        ) : (
          <span />
        )}
        {session.next ? (
          <Link
            href={`/${session.lecturer}/${session.course}/${session.next}/`}
            className="btn-soft"
          >
            فصل بعد
            <ArrowLeftIcon className="h-4 w-4" />
          </Link>
        ) : (
          <span />
        )}
      </nav>
    </div>
  );
}
