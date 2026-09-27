#!/usr/bin/env python3
"""Open Gemini, click Sign in, wait for a real session, smoke-test Send."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gemini_book_style as g  # noqa: E402
from playwright.async_api import async_playwright  # noqa: E402

READY = Path("/tmp/gemini_login_ready")


async def click_sign_in(page) -> bool:
    for sel in (
        'button:has-text("Sign in")',
        'a:has-text("Sign in")',
        'button:has-text("ورود")',
        'a:has-text("ورود")',
        'a[href*="accounts.google.com/ServiceLogin"]',
        'a[href*="accounts.google.com/signin"]',
        'a[href*="accounts.google.com/v3/signin"]',
    ):
        loc = page.locator(sel).first
        try:
            if await loc.count() and await loc.is_visible(timeout=800):
                g.log(f"Clicking Sign in via {sel}")
                await loc.click(timeout=5000)
                return True
        except Exception as exc:  # noqa: BLE001
            g.log(f"click fail {sel}: {exc}")
    for role in ("button", "link"):
        loc = page.get_by_role(role, name="Sign in")
        if await loc.count():
            g.log(f"Clicking role={role} Sign in")
            await loc.first.click(timeout=5000)
            return True
    return False


async def main() -> None:
    READY.unlink(missing_ok=True)
    async with async_playwright() as p:
        ctx = await g.open_context(p, Path.home() / ".gemini_playwright_profile", False, None)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(g.GEMINI_URL, wait_until="domcontentloaded", timeout=120_000)
        await page.wait_for_timeout(3000)
        g.log(
            f"start signed_in={await g.is_signed_in(page)} "
            f"model={await g.read_model_label(page)!r}"
        )

        if not await g.is_signed_in(page):
            if await click_sign_in(page):
                g.log("Sign in clicked. Finish Google account picker in the window…")
            else:
                g.log("WARNING: no Sign in control found — please click it yourself.")
            ok = await g.wait_for_login(page, 900.0)
            if not ok:
                g.log("Timed out waiting for sign-in.")
                READY.write_text("fail")
                await ctx.close()
                return

        await g.dismiss_gemini_banners(page)
        await page.wait_for_timeout(1500)
        await page.goto(g.GEMINI_URL, wait_until="domcontentloaded", timeout=120_000)
        await page.wait_for_timeout(2000)
        await g.dismiss_gemini_banners(page)
        g.log(
            f"Signed in confirmed. model={await g.read_model_label(page)!r} "
            f"signed_in={await g.is_signed_in(page)}"
        )
        try:
            shown = await g.select_pro_model(page, "3.7 Flash", allow_flash=True)
            g.log(f"Model: {shown!r}")
        except Exception as exc:  # noqa: BLE001
            g.log(f"model select: {exc}")

        composer = await g.wait_for_composer(page, g.COMPOSER_SELECTORS, 60)
        await g.fill_composer(page, composer, "ping — reply ok", tag="[login] ")
        await g.submit(page, composer, tag="[login] ")
        sent = await g.confirm_sent(page, composer, timeout=20)
        g.log(f"smoke send landed={sent}")
        if sent:
            await page.wait_for_timeout(8000)
            reply = await g.last_reply_text(page, "")
            g.log(f"smoke reply={reply[:120]!r}")
        READY.write_text("ok" if sent else "send_failed")
        await page.wait_for_timeout(1500)
        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
