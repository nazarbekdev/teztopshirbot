#!/usr/bin/env bash
# 2-reel (chat hikoya, kurs ishi) yig'ish.
#   ./make_reel2.sh <ishchi_papka> <tts_python> <playwright_python>
set -euo pipefail
W="$1"; TTS_PY="$2"; PW_PY="$3"; HERE="$(cd "$(dirname "$0")" && pwd)"; mkdir -p "$W" "$HERE/out"
"$TTS_PY" "$HERE/build_timeline2.py" "$W"
rm -rf "$W/frames2"
"$PW_PY" "$HERE/render_frames2.py" "$W" 30
"$TTS_PY" "$HERE/mix_audio2.py" "$W"
ffmpeg -y -loglevel error -framerate 30 -i "$W/frames2/f%05d.jpg" -i "$W/mix2.wav" -af "loudnorm=I=-14:TP=-1.5:LRA=9" \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -profile:v high -c:a aac -b:a 192k -ar 44100 -movflags +faststart \
  -shortest "$HERE/out/teztopshir-reel2-kursishi.mp4"
echo "tayyor: $HERE/out/teztopshir-reel2-kursishi.mp4"
