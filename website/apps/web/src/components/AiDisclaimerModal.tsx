"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "ai-disclaimer-dismissed-v1";

export function AiDisclaimerModal() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    try {
      if (window.localStorage.getItem(STORAGE_KEY) === "1") return;
    } catch {
      /* private mode / blocked storage — still show once per page load */
    }
    setOpen(true);
  }, []);

  const dismiss = () => {
    try {
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      /* ignore */
    }
    setOpen(false);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-ink/45 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ai-disclaimer-title"
      onClick={dismiss}
    >
      <div
        className="animate-rise w-full max-w-lg rounded-card border border-white/70 bg-surface p-5 shadow-lift sm:p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          id="ai-disclaimer-title"
          className="text-lg font-extrabold tracking-tight"
        >
          دربارهٔ متن درس‌گفتارها
        </h2>
        <div className="mt-3 space-y-3 text-sm leading-7 text-ink/75">
          <p>
            متن این درس‌گفتارها با بهره‌گیری از فناوری هوش مصنوعی و بر اساس
            فایل‌های صوتی تهیه شده است. از آنجا که دقت پیاده‌سازی به کیفیت صدای
            هر جلسه وابسته است، ممکن است در بخش‌هایی از متن، خطاها یا ابهام‌های
            جزئی وجود داشته باشد.
          </p>
          <p>
            این متن‌ها با هدف دسترسی آسان‌تر و استفاده بهتر از محتوای
            درس‌گفتارها در اختیار شما قرار گرفته‌اند. می‌توانید پس از شنیدن هر
            جلسه، مطالب را در قالب متن مرور کنید، در میان آن‌ها جستجو کنید،
            نسخه‌ای برای مطالعه یا چاپ تهیه کنید و در صورت نیاز، بخش‌هایی را
            به‌صورت دستی اصلاح نمایید.
          </p>
          <p>
            همچنین تلاش می‌کنیم با بهبود فناوری و بازبینی محتوا، به‌مرور
            نسخه‌های دقیق‌تر و کامل‌تری از متن‌ها ارائه کنیم.
          </p>
          <p>
            امیدواریم این امکان، مطالعه، مرور و بهره‌مندی از محتوای درس‌گفتارها
            را برای شما ساده‌تر و مفیدتر کند.
          </p>
        </div>
        <div className="mt-5 flex justify-end">
          <button type="button" onClick={dismiss} className="btn-primary">
            متوجه شدم
          </button>
        </div>
      </div>
    </div>
  );
}
