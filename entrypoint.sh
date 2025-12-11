#!/usr/bin/env bash
set -euo pipefail

# Defaults
: "${PORT:=8000}"
: "${HOST:=0.0.0.0}"

echo "Starting uvicorn on ${HOST}:${PORT}"
exec uvicorn image_edit_server:app --host "$HOST" --port "$PORT" --proxy-headers
