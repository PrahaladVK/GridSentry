#!/usr/bin/env bash
set -e

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
backend="$root/backend"
frontend="$root/frontend"

if [ ! -f "$backend/.venv/bin/python" ] && [ ! -f "$backend/.venv/Scripts/python.exe" ]; then
  echo "Creating backend virtual environment..."
  python3 -m venv "$backend/.venv"
fi

if [ -f "$backend/.venv/bin/python" ]; then
  venv_python="$backend/.venv/bin/python"
else
  venv_python="$backend/.venv/Scripts/python.exe"
fi

echo "Installing backend dependencies..."
"$venv_python" -m pip install -q -r "$backend/requirements.txt"

if [ ! -f "$backend/artifacts/gridsentry.db" ]; then
  echo "Seeding database and training models (first run, a few minutes)..."
  (cd "$backend" && "$venv_python" seed.py)
fi

if [ ! -d "$frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$frontend" && npm install)
fi

echo "Starting backend on http://127.0.0.1:8000 ..."
(cd "$backend" && "$venv_python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
backend_pid=$!

echo "Starting frontend on http://localhost:5173 ..."
(cd "$frontend" && npm run dev) &
frontend_pid=$!

trap "kill $backend_pid $frontend_pid 2>/dev/null" EXIT
echo "GridSentry is running. Press Ctrl+C to stop it."
wait
