#!/bin/bash
set -e

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "=== SpeedHQ → MP4 コンバーター ==="
echo ">>> http://${HOST}:${PORT} で起動中..."
echo ">>> 停止: Ctrl+C"
echo ""

exec uvicorn app:app --host "$HOST" --port "$PORT" --reload
