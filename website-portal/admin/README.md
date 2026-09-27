# Portal admin (simple UI for editors)

Password-protected panel for **non-technical editors**: rename courses/sessions, hide sessions, upload lecturer photos, then **Publish** to rebuild the static portal.

This is **not** the public site. It is a small **server app** (Node.js).

---

## Where can it be hosted?

| Place | Works? | Notes |
| --- | --- | --- |
| **Arvan static buckets** (`islamic-asr-portal-web`) | **No** | Only HTML/JS files — no login, no save, no publish |
| **Arvan Cloud VPS / VM** | **Yes — recommended** | Same country, low latency, run `npm run start` |
| **Your Mac (local only)** | Yes | Good for testing; not for collaborators |
| **Random foreign VPS** | Yes | Works but slower in Iran unless CDN |

**Summary:** Public site stays on **Arvan Object Storage**. Admin runs on a **small Arvan VPS** (e.g. 1 CPU, 1–2 GB RAM) at something like `admin.yoursite.ir`.

The VPS needs:

- This git repo (or a deploy copy)
- Node 20+, Python `.venv`, `ffmpeg`
- Env vars: `ADMIN_PASSWORD`, optional Arvan keys for one-click deploy

---

## Local dev

```bash
cd website-portal/admin
cp .env.example .env.local
# edit ADMIN_PASSWORD

npm install
npm run dev
```

Open **http://localhost:3002** → login → edit → **انتشار**.

Publish runs (on the machine where admin runs):

1. `website/tools/build_content.py --site-root website-portal --skip-subtitles`
2. `npm run build` in `website-portal/apps/web`
3. Optionally upload `out/` to Arvan if **آپلود Arvan** is checked

---

## What editors can change

- Lecturer **name**, **title**, **bio**, **photo**
- Course **title**, **description**
- Session **display title** (stored in `course.json` → `titles`)
- **Hide** session (adds to `hidden` — removed from site, audio not deleted)
- **Edit book** (`*.book.md`) and **summary** (`*.summary.md`) — saves to `Audios/`, backs up previous version as `*.prev.md`

New sessions are added via the technical pipeline (audio + ASR), not in admin.

They **cannot** (yet): upload audio, run ASR, add sessions, edit raw transcript / synced subtitles, change player code.

---

## Production on Arvan VPS (outline)

1. Create Ubuntu VM on Arvan Cloud.
2. Clone repo, install Node 20, Python venv, `npm ci` in `admin/` and `apps/web/`.
3. Set `.env.local` + copy `.env.arvan.portal` for deploy keys.
4. Run with **systemd** or **pm2**:

```bash
cd website-portal/admin
npm run build
npm run start   # port 3002
```

5. Point DNS `admin.example.com` → VPS; put **nginx** in front with HTTPS.
6. Restrict by firewall / VPN if possible (admin has one shared password).

---

## Same for `website/` (Bayat)?

This admin targets **website-portal** only. The Bayat single site uses the same `content/` pattern — we can add a site switcher later or duplicate the admin with `SITE_ROOT=website`.

---

## Security notes

- Use a **strong** `ADMIN_PASSWORD`.
- Do not expose admin to the public internet without HTTPS.
- Prefer IP allowlist or VPN for editors if you can.
- Arvan keys on the server only — never in git.
