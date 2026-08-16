#!/usr/bin/env python3
"""חותך את תיבת החידה מדפי ה-PDF, לחידות שהניסוח שלהן חסר פשר בלי התמונה.

חלק מהחידות בדפים הן חידות ציור: "מה הקשר של התמונה הזו לכאן?" או חידת רבוס
עם שתי תמונות וכיתוב. הטקסט לבדו חסר משמעות, ולכן חותכים את **התיבה כולה**
ולא תמונה בודדת — כדי לא לאבד כיתוב או תמונה שנייה שהחידה נשענת עליהם.

איתור התיבה: מחפשים את כותרת החידה בעמוד, ואז את המלבן המצויר הקטן ביותר
שמכיל אותה. הגבולות נלקחים מה-PDF עצמו ולא מנוחשים.

הרצה:  python3 scripts/crop-riddle-images.py
פלט:   assets/riddles/<פרשה>.png
"""

import glob
import json
import os
import sys

import pymupdf

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT_DIR = os.path.join(ROOT, 'assets', 'riddles')
DPI = 200

# הפרשות שהחידה בהן תלויה בתמונה. חייב להתאים ל-img ב-js/riddles.js
NEEDS_IMAGE = ['לך לך', 'וירא', 'חיי שרה', 'תולדות', 'ויגש', 'מקץ', 'צו', 'אחרי מות', 'ויקרא']
HEADINGS = ['לקינוח', 'קינוח', 'לסיום חידה', 'חידה']

# חידות שאין סביבן מסגרת מצוירת, ולכן האיתור האוטומטי לא תופס אותן.
# הגבולות נמדדו מהעמוד עצמו (get_image_rects / get_text('blocks')), לא בעין.
# פרשה -> (עמוד 0-based, x0, y0, x1, y1) בנקודות
MANUAL = {
    # קוד QR (160,580-249,670) עם כותרת בכתב יד (214,563-336,594), בלי מסגרת
    'ויקרא': (2, 156, 558, 340, 674),
}

# טקסט זר שנופל בתוך אזור החיתוך ואינו חלק מהחידה — מוסתר לפני הרינדור.
# כאן: הערת שוליים 12 על ועדת וינוגרד, שחולקת שורות עם קוד ה-QR.
REDACT = {
    'ויקרא': [(2, 290, 634, 340, 652)],
}


def find_heading(doc):
    """כותרת החידה יושבת בסוף הדף, ולכן סורקים מהעמוד האחרון אחורה."""
    for pno in range(len(doc) - 1, -1, -1):
        for h in HEADINGS:
            hits = doc[pno].search_for(h)
            if hits:
                return pno, hits[0]
    return None


def enclosing_box(page, head_rect):
    """המלבן המצויר הקטן ביותר שמכיל את הכותרת — היא מסגרת תיבת החידה."""
    page_area = page.rect.width * page.rect.height
    boxes = [d['rect'] for d in page.get_drawings()
             if d['rect'].contains(head_rect)
             and d['rect'].get_area() < page_area * 0.45
             and d['rect'].width > 60 and d['rect'].height > 60]
    return min(boxes, key=lambda r: r.get_area()) if boxes else None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    riddles = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'scripts', 'riddles-source', '*.json'))):
        for r in json.load(open(f)):
            riddles[r['parasha']] = r

    failed = []
    for name in NEEDS_IMAGE:
        rec = riddles.get(name)
        if not rec:
            failed.append(name + ' — אין רשומה'); continue
        doc = pymupdf.open(os.path.join(ROOT, 'assets', 'pdfs', rec['file']))

        if name in MANUAL:
            pno, x0, y0, x1, y1 = MANUAL[name]
            page = doc[pno]
            clip = pymupdf.Rect(x0, y0, x1, y1) & page.rect
        else:
            found = find_heading(doc)
            if not found:
                failed.append(name + ' — לא נמצאה כותרת חידה'); doc.close(); continue
            pno, head = found
            page = doc[pno]
            box = enclosing_box(page, head)
            if box is None:
                failed.append(name + ' — לא נמצאה תיבה עוטפת'); doc.close(); continue
            clip = pymupdf.Rect(box.x0 - 2, box.y0 - 2, box.x1 + 2, box.y1 + 2) & page.rect

        for rpno, rx0, ry0, rx1, ry1 in REDACT.get(name, []):
            if rpno == pno:
                page.add_redact_annot(pymupdf.Rect(rx0, ry0, rx1, ry1), fill=(1, 1, 1))
        if REDACT.get(name):
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE)

        pix = page.get_pixmap(clip=clip, dpi=DPI)
        path = os.path.join(OUT_DIR, name + '.png')
        pix.save(path)
        print('%-10s %s עמ\'%d  %dx%d px  %.0fKB'
              % (name, rec['file'], pno + 1, pix.width, pix.height,
                 os.path.getsize(path) / 1024))
        doc.close()

    if failed:
        sys.exit('נכשלו:\n  ' + '\n  '.join(failed))
    print('\nנוצרו %d תמונות ב-%s' % (len(NEEDS_IMAGE), OUT_DIR))


if __name__ == '__main__':
    main()
