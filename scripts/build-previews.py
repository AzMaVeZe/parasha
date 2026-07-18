#!/usr/bin/env python3
"""מייצר תמונת תצוגה מקדימה (עמוד ראשון, PNG) לכל קובץ ב-assets/pdfs.
להריץ אחרי הוספת קבצים: python3 scripts/build-previews.py  (דורש pip install pypdfium2)"""
import os, sys
import pypdfium2 as pdfium

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "assets", "pdfs")
DST = os.path.join(ROOT, "assets", "previews")
WIDTH = 720

os.makedirs(DST, exist_ok=True)
made = skipped = 0
for name in sorted(os.listdir(SRC)):
    if not name.lower().endswith(".pdf"):
        continue
    out = os.path.join(DST, os.path.splitext(name)[0] + ".jpg")
    if os.path.exists(out) and os.path.getmtime(out) > os.path.getmtime(os.path.join(SRC, name)):
        skipped += 1
        continue
    try:
        pdf = pdfium.PdfDocument(os.path.join(SRC, name))
        page = pdf[0]
        scale = WIDTH / page.get_width()
        page.render(scale=scale).to_pil().convert("RGB").save(out, quality=78, optimize=True)
        pdf.close()
        made += 1
    except Exception as e:
        print(f"FAIL {name}: {e}", file=sys.stderr)
print(f"previews: {made} generated, {skipped} up to date")
