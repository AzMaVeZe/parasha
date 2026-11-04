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
from pdf_layout import lines, _glyphs     # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PDF_DIR = os.path.join(ROOT, 'assets', 'pdfs')
OUT = os.path.join(ROOT, 'scripts', 'sheet-text')
# עותק רזה לאתר: העמודים הסטטיים מטמיעים אותו, והעמוד הדינמי טוען אותו בלחיצה
SITE_OUT = os.path.join(ROOT, 'assets', 'sheet-text')

MIN_PARAGRAPH = 15          # קצר מזה הוא ריהוט עמוד: 'לק"י', שנה, מספר עמוד
HEB = 'א-ת'


CAPTION_BELOW = 26     # עד כמה נקודות מתחת לתמונה יושב הכיתוב שלה
CAPTION_MAX_LINES = 4  # כיתוב הוא שורה-שתיים; יותר מזה כבר טקסט


def caption_glyphs(page, expand, rule):
    """הגליפים של כיתובי התמונות בעמוד.

    כיתוב ("ג'יימס טיסוט, צרפת, 1836-1902") יושב בתוך התמונה או ממש מתחתיה, בגופן
    קטן מגוף הטקסט. מכיוון שהשורות נבנות לפי גובה לרוחב כל העמוד, כיתוב שליד הטור
    השני היה נכנס לאמצע שורה שם — לפעמים לאמצע פסוק. הוא אינו חלק מהדף כטקסט.
    מה שמתחת לקו הערות השוליים אינו כיתוב, ותמונה זעירה (פחות מ-30 נקודות) אינה תמונה."""
    gs = _glyphs(page, expand)
    if not gs:
        return set()
    sizes = sorted(round(g['size']) for g in gs)
    body = max(set(sizes), key=sizes.count)
    out = set()
    for info in page.get_image_info():
        x0, y0, x1, y1 = info['bbox']
        if x1 - x0 < 30 or y1 - y0 < 30:
            continue
        # מתחת לקו ההערות — רק אותיות בגופן זעיר מאוד (8.5 ומטה), שהן כיתוב ולא הערה.
        # ספרות שם נשארות: מספר ההערה הזעיר שפותח כל הערה הוא מה שמפריד בין הערה להערה.
        ok = lambda g: g['size'] < body - 1.5 and (
            rule is None or g['y'] < rule or (g['size'] <= 8.6 and not g['s'].isdigit()))
        inx = lambda g: x0 - 4 <= g['x'] <= x1 + 4
        below = [g for g in gs if inx(g) and y1 - 2 < g['y'] <= y1 + CAPTION_BELOW and ok(g)]
        inside = [g for g in gs if inx(g) and y0 <= g['y'] <= y1 - 2 and ok(g)]
        # בתוך התמונה: טקסט רגיל שעוקף אותה נוגע לפעמים בתיבה שלה. אם יש שם יותר מדי
        # שורות, נשאר רק הגופן הזעיר (9 ומטה), שהוא הכיתוב.
        if len({round(g['y'] / 3) for g in inside}) > CAPTION_MAX_LINES:
            inside = [g for g in inside if g['size'] <= 9.2]
        for cand in (below, inside):
            rows = {round(g['y'] / 3) for g in cand}
            # טקסט קטן בתוך תמונה של חידה הוא החידה עצמה, לא כיתוב — נשאר
            text = ''.join(g['s'] for g in sorted(cand, key=lambda g: (round(g['y'] / 3), -g['x'])))
            if not cand or len(rows) > CAPTION_MAX_LINES or re.search(r'חיד|לקינוח|פתרון|התשובה', text):
                continue
            out |= {(round(g['x'], 2), round(g['y'], 2), g['s']) for g in cand}
    return out


def page_lines(doc, expand):
    """שורות כל עמוד, עמוד־עמוד, וגובה הקו שמפריד את הערות השוליים (או None).
    כיתובי התמונות יורדים (caption_glyphs)."""
    out = []
    for page in doc:
        rows = lines(page, expand)
        if not rows:
            continue
        rule = footnote_rule(page, rows)
        cap = caption_glyphs(page, expand, rule)
        if cap:
            rows = lines(page, expand, skip=lambda g: (round(g['x'], 2), round(g['y'], 2), g['s']) in cap)
            if not rows:
                continue
        out.append((rows, rule, page.rect.height - 50))
    return out


def footnote_rule(page, rows):
    """Word מפריד את הערות השוליים בקו קצר בצד ימין, מעליהן בתחתית העמוד.

    הקו הוא מלבן דק (גובה פחות מ-2 נקודות), ברוחב 100–200 נקודות, בחצי
    התחתון של העמוד, והקצה הימני שלו צמוד לקצה ההערות שמתחתיו. מתחתיו יש
    רק שורות בגופן קטן מגוף הטקסט (או כותרת תחתונה גדולה) — אחרת זה סתם קו."""
    best = None
    for d in page.get_drawings():
        for it in d['items']:
            r = it[1] if it[0] == 're' else None
            if it[0] == 'l' and abs(it[1].y - it[2].y) < 1:
                r = pymupdf_rect(it[1], it[2])
            # קו קצר (כ-144) מעל הערות שמתחילות בעמוד; קו ארוך (עד רוחב
            # הטקסט) מעל המשך של הערה מהעמוד הקודם
            if not r or r.height > 2 or not 100 <= r.width <= 450:
                continue
            if r.y0 < page.rect.height * 0.5:
                continue
            # גודל גוף הטקסט נמדד רק מעל הקו: בדף עם הרבה הערות, החציון של כל
            # העמוד יוצא בגודל של ההערות עצמן
            above = sorted(x['size'] for x in rows if x['y'] <= r.y0)
            if not above:
                continue
            body = above[len(above) // 2]
            # מספר העמוד והכותרת התחתונה יושבים מתחת להערות ואינם חלק מהן
            foot = page.rect.height - 50
            below = [x for x in rows if r.y0 < x['y'] <= foot]
            small = [x for x in below if x['size'] < body - 0.5]
            # השוליים הימניים נמדדים מההערות עצמן: בראש העמוד יש לפעמים עיגול
            # "לק"י" או כיתוב תמונה שחורגים מהם
            # ההערה הראשונה מתחת לקו נפתחת במספר זעיר. כשההערות בגודל של גוף
            # הטקסט, זה מה שמבדיל אותן; אחרת — כל מה שמתחת לקו קטן מהגוף.
            opens = bool(below) and below[0]['size'] < 8.5 and \
                re.fullmatch(r'\d{1,3}|\*', below[0]['text'].strip())
            if not opens and (not small or abs(r.x1 - max(x['x1'] for x in small)) > 20):
                continue
            if opens or all(x['size'] < body - 0.5 or x['size'] > body + 4 for x in below):
                best = r.y0 if best is None else min(best, r.y0)
    return best if best is not None else unruled_footnotes(page, rows)


def unruled_footnotes(page, rows):
    """דף שבו הקו המפריד לא צויר: מזהים את גוש ההערות מלמטה למעלה.

    גוש ההערות הוא רצף שורות בתחתית העמוד, קטנות מגוף הטקסט, שראשו מספר
    זעיר (פחות מ-7.5) בשוליים הימניים — כך נראית פתיחת הערה בכל הדפים.
    מספרי ההפניה בתוך הטקסט גדולים יותר (כ-8) ויושבים באמצע השורה."""
    foot = page.rect.height - 50
    sizes = sorted(r['size'] for r in rows)
    body = sizes[len(sizes) // 2]
    right = sorted(r['x1'] for r in rows)[int(len(rows) * 0.9)]
    start = None
    for r in reversed([r for r in rows if r['y'] <= foot]):
        if r['size'] >= body - 0.5:
            break
        if r['size'] < 7.5 and re.fullmatch(r'\d{1,3}', r['text'].strip()) and r['x1'] > right - 15:
            start = r['y']
    return start - 1 if start is not None else None


def pymupdf_rect(p1, p2):
    import pymupdf
    return pymupdf.Rect(min(p1.x, p2.x), min(p1.y, p2.y) - 0.1, max(p1.x, p2.x), max(p1.y, p2.y) + 0.1)


def split_footnotes(rows, rule, foot=792):
    """מפריד את שורות הערות השוליים מגוף העמוד.

    מתחת לקו: מספר ההערה הוא שורה משלו בגופן זעיר (כ-6.5), ואחריו טקסט ההערה
    (כ-10). שורה גדולה מגוף הטקסט מתחת לקו היא כותרת תחתונה של העמוד, והיא
    נשארת בגוף. מחזיר (שורות הגוף, [(מספר, [שורות])])."""
    if rule is None:
        return rows, []
    body = [r for r in rows if r['y'] <= rule]
    size = sorted(r['size'] for r in body)[len(body) // 2] if body else 12
    notes = []
    for r in rows:
        if r['y'] <= rule:
            continue
        text = r['text'].strip()
        last = notes[-1][0] if notes and isinstance(notes[-1][0], int) else None
        lead = re.match(r'(\d{1,3}) +(\S.*)', text)
        if r['size'] > size + 4 or r['y'] > foot:
            body.append(r)
        elif re.fullmatch(r'\d{1,3}|\*', text) and r['size'] < 8.5:
            notes.append((text if text == '*' else int(text), []))
        # בחלק מהדפים המספר באותה שורה עם ההערה. שורת המשך יכולה גם היא
        # להתחיל במספר ("40 שנה"), ולכן רק אם זה המספר הבא בתור.
        elif lead and (last is None or int(lead.group(1)) == last + 1) and \
                (last is not None or not notes):
            notes.append((int(lead.group(1)), [lead.group(2)]))
        elif notes:
            notes[-1][1].append(r['text'])
        else:
            notes.append((None, [r['text']]))
    return body, [(n, t) for n, t in notes if t]


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


def is_quote(p):
    """כמו באתר (build-pages.js, site.js): פסקה מנוקדת מוצגת כמובאה."""
    return len(re.findall('[%s]' % NIK, p)) > len(p) * 0.08


PROSE_RUN = 4   # כך הרבה מילים בלי ניקוד ברצף — זה כבר טקסט, לא מילה לא מנוקדת בתוך פסוק


def split_verse(p):
    """פסוק מנוקד וטקסט רגיל שנדבקו בחילוץ לפסקה אחת ("...קָנִיתִי אִישׁ אֶת-ה'. עד עתה עסקנו...").

    רק בפסקה שמוצגת כמובאה: שם הטקסט שאחרי הפסוק (או לפניו) מעוצב בטעות כמו הפסוק.
    חותכים בגבול המילים שבין הרצף המנוקד לרצף הלא מנוקד. מילה בודדת בלי ניקוד בתוך
    פסוק (ה', "(...)") לא נחשבת גבול, ומראה המקום שבסוגריים אחרי הפסוק נשאר איתו.
    הטקסט עצמו לא משתנה: הפסקה רק מתחלקת לכמה פסקאות.
    """
    if not is_quote(p):
        return [p]
    words = p.split(' ')
    voc = [bool(re.search('[%s]' % NIK, w)) for w in words]
    # מילה עם אותיות. ה' וא-לוהים בלי ניקוד הם חלק מהפסוק, לא טקסט.
    # {ס} ו-{פ} של הפרשיות הם סימנים, לא טקסט.
    heb = [bool(re.search('[%s]' % HEB, w))
           and not re.fullmatch(r'[^%s]*ה[\'׳][^%s]*|\{[פס]\}' % (HEB, HEB), w) for w in words]
    prose, start = [], None
    for i in range(len(words) + 1):
        if i < len(words) and not voc[i]:
            if start is None and heb[i]:
                start = i
            continue
        if start is not None:
            end = i
            while not heb[end - 1]:         # מרכאות פותחות של הפסוק הבא שייכות אליו
                end -= 1
            n = sum(heb[start:end])
            # פתיחה קצרה לפני פסוק ("ונסיים בפסוק:") נחשבת גם היא, אם היא נגמרת בנקודתיים
            if n >= PROSE_RUN or (start == 0 and n >= 2 and words[end - 1].endswith(':')):
                before = ' '.join(words[prose[-1][1] if prose else 0:start])
                if words[start].startswith('(') or before.count('(') > before.count(')'):
                    # "...פסוק (ויקרא כה, לה-לז) הטקסט" — מראה המקום הולך עם הפסוק
                    close = next((k for k in range(start, min(start + 5, end)) if ')' in words[k]), None)
                    if close is not None:
                        start = close + 1
                if start < end:
                    prose.append((start, end))
            start = None
    cuts = sorted({k for a, b in prose for k in (a, b) if 0 < k < len(words)})
    parts = [' '.join(words[a:b]) for a, b in zip([0] + cuts, cuts + [len(words)])]
    # קטע קצר מדי (שארית של מראה מקום, "לקינוח:") מתחבר לקטע שלפניו
    out = []
    for x in parts:
        if out and len(x) < MIN_PARAGRAPH:
            out[-1] += ' ' + x
        elif out and len(out[-1]) < MIN_PARAGRAPH:
            out[-1] += ' ' + x
        else:
            out.append(x)
    return out


def extract(path):
    doc, expand, unknown = open_fixed(path)
    pages = page_lines(doc, expand)
    tmp = doc._tmp_path
    doc.close()
    os.unlink(tmp)

    paras, footnotes = [], []
    for rows, rule, foot in pages:
        body_rows, notes = split_footnotes(rows, rule, foot)
        paras += [join(p) for p in split_paragraphs(body_rows)]
        for n, t in notes:
            # הערה שנמשכת לעמוד הבא: שם היא מופיעה בלי מספר, מתחת לקו ארוך
            if n is None and footnotes:
                footnotes[-1]['text'] += ' ' + join(t)
            else:
                footnotes.append({'n': n, 'text': join(t)})
    paras = [p for p in paras
             if len(p) >= MIN_PARAGRAPH and len(re.findall(r'[א-תA-Za-z]', p)) >= 3]
    paras = [x for p in paras for x in split_verse(p)]
    body = '\n\n'.join(paras + [f['text'] for f in footnotes])
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
        # הערות השוליים, לפי הסדר ועם המספור שבדף. מוצגות בסוף, לא באמצע הטקסט.
        'footnotes': footnotes,
        'chars': len(body),
        'hebrew_ratio': round(
            sum(1 for c in body if 0x05D0 <= ord(c) <= 0x05EA) / max(len(body), 1), 2),
        'notes': notes,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SITE_OUT, exist_ok=True)
    targets = sys.argv[1:] or sorted(glob.glob(os.path.join(PDF_DIR, '*.pdf')))
    targets = [t if os.path.dirname(t) else os.path.join(PDF_DIR, t) for t in targets]
    total = 0
    for path in targets:
        r = extract(path)
        name = os.path.splitext(r['file'])[0]
        with open(os.path.join(OUT, name + '.json'), 'w') as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
        with open(os.path.join(SITE_OUT, name + '.json'), 'w') as f:
            json.dump({'paragraphs': r['paragraphs'], 'footnotes': r['footnotes'],
                       'notes': r['notes']},
                      f, ensure_ascii=False)
        total += r['chars']
        flag = '  ← נבדוק' if r['hebrew_ratio'] < 0.5 or r['chars'] < 800 else ''
        print(f"{r['file']:34} {r['chars']:6} תווים  {len(r['paragraphs']):3} פסקאות  "
              f"{len(r['footnotes']):2} הערות  "
              f"עברית {r['hebrew_ratio']:.0%}{flag}")
    print(f'\n{len(targets)} דפים, {total:,} תווים → {OUT}/')


if __name__ == '__main__':
    main()
