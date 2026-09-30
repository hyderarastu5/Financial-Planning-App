#!/usr/bin/env bash
# Starts the backend (http://127.0.0.1:8000) and the frontend (http://localhost:5173).
set -euo pipefail
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:$PATH"

backend/.venv/bin/uvicorn app.main:app --app-dir backend --port 8000 --reload --reload-dir backend/app &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null' EXIT

cd frontend && npm run dev
