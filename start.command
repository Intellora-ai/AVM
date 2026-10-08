#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "Install Python 3 from python.org, then retry."; exit 1; }
command -v npm >/dev/null || { echo "Install Node.js LTS from nodejs.org, then retry."; exit 1; }
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -q -r requirements.txt
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}"
(cd frontend && npm ci --no-audit --no-fund && npm run build)
echo "Open http://localhost:8000 in your browser. Press Control-C to stop."
if [[ "${OSTYPE:-}" == darwin* ]]; then
  (for attempt in {1..30}; do
     if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then open http://localhost:8000; break; fi
     sleep 1
   done) &
fi
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
