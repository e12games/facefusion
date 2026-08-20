#!/bin/bash
set -euo pipefail
PORT="${LIANHUAN_PORT:-8092}"
exec /opt/lianhuan/venv/bin/uvicorn app:app --host 127.0.0.1 --port "$PORT" --proxy-headers --forwarded-allow-ips='*'
