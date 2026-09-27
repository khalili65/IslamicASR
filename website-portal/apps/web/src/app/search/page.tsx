import { Suspense } from "react";
import fs from "fs";
import path from "path";
import { SearchClient, type SearchCatalog } from "@/components/SearchClient";
import { getSiteIndex } from "@/lib/data";

function loadCatalog(): SearchCatalog {
  const file = path.join(process.cwd(), "public", "data", "search", "catalog.json");
  if (fs.existsSync(file)) {
    return JSON.parse(fs.readFileSync(file, "utf8")) as SearchCatalog;
  }

  // Fallback if indexes not built yet: derive from site index only.
  const site = getSiteIndex();
  return {
    v: 1,
    lecturers: site.lecturers.map((l) => ({
      slug: l.slug,
      name: l.name,
      format: l.format,
      courses: l.courses.map((c) => ({
        slug: c.slug,
        title: c.title,
        format: c.format || l.format,
      })),
    })),
  };
}

export default function SearchPage() {
  const catalog = loadCatalog();

  if (!catalog.lecturers.length) {
    return <main className="py-10 text-center">دوره‌ای یافت نشد.</main>;
  }

  return (
    <Suspense
      fallback={
        <main className="py-10 text-center text-sm text-ink/50">
          در حال بارگذاری جستجو…
        </main>
      }
    >
      <SearchClient catalog={catalog} />
    </Suspense>
  );
}
