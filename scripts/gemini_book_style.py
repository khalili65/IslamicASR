#!/usr/bin/env python3
"""Turn raw ASR transcripts into book-style Markdown via Gemini's web UI (Pro).

Same pipeline as scripts/chatgpt_book_style.py, but drives gemini.google.com
with your logged-in Google session (subscription, not API). Default model is
**Pro** — not Flash/Fast.

Pipeline (see prompts/lecture-transcript-pipeline.md):
  1. ElevenLabs ASR → *.txt (raw, never overwritten)
  2. This script → *.book.md (citations, clarity, drop Q&A, Farsi under Arabic, polish)
  3. --summarize → *.summary.md

Usage:
    python scripts/gemini_book_style.py --login
    python scripts/gemini_book_style.py Audios/Qasemian/InsaneKamel --dry-run
    python scripts/gemini_book_style.py Audios/Qasemian/InsaneKamel --only 001
    python scripts/gemini_book_style.py Audios/Qasemian/InsaneKamel --jobs 2
    python scripts/gemini_book_style.py Audios/Qasemian/InsaneKamel --summarize

By default the script reads raw `*.txt` (strips `--- Segments ---`). Use
`--input cleaned` for legacy `*.cleaned.txt` files.

Each lecture opens one new chat, sends the transcript in chunks, and writes
`*.book.md`. Chunk replies are cached in `.book_parts_<stem>/` for resume.

Setup:
    pip install playwright
    playwright install chromium

`--login` saves the session in ~/.gemini_playwright_profile. The window stays
visible — Gemini often blocks or throttles headless traffic.

If the composer or reply selectors break, pass --composer-selector /
--assistant-selector instead of editing this file.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULT_PROFILE = Path.home() / ".gemini_playwright_profile"
GEMINI_URL = "https://gemini.google.com/app"

# Prefer Pro. Flash/Fast are rejected by select_pro_model().
DEFAULT_MODEL = "Pro"
FLASH_MARKERS = ("flash", "fast")

# Quill / rich-textarea composer (order matters).
COMPOSER_SELECTORS = (
    '.ql-editor[contenteditable="true"]',
    'rich-textarea div[contenteditable="true"]',
    'div[contenteditable="true"][data-placeholder]',
    'div[contenteditable="true"].ql-editor',
    '[role="textbox"][contenteditable="true"]',
)
SEND_SELECTORS = (
    'button[aria-label="Send message"]',
    'button[aria-label*="Send message"]',
    'button[aria-label*="Send"]',
    'button[aria-label*="ارسال"]',
    'button[data-mat-icon-name="send"]',
    'button[data-mat-icon-name="arrow_upward"]',
    "button.send-button",
)
STOP_SELECTORS = (
    'button[aria-label*="Stop"]',
    'button[aria-label*="توقف"]',
    'button[aria-label*="Cancel"]',
)
# Prefer message-content .markdown; Gemini remounts nodes mid-stream.
ASSISTANT_SELECTORS = (
    "message-content .markdown",
    "message-content",
    "model-response .markdown",
    "model-response",
    ".model-response-text",
    ".markdown",
)
# The mode picker mounts after the composer, so a generic aria-haspopup match
# can hit the settings menu first; keep the specific selectors ahead of it.
MODEL_PICKER_SELECTORS = (
    'button[data-test-id="bard-mode-menu-button"]',
    'button[aria-label^="Open mode picker"]',
    'button[aria-label*="mode picker"]',
    'button[aria-label*="model"]',
    'button[aria-label*="Model"]',
)
NEW_CHAT_SELECTORS = (
    'button[aria-label*="New chat"]',
    'button[aria-label*="New conversation"]',
    'a[aria-label*="New chat"]',
    'button[aria-label*="گفتگوی جدید"]',
    'a[href="/app"]',
)
LOGIN_MARKERS = (
    'button:has-text("Sign in")',
    'a:has-text("Sign in")',
    'button:has-text("ورود")',
    'a:has-text("ورود")',
    # Guest CTA only — do NOT match accounts.google.com/SignOutOptions (signed-in avatar).
    'a[href*="accounts.google.com/ServiceLogin"]',
    'a[href*="accounts.google.com/v3/signin"]',
    'a[href*="accounts.google.com/signin"]',
)
RATE_LIMIT_SELECTORS = (
    '[role="dialog"]:has-text("limit")',
    '[role="dialog"]:has-text("try again")',
    '[role="dialog"]:has-text("Too many")',
    'text=/quota|rate limit|try again later/i',
)

OUTPUT_SUFFIX = ".book.md"
SUMMARY_SUFFIX = ".summary.md"
PARTS_PREFIX = ".book_parts_"
SUMMARY_PARTS_PREFIX = ".summary_parts_"
SEGMENTS_MARKER = "--- Segments ---"

DERIVED_TXT_SUFFIXES = (
    ".corrected.txt",
    ".cleaned.txt",
    ".partial.txt",
    ".rawbak",
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟؛])\s+")

STYLE_RULES = """این متن، پیاده‌سازیِ ماشینی (ASR) از گفتارِ یک استاد در جلسهٔ درس/سخنرانی فارسی است. آن را به یک فایل **مطالعهٔ کتابی** به‌صورت Markdown تبدیل کن.

## کارهایی که باید انجام دهی

### ۱) اصلاحِ ارجاعات و **آوردنِ متن عربی آیات**
- آیات قرآن، احادیث، نهج‌البلاغه، ادعیه و نقل‌های عربی/کلاسیک را وقتی قابل‌شناسایی‌اند اصلاح کن.
- نام سوره، شماره آیه، «صلوات»، «علیه‌السلام» و عبارات مذهبیِ mangled را درست کن.
- برای هر نقلِ مهم **جست‌وجوی وب** بزن و متن معتبر را بیار (tanzil.net، quran.com، منابع معتبر). روی حافظه تکیه نکن.

#### آوردن عربی وقتی استاد دربارهٔ آیه حرف می‌زند (حتی اگر عربی نخوانده)
- اگر استاد **دربارهٔ یک آیه** صحبت می‌کند — با اشاره به سوره/شماره آیه، مضمون، ترجمهٔ شفاهی، یا تکه‌عبارت عربی — باید **متن عربی استاندارد همان آیه** را در همان محل بحث بیاوری (با قالب HTML زیر)، نه فقط ترجمه یا توضیح فارسی.
- نشانه‌های رایج: «آیهٔ … سورهٔ …»، «در قرآن می‌فرماید»، «خداوند می‌گوید»، نقل مضمون آیه، یا اشاره به آیه‌ای که جلسهٔ قبل خوانده شده.
- برای آیهٔ شناسایی‌شده: (۱) بلوک عربی کامل آیه، (۲) `<span class="ayah-ref">` با نام سوره و شماره، (۳) بلافاصله زیرش ترجمهٔ مدل با برچسب.
- اگر استاد فقط **تکهٔ کوتاهی** از آیه را خوانده ولی آیه مشخص است، **کل همان آیه** را بیاور (نه کل سوره).
- اگر چند آیهٔ پشت‌سرهم را بحث می‌کند، همان چند آیه را بیاور — سوره را یکجا dump نکن.
- حدیث / نهج / دعا: فقط همان بخشی را که استاد خوانده یا صریحاً به آن ارجاع داده بازسازی کن؛ بی‌دلیل طولانی نکن.
- آیه‌ای که استاد به آن **اصلاً اشاره نکرده** نیاور.

> **ممنوع:** نوشتن «ترجمهٔ فارسی (توسط مدل، نه استاد): …» بدون آنکه بلافاصله **بالای آن** متن عربی آیه/روایت آمده باشد. ترجمهٔ بدون عربی خطای جدی است. هر برچسب ترجمه باید دقیقاً زیر یک بلوک عربی باشد.

#### گامِ اجباری: اول فهرستِ آیات را دربیاور
پیش از نوشتنِ خروجی، کلِ متن را یک بار بخوان و **فهرستی از هر آیه‌ای که استاد دربارهٔ آن حرف می‌زند** بساز — حتی اگر عربی‌اش را نخوانده باشد.
- استاد اغلب فقط **مضمون** آیه را نقل می‌کند یا به ماجرای آن اشاره می‌کند؛ این هم «اشاره به آیه» است و آوردنِ عربی‌اش **الزامی** است.
- نمونهٔ اشارهٔ ضمنی: «ماجرای در میان گذاشتنِ خلقتِ آدم با فرشتگان» ← بقره/۳۰ ؛ «تعلیم اسماء به آدم» ← بقره/۳۱ ؛ «آیاتِ جلسهٔ قبل از سورهٔ نور» ← همان آیه.
- برای هر موردِ فهرست، بلوکِ `<p class="ayah-ar" …>` با متنِ کاملِ عربی + `<span class="ayah-ref">` + ترجمهٔ برچسب‌دار بگذار.
- اگر در بخشی دربارهٔ آیه‌ای بحث شده و عربی‌اش را نیاورده‌ای، آن بخش **ناقص** است.

### ۲) ویرایشِ وضوح (بدون تغییرِ فکر استاد)
- ایده، استدلال، ترتیب مطالب، مثال‌ها و داستان‌های **استاد** را حفظ کن.
- garble سنگین ASR را به فارسیِ روان تبدیل کن (می‌گه ← می‌گوید، اینو ← این را).
- پرکننده‌های بی‌معنا («خب»، «دیگه»، لکنت، تکرار) را کم کن؛ محتوای علمی/معنوی را نه.

### ۳) حذفِ کاملِ گفتارِ حاضران (فقط صدای استاد بماند)
- **فقط monologue استاد** در خروجی باشد — انگار فقط یک نوارِ صوتی از سخنرانی استاد را می‌خوانی.
- **حذف کن (کامل، بدون بازنویسی):**
  - هر سؤال، جواب، یا حرفِ دانشجو / حاضر / سالن
  - «بلند بگویید»، «جان؟»، «خواهرها چه گفتند؟»، «احسنت»، شوخی با جمع
  - گفت‌وگوی دونفره یا چندنفرهٔ جانبی
  - متنِ ASRِ نامفهوم که clearly از میکروفونِ دور یا صدای مخاطب است — **بازسازی نکن**؛ همان بخش را حذف کن
  - نشانه‌هایی مثل `[صدای …]`، `[پخش …]`، `[خنده]` وقتی مربوط به مخاطب است
- **نگه دار:** وقتی **خودِ استاد** سؤال می‌پرسد و خودش جواب می‌دهد (بحث درسی).
- اگر استاد خلاصهٔ سؤالِ مخاطب را تکرار می‌کند و بعد پاسخ می‌دهد، **فقط پاسخِ استاد** (و تکرارِ خلاصه در صورت نیاز) بماند؛ متنِ خامِ سؤالِ مخاطب نیاید.

### ۴) ترجمهٔ فارسی زیر عربی
- زیر هر بلوک عربی (به‌ویژه آیاتِ درج‌شده)، این برچسب را بگذار:
  > **ترجمهٔ فارسی (توسط مدل، نه استاد):** …
- در ابتدای فایل (بخش اول) یک یادداشت کوتاه: ترجمه‌های زیرِ عربی توسط **مدل** است نه استاد؛ متن عربی آیات از منابع معتبر درج شده است.

### ۵) قالب Markdown
- با `##` / `###` بر اساس جریان جلسه بخش‌بندی کن.
- آیات را با فونت بزرگ‌تر HTML بنویس، مثلاً:
  ```html
  <p class="ayah-ar" dir="rtl" style="font-size:1.5em; line-height:2.1; font-family: Amiri, 'Scheherazade New', 'Noto Naskh Arabic', serif;">
  «…» <span class="ayah-ref">(نور/۲)</span>
  </p>
  ```
- در **بخش آخر** یک پاورقی: منبع ASR، ترجمه‌ها از مدل، آیات عربی از منبع معتبر، پرسش‌وپاسخ حذف شده، Segments نیست.

## قواعد سخت
- **خلاصه نکن.** این فایل مطالعه است نه digest (خلاصه جداگانه می‌آید).
- این «بازنویسیِ کامل» است، نه بازگوییِ فشرده: تک‌تکِ جمله‌های استاد باید به فارسیِ کتابی منتقل شود.
- هیچ مثال، حکایت، طعنه، پرسشِ بلاغی، تکرارِ تأکیدی یا تعبیرِ عامیانهٔ استاد را حذف نکن؛ همان را کتابی بنویس.
- لحن و صدای گویندهٔ اصلی حفظ شود؛ به نثرِ گزارشیِ خنثی تبدیلش نکن.
- خروجی معمولاً باید از متنِ ورودی **بلندتر** باشد (حدود ۱.۵ تا ۲ برابر)، نه کوتاه‌تر.
- آیه/حدیثی که استاد به آن اشاره نکرده **اختراع نکن**؛ ولی برای آیه‌ای که بحث کرده، آوردن عربیِ استاندارد **الزامی** است حتی اگر در ASR عربی کامل نباشد.
- خروجی **فقط Markdown ویرای‌شده** — بدون «البته من … کردم»، بدون توضیح دربارهٔ دستورالعمل.
- اگر جایی نامفهوم است، همان معنا را روان بنویس؛ حدسِ جدید نزن.

## قالبِ پاسخ (بسیار مهم)
تمام خروجی را **داخل یک بلوکِ کدِ markdown** بگذار تا سورس خام (بدون رندر شدن) منتقل شود:

````
```markdown
## عنوان بخش
متن…

<p class="ayah-ar" dir="rtl" style="font-size:1.5em; line-height:2.1; font-family: Amiri, 'Scheherazade New', 'Noto Naskh Arabic', serif;">
«إِنَّا أَنزَلْنَاهُ فِي لَيْلَةِ الْقَدْرِ» <span class="ayah-ref">(قدر/۱)</span>
</p>

> **ترجمهٔ فارسی (توسط مدل، نه استاد):** …
```
````

- هیچ متنی **بیرون** از این بلوک ننویس (نه مقدمه، نه توضیح، نه «بفرمایید»).
- علائم Markdown مثل `##`، `>` و تگ‌های HTML باید **عیناً** داخل بلوک بمانند.

متن در {total} بخش پشت‌سرهم می‌آید. هر بخش را جداگانه ویرایش کن و **فقط** خروجی همان بخش را در یک بلوک ```markdown بده، سپس منتظر بخش بعد بمان."""

SUMMARY_RULES = """این متن، نسخهٔ **کتابیِ ویرای‌شده** از یک جلسهٔ درس/سخنرانی فارسی است (`*.book.md`). یک فایل خلاصهٔ Markdown بنویس.

## ساختار خروجی (دقیقاً این سرعنوان‌ها)

## خلاصهٔ کوتاه
۵–۱۰ جمله: موضوع جلسه و پیام اصلی.

## فهرست مطالب
فهرست bullet از بخش‌های جلسه (هم‌تراز با عناوین book.md).

## نکات کلیدی
۸–۱۵ bullet: ادعاها، توصیه‌ها، هشدارها، اعمالی که استاد تأکید کرد.

## اصطلاحات و منابع
(فقط اگر در جلسه بود) اصطلاحات فنی + کتاب/مرجع نام‌برده.

---
> خلاصه توسط **مدل** از متن کتابیِ جلسه — نقل مستقیم طولانی از عربی لازم نیست.

## قواعد
- فقط از روی متن؛ چیز جدید اختراع نکن.
- آیات/روایات را دوباره طولانی نقل نکن.
- فارسی روان و فشرده.

## قالبِ پاسخ (بسیار مهم)
کل خروجی را داخل یک بلوکِ کدِ ```markdown بگذار تا سورس خام منتقل شود و هیچ متنی بیرون آن ننویس."""

CHUNK_HEADER = "بخش {index} از {total} — با همان قواعد ویرایش کن و فقط Markdownِ ویرای‌شدهٔ همان بخش را بده:"
SUMMARY_HEADER = "متن کاملِ جلسه — خلاصهٔ Markdown بنویس (فقط خروجی خلاصه، بدون مقدمه):"
RESUME_NOTE = (
    "برای پیوستگی، پایانِ بخشِ ویرایش‌شدهٔ پیشین را می‌آورم. آن را بازنویسی نکن و "
    "در خروجی تکرارش نکن؛ فقط لحن و ادامهٔ مطلب را با آن هم‌آهنگ کن:"
)

# Quill ignores fill()/synthetic InputEvents. execCommand('insertText') works, but
# a single huge paste often truncates — so we insert in slices and verify length.
_EDITOR_JS = """() => {
    return document.querySelector('.ql-editor[contenteditable="true"]')
        || document.querySelector('rich-textarea div[contenteditable="true"]')
        || document.querySelector('div[contenteditable="true"][data-placeholder]')
        || document.querySelector('[role="textbox"][contenteditable="true"]');
}"""

_CLEAR_EDITOR_JS = """() => {
    const editor = document.querySelector('.ql-editor[contenteditable="true"]')
        || document.querySelector('rich-textarea div[contenteditable="true"]')
        || document.querySelector('div[contenteditable="true"][data-placeholder]')
        || document.querySelector('[role="textbox"][contenteditable="true"]');
    if (!editor) return false;
    editor.focus();
    const sel = window.getSelection();
    sel.removeAllRanges();
    const range = document.createRange();
    range.selectNodeContents(editor);
    sel.addRange(range);
    document.execCommand('selectAll', false);
    document.execCommand('delete', false);
    // Quill often leaves an empty <p><br></p>; that's fine.
    return true;
}"""

_INSERT_TEXT_CHUNKED_JS = """(text) => {
    const editor = document.querySelector('.ql-editor[contenteditable="true"]')
        || document.querySelector('rich-textarea div[contenteditable="true"]')
        || document.querySelector('div[contenteditable="true"][data-placeholder]')
        || document.querySelector('[role="textbox"][contenteditable="true"]');
    if (!editor) return { ok: false, reason: 'no-editor' };
    editor.focus();
    const sel = window.getSelection();
    const placeCaretAtEnd = () => {
        sel.removeAllRanges();
        const range = document.createRange();
        range.selectNodeContents(editor);
        range.collapse(false);
        sel.addRange(range);
    };
    placeCaretAtEnd();
    // One-shot first (fast path).
    if (document.execCommand('insertText', false, text)) {
        const got = (editor.innerText || '').trim().length;
        if (got >= Math.floor(text.trim().length * 0.85)) {
            return { ok: true, method: 'oneshot', got };
        }
    }
    // Clear and retry in slices — large Persian/Markdown blobs truncate otherwise.
    document.execCommand('selectAll', false);
    document.execCommand('delete', false);
    placeCaretAtEnd();
    const slice = 1200;
    let inserted = 0;
    for (let i = 0; i < text.length; i += slice) {
        const piece = text.slice(i, i + slice);
        placeCaretAtEnd();
        if (!document.execCommand('insertText', false, piece)) {
            return { ok: false, reason: 'slice-failed', at: i, inserted };
        }
        inserted += piece.length;
    }
    const got = (editor.innerText || '').trim().length;
    return { ok: got >= Math.floor(text.trim().length * 0.85), method: 'chunked', got, inserted };
}"""

_INSTALL_RESPONSE_OBSERVER_JS = """(selectors) => {
    if (window.__islamAsrResponseObserver) {
        window.__islamAsrResponseObserver.disconnect();
    }
    window.__islamAsrInitialCounts = {};
    selectors.forEach(sel => {
        window.__islamAsrInitialCounts[sel] = document.querySelectorAll(sel).length;
    });
    window.__islamAsrBestResponse = { text: '', selector: '', length: 0 };

    const scan = () => {
        selectors.forEach(sel => {
            const els = Array.from(document.querySelectorAll(sel));
            const initial = window.__islamAsrInitialCounts[sel] || 0;
            els.slice(initial).forEach(el => {
                const text = el.innerText || el.textContent || '';
                if (text.length > window.__islamAsrBestResponse.length) {
                    window.__islamAsrBestResponse = {
                        text,
                        selector: sel,
                        length: text.length
                    };
                }
            });
        });
        return window.__islamAsrBestResponse;
    };

    scan();
    window.__islamAsrResponseObserver = new MutationObserver(scan);
    window.__islamAsrResponseObserver.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true
    });
    return window.__islamAsrInitialCounts;
}"""

# Gemini renders Markdown, so innerText of a reply loses `##`, `>` and any HTML
# (the Arabic ayah blocks). Code blocks are the one place the literal source
# survives, so we ask for a ```markdown fence and read <pre><code> directly.
_CODE_BLOCK_RESPONSE_JS = """(initialCount) => {
    const blocks = Array.from(document.querySelectorAll(
        'message-content pre code, model-response pre code, pre code, code-block pre'
    ));
    if (blocks.length <= initialCount) return { text: '', count: blocks.length };
    let best = '';
    blocks.slice(initialCount).forEach(el => {
        const t = el.innerText || el.textContent || '';
        if (t.length > best.length) best = t;
    });
    return { text: best, count: blocks.length };
}"""

_COUNT_CODE_BLOCKS_JS = """() => document.querySelectorAll(
    'message-content pre code, model-response pre code, pre code, code-block pre'
).length"""

_LONGEST_RESPONSE_JS = """(args) => {
    const [selectors, initialCounts] = args;
    let best = '';
    let selector = '';
    selectors.forEach(sel => {
        const els = Array.from(document.querySelectorAll(sel));
        const initial = initialCounts[sel] || 0;
        els.slice(initial).forEach(el => {
            const t = el.innerText || el.textContent || '';
            if (t.length > best.length) {
                best = t;
                selector = sel;
            }
        });
    });
    const observed = window.__islamAsrBestResponse || { text: '', selector: '', length: 0 };
    if ((observed.text || '').length > best.length) {
        return observed;
    }
    return { text: best, selector, length: best.length };
}"""


class BrowserFlowError(RuntimeError):
    """Raised when the page is not in the state the script expects."""


class RateLimitedError(BrowserFlowError):
    """Gemini kept showing a rate/quota dialog past the backoff budget."""


def log(message: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {message}", flush=True)


# --------------------------------------------------------------------------- #
# Transcript discovery and chunking (same contract as chatgpt_book_style.py)
# --------------------------------------------------------------------------- #


def is_derived_txt(path: Path) -> bool:
    name = path.name
    if not name.endswith(".txt"):
        return False
    return any(name.endswith(suffix) for suffix in DERIVED_TXT_SUFFIXES)


def transcript_stem(path: Path) -> str:
    for suffix in (".cleaned.txt", ".txt"):
        if path.name.endswith(suffix):
            return path.name[: -len(suffix)]
    return path.stem


def continuous_text(text: str) -> str:
    if SEGMENTS_MARKER in text:
        return text.split(SEGMENTS_MARKER, 1)[0].strip()
    return text.strip()


def find_transcripts(target: Path, input_kind: str) -> list[Path]:
    if target.is_file():
        if target.suffix == ".md" and target.name.endswith(".book.md"):
            return []
        if target.suffix == ".txt" and not is_derived_txt(target):
            return [target]
        if target.name.endswith(".cleaned.txt"):
            return [target]
        sys.exit(f"Not a transcript file: {target}")
    if not target.is_dir():
        sys.exit(f"Not found: {target}")

    found: list[Path] = []
    patterns = ("*.txt", "*/*.txt")
    if input_kind in ("cleaned", "auto"):
        patterns = ("*.cleaned.txt", "*/*.cleaned.txt") + patterns

    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(target.glob(pattern)):
            if not path.is_file() or path in seen:
                continue
            if path.name.endswith(".cleaned.txt"):
                seen.add(path)
                found.append(path)
            elif not is_derived_txt(path):
                seen.add(path)
                found.append(path)

    if input_kind == "raw":
        return [p for p in found if not p.name.endswith(".cleaned.txt")]
    if input_kind == "cleaned":
        return [p for p in found if p.name.endswith(".cleaned.txt")]
    by_stem: dict[str, Path] = {}
    for path in found:
        stem = transcript_stem(path)
        existing = by_stem.get(stem)
        if existing is None:
            by_stem[stem] = path
        elif path.name.endswith(".cleaned.txt") and not existing.name.endswith(".cleaned.txt"):
            continue
        else:
            by_stem[stem] = path
    return sorted(by_stem.values())


def find_book_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.name.endswith(".book.md") else []
    if not target.is_dir():
        sys.exit(f"Not found: {target}")
    return sorted(
        p
        for pattern in ("*.book.md", "*/*.book.md")
        for p in target.glob(pattern)
        if p.is_file()
    )


def book_stem(path: Path) -> str:
    return path.name[: -len(".book.md")]


def lecture_number(path: Path) -> int | None:
    match = re.match(r"(\d+)", path.parent.name)
    return int(match.group(1)) if match else None


def filter_transcripts(
    transcripts: list[Path],
    only: list[str],
    start: int | None,
    end: int | None,
) -> list[Path]:
    kept = []
    for path in transcripts:
        if only and not any(token in path.parent.name or token in path.name for token in only):
            continue
        number = lecture_number(path)
        if start is not None and (number is None or number < start):
            continue
        if end is not None and (number is None or number > end):
            continue
        kept.append(path)
    return kept


def split_paragraph(paragraph: str, budget: int) -> list[str]:
    pieces: list[str] = []
    buffer = ""
    for sentence in SENTENCE_SPLIT.split(paragraph):
        candidate = f"{buffer} {sentence}".strip() if buffer else sentence
        if len(candidate) <= budget or not buffer:
            buffer = candidate
        else:
            pieces.append(buffer)
            buffer = sentence
        while len(buffer) > budget:
            pieces.append(buffer[:budget])
            buffer = buffer[budget:]
    if buffer:
        pieces.append(buffer)
    return pieces


def split_chunks(text: str, budget: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for raw in text.splitlines():
        paragraph = raw.strip()
        if not paragraph:
            continue
        pieces = split_paragraph(paragraph, budget) if len(paragraph) > budget else [paragraph]
        for piece in pieces:
            if current and size + len(piece) > budget:
                chunks.append("\n\n".join(current))
                current, size = [], 0
            current.append(piece)
            size += len(piece) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def parts_dir(transcript: Path, prefix: str = PARTS_PREFIX) -> Path:
    stem = transcript_stem(transcript)
    return transcript.parent / f"{prefix}{stem[:60]}"


def part_path(transcript: Path, index: int, prefix: str = PARTS_PREFIX) -> Path:
    return parts_dir(transcript, prefix) / f"part_{index:03d}.md"


def output_path(transcript: Path, suffix: str) -> Path:
    return transcript.parent / (transcript_stem(transcript) + suffix)


def summary_output_path(book: Path) -> Path:
    return book.parent / (book_stem(book) + SUMMARY_SUFFIX)


def partial_suffix(suffix: str) -> str:
    base, dot, extension = suffix.rpartition(".")
    return f"{base}.partial{dot}{extension}" if dot else f"{suffix}.partial"


# --------------------------------------------------------------------------- #
# Browser plumbing
# --------------------------------------------------------------------------- #


def require_async_playwright():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        sys.exit(
            "Playwright is not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )
    return async_playwright


async def open_context(playwright, profile: Path, headless: bool, channel: str | None):
    profile.mkdir(parents=True, exist_ok=True)
    # Clear stale Singleton* locks left by crashed Chromes — otherwise the next
    # launch opens a throwaway profile and looks "signed out".
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        try:
            (profile / name).unlink(missing_ok=True)
        except OSError:
            pass

    kwargs = {
        "user_data_dir": str(profile),
        "headless": headless,
        "viewport": {"width": 1280, "height": 900},
        "device_scale_factor": 2,
        "args": ["--disable-blink-features=AutomationControlled"],
        # Playwright's defaults include --disable-sync, which makes Google
        # accounts drop on relaunch. Keep sync so Gemini stays signed in.
        "ignore_default_args": ["--disable-sync", "--enable-automation"],
    }
    if channel:
        kwargs["channel"] = channel
    try:
        context = await playwright.chromium.launch_persistent_context(**kwargs)
    except Exception as exc:  # noqa: BLE001
        if channel:
            log(f"Could not launch channel={channel!r} ({exc}); falling back to Chromium.")
            kwargs.pop("channel", None)
            context = await playwright.chromium.launch_persistent_context(**kwargs)
        else:
            raise
    try:
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        await context.grant_permissions(
            ["clipboard-read", "clipboard-write"], origin="https://gemini.google.com"
        )
    except Exception as exc:  # noqa: BLE001
        log(f"Could not grant clipboard permissions ({exc}).")
    return context


async def first_visible(page, selectors, timeout: float = 2000):
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible(timeout=timeout):
                return locator
        except Exception:  # noqa: BLE001
            continue
    return None


async def is_generating(page) -> bool:
    return await first_visible(page, STOP_SELECTORS, timeout=300) is not None


async def rate_limited(page) -> bool:
    return await first_visible(page, RATE_LIMIT_SELECTORS, timeout=200) is not None


async def ride_out_rate_limit(page, budget: float, tag: str = "") -> None:
    waited = 0.0
    pause = 30.0
    while waited < budget:
        # Best-effort dismiss of dialogs.
        for sel in (
            'button:has-text("Got it")',
            'button:has-text("OK")',
            'button:has-text("Dismiss")',
            'button:has-text("باشه")',
        ):
            btn = await first_visible(page, (sel,), timeout=200)
            if btn is not None:
                try:
                    await btn.click(timeout=2000, force=True)
                except Exception:  # noqa: BLE001
                    pass
        await page.wait_for_timeout(2000)
        if not await rate_limited(page):
            if waited:
                log(f"{tag}Rate/quota dialog cleared after {waited:.0f}s.")
            return
        log(f"{tag}Rate/quota limited; waiting {pause:.0f}s (used {waited:.0f}s of {budget:.0f}s).")
        await page.wait_for_timeout(int(pause * 1000))
        waited += pause + 2
        pause = min(pause * 1.5, 180.0)
    raise RateLimitedError(
        f"Gemini kept rate-limiting for {budget:.0f}s. Wait longer, then rerun with --jobs 1."
    )


async def wait_for_composer(
    page, selectors, timeout: float, login_grace: float = 8.0, rate_limit_budget: float = 600.0, tag: str = ""
):
    started = time.time()
    deadline = started + timeout
    while time.time() < deadline:
        if await rate_limited(page):
            await ride_out_rate_limit(page, rate_limit_budget, tag)
            deadline = time.time() + timeout
        composer = await first_visible(page, selectors, timeout=500)
        if composer is not None:
            # Guest Flash-Lite also has a composer + Sign in. Don't treat that as ready.
            if await first_visible(page, LOGIN_MARKERS, timeout=200) is not None:
                raise BrowserFlowError(
                    "Gemini is showing the login screen. Run again with --login and sign in to Google."
                )
            return composer
        if (
            time.time() - started >= login_grace
            and await first_visible(page, LOGIN_MARKERS, timeout=300) is not None
        ):
            raise BrowserFlowError(
                "Gemini is showing the login screen. Run again with --login and sign in to Google."
            )
        await page.wait_for_timeout(500)
    raise BrowserFlowError(
        "Could not find the message box on gemini.google.com. If the page looks fine, pass the "
        "right selector with --composer-selector."
    )


async def is_signed_in(page) -> bool:
    """True only when a real Google session is present — not guest Flash-Lite."""
    if await first_visible(page, LOGIN_MARKERS, timeout=400) is not None:
        return False
    # Guest landing page still has a composer; require no "Sign in" chrome in the body.
    try:
        head = (await page.locator("body").inner_text(timeout=2000))[:900]
    except Exception:  # noqa: BLE001
        head = ""
    if re.search(r"\bSign in\b", head) or "ورود" in head[:200]:
        return False
    if await first_visible(page, COMPOSER_SELECTORS, timeout=800) is None:
        return False
    # Strong signal: Google auth cookies on this context.
    try:
        cookies = await page.context.cookies()
        names = {c["name"] for c in cookies if "google" in c.get("domain", "")}
        if names & {"SID", "__Secure-1PSID", "SAPISID", "__Secure-3PSID"}:
            return True
    except Exception:  # noqa: BLE001
        pass
    # Soft pass: model picker visible and not stuck on Flash-Lite-only guest UI.
    label = await read_model_label(page)
    if label and not looks_like_lite(label):
        return True
    # Composer alone is not enough (guest mode).
    return False


async def wait_for_login(page, timeout: float) -> bool:
    deadline = time.time() + timeout
    announced = False
    while time.time() < deadline:
        if await is_signed_in(page):
            return True
        if not announced:
            log("Waiting for you to sign in to Google Gemini in the open browser window…")
            announced = True
        await page.wait_for_timeout(2000)
    return False


def looks_like_flash(label: str) -> bool:
    lower = label.lower()
    return any(marker in lower for marker in FLASH_MARKERS)


def looks_like_lite(label: str) -> bool:
    return "lite" in (label or "").lower()


def looks_like_pro(label: str, preferred: str) -> bool:
    lower = label.lower()
    pref = preferred.lower()
    # Prefer an exact-ish match. "3.7 Flash" must NOT match "Flash-Lite".
    if pref:
        if pref in lower and not (looks_like_lite(lower) and "lite" not in pref):
            return True
        # "Flash" alone is too broad when preferred is "3.7 Flash".
        if preferred.lower() == "flash" and "flash" in lower and not looks_like_lite(lower):
            return True
    if looks_like_flash(lower):
        return False
    return "pro" in lower


async def list_model_options(page) -> list[str]:
    """Open the model picker and return the option labels it offers."""
    # The mode pill hydrates well after the composer, so poll instead of a single probe.
    picker = None
    for _ in range(20):
        picker = await first_visible(page, MODEL_PICKER_SELECTORS, timeout=1500)
        if picker is not None:
            break
        await page.wait_for_timeout(1000)
    if picker is None:
        return []
    try:
        await picker.click(timeout=5000)
        await page.wait_for_timeout(1200)
    except Exception:  # noqa: BLE001
        return []
    labels: list[str] = []
    items = page.locator('[role="menuitemradio"], [role="menuitem"], [role="option"]')
    try:
        for i in range(await items.count()):
            text = " ".join((await items.nth(i).inner_text()).split())
            if text:
                labels.append(text)
    except Exception:  # noqa: BLE001
        pass
    try:
        await page.keyboard.press("Escape")
    except Exception:  # noqa: BLE001
        pass
    return labels


async def read_model_label(page) -> str:
    for selector in MODEL_PICKER_SELECTORS:
        try:
            loc = page.locator(selector).first
            if await loc.count() == 0:
                continue
            text = (await loc.inner_text()).strip()
            if text:
                return text
        except Exception:  # noqa: BLE001
            continue
    return ""


def resolve_rules(args) -> str:
    """STYLE_RULES plus any --extra-rules text appended."""
    extra = (getattr(args, "extra_rules", "") or "").strip()
    return f"{STYLE_RULES}\n\n{extra}\n" if extra else STYLE_RULES


GO_FILE = Path(os.environ.get("GEMINI_GO_FILE", "/tmp/gemini_go"))


async def wait_for_go_ahead(timeout: float = 1800.0) -> None:
    """Pause before the first send so a human can check the window.

    Uses the terminal when one is attached; otherwise waits for GO_FILE, so the
    pause also works when the script runs detached from a TTY.
    """
    if sys.stdin and sys.stdin.isatty():
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: input("Check the browser (model, captcha), then press Enter here… "),
        )
        return

    GO_FILE.unlink(missing_ok=True)
    log(f"Paused. Set the model in the window, then: touch {GO_FILE}")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if GO_FILE.exists():
            GO_FILE.unlink(missing_ok=True)
            log("Go-ahead received; sending the first message.")
            return
        await asyncio.sleep(2)
    raise BrowserFlowError(f"No go-ahead within {timeout:.0f}s (expected {GO_FILE}).")


async def select_pro_model(
    page,
    preferred: str,
    tag: str = "",
    allow_flash: bool = False,
    no_switch: bool = False,
) -> str:
    """Open the model menu and pick `preferred` (Pro unless --allow-flash)."""
    def rejected(label: str) -> bool:
        if looks_like_flash(label) and not allow_flash:
            return True
        # Even with --allow-flash, never settle on Flash-Lite when asking for 3.7 Flash.
        if looks_like_lite(label) and "lite" not in preferred.lower():
            return True
        return False

    if no_switch:
        # Whatever the user picked in the window wins; just report it.
        shown = await read_model_label(page)
        log(f"{tag}Model switching disabled; using the selected mode: {shown or 'unknown'!r}")
        return shown

    shown = await read_model_label(page)
    if shown and looks_like_pro(shown, preferred):
        log(f"{tag}Model already looks like {preferred}: {shown!r}")
        return shown

    picker = await first_visible(page, MODEL_PICKER_SELECTORS, timeout=2000)
    if picker is None:
        log(f"{tag}WARNING: could not find model picker; verify {preferred} is selected.")
        return shown

    try:
        await picker.click(timeout=5000)
        await page.wait_for_timeout(800)
    except Exception as exc:  # noqa: BLE001
        log(f"{tag}WARNING: could not open model picker ({exc}).")
        return shown

    option_queries = [preferred]
    if allow_flash or "flash" in preferred.lower():
        option_queries += ["3.7 Flash", "All-around help", "All-around"]
    if not allow_flash:
        option_queries += ["Pro", "Gemini Pro", "2.5 Pro", "3.1 Pro", "3 Pro", "Thinking"]
    # De-dupe while preserving order
    seen: set[str] = set()
    option_queries = [q for q in option_queries if not (q.lower() in seen or seen.add(q.lower()))]
    for label in option_queries:
        # Gemini's mode menu uses menuitemradio, so plain "menuitem" misses it.
        candidates = page.locator(
            '[role="menuitemradio"], [role="menuitem"], [role="option"]'
        ).filter(has_text=re.compile(re.escape(label), re.I))
        count = await candidates.count()
        for i in range(count):
            item = candidates.nth(i)
            try:
                text = " ".join((await item.inner_text()).split())
            except Exception:  # noqa: BLE001
                continue
            if rejected(text):
                continue
            if not looks_like_pro(text, preferred) and label.lower() not in text.lower():
                continue
            try:
                await item.click(timeout=5000)
                await page.wait_for_timeout(1000)
                shown = await read_model_label(page) or text
                log(f"{tag}Selected model: {shown!r}")
                if rejected(shown):
                    raise BrowserFlowError(
                        f"Model still looks like Flash/Fast after selection: {shown!r}. "
                        "Pick Pro manually in the window, then rerun with --confirm-first-send."
                    )
                return shown
            except BrowserFlowError:
                raise
            except Exception:  # noqa: BLE001
                continue

        # Fallback: any visible text node / button containing the label.
        loc = page.locator(f'text=/{re.escape(label)}/i').first
        try:
            if await loc.count() > 0 and await loc.is_visible(timeout=500):
                text = (await loc.inner_text()).strip()
                if rejected(text):
                    continue
                await loc.click(timeout=5000)
                await page.wait_for_timeout(1000)
                shown = await read_model_label(page) or text
                if rejected(shown):
                    continue
                log(f"{tag}Selected model via text match: {shown!r}")
                return shown
        except Exception:  # noqa: BLE001
            continue

    # Close menu with Escape if still open.
    try:
        await page.keyboard.press("Escape")
    except Exception:  # noqa: BLE001
        pass
    shown = await read_model_label(page) or shown
    if rejected(shown):
        raise BrowserFlowError(
            f"Active model looks like Flash/Fast ({shown!r}). Select Pro in the UI, then rerun."
        )
    log(
        f"{tag}WARNING: could not auto-select {preferred} (current label {shown!r}). "
        "Confirm the model in the browser window."
    )
    return shown


async def start_chat(
    page,
    model: str,
    selectors,
    timeout: float,
    tag: str = "",
    rate_limit_budget: float = 600.0,
    allow_flash: bool = False,
    no_switch: bool = False,
):
    await page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=120_000)
    await page.wait_for_timeout(1500)
    # Dismiss welcome / continue screens.
    for sel in (
        'button:has-text("Continue")',
        'button:has-text("Get started")',
        'button:has-text("Got it")',
        'button:has-text("I understand")',
        'button:has-text("ادامه")',
    ):
        btn = await first_visible(page, (sel,), timeout=400)
        if btn is not None:
            try:
                await btn.click(timeout=2000)
                await page.wait_for_timeout(800)
            except Exception:  # noqa: BLE001
                pass

    composer = await wait_for_composer(
        page, selectors, timeout, rate_limit_budget=rate_limit_budget, tag=tag
    )
    await dismiss_gemini_banners(page, tag)
    shown = await select_pro_model(
        page, model, tag, allow_flash=allow_flash, no_switch=no_switch
    )
    if shown and looks_like_flash(shown) and not (allow_flash or no_switch):
        raise BrowserFlowError(f"Refusing to run on Flash/Fast model: {shown!r}")
    return composer


def _composer_has_enough(current: str, expected: str) -> bool:
    """Quill normalizes newlines; require ~85% of non-whitespace length."""
    exp = len("".join(expected.split()))
    got = len("".join(current.split()))
    if exp == 0:
        return bool(got)
    return got >= int(exp * 0.85)


def _asr_anchor(chunk: str) -> str:
    """Stable snippet from the raw ASR body (not from the instruction header)."""
    compact = " ".join(chunk.split())
    if len(compact) <= 48:
        return compact
    # Prefer a mid-chunk window so we don't only match a shared bismillah prefix.
    start = min(80, max(0, len(compact) // 4))
    return compact[start : start + 48]


async def _nudge_composer_for_send(page) -> None:
    """Wake Angular/Quill so the Send button enables after programmatic insert.

    execCommand('insertText') fills the visible editor but often skips the
    framework's change detection, leaving Send disabled while text is on screen.
    """
    await page.evaluate(
        """() => {
            const editor = document.querySelector('.ql-editor[contenteditable="true"]')
                || document.querySelector('[role="textbox"][contenteditable="true"]');
            if (!editor) return;
            editor.focus();
            editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText' }));
            editor.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )
    # A real keystroke is what Gemini's enable-Send logic listens for.
    await page.keyboard.press(" ")
    await page.keyboard.press("Backspace")
    await page.wait_for_timeout(200)


async def fill_composer(
    page, composer, text: str, tag: str = "", must_contain: str | None = None
) -> None:
    """Put the full prompt (rules + raw ASR chunk) into Gemini's Quill editor.

    Gemini's editor ignores Playwright fill() and synthetic paste events. Prefer
    execCommand('insertText') in slices, then clipboard+Cmd/Ctrl+V, then
    keyboard.insert_text. Refuse to continue unless ~85% of the text landed —
    an earlier bug used min(80, …) and happily sent near-empty composers.
    """
    expected = text.strip()
    anchor = (must_contain or "").strip()
    if anchor and len(anchor) > 64:
        anchor = anchor[:64]
    await composer.click()
    await page.wait_for_timeout(150)
    await page.evaluate(_CLEAR_EDITOR_JS)
    await page.wait_for_timeout(100)

    result = await page.evaluate(_INSERT_TEXT_CHUNKED_JS, text)
    await page.wait_for_timeout(400)
    current = (await composer.inner_text()).strip()
    method = (result or {}).get("method", "execCommand")
    log(
        f"{tag}  composer after {method}: {len(current):,} / {len(expected):,} chars "
        f"(asr_anchor={'yes' if not anchor or anchor in current else 'no'})"
    )

    if not _composer_has_enough(current, expected) or (anchor and anchor not in current):
        # Trusted paste: write clipboard, then Meta/Ctrl+V (Quill honors real paste).
        log(f"{tag}  insert incomplete — trying clipboard paste…")
        await page.evaluate(_CLEAR_EDITOR_JS)
        await composer.click()
        try:
            await page.evaluate(
                """async (value) => {
                    await navigator.clipboard.writeText(value);
                    return true;
                }""",
                text,
            )
            await page.keyboard.press("Meta+V" if sys.platform == "darwin" else "Control+V")
            await page.wait_for_timeout(800)
        except Exception as exc:  # noqa: BLE001
            log(f"{tag}  clipboard paste failed ({exc}); trying keyboard.insert_text…")
            await page.evaluate(_CLEAR_EDITOR_JS)
            await composer.click()
            await page.keyboard.insert_text(text)
            await page.wait_for_timeout(500)
        current = (await composer.inner_text()).strip()
        log(
            f"{tag}  composer after fallback: {len(current):,} / {len(expected):,} chars "
            f"(asr_anchor={'yes' if not anchor or anchor in current else 'no'})"
        )

    if not current:
        raise BrowserFlowError("The message box stayed empty after inserting the text.")
    if not _composer_has_enough(current, expected):
        raise BrowserFlowError(
            f"Composer only kept {len(current)} of {len(expected)} chars — "
            "refusing to send an incomplete prompt (ASR would be missing)."
        )
    if anchor and anchor not in current:
        raise BrowserFlowError(
            f"Composer is missing the ASR anchor {anchor!r} — refusing to send. "
            "The rules header may have been pasted without the transcript body."
        )
    await _nudge_composer_for_send(page)


async def dismiss_gemini_banners(page, tag: str = "") -> None:
    """Dismiss Terms / cookie / onboarding banners that block Send."""
    for sel in (
        'button:has-text("Got it")',
        'button:has-text("I understand")',
        'button:has-text("Accept")',
        'button:has-text("Continue")',
        'button:has-text("Agree")',
        'button:has-text("باشه")',
        'button:has-text("متوجه شدم")',
    ):
        btn = await first_visible(page, (sel,), timeout=400)
        if btn is None:
            continue
        try:
            await btn.click(timeout=2000)
            log(f"{tag}Dismissed banner via {sel}")
            await page.wait_for_timeout(600)
        except Exception:  # noqa: BLE001
            pass


async def _click_send_button(page) -> str:
    """Click Gemini's Send control. Returns how it was clicked, or '' if not found."""
    try:
        await page.bring_to_front()
    except Exception:  # noqa: BLE001
        pass
    await dismiss_gemini_banners(page)

    candidates = [
        'gem-icon-button.send-button button[aria-label="Send message"]',
        'gem-icon-button.send-button.has-input button',
        'gem-icon-button.send-button',
        'button[aria-label="Send message"]',
        'button[aria-label*="Send message"]',
        'button[aria-label*="ارسال"]',
        'button[data-mat-icon-name="arrow_upward"]',
        *SEND_SELECTORS,
    ]
    for sel in candidates:
        try:
            btn = page.locator(sel).last
            if await btn.count() == 0:
                continue
            if not await btn.is_visible(timeout=500):
                continue
            disabled = await btn.get_attribute("disabled")
            aria_dis = await btn.get_attribute("aria-disabled")
            if disabled is not None or aria_dis in ("true", "True"):
                log(f"  Send found but disabled ({sel}); waiting…")
                await page.wait_for_timeout(1500)
                continue
            await btn.scroll_into_view_if_needed()
            # Prefer a normal Playwright click (trusted) on the inner button.
            try:
                await btn.click(timeout=3000)
                return f"playwright:{sel}"
            except Exception:  # noqa: BLE001
                pass
            box = await btn.bounding_box()
            if box:
                await page.mouse.click(
                    box["x"] + box["width"] / 2,
                    box["y"] + box["height"] / 2,
                )
                return f"mouse:{sel}"
        except Exception:  # noqa: BLE001
            continue

    clicked = await page.evaluate(
        """(sels) => {
            for (const sel of sels) {
                const nodes = [...document.querySelectorAll(sel)];
                const btn = nodes.reverse().find(b => {
                    const r = b.getBoundingClientRect();
                    return r.width > 0 && r.height > 0
                        && !b.disabled
                        && b.getAttribute('aria-disabled') !== 'true';
                });
                if (!btn) continue;
                btn.focus();
                btn.click();
                return sel;
            }
            return '';
        }""",
        candidates,
    )
    return f"dom:{clicked}" if clicked else ""


async def submit(page, composer, tag: str = "") -> None:
    # Install peak-text observer before clicking send (Gemini remounts reply nodes).
    await page.evaluate(_INSTALL_RESPONSE_OBSERVER_JS, list(ASSISTANT_SELECTORS))
    await page.evaluate(
        "(n) => { window.__islamAsrInitialCodeBlocks = n; }",
        await page.evaluate(_COUNT_CODE_BLOCKS_JS),
    )
    await _nudge_composer_for_send(page)

    # Hard requirement: click the Send button. Do NOT trust Enter — Quill treats
    # plain Enter as a newline, which is why prompts were sitting in the box.
    how = await _click_send_button(page)
    if how:
        log(f"{tag}  clicked Send ({how})")
        return

    log(f"{tag}  WARNING: Send button not found; falling back to Meta+Enter")
    await composer.click()
    await page.keyboard.press("Meta+Enter" if sys.platform == "darwin" else "Control+Enter")


def _strip_code_fence(text: str) -> str:
    """Unwrap a ```markdown … ``` fence, keeping inner fences intact."""
    body = text.strip()
    if not body.startswith("```"):
        return body
    lines = body.splitlines()
    lines = lines[1:]  # drop opening fence (with optional language tag)
    while lines and lines[-1].strip() == "```":
        lines.pop()
    return "\n".join(lines).strip()


async def code_block_reply(page) -> str:
    """Raw Markdown source from the reply's code fence (preserves ## and HTML)."""
    initial = await page.evaluate("() => window.__islamAsrInitialCodeBlocks || 0")
    result = await page.evaluate(_CODE_BLOCK_RESPONSE_JS, initial)
    return _strip_code_fence(str(result.get("text") or ""))


async def peak_reply_text(page) -> str:
    initial = await page.evaluate("() => window.__islamAsrInitialCounts || {}")
    result = await page.evaluate(_LONGEST_RESPONSE_JS, [list(ASSISTANT_SELECTORS), initial])
    return str(result.get("text") or "").strip()


async def last_reply_text(page, _assistant_selector: str = "") -> str:
    # A code fence carries the literal Markdown; rendered text loses it.
    try:
        fenced = await code_block_reply(page)
        if fenced:
            return _clean_model_reply(fenced)
    except Exception:  # noqa: BLE001  page mid-navigation
        pass
    # Fall back to the peak observer (survives remounts), then the last node.
    peak = await peak_reply_text(page)
    if peak:
        return _clean_model_reply(peak)
    for selector in ASSISTANT_SELECTORS:
        turns = page.locator(selector)
        try:
            if await turns.count() == 0:
                continue
            text = (await turns.last.inner_text()).strip()
            if text:
                return _clean_model_reply(text)
        except Exception:  # noqa: BLE001
            continue
    return ""


def _clean_model_reply(text: str) -> str:
    """Drop Gemini UI chrome that sometimes prefixes scraped replies."""
    cleaned = text.strip()
    for prefix in (
        "Gemini said",
        "Gemini said:",
        "Gemini:",
        "Model:",
        "Refining Transcription Format",
        "Thinking",
        "Loading…",
        "Loading...",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].lstrip("\n :")
    # Drop a lone UI status line if that's all we got.
    if cleaned.lower() in {"gemini said", "thinking", "loading", "refining transcription format"}:
        return ""
    return cleaned.strip()


ARABIC_LETTERS = re.compile(r"[\u0621-\u064A]")
TRANSLATION_LABEL = "ترجمهٔ فارسی"


def _reply_missing_arabic(reply: str) -> bool:
    """True when the model wrote translations but dropped the Arabic above them.

    Rendered-text scraping used to swallow the ayah HTML, and Gemini sometimes
    skips it outright; both show up as translation labels with no Arabic script.
    """
    if TRANSLATION_LABEL not in reply:
        return False
    for block in reply.split(TRANSLATION_LABEL)[:-1]:
        # Persian and Arabic share a block, so look for Arabic-only diacritics
        # or a decent run of Arabic letters just before each translation label.
        tail = block[-400:]
        if len(ARABIC_LETTERS.findall(tail)) >= 20:
            continue
        return True
    return False


def _reply_looks_usable(reply: str, chunk: str | None = None) -> bool:
    """Reject empty/UI-junk replies so we don't cache a 40-char stub as a part."""
    text = (reply or "").strip()
    if len(text) < 200:
        return False
    lower = text.lower()
    if lower in {"gemini said", "thinking"} or lower.startswith("refining transcription"):
        return False
    # Book edits should not shrink the ASR chunk to almost nothing.
    if chunk and len(chunk) > 800 and len(text) < max(200, int(len(chunk) * 0.12)):
        return False
    return True


ANSWER_NOW_SELECTORS = (
    'button:has-text("Answer now")',
    'button:has-text("پاسخ بده")',
    '[role="button"]:has-text("Answer now")',
)


async def click_answer_now(page) -> bool:
    """Skip Gemini's extended-thinking wait if it offers an 'Answer now' button."""
    button = await first_visible(page, ANSWER_NOW_SELECTORS, timeout=200)
    if button is None:
        return False
    try:
        await button.click(timeout=3000)
        return True
    except Exception:  # noqa: BLE001
        return False


async def wait_for_reply(
    page,
    assistant_selector: str,
    before_text: str,
    timeout: float,
    settle: float,
    tag: str = "",
    rate_limit_budget: float = 600.0,
) -> None:
    deadline = time.time() + timeout
    started = time.time()
    last_size = -1
    stable_since = None
    # Every reader is scoped to nodes added after submit(), so start empty.
    # Seeding with before_text would strand any reply shorter than the last one.
    peak = ""
    last_beat = 0.0
    answer_now_clicks = 0
    last_resend = 0.0

    while time.time() < deadline:
        if await rate_limited(page):
            await ride_out_rate_limit(page, rate_limit_budget, tag)
            deadline = time.time() + timeout
        generating = await is_generating(page)
        pending = ""
        try:
            box = await first_visible(page, COMPOSER_SELECTORS, timeout=200)
            if box is not None:
                pending = (await box.inner_text()) or ""
        except Exception:  # noqa: BLE001
            pass

        waited = time.time() - started
        if waited - last_beat >= 30:
            last_beat = waited
            log(
                f"{tag}    …waiting {waited:.0f}s (generating={generating}, "
                f"reply={len(peak):,} chars, composer={len(pending.strip()):,} chars)"
            )

        # Extended thinking can sit behind an "Answer now" button indefinitely.
        if waited >= 45:
            clicked = await click_answer_now(page)
            if clicked:
                answer_now_clicks += 1
                log(f"{tag}    clicked 'Answer now' (#{answer_now_clicks})")

        # False send: confirm_sent lied, prompt still in the box, nothing streaming.
        if (
            waited >= 20
            and not generating
            and len(pending.strip()) > 80
            and (waited - last_resend) >= 25
        ):
            last_resend = waited
            log(
                f"{tag}    send never landed ({len(pending.strip()):,} chars still in composer); "
                "clicking Send again"
            )
            try:
                await _nudge_composer_for_send(page)
                how = await _click_send_button(page)
                log(f"{tag}    resend via {how or 'FAILED'}")
                await page.wait_for_timeout(1500)
            except Exception as exc:  # noqa: BLE001
                log(f"{tag}    resend failed: {type(exc).__name__}: {exc}")
            continue

        if generating:
            last_size, stable_since = -1, None
            await page.wait_for_timeout(1000)
            continue

        current = await last_reply_text(page, assistant_selector)
        if current and len(current) > len(peak):
            peak = current
        # An exact match with before_text means we read a stale node, not a reply.
        if not peak or peak == before_text:
            await page.wait_for_timeout(500)
            continue

        if len(peak) == last_size:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since >= settle:
                # Stash peak for read_reply even if DOM emptied.
                await page.evaluate(
                    """(text) => {
                        window.__islamAsrBestResponse = {
                            text, selector: 'peak', length: text.length
                        };
                    }""",
                    peak,
                )
                return
        else:
            last_size, stable_since = len(peak), None
        await page.wait_for_timeout(800)

    raise BrowserFlowError(
        f"No finished reply after {timeout:.0f}s. Pro mode can be slow — retry with a "
        "larger --response-timeout, or check the browser window for a captcha or usage limit."
    )


async def _composer_pending_chars(page, composer=None) -> int:
    """Chars still sitting in the message box (0 = cleared / sent).

    Always re-query a fresh locator. Quill remounts after Send; treating a
    dead handle as "sent" is what produced the generating=False / composer>0 stalls.
    """
    try:
        fresh = await first_visible(page, COMPOSER_SELECTORS, timeout=400)
        target = fresh if fresh is not None else composer
        if target is None:
            return -1  # unknown
        text = (await target.inner_text()).strip()
        if not text or text in ("\n", "\u200b"):
            return 0
        return len(text)
    except Exception:  # noqa: BLE001
        return -1


async def confirm_sent(page, composer, timeout: float = 12.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        pending = await _composer_pending_chars(page, composer)
        generating = await is_generating(page)
        # Composer empty is the only reliable "sent" signal. Generating alone
        # can false-positive on leftover Stop/Cancel controls.
        if pending == 0:
            return True
        if generating and pending > 0 and pending < 40:
            # Tiny leftover placeholder while Stop is visible — treat as sent.
            return True
        await page.wait_for_timeout(500)
    return False


async def ask(
    page,
    composer,
    message: str,
    args,
    before_text: str,
    tag: str = "",
    must_contain: str | None = None,
    source_chunk: str | None = None,
) -> str:
    for attempt in (1, 2):
        if await rate_limited(page):
            await ride_out_rate_limit(page, args.rate_limit_wait, tag)
            composer = await wait_for_composer(
                page,
                args.composer_selectors,
                args.load_timeout,
                rate_limit_budget=args.rate_limit_wait,
                tag=tag,
            )
        try:
            await fill_composer(page, composer, message, tag, must_contain=must_contain)
            break
        except Exception as exc:  # noqa: BLE001
            if attempt == 2:
                raise
            log(f"{tag}Could not fill the message box ({type(exc).__name__}: {exc}); retrying.")
            await ride_out_rate_limit(page, args.rate_limit_wait, tag)
            composer = await wait_for_composer(
                page,
                args.composer_selectors,
                args.load_timeout,
                rate_limit_budget=args.rate_limit_wait,
                tag=tag,
            )
    # Final guard: never click Send on a short/empty box.
    final_text = (await composer.inner_text()).strip()
    if not _composer_has_enough(final_text, message):
        raise BrowserFlowError(
            f"Abort send: composer has {len(final_text)} chars, message is {len(message)}."
        )
    if must_contain and must_contain not in final_text:
        raise BrowserFlowError(
            f"Abort send: ASR anchor missing from composer ({must_contain[:40]!r}…)."
        )
    await submit(page, composer, tag=tag)
    if not await confirm_sent(page, composer):
        log(f"{tag}The message did not leave the box; clicking Send again.")
        await submit(page, composer, tag=tag)
        if not await confirm_sent(page, composer):
            how = await _click_send_button(page)
            log(f"{tag}Final Send attempt: {how or 'button not found'}")
            if not await confirm_sent(page, composer, timeout=15.0):
                # Soft blocks often clear after a fresh chat.
                log(f"{tag}Send stuck — opening a new chat and retrying once.")
                await page.wait_for_timeout(8000)
                composer = await start_chat(
                    page,
                    args.model,
                    args.composer_selectors,
                    args.load_timeout,
                    tag,
                    args.rate_limit_wait,
                    allow_flash=args.allow_flash,
                    no_switch=args.no_model_switch,
                )
                await fill_composer(page, composer, message, tag, must_contain=must_contain)
                await submit(page, composer, tag=tag)
                if not await confirm_sent(page, composer, timeout=15.0):
                    raise BrowserFlowError(
                        "Could not send the message — Send was clicked but the composer never cleared."
                    )
    await wait_for_reply(
        page,
        args.assistant_selector,
        before_text,
        args.response_timeout,
        args.settle,
        tag,
        args.rate_limit_wait,
    )
    reply = await last_reply_text(page, args.assistant_selector)
    if not reply or reply == before_text:
        raise BrowserFlowError("Gemini's reply came back empty.")
    if not _reply_looks_usable(reply, source_chunk):
        raise BrowserFlowError(
            f"Gemini reply too short/junk ({len(reply)} chars) — not caching. "
            f"Preview: {reply[:80]!r}"
        )
    return reply


# --------------------------------------------------------------------------- #
# Per-lecture driver
# --------------------------------------------------------------------------- #


def build_message(
    index: int,
    total: int,
    chunk: str,
    previous_tail: str | None,
    rules: str = STYLE_RULES,
) -> str:
    parts = []
    if index == 1:
        parts.append(rules.format(total=total))
    elif previous_tail:
        parts.append(rules.format(total=total))
        parts.append(f"{RESUME_NOTE}\n\n«…{previous_tail}»")
    parts.append(CHUNK_HEADER.format(index=index, total=total))
    parts.append(chunk)
    return "\n\n".join(parts)


async def process_transcript(page, transcript: Path, args, tag: str = "") -> Path | None:
    raw = transcript.read_text(encoding="utf-8")
    text = continuous_text(raw)
    chunks = split_chunks(text, args.chunk_chars)
    if not chunks:
        log(f"{tag}Skipping {transcript.name}: no text in it.")
        return None

    target = output_path(transcript, args.suffix)
    cache = parts_dir(transcript)
    cache.mkdir(exist_ok=True)

    done = {i for i in range(1, len(chunks) + 1) if part_path(transcript, i).exists()}
    todo = [i for i in range(1, len(chunks) + 1) if i not in done]
    if args.max_chunks:
        todo = todo[: args.max_chunks]

    log(
        f"{tag}{transcript.parent.name}: {len(text):,} chars in {len(chunks)} chunk(s); "
        f"{len(done)} cached, sending {len(todo)}."
    )

    if todo:
        composer = await start_chat(
            page,
            args.model,
            args.composer_selectors,
            args.load_timeout,
            tag,
            args.rate_limit_wait,
            allow_flash=args.allow_flash,
            no_switch=args.no_model_switch,
        )
        if args.confirm_first_send and not tag:
            await wait_for_go_ahead()
            composer = await wait_for_composer(page, args.composer_selectors, args.load_timeout)

        for position, index in enumerate(todo):
            previous = part_path(transcript, index - 1)
            tail = None
            if index > 1 and position == 0 and previous.exists():
                tail = previous.read_text(encoding="utf-8").strip()[-args.tail_chars :]
            message = build_message(
                index, len(chunks), chunks[index - 1], tail, resolve_rules(args)
            )
            asr_snip = _asr_anchor(chunks[index - 1])

            log(f"{tag}  chunk {index}/{len(chunks)} → sending {len(chunks[index - 1]):,} chars")
            before_text = await last_reply_text(page, args.assistant_selector)
            reply = await ask(
                page,
                composer,
                message,
                args,
                before_text,
                tag,
                must_contain=asr_snip,
                source_chunk=chunks[index - 1],
            )
            if "##" not in reply:
                log(f"{tag}  WARNING: reply has no Markdown headings (fence may have been lost).")
            if _reply_missing_arabic(reply):
                log(f"{tag}  WARNING: translation label without Arabic above it in chunk {index}.")
            part_path(transcript, index).write_text(reply + "\n", encoding="utf-8")
            log(f"{tag}  chunk {index}/{len(chunks)} ← got {len(reply):,} chars")

            if index != todo[-1]:
                await page.wait_for_timeout(int(args.delay * 1000))
                composer = await wait_for_composer(
                    page,
                    args.composer_selectors,
                    args.load_timeout,
                    rate_limit_budget=args.rate_limit_wait,
                    tag=tag,
                )

    have = [i for i in range(1, len(chunks) + 1) if part_path(transcript, i).exists()]
    body = "\n\n".join(
        part_path(transcript, i).read_text(encoding="utf-8").strip() for i in have
    )
    if len(have) < len(chunks):
        partial = output_path(transcript, partial_suffix(args.suffix))
        partial.write_text(body + "\n", encoding="utf-8")
        log(f"{tag}  {len(have)}/{len(chunks)} chunks done → {partial.name} (rerun to finish)")
        return partial

    target.write_text(body + "\n", encoding="utf-8")
    log(f"{tag}  wrote {target.name} ({len(body):,} chars)")
    return target


async def process_summary(page, book: Path, args, tag: str = "") -> Path | None:
    text = book.read_text(encoding="utf-8").strip()
    if not text:
        log(f"{tag}Skipping {book.name}: empty.")
        return None

    target = summary_output_path(book)
    cache = parts_dir(book, SUMMARY_PARTS_PREFIX)
    cache.mkdir(exist_ok=True)

    chunks = split_chunks(text, args.summary_chunk_chars)
    done = {
        i
        for i in range(1, len(chunks) + 1)
        if (cache / f"part_{i:03d}.md").exists()
    }
    todo = [i for i in range(1, len(chunks) + 1) if i not in done]

    log(
        f"{tag}{book.parent.name}: summarize {len(text):,} chars, "
        f"{len(chunks)} chunk(s), sending {len(todo)}."
    )

    if len(chunks) == 1:
        message = f"{SUMMARY_RULES}\n\n{SUMMARY_HEADER}\n\n{text}"
        composer = await start_chat(
            page,
            args.model,
            args.composer_selectors,
            args.load_timeout,
            tag,
            args.rate_limit_wait,
            allow_flash=args.allow_flash,
            no_switch=args.no_model_switch,
        )
        before_text = await last_reply_text(page, args.assistant_selector)
        reply = await ask(
            page, composer, message, args, before_text, tag, must_contain=_asr_anchor(text)
        )
        target.write_text(reply + "\n", encoding="utf-8")
        log(f"{tag}  wrote {target.name} ({len(reply):,} chars)")
        return target

    if todo:
        composer = await start_chat(
            page,
            args.model,
            args.composer_selectors,
            args.load_timeout,
            tag,
            args.rate_limit_wait,
            allow_flash=args.allow_flash,
            no_switch=args.no_model_switch,
        )
        for index in todo:
            header = f"بخش {index} از {len(chunks)} — فقط یادداشت‌های خلاصه برای این قطعه:"
            message = f"{SUMMARY_RULES}\n\n{header}\n\n{chunks[index - 1]}"
            before_text = await last_reply_text(page, args.assistant_selector)
            reply = await ask(
                page,
                composer,
                message,
                args,
                before_text,
                tag,
                must_contain=_asr_anchor(chunks[index - 1]),
            )
            (cache / f"part_{index:03d}.md").write_text(reply + "\n", encoding="utf-8")
            if index != todo[-1]:
                await page.wait_for_timeout(int(args.delay * 1000))
                composer = await wait_for_composer(
                    page,
                    args.composer_selectors,
                    args.load_timeout,
                    rate_limit_budget=args.rate_limit_wait,
                    tag=tag,
                )

    partial_notes = "\n\n".join(
        (cache / f"part_{i:03d}.md").read_text(encoding="utf-8").strip()
        for i in range(1, len(chunks) + 1)
        if (cache / f"part_{i:03d}.md").exists()
    )
    merge_message = (
        f"{SUMMARY_RULES}\n\n"
        "یادداشت‌های خلاصهٔ هر بخش از یک جلسهٔ طولانی:\n\n"
        f"{partial_notes}\n\n"
        "اکنون **یک** فایل خلاصهٔ نهایی با ساختار خواسته‌شده بنویس (بدون تکرار بخش‌ها):"
    )
    composer = await start_chat(
        page,
        args.model,
        args.composer_selectors,
        args.load_timeout,
        tag,
        args.rate_limit_wait,
        allow_flash=args.allow_flash,
        no_switch=args.no_model_switch,
    )
    before_text = await last_reply_text(page, args.assistant_selector)
    reply = await ask(page, composer, merge_message, args, before_text, tag)
    target.write_text(reply + "\n", encoding="utf-8")
    log(f"{tag}  wrote {target.name} ({len(reply):,} chars)")
    return target


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Raw ASR → book-style Markdown (+ optional summary) via Gemini web UI (Pro).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        help="A *.txt file, lecture folder (001/), or series folder.",
    )
    parser.add_argument("--login", action="store_true", help="Open the browser to sign in, then exit.")
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Summarize existing *.book.md → *.summary.md (instead of book pass).",
    )
    parser.add_argument(
        "--input",
        choices=("raw", "cleaned", "auto"),
        default="raw",
        help="Transcript source: raw *.txt (default), *.cleaned.txt, or auto-prefer-raw.",
    )
    parser.add_argument(
        "--wait-login",
        type=float,
        default=0.0,
        help="Before starting, open Gemini and wait up to N seconds for you to sign in.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show the chunk plan; no browser.")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE, help="Browser profile dir.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help='Model preference for the picker (default "Pro"). Flash/Fast are refused.',
    )
    parser.add_argument(
        "--channel",
        default="",
        help='Playwright browser channel (default: bundled Chromium). Pass "chrome" to use system Chrome.',
    )
    parser.add_argument(
        "--allow-flash",
        action="store_true",
        help="Permit a Flash/Fast model (default: refuse, Pro only).",
    )
    parser.add_argument(
        "--extra-rules",
        default="",
        help="Extra prompt rules appended to the built-in style rules.",
    )
    parser.add_argument(
        "--no-model-switch",
        action="store_true",
        help="Never touch the mode picker; use whatever you selected in the window.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print the model names the picker offers, then exit.",
    )
    parser.add_argument("--headless", action="store_true", help="Hide the browser (often blocked).")
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Open this many Gemini tabs and process that many lectures at once (default 1).",
    )

    selection = parser.add_argument_group("selection")
    selection.add_argument("--only", nargs="*", default=[], help="Keep lectures matching these strings.")
    selection.add_argument("--start", type=int, help="First lecture number to process.")
    selection.add_argument("--end", type=int, help="Last lecture number to process.")
    selection.add_argument("--limit", type=int, default=0, help="Stop after N lectures.")
    selection.add_argument("--overwrite", action="store_true", help="Redo lectures that already have output.")
    selection.add_argument("--max-chunks", type=int, default=0, help="Send at most N chunks per lecture (smoke test).")

    pacing = parser.add_argument_group("pacing and limits")
    pacing.add_argument("--chunk-chars", type=int, default=6000, help="Characters per book message (default 6000).")
    pacing.add_argument(
        "--summary-chunk-chars",
        type=int,
        default=12000,
        help="Characters per chunk when summarizing very long book.md (default 12000).",
    )
    pacing.add_argument("--tail-chars", type=int, default=600, help="Context carried into a resumed chat.")
    pacing.add_argument("--delay", type=float, default=5.0, help="Seconds to wait between messages.")
    pacing.add_argument("--response-timeout", type=float, default=900.0, help="Max seconds to wait per reply.")
    pacing.add_argument(
        "--settle",
        type=float,
        default=8.0,
        help="Seconds a reply must stay unchanged (Flash streams in bursts; keep this generous).",
    )
    pacing.add_argument("--load-timeout", type=float, default=90.0, help="Max seconds to wait for the composer.")
    pacing.add_argument("--confirm-first-send", action="store_true", help="Pause before the first message (jobs=1 only).")
    pacing.add_argument("--stop-on-error", action="store_true", help="Abort instead of skipping to the next lecture.")
    pacing.add_argument(
        "--stagger",
        type=float,
        default=1.5,
        help="Seconds between opening each parallel tab (default 1.5).",
    )
    pacing.add_argument(
        "--rate-limit-wait",
        type=float,
        default=900.0,
        help="Seconds to keep waiting out a rate/quota dialog.",
    )

    advanced = parser.add_argument_group("advanced")
    advanced.add_argument("--suffix", default=OUTPUT_SUFFIX, help=f"Book output suffix (default {OUTPUT_SUFFIX}).")
    advanced.add_argument("--composer-selector", help="Override the message-box selector.")
    advanced.add_argument(
        "--assistant-selector",
        default=ASSISTANT_SELECTORS[0],
        help="Primary reply selector (peak observer still uses the full list).",
    )

    args = parser.parse_args(argv)
    args.profile = args.profile.expanduser()
    args.jobs = max(1, args.jobs)
    args.channel = args.channel.strip() or None
    if looks_like_flash(args.model) and not args.allow_flash:
        parser.error("--model looks like Flash/Fast; pass --allow-flash to permit it.")
    args.composer_selectors = (
        (args.composer_selector,) + COMPOSER_SELECTORS if args.composer_selector else COMPOSER_SELECTORS
    )
    if not args.login and not args.list_models and args.target is None:
        parser.error("give a path to process, or use --login")
    return args


async def run_list_models(args) -> None:
    async_playwright = require_async_playwright()
    async with async_playwright() as playwright:
        context = await open_context(
            playwright, args.profile, headless=args.headless, channel=args.channel
        )
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=120_000)
            await wait_for_composer(page, args.composer_selectors, args.load_timeout)
            log(f"Current model label: {await read_model_label(page)!r}")
            options = await list_model_options(page)
            if not options:
                log("Could not read the model menu; check the browser window.")
            for option in options:
                log(f"  option: {option}")
        finally:
            await context.close()


async def run_login(args) -> None:
    async_playwright = require_async_playwright()
    async with async_playwright() as playwright:
        context = await open_context(playwright, args.profile, headless=False, channel=args.channel)
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=120_000)
        log(f"Sign in to Google Gemini in the open window. Session is saved in {args.profile}.")
        log("Click Sign in, finish Google login, then wait until the Sign in button disappears.")
        if await wait_for_login(page, args.wait_login or 900.0):
            # Give Chromium a moment to flush cookies to the profile dir.
            await page.wait_for_timeout(2500)
            await page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=120_000)
            await page.wait_for_timeout(2000)
            if not await is_signed_in(page):
                log("WARNING: still looks signed out after login. Try again.")
            else:
                log("Signed in (Google session cookies present).")
            try:
                shown = await select_pro_model(
                    page, args.model, allow_flash=args.allow_flash, no_switch=args.no_model_switch
                )
                log(f"Model after login: {shown!r}")
            except BrowserFlowError as exc:
                log(f"WARNING: {exc}")
            await page.wait_for_timeout(1500)
        else:
            log("Timed out waiting for sign-in. Rerun with --login.")
        await context.close()


def run_dry(transcripts: list[Path], args, summarize: bool = False) -> None:
    total_chunks = 0
    if summarize:
        for book in transcripts:
            text = book.read_text(encoding="utf-8")
            chunks = split_chunks(text, args.summary_chunk_chars)
            total_chunks += max(1, len(chunks))
            exists = "exists" if summary_output_path(book).exists() else "-"
            log(f"{book.parent.name}: {len(text):,} chars → summary output={exists}")
        log(f"{len(transcripts)} book file(s) to summarize.")
        return

    for transcript in transcripts:
        text = continuous_text(transcript.read_text(encoding="utf-8"))
        chunks = split_chunks(text, args.chunk_chars)
        total_chunks += len(chunks)
        cached = sum(1 for i in range(1, len(chunks) + 1) if part_path(transcript, i).exists())
        exists = "exists" if output_path(transcript, args.suffix).exists() else "-"
        sizes = ", ".join(f"{len(c):,}" for c in chunks[:6]) + (" …" if len(chunks) > 6 else "")
        log(
            f"{transcript.parent.name}: {len(chunks)} chunk(s) [{sizes}] "
            f"cached={cached} output={exists}"
        )
    log(f"{len(transcripts)} lecture(s), {total_chunks} message(s) to send in total.")


async def run_parallel(items: list[Path], args, summarize: bool = False) -> int:
    jobs = min(args.jobs, len(items))
    if jobs > 4:
        log(
            f"Opening {jobs} tabs — Gemini may rate-limit or show captchas; "
            "rerun with a smaller --jobs if that happens."
        )
    else:
        log(f"Opening {jobs} tab(s) for {len(items)} item(s).")

    queue: asyncio.Queue[Path | None] = asyncio.Queue()
    for item in items:
        await queue.put(item)
    for _ in range(jobs):
        await queue.put(None)

    failures = 0
    fail_lock = asyncio.Lock()
    stop = asyncio.Event()

    async_playwright = require_async_playwright()
    async with async_playwright() as playwright:
        context = await open_context(
            playwright, args.profile, headless=args.headless, channel=args.channel
        )
        try:
            bootstrap = context.pages[0] if context.pages else await context.new_page()
            if args.wait_login:
                await bootstrap.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=120_000)
                if not await wait_for_login(bootstrap, args.wait_login):
                    log("Never signed in, so nothing was sent. Rerun when you are ready.")
                    return 1
                log("Signed in.")

            async def worker(worker_id: int) -> None:
                nonlocal failures
                tag = f"[tab{worker_id}] "
                if worker_id > 1:
                    await asyncio.sleep(args.stagger * (worker_id - 1))
                page = bootstrap if worker_id == 1 else await context.new_page()
                while not stop.is_set():
                    item = await queue.get()
                    if item is None:
                        return
                    if stop.is_set():
                        return
                    try:
                        if summarize:
                            await process_summary(page, item, args, tag)
                        else:
                            await process_transcript(page, item, args, tag)
                    except RateLimitedError as exc:
                        async with fail_lock:
                            failures += 1
                        log(f"{tag}{item.parent.name}: {exc}")
                        stop.set()
                        return
                    except BrowserFlowError as exc:
                        async with fail_lock:
                            failures += 1
                        log(f"{tag}{item.parent.name}: {exc}")
                        if args.stop_on_error:
                            stop.set()
                            return
                    except Exception as exc:  # noqa: BLE001
                        async with fail_lock:
                            failures += 1
                        log(f"{tag}{item.parent.name}: unexpected error: {exc}")
                        if args.stop_on_error:
                            stop.set()
                            return

            await asyncio.gather(*(worker(i + 1) for i in range(jobs)))
        finally:
            await context.close()

    return failures


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.login:
        asyncio.run(run_login(args))
        if args.target is None:
            return 0

    if args.list_models:
        asyncio.run(run_list_models(args))
        return 0

    summarize = args.summarize
    if summarize:
        items = filter_transcripts(find_book_files(args.target), args.only, args.start, args.end)
        if not args.overwrite:
            items = [b for b in items if not summary_output_path(b).exists()]
        empty_msg = "Nothing to do (no matching *.book.md, or all summaries exist)."
    else:
        items = filter_transcripts(find_transcripts(args.target, args.input), args.only, args.start, args.end)
        if not args.overwrite:
            items = [t for t in items if not output_path(t, args.suffix).exists()]
        empty_msg = "Nothing to do (no matching *.txt, or all book outputs exist)."

    if args.limit:
        items = items[: args.limit]

    if not items:
        log(empty_msg)
        return 0

    if args.dry_run:
        run_dry(items, args, summarize=summarize)
        return 0

    if args.confirm_first_send and args.jobs > 1:
        log("--confirm-first-send is ignored when --jobs > 1.")

    try:
        failures = asyncio.run(run_parallel(items, args, summarize=summarize))
    except KeyboardInterrupt:
        log("Interrupted. Finished chunks are cached; rerun to continue.")
        return 130

    if failures:
        log(f"Done with {failures} item(s) unfinished. Rerun to resume from the cache.")
        return 1
    log("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
