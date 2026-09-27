# Bayat admin on Arvan VPS

The **public Bayat site** stays on Arvan bucket `islamic-asr-web` (already live).

The **admin panel** must run on a small **Cloud Server (VPS)** — it cannot run on object storage.

## Cost (approximate, Arvan 2026)

| Item | Cost |
| --- | --- |
| VPS **eco-small4** (2 vCPU, 2 GB RAM, 30 GB SSD) | ~€8/month |
| Public site bucket `islamic-asr-web` | Already running — negligible for HTML |
| Media bucket `islamic-asr-media` | Storage + download traffic (existing audio) |
| **Admin only (new)** | **~€8–10/month** for the VM |

Use **2 GB RAM** minimum — Publish runs Python + Next.js build on the server.

## One-time setup on the VPS

1. Create **Ubuntu 22.04** VM on [Arvan Cloud](https://www.arvancloud.ir) (Tehran region).
2. SSH in, install dependencies:

```bash
sudo apt update && sudo apt install -y git nginx nodejs npm python3 python3-venv ffmpeg
# Node 20+ recommended — use nvm if apt node is old
```

3. Clone the repo (or rsync from your Mac):

```bash
git clone <your-repo-url> IslamASR
cd IslamASR
python3 -m venv .venv
.venv/bin/pip install -r website/tools/requirements.txt  # if present
cd website-portal/admin && npm ci && npm run build
```

4. Create `/opt/islam-asr-admin.env`:

```bash
ADMIN_PASSWORD=<strong-password>
REPO_ROOT=/home/ubuntu/IslamASR
SITE_ROOT=/home/ubuntu/IslamASR/website
SITE_LABEL=درس‌گفتارهای استاد بیات
# Arvan keys copied from .env.arvan — or rely on repo .env.arvan on disk
```

5. Copy `deploy/islam-asr-admin.service` to systemd and start (see below).

6. Point `admin.yourdomain.ir` DNS → VPS IP; enable HTTPS with certbot.

## Important: Audios/ on the server

Editors save book/summary into `Audios/Bayat/...`. The VPS needs either:

- Full `Audios/` tree (large), or
- **Git + rsync** from your Mac before/after edits, or
- NFS/sync — your choice.

For a small team, syncing `Audios/Bayat` + `website/content` to the VPS is enough.

## Switch back to portal later

Change on the VPS:

```bash
SITE_ROOT=/home/ubuntu/IslamASR/website-portal
SITE_LABEL=پورتال درس‌گفتارها
```

Restart the service.
