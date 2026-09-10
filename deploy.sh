#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/stockintel"
git pull origin main

cd "$HOME/stockintel/backend"
# shellcheck disable=SC1091
source venv/bin/activate
pip install -r requirements.txt
pm2 restart backend --update-env

cd "$HOME/stockintel/frontend"
if [ -f package-lock.json ]; then
  npm install --legacy-peer-deps
fi
NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=1536}" npm run build
mkdir -p .next/standalone/.next
cp -r .next/static .next/standalone/.next/
if [ -d public ]; then
  cp -r public .next/standalone/
fi
pm2 restart frontend --update-env

pm2 status
curl -sS -m 8 http://127.0.0.1:8000/api/v1/health || true
echo
