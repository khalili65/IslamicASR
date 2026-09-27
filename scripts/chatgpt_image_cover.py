#!/usr/bin/env python3
"""Generate a course cover image via ChatGPT's web UI (Playwright).

Uploads a reference book cover and asks ChatGPT to produce a polished
promotional image: Allameh Hassanzadeh Amoli holding that book, with the
lecturer name in Nastaliq calligraphy.

Does NOT modify scripts/chatgpt_book_style.py — this is a separate tool.

Usage:
    python scripts/chatgpt_image_cover.py \\
      --reference "/path/to/book.jpg" \\
      --out website/apps/web/public/images/courses/marefat_nafs.png \\
      --prompt-extra "…"

Requires the same Playwright profile as the book-style script
(~/.chatgpt_playwright_profile). Run once with --login if needed.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

DEFAULT_PROFILE = Path.home() / ".chatgpt_playwright_profile"
CHATGPT_URL = "https://chatgpt.com/"
DEFAULT_MODEL = "gpt-5-thinking"

COMPOSER_SELECTORS = (
    "div#prompt-textarea[contenteditable='true']",
    "#prompt-textarea",
    "div[contenteditable='true'].ProseMirror",
)
SEND_SELECTORS = (
    "button[data-testid='send-button']",
    "button[aria-label='Send prompt']",
    "button#composer-submit-button",
)
ASSISTANT_SELECTOR = "[data-message-author-role='assistant']"
FILE_INPUT_SELECTORS = (
    "input[type='file'][accept*='image']",
    "input[type='file']",
)
IMAGE_SELECTORS = (
    f"{ASSISTANT_SELECTOR} img",
    "img[alt*='Generated']",
    "img[src*='oaiusercontent']",
    "img[src*='images.openai']",
)

DEFAULT_PROMPT = """این تصویر جلد کتاب «دروس معرفة النفس» اثر علامه حسن‌زاده آملی است (پیوست).

لطفاً یک تصویر تبلیغاتی باکیفیت و محترمانه بساز با این مشخصات:

1) علامه حسن‌زاده آملی (عالم و فیلسوف شیعه ایرانی مسن با عمامه و لباس روحانیت، چهرهٔ آرام و نورانی) این همان کتاب آبی‌رنگ با عنوان زرد نستعلیق «دروس معرفة النفس» را در دست دارد؛ جلد کتاب باید شبیه تصویر مرجع باشد.
2) در تصویر، نام مدرس دوره با خوشنویسی فارسی نستعلیق طلایی/سفید خوانا نوشته شود:
   «حضرت استاد بیات (عبدالزهرا)»
3) فضای تصویر: آرام، کتابخانهٔ سنتی ایرانی، نور گرم ملایم، بدون متن انگلیسی، بدون واترمارک، بدون لوگوهای مدرن.
4) نسبت تصویر افقی نزدیک به ۱۶:۹ برای کاور وب‌سایت دوره.

ابتدا تصویر را تولید کن (image generation). فقط تصویر را بده."""


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def require_async_playwright():
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover
        sys.exit(f"Install playwright first: pip install playwright && playwright install chromium ({exc})")
    return async_playwright


async def first_visible(page, selectors, timeout: float = 2000):
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if await loc.is_visible(timeout=timeout):
                return loc
        except Exception:  # noqa: BLE001
            continue
    return None


async def open_context(playwright, profile: Path, headless: bool):
    profile.mkdir(parents=True, exist_ok=True)
    return await playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile),
        headless=headless,
        viewport={"width": 1280, "height": 900},
        accept_downloads=True,
        args=["--disable-blink-features=AutomationControlled"],
    )


async def wait_for_composer(page, timeout: float = 90.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        composer = await first_visible(page, COMPOSER_SELECTORS, timeout=500)
        if composer is not None:
            return composer
        await page.wait_for_timeout(400)
    raise RuntimeError("Could not find ChatGPT composer. Try --login first.")


async def upload_reference(page, reference: Path) -> None:
    for sel in FILE_INPUT_SELECTORS:
        inputs = page.locator(sel)
        count = await inputs.count()
        for i in range(count):
            handle = inputs.nth(i)
            try:
                await handle.set_input_files(str(reference))
                log(f"Uploaded reference via {sel}")
                await page.wait_for_timeout(1500)
                return
            except Exception:  # noqa: BLE001
                continue
    # Fallback: click the attach button then set files on any new input.
    attach = page.locator(
        "button[aria-label*='Attach'], button[aria-label*='Upload'], "
        "button[data-testid='composer-plus-btn'], button:has-text('Attach')"
    ).first
    try:
        await attach.click(timeout=3000)
        await page.wait_for_timeout(500)
    except Exception:  # noqa: BLE001
        pass
    for sel in FILE_INPUT_SELECTORS:
        handle = page.locator(sel).last
        try:
            await handle.set_input_files(str(reference))
            log("Uploaded reference after opening attach menu")
            await page.wait_for_timeout(1500)
            return
        except Exception:  # noqa: BLE001
            continue
    raise RuntimeError("Could not upload the reference image to ChatGPT.")


async def fill_and_send(page, composer, prompt: str) -> None:
    await composer.click()
    await page.keyboard.insert_text(prompt)
    await page.wait_for_timeout(400)
    send = await first_visible(page, SEND_SELECTORS, timeout=3000)
    if send is None:
        await page.keyboard.press("Enter")
    else:
        await send.click()


async def wait_for_generated_image(page, timeout: float = 300.0):
    deadline = time.time() + timeout
    last_count = 0
    while time.time() < deadline:
        for sel in IMAGE_SELECTORS:
            imgs = page.locator(sel)
            count = await imgs.count()
            if count > last_count:
                last_count = count
            if count:
                # Prefer the last assistant image.
                img = imgs.last
                try:
                    if await img.is_visible(timeout=500):
                        src = await img.get_attribute("src")
                        if src and src.startswith("http"):
                            return img, src
                except Exception:  # noqa: BLE001
                    continue
        await page.wait_for_timeout(2000)
    raise RuntimeError("Timed out waiting for a generated image from ChatGPT.")


async def download_image(page, src: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # Prefer Playwright download / fetch in-page to keep cookies.
    data = await page.evaluate(
        """async (url) => {
          const res = await fetch(url);
          const buf = await res.arrayBuffer();
          return Array.from(new Uint8Array(buf));
        }""",
        src,
    )
    out.write_bytes(bytes(data))
    log(f"Wrote {out} ({out.stat().st_size:,} bytes)")


async def run_login(profile: Path) -> None:
    async_playwright = require_async_playwright()
    async with async_playwright() as playwright:
        context = await open_context(playwright, profile, headless=False)
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(CHATGPT_URL, wait_until="domcontentloaded")
        log(f"Sign in, then close the window. Profile: {profile}")
        await page.wait_for_timeout(600_000)


async def run_generate(args) -> None:
    async_playwright = require_async_playwright()
    prompt = args.prompt or DEFAULT_PROMPT
    if args.prompt_extra:
        prompt = f"{prompt}\n\n{args.prompt_extra}"

    async with async_playwright() as playwright:
        context = await open_context(playwright, args.profile, headless=args.headless)
        page = context.pages[0] if context.pages else await context.new_page()
        url = f"{CHATGPT_URL}?model={args.model}" if args.model else CHATGPT_URL
        await page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        composer = await wait_for_composer(page, timeout=args.load_timeout)
        await upload_reference(page, args.reference)
        before = await page.locator(ASSISTANT_SELECTOR).count()
        await fill_and_send(page, composer, prompt)
        # Wait until a new assistant turn appears, then for an image.
        deadline = time.time() + args.response_timeout
        while time.time() < deadline:
            if await page.locator(ASSISTANT_SELECTOR).count() > before:
                break
            await page.wait_for_timeout(1000)
        _img, src = await wait_for_generated_image(page, timeout=args.response_timeout)
        await download_image(page, src, args.out)
        await context.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--login", action="store_true", help="Open browser to sign in, then exit.")
    p.add_argument("--reference", type=Path, help="Reference book cover image.")
    p.add_argument("--out", type=Path, help="Output image path (.png/.jpg).")
    p.add_argument("--prompt", default=None, help="Override the default generation prompt.")
    p.add_argument("--prompt-extra", default="", help="Appended notes for the model.")
    p.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--headless", action="store_true")
    p.add_argument("--load-timeout", type=float, default=90.0)
    p.add_argument("--response-timeout", type=float, default=360.0)
    args = p.parse_args(argv)
    args.profile = args.profile.expanduser()
    if not args.login:
        if args.reference is None or args.out is None:
            p.error("--reference and --out are required (unless --login)")
        args.reference = args.reference.expanduser().resolve()
        args.out = args.out.expanduser().resolve()
        if not args.reference.is_file():
            p.error(f"Reference not found: {args.reference}")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.login:
        asyncio.run(run_login(args.profile))
        return
    asyncio.run(run_generate(args))


if __name__ == "__main__":
    main()
