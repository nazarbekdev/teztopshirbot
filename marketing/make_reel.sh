#!/usr/bin/env bash
# Reelni noldan yig'ish. Talab: ffmpeg, Google Chrome, Python (edge-tts, numpy — alohida venv), playwright (loyiha venv).
#   ./make_reel.sh <ishchi_papka> <tts_python> <playwright_python>
set -euo pipefail
W="$1"; TTS_PY="$2"; PW_PY="$3"; HERE="$(cd "$(dirname "$0")" && pwd)"; mkdir -p "$W" "$HERE/out"
"$TTS_PY" "$HERE/build_timeline.py" "$W"
rm -rf "$W/frames"
"$PW_PY" "$HERE/render_frames.py" "$W" 30
"$TTS_PY" "$HERE/mix_audio.py" "$W"
ffmpeg -y -loglevel error -framerate 30 -i "$W/frames/f%05d.jpg" -i "$W/mix.wav" -c:v libx264 -preset slow -crf 17 \
  -pix_fmt yuv420p -profile:v high -c:a aac -b:a 192k -movflags +faststart -shortest "$HERE/out/teztopshir-reel.mp4"
echo "tayyor: $HERE/out/teztopshir-reel.mp4"
