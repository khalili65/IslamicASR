import type { Metadata } from "next";
import "./globals.css";
import { getSiteIndex } from "@/lib/data";
import { SiteHeader } from "@/components/SiteHeader";
import { themeToCssVars } from "@/lib/theme";

export const metadata: Metadata = {
  title: "دروس سخنرانی",
  description: "پخش صوت و متن همگام جلسات",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const site = getSiteIndex();
  const cssVars = themeToCssVars(site.theme || {});
  const brandName = site.brand?.name || site.lecturers[0]?.name || "دروس";

  return (
    <html lang="fa" dir="rtl">
      <body>
        {cssVars ? (
          <style dangerouslySetInnerHTML={{ __html: `:root{${cssVars}}` }} />
        ) : null}
        <SiteHeader brandName={brandName} mode={site.mode} />
        <div className="mx-auto min-h-screen w-full max-w-3xl px-4 pb-24 pt-6">
          {children}
        </div>
        <footer className="pb-10 text-center text-xs text-ink/40">
          {brandName}
        </footer>
      </body>
    </html>
  );
}
