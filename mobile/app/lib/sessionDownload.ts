import * as FileSystem from "expo-file-system/legacy";
import * as Print from "expo-print";
import * as Sharing from "expo-sharing";
import { markdownToHtml } from "@/lib/markdownToHtml";

export type DownloadFormat = "txt" | "pdf" | "audio";

export type DownloadItem = {
  key: string;
  label: string;
  /** Source URL: markdown/txt for docs, media URL for audio. */
  url: string;
  filename: string;
  format: DownloadFormat;
};

function safeName(name: string): string {
  return name.replace(/[/\\?%*:|"<>]/g, "-").trim() || "download";
}

function cachePath(filename: string): string {
  const root = FileSystem.cacheDirectory;
  if (!root) throw new Error("no cache directory");
  return `${root}${safeName(filename)}`;
}

async function shareLocalFile(
  uri: string,
  opts: { mimeType: string; uti?: string; dialogTitle: string },
): Promise<void> {
  const available = await Sharing.isAvailableAsync();
  if (!available) throw new Error("sharing unavailable");
  await Sharing.shareAsync(uri, {
    mimeType: opts.mimeType,
    UTI: opts.uti,
    dialogTitle: opts.dialogTitle,
  });
}

function pdfHtml(title: string, body: string): string {
  const safeTitle = title
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return `<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
<meta charset="utf-8" />
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    direction: rtl;
    text-align: right;
    line-height: 1.85;
    padding: 28px;
    color: #1c1917;
    font-size: 15px;
  }
  h1, h2, h3, h4 { margin: 1.1em 0 0.45em; line-height: 1.4; }
  h1 { font-size: 1.45em; }
  h2 { font-size: 1.25em; }
  p, li { margin: 0.55em 0; }
  blockquote {
    margin: 0.8em 0;
    padding: 0.4em 0.9em;
    border-right: 3px solid #a8a29e;
    color: #44403c;
  }
  hr { border: none; border-top: 1px solid #e7e5e4; margin: 1.4em 0; }
  .ayah-ar { font-size: 1.12em; line-height: 2; }
</style>
</head>
<body>
  <h1>${safeTitle}</h1>
  ${markdownToHtml(body)}
</body>
</html>`;
}

async function fetchText(url: string): Promise<string> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(String(res.status));
  return res.text();
}

/** Download item to a local file and open the system share sheet (Save to Files). */
export async function downloadSessionItem(
  item: DownloadItem,
  opts?: { title?: string },
): Promise<void> {
  const title = opts?.title || item.label;

  if (item.format === "audio") {
    const dest = cachePath(item.filename);
    const result = await FileSystem.downloadAsync(item.url, dest);
    await shareLocalFile(result.uri, {
      mimeType: "audio/mp4",
      uti: "public.mpeg-4-audio",
      dialogTitle: item.label,
    });
    return;
  }

  const raw = await fetchText(item.url);

  if (item.format === "txt") {
    const dest = cachePath(item.filename.replace(/\.md$/i, ".txt"));
    await FileSystem.writeAsStringAsync(dest, `\ufeff${raw}`, {
      encoding: FileSystem.EncodingType.UTF8,
    });
    await shareLocalFile(dest, {
      mimeType: "text/plain",
      uti: "public.plain-text",
      dialogTitle: item.label,
    });
    return;
  }

  // PDF — generate from markdown/text content (website print pages are not real PDF files)
  const { uri } = await Print.printToFileAsync({
    html: pdfHtml(title, raw),
  });
  const dest = cachePath(item.filename);
  try {
    await FileSystem.deleteAsync(dest, { idempotent: true });
  } catch {
    /* ok */
  }
  await FileSystem.copyAsync({ from: uri, to: dest });
  await shareLocalFile(dest, {
    mimeType: "application/pdf",
    uti: "com.adobe.pdf",
    dialogTitle: item.label,
  });
}
