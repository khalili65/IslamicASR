# Content versioning & incremental sync

Goal: publishing a new course or lesson through the Portal updates phones
**without** an App Store / Play release. The app discovers adds/updates via the
backend (published artifacts), not via a hardcoded catalog in the binary.

---

## 1. Constraints from this repo

- Content is files, not rows in a DB.
- Publish already runs `build_content.py` → `public/data/**` → Arvan web bucket.
- Session bodies (especially `.cues.json`) can be large; there may be **hundreds
  or thousands** of sessions over time.
- Two sites / two media buckets must appear as **one library** in the app.

Therefore sync is designed as:

1. A **small, frequently polled** sync document (versions + change list).
2. **On-demand** fetch of session / cues / markdown / audio when the user opens
   or downloads a lesson.

---

## 2. Identifiers

Stable IDs (never change once published):

| Entity | `id` |
| --- | --- |
| Lecturer | `{lecturer}` e.g. `bayat` |
| Course | `{lecturer}/{course}` e.g. `bayat/marefat_nafs` |
| Session | `{lecturer}/{course}/{session}` e.g. `bayat/marefat_nafs/001` |

Each entity carries:

| Field | Meaning |
| --- | --- |
| `contentVersion` | Monotonic int **or** content hash (sha256 of canonical bytes). Prefer **hash** for correctness; expose also `updatedAt` |
| `site` | `website` \| `website-portal` (which tree produced it) |
| `dataBase` | Origin for JSON/MD (e.g. Bayat or portal s3-website URL) |
| `mediaBase` | Arvan media host for that site |

Audio URL in session JSON stays relative (`/audio/...`); the client applies
`mediaBase` the same way `resolveMediaUrl` does on the web.

---

## 3. Artifacts produced at publish time

Suggested output (written under a single mobile prefix, e.g. portal bucket):

```
/data/mobile/
  manifest.json          # full catalog snapshot (compact)
  sync.json              # current global syncVersion + pointer
  changelog.jsonl        # append-only: one JSON object per publish batch
  # optional packed deltas:
  deltas/{syncVersion}.json
```

### `sync.json` (tiny — polled often)

```json
{
  "syncVersion": 1842,
  "generatedAt": "2026-09-26T22:00:00Z",
  "manifestUrl": "/data/mobile/manifest.json",
  "manifestSha256": "…",
  "catalogCounts": { "lecturers": 4, "courses": 40, "sessions": 1200 }
}
```

### `manifest.json` (full metadata, no cue text)

Enough to render lecturer → course → session lists offline after one download:

```json
{
  "syncVersion": 1842,
  "lecturers": [
    {
      "id": "bayat",
      "name": "…",
      "title": "…",
      "avatar": { "url": "…", "dataBase": "https://…islamic-asr-web…" },
      "contentVersion": "a1b2…"
    }
  ],
  "courses": [
    {
      "id": "bayat/marefat_nafs",
      "lecturerId": "bayat",
      "slug": "marefat_nafs",
      "title": "…",
      "cover": { "path": "/images/courses/….png", "dataBase": "…" },
      "sessionCount": 40,
      "contentVersion": "c3d4…",
      "site": "website",
      "dataBase": "https://islamic-asr-web.s3-website.…",
      "mediaBase": "https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir"
    }
  ],
  "sessions": [
    {
      "id": "bayat/marefat_nafs/001",
      "courseId": "bayat/marefat_nafs",
      "index": 1,
      "title": "…",
      "duration": 2926.38,
      "hasTranscript": true,
      "hasBook": true,
      "hasSummary": true,
      "contentVersion": "e5f6…",
      "paths": {
        "session": "/data/bayat/marefat_nafs/001.json",
        "cues": "/data/bayat/marefat_nafs/001.cues.json",
        "book": "/data/bayat/marefat_nafs/001.book.md",
        "summary": "/data/bayat/marefat_nafs/001.summary.md"
      }
    }
  ]
}
```

Cue arrays and markdown bodies are **not** in the manifest. Fetch by `dataBase + paths.*` when needed.

### Changelog / delta (incremental)

Each successful publish appends one record:

```json
{
  "syncVersion": 1842,
  "prevSyncVersion": 1841,
  "generatedAt": "…",
  "upserts": [
    { "kind": "session", "id": "manaee/term1/012", "contentVersion": "…", "paths": { "…" : "…" } },
    { "kind": "course", "id": "manaee/term1", "contentVersion": "…" }
  ],
  "deletes": [
    { "kind": "session", "id": "shojai/old_course/099" }
  ]
}
```

`contentVersion` for a session should hash: session JSON + cues + book + summary
(+ words if we ever use them). Changing only a title in `course.json` bumps the
course entity and any affected session list fields.

---

## 4. Client protocol

### Cold start / reinstall

1. `GET {SYNC_BASE}/data/mobile/sync.json`
2. `GET` full `manifest.json` (or cached if `manifestSha256` matches)
3. Persist to SQLite / MMKV: entities keyed by `id` + `contentVersion`
4. UI reads local DB

### Subsequent opens / pull-to-refresh

```
GET /data/mobile/sync.json
if remote.syncVersion == local.syncVersion → done
else if (remote - local) is small → apply deltas
else → download full manifest and replace
```

### Proposed API shape (static-friendly)

**Phase A (no new server process)** — static files only:

| Call | Behavior |
| --- | --- |
| `GET …/sync.json` | Current version |
| `GET …/deltas/{v}.json` | Changes introduced *at* version `v` |
| Client | For `v = local+1 … remote`, apply each delta; if gap/missing → full manifest |

**Phase B (optional, on existing admin VPS)** — thin read-only route:

```
GET /api/mobile/sync?since=<last_sync_version>
```

Response:

```json
{
  "syncVersion": 1842,
  "since": 1800,
  "complete": true,
  "upserts": [ /* same as changelog upserts */ ],
  "deletes": [ /* … */ ],
  "manifestSha256": "…"
}
```

If `since` is too old or unknown: `{ "complete": false, "syncVersion": 1842, "manifestUrl": "…" }`
and the client falls back to full manifest.

Phase B is sugar over the same files Phase A already writes. Prefer Phase A
first so mobile does not depend on the VPS being up for catalog reads (Arvan
static is already how the websites work).

---

## 5. When versions bump

| Editor action | Entities bumped |
| --- | --- |
| Publish after new session folder in `Audios/` | session + parent course (+ lecturer course list) |
| Edit session title / hide in admin | course (+ session summary fields in manifest) |
| Edit book / summary MD | that session `contentVersion` |
| Rebuild cues / subtitles | that session |
| New lecturer / course | lecturer + course + sessions |
| Hide session | treat as delete from mobile catalog **or** flag `hidden: true` (match web `hidden[]`) |

Hidden sessions should follow web rules: omit from catalog or mark hidden so
the app never shows them.

---

## 6. Unifying Bayat + portal

Builder inputs:

1. `website/apps/web/public/data/index.json` + per-course trees  
2. `website-portal/apps/web/public/data/index.json` + per-course trees  
3. Site defs from `website-portal/admin/src/lib/sites.ts` (`mediaBase`, web origin)

Output: one `manifest.json` with every lecturer. Collision policy: lecturer
slugs must remain globally unique (`bayat`, `qasemian`, …) — already true.

Publish integration:

- After **either** site’s `build_content` + deploy, run `build_mobile_manifest`
  and upload `/data/mobile/*` to the chosen SYNC_BASE (recommend always
  updating from the admin publish job so one button refreshes mobile).

---

## 7. Audio & large files

| Asset | Sync? | Fetch |
| --- | --- | --- |
| Catalog / session metadata | Yes (manifest) | Sync protocol |
| `.cues.json` | Version tracked; body on demand | When opening player or prefetch |
| `.book.md` / `.summary.md` | Same | When opening text tab |
| `*_play.m4a` | Not in sync body | Stream from `mediaBase`; optional offline download queue |

Offline downloads store `contentVersion` beside the file; on sync, if version
changed, invalidate cache and re-fetch.

---

## 8. App Store independence checklist

- [ ] No lecturer/course list compiled into the binary  
- [ ] `SYNC_BASE_URL` is config (env / Expo extra), not content  
- [ ] Opening the app applies sync before or alongside showing cached library  
- [ ] New session appears after Portal publish + manifest upload only  
- [ ] Player features may need app updates; **content never does**

---

## 9. Implementation sketch (later code)

```
website/tools/build_mobile_manifest.py
  --website-data website/apps/web/public/data
  --portal-data  website-portal/apps/web/public/data
  --out          website-portal/apps/web/public/data/mobile
  --prev         (previous manifest for diff)
```

Hook from `website-portal/admin/src/lib/publish.ts` after successful content
build (and upload with `deploy_arvan_web.py` or a small sibling uploader).

Until that script exists, the app can temporarily bootstrap from
`index.json` on both sites — workable for a prototype, not for incremental sync.
