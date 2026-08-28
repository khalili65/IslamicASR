#!/usr/bin/env bash
# Upload lecture audio to Cloudflare R2 for production playback.
#
# Prerequisites:
#   export PATH="$HOME/.local/node/bin:$PATH"
#   npx wrangler login
#   export R2_BUCKET=islamic-asr-media
#
# Usage (from repo root):
#   ./website/scripts/upload_r2.sh
#   ./website/scripts/upload_r2.sh Audios/Bayat/marefat_nafs
#   ./website/scripts/upload_r2.sh Audios/Bayat/marefat_nafs/001

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PATH="${HOME}/.local/node/bin:${PATH}"

BUCKET="${R2_BUCKET:-islamic-asr-media}"
SRC="${1:-Audios/Bayat}"

if [[ ! -d "$SRC" ]]; then
  echo "Not a directory: $SRC" >&2
  exit 1
fi

echo "Bucket : $BUCKET"
echo "Source : $SRC"
echo

uploaded=0
while IFS= read -r -d '' file; do
  # Normalize to path relative to Audios/
  rel="${file}"
  case "$rel" in
    Audios/*) rel="${rel#Audios/}" ;;
    ./Audios/*) rel="${rel#./Audios/}" ;;
  esac

  lecturer_raw="$(printf '%s' "$rel" | cut -d/ -f1)"
  lecturer="$(printf '%s' "$lecturer_raw" | tr '[:upper:]' '[:lower:]')"
  rest="$(printf '%s' "$rel" | cut -d/ -f2-)"
  key="${lecturer}/${rest}"

  # Prefer NNN_play.m4a over the raw mp3 when both exist.
  if [[ "$file" == *.mp3 ]]; then
    session_dir="$(dirname "$file")"
    session_id="$(basename "$session_dir")"
    preferred="${session_dir}/${session_id}_play.m4a"
    if [[ -f "$preferred" ]]; then
      continue
    fi
  fi

  echo "→ r2://${BUCKET}/${key}"
  npx --yes wrangler r2 object put "${BUCKET}/${key}" --file="$file" --remote
  uploaded=$((uploaded + 1))
done < <(find "$SRC" \( -name '*_play.m4a' -o -name '*.mp3' \) -type f -print0 | sort -z)

echo
echo "Uploaded $uploaded object(s)."
echo "Set Cloudflare Pages env NEXT_PUBLIC_MEDIA_BASE to your R2 public URL (no trailing slash)."
