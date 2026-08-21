#!/usr/bin/env python3
"""משחזר את האותיות הסופיות שנפלו בחילוץ הטקסט מה-PDF.

הבעיה: הגופנים בקבצים מוטמעים כתת-קבוצה, ומפת ה-ToUnicode שלהם אינה כוללת את
האותיות הסופיות (ם ן ך ף ץ). התוצאה: "אנשים" יוצא "אנשי", "בהמשך" יוצא "בהמש&".
הקוד שמופיע במקומן שרירותי ושונה מגופן לגופן — ב-TTE13999D0 הקוד ‎\\x10 הוא ם,
ובגופן אחר אותו קוד עשוי להיות משהו אחר.

טבלת ה-post של הגופנים היא גרסה 3.0, כלומר בלי שמות גליפים, ולכן אי אפשר
לשחזר את המיפוי מהגופן עצמו. במקום זה מסיקים אותו מההקשר: אות סופית מופיעה רק
בסוף מילה, והצורות המקבילות (כ מ נ פ צ) כן ממופות.

**הסקריפט אינו מחליט לבד.** הוא מדפיס לכל קוד את המילים שבהן הוא מופיע ואת
ההסקה, כדי שאפשר יהיה לאשר או לתקן לפני שמשהו נכנס לאתר.

הרצה:  python3 scripts/infer-final-letters.py
"""

import collections
import glob
import json
import os
import re
import unicodedata

import pymupdf

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PDF_DIR = os.path.join(ROOT, 'assets', 'pdfs')

# תבניות סיום מילה בעברית, לפי סדר ביטחון. הראשונה שמתאימה קובעת.
#   (ביטוי על מה שלפני האות הסופית, האות, הסבר)
PATTERNS = [
    (r'י$',            'ם', 'סיומת ריבוי ‎-ים'),
    (r'ו$',            'ם', 'סיומת ‎-ום'),
    (r'^ב$|^בי$',      'ן', '"בין"'),
    (r'ו$',            'ן', 'סיומת ‎-ון'),
    (r'ש$|מש$|כ$',     'ך', 'סיומת ‎-ך'),
    (r'ס$|ו$',         'ף', 'סיומת ‎-ף'),
]
FINALS = 'םןךףץ'
# הצורה הלא-סופית של כל אות סופית, לזיהוי הקשרים
PAIR = {'ם': 'מ', 'ן': 'נ', 'ך': 'כ', 'ף': 'פ', 'ץ': 'צ'}


def suspicious(c):
    """תו שאינו עברי ואינו פיסוק סביר — מועמד להיות אות סופית שנפלה."""
    if 0x0590 <= ord(c) <= 0x05FF:
        return False
    return (ord(c) < 32 and c not in '\n\t\r') or unicodedata.category(c) in ('Cc', 'Co')


def collect():
    """אוסף לכל (גופן, קוד) את המילים שבהן הוא מופיע."""
    seen = collections.defaultdict(collections.Counter)
    for path in sorted(glob.glob(os.path.join(PDF_DIR, '*.pdf'))):
        doc = pymupdf.open(path)
        for page in doc:
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines', []):
                    for span in line['spans']:
                        font, text = span['font'], span['text']
                        for m in re.finditer(r'([א-ת]{1,12})(.)(?=\s|$|[.,:;?!)\]"\'])', text):
                            if suspicious(m.group(2)):
                                seen[(font, m.group(2))][m.group(1)] += 1
        doc.close()
    return seen


def infer(words):
    """מסיק את האות הסופית מתוך המילים שקדמו לקוד."""
    votes = collections.Counter()
    for stem, n in words.items():
        for pat, letter, why in PATTERNS:
            if re.search(pat, stem):
                votes[(letter, why)] += n
                break
    if not votes:
        return None, 'אין תבנית מתאימה', 0
    (letter, why), n = votes.most_common(1)[0]
    total = sum(votes.values())
    return letter, why, n / total


def main():
    seen = collect()
    table, unsure = {}, []
    print(f'{"גופן":22} {"קוד":8} {"מופעים":>7} {"אות":>4} {"ביטחון":>7}  מילים לדוגמה')
    for (font, code), words in sorted(seen.items(), key=lambda x: -sum(x[1].values())):
        n = sum(words.values())
        if n < 3:
            continue
        letter, why, conf = infer(words)
        ex = ', '.join(w + (letter or '?') for w, _ in words.most_common(3))
        mark = '' if conf >= 0.75 and letter else '   ← לבדיקה'
        print(f'{font[-20:]:22} {code!r:8} {n:7} {letter or "?":>4} {conf:6.0%}  {ex}{mark}')
        if letter and conf >= 0.75:
            table[f'{font}\t{code}'] = letter
        else:
            unsure.append({'font': font, 'code': code, 'count': n,
                            'words': dict(words.most_common(8))})

    out = os.path.join(ROOT, 'scripts', 'final-letters.json')
    with open(out, 'w') as f:
        json.dump({'map': table, 'unsure': unsure}, f, ensure_ascii=False, indent=1)
    print(f'\n{len(table)} מיפויים בביטחון גבוה, {len(unsure)} דורשים בדיקה → {out}')


if __name__ == '__main__':
    main()
