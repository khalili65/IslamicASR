#!/usr/bin/env bash
# Start the lecture website locally.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="${HOME}/.local/node/bin:${PATH}"

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required. Install Node 20+ and retry."
  exit 1
fi

cd "$ROOT/apps/web"

if [ ! -d node_modules/next ]; then
  echo "Installing dependencies…"
  npm install --registry=https://registry.npmmirror.com --ignore-scripts --no-fund --no-audit
fi

# Ensure local audio symlink
mkdir -p public
ln -sfn ../../../../Audios public/audio

echo "Open http://localhost:3000"
echo "Player: http://localhost:3000/bayat/marefat_nafs/001/"
exec npm run dev
