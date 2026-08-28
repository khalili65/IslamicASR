#!/usr/bin/env python3
"""Turn cleaned ASR transcripts into book-style Persian prose via ChatGPT's web UI.

This drives chatgpt.com in a real browser with your own logged-in session, so it
uses your ChatGPT subscription instead of the paid API.

Usage:
    python scripts/chatgpt_book_style.py --login                      # once, to sign in
    python scripts/chatgpt_book_style.py Audios/Bayat/marefat_nafs --dry-run
    python scripts/chatgpt_book_style.py Audios/Bayat/marefat_nafs --only 019
    python scripts/chatgpt_book_style.py Audios/Bayat/marefat_nafs --jobs 20

For every `*.cleaned.txt` it finds, the script opens one new chat, sends the
transcript in chunks (a 90-minute lecture is far too long for one message), and
writes the replies to `*.book.md` beside the source. Each chunk's reply is also
cached in `.book_parts_<stem>/`, so an interrupted run resumes where it stopped.

`--jobs N` opens N ChatGPT tabs in one browser and processes N lectures at once.

Setup:
    pip install playwright
    playwright install chromium

`--login` opens a browser window where you sign in normally. The session lives in
a local browser profile (default `~/.chatgpt_playwright_profile`), so later runs
need no login. The window is visible by design: ChatGPT blocks headless traffic,
and you may need to answer a captcha or pick the thinking model by hand.

chatgpt.com's markup is not a stable API. If a run reports that it cannot find
the composer or the reply, pass different selectors via `--composer-selector` /
`--assistant-selector` instead of editing this file.
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
PARTS_PREFIX = ".book_parts_"

# Persian sentence enders, used when a single paragraph is longer than the budget.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?؟؛])\s+")

STYLE_RULES = """این متن، پیاده‌سازیِ ماشینیِ گفتار (ASR) از یک سخنرانی فارسی است و کاملاً «گفتاری» است. می‌خواهم آن را به نثرِ «نوشتاریِ کتابی» تبدیل کنی تا در یک کتاب چاپ شود.

قواعد الزامی:
۱) فقط ویرایشِ زبانی و نگارشی. مفهوم، استدلال، ترتیب مطالب، مثال‌ها، داستان‌ها و پرسش‌وپاسخ‌ها را تغییر نده.
۲) هیچ مطلبی اضافه نکن و هیچ مطلبی حذف نکن. خلاصه نکن. تفسیر، توضیح، نتیجه‌گیری یا پانویسِ از خودت اضافه نکن.
۳) فعل‌ها و ضمیرهای شکستهٔ گفتاری را نوشتاری کن (می‌گه ← می‌گوید، اینو ← این را، می‌تونیم ← می‌توانیم، تو بحث ← در بحث).
۴) کلمات پرکننده و تکرارهای بی‌معنای گفتاری (مانند «خب»، «دیگه»، «یعنی»های تکراری، لکنت‌ها و جمله‌های نیمه‌رها) را حذف یا اصلاح کن، اما محتوا را دست‌نخورده نگه دار.
۵) جمله‌های ناتمام یا آشفتهٔ ASR را به جملهٔ کاملِ روان تبدیل کن، بدون افزودنِ معنای جدید.
۶) عبارت‌های عربی (آیات، روایات، دعاها) را دقیقاً همان‌گونه که آمده نگه دار؛ ترجمه نکن و حدسی اصلاح نکن.
۷) پرسش‌های حاضران و پاسخ استاد را حفظ کن؛ در صورت نیاز با «پرسش:» و «پاسخ:» از هم جدا کن.
۸) پاراگراف‌بندیِ مناسبِ کتاب انجام بده، اما عنوان و تیتر و شماره‌گذاریِ جدید اختراع نکن.
۹) خروجی فقط و فقط متنِ ویرایش‌شدهٔ فارسی باشد: بدون مقدمه، بدون توضیح دربارهٔ کاری که کردی، و بدون عبارت‌هایی مثل «در ادامه…».
۱۰) اگر جایی نامفهوم است، نزدیک‌ترین صورتِ روانِ همان جمله را بنویس و چیزی از خودت به محتوا نیفزا.

متن در {total} بخشِ پشت‌سرهم فرستاده می‌شود. هر بخش را جداگانه ویرایش کن و بی‌درنگ فقط متنِ ویرایش‌شدهٔ همان بخش را بازگردان، سپس منتظرِ بخش بعدی بمان."""

CHUNK_HEADER = "بخش {index} از {total} — با همان قواعد ویرایش کن و فقط متنِ ویرایش‌شده را بده:"
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


def find_transcripts(target: Path) -> list[Path]:
    """Collect `*.cleaned.txt` files from a file, a lecture folder, or a series."""
    if target.is_file():
        return [target]
    if not target.is_dir():
        sys.exit(f"Not found: {target}")
    found = sorted(target.glob("*.cleaned.txt")) + sorted(target.glob("*/*.cleaned.txt"))
    return [path for path in found if path.is_file()]


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


def parts_dir(transcript: Path) -> Path:
    stem = transcript.name[: -len(".cleaned.txt")]
    return transcript.parent / f"{PARTS_PREFIX}{stem[:60]}"


def part_path(transcript: Path, index: int) -> Path:
    return parts_dir(transcript) / f"part_{index:03d}.md"


def output_path(transcript: Path, suffix: str) -> Path:
    return transcript.parent / (transcript.name[: -len(".cleaned.txt")] + suffix)


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


def build_message(index: int, total: int, chunk: str, previous_tail: str | None) -> str:
    parts = []
    if index == 1:
        parts.append(STYLE_RULES.format(total=total))
    elif previous_tail:
        parts.append(STYLE_RULES.format(total=total))
        parts.append(f"{RESUME_NOTE}\n\n«…{previous_tail}»")
    parts.append(CHUNK_HEADER.format(index=index, total=total))
    parts.append(chunk)
    return "\n\n".join(parts)


async def process_transcript(page, transcript: Path, args, tag: str = "") -> Path | None:
    text = transcript.read_text(encoding="utf-8")
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
            message = build_message(index, len(chunks), chunks[index - 1], tail)

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


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rewrite cleaned ASR transcripts as book-style Persian prose "
        "using the ChatGPT web app (no API key).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target",
        nargs="?",
        type=Path,
        help="A *.cleaned.txt file, a lecture folder, or a series folder "
        "(e.g. Audios/Bayat/marefat_nafs).",
    )
    parser.add_argument("--login", action="store_true", help="Open the browser to sign in, then exit.")
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
    pacing.add_argument("--chunk-chars", type=int, default=6000, help="Characters per message (default 6000).")
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
    advanced.add_argument("--suffix", default=OUTPUT_SUFFIX, help=f"Output suffix (default {OUTPUT_SUFFIX}).")
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


def run_dry(transcripts: list[Path], args) -> None:
    total_chunks = 0
    for transcript in transcripts:
        chunks = split_chunks(transcript.read_text(encoding="utf-8"), args.chunk_chars)
        total_chunks += len(chunks)
        cached = sum(1 for i in range(1, len(chunks) + 1) if part_path(transcript, i).exists())
        exists = "exists" if output_path(transcript, args.suffix).exists() else "-"
        sizes = ", ".join(f"{len(c):,}" for c in chunks[:6]) + (" …" if len(chunks) > 6 else "")
        log(
            f"{transcript.parent.name}: {len(chunks)} chunk(s) [{sizes}] "
            f"cached={cached} output={exists}"
        )
    log(f"{len(transcripts)} lecture(s), {total_chunks} message(s) to send in total.")


async def run_parallel(transcripts: list[Path], args) -> int:
    """Process lectures across `args.jobs` ChatGPT tabs in one browser window."""
    jobs = min(args.jobs, len(transcripts))
    if jobs > 12:
        log(
            f"Opening {jobs} tabs — ChatGPT may rate-limit or show captchas; "
            "rerun with a smaller --jobs if that happens."
        )
    else:
        log(f"Opening {jobs} tab(s) for {len(transcripts)} lecture(s).")

    queue: asyncio.Queue[Path | None] = asyncio.Queue()
    for transcript in transcripts:
        await queue.put(transcript)
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
                    transcript = await queue.get()
                    if transcript is None:
                        return
                    if stop.is_set():
                        return
                    try:
                        await process_transcript(page, transcript, args, tag)
                    except RateLimitedError as exc:
                        async with fail_lock:
                            failures += 1
                        log(f"{tag}{transcript.parent.name}: {exc}")
                        stop.set()
                        # Put the lecture back so a later rerun still sees it as unfinished
                        # (its finished chunks remain cached).
                        return
                    except BrowserFlowError as exc:
                        async with fail_lock:
                            failures += 1
                        log(f"{tag}{transcript.parent.name}: {exc}")
                        if args.stop_on_error:
                            stop.set()
                            return
                    except Exception as exc:  # noqa: BLE001  keep other tabs going
                        async with fail_lock:
                            failures += 1
                        log(f"{tag}{transcript.parent.name}: unexpected error: {exc}")
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

    transcripts = filter_transcripts(
        find_transcripts(args.target), args.only, args.start, args.end
    )
    if not args.overwrite:
        transcripts = [t for t in transcripts if not output_path(t, args.suffix).exists()]
    if args.limit:
        transcripts = transcripts[: args.limit]

    if not transcripts:
        log("Nothing to do (no matching *.cleaned.txt, or all outputs already exist).")
        return 0

    if args.dry_run:
        run_dry(transcripts, args)
        return 0

    if args.confirm_first_send and args.jobs > 1:
        log("--confirm-first-send is ignored when --jobs > 1.")

    try:
        failures = asyncio.run(run_parallel(transcripts, args))
    except KeyboardInterrupt:
        log("Interrupted. Finished chunks are cached; rerun to continue.")
        return 130

    if failures:
        log(f"Done with {failures} lecture(s) unfinished. Rerun to resume from the cache.")
        return 1
    log("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
