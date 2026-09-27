#!/usr/bin/env bash
# Deploy Manaee RAG API to the Arvan VPS (bayat-admin).
# Run from Mac repo root:
#   bash rag/deploy/deploy_to_vps.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VPS_HOST="${VPS_HOST:-185.204.168.239}"
VPS_USER="${VPS_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
REMOTE="${VPS_USER}@${VPS_HOST}"
SSH=(ssh -i "$SSH_KEY" -o IdentitiesOnly=yes -o ConnectTimeout=20 "$REMOTE")
RSYNC=(rsync -az -e "ssh -i ${SSH_KEY} -o IdentitiesOnly=yes -o ConnectTimeout=20")

cd "$REPO_ROOT"

echo "==> 1/6 sync rag code"
"${RSYNC[@]}" \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'eval/runs/' \
  --exclude 'store/*.log' \
  --exclude 'store/reembed_qwen3.log' \
  --exclude 'eval/bakeoff*.log' \
  rag/ "$REMOTE:/home/ubuntu/IslamASR/rag/"

echo "==> 2/6 sync vector stores (manaee + bayat)"
"${RSYNC[@]}" \
  rag/store/manaee/ "$REMOTE:/home/ubuntu/IslamASR/rag/store/manaee/"
"${RSYNC[@]}" \
  rag/store/manaee_qwen3_8b/ "$REMOTE:/home/ubuntu/IslamASR/rag/store/manaee_qwen3_8b/"
if [ -f rag/store/bayat_qwen3_8b/embeddings.npy ]; then
  "${RSYNC[@]}" \
    rag/store/bayat_qwen3_8b/ "$REMOTE:/home/ubuntu/IslamASR/rag/store/bayat_qwen3_8b/"
else
  echo "  (skip bayat store — not built yet)"
fi

echo "==> 3/6 sync Manaee + Bayat raw .txt (for /source highlight)"
# Preserve path Audios/Manaee → symlink target on Mac is Tadabor_Sobohi/Manaee
"${SSH[@]}" 'mkdir -p /home/ubuntu/IslamASR/Audios/Manaee /home/ubuntu/IslamASR/Audios/Bayat'
"${RSYNC[@]}" \
  --include '*/' \
  --include '*.txt' \
  --exclude '*' \
  Audios/Tadabor_Sobohi/Manaee/ "$REMOTE:/home/ubuntu/IslamASR/Audios/Manaee/"
"${RSYNC[@]}" \
  --include '*/' \
  --include '*.txt' \
  --exclude '*' \
  Audios/Bayat/ "$REMOTE:/home/ubuntu/IslamASR/Audios/Bayat/"

echo "==> 4/6 write env + install deps on VPS"
# Build remote env from local .env without echoing secrets
python3 - <<'PY' > /tmp/islam-asr-rag.env
from pathlib import Path
keys = ("DEEPINFRA_API_KEY", "DEEPINFRA_BASE_URL", "DEEPINFRA_EMBED_MODEL", "RAG_ACCESS_PASSWORD")
vals = {}
for line in Path("/Users/mohammadreza/IslamASR/.env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    if k in keys:
        vals[k] = v
need = ["DEEPINFRA_API_KEY", "RAG_ACCESS_PASSWORD"]
missing = [k for k in need if not vals.get(k)]
if missing:
    raise SystemExit(f"missing in .env: {missing}")
vals.setdefault("DEEPINFRA_BASE_URL", "https://api.deepinfra.com/v1/openai")
vals.setdefault("DEEPINFRA_EMBED_MODEL", "BAAI/bge-m3")
# Also load dotenv into process cwd for rag.config
out = [
    f"{k}={vals[k]}" for k in ("DEEPINFRA_API_KEY", "DEEPINFRA_BASE_URL", "DEEPINFRA_EMBED_MODEL", "RAG_ACCESS_PASSWORD")
]
print("\n".join(out))
PY

scp -i "$SSH_KEY" -o IdentitiesOnly=yes /tmp/islam-asr-rag.env "$REMOTE:/tmp/islam-asr-rag.env"
rm -f /tmp/islam-asr-rag.env
"${SSH[@]}" 'sudo mv /tmp/islam-asr-rag.env /opt/islam-asr-rag.env && sudo chown root:root /opt/islam-asr-rag.env && sudo chmod 600 /opt/islam-asr-rag.env'
# Mirror into repo .env so rag.config load_dotenv works even without EnvironmentFile alone
"${SSH[@]}" 'sudo grep -E "^(DEEPINFRA_|RAG_)" /opt/islam-asr-rag.env | sudo tee /home/ubuntu/IslamASR/.env >/dev/null && sudo chown ubuntu:ubuntu /home/ubuntu/IslamASR/.env && sudo chmod 600 /home/ubuntu/IslamASR/.env'

"${SSH[@]}" 'cd /home/ubuntu/IslamASR && .venv/bin/pip install -q --index-url https://pypi.org/simple --trusted-host pypi.org --trusted-host files.pythonhosted.org -r rag/requirements.txt'

echo "==> 5/6 systemd + nginx"
scp -i "$SSH_KEY" -o IdentitiesOnly=yes \
  rag/deploy/islam-asr-rag.service \
  rag/deploy/nginx-rag.conf.snippet \
  "$REMOTE:/tmp/"
"${SSH[@]}" 'sudo mv /tmp/islam-asr-rag.service /etc/systemd/system/islam-asr-rag.service
sudo mkdir -p /etc/nginx/snippets
sudo mv /tmp/nginx-rag.conf.snippet /etc/nginx/snippets/islam-asr-rag.conf
# Inject include into default server if missing
if ! grep -q "islam-asr-rag.conf" /etc/nginx/sites-enabled/default; then
  sudo python3 - <<"PY"
from pathlib import Path
p = Path("/etc/nginx/sites-enabled/default")
text = p.read_text()
needle = "\tlocation / {\n"
inject = "\tinclude snippets/islam-asr-rag.conf;\n\n"
if "islam-asr-rag.conf" not in text:
    if needle in text:
        text = text.replace(needle, inject + needle, 1)
    else:
        text = text.replace("server {", "server {\n\tinclude snippets/islam-asr-rag.conf;\n", 1)
    p.write_text(text)
    print("nginx include added")
else:
    print("nginx include already present")
PY
fi
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable islam-asr-rag
sudo systemctl restart islam-asr-rag
sudo systemctl reload nginx
'

echo "==> 6/6 health check"
sleep 2
"${SSH[@]}" 'systemctl is-active islam-asr-rag; curl -s http://127.0.0.1:8001/health; echo; curl -s http://127.0.0.1/rag/health; echo'
curl -s --max-time 15 "http://${VPS_HOST}/rag/health" || true
echo
echo "Done. API public: http://${VPS_HOST}/rag"
echo "Rebuild portal with:"
echo "  NEXT_PUBLIC_RAG_API_URL=http://${VPS_HOST}/rag npm run build"
