#!/usr/bin/env python3
"""Download audio files from an Eitaa channel you are a member of.

Usage:
    python scripts/eitaa_download.py shajareh --login          # once, to sign in
    python scripts/eitaa_download.py shajareh --dry-run        # list what it sees
    python scripts/eitaa_download.py shajareh --out Audios/Shajareh
    python scripts/eitaa_download.py shajareh --name-contains سخنرانی --jobs 4

By default the script uses the web client's getSearch API to list matching
audio (including old posts), builds authenticated /stream/ URLs, then downloads
them in parallel (--jobs). Pass --via-scroll to use the older DOM-scroll path.

Eitaa has no public API or direct file URLs for channel media: the public web
view (see `eitaa_list.py`) lists file names but never a downloadable link, and
web.eitaa.com fetches files over an authenticated MTProto session. So this
script drives that web client with Playwright, using your own login.

Setup:
    pip install playwright
    playwright install chromium

`--login` opens a browser window where you sign in with your phone number and
the code Eitaa sends you. The session is kept in a local browser profile
(default `~/.eitaa_playwright_profile`), so later runs need no login.

The web client's markup is not a stable API. If a run reports that it found no
audio, use `--inspect` to dump the message markup and pass the right selectors
via `--audio-selector` / `--download-selector` — no code change needed.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote, unquote

DEFAULT_PROFILE = Path.home() / ".eitaa_playwright_profile"
WEB_CLIENT = "https://web.eitaa.com"

AUDIO_EXTS = (".mp3", ".m4a", ".ogg", ".opus", ".wav", ".aac", ".flac")

# Prefer multiples of 512KiB (Eitaa/Telegram stream alignment). Larger = fewer
# round-trips and usually faster; too many parallel workers still hit HTTP 408.
STREAM_CHUNK = 2 * 1024 * 1024  # 2 MiB
ALIGN_CHUNK = 524_288

# web.eitaa.com is a Telegram-Web-K fork, so the login screen and the chat view
# are two panes that are swapped in place; whichever is visible tells us which
# state we are in. The client needs 20-40s to boot before either appears.
AUTH_PANE = "#auth-pages"
CHATS_PANE = "#page-chats"

# Audio posts render as custom <audio-element class="audio"> nodes. Only a
# window of them is in the DOM at once (virtualized list).
AUDIO_SELECTOR_CANDIDATES = (
    "audio-element.audio",
    "audio-element",
    ".audio",
    ".document",
)

# Context-menu item used by the web client (Persian label: دانلود).
MENU_DOWNLOAD_SELECTOR = ".btn-menu-item.tgico-download"

ILLEGAL_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|\x00-\x1f]')
JOINCHAT_RE = re.compile(
    r"(?:joinchat/|#/?joinchat/)([A-Za-z0-9_-]+)|(?:^|/)([0-9]+[A-Za-z0-9_-]{8,})$"
)


def sanitize_filename(name: str) -> str:
    """Keep Persian text intact but make the name safe for the filesystem."""
    name = unicodedata.normalize("NFC", name).strip()
    name = ILLEGAL_FILENAME_CHARS.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return name[:180] or "audio"


def parse_invite_hash(value: str | None) -> str | None:
    """Extract an Eitaa/Telegram joinchat hash from a URL or raw hash string."""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if re.fullmatch(r"[0-9]+[A-Za-z0-9_-]{8,}", text):
        return text
    match = JOINCHAT_RE.search(text)
    if not match:
        return None
    return match.group(1) or match.group(2)


def require_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "Playwright is not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )
    return sync_playwright


def open_context(playwright, profile: Path, headless: bool, downloads: Path):
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(profile),
        headless=headless,
        accept_downloads=True,
        downloads_path=str(downloads),
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )


def is_visible(page, selector: str) -> bool:
    try:
        locator = page.locator(selector)
        return locator.count() > 0 and locator.first.is_visible(timeout=1500)
    except Exception:  # noqa: BLE001  pane not mounted yet
        return False


def open_client(page, url: str, boot_timeout: float, log=print) -> str:
    """Load the client and wait for either the login or the chat pane.

    Returns "auth", "chats", or "unknown". `commit` is used rather than a load
    state because the client keeps connections open and never reports idle.
    """
    log(f"Opening {url}")
    page.goto(url, wait_until="commit", timeout=60_000)
    # Chromium sometimes drops the hash on the first navigation to this SPA.
    if "#" in url:
        wanted_hash = "#" + url.split("#", 1)[1]
        page.evaluate(
            """(h) => {
              if (location.hash !== h) location.hash = h;
            }""",
            wanted_hash,
        )

    deadline = time.monotonic() + boot_timeout
    while time.monotonic() < deadline:
        if is_visible(page, CHATS_PANE):
            return "chats"
        if is_visible(page, AUTH_PANE):
            return "auth"
        page.wait_for_timeout(1000)
    return "unknown"


def wait_for_channel_peer(
    page, timeout: float = 60.0, channel: str | None = None, log=print
) -> int | None:
    """Wait until the opened channel has a usable peerId for getSearch."""
    deadline = time.monotonic() + timeout
    # Only force #@username when it looks like a public username (not an invite label).
    wanted = None
    if channel and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,}", channel):
        wanted = f"#@{channel}"
    if wanted:
        page.evaluate(
            """(h) => {
              if (location.hash !== h) location.hash = h;
            }""",
            wanted,
        )
    while time.monotonic() < deadline:
        peer = page.evaluate(
            """() => {
              try {
                const peer = appImManager.chat && appImManager.chat.peerId;
                return (peer && peer !== 0) ? peer : null;
              } catch (e) {
                return null;
              }
            }"""
        )
        if peer:
            return int(peer)
        if wanted:
            page.evaluate(
                """(h) => {
                  try {
                    if (location.hash !== h) location.hash = h;
                    else if (appImManager && appImManager.onHashChange) {
                      appImManager.onHashChange();
                    }
                  } catch (e) {}
                }""",
                wanted,
            )
        page.wait_for_timeout(500)
    log("channel peerId did not become ready")
    return None


def open_invite_channel(page, invite_hash: str, log=print) -> dict:
    """Join/open a channel from an invite hash and return {peerId, title, chatId}."""
    log(f"Opening invite hash {invite_hash}...")
    info = page.evaluate(
        """(hash) => (async () => {
          const inv = await apiManager.invokeApi('messages.checkChatInvite', {hash});
          const chat = inv.chat || (inv.channel ? inv.channel : null);
          if (!chat) {
            // Not a member yet — import then re-check.
            await apiManager.invokeApi('messages.importChatInvite', {hash});
            const again = await apiManager.invokeApi('messages.checkChatInvite', {hash});
            const chat2 = again.chat;
            if (!chat2) throw new Error('invite has no chat after import: ' + (again._ || ''));
            if (appChatsManager.saveApiChat) appChatsManager.saveApiChat(chat2);
            const peerId = -Math.abs(Number(chat2.id));
            await appImManager.setPeer(peerId);
            return {peerId, title: chat2.title || '', chatId: Number(chat2.id), via: again._};
          }
          if (appChatsManager.saveApiChat) appChatsManager.saveApiChat(chat);
          try {
            await apiManager.invokeApi('messages.importChatInvite', {hash});
          } catch (e) {
            // Already a member is fine.
          }
          const peerId = -Math.abs(Number(chat.id));
          await appImManager.setPeer(peerId);
          return {
            peerId,
            title: chat.title || '',
            chatId: Number(chat.id),
            via: inv._,
          };
        })()""",
        invite_hash,
    )
    # Give the chat UI a moment after setPeer.
    page.wait_for_timeout(2500)
    peer = page.evaluate(
        "() => (appImManager.chat && appImManager.chat.peerId) || null"
    )
    if not peer:
        raise RuntimeError(f"invite opened but peerId missing: {info!r}")
    log(
        f"  channel {info.get('title')!r} peerId={peer} "
        f"(chatId={info.get('chatId')}, {info.get('via')})"
    )
    return info


def wait_for_login(page, timeout: float, log=print) -> bool:
    """Wait until the chat list appears, or until Enter is pressed (if stdin is a TTY)."""
    import threading

    done = {"ok": False, "cancelled": False}

    def watch_enter() -> None:
        if not sys.stdin.isatty():
            return
        try:
            input()
            done["ok"] = True
        except (EOFError, KeyboardInterrupt):
            done["cancelled"] = True

    thread = threading.Thread(target=watch_enter, daemon=True)
    thread.start()

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and not done["ok"] and not done["cancelled"]:
        if is_visible(page, CHATS_PANE):
            done["ok"] = True
            break
        page.wait_for_timeout(1000)

    return done["ok"] and not done["cancelled"]


def do_login(profile: Path, boot_timeout: float, log=print) -> None:
    sync_playwright = require_playwright()
    with sync_playwright() as playwright:
        context = open_context(playwright, profile, headless=False, downloads=profile)
        page = context.pages[0] if context.pages else context.new_page()
        state = open_client(page, WEB_CLIENT, boot_timeout, log)
        if state == "chats":
            log("Already signed in — nothing to do.")
            context.close()
            return

        log(
            "\nA browser window is open. Sign in to Eitaa with your phone number "
            "and the code you receive.\n"
            "This script waits until your chat list appears (up to 10 minutes).\n"
            "If you are already signed in, press Enter here to continue."
        )
        ok = wait_for_login(page, timeout=600.0, log=log)

        if ok or is_visible(page, CHATS_PANE):
            log(f"Session saved in {profile}")
        else:
            log("Still on the login screen — the session may not have been saved.")
        context.close()


def audio_filename(element) -> str | None:
    """Read the display title of an <audio-element> and turn it into a .mp3 name."""
    try:
        title = element.locator(".audio-title [title]").first.get_attribute(
            "title", timeout=1500
        )
    except Exception:  # noqa: BLE001
        title = None
    if not title:
        try:
            title = (element.locator(".audio-title").inner_text(timeout=1500) or "").strip()
        except Exception:  # noqa: BLE001
            title = None
    if not title:
        try:
            title = (element.inner_text(timeout=1500) or "").splitlines()[0].strip()
        except Exception:  # noqa: BLE001
            return None
    title = title.strip()
    if not title:
        return None
    if not title.lower().endswith(AUDIO_EXTS):
        title = f"{title}.mp3"
    return sanitize_filename(title)


def audio_key(element) -> str:
    """Stable id for an audio row across virtualized re-renders."""
    try:
        mid = element.get_attribute("data-mid")
        if mid:
            return f"mid:{mid}"
    except Exception:  # noqa: BLE001
        pass
    name = audio_filename(element)
    return f"name:{name}" if name else f"obj:{id(element)}"


def scroll_chat_up(page, amount: int = 2400) -> None:
    """Scroll the message list upward so older posts are virtualized in."""
    page.evaluate(
        """(amount) => {
          const bubbles = document.querySelector('.bubbles');
          if (bubbles) {
            const rect = bubbles.getBoundingClientRect();
            const x = rect.left + rect.width / 2;
            const y = rect.top + Math.min(rect.height / 2, 300);
            bubbles.dispatchEvent(new WheelEvent('wheel', {
              bubbles: true, cancelable: true, deltaY: -amount, clientX: x, clientY: y
            }));
          }
          const inner = document.querySelector('.bubbles-inner');
          if (inner && inner.parentElement) {
            const scroller = inner.closest('.scrollable') || inner.parentElement;
            if (scroller && scroller.scrollHeight > scroller.clientHeight) {
              scroller.scrollTop = Math.max(0, scroller.scrollTop - amount);
            }
          }
        }""",
        amount,
    )
    page.mouse.move(900, 450)
    page.mouse.wheel(0, -amount)


def collect_stream_urls(page) -> list[str]:
    return page.evaluate(
        """() => {
          const out = [];
          const add = v => {
            if (typeof v === 'string' && v.includes('/stream/')) out.push(v);
          };
          document.querySelectorAll('audio, source, [src]').forEach(n => {
            try { add(n.getAttribute('src')); } catch (e) {}
            try { if (typeof n.src === 'string') add(n.src); } catch (e) {}
          });
          try {
            performance.getEntriesByType('resource').forEach(e => add(e.name));
          } catch (e) {}
          return [...new Set(out)];
        }"""
    )


def parse_stream_meta(url: str) -> dict:
    payload = unquote(url.split("/stream/", 1)[1].split("?", 1)[0])
    return json.loads(payload)


def build_stream_url(meta: dict) -> str:
    """Build an authenticated /stream/ URL from document metadata."""
    payload = json.dumps(meta, separators=(",", ":"), ensure_ascii=False)
    return f"{WEB_CLIENT}/stream/{quote(payload, safe='')}"


def collect_stream_jobs_via_search(
    page,
    out_dir: Path,
    *,
    name_filter: str,
    limit: int,
    dry_run: bool,
    max_pages: int = 80,
    channel: str | None = None,
    invite_hash: str | None = None,
    log=print,
) -> tuple[list[dict], int, int, int]:
    """Use the web client's getSearch API to list matching audio and build /stream/ URLs.

    This reaches far older posts than DOM scrolling (virtualized history window).
    """
    if invite_hash:
        open_invite_channel(page, invite_hash, log=log)
    elif not wait_for_channel_peer(page, timeout=60.0, channel=channel, log=log):
        raise RuntimeError("channel peerId not ready")

    query = name_filter or ""
    log(f"Searching channel audio via getSearch (query={query!r})...")
    raw = page.evaluate(
        """(args) => (async () => {
          const {query, maxPages, nameFilter} = args;
          const peerId = appImManager.chat && appImManager.chat.peerId;
          if (!peerId) throw new Error('channel peerId not ready');
          const seen = new Set();
          const items = [];
          let maxId = 0;
          let pages = 0;
          let scanned = 0;
          // Music + voice covers typical channel audio posts.
          const filters = [
            {_: 'inputMessagesFilterMusic'},
            {_: 'inputMessagesFilterVoice'},
          ];
          for (const inputFilter of filters) {
            maxId = 0;
            for (let page = 0; page < maxPages; page++) {
              pages++;
              const r = await appMessagesManager.getSearch({
                peerId,
                query: query || '',
                inputFilter,
                maxId,
                limit: 50,
              });
              const hist = [...(r.history || [])];
              if (!hist.length) break;
              for (const m of hist) {
                scanned++;
                const doc = m && m.media && m.media.document;
                if (!doc) continue;
                const name = doc.file_name || '';
                if (nameFilter) {
                  const ok = name.includes(nameFilter)
                    || (nameFilter === 'سخنرانی' && name.includes('سخمرانی'));
                  if (!ok) continue;
                }
                const key = String(doc.id);
                if (seen.has(key)) continue;
                seen.add(key);
                let fr = doc.file_reference;
                if (fr instanceof Uint8Array) fr = Array.from(fr);
                else if (ArrayBuffer.isView(fr)) {
                  fr = Array.from(new Uint8Array(fr.buffer, fr.byteOffset, fr.byteLength));
                } else if (Array.isArray(fr)) fr = fr.slice();
                else fr = [];
                const idNum = typeof doc.id === 'bigint' ? Number(doc.id) : Number(doc.id);
                items.push({
                  mid: Number(m.mid || m.id),
                  date: Number(m.date || 0),
                  fileName: name,
                  size: Number(doc.size),
                  dcId: doc.dc_id,
                  id: Number.isFinite(idNum) ? idNum : doc.id,
                  access_hash: String(doc.access_hash),
                  file_reference: fr,
                  mimeType: doc.mime_type || 'audio/mpeg',
                });
              }
              const last = hist[hist.length - 1];
              const next = Number(last.mid || last.id);
              if (!next || next === maxId) break;
              maxId = next;
              if (hist.length < 50) break;
            }
          }
          return {pages, scanned, items};
        })()""",
        {
            "query": query,
            "maxPages": max_pages,
            "nameFilter": name_filter or "",
        },
    )
    jobs: list[dict] = []
    skipped = filtered = failed = 0
    catalog: list[dict] = []
    log(
        f"  search pages={raw.get('pages')} scanned={raw.get('scanned')} "
        f"matched={len(raw.get('items') or [])}"
    )
    for item in raw.get("items") or []:
        filename = sanitize_filename(item.get("fileName") or "audio.mp3")
        if not filename.lower().endswith(AUDIO_EXTS):
            filename += ".mp3"
        date = int(item.get("date") or 0)
        catalog.append(
            {
                "filename": filename,
                "original_name": item.get("fileName") or filename,
                "date": date,
                "mid": item.get("mid"),
                "size": int(item.get("size") or 0),
            }
        )

    for item in raw.get("items") or []:
        filename = sanitize_filename(item.get("fileName") or "audio.mp3")
        if not filename.lower().endswith(AUDIO_EXTS):
            filename += ".mp3"
        date = int(item.get("date") or 0)
        target = out_dir / filename
        # Also treat already-renumbered copies (001_name.mp3) as present.
        if not (target.exists() and target.stat().st_size > 0):
            numbered = list(out_dir.glob(f"[0-9][0-9][0-9]_{filename}"))
            if any(p.stat().st_size > 0 for p in numbered):
                log(f"  skip     (numbered) {filename}")
                skipped += 1
                continue
        if target.exists() and target.stat().st_size > 0:
            log(f"  skip     {filename}")
            skipped += 1
            continue
        size = int(item.get("size") or 0)
        if dry_run:
            log(f"  would get {filename} ({size} bytes)")
            jobs.append({"filename": filename, "url": None, "size": size, "date": date})
        else:
            try:
                meta = {
                    "dcId": item["dcId"],
                    "location": {
                        "_": "inputDocumentFileLocation",
                        "id": item["id"],
                        "access_hash": item["access_hash"],
                        "file_reference": item["file_reference"],
                    },
                    "size": size,
                    "mimeType": item.get("mimeType") or "audio/mpeg",
                    "fileName": item.get("fileName") or filename,
                }
                url = build_stream_url(meta)
                jobs.append(
                    {"filename": filename, "url": url, "size": size, "date": date}
                )
                log(f"  queued   {filename} ({size} bytes)")
            except Exception as exc:  # noqa: BLE001
                log(f"  failed   {filename}: {str(exc).splitlines()[0]}")
                failed += 1
        if limit and len(jobs) >= limit:
            log(f"  collect limit {limit} reached")
            break

    catalog_path = out_dir / "catalog.json"
    # Merge with any previous catalog so renumber still sees skipped files.
    by_name = {c["filename"]: c for c in catalog}
    if catalog_path.exists():
        try:
            prev = json.loads(catalog_path.read_text(encoding="utf-8"))
            for row in prev if isinstance(prev, list) else prev.get("items", []):
                name = row.get("filename")
                if name and name not in by_name:
                    by_name[name] = row
        except Exception:  # noqa: BLE001
            pass
    merged = sorted(by_name.values(), key=lambda r: (int(r.get("date") or 0), r["filename"]))
    catalog_path.write_text(
        json.dumps({"items": merged}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"  wrote catalog ({len(merged)} items): {catalog_path}")
    return jobs, skipped, filtered, failed


def renumber_by_upload_date(out_dir: Path, log=print) -> int:
    """Rename audio files to NNN_name.mp3 ordered by Eitaa upload date (oldest=001)."""
    catalog_path = out_dir / "catalog.json"
    if not catalog_path.exists():
        raise FileNotFoundError(
            f"No catalog at {catalog_path}. Re-run a download/collect first."
        )
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else payload.get("items", [])
    if not items:
        log("Catalog is empty — nothing to renumber.")
        return 0

    # Oldest upload first.
    ordered = sorted(
        items,
        key=lambda r: (int(r.get("date") or 0), r.get("mid") or 0, r.get("filename") or ""),
    )
    width = max(3, len(str(len(ordered))))
    renamed = 0
    # Two-pass: first move to temp names to avoid collisions.
    plan: list[tuple[Path, Path, dict]] = []
    for index, row in enumerate(ordered, start=1):
        filename = row.get("filename") or ""
        if not filename:
            continue
        src = out_dir / filename
        if not (src.exists() and src.stat().st_size > 0):
            # Maybe already numbered.
            matches = sorted(out_dir.glob(f"[0-9]*_{filename}"))
            matches = [p for p in matches if p.stat().st_size > 0]
            if not matches:
                log(f"  missing  {filename}")
                continue
            src = matches[0]
        prefix = f"{index:0{width}d}_"
        # Strip any existing leading NNN_
        bare = re.sub(r"^\d+_", "", src.name)
        dest = out_dir / f"{prefix}{bare}"
        if src.resolve() == dest.resolve():
            continue
        plan.append((src, dest, row))

    for i, (src, dest, row) in enumerate(plan):
        tmp = out_dir / f".renumber_tmp_{i}_{src.name}"
        src.rename(tmp)
        plan[i] = (tmp, dest, row)

    for tmp, dest, row in plan:
        if dest.exists():
            dest.unlink()
        tmp.rename(dest)
        date = int(row.get("date") or 0)
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(date)) if date else "?"
        log(f"  {dest.name}  (uploaded {when})")
        renamed += 1

    # Update catalog with numbered names.
    for index, row in enumerate(ordered, start=1):
        filename = row.get("filename") or ""
        if not filename:
            continue
        bare = re.sub(r"^\d+_", "", filename)
        row["numbered"] = f"{index:0{width}d}_{bare}"
        row["index"] = index
    catalog_path.write_text(
        json.dumps({"items": ordered}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"Renumbered {renamed} file(s) in {out_dir}")
    return renamed


def materialize_stream_url(
    page, element, timeout: float = 30.0, want_name: str | None = None
) -> str:
    """Click play so the client creates a /stream/... URL for this audio."""
    page.keyboard.press("Escape")
    element.scroll_into_view_if_needed(timeout=10_000)
    page.wait_for_timeout(250)

    before = set(collect_stream_urls(page))
    element.locator(".audio-toggle").click(timeout=10_000)

    def pick(urls: list[str]) -> str | None:
        abs_urls = [
            u if u.startswith("http") else f"https://web.eitaa.com{u}" for u in urls
        ]
        if want_name:
            stem = Path(want_name).stem
            for url in abs_urls:
                try:
                    meta = parse_stream_meta(url)
                except Exception:  # noqa: BLE001
                    continue
                name = meta.get("fileName") or ""
                if stem and stem in name:
                    return url
        # Prefer newly appeared URLs.
        for url in abs_urls:
            rel = url.replace("https://web.eitaa.com", "")
            if url not in before and rel not in before:
                return url
        return abs_urls[-1] if abs_urls else None

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        chosen = pick(collect_stream_urls(page))
        if chosen:
            return chosen
        page.wait_for_timeout(500)

    chosen = pick(collect_stream_urls(page))
    if not chosen:
        raise RuntimeError("no /stream/ URL appeared after play")
    return chosen


def download_stream_url(page, url: str, target: Path, timeout: float, log=print):
    """Range-download one authenticated /stream/ URL through the page session."""
    meta = parse_stream_meta(url)
    size = int(meta.get("size") or 0)
    if size <= 0:
        raise RuntimeError(f"stream meta missing size: {meta!r}")

    suggested = meta.get("fileName") or target.name
    target = target.with_name(sanitize_filename(suggested))
    if not target.name.lower().endswith(AUDIO_EXTS):
        target = target.with_name(target.name + ".mp3")

    chunk = STREAM_CHUNK
    tmp = target.with_suffix(target.suffix + ".part")
    # Resume partial downloads when possible.
    start_at = tmp.stat().st_size if tmp.exists() else 0
    if start_at > size:
        tmp.unlink()
        start_at = 0
    if start_at and start_at % ALIGN_CHUNK != 0:
        # Keep alignment with server's preferred 512KiB parts.
        start_at = start_at - (start_at % ALIGN_CHUNK)
        with tmp.open("rb+") as out:
            out.truncate(start_at)

    log(f"           stream size={size} bytes" + (f" resume@{start_at}" if start_at else ""))
    got = start_at
    deadline = time.monotonic() + timeout
    mode = "ab" if start_at else "wb"
    with tmp.open(mode) as out:
        offset = start_at
        while offset < size:
            if time.monotonic() > deadline:
                raise RuntimeError(f"timed out after {timeout:g}s at {got}/{size}")
            end = min(offset + chunk - 1, size - 1)
            last_err = None
            data = b""
            for attempt in range(6):
                try:
                    b64 = page.evaluate(
                        """(args) => {
                          const {url, start, end} = args;
                          return fetch(url, {
                            credentials: 'include',
                            headers: {Range: `bytes=${start}-${end}`}
                          }).then(async (r) => {
                            if (!r.ok && r.status !== 206) {
                              throw new Error('HTTP ' + r.status);
                            }
                            const bytes = new Uint8Array(await r.arrayBuffer());
                            let s = '';
                            const step = 0x8000;
                            for (let i = 0; i < bytes.length; i += step) {
                              s += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
                            }
                            return btoa(s);
                          });
                        }""",
                        {"url": url, "start": offset, "end": end},
                    )
                    data = base64.b64decode(b64)
                    break
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    msg = str(exc)
                    if "HTTP 408" in msg or "HTTP 429" in msg or "HTTP 5" in msg:
                        time.sleep(1.2 * (attempt + 1))
                        continue
                    raise
            else:
                raise RuntimeError(str(last_err))
            if not data:
                raise RuntimeError(f"empty chunk at offset {offset}")
            out.write(data)
            got += len(data)
            offset = got

    if got < size * 0.95:
        raise RuntimeError(f"incomplete download {got}/{size}")
    tmp.replace(target)
    return target, suggested


def download_via_stream(page, element, target: Path, timeout: float, log=print):
    """Click play to get a /stream/ URL, then download it."""
    url = materialize_stream_url(
        page, element, timeout=min(45.0, timeout), want_name=target.name
    )
    saved, suggested = download_stream_url(page, url, target, timeout, log=log)
    try:
        page.keyboard.press("Escape")
        element.locator(".audio-toggle").click(timeout=2000)
    except Exception:  # noqa: BLE001
        pass
    return saved, suggested


def collect_stream_jobs(
    page,
    audio_selector: str,
    out_dir: Path,
    *,
    name_filter: str,
    scrolls: int,
    scroll_delay: float,
    limit: int,
    dry_run: bool,
    log=print,
) -> tuple[list[dict], int, int, int]:
    """Scroll the channel and collect /stream/ jobs for matching audio posts."""
    seen_keys: set[str] = set()
    jobs: list[dict] = []
    skipped = filtered = failed = 0
    idle_scrolls = 0

    page.keyboard.press("End")
    page.wait_for_timeout(1500)
    try:
        page.locator(".bubbles").click(timeout=3000, position={"x": 200, "y": 200})
    except Exception:  # noqa: BLE001
        pass
    log("Collecting stream URLs...")

    for step in range(1, scrolls + 1):
        rows = visible_audio_rows(page, audio_selector)
        new_rows = [(k, n, el) for k, n, el in rows if k not in seen_keys]
        if not new_rows:
            idle_scrolls += 1
        else:
            idle_scrolls = 0

        for key, filename, element in new_rows:
            seen_keys.add(key)
            if name_filter and name_filter not in filename:
                filtered += 1
                continue

            target = out_dir / filename
            # Also treat already-saved stream filenames as done once we know them.
            if target.exists() and target.stat().st_size > 0:
                log(f"  skip     {target.name}")
                skipped += 1
                continue

            if dry_run:
                log(f"  would get {filename}")
                jobs.append({"filename": filename, "url": None, "size": 0})
                if limit and len(jobs) >= limit:
                    return jobs, skipped, filtered, failed
                continue

            log(f"  resolve  {filename}")
            try:
                url = materialize_stream_url(
                    page, element, timeout=30.0, want_name=filename
                )
                meta = parse_stream_meta(url)
                suggested = sanitize_filename(meta.get("fileName") or filename)
                if not suggested.lower().endswith(AUDIO_EXTS):
                    suggested += ".mp3"
                size = int(meta.get("size") or 0)
                final_path = out_dir / suggested
                if final_path.exists() and final_path.stat().st_size > 0:
                    log(f"  skip     {suggested}")
                    skipped += 1
                else:
                    jobs.append(
                        {
                            "key": key,
                            "filename": suggested,
                            "url": url,
                            "size": size,
                        }
                    )
                    log(f"           queued ({size} bytes)")
                try:
                    page.keyboard.press("Escape")
                    element.locator(".audio-toggle").click(timeout=1500)
                except Exception:  # noqa: BLE001
                    pass
                page.wait_for_timeout(300)
            except Exception as exc:  # noqa: BLE001
                log(f"           failed to resolve: {str(exc).splitlines()[0]}")
                failed += 1
                page.keyboard.press("Escape")

            if limit and len(jobs) >= limit:
                log(f"  collect limit {limit} reached")
                return jobs, skipped, filtered, failed

        if idle_scrolls >= 20:
            log("No new audio for several scrolls — collection done.")
            break

        scroll_chat_up(page, 2600)
        page.wait_for_timeout(int(scroll_delay * 1000))
        if step % 10 == 0:
            log(
                f"  collect progress: scrolled {step}/{scrolls}, "
                f"queued={len(jobs)}, skipped={skipped}, failed={failed}"
            )

    return jobs, skipped, filtered, failed


def download_jobs_parallel_pages(
    profile: str,
    jobs: list[dict],
    out_dir: Path,
    *,
    workers: int,
    timeout: float,
    log=print,
) -> tuple[int, int]:
    """Download jobs in parallel using several pages that share the login profile."""
    workers = max(1, min(workers, max(1, len(jobs))))
    return _asyncio_parallel_download(
        profile=profile,
        jobs=jobs,
        out_dir=out_dir,
        workers=workers,
        timeout=timeout,
        log=log,
    )


def _asyncio_parallel_download(
    *,
    profile: str,
    jobs: list[dict],
    out_dir: Path,
    workers: int,
    timeout: float,
    log=print,
) -> tuple[int, int]:
    import asyncio

    from playwright.async_api import async_playwright

    async def fetch_chunk(page, url: str, start: int, end: int) -> bytes:
        """Fetch a byte range. Prefer Playwright request API (no base64 overhead)."""
        last_err: Exception | None = None
        for attempt in range(8):
            try:
                response = await page.request.get(
                    url,
                    headers={"Range": f"bytes={start}-{end}"},
                    timeout=120_000,
                )
                status = response.status
                if status not in (200, 206):
                    raise RuntimeError(f"HTTP {status}")
                return await response.body()
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                msg = str(exc)
                if (
                    "HTTP 408" in msg
                    or "HTTP 429" in msg
                    or "HTTP 5" in msg
                    or "Timeout" in msg
                    or "timeout" in msg
                ):
                    await asyncio.sleep(min(8.0, 1.2 * (attempt + 1)))
                    continue
                # Fallback to in-page fetch once if request API rejects cookies/auth.
                try:
                    b64 = await page.evaluate(
                        """(args) => {
                          const {url, start, end} = args;
                          return fetch(url, {
                            credentials: 'include',
                            headers: {Range: `bytes=${start}-${end}`}
                          }).then(async (r) => {
                            if (!r.ok && r.status !== 206) throw new Error('HTTP ' + r.status);
                            const bytes = new Uint8Array(await r.arrayBuffer());
                            let s = '';
                            const step = 0x8000;
                            for (let i = 0; i < bytes.length; i += step) {
                              s += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
                            }
                            return btoa(s);
                          });
                        }""",
                        {"url": url, "start": start, "end": end},
                    )
                    return base64.b64decode(b64)
                except Exception as exc2:  # noqa: BLE001
                    last_err = exc2
                    msg2 = str(exc2)
                    if "HTTP 408" in msg2 or "HTTP 429" in msg2 or "HTTP 5" in msg2:
                        await asyncio.sleep(min(8.0, 1.2 * (attempt + 1)))
                        continue
                    raise
        raise RuntimeError(str(last_err))

    async def download_one(page, job: dict, sem: asyncio.Semaphore) -> tuple[str, bool, str]:
        name = job["filename"]
        url = job["url"]
        size = int(job["size"] or 0)
        target = out_dir / name
        if target.exists() and target.stat().st_size > 0:
            return name, True, "skipped"
        async with sem:
            log(f"  download {name} ({size} bytes)")
            try:
                chunk = STREAM_CHUNK
                tmp = target.with_suffix(target.suffix + ".part")
                start_at = tmp.stat().st_size if tmp.exists() else 0
                if start_at > size:
                    tmp.unlink()
                    start_at = 0
                if start_at and start_at % ALIGN_CHUNK != 0:
                    start_at -= start_at % ALIGN_CHUNK
                    with tmp.open("rb+") as out:
                        out.truncate(start_at)
                deadline = time.monotonic() + timeout
                written = start_at
                with tmp.open("ab" if start_at else "wb") as out:
                    while written < size:
                        if time.monotonic() > deadline:
                            raise RuntimeError(f"timeout at {written}/{size}")
                        end = min(written + chunk - 1, size - 1)
                        data = await fetch_chunk(page, url, written, end)
                        if not data:
                            raise RuntimeError(f"empty chunk at {written}")
                        out.write(data)
                        written += len(data)
                if tmp.stat().st_size < size * 0.95:
                    raise RuntimeError(f"incomplete {tmp.stat().st_size}/{size}")
                tmp.replace(target)
                log(f"  saved    {name} ({target.stat().st_size / 1_048_576:.1f} MB)")
                return name, True, "ok"
            except Exception as exc:  # noqa: BLE001
                msg = str(exc).splitlines()[0]
                log(f"  failed   {name}: {msg}")
                return name, False, msg

    async def runner() -> tuple[int, int]:
        async with async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=profile,
                headless=False,
                accept_downloads=True,
                downloads_path=str(out_dir),
                viewport={"width": 1280, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
            # One shared page: multiple tabs against /stream/ tend to get HTTP 408.
            page = await context.new_page()
            await page.goto(WEB_CLIENT, wait_until="commit", timeout=60_000)
            for _ in range(90):
                try:
                    if await page.locator(CHATS_PANE).count() and await page.locator(
                        CHATS_PANE
                    ).first.is_visible():
                        break
                except Exception:  # noqa: BLE001
                    pass
                await page.wait_for_timeout(1000)

            sem = asyncio.Semaphore(max(1, workers))
            # Process in waves so a dead URL does not starve the queue forever.
            results: list[tuple[str, bool, str]] = []
            batch = max(workers * 2, 4)
            for i in range(0, len(jobs), batch):
                wave = jobs[i : i + batch]
                results.extend(
                    await asyncio.gather(
                        *[download_one(page, job, sem) for job in wave]
                    )
                )
            await context.close()
            downloaded = sum(1 for _, ok, why in results if ok and why == "ok")
            failed = sum(1 for _, ok, _ in results if not ok)
            return downloaded, failed

    log(f"Parallel download: {len(jobs)} file(s), workers={workers}")
    # Cursor / notebooks may already have an event loop; run asyncio in a thread.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(runner())).result()


def download_jobs_parallel(
    page,
    jobs: list[dict],
    out_dir: Path,
    *,
    workers: int,
    timeout: float,
    log=print,
) -> tuple[int, int]:
    """Legacy single-page blob batch helper (unused when pages parallel is available)."""
    del page, jobs, out_dir, workers, timeout, log
    return 0, 0


def visible_audio_rows(page, audio_selector: str) -> list[tuple[str, str, object]]:
    """Return (key, filename, locator) for audio rows currently in the DOM."""
    rows: list[tuple[str, str, object]] = []
    locator = page.locator(audio_selector)
    for index in range(locator.count()):
        element = locator.nth(index)
        filename = audio_filename(element)
        if not filename:
            continue
        rows.append((audio_key(element), filename, element))
    return rows


def first_matching_selector(page, candidates: tuple[str, ...]) -> str | None:
    for selector in candidates:
        try:
            if page.locator(selector).count() > 0:
                return selector
        except Exception:  # noqa: BLE001
            continue
    return None


def inspect(page, audio_selector: str | None, out_path: Path, log=print) -> None:
    """Dump candidate markup so selectors can be corrected without guessing."""
    lines: list[str] = []
    for selector in AUDIO_SELECTOR_CANDIDATES:
        try:
            count = page.locator(selector).count()
        except Exception:  # noqa: BLE001
            count = -1
        lines.append(f"{selector!r}: {count} match(es)")
    lines.append("")
    streams = collect_stream_urls(page)
    lines.append(f"stream urls: {len(streams)}")
    for url in streams[:5]:
        lines.append(f"  {url[:180]}")
    lines.append("")

    if audio_selector:
        locator = page.locator(audio_selector)
        for index in range(min(3, locator.count())):
            try:
                markup = locator.nth(index).evaluate("el => el.outerHTML")
            except Exception as exc:  # noqa: BLE001
                markup = f"<could not read: {exc}>"
            lines.append(f"--- {audio_selector} [{index}] ---\n{markup}\n")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    log("\n".join(lines[: len(AUDIO_SELECTOR_CANDIDATES) + 3]))
    log(f"Full markup dump: {out_path}")


def run(args) -> int:
    sync_playwright = require_playwright()
    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    invite_hash = parse_invite_hash(args.invite) or parse_invite_hash(args.url)
    # Invite links are not #@username routes; boot the shell first, then open via API.
    url = WEB_CLIENT if invite_hash else (args.url or f"{WEB_CLIENT}/#@{args.channel}")
    log = print

    with sync_playwright() as playwright:
        context = open_context(
            playwright, Path(args.profile).expanduser(), args.headless, out_dir
        )
        page = context.pages[0] if context.pages else context.new_page()

        state = open_client(page, url, args.settle, log)
        if state == "auth":
            context.close()
            log(
                "\nNot signed in. Run once:\n"
                f"  python scripts/eitaa_download.py {args.channel} --login"
            )
            return 1
        if state == "unknown":
            context.close()
            log(
                f"\nThe client did not finish loading within {args.settle:g}s. "
                "Retry with a larger --settle."
            )
            return 1

        # Give the client a moment after the pane appears.
        page.wait_for_timeout(2000)
        page.keyboard.press("Escape")
        if invite_hash:
            try:
                open_invite_channel(page, invite_hash, log=log)
            except Exception as exc:  # noqa: BLE001
                context.close()
                log(f"\nCould not open invite: {exc}")
                return 1
        else:
            wait_for_channel_peer(page, timeout=60.0, channel=args.channel, log=log)

        audio_selector = args.audio_selector or first_matching_selector(
            page, AUDIO_SELECTOR_CANDIDATES
        )

        if args.inspect:
            # A bit of history so the dump is useful.
            for _ in range(min(args.scrolls, 10)):
                page.mouse.move(640, 450)
                page.mouse.wheel(0, -2000)
                page.wait_for_timeout(int(args.scroll_delay * 1000))
            inspect(page, audio_selector, out_dir / "eitaa_inspect.html", log)
            context.close()
            return 0

        name_filter = (args.name_contains or "").strip()
        if name_filter:
            log(f"Filename filter: must contain {name_filter!r}")
        else:
            log("Filename filter: none (download all audio)")

        use_search = not args.via_scroll
        if use_search:
            log(
                "Collecting via channel search (fast; reaches old posts), "
                + (
                    f"then download with {args.jobs} parallel workers."
                    if args.jobs > 1
                    else "then download sequentially."
                )
            )
            try:
                jobs, skipped, filtered, resolve_failed = collect_stream_jobs_via_search(
                    page,
                    out_dir,
                    name_filter=name_filter,
                    limit=args.limit,
                    dry_run=args.dry_run,
                    max_pages=args.search_pages,
                    channel=None if invite_hash else args.channel,
                    invite_hash=None,  # already opened above
                    log=log,
                )
            except Exception as exc:  # noqa: BLE001
                log(f"Search collection failed ({exc}); falling back to scroll.")
                use_search = False

        if not use_search:
            if not audio_selector:
                log(
                    "\nNo audio rows matched the built-in selectors. Re-run with "
                    "--inspect to dump the markup, then pass --audio-selector."
                )
                context.close()
                return 1
            log(
                f"Using selector {audio_selector!r}. "
                "Collect stream URLs by scrolling, then download"
                + (f" with {args.jobs} parallel workers." if args.jobs > 1 else ".")
            )
            jobs, skipped, filtered, resolve_failed = collect_stream_jobs(
                page,
                audio_selector,
                out_dir,
                name_filter=name_filter,
                scrolls=args.scrolls,
                scroll_delay=args.scroll_delay,
                limit=args.limit,
                dry_run=args.dry_run,
                log=log,
            )
        log(f"Queued {len(jobs)} file(s) for download.")

        downloaded = failed = resolve_failed
        if args.dry_run:
            for job in jobs:
                log(f"  would get {job['filename']}")
            context.close()
        elif not jobs:
            context.close()
        elif args.jobs <= 1:
            for index, job in enumerate(jobs, start=1):
                target = out_dir / job["filename"]
                log(f"  download [{index}/{len(jobs)}] {target.name}")
                try:
                    saved, _ = download_stream_url(
                        page, job["url"], target, args.timeout, log=log
                    )
                    log(f"           saved ({saved.stat().st_size / 1_048_576:.1f} MB)")
                    downloaded += 1
                except Exception as exc:  # noqa: BLE001
                    log(f"           failed: {str(exc).splitlines()[0]}")
                    failed += 1
                time.sleep(args.delay)
            context.close()
        else:
            profile = str(Path(args.profile).expanduser())
            context.close()  # release profile lock before async relaunch
            d, f = _asyncio_parallel_download(
                profile=profile,
                jobs=jobs,
                out_dir=out_dir,
                workers=args.jobs,
                timeout=args.timeout,
                log=log,
            )
            downloaded += d
            failed += f

    log(
        f"\nDone. downloaded={downloaded} skipped={skipped} failed={failed} "
        f"filtered={filtered}\nOutput: {out_dir}"
    )
    if getattr(args, "renumber_after", False) and not args.dry_run:
        try:
            renumber_by_upload_date(out_dir, log=log)
        except Exception as exc:  # noqa: BLE001
            log(f"Renumber skipped: {exc}")
    if downloaded:
        log(
            "\nTranscribe with:\n"
            f'  python transcribe.py "{out_dir}/<file>.mp3" --language fa -p elevenlabs'
        )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download audio from an Eitaa channel via the web client."
    )
    parser.add_argument(
        "channel",
        nargs="?",
        default="channel",
        help="Channel username, e.g. shajareh (label only when using --invite)",
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Open a browser to sign in once, then save the session and exit.",
    )
    parser.add_argument(
        "--invite",
        default=None,
        help="Eitaa invite hash or joinchat URL "
             "(e.g. https://eitaa.com/joinchat/2912028064Cb9fd779798).",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Directory for the audio files (default: Audios/<channel>).",
    )
    parser.add_argument(
        "--profile",
        default=str(DEFAULT_PROFILE),
        help=f"Browser profile holding the login (default: {DEFAULT_PROFILE}).",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Exact web client URL, if the default #@channel form does not open it.",
    )
    parser.add_argument(
        "--scrolls",
        type=int,
        default=250,
        help="Max scroll steps while walking history (default: 250).",
    )
    parser.add_argument(
        "--scroll-delay",
        type=float,
        default=0.8,
        help="Seconds between scroll steps (default: 0.8).",
    )
    parser.add_argument(
        "--settle",
        type=float,
        default=90.0,
        help="Seconds to wait for the client to boot; it is slow (default: 90).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds between downloads (default: 1.5).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Seconds to wait for one file (default: 300).",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=2,
        help="Parallel download workers after URLs are collected (default: 2). "
             "Higher values often hit HTTP 408 from Eitaa. Use 1 for sequential.",
    )
    parser.add_argument(
        "--renumber",
        action="store_true",
        help="Only renumber existing files in --out using catalog.json "
             "(001_ oldest upload …). Does not download.",
    )
    parser.add_argument(
        "--renumber-after",
        action="store_true",
        help="After downloading, rename files to NNN_name.mp3 by upload date "
             "(oldest = 001).",
    )
    parser.add_argument(
        "--via-scroll",
        action="store_true",
        help="Collect by scrolling the chat UI instead of getSearch "
             "(slower; only recent posts).",
    )
    parser.add_argument(
        "--search-pages",
        type=int,
        default=80,
        help="Max getSearch pages when collecting via search (default: 80).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stop after N new files (0 = no limit).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be downloaded without fetching anything.",
    )
    parser.add_argument(
        "--inspect",
        action="store_true",
        help="Dump the message markup and selector match counts, then exit.",
    )
    parser.add_argument(
        "--name-contains",
        default=None,
        help="Only download files whose title/filename contains this text "
             "(e.g. سخنرانی).",
    )
    parser.add_argument(
        "--audio-selector",
        default=None,
        help="CSS selector for an audio post row (overrides the built-in list).",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without a visible window (only after --login has succeeded).",
    )
    args = parser.parse_args()

    args.channel = args.channel.strip().lstrip("@").rstrip("/").split("/")[-1]
    if args.out is None:
        args.out = str(Path("Audios") / args.channel)

    if args.login:
        do_login(Path(args.profile).expanduser(), args.settle)
        return

    if args.renumber:
        out_dir = Path(args.out).expanduser()
        try:
            renumber_by_upload_date(out_dir)
        except Exception as exc:  # noqa: BLE001
            sys.exit(f"Renumber failed: {exc}")
        return

    sys.exit(run(args))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
