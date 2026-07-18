#!/usr/bin/env bash
# מחולל את js/pdf-manifest.js מרשימת הקבצים ב-assets/pdfs.
# יש להריץ אחרי כל הוספה/הסרה של קובץ: bash scripts/build-pdf-manifest.sh
cd "$(dirname "$0")/.."
{
  echo "// נוצר אוטומטית ע\"י scripts/build-pdf-manifest.sh — לא לערוך ידנית"
  echo "window.PDF_FILES = ["
  for f in assets/pdfs/*.pdf assets/pdfs/*.PDF; do
    [ -e "$f" ] && printf " '%s',\n" "${f#assets/pdfs/}"
  done
  echo "];"
} > js/pdf-manifest.js
echo "wrote js/pdf-manifest.js ($(grep -c "'" js/pdf-manifest.js) files)"
