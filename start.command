#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Install Python 3 from python.org, then retry."; exit 1; }
command -v npm >/dev/null || { echo "Install Node.js LTS from nodejs.org, then retry."; exit 1; }
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -q -r requirements.txt
(cd frontend && npm ci --no-audit --no-fund && npm run build)
echo "Open http://localhost:8000 in your browser. Press Control-C to stop."
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
