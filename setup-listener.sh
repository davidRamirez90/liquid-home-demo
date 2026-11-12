#!/bin/sh
set -eu
cd "$(dirname "$0")"
command -v uv >/dev/null 2>&1 || { echo 'Install uv from https://docs.astral.sh/uv/' >&2; exit 1; }
command -v ffplay >/dev/null 2>&1 || { echo 'ffplay is required. Install ffmpeg with: brew install ffmpeg' >&2; exit 1; }
if [ ! -x .venv/bin/python ]; then
  uv venv --python 3.12
  uv pip install --python .venv/bin/python -r requirements.txt
fi
uv pip install --python .venv/bin/python -r requirements-listener.txt
.venv/bin/python -c 'from openwakeword.utils import download_models; download_models(model_names=["hey_jarvis"])'
echo 'Listener setup complete. Start ./start.sh in one terminal and ./listen.sh in another.'
