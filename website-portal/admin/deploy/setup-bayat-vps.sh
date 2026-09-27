#!/usr/bin/env bash
# Run ON the Arvan VPS as root or ubuntu (after git clone).
# Usage: sudo bash setup-bayat-vps.sh /home/ubuntu/IslamASR
set -euo pipefail

REPO="${1:-/home/ubuntu/IslamASR}"
ADMIN_ENV="/opt/islam-asr-admin.env"

echo "==> Installing packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git nginx curl ffmpeg python3 python3-venv python3-pip

if ! command -v node >/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

echo "==> Python venv..."
cd "$REPO"
python3 -m venv .venv
.venv/bin/pip install -q boto3 botocore

echo "==> Admin npm..."
cd "$REPO/website-portal/admin"
npm ci
npm run build

if [[ ! -f "$ADMIN_ENV" ]]; then
  echo "==> Create $ADMIN_ENV with ADMIN_PASSWORD and paths"
  cat >"$ADMIN_ENV" <<EOF
ADMIN_PASSWORD=CHANGE_ME
REPO_ROOT=$REPO
SITE_ROOT=$REPO/website
SITE_LABEL=درس‌گفتارهای استاد بیات
EOF
  chmod 600 "$ADMIN_ENV"
  echo "Edit $ADMIN_ENV then re-run: systemctl restart islam-asr-admin"
fi

echo "==> systemd..."
cp "$REPO/website-portal/admin/deploy/islam-asr-admin.service" /etc/systemd/system/
sed -i "s|/home/ubuntu/IslamASR|$REPO|g" /etc/systemd/system/islam-asr-admin.service
systemctl daemon-reload
systemctl enable islam-asr-admin
systemctl restart islam-asr-admin || true

echo "==> Done. Admin on http://$(hostname -I | awk '{print $1}'):3002"
echo "    Point nginx + HTTPS using deploy/nginx-admin.conf.example"
