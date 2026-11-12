#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ] || ! .venv/bin/python -c 'import openwakeword, onnxruntime, sounddevice, webrtcvad, rumps' >/dev/null 2>&1; then
  echo 'Run ./setup-listener.sh first.' >&2
  exit 1
fi
if ! command -v ffplay >/dev/null 2>&1; then echo 'ffplay is required: brew install ffmpeg' >&2; exit 1; fi
printf 'Starting Haven listener. Say "Hey Jarvis" followed by a command.\nUse the Haven menu-bar item to pause or quit.\n'
exec .venv/bin/python listener.py
