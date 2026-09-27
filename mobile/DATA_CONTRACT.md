# Mobile data contract

Mobile consumes the **same JSON the websites already publish**. Do not invent
parallel lesson schemas. Types today live in:

- `website/apps/web/src/lib/types.ts`
- (portal copy) `website-portal/apps/web/src/lib/types.ts`

Prefer extracting a shared package later; until then, treat the website types
as canonical.

---

## Discovery (web today)

| Resource | Path |
| --- | --- |
| Site index | `/data/index.json` |
| Course | `/data/{lecturer}/{course}/course.json` |
| Session | `/data/{lecturer}/{course}/{id}.json` |
| Cues | `/data/{lecturer}/{course}/{id}.cues.json` |
| Words (unused by web player UI) | `…/{id}.words.json` |
| Book / summary | `…/{id}.book.md`, `…/{id}.summary.md` |
| Search | `/data/search/catalog.json`, `/data/search/{lecturer}.json` |

### Media

Session `audio.url` looks like:

`/audio/{lecturer}/{course}/{id}/{id}_play.m4a`

Resolve:

`{mediaBase}/{lecturer}/{course}/{id}/{id}_play.m4a`

| Site | `mediaBase` |
| --- | --- |
| website (Bayat) | `https://islamic-asr-media.s3.ir-thr-at1.arvanstorage.ir` |
| website-portal | `https://islamic-asr-portal-media.s3.ir-thr-at1.arvanstorage.ir` |

---

## Core shapes (abridged)

### `SiteIndex` (`index.json`)

- `mode`: `"single-lecturer"` \| `"portal"`
- `lecturers[]`: `slug`, `name`, `title`, `bio`, `avatar`, `courses[]`
- Course entries: `slug`, `title`, `description`, `cover`, `sessionCount`, …

### `CourseIndex` (`course.json`)

- `lecturer`, `slug`, `title`, `sessions[]` with `id`, `title`, `duration`, `hasTranscript`, …

### `SessionPayload` (`{id}.json`)

- Identity: `id`, `lecturer`, `course`, `title`, `summary`
- Flags: `hasBook`, `hasSummary`, `hasTranscript`, `subtitleSource`, …
- `audio`: `{ url, duration, … } | null`
- `subtitles.fa`: `{ vtt, cues, words }` filenames
- `chapters[]`: `{ index, title, start, end }`
- `previous` / `next` session ids

### `CuesFile` (`{id}.cues.json`)

```ts
{
  version: number;
  sessionId: string;
  lang: string;
  duration: number;
  chapters: Chapter[];
  cues: Array<{
    i: number;
    start: number;
    end: number;
    text: string;
    kind: "speech" | "quote";
    chapter: number | null;
    block: number;
    translation?: string;
  }>;
}
```

Player sync: binary search on `start`/`end` vs playhead (`findCueIndex`).

---

## Mobile-only wrapper

See [SYNC.md](./SYNC.md) for `manifest.json` / `sync.json`. Those wrap the
paths above; they do not replace session or cue schemas.

---

## Auth headers

Public lecture JSON/audio: **none**.

Do not send admin cookies from the app.
