"""מוסיף עמודים ריקים בסוף ה-PDF עד כפולה של 4 (דרישת בוקפוד). python3 book/pad.py book.pdf"""
import sys

import pymupdf

doc = pymupdf.open(sys.argv[1])
n = len(doc)
add = (-n) % 4
for _ in range(add):
    r = doc[-1].rect
    doc.new_page(width=r.width, height=r.height)
if add:
    doc.saveIncr() if doc.can_save_incrementally() else None
print(f'→ {n + add} (+{add} ריקים)')
