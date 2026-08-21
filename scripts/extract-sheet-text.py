#!/usr/bin/env python3
"""מחלץ את הטקסט מדפי ה-PDF, לשימוש כתוכן קריא בעמודי /p/.

הרקע: לעמודי הדפים באתר יש כותרת ונתונים מובנים, אבל התוכן עצמו נעול בתוך
ה-PDF. מנוע חיפוש רואה עמוד ששמו "פרשת ראה" ואין בו דבר על פרשת ראה.

הפענוח נעשה ב-`pdf_glyphs.py`, שקורא את טבלת שמות הגליפים שבקובץ, וסידור
השורות ב-`pdf_layout.py`, שבונה אותן לפי מיקומי הגליפים. כאן נשאר רק הניקוי,
ורק לפי מה שנמצא בקבצים בפועל:

1. **שברי שורות** — PDF שומר כל שורה בנפרד; כאן הן מחוברות חזרה לפסקאות
   לפי הפריסה: רווח אנכי חריג, שינוי גודל, או שורה שנגמרה מוקדם.
2. **פיסוק שהוזז** — סימן פיסוק שיושב בין עברית לעברית מוחזר למקומו.
3. **כתובות מייל** — יורדות. הן פרטיות, והריפו והאתר ציבוריים.

הפלט הוא JSON לכל דף: הפסקאות, כמה תווים יצאו, ומה שדרש שיקול דעת — כדי
שאפשר יהיה לבדוק כל דף מול המקור.

הרצה:  python3 scripts/extract-sheet-text.py [שם-קובץ.pdf ...]
        בלי ארגומנטים — כל הדפים.
"""

import glob
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdf_glyphs import open_fixed          # noqa: E402
from pdf_layout import lines               # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PDF_DIR = os.path.join(ROOT, 'assets', 'pdfs')
OUT = os.path.join(ROOT, 'scripts', 'sheet-text')

MIN_PARAGRAPH = 15          # קצר מזה הוא ריהוט עמוד: 'לק"י', שנה, מספר עמוד
HEB = 'א-ת'


def page_lines(doc, expand):
    """שורות כל עמוד, עמוד־עמוד."""
    return [rows for rows in (lines(page, expand) for page in doc) if rows]


def split_paragraphs(rows):
    """שוברים לפסקאות לפי הפריסה: רווח אנכי חריג, או שורה שנגמרה מוקדם.

    בעברית השורה נגמרת בצד שמאל, ולכן שורה אחרונה בפסקה נעצרת ימינה
    מהשוליים — כלומר ה-x0 שלה גדול מהרגיל. השוליים נמדדים מקומית ולא לכל
    העמוד, כי בדפים שהטקסט בהם עוקף תמונה יש קטעים בעמודה צרה.
    """
    if not rows:
        return []
    gaps = sorted(b['y'] - a['y'] for a, b in zip(rows, rows[1:]))
    step = gaps[len(gaps) // 2] if gaps else 0

    paras, cur = [], [rows[0]['text']]
    for i, (prev, row) in enumerate(zip(rows, rows[1:])):
        near = rows[max(0, i - 3):i + 5]
        margin = min(r['x0'] for r in near)
        width = max(r['x1'] for r in near) - margin
        short = prev['x0'] > margin + 0.25 * width
        gap = step and (row['y'] - prev['y']) > 1.4 * step
        size = abs(row['size'] - prev['size']) > 1.5
        if short or gap or size:
            paras.append(cur)
            cur = []
        cur.append(row['text'])
    paras.append(cur)
    return paras


NIK = '֑-ׇ'


def tidy(text):
    """מחזיר פיסוק שהוזז בסידור הדו-כיווני למקומו בתוך המשפט."""
    # " . א" בראש סעיף → "א. "
    text = re.sub(r'(?<![%s])\.\s*([א-ט])(?=[ ])' % HEB, r'\1.', text)
    # ראשי תיבות שהגרשיים בהם נותקו: 'הקב "ה' → 'הקב"ה'. רק אות אחת אחרי
    # הגרשיים, אחרת מדובר במרכאות פותחות של ציטוט.
    text = re.sub(r'([%s]{1,4}) *" *([%s])(?![%s%s])' % (HEB, HEB, HEB, NIK),
                  r'\1"\2', text)
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    text = re.sub(r'([%s])\(' % HEB, r'\1 (', text)
    text = re.sub(r'\)([%s])' % HEB, r') \1', text)
    # "מילה , מילה" → "מילה, מילה". אחרון, כדי שהכללים שלמעלה לא יחזירו רווח.
    text = re.sub(r'[ ]+([,.;:?!])', r'\1', text)
    text = re.sub(r'([,.;:?!])([%s])' % HEB, r'\1 \2', text)
    return re.sub(r' {2,}', ' ', text)


# בכותרת התחתונה של הדפים מופיעות כתובות מייל אישיות (של אריאל ושל קוראים
# שהדף הועבר אליהם). הריפו ציבורי והטקסט מיועד לאתר, ולכן הן יורדות כאן.
EMAIL = re.compile(r'\b[\w.+-]+ ?@ ?[\w.-]+\.[A-Za-z]{2,}\.?')

UNREADABLE = '□'


def join(rows):
    """PDF שומר כל שורה בנפרד. מחברים חזרה לפסקה אחת."""
    text = ' '.join(rows)
    text = EMAIL.sub('[כתובת מייל]', text)
    text = re.sub(r'[‎‏‪-‮]', '', text)   # סימני כיווניות
    # גליף שחסר כבר בקובץ המקור ומוצג גם שם כריבוע ריק. לא מנחשים מה היה שם.
    text = text.replace('\x00', UNREADABLE).replace('�', UNREADABLE)
    text = re.sub(r'[ \t\xa0]+', ' ', text)
    # סדר קנוני לסימני הניקוד, כדי שאותו פסוק ייצא זהה בכל דף
    return unicodedata.normalize('NFC', tidy(text)).strip()


def extract(path):
    doc, expand, unknown = open_fixed(path)
    pages = page_lines(doc, expand)
    tmp = doc._tmp_path
    doc.close()
    os.unlink(tmp)

    paras = [join(p) for page in pages for p in split_paragraphs(page)]
    paras = [p for p in paras
             if len(p) >= MIN_PARAGRAPH and len(re.findall(r'[א-תA-Za-z]', p)) >= 3]
    body = '\n\n'.join(paras)
    notes = []
    if UNREADABLE in body:
        notes.append(f'{body.count(UNREADABLE)} תווים חסרים כבר בקובץ המקור — הוא מציג '
                     f'שם ריבוע ריק. סומנו כאן {UNREADABLE} ולא נוחשו.')
    left = sorted({c for c in body if c not in '\n\t'
                   and (ord(c) < 32 or unicodedata.category(c) in ('Cc', 'Co'))})
    if left:
        notes.append('תווים שלא פוענחו: ' + ' '.join(hex(ord(c)) for c in left))
    return {
        'file': os.path.basename(path),
        'paragraphs': paras,
        'chars': len(body),
        'hebrew_ratio': round(
            sum(1 for c in body if 0x05D0 <= ord(c) <= 0x05EA) / max(len(body), 1), 2),
        'notes': notes,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    targets = sys.argv[1:] or sorted(glob.glob(os.path.join(PDF_DIR, '*.pdf')))
    targets = [t if os.path.dirname(t) else os.path.join(PDF_DIR, t) for t in targets]
    total = 0
    for path in targets:
        r = extract(path)
        name = os.path.splitext(r['file'])[0]
        with open(os.path.join(OUT, name + '.json'), 'w') as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
        total += r['chars']
        flag = '  ← נבדוק' if r['hebrew_ratio'] < 0.5 or r['chars'] < 800 else ''
        print(f"{r['file']:34} {r['chars']:6} תווים  {len(r['paragraphs']):3} פסקאות  "
              f"עברית {r['hebrew_ratio']:.0%}{flag}")
    print(f'\n{len(targets)} דפים, {total:,} תווים → {OUT}/')


if __name__ == '__main__':
    main()
