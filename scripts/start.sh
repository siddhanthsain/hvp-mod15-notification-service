#!/usr/bin/env bash
set -eu

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3.11 -m venv .venv
fi

source .venv/bin/activate

export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/data/tmp/pip-cache}"
mkdir -p "$PIP_CACHE_DIR"

echo "Installing dependencies..."
pip install --no-cache-dir -e ".[dev]" -q

PORT="${PORT:-8015}"
echo "Starting MOD-15 on port $PORT..."
uvicorn hvp_mod15_notification_service.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --app-dir src \
  --reload
