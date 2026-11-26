"""איפה בטקסט יושבת כל הערת שוליים: מספר ההערה בגוף הדף (ספרה קטנה ומוגבהת) והמילים שלפניו.

  python3 book/note_anchors.py      # ← book/note_anchors.json

החילוץ לטקסט (scripts/extract-sheet-text.py) שומר את ההערות עצמן, אבל המספרים הקטנים שבגוף הדף
יורדים בדרך. כאן מוצאים אותם שוב ב-PDF: ספרות בגופן קטן מגוף הטקסט, מעל קו ההערות, שהרצף שלהן
לפי סדר הקריאה הוא 1, 2, 3... לכל מספר נשמרות האותיות העבריות שלפניו (עד 24, בלי ניקוד ופיסוק) –
וכך build_book מוצא את המקום בפסקה ומחזיר לשם את מספר ההערה.
"""
import glob
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
from pdf_glyphs import open_fixed            # noqa: E402
from pdf_layout import _glyphs, lines       # noqa: E402
import importlib.util                        # noqa: E402
_spec = importlib.util.spec_from_file_location('extract', os.path.join(ROOT, 'scripts', 'extract-sheet-text.py'))
extract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(extract)            # footnote_rule: הקו שמעל הערות השוליים

LETTER = re.compile('[א-ת]')


def base(g):
    """האות של הגליף, בלי ניקוד – גם מצורות מוכנות כמו בּ (FB31), שמתפרקות ב-NFKD."""
    m = LETTER.search(unicodedata.normalize('NFKD', g['s']))
    return m.group() if m else ''
CONTEXT = 24


def refs(path, numbers):
    """{מספר: הקשר} לכל הערה שנמצא לה מקום בגוף הדף. numbers – מספרי ההערות לפי הסדר."""
    doc, expand, _ = open_fixed(path)
    cands, pages = [], []
    for pno, page in enumerate(doc):
        seen, gs = set(), []
        for g in _glyphs(page, expand):          # טקסט מודגש מודפס כמה פעמים באותו מקום – פעם אחת
            key = (round(g['x'] / 0.9), round(g['y'] / 0.9), g['s'])   # הדפסה כפולה בהזזה קטנה
            if key not in seen:
                seen.add(key); gs.append(g)
        rows = lines(page, expand)
        rule = extract.footnote_rule(page, rows) if rows else None
        if rule is not None:                      # מה שמתחת לקו הוא ההערות עצמן
            gs = [g for g in gs if g['y'] < rule]
        letters = [g for g in gs if base(g)]
        pages.append(letters)
        small = sorted((g for g in gs if g['s'].isdigit()), key=lambda g: (round(g['y']), g['x']))
        groups = []                               # ספרות צמודות באותו גובה ובאותו גודל – מספר אחד ("12")
        for g in small:
            if (groups and abs(groups[-1][-1]['y'] - g['y']) < 1 and groups[-1][-1]['size'] == g['size']
                    and 0 < g['x'] - groups[-1][-1]['x'] < g['size'] * 0.9):
                groups[-1].append(g)
            else:
                groups.append([g])
        for grp in groups:
            y, size = grp[0]['y'], grp[0]['size']
            x0, x1 = min(g['x0'] for g in grp), max(g['x1'] for g in grp)
            # מספר הערה בגוף הדף: קטן בבירור מהאותיות שבאותה שורה, וזו שורה של גוף הטקסט (9pt ומעלה);
            # בתחתית העמוד מספר ההערה יושב ליד טקסט קטן – ולכן לא נספר
            line = [g for g in letters if abs(g['y'] - y) < 6]
            if not line:
                continue
            sizes = sorted(g['size'] for g in line)
            med = sizes[len(sizes) // 2]
            if med >= 9 and size <= med - 1.2:
                cands.append((pno, y, -x1, int(''.join(g['s'] for g in grp)), x0, x1, line))
    cands.sort(key=lambda c: (c[0], c[1], c[2]))
    out, k = {}, 0
    for pno, y, _, n, x0, x1, line in cands:
        if k >= len(numbers):
            break
        if n == numbers[k]:
            pass
        elif k + 1 < len(numbers) and n == numbers[k + 1]:
            k += 1                                # מספר אחד לא נמצא – ממשיכים מהבא
        else:
            continue
        k += 1
        # הטקסט שלפני המספר: מימין לו באותה שורה (עברית), ואם אין מספיק – סוף השורה הקודמת
        right = sorted((g for g in line if g['x'] > x1 - 1), key=lambda g: g['x'])
        ctx = ''.join(base(g) for g in right[:CONTEXT])[::-1]
        if len(ctx) < 10:
            above = [g for g in pages[pno] if g['y'] < y - 6]
            if above:
                ly = max(g['y'] for g in above)
                prev = sorted((g for g in above if abs(g['y'] - ly) < 2), key=lambda g: g['x'])
                ctx = ''.join(base(g) for g in prev[:CONTEXT - len(ctx)])[::-1] + ctx
        out[n] = ctx
    return out


def main():
    result, missing = {}, 0
    for f in sorted(glob.glob(os.path.join(ROOT, 'assets', 'sheet-text', '*.json'))):
        name = os.path.basename(f)[:-5]
        notes = json.load(open(f, encoding='utf-8'))['footnotes']
        pdf = os.path.join(ROOT, 'assets', 'pdfs', name + '.pdf')
        if not notes or not os.path.exists(pdf):
            continue
        found = refs(pdf, [x['n'] for x in notes if isinstance(x['n'], int)])
        result[name] = {str(n): c for n, c in found.items()}
        lost = [x['n'] for x in notes if isinstance(x['n'], int) and x['n'] not in found]
        missing += len(lost)
        print(f'{name:32} {len(found):3}/{len(notes):3}' + (f'   חסרות: {lost}' if lost else ''))
    json.dump(result, open(os.path.join(HERE, 'note_anchors.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('חסרות בסך הכול:', missing)


if __name__ == '__main__':
    main()
