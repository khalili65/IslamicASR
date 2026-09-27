#!/usr/bin/env python3
"""Turn raw or cleaned ASR transcripts into book-style Markdown via ChatGPT's web UI.

Pipeline (see prompts/lecture-transcript-pipeline.md):
  1. ElevenLabs ASR → *.txt (raw, never overwritten)
  2. This script → *.book.md (citations, clarity, drop Q&A, Farsi under Arabic, polish)
  3. --summarize → *.summary.md

Uses chatgpt.com in a real browser with your logged-in session (subscription, not API).

Usage:
    python scripts/chatgpt_book_style.py --login
    python scripts/chatgpt_book_style.py Audios/Tadabor_Sobohi/Manaee/Term1 --dry-run
    python scripts/chatgpt_book_style.py Audios/Tadabor_Sobohi/Manaee/Term1 --only 001
    python scripts/chatgpt_book_style.py Audios/Bayat/marefat_nafs --jobs 3
    python scripts/chatgpt_book_style.py Audios/.../Term1 --summarize

By default the script reads raw `*.txt` (strips `--- Segments ---`). Use
`--input cleaned` for legacy `*.cleaned.txt` files.

Each lecture opens one new chat, sends the transcript in chunks, and writes
`*.book.md`. Chunk replies are cached in `.book_parts_<stem>/` for resume.

Setup:
    pip install playwright
    playwright install chromium

`--login` saves the session in ~/.chatgpt_playwright_profile. The window stays
visible — ChatGPT blocks headless traffic.

If the composer or reply selectors break, pass --composer-selector /
--assistant-selector instead of editing this file.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULT_PROFILE = Path.home() / ".chatgpt_playwright_profile"
CHATGPT_URL = "https://chatgpt.com/"

# ChatGPT accepts a model slug as a query param, which is the only reliable way
# to start a chat in thinking mode without clicking through the model menu.
DEFAULT_MODEL = "gpt-5-thinking"

# The composer is a ProseMirror contenteditable, not a <textarea>.
COMPOSER_SELECTORS = (
    "div#prompt-textarea[contenteditable='true']",
    "#prompt-textarea",
    "[data-testid='composer-input']",
    "div[contenteditable='true'].ProseMirror",
)
SEND_SELECTORS = (
    "button[data-testid='send-button']",
    "button[aria-label='Send prompt']",
    "button#composer-submit-button",
)
STOP_SELECTORS = (
    "button[data-testid='stop-button']",
    "button[aria-label='Stop streaming']",
    "button[aria-label='Stop generating']",
)
ASSISTANT_SELECTOR = "[data-message-author-role='assistant']"
MODEL_LABEL_SELECTORS = (
    "[data-testid='model-switcher-dropdown-button']",
    "button[aria-label*='Model selector']",
    "button[data-testid*='model-switcher']",
)
COPY_SELECTOR = "button[data-testid='copy-turn-action-button']"
CONTINUE_SELECTOR = "button:has-text('Continue generating')"
# The "Too many requests" modal has a stable id, which beats matching its text:
# it covers the whole page and swallows clicks meant for the composer.
RATE_LIMIT_SELECTORS = (
    "[data-testid='modal-conversation-history-rate-limit']",
    "#modal-conversation-history-rate-limit",
    "[role='dialog']:has-text('Too many requests')",
)
RATE_LIMIT_DISMISS_SELECTORS = (
    "[data-testid='modal-conversation-history-rate-limit'] button:has-text('Got it')",
    "#modal-conversation-history-rate-limit button:has-text('Got it')",
    "[role='dialog'] button:has-text('Got it')",
    "button:has-text('Got it')",
)
LOGIN_MARKERS = (
    "[data-testid='login-button']",
    "[data-testid='mobile-login-button']",
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

# Persian sentence enders, used when a single paragraph is longer than the budget.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟؛])\s+")

STYLE_RULES = """این متن، پیاده‌سازیِ ماشینی (ASR) از گفتارِ یک استاد در جلسهٔ درس/سخنرانی فارسی است. آن را به یک فایل **مطالعهٔ کتابی** به‌صورت Markdown تبدیل کن.

## کارهایی که باید انجام دهی

### ۱) اصلاحِ ارجاعات و نقلِ اسلامی
- آیات قرآن، احادیث، نهج‌البلاغه، ادعیه و نقل‌های عربی/کلاسیک را وقتی قابل‌شناسایی‌اند اصلاح کن.
- نام سوره، شماره آیه، «صلوات»، «علیه‌السلام» و عبارات مذهبیِ mangled را درست کن.
- برای هر نقلِ مهم، در صورت امکان **جست‌وجوی وب** بزن و متن معتبر را بیار (tanzil.net، quran.com، منابع معتبر).
- نقل را حدسی گسترش نده؛ فقط همان بخشی را که سخنران خوانده یا اشاره کرده بازسازی کن.

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
- زیر هر بلوک عربی، این برچسب را بگذار:
  > **ترجمهٔ فارسی (توسط مدل، نه استاد):** …
- در ابتدای فایل (بخش اول) یک یادداشت کوتاه: ترجمه‌های زیرِ عربی توسط **مدل** است نه استاد.

### ۵) قالب Markdown
- با `##` / `###` بر اساس جریان جلسه بخش‌بندی کن.
- آیات را با فونت بزرگ‌تر HTML بنویس، مثلاً:
  ```html
  <p class="ayah-ar" dir="rtl" style="font-size:1.5em; line-height:2.1; font-family: Amiri, 'Scheherazade New', 'Noto Naskh Arabic', serif;">
  «…» <span class="ayah-ref">(سوره/آیه)</span>
  </p>
  ```
- در **بخش آخر** یک پاورقی: منبع ASR، ترجمه‌ها از مدل، پرسش‌وپاسخ حذف شده، Segments نیست.

## قواعد سخت
- **خلاصه نکن.** این فایل مطالعه است نه digest (خلاصه جداگانه می‌آید).
- ادعای تازه یا آیه‌ای که سخنران نگفته **نیاور**.
- خروجی **فقط Markdown ویرای‌شده** — بدون «البته من … کردم»، بدون توضیح دربارهٔ دستورالعمل.
- اگر جایی نامفهوم است، همان معنا را روان بنویس؛ حدسِ جدید نزن.

متن در {total} بخش پشت‌سرهم می‌آید. هر بخش را جداگانه ویرایش کن و **فقط** خروجی همان بخش را بده، سپس منتظر بخش بعد بمان."""

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
- فارسی روان و فشرده."""

CHUNK_HEADER = "بخش {index} از {total} — با همان قواعد ویرایش کن و فقط Markdownِ ویرای‌شدهٔ همان بخش را بده:"
SUMMARY_HEADER = "متن کاملِ جلسه — خلاصهٔ Markdown بنویس (فقط خروجی خلاصه، بدون مقدمه):"
RESUME_NOTE = (
    "برای پیوستگی، پایانِ بخشِ ویرایش‌شدهٔ پیشین را می‌آورم. آن را بازنویسی نکن و "
    "در خروجی تکرارش نکن؛ فقط لحن و ادامهٔ مطلب را با آن هم‌آهنگ کن:"
)


class BrowserFlowError(RuntimeError):
    """Raised when the page is not in the state the script expects."""


def log(message: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {message}", flush=True)


# --------------------------------------------------------------------------- #
# Transcript discovery and chunking
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
    """Drop the timestamp block; ChatGPT only needs continuous prose."""
    if SEGMENTS_MARKER in text:
        return text.split(SEGMENTS_MARKER, 1)[0].strip()
    return text.strip()


def find_transcripts(target: Path, input_kind: str) -> list[Path]:
    """Collect transcript files from a file, lecture folder, or series."""
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
    # auto: prefer raw *.txt; drop cleaned when raw exists for same stem
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
    """Collect *.book.md files for the summarize pass."""
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
    """Leading digits of the lecture folder (`.../019/019_....cleaned.txt` -> 19)."""
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
    """Break one over-long paragraph on sentence boundaries, then on raw length."""
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
    """Group transcript paragraphs into messages of at most `budget` characters."""
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
    """`.book.md` -> `.book.partial.md`, so unfinished runs never look final."""
    base, dot, extension = suffix.rpartition(".")
    return f"{base}.partial{dot}{extension}" if dot else f"{suffix}.partial"


# --------------------------------------------------------------------------- #
# Browser plumbing (async — required for multi-tab parallelism)
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


async def open_context(playwright, profile: Path, headless: bool):
    profile.mkdir(parents=True, exist_ok=True)
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile),
        headless=headless,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )
    try:
        await context.grant_permissions(
            ["clipboard-read", "clipboard-write"], origin="https://chatgpt.com"
        )
    except Exception as exc:  # noqa: BLE001  older Chromium builds refuse this
        log(f"Could not grant clipboard permissions ({exc}); will paste via DOM events.")
    return context


async def first_visible(page, selectors, timeout: float = 2000):
    """Return the first selector in `selectors` that is present and visible."""
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count() > 0 and await locator.is_visible(timeout=timeout):
                return locator
        except Exception:  # noqa: BLE001  not mounted yet
            continue
    return None


async def is_generating(page) -> bool:
    return await first_visible(page, STOP_SELECTORS, timeout=300) is not None


async def rate_limited(page) -> bool:
    return await first_visible(page, RATE_LIMIT_SELECTORS, timeout=200) is not None


class RateLimitedError(BrowserFlowError):
    """ChatGPT kept showing the “Too many requests” dialog past the backoff budget."""


async def ride_out_rate_limit(page, budget: float, tag: str = "") -> None:
    """Dismiss the “Too many requests” modal and wait for it to stop coming back.

    The dialog is often transient — it disappears on its own after a short pause —
    so treating the first sighting as fatal ends runs that would have recovered.
    """
    waited = 0.0
    pause = 20.0
    while waited < budget:
        button = await first_visible(page, RATE_LIMIT_DISMISS_SELECTORS, timeout=300)
        if button is not None:
            try:
                await button.click(timeout=3000, force=True)
            except Exception:  # noqa: BLE001  modal may vanish mid-click
                pass
        await page.wait_for_timeout(2000)
        if not await rate_limited(page):
            if waited:
                log(f"{tag}Rate limit cleared after {waited:.0f}s.")
            return
        log(f"{tag}Rate limited; waiting {pause:.0f}s (used {waited:.0f}s of {budget:.0f}s).")
        await page.wait_for_timeout(int(pause * 1000))
        waited += pause + 2
        pause = min(pause * 1.5, 120.0)
    raise RateLimitedError(
        f"ChatGPT kept rate-limiting for {budget:.0f}s. Wait longer, then rerun "
        "with --jobs 1."
    )


async def wait_for_composer(
    page, selectors, timeout: float, login_grace: float = 8.0, rate_limit_budget: float = 600.0, tag: str = ""
):
    """Wait for the message box, or fail early if the page wants a login."""
    started = time.time()
    deadline = started + timeout
    while time.time() < deadline:
        if await rate_limited(page):
            await ride_out_rate_limit(page, rate_limit_budget, tag)
            deadline = time.time() + timeout
        composer = await first_visible(page, selectors, timeout=500)
        if composer is not None:
            return composer
        if (
            time.time() - started >= login_grace
            and await first_visible(page, LOGIN_MARKERS, timeout=300) is not None
        ):
            raise BrowserFlowError(
                "ChatGPT is showing the login screen. Run again with --login and sign in."
            )
        await page.wait_for_timeout(500)
    raise BrowserFlowError(
        "Could not find the message box on chatgpt.com. If the page looks fine, pass the "
        "right selector with --composer-selector."
    )


async def is_signed_in(page) -> bool:
    if await first_visible(page, LOGIN_MARKERS, timeout=300) is not None:
        return False
    return await first_visible(page, COMPOSER_SELECTORS, timeout=500) is not None


async def wait_for_login(page, timeout: float) -> bool:
    deadline = time.time() + timeout
    announced = False
    while time.time() < deadline:
        if await is_signed_in(page):
            return True
        if not announced:
            log("Waiting for you to sign in to ChatGPT in the open browser window…")
            announced = True
        await page.wait_for_timeout(2000)
    return False


async def start_chat(
    page, model: str, selectors, timeout: float, tag: str = "", rate_limit_budget: float = 600.0
):
    url = f"{CHATGPT_URL}?model={model}" if model else CHATGPT_URL
    await page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    composer = await wait_for_composer(
        page, selectors, timeout, rate_limit_budget=rate_limit_budget, tag=tag
    )
    label = await first_visible(page, MODEL_LABEL_SELECTORS)
    shown = ""
    if label is not None:
        try:
            shown = (await label.inner_text()).strip()
            log(f"{tag}Model selector shows: {shown!r}")
        except Exception:  # noqa: BLE001  label is cosmetic
            pass
    if not shown:
        log(f"{tag}Could not read the model label; check the window if the mode matters.")
    elif "thinking" in model.lower() and "thinking" not in shown.lower():
        log(
            f"{tag}WARNING: this chat does not look like thinking mode. Pick the mode in "
            "the window, or pass --model with the current slug."
        )
    return composer


async def fill_composer(page, composer, text: str) -> None:
    """Put `text` in the composer without touching the system clipboard.

    Parallel tabs must not share the OS clipboard — a paste event with a
    synthetic DataTransfer stays inside the page and is safe across workers.
    """
    await composer.click()
    await page.keyboard.press("Meta+A" if sys.platform == "darwin" else "Control+A")
    await page.keyboard.press("Backspace")

    inserted = await page.evaluate(
        """(value) => {
            const el = document.querySelector('#prompt-textarea')
                || document.querySelector('[data-testid="composer-input"]')
                || document.querySelector('div[contenteditable="true"].ProseMirror');
            if (!el) return false;
            el.focus();
            const dt = new DataTransfer();
            dt.setData('text/plain', value);
            el.dispatchEvent(new ClipboardEvent('paste', {
                clipboardData: dt, bubbles: true, cancelable: true
            }));
            return (el.innerText || '').length >= Math.min(80, Math.floor(value.length * 0.4));
        }""",
        text,
    )
    if not inserted:
        for number, line in enumerate(text.split("\n")):
            if number:
                await page.keyboard.press("Shift+Enter")
            await page.keyboard.insert_text(line)
        await page.wait_for_timeout(300)

    if not (await composer.inner_text()).strip():
        raise BrowserFlowError("The message box stayed empty after inserting the text.")


async def submit(page, composer) -> None:
    button = await first_visible(page, SEND_SELECTORS)
    if button is not None:
        await button.click()
        return
    await composer.click()
    await page.keyboard.press("Enter")


async def markdown_text(turn) -> str:
    bodies = turn.locator(".markdown")
    if await bodies.count() > 0:
        return (await bodies.last.inner_text()).strip()
    return (await turn.inner_text()).strip()


async def read_reply(page, assistant_selector: str, tag: str = "") -> str:
    """Read the last assistant turn from the DOM (safe under parallel tabs)."""
    turn = page.locator(assistant_selector).last
    await turn.scroll_into_view_if_needed()
    await page.wait_for_timeout(300)
    text = await markdown_text(turn)
    if text:
        return text
    # Optional copy-button path — only useful when a single tab owns the clipboard.
    copy_button = turn.locator(COPY_SELECTOR).last
    if await copy_button.count() == 0:
        copy_button = page.locator(COPY_SELECTOR).last
    try:
        if await copy_button.count() > 0:
            await copy_button.click(timeout=3000, force=True)
            await page.wait_for_timeout(300)
            copied = await page.evaluate("() => navigator.clipboard.readText()")
            if copied and copied.strip():
                return copied.strip()
    except Exception as exc:  # noqa: BLE001
        log(f"{tag}Copy button unavailable ({exc}); using empty DOM text.")
    return text


async def last_reply_text(page, assistant_selector: str) -> str:
    turns = page.locator(assistant_selector)
    if await turns.count() == 0:
        return ""
    return await markdown_text(turns.last)


async def wait_for_reply(
    page,
    assistant_selector: str,
    before_text: str,
    timeout: float,
    settle: float,
    tag: str = "",
    rate_limit_budget: float = 600.0,
) -> None:
    """Block until the newest assistant turn differs from `before_text` and settles."""
    deadline = time.time() + timeout
    last_size = -1
    stable_since = None

    while time.time() < deadline:
        if await rate_limited(page):
            await ride_out_rate_limit(page, rate_limit_budget, tag)
            deadline = time.time() + timeout
        if await is_generating(page):
            last_size, stable_since = -1, None
            await page.wait_for_timeout(1000)
            continue

        continue_button = await first_visible(page, (CONTINUE_SELECTOR,), timeout=200)
        if continue_button is not None:
            log(f"{tag}Reply was cut off; clicking “Continue generating”.")
            await continue_button.click()
            last_size, stable_since = -1, None
            await page.wait_for_timeout(1000)
            continue

        current = await last_reply_text(page, assistant_selector)
        if not current or current == before_text:
            await page.wait_for_timeout(500)
            continue

        if len(current) == last_size:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since >= settle:
                return
        else:
            last_size, stable_since = len(current), None
        await page.wait_for_timeout(800)

    raise BrowserFlowError(
        f"No finished reply after {timeout:.0f}s. Thinking mode can be slow — retry with a "
        "larger --response-timeout, or check the browser window for a captcha or usage limit."
    )


async def confirm_sent(page, composer, timeout: float = 12.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if not (await composer.inner_text()).strip():
                return True
        except Exception:  # noqa: BLE001  composer re-rendered, treat as sent
            return True
        await page.wait_for_timeout(500)
    return False


async def ask(page, composer, message: str, args, before_text: str, tag: str = "") -> str:
    # The rate-limit modal covers the page and eats clicks aimed at the composer,
    # so clear it before typing rather than letting the click time out.
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
            await fill_composer(page, composer, message)
            break
        except Exception as exc:  # noqa: BLE001  usually an intercepted click
            if attempt == 2:
                raise
            log(f"{tag}Could not fill the message box ({type(exc).__name__}); retrying.")
            await ride_out_rate_limit(page, args.rate_limit_wait, tag)
            composer = await wait_for_composer(
                page,
                args.composer_selectors,
                args.load_timeout,
                rate_limit_budget=args.rate_limit_wait,
                tag=tag,
            )
    await submit(page, composer)
    if not await confirm_sent(page, composer):
        log(f"{tag}The message did not leave the box; pressing Enter again.")
        await submit(page, composer)
        if not await confirm_sent(page, composer):
            raise BrowserFlowError("Could not send the message — the composer never cleared.")
    await wait_for_reply(
        page,
        args.assistant_selector,
        before_text,
        args.response_timeout,
        args.settle,
        tag,
        args.rate_limit_wait,
    )
    reply = await read_reply(page, args.assistant_selector, tag)
    if not reply:
        raise BrowserFlowError("ChatGPT's reply came back empty.")
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
            page, args.model, args.composer_selectors, args.load_timeout, tag, args.rate_limit_wait
        )
        if args.confirm_first_send and not tag:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: input(
                    "Check the browser (model, thinking mode, captcha), then press Enter here… "
                ),
            )
            composer = await wait_for_composer(page, args.composer_selectors, args.load_timeout)

        for position, index in enumerate(todo):
            previous = part_path(transcript, index - 1)
            tail = None
            if index > 1 and position == 0 and previous.exists():
                tail = previous.read_text(encoding="utf-8").strip()[-args.tail_chars :]
            message = build_message(index, len(chunks), chunks[index - 1], tail, STYLE_RULES)

            log(f"{tag}  chunk {index}/{len(chunks)} → sending {len(chunks[index - 1]):,} chars")
            before_text = await last_reply_text(page, args.assistant_selector)
            reply = await ask(page, composer, message, args, before_text, tag)
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
            page, args.model, args.composer_selectors, args.load_timeout, tag, args.rate_limit_wait
        )
        before_text = await last_reply_text(page, args.assistant_selector)
        reply = await ask(page, composer, message, args, before_text, tag)
        target.write_text(reply + "\n", encoding="utf-8")
        log(f"{tag}  wrote {target.name} ({len(reply):,} chars)")
        return target

    # Very long book.md: summarize each chunk, then merge in a final chat.
    if todo:
        composer = await start_chat(
            page, args.model, args.composer_selectors, args.load_timeout, tag, args.rate_limit_wait
        )
        for index in todo:
            header = f"بخش {index} از {len(chunks)} — فقط یادداشت‌های خلاصه برای این قطعه:"
            message = f"{SUMMARY_RULES}\n\n{header}\n\n{chunks[index - 1]}"
            before_text = await last_reply_text(page, args.assistant_selector)
            reply = await ask(page, composer, message, args, before_text, tag)
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
        page, args.model, args.composer_selectors, args.load_timeout, tag, args.rate_limit_wait
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
        description="Raw ASR → book-style Markdown (+ optional summary) via ChatGPT web UI.",
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
        help="Before starting, open chatgpt.com and wait up to N seconds for you to sign in.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show the chunk plan; no browser.")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE, help="Browser profile dir.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model slug for the ?model= param.")
    parser.add_argument("--headless", action="store_true", help="Hide the browser (usually blocked).")
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Open this many ChatGPT tabs and process that many lectures at once (default 1).",
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
    pacing.add_argument("--settle", type=float, default=3.0, help="Seconds a reply must stay unchanged.")
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
        help="Seconds to keep dismissing and waiting out a “Too many requests” dialog.",
    )

    advanced = parser.add_argument_group("advanced")
    advanced.add_argument("--suffix", default=OUTPUT_SUFFIX, help=f"Book output suffix (default {OUTPUT_SUFFIX}).")
    advanced.add_argument("--composer-selector", help="Override the message-box selector.")
    advanced.add_argument("--assistant-selector", default=ASSISTANT_SELECTOR, help="Override the reply selector.")
    advanced.add_argument(
        "--insert-method",
        choices=("paste", "type"),
        default="paste",
        help="Ignored: fills always use an in-page paste event (safe for --jobs > 1).",
    )

    args = parser.parse_args(argv)
    args.profile = args.profile.expanduser()
    args.jobs = max(1, args.jobs)
    args.composer_selectors = (
        (args.composer_selector,) + COMPOSER_SELECTORS if args.composer_selector else COMPOSER_SELECTORS
    )
    if not args.login and args.target is None:
        parser.error("give a path to process, or use --login")
    return args


async def run_login(args) -> None:
    async_playwright = require_async_playwright()
    async with async_playwright() as playwright:
        context = await open_context(playwright, args.profile, headless=False)
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(CHATGPT_URL, wait_until="domcontentloaded", timeout=120_000)
        log(f"Sign in to ChatGPT in the open window. Session is saved in {args.profile}.")
        if await wait_for_login(page, args.wait_login or 600.0):
            log("Signed in.")
        else:
            log("Still not signed in when the wait ran out.")
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
    """Process lectures across `args.jobs` ChatGPT tabs in one browser window."""
    jobs = min(args.jobs, len(items))
    if jobs > 12:
        log(
            f"Opening {jobs} tabs — ChatGPT may rate-limit or show captchas; "
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
        context = await open_context(playwright, args.profile, headless=args.headless)
        try:
            bootstrap = context.pages[0] if context.pages else await context.new_page()
            if args.wait_login:
                await bootstrap.goto(CHATGPT_URL, wait_until="domcontentloaded", timeout=120_000)
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
                    except Exception as exc:  # noqa: BLE001  keep other tabs going
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
