# Plan: Offline download for a session (تذکار mobile)

Share this with whoever implements the feature.

## Problem

The app currently **streams** audio and **fetches** books/text from remote servers (Arvan). In areas with expensive or weak internet, users cannot reliably listen or read later.

Today’s **دانلود** button only exports via the share sheet (Save to Files). It does **not** keep content for in-app offline use.

## Goal

Add **دانلود برای آفلاین** so the user can download **one session** into app storage and later open/play/read it **without internet**.

## Scope (v1)

- Per **session** only (not whole course yet).
- One clear action on the session player: **دانلود برای آفلاین**.
- When pressed, download and store locally (whatever exists for that session):
  - Audio
  - Book (`.book`)
  - Full text / transcript
  - Summary (recommended; small)
  - Cues/subtitles (recommended so offline play still has synced text)
- After download succeeds, opening that session should prefer **local files** over the network.
- Show clear UI states: not downloaded / downloading (progress) / downloaded / error.
- Allow **حذف دانلود** (delete offline copy) to free storage.
- Prefer Wi‑Fi / warn on cellular before large audio downloads if easy; at least make data/storage cost visible.

## Storage size & user communication (required)

Audio is the heavy part (often tens of MB per session). Users must understand storage impact before downloading.

**Show:**

- Before/during download: approximate size, e.g. «حدود ۴۵ مگابایت» (or total pack size if known).
- A short note that the session will be saved **on the phone** for offline use.
- After download: clear **حذف دانلود** so they can remove it themselves from inside the app.

**Suggested copy (Persian concept):**

> این جلسه برای استفاده آفلاین روی گوشی ذخیره می‌شود (حدود XX مگابایت). در صورت نیاز بعداً می‌توانید آن را از داخل برنامه حذف کنید.

**Do not:**

- Rely on users deleting files from the iOS Files app or phone Settings.
- Use a long scary warning every time — size + short note + in-app delete is enough.

## Out of scope (for now)

- Bundling the whole library into the app install
- Auto-downloading everything
- “Download entire course” (possible later feature)
- Changing the existing share-sheet **دانلود** (TXT/PDF/audio export) — keep it separate from offline download

## Behavior details

1. Streaming remains the default when nothing is downloaded.
2. Offline pack is stored **inside the app**, not only in Files.
3. Bookmarks / “saved” list stay as they are (metadata only); offline is a separate concept.
4. If a file is missing on the server (e.g. no book), download the rest; don’t fail the whole pack unless **audio** fails (audio is the minimum success requirement).
5. Offline sessions should still work for: play audio, open book, open text/summary, show cues if downloaded.
6. Deleting the offline pack must free the space used by that session’s local files.

## UX suggestions

| State | UI |
|-------|-----|
| Not downloaded | Button: **دانلود برای آفلاین** + size hint |
| Downloading | Progress (and cancel if feasible) |
| Downloaded | **دانلود شده** + **حذف دانلود** |
| Error | Short error; allow retry |

Optional later: choose “audio only” vs “full pack”. For v1, one tap = full available pack is fine.

## Acceptance criteria

- [x] User can download the current session while online
- [x] Approximate download/storage size is shown before or at start of download
- [x] User is informed content is stored on the device and can be removed in-app
- [x] After airplane mode / no network, that session still plays and shows downloaded texts
- [x] Undownloaded sessions still need network (same as today)
- [x] User can delete the offline copy from inside the app and free space
- [x] Existing share **دانلود** still works as before

## Implemented (Sep 2026)

- `mobile/app/lib/offlineSession.ts` — offline pack download/delete/local paths
- Player chip **آفلاین** / **حذف** with size confirmation Alert
- Local audio + texts preferred when pack exists; share-sheet **دانلود** unchanged

## Technical notes (current app)

- Expo / React Native app under `mobile/app`
- Player: `LecturePlayer` + `expo-audio` with remote `audioUrl`
- Content URLs come from `dataBase` / `mediaBase` (Arvan) — see `mobile/app/constants/theme.ts` and `mobile/app/lib/api.ts`
- Session audio size may already be available in session JSON (`audio.size`) — use it for the size hint when possible
- Store files in app document storage (persistent) and resolve local paths in the player/document viewer when present
- Keep share-sheet export (`sessionDownload.ts`) separate from this offline store

## Later (not v1)

- Download entire course
- Manage-downloads screen (list all offline sessions + total storage used)
- Audio-only vs full-pack choice
- Auto-cleanup / storage limits
