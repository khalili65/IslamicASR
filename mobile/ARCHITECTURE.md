# Mobile architecture

Grounded in the current repo (inspected Sep 2026). This is not a greenfield redesign.

---

## 1. What exists today

```
                    ┌─────────────────────────────┐
                    │  website-portal/admin (VPS)  │
                    │  cookie auth · edit JSON/MD  │
                    │  POST /api/publish           │
                    └──────────────┬──────────────┘
                                   │ build_content.py + next build
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
   website/ (Bayat)        website-portal/           Audios/ + Arvan media
   static Next export      static Next export        *_play.m4a
   islamic-asr-web         islamic-asr-portal-web    two media buckets
   islamic-asr-media       islamic-asr-portal-media
```

| Layer | Reality |
| --- | --- |
| CMS | Filesystem: `content/**/*.json`, `Audios/**/*.book.md`, etc. **No database** |
| Public “API” | Static JSON under `apps/web/public/data/` served from Arvan |
| Auth (users) | Public site has **none**. Admin is shared-password cookie. RAG `/ask` has Bearer login |
| Player | Next.js + Zustand + `<audio>` + cue JSON + `findCueIndex` binary search + rAF clock |
| Sites | Two branded static sites; admin publishes either via `?site=` |

There is **no** product REST API for courses/lessons. Mobile must become another
client of the **same published data**, not a second CMS.

---

## 2. Target architecture

```
Portal admin ──publish──► build_content + (new) build_mobile_manifest
                              │
                              ├─► islamic-asr-web (+ Bayat /data)
                              ├─► islamic-asr-portal-web (+ portal /data)
                              └─► unified mobile sync artifacts
                                    (hosted on one stable origin — see SYNC.md)

website  ──► same /data + media
website-portal ──► same /data + media
iOS app  ──► sync + /data + media
Android app ──► sync + /data + media
```

Portal/admin remains the **only** write path. Mobile never writes content.

---

## 3. Framework recommendation: React Native + Expo

### What the codebase actually is

- Both public apps: **Next.js 15, React 19, TypeScript, Zustand, Tailwind**
- Shared mental model: `SessionPayload`, `Cue`, `CourseIndex`, `SiteIndex` in `website/apps/web/src/lib/types.ts`
- Sync player core is **framework-agnostic TypeScript**:
  - `findCueIndex` / `CUE_LEAD_SECONDS` in `lib/format.ts`
  - Zustand player store in `lib/store.ts`
  - `resolveMediaUrl` in `lib/media.ts`
- Zero Dart/Flutter, zero SwiftUI/Kotlin UI shared with the product
- Team already ships Persian RTL UI in React

### Scoring against *this* repo

| Criterion | Expo / RN | Flutter |
| --- | --- | --- |
| Reuse `Cue` / session types | Direct TS share | Rewrite in Dart |
| Port `findCueIndex` + player clock | Copy/share package | Rewrite |
| Match existing Zustand patterns | Same Zustand | Different state story |
| Audio + background playback | `expo-av` / `expo-audio` mature | Also mature |
| Offline file cache | `expo-file-system` | Also fine |
| OTA JS updates (UI fixes without store review) | Expo Updates | CodePush-like extras |
| Hiring / continuity with `website/` | Same stack | New stack |

**Recommendation: React Native with Expo (managed workflow + Expo Router).**

Not because Expo is “popular”, but because almost every non-UI line of the
current player and data model is TypeScript we can reuse, and the product has
no Flutter footprint.

### Explicit non-choices

| Option | Why not (here) |
| --- | --- |
| Flutter | Clean UI toolkit, but **zero reuse** of our TS player/types; would fork the sync logic |
| Native Swift + Kotlin | Two UIs for identical RTL player; contradicts “one codebase” |
| Capacitor wrapping the Next static site | Poor background audio, offline, App Store UX; static export is not a mobile shell |
| Separate Node BFF reinventing courses | Violates “don’t redesign backend / don’t invent a second system” |

---

## 4. One app, all lecturers

Today content is split:

| Site | Lecturers (`sources.audioDirs`) | Media base |
| --- | --- | --- |
| `website` | Bayat | `islamic-asr-media` |
| `website-portal` | Qasemian, Manaee, Shojai | `islamic-asr-portal-media` |

The mobile app should present **one library**: Bayat + Qasemian + Manaee + Shojai
(+ future lecturers), without shipping a new binary when a course is published.

**Preferred approach (minimal disruption to public websites):**

1. Keep the two static websites as they are (separate branding / buckets).
2. At publish time, generate a **unified mobile catalog** that merges both
   `index.json` trees and tags every course/session with its `mediaBase` and
   `dataBase` (which web bucket / CDN path hosts that JSON).
3. Optionally later: add Bayat into `website-portal` `audioDirs` so the portal
   site also lists everyone — nice for web, not required for mobile if the
   unified manifest exists.

Do **not** hardcode lecturer lists in the app binary.

---

## 5. App surface (product)

Mirror the web information architecture, in one place:

1. **Library** — all lecturers → courses → sessions  
2. **Player** — audio + synced cues (same algorithm as web) + chapters  
3. **Text** — book / summary / full text when flags say they exist  
4. **Search** — reuse published search indexes (`/data/search/…`) or a later API  
5. **My list / progress** — device-local first (web uses `localStorage`); account sync only if we add real user auth later  

Out of scope for v1 unless requested: admin editing, publishing, RAG `/ask`.

---

## 6. Player port (behavior parity)

Web player (`website/apps/web/src/components/Player.tsx` and portal twin):

1. Load session JSON + cues JSON (web SSG-embeds cues; mobile **fetches** them).
2. Play audio from `resolveMediaUrl(session.audio.url)` with the correct `mediaBase`.
3. Poll playback position ~every frame (or `expo-av` status callback at high rate).
4. `activeIndex = findCueIndex(cues, currentTime)`.
5. Highlight subtitle stage + transcript list; seek on cue/chapter tap.

Port first into `mobile/packages/player-core` (pure TS, no React Native imports)
so web and mobile can eventually share one package. UI stays RN-specific.

Use the same cue JSON the web uses — **not** browser `<track>` / SRT parsing.
`.vtt` exists in the pipeline but the live web player does not use it.

---

## 7. Auth

| Audience | Today | Mobile v1 |
| --- | --- | --- |
| End users browsing lectures | No auth | No auth (same public content) |
| Admin editors | Cookie + `ADMIN_PASSWORD` | Stay on web admin only |
| RAG ask | Bearer token | Optional later; reuse RAG API |

Do not reuse admin cookie APIs from the phone. Those are CMS endpoints.

If paid / private courses appear later, add a real user auth service once —
still with Portal as content source of truth, not a second content DB.

---

## 8. What we will add to the existing platform (small)

| Addition | Where | Why |
| --- | --- | --- |
| `build_mobile_manifest.py` (or step in `build_content.py`) | `website/tools/` or `mobile/tools/` | Emit unified catalog + sync versions |
| Publish hook | `website-portal/admin` publish pipeline | Rebuild + upload mobile manifests whenever either site publishes |
| Hosting for manifests | One stable CDN prefix (recommend portal web bucket or a dedicated `islamic-asr-mobile` prefix) | App needs one `SYNC_BASE_URL` |

We do **not** need Postgres, a new CMS, or rewriting Arvan upload for v1.

---

## 9. Implementation phases (when coding starts)

1. **Manifest + sync artifacts** from existing `public/data` (see SYNC.md)  
2. **Expo app skeleton** in `mobile/app` — library browse from unified catalog  
3. **Player** — audio + cues parity with web  
4. **Offline** — cache catalog + optional download of audio/cues  
5. **Search / my-list** — parity with web  
6. **Optional** thin `GET /sync?since=` on the admin VPS if static changelog proves awkward  

Stop after phase 1–3 for a usable TestFlight / Play internal build.
