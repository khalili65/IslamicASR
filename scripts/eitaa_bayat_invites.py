#!/usr/bin/env python3
"""Join / inventory / download Bayat private Eitaa channels via invite links.

Why this exists (separate from `eitaa_download.py`):
  Phone-app membership often does not make `https://web.eitaa.com/#-<peerId>`
  work in the Playwright web session. Private channels need
  `messages.importChatInvite` with the joinchat hash. This wrapper keeps the
  invite catalog and joins them first, then calls the existing downloader.

Does NOT modify `scripts/eitaa_download.py`.

Usage:
  # Once: ensure web.eitaa.com login (same profile as eitaa_download)
  python scripts/eitaa_download.py --login

  # List catalog
  python scripts/eitaa_bayat_invites.py --list

  # Join all invites into the web session + count music/voice/docs
  python scripts/eitaa_bayat_invites.py --inventory --headless

  # Dry-run download one course
  python scripts/eitaa_bayat_invites.py --download doroos_marefat_nafs --dry-run --headless

  # Download by catalog id
  python scripts/eitaa_bayat_invites.py --download 21 --renumber-after --headless

  # Download several
  python scripts/eitaa_bayat_invites.py --download 8,10,21 --headless
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = Path(__file__).resolve().parent / "data" / "bayat_eitaa_invites.json"
DEFAULT_OUT_ROOT = ROOT / "Audios" / "Bayat"
DOWNLOADER = ROOT / "scripts" / "eitaa_download.py"
INVENTORY_JSON = DEFAULT_OUT_ROOT / "_eitaa_tmp" / "invite_inventory.json"


def load_catalog(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    channels = data.get("channels") or data
    if not isinstance(channels, list):
        sys.exit(f"Bad catalog shape in {path}")
    return channels


def folder_has_audio(out_root: Path, slug: str) -> int:
    """Count existing audio files under Audios/Bayat/<slug>/ (any layout)."""
    folder = out_root / slug
    if not folder.is_dir():
        # Leghaallah used different casing historically.
        for alt in out_root.iterdir():
            if alt.is_dir() and alt.name.lower() == slug.lower():
                folder = alt
                break
        else:
            return 0
    n = 0
    for pat in ("*.mp3", "*.ogg", "*.opus", "*.m4a", "*.aac"):
        for p in folder.rglob(pat):
            if p.name.endswith("_play.m4a") or p.name.endswith(".play.m4a"):
                continue
            n += 1
    return n


def folder_has_partials(out_root: Path, slug: str) -> bool:
    """True if a prior download left .part files or an incomplete marker."""
    folder = out_root / slug
    if not folder.is_dir():
        for alt in out_root.iterdir() if out_root.is_dir() else []:
            if alt.is_dir() and alt.name.lower() == slug.lower():
                folder = alt
                break
        else:
            return False
    if (folder / ".download_incomplete").exists():
        return True
    return any(folder.rglob("*.part"))


def resolve_selection(
    channels: list[dict],
    raw: str,
    *,
    include_skipped: bool = False,
    out_root: Path | None = None,
    skip_if_on_disk: bool = True,
) -> list[dict]:
    """Accept slug, numeric id, or comma-separated mix. `all` = everything.

    Channels marked skip_download in the catalog are omitted unless
    include_skipped is True. When skip_if_on_disk, also skip channels whose
    Audios/Bayat/<slug>/ folder already has audio files — unless leftover
    `.part` files show the course is incomplete and needs a resume pass.
    """
    raw = (raw or "").strip()
    if not raw:
        return []

    by_id = {int(c["id"]): c for c in channels}
    by_slug = {str(c["slug"]).lower(): c for c in channels}
    chosen: list[dict] = []
    seen: set[int] = set()
    root = out_root or DEFAULT_OUT_ROOT

    def add(ch: dict, *, honor_skip: bool) -> None:
        if honor_skip and ch.get("skip_download") and not include_skipped:
            print(
                f"skip  #{ch['id']} {ch['slug']} "
                f"(already on disk / skip_download)"
            )
            return
        if skip_if_on_disk and not include_skipped:
            existing = folder_has_audio(root, ch["slug"])
            partials = folder_has_partials(root, ch["slug"])
            if existing > 0 and not partials:
                print(
                    f"skip  #{ch['id']} {ch['slug']} "
                    f"(found {existing} audio file(s) on disk)"
                )
                return
            if existing > 0 and partials:
                print(
                    f"resume #{ch['id']} {ch['slug']} "
                    f"(have {existing} audio, leftover .part files)"
                )
        cid = int(ch["id"])
        if cid not in seen:
            chosen.append(ch)
            seen.add(cid)

    if raw.lower() in {"all", "*"}:
        for ch in channels:
            add(ch, honor_skip=True)
        return chosen

    for part in raw.split(","):
        key = part.strip()
        if not key:
            continue
        ch = None
        if key.isdigit():
            ch = by_id.get(int(key))
        if ch is None:
            ch = by_slug.get(key.lower())
        if ch is None:
            sys.exit(
                f"Unknown channel {key!r}. Use --list to see ids/slugs."
            )
        # Explicit id/slug still respects skip_download unless --force-skipped.
        add(ch, honor_skip=True)
    return chosen


def cmd_list(channels: list[dict]) -> int:
    print(f"{'id':>3}  {'slug':<22}  title")
    print("-" * 72)
    for c in channels:
        flags = []
        if c.get("skip_download"):
            flags.append("SKIP")
        if c.get("note") and not c.get("skip_download"):
            flags.append(c["note"])
        elif c.get("skip_download") and c.get("note"):
            flags.append(c["note"])
        suffix = f"  # {'; '.join(flags)}" if flags else ""
        print(f"{c['id']:>3}  {c['slug']:<22}  {c['title_fa']}{suffix}")
    return 0


def cmd_inventory(channels: list[dict], headless: bool, settle: float) -> int:
    """Join each invite in the Playwright profile and report audio counts."""
    # Import helpers from the existing downloader without changing it.
    sys.path.insert(0, str(ROOT))
    from scripts.eitaa_download import (  # noqa: WPS433
        DEFAULT_PROFILE,
        WEB_CLIENT,
        open_client,
        open_context,
        parse_invite_hash,
        require_playwright,
    )

    sync_playwright = require_playwright()
    results: list[dict] = []

    with sync_playwright() as playwright:
        context = open_context(
            playwright,
            Path(DEFAULT_PROFILE).expanduser(),
            headless=headless,
            downloads=Path("/tmp/eitaa_bayat_invites"),
        )
        page = context.pages[0] if context.pages else context.new_page()
        state = open_client(page, WEB_CLIENT, settle, log=print)
        if state != "chats":
            context.close()
            sys.exit(
                "Eitaa web session is not logged in. Run:\n"
                "  python scripts/eitaa_download.py --login"
            )
        if not wait_for_api_manager(page, timeout=max(settle, 90.0), log=print):
            context.close()
            sys.exit("Eitaa web managers never became ready.")

        for ch in channels:
            invite = ch["invite"]
            h = parse_invite_hash(invite)
            row: dict = {
                "id": ch["id"],
                "slug": ch["slug"],
                "title_fa": ch["title_fa"],
                "invite": invite,
            }
            try:
                inject_manager_shims(page)
                check = page.evaluate(
                    """async (hash) => {
                      try {
                        const api = apiManager || rootScope.managers.apiManager;
                        const inv = await api.invokeApi(
                          'messages.checkChatInvite', {hash}
                        );
                        return {
                          _: inv._,
                          title: inv.title || inv.chat?.title || null,
                          participants: inv.participants_count
                            || inv.chat?.participants_count || null,
                          alreadyMember: !!inv.chat,
                        };
                      } catch (e) {
                        return {
                          err: e?.error_message || e?.message || String(e),
                        };
                      }
                    }""",
                    h,
                )
                row["check"] = check
                info = open_invite_channel_compat(page, h, log=print)
                row["opened"] = info
                peer = info.get("peerId")
                inject_manager_shims(page)
                counts = page.evaluate(
                    """async (peerId) => {
                      const one = async (filter) => {
                        try {
                          const r = await appMessagesManager.getSearch({
                            peerId,
                            query: '',
                            inputFilter: {_: filter},
                            maxId: 0,
                            limit: 1,
                          });
                          return r?.count ?? null;
                        } catch (e) {
                          return null;
                        }
                      };
                      return {
                        music: await one('inputMessagesFilterMusic'),
                        voice: await one('inputMessagesFilterVoice'),
                        docs: await one('inputMessagesFilterDocument'),
                      };
                    }""",
                    peer,
                )
                row["peerId"] = peer
                row["counts"] = counts
                row["ok"] = True
                c = counts or {}
                print(
                    f"OK  #{ch['id']:<2} {ch['slug']:<22} "
                    f"peer={peer} music={c.get('music')} "
                    f"voice={c.get('voice')} docs={c.get('docs')} "
                    f"title={info.get('title')!r}"
                )
            except Exception as exc:  # noqa: BLE001
                row["ok"] = False
                row["error"] = str(exc)
                print(f"FAIL #{ch['id']:<2} {ch['slug']:<22} {exc}")
            results.append(row)
            time.sleep(0.35)

        context.close()

    INVENTORY_JSON.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nWrote {INVENTORY_JSON}")
    ok = sum(1 for r in results if r.get("ok"))
    print(f"Joined/opened {ok}/{len(results)} channels in the web session.")
    return 0 if ok == len(results) else 1


def open_invite_channel_compat(page, invite_hash: str, log=print) -> dict:
    """Join/open invite using rootScope managers (compatible with newer Eitaa Web).

    Does not modify scripts/eitaa_download.py — newer builds expect setPeer({peerId})
    and keep apiManager under rootScope.managers.
    """
    log(f"Opening invite hash {invite_hash}...")
    inject_manager_shims(page)
    info = page.evaluate(
        """(hash) => (async () => {
          const api = (typeof apiManager !== 'undefined' && apiManager)
            || (rootScope && rootScope.managers && rootScope.managers.apiManager);
          const chats = (typeof appChatsManager !== 'undefined' && appChatsManager)
            || (rootScope && rootScope.managers && rootScope.managers.appChatsManager);
          const im = (typeof appImManager !== 'undefined' && appImManager)
            || (rootScope && rootScope.managers && rootScope.managers.appImManager);
          if (!api || !api.invokeApi) throw new Error('apiManager missing');
          if (!im || !im.setPeer) throw new Error('appImManager.setPeer missing');

          const setPeer = async (peerId) => {
            try {
              await im.setPeer({peerId});
            } catch (e1) {
              try {
                await im.setPeer(peerId);
              } catch (e2) {
                throw e2;
              }
            }
          };

          const inv = await api.invokeApi('messages.checkChatInvite', {hash});
          let chat = inv.chat || (inv.channel ? inv.channel : null);
          let via = inv._;
          if (!chat) {
            await api.invokeApi('messages.importChatInvite', {hash});
            const again = await api.invokeApi('messages.checkChatInvite', {hash});
            chat = again.chat;
            via = again._;
            if (!chat) throw new Error('invite has no chat after import: ' + (again._ || ''));
          } else {
            try {
              await api.invokeApi('messages.importChatInvite', {hash});
            } catch (e) {
              // already a member
            }
          }
          if (chats && chats.saveApiChat) chats.saveApiChat(chat);
          const peerId = -Math.abs(Number(chat.id));
          await setPeer(peerId);
          return {
            peerId,
            title: chat.title || '',
            chatId: Number(chat.id),
            via,
          };
        })()""",
        invite_hash,
    )
    page.wait_for_timeout(2500)
    peer = page.evaluate(
        """() => {
          try {
            return (appImManager && appImManager.chat && appImManager.chat.peerId)
              || (rootScope && rootScope.managers && rootScope.managers.appImManager
                  && rootScope.managers.appImManager.chat
                  && rootScope.managers.appImManager.chat.peerId)
              || null;
          } catch (e) { return null; }
        }"""
    )
    if not peer:
        # Fall back to the peer we just opened even if UI chat pointer is slow.
        peer = info.get("peerId")
    if not peer:
        raise RuntimeError(f"invite opened but peerId missing: {info!r}")
    log(
        f"  channel {info.get('title')!r} peerId={peer} "
        f"(chatId={info.get('chatId')}, {info.get('via')})"
    )
    return info


def inject_manager_shims(page) -> bool:
    """Expose rootScope.managers.* as legacy globals expected by eitaa_download.py.

    Newer Eitaa Web builds keep managers under rootScope.managers and no longer
    put bare `apiManager` / `appMessagesManager` on window. The main downloader
    still uses those names; shimming here avoids changing eitaa_download.py.
    """
    return bool(
        page.evaluate(
            """() => {
              try {
                const m = rootScope && rootScope.managers;
                if (!m || !m.apiManager) return false;
                // Never overwrite the UI appImManager — worker managers break setPeer.
                const names = [
                  'apiManager',
                  'appChatsManager',
                  'appMessagesManager',
                  'appPeersManager',
                ];
                for (const name of names) {
                  if (m[name] && typeof window[name] === 'undefined') {
                    window[name] = m[name];
                  }
                }
                return typeof window.apiManager !== 'undefined'
                  && typeof window.apiManager.invokeApi === 'function';
              } catch (e) {
                return false;
              }
            }"""
        )
    )


def wait_for_api_manager(page, timeout: float = 90.0, log=print) -> bool:
    """Wait until Eitaa managers are available (and shimmed onto window)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if inject_manager_shims(page):
            return True
        page.wait_for_timeout(1000)
    log("apiManager did not become ready in time")
    return False


def collect_jobs_via_get_search(
    page,
    out_dir: Path,
    *,
    peer_id: int,
    max_pages: int,
    dry_run: bool,
    limit: int,
    log=print,
) -> tuple[list[dict], int, int, int]:
    """List audio via getHistory + getMessageByPeer and build /stream/ URLs.

    Newer Eitaa Web proxies managers to a worker: getSearch throws
    `n[i][t][s] is not a function`, and DOM play-to-/stream/ materialize fails.
    getHistory({peerId,...}) still works; awaiting getMessageByPeer yields docs.
    """
    from scripts.eitaa_download import (  # noqa: WPS433
        AUDIO_EXTS,
        build_stream_url,
        sanitize_filename,
    )

    inject_manager_shims(page)
    log(f"Listing channel audio via getHistory (peerId={peer_id})...")
    raw = page.evaluate(
        """(args) => (async () => {
          const {peerId, maxPages} = args;
          const mgr = (typeof appMessagesManager !== 'undefined' && appMessagesManager)
            || (rootScope && rootScope.managers && rootScope.managers.appMessagesManager);
          if (!mgr || !mgr.getHistory) throw new Error('appMessagesManager.getHistory missing');

          const frToArr = (fr) => {
            if (fr instanceof Uint8Array) return Array.from(fr);
            if (ArrayBuffer.isView(fr)) {
              return Array.from(new Uint8Array(fr.buffer, fr.byteOffset, fr.byteLength));
            }
            if (Array.isArray(fr)) return fr.slice();
            return [];
          };

          const seen = new Set();
          const items = [];
          const errors = [];
          let pages = 0;
          let scanned = 0;
          let offsetId = 0;
          for (let page = 0; page < maxPages; page++) {
            pages++;
            let r;
            try {
              r = await mgr.getHistory({
                peerId,
                offsetId,
                offsetDate: 0,
                limit: 50,
                addOffset: 0,
              });
            } catch (e) {
              errors.push(String(e && (e.message || e.type || e.error_message) || e));
              break;
            }
            const hist = [...(r.history || [])];
            if (!hist.length) break;
            for (const mid of hist) {
              scanned++;
              try {
                const msg = await mgr.getMessageByPeer(peerId, mid);
                const doc = msg && msg.media && msg.media.document;
                if (!doc) continue;
                const mime = doc.mime_type || '';
                const name = doc.file_name || '';
                const attrs = doc.attributes || [];
                const isAudio = mime.startsWith('audio/')
                  || /\\.(mp3|m4a|ogg|opus|aac|flac|wav)$/i.test(name)
                  || attrs.some((a) => a && a._ === 'documentAttributeAudio');
                if (!isAudio) continue;
                const key = String(doc.id);
                if (seen.has(key)) continue;
                seen.add(key);
                const idNum = typeof doc.id === 'bigint' ? Number(doc.id) : Number(doc.id);
                items.push({
                  mid: Number(mid),
                  date: Number(msg.date || 0),
                  fileName: name,
                  size: Number(doc.size),
                  dcId: doc.dc_id,
                  id: Number.isFinite(idNum) ? idNum : String(doc.id),
                  access_hash: String(doc.access_hash),
                  file_reference: frToArr(doc.file_reference),
                  mimeType: mime || 'audio/mpeg',
                });
              } catch (e) {
                errors.push(String(e && (e.message || e) || e));
              }
            }
            const oldest = Number(hist[hist.length - 1]);
            if (!oldest || oldest === offsetId) break;
            offsetId = oldest;
            if (r.isEnd || hist.length < 50) break;
          }
          return {pages, scanned, items, errors};
        })()""",
        {"peerId": peer_id, "maxPages": max_pages},
    )
    if raw.get("errors"):
        log(f"  getHistory errors: {raw['errors'][:3]}")
    log(
        f"  history pages={raw.get('pages')} scanned={raw.get('scanned')} "
        f"audio={len(raw.get('items') or [])}"
    )

    jobs_list: list[dict] = []
    skipped = filtered = failed = 0
    catalog: list[dict] = []

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
        target = out_dir / filename
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
            jobs_list.append(
                {"filename": filename, "url": None, "size": size, "date": date}
            )
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
                jobs_list.append(
                    {"filename": filename, "url": url, "size": size, "date": date}
                )
                log(f"  queued   {filename} ({size} bytes)")
            except Exception as exc:  # noqa: BLE001
                log(f"  failed   {filename}: {str(exc).splitlines()[0]}")
                failed += 1
        if limit and len(jobs_list) >= limit:
            log(f"  collect limit {limit} reached")
            break

    catalog_path = out_dir / "catalog.json"
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
    merged = sorted(
        by_name.values(), key=lambda r: (int(r.get("date") or 0), r["filename"])
    )
    catalog_path.write_text(
        json.dumps({"items": merged}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log(f"  wrote catalog with {len(merged)} item(s)")
    return jobs_list, skipped, filtered, failed


def download_stream_via_api(
    page,
    url: str,
    target: Path,
    timeout: float,
    log=print,
):
    """Range-download a /stream/ URL via page.evaluate(fetch) with strong retries.

    Eitaa /stream/ is served by the page service worker (MTProto). Playwright's
    APIRequest bypasses that and gets the SPA HTML, so we must fetch in-page.
    """
    import base64

    from scripts.eitaa_download import (  # noqa: WPS433
        ALIGN_CHUNK,
        AUDIO_EXTS,
        STREAM_CHUNK,
        parse_stream_meta,
        sanitize_filename,
    )

    meta = parse_stream_meta(url)
    size = int(meta.get("size") or 0)
    if size <= 0:
        raise RuntimeError(f"stream meta missing size: {meta!r}")

    suggested = meta.get("fileName") or target.name
    target = target.with_name(sanitize_filename(suggested))
    if not target.name.lower().endswith(AUDIO_EXTS):
        target = target.with_name(target.name + ".mp3")

    tmp = target.with_suffix(target.suffix + ".part")
    start_at = tmp.stat().st_size if tmp.exists() else 0
    if start_at > size:
        tmp.unlink()
        start_at = 0
    if start_at and start_at % ALIGN_CHUNK != 0:
        start_at = start_at - (start_at % ALIGN_CHUNK)
        with tmp.open("rb+") as out:
            out.truncate(start_at)

    log(
        f"           stream size={size} bytes"
        + (f" resume@{start_at}" if start_at else "")
    )
    got = start_at
    deadline = time.time() + timeout
    mode = "ab" if start_at else "wb"
    with tmp.open(mode) as out:
        offset = start_at
        while offset < size:
            if time.time() > deadline:
                raise RuntimeError(f"timed out after {timeout:g}s at {got}/{size}")
            end = min(offset + STREAM_CHUNK - 1, size - 1)
            last_err = None
            data = b""
            for attempt in range(8):
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
                            // Reject SPA HTML fallback (bad /stream/ auth).
                            if (bytes.length >= 15) {
                              const head = String.fromCharCode(
                                ...bytes.slice(0, 15)
                              ).toLowerCase();
                              if (head.startsWith('<!doctype html')
                                  || head.startsWith('<html')) {
                                throw new Error('HTTP stream returned HTML');
                              }
                            }
                            let s = '';
                            const step = 0x8000;
                            for (let i = 0; i < bytes.length; i += step) {
                              s += String.fromCharCode.apply(
                                null, bytes.subarray(i, i + step)
                              );
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
                    if any(
                        s in msg
                        for s in (
                            "HTTP 408",
                            "HTTP 429",
                            "HTTP 5",
                            "Failed to fetch",
                            "stream returned HTML",
                            "Timeout",
                            "timeout",
                        )
                    ):
                        time.sleep(1.5 * (attempt + 1))
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


def cmd_download(
    channels: list[dict],
    *,
    out_root: Path,
    headless: bool,
    dry_run: bool,
    renumber_after: bool,
    jobs: int,
    search_pages: int,
    limit: int,
    settle: float,
) -> int:
    """Download missing channels in one Playwright session (no subprocess).

    Spawning eitaa_download.py per channel was racing the Chromium profile and
    often hit `apiManager is not defined`. Keeping one persistent session avoids
    that while still using helpers from eitaa_download.py unchanged.
    """
    sys.path.insert(0, str(ROOT))
    from scripts.eitaa_download import (  # noqa: WPS433
        DEFAULT_PROFILE,
        WEB_CLIENT,
        open_client,
        open_context,
        parse_invite_hash,
        renumber_by_upload_date,
        require_playwright,
    )

    sync_playwright = require_playwright()
    failures = 0
    profile = Path(DEFAULT_PROFILE).expanduser()

    with sync_playwright() as playwright:
        context = open_context(
            playwright,
            profile,
            headless=headless,
            downloads=Path("/tmp/eitaa_bayat_dl"),
        )
        page = context.pages[0] if context.pages else context.new_page()
        state = open_client(page, WEB_CLIENT, settle, log=print)
        if state != "chats":
            context.close()
            print(
                "Eitaa web session is not logged in. Run:\n"
                "  python scripts/eitaa_download.py --login"
            )
            return 1
        if not wait_for_api_manager(page, timeout=max(settle, 90.0), log=print):
            context.close()
            print("Eitaa web managers never became ready.")
            return 1

        for ch in channels:
            out_dir = out_root / ch["slug"]
            out_dir.mkdir(parents=True, exist_ok=True)
            invite = ch["invite"]
            h = parse_invite_hash(invite)
            print("\n===", ch["id"], ch["slug"], ch["title_fa"], "===")
            try:
                if not wait_for_api_manager(page, timeout=60.0, log=print):
                    raise RuntimeError("apiManager not ready before invite")
                info = open_invite_channel_compat(page, h, log=print)
                peer = info.get("peerId")
                if not peer:
                    raise RuntimeError(f"invite opened but peerId missing: {info!r}")
                # Prefer getHistory+getMessageByPeer over DOM scroll / getSearch;
                # materialize via .audio-toggle and getSearch fail on current Web.
                jobs_list, skipped, filtered, resolve_failed = collect_jobs_via_get_search(
                    page,
                    out_dir,
                    peer_id=int(peer),
                    max_pages=max(search_pages, 40),
                    dry_run=dry_run,
                    limit=limit,
                    log=print,
                )
                print(f"Queued {len(jobs_list)} file(s) for download.")
                downloaded = 0
                failed = resolve_failed
                if dry_run:
                    for job in jobs_list:
                        print(f"  would get {job['filename']}")
                else:
                    for index, job in enumerate(jobs_list, start=1):
                        target = out_dir / job["filename"]
                        print(f"  download [{index}/{len(jobs_list)}] {target.name}")
                        last_err = None
                        for attempt in range(1, 8):
                            try:
                                # On later retries, drop a corrupt trailing chunk.
                                if attempt > 1:
                                    part = target.with_suffix(target.suffix + ".part")
                                    # Also handle sanitized name used inside downloader.
                                    from scripts.eitaa_download import (  # noqa: WPS433
                                        ALIGN_CHUNK,
                                        sanitize_filename,
                                    )

                                    candidates = [part]
                                    alt = target.with_name(
                                        sanitize_filename(target.name)
                                    ).with_suffix(target.suffix + ".part")
                                    candidates.append(alt)
                                    for p in candidates:
                                        if p.exists() and p.stat().st_size >= ALIGN_CHUNK:
                                            new_size = p.stat().st_size - ALIGN_CHUNK
                                            new_size -= new_size % ALIGN_CHUNK
                                            with p.open("rb+") as fh:
                                                fh.truncate(new_size)
                                            print(
                                                f"           trimmed part to {new_size}"
                                            )
                                            break
                                saved, _ = download_stream_via_api(
                                    page, job["url"], target, 600.0, log=print
                                )
                                print(
                                    f"           saved "
                                    f"({saved.stat().st_size / 1_048_576:.1f} MB)"
                                )
                                downloaded += 1
                                last_err = None
                                break
                            except Exception as exc:  # noqa: BLE001
                                last_err = str(exc).splitlines()[0]
                                transient = any(
                                    s in last_err
                                    for s in (
                                        "Failed to fetch",
                                        "HTTP 408",
                                        "HTTP 429",
                                        "HTTP 5",
                                        "timed out",
                                        "Timeout",
                                        "incomplete download",
                                        "ECONNRESET",
                                    )
                                )
                                if transient and attempt < 7:
                                    wait = min(30.0, 3.0 * attempt)
                                    print(
                                        f"           retry {attempt}/7 "
                                        f"after {wait:g}s: {last_err}"
                                    )
                                    time.sleep(wait)
                                    continue
                                print(f"           failed: {last_err}")
                                failed += 1
                                break
                        time.sleep(1.5)
                    if renumber_after and not dry_run:
                        try:
                            renumber_by_upload_date(out_dir, log=print)
                        except Exception as exc:  # noqa: BLE001
                            print(f"Renumber skipped: {exc}")
                print(
                    f"Done {ch['slug']}: downloaded={downloaded} "
                    f"skipped={skipped} failed={failed} filtered={filtered}"
                )
                if failed or not (downloaded or skipped or dry_run):
                    if failed or (not dry_run and downloaded == 0 and skipped == 0):
                        failures += 1
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"FAIL {ch['slug']}: {exc}")
            time.sleep(0.5)

        context.close()

    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Join/inventory/download Bayat private Eitaa channels via invite "
            "links. Leaves eitaa_download.py unchanged."
        )
    )
    parser.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG),
        help=f"Invite catalog JSON (default: {DEFAULT_CATALOG})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print catalog ids/slugs and exit.",
    )
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="Join each invite in the web session and count audio posts.",
    )
    parser.add_argument(
        "--download",
        default=None,
        metavar="SPEC",
        help="Download by id/slug/comma-list, or 'all'. Uses eitaa_download.py.",
    )
    parser.add_argument(
        "--force-skipped",
        action="store_true",
        help="Also download catalog entries marked skip_download "
             "(leghaallah / sermaknoon / marefat_nafs).",
    )
    parser.add_argument(
        "--out-root",
        default=str(DEFAULT_OUT_ROOT),
        help=f"Parent folder for courses (default: {DEFAULT_OUT_ROOT})",
    )
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--renumber-after",
        action="store_true",
        help="Pass through to eitaa_download.py (NNN_ oldest first).",
    )
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--search-pages", type=int, default=80)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--settle", type=float, default=90.0)
    args = parser.parse_args()

    channels = load_catalog(Path(args.catalog).expanduser())

    if args.list:
        return cmd_list(channels)

    if args.inventory:
        # Inventory only channels that are not already on disk / skip_download,
        # unless --force-skipped.
        to_check = resolve_selection(
            channels,
            "all",
            include_skipped=args.force_skipped,
            out_root=Path(args.out_root).expanduser(),
        )
        if not to_check:
            print("Nothing to inventory (all channels already on disk).")
            return 0
        print(f"Inventorying {len(to_check)} missing channel(s)…")
        return cmd_inventory(to_check, headless=args.headless, settle=args.settle)

    if args.download:
        selected = resolve_selection(
            channels,
            args.download,
            include_skipped=args.force_skipped,
            out_root=Path(args.out_root).expanduser(),
        )
        if not selected:
            sys.exit("No channels selected (all matched entries are skipped).")
        return cmd_download(
            selected,
            out_root=Path(args.out_root).expanduser(),
            headless=args.headless,
            dry_run=args.dry_run,
            renumber_after=args.renumber_after,
            jobs=args.jobs,
            search_pages=args.search_pages,
            limit=args.limit,
            settle=args.settle,
        )

    parser.print_help()
    print(
        "\nTip: phone join ≠ web session. Run --inventory first so invite "
        "hashes are imported into ~/.eitaa_playwright_profile, then --download."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
