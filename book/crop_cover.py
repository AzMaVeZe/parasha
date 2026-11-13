"""חותך את cover.pdf למידה המדויקת (cover.size, במ"מ): בוקפוד מבקש גלישה של 3.2 מ"מ בדיוק."""
import os
import sys

import pymupdf

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build', 'out')
W, H = map(float, open(os.path.join(out, 'cover.size')).read().split())
pt = 72 / 25.4
doc = pymupdf.open(os.path.join(out, 'cover.pdf'))
page = doc[0]
page.set_cropbox(pymupdf.Rect(0, 0, W * pt, H * pt))
page.set_mediabox(pymupdf.Rect(0, 0, W * pt, H * pt))
doc.save(os.path.join(out, 'cover-exact.pdf'))
os.replace(os.path.join(out, 'cover-exact.pdf'), os.path.join(out, 'cover.pdf'))
print(f'cover.pdf {W}×{H} מ"מ')
