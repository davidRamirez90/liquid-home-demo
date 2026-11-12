#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v ffmpeg >/dev/null 2>&1; then echo 'ffmpeg is required. Install it with: brew install ffmpeg' >&2; exit 1; fi
if [ ! -x .venv/bin/python ]; then
  command -v uv >/dev/null 2>&1 || { echo 'Install uv from https://docs.astral.sh/uv/' >&2; exit 1; }
  uv venv --python 3.12
  uv pip install --python .venv/bin/python -r requirements.txt
fi
printf '\nHaven: http://127.0.0.1:8765\nPress Ctrl+C to stop.\n\n'
exec .venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8765
