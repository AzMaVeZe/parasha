"""בונה את שורות העמוד מתוך מיקומי הגליפים, במקום לסמוך על MuPDF.

למה זה נחוץ: הפסוקים המנוקדים בדפים מסודרים ב-PDF לפי מיקום ולא לפי סדר
קריאה, וכל סימן ניקוד הוא גליף נפרד. הסידור הדו-כיווני של MuPDF לא תמיד
מצליח להרכיב אותם חזרה, ו"דְּבַר" יוצא "ְבַרדּ".

המידע הדרוש קיים: לכל גליף יש מיקום ותיבה תוחמת. עברית נקראת מימין לשמאל,
כלומר לפי x יורד; סימן ניקוד שייך לאות שהתיבה שלה מכילה את מיקומו; ורצף
של ספרות או לטינית בתוך שורה עברית נקרא לשמאל־ימין ולכן מוחזר.

הפונקציה `lines(page, expand)` מחזירה את שורות העמוד כמחרוזות.
"""

import unicodedata

Y_TOLERANCE = 3.0       # גליפים בהפרש קטן מזה נחשבים לאותה שורה
LTR = set('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')


def _glyphs(page, expand):
    out = []
    for span in page.get_texttrace():
        if span.get('type') != 0:
            continue
        for ucs, gid, org, bb in span['chars']:
            s = expand(chr(ucs))
            if not s:
                continue
            out.append({'s': s, 'x': org[0], 'y': org[1],
                        'x0': bb[0], 'x1': bb[2], 'size': span['size']})
    return out


HOLAM = 'ֹ'      # U+05B9


def _attach_marks(row):
    """מצמיד כל סימן ניקוד לאות שלו.

    רוב הסימנים מצוירים מתחת למרכז האות, ולכן התיבה של האות מכילה אותם.
    החולם יוצא דופן: הוא מצויר בפינה השמאלית העליונה, על גבול האות הבאה,
    ולפעמים אף בתוך התיבה שלה — ולכן "לֹא" היה יוצא "לאֹ". מה שכן יציב הוא
    המרחק לשפה השמאלית של האות שלו: החולם תמיד צמוד ל-x0 של בעליו.
    """
    bases = [g for g in row if unicodedata.category(g['s'][0]) != 'Mn']
    marks = [g for g in row if unicodedata.category(g['s'][0]) == 'Mn']
    for g in bases:
        g['marks'] = []
    if not bases:
        return bases
    letters = [b for b in bases if not b['s'].isspace()] or bases
    for m in marks:
        if m['s'] == HOLAM:
            target = min(letters, key=lambda b: abs(b['x0'] - m['x']))
        else:
            inside = [b for b in letters if b['x0'] <= m['x'] <= b['x1']] or letters
            target = min(inside, key=lambda b: abs((b['x0'] + b['x1']) / 2 - m['x']))
        target['marks'].append(m['s'])
    return bases


def _dedupe(row):
    """מוריד עותקי צל: כותרות בדפים מצוירות כמה פעמים בהיסט זעיר.

    בלי זה "לק״י" יוצא 'ללללקקקק' ופסוק מנוקד בכותרת יוצא 'קקקָָָָקרררָ'.
    """
    out = []
    for g in sorted(row, key=lambda g: -g['x']):
        if any(p['s'] == g['s'] and abs(p['x'] - g['x']) < 0.3 * max(g['size'], 1)
               for p in out[-4:]):
            continue
        out.append(g)
    return out


MIRROR = str.maketrans('()[]{}<>', ')(][}{><')


def _unreverse_ltr(text):
    """רצף ספרות או לטינית בתוך שורה עברית נקרא הפוך. מחזירים אותו."""
    out, i = [], 0
    while i < len(text):
        if text[i] in LTR:
            j = i
            while j < len(text) and (text[j] in LTR or
                                     (text[j] in '.,:/@_-' and j + 1 < len(text)
                                      and text[j + 1] in LTR)):
                j += 1
            out.append(text[i:j][::-1])
            i = j
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)


def _unmirror(text):
    """סוגריים בשורה עברית מצוירים הפוך. מחזירים אותם לתו הלוגי."""
    heb = sum(1 for c in text if 'א' <= c <= 'ת')
    lat = sum(1 for c in text if c.isascii() and c.isalpha())
    return text.translate(MIRROR) if heb > lat else text


def _spaced(bases):
    """מרכיב את השורה, ומחליט על רווחים לפי המרחק בפועל.

    הרווחים שכתובים בקובץ אינם תמיד נכונים — יש בו רווח בתוך מילה
    ("פ תרון") וגם מילים שנדבקו. הרוחב האמיתי של רווח משתנה משורה
    לשורה בגלל יישור לשוליים, ולכן הוא נמדד לכל שורה בנפרד: רווח
    שכתוב בקובץ אבל צר בהרבה מהאחרים באותה שורה אינו רווח אמיתי.
    """
    glyphs, written, pending = [], [], False
    for b in bases:
        if b['s'].isspace():
            pending = True
            continue
        glyphs.append(b)
        written.append(pending)
        pending = False
    if len(glyphs) < 2:
        return ''.join(b['s'] for b in glyphs)
    written = written[1:]
    gaps = [a['x0'] - b['x1'] for a, b in zip(glyphs, glyphs[1:])]

    marked = sorted(g for g, w in zip(gaps, written) if w)
    typical = marked[len(marked) // 2] if len(marked) >= 3 else None

    parts = []
    for n, g in enumerate(glyphs):
        if n:
            gap, has = gaps[n - 1], written[n - 1]
            if typical is None:
                space = has
            else:
                space = gap > 1.5 * typical or (has and gap > 0.5 * typical)
            if space:
                parts.append(' ')
        parts.append(g['s'] + ''.join(sorted(g['marks'], key=unicodedata.combining)))
    return ''.join(parts)


def lines(page, expand):
    """שורות העמוד, בסדר קריאה."""
    gs = _glyphs(page, expand)
    if not gs:
        return []
    rows, cur = [], []
    for g in sorted(gs, key=lambda g: (round(g['y'] / Y_TOLERANCE), -g['x'])):
        if cur and abs(g['y'] - cur[0]['y']) > Y_TOLERANCE:
            rows.append(cur)
            cur = []
        cur.append(g)
    rows.append(cur)

    out = []
    for row in rows:
        bases = sorted(_attach_marks(_dedupe(row)), key=lambda g: -g['x'])
        text = _spaced(bases)
        text = _unmirror(_unreverse_ltr(text)).strip()
        if text:
            out.append({'text': text, 'y': row[0]['y'],
                        'x0': min(b['x0'] for b in bases),
                        'x1': max(b['x1'] for b in bases),
                        'size': max(b['size'] for b in bases)})
    return out
