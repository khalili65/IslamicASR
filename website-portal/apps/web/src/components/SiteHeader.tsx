"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ListIcon, SearchIcon } from "@/components/Icons";

type Props = {
  brandName: string;
  mode: string;
};

const LINKS = [
  { href: "/search/", label: "جستجو", Icon: SearchIcon },
  { href: "/my-list/", label: "فهرست من", Icon: ListIcon },
];

export function SiteHeader({ brandName }: Props) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-white/50 bg-bg/70 backdrop-blur-lg">
      <div className="mx-auto flex h-16 max-w-3xl items-center justify-between gap-3 px-4">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-deep text-sm font-black text-white shadow-card">
            {brandName.trim().charAt(0) || "د"}
          </span>
          <span className="text-base font-extrabold tracking-tight">
            {brandName || "دروس"}
          </span>
        </Link>
        <nav className="flex items-center gap-1.5 text-sm">
          {LINKS.map(({ href, label, Icon }) => {
            const active = pathname?.startsWith(href.replace(/\/$/, ""));
            return (
              <Link
                key={href}
                href={href}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-2 font-medium transition ${
                  active
                    ? "bg-brand-deep text-white shadow-card"
                    : "text-ink/65 hover:bg-white/70 hover:text-ink"
                }`}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
