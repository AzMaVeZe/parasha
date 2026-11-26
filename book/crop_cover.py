"""חותך את cover.pdf למידה המדויקת (cover.size, במ"מ): בוקפוד מבקש גלישה של 3.2 מ"מ בדיוק."""
import os
import sys

import pymupdf

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build', 'out')
W, H = map(float, open(os.path.join(out, 'cover.size')).read().split())
pt = 72 / 25.4
src = pymupdf.open(os.path.join(out, 'cover.pdf'))
# העמוד שהדפדפן הפיק גדול מהמידה ב-1 מ"מ מימין ומלמטה (cover.py). מעתיקים אותו כווקטור לעמוד
# חדש במידה המדויקת, עם חלון שמתחיל בפינה השמאלית-העליונה (ב-PyMuPDF ציר y יורד מלמעלה).
# קודם שינינו את MediaBox, ששם ציר y עולה מלמטה — וכך נחתך המ"מ מלמעלה ובתחתית נשארה רצועה בצבע הרקע.
doc = pymupdf.open()
page = doc.new_page(width=W * pt, height=H * pt)
page.show_pdf_page(page.rect, src, 0, clip=pymupdf.Rect(0, 0, W * pt, H * pt))
doc.save(os.path.join(out, 'cover-exact.pdf'), garbage=3, deflate=True)
os.replace(os.path.join(out, 'cover-exact.pdf'), os.path.join(out, 'cover.pdf'))
print(f'cover.pdf {W}×{H} מ"מ')
