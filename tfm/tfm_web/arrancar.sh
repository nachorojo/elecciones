#!/usr/bin/env bash
cd "$(dirname "$0")"
if command -v ollama >/dev/null 2>&1; then
  pgrep -x ollama >/dev/null || (ollama serve >/dev/null 2>&1 &)
  sleep 2
fi
exec python3 app.py "$@"
