#!/usr/bin/env bash
# מחולל את js/audio-manifest.js מרשימת קובצי השמע ב-assets/audio.
# להריץ אחרי כל הוספה/הסרה של פודקאסט: bash scripts/build-audio-manifest.sh
cd "$(dirname "$0")/.."
{
  echo "// נוצר אוטומטית ע\"י scripts/build-audio-manifest.sh — לא לערוך ידנית"
  echo "window.AUDIO_FILES = ["
  shopt -s nullglob
  for f in assets/audio/*.m4a assets/audio/*.mp3 assets/audio/*.wav; do
    printf " '%s',\n" "${f#assets/audio/}"
  done
  echo "];"
} > js/audio-manifest.js
echo "wrote js/audio-manifest.js ($(grep -c "'" js/audio-manifest.js || true) files)"
