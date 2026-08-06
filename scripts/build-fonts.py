#!/usr/bin/env python3
"""מוריד את הגופנים מ-Google Fonts ומייצר assets/fonts/fonts.css מקומי.

הגופנים מתארחים אצלנו ולא אצל גוגל — גם בשביל הפרטיות של הקוראים (בלי בקשה
לשרת חיצוני בכל טעינה) וגם כדי ש-CSP יוכל להישאר font-src 'self'.

הרצה:  python3 scripts/build-fonts.py
הסקריפט אידמפוטנטי: אפשר להריץ שוב ושוב, והוא מוחק קבצים שכבר לא בשימוש.
"""

import os
import re
import sys
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT_DIR = os.path.join(ROOT, 'assets', 'fonts')

# (שם המשפחה ב-CSS, שאילתת המשקלים ל-Google, קידומת לשמות הקבצים)
# משקלים בטווח (`300..900`) = גופן משתנה: קובץ אחד לכל תת-קבוצה, כל המשקלים בתוכו.
# משקלים מופרדים בנקודה-פסיק = גופן סטטי: קובץ נפרד לכל משקל.
FAMILIES = [
    ('Frank Ruhl Libre', 'wght@300..900', 'frankruhllibre'),   # כותרות — פרנק-ריהל, גופן הספר העברי
    ('Assistant',        'wght@200..800', 'assistant'),        # טקסט רץ ו-UI
    ('David Libre',      'wght@400;500;700', 'davidlibre'),    # פסוקים וציטוטים
]

# בלי User-Agent מודרני, Google מחזיר ttf/eot במקום woff2
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if binary else data.decode('utf-8')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    css_parts = []
    keep = set()

    for family, axis, prefix in FAMILIES:
        url = ('https://fonts.googleapis.com/css2?family='
               + family.replace(' ', '+') + ':' + axis + '&display=swap')
        print('->', family)
        css = fetch(url)

        blocks = re.findall(r'(/\*[^*]*\*/\s*)?(@font-face\s*\{[^}]*\})', css)
        if not blocks:
            sys.exit('לא התקבלו בלוקי @font-face עבור ' + family)

        for comment, block in blocks:
            m = re.search(r"src:\s*url\((https://[^)]+\.woff2)\)", block)
            if not m:
                sys.exit('בלוק בלי קובץ woff2 עבור ' + family)
            remote = m.group(1)
            name = prefix + '-' + remote.rsplit('/', 1)[-1]
            path = os.path.join(OUT_DIR, name)
            if not os.path.exists(path):
                with open(path, 'wb') as f:
                    f.write(fetch(remote, binary=True))
            keep.add(name)
            # גוגל מחזיר url(https://…) בלי מרכאות; מחליפים בקובץ מקומי במרכאות
            css_parts.append((comment or '') + block.replace(remote, "'" + name + "'"))

        print('   ', len(blocks), 'בלוקים')

    # ניקוי קבצים שכבר אינם מוזכרים (למשל אחרי החלפת גופן)
    removed = []
    for f in sorted(os.listdir(OUT_DIR)):
        if f.endswith('.woff2') and f not in keep:
            os.remove(os.path.join(OUT_DIR, f))
            removed.append(f)
    if removed:
        print('נמחקו', len(removed), 'קבצים שאינם בשימוש')

    header = ('/* נוצר על ידי scripts/build-fonts.py — אין לערוך ידנית.\n'
              '   להחלפת גופן: לערוך את FAMILIES בסקריפט ולהריץ אותו מחדש. */\n')
    with open(os.path.join(OUT_DIR, 'fonts.css'), 'w') as f:
        f.write(header + '\n'.join(css_parts) + '\n')

    # אימות: כל קובץ שמוזכר ב-CSS באמת קיים
    final = open(os.path.join(OUT_DIR, 'fonts.css')).read()
    refs = set(re.findall(r"url\('([^']+)'\)", final))
    missing = [r for r in refs if not os.path.exists(os.path.join(OUT_DIR, r))]
    if missing:
        sys.exit('קבצים חסרים אחרי הבנייה: ' + ', '.join(missing))
    print('סיום:', len(refs), 'קבצי גופן,', final.count('@font-face'), 'בלוקים')


if __name__ == '__main__':
    main()
