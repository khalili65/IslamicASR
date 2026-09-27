#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { marked } from "marked";
import puppeteer from "puppeteer";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const mdPath = path.join(__dirname, "rahnama-virastaran.md");
const pdfPath = path.join(__dirname, "rahnama-virastaran.pdf");
const md = fs.readFileSync(mdPath, "utf8");

marked.setOptions({ gfm: true, breaks: false });
const body = marked.parse(md);

const html = `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <title>راهنمای ویراستاران</title>
  <style>
    @page { size: A4; margin: 18mm 16mm 20mm 16mm; }
    * { box-sizing: border-box; }
    body {
      font-family: "Vazirmatn", "Arial Unicode MS", Tahoma, sans-serif;
      font-size: 11pt;
      line-height: 1.75;
      color: #1a1a1a;
      background: #fff;
      margin: 0;
      padding: 0;
    }
    h1 {
      font-size: 20pt;
      font-weight: 800;
      margin: 0 0 0.6em;
      padding-bottom: 0.35em;
      border-bottom: 2px solid #e5e5e5;
      page-break-after: avoid;
    }
    h2 {
      font-size: 14pt;
      font-weight: 700;
      margin: 1.4em 0 0.5em;
      color: #222;
      page-break-after: avoid;
    }
    h3 {
      font-size: 12pt;
      font-weight: 700;
      margin: 1.1em 0 0.4em;
      page-break-after: avoid;
    }
    p { margin: 0.5em 0; }
    hr {
      border: none;
      border-top: 1px solid #ddd;
      margin: 1.2em 0;
    }
    strong { font-weight: 700; }
    code, pre {
      font-family: "SF Mono", Menlo, Consolas, monospace;
      font-size: 9pt;
      direction: ltr;
      text-align: left;
    }
    code {
      background: #f4f4f5;
      padding: 0.1em 0.35em;
      border-radius: 4px;
    }
    pre {
      background: #f8f8f8;
      border: 1px solid #e8e8e8;
      border-radius: 8px;
      padding: 0.8em 1em;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
      page-break-inside: avoid;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 0.8em 0 1em;
      font-size: 10pt;
      page-break-inside: avoid;
    }
    th, td {
      border: 1px solid #d4d4d8;
      padding: 0.45em 0.55em;
      vertical-align: top;
      text-align: right;
    }
    th {
      background: #f4f4f5;
      font-weight: 700;
    }
    ul, ol {
      margin: 0.4em 0 0.8em;
      padding-right: 1.4em;
      padding-left: 0;
    }
    li { margin: 0.25em 0; }
    li input[type="checkbox"] { margin-left: 0.4em; }
    em { color: #555; font-style: normal; font-size: 9.5pt; }
    a { color: #444; text-decoration: none; }
  </style>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap" rel="stylesheet" />
</head>
<body>${body}</body>
</html>`;

const browser = await puppeteer.launch({
  headless: true,
  args: ["--no-sandbox", "--disable-setuid-sandbox"],
});
try {
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: "networkidle0" });
  await page.pdf({
    path: pdfPath,
    format: "A4",
    printBackground: true,
    preferCSSPageSize: true,
  });
  console.log("Wrote", pdfPath);
} finally {
  await browser.close();
}
