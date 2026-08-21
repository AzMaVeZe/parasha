"""בונה את שורות העמוד מתוך מיקומי הגליפים, במקום לסמוך על MuPDF.

למה זה נחוץ: הפסוקים המנוקדים בדפים מסודרים ב-PDF לפי מיקום ולא לפי סדר
קריאה, וכל סימן ניקוד הוא גליף נפרד. הסידור הדו-כיווני של MuPDF לא תמיד
מצליח להרכיב אותם חזרה, ו"דְּבַר" יוצא "ְבַרדּ".

המידע הדרוש קיים: לכל גליף יש מיקום ותיבה תוחמת. עברית נקראת מימין לשמאל,
כלומר לפי x יורד; סימן ניקוד שייך לאות שהתיבה שלה מכילה את מיקומו; ורצף
של ספרות או לטינית בתוך שורה עברית נקרא לשמאל־ימין ולכן מוחזר.

הפונקציה `lines(page, expand)` מחזירה את שורות העמוד כמחרוזות.
"""

import re
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
DAGESH = 'ּ'     # U+05BC
GUTTURAL = 'אחער'


def _takes_dagesh(bases, i):
    """האם האות הזאת יכולה לקבל דגש.

    כלל של השפה, לא ניחוש: אחע"ר לעולם לא מקבלות דגש.

    ה' היא היוצאת דופן היחידה, בזכות המפיק — אבל המפיק הוא כינוי הנסתרת
    ("לְרִשְׁתָּהּ", "בָּהּ"), ולכן הוא בא רק בסוף מילה ורק אחרי קמץ. ה'
    סופית אחרי סגול או צירי ("הַזֶּה", "מֹשֶׁה") היא נחה, ואינה מקבלת דגש.
    """
    s = bases[i]['s']
    if not ('א' <= s <= 'ת'):
        return False
    if s in GUTTURAL:
        return False
    if s == 'ה':
        nxt = bases[i + 1]['s'] if i + 1 < len(bases) else ' '
        if 'א' <= nxt <= 'ת':
            return False
        prev = bases[i - 1] if i else None
        return bool(prev and 'ָ' in prev.get('marks', []))
    return True


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
    letters = sorted((b for b in bases if not b['s'].isspace()),
                     key=lambda g: -g['x']) or bases
    # הדגש מטופל אחרון: ההחלטה אם ה' סופית מקבלת מפיק תלויה בתנועה
    # שעל האות שלפניה, וזו צריכה כבר להיות במקומה.
    for m in sorted(marks, key=lambda m: m['s'] == DAGESH):
        if m['s'] == HOLAM:
            target = min(letters, key=lambda b: abs(b['x0'] - m['x']))
        elif m['s'] == DAGESH:
            ok = [b for i, b in enumerate(letters) if _takes_dagesh(letters, i)]
            if not ok:
                continue
            inside = [b for b in ok if b['x0'] <= m['x'] <= b['x1']]
            # הדגש מצויר על גבול האות, ולפעמים כבר בתחומי השכנה משמאל.
            # כשהאות שמכילה אותו אינה יכולה לקבל דגש, הבעלים הוא זו שמימין.
            target = (inside[0] if inside else
                      min((b for b in ok if b['x0'] >= m['x']), key=lambda b: b['x0'],
                          default=min(ok, key=lambda b: abs(b['x0'] - m['x']))))
        else:
            inside = [b for b in letters if b['x0'] <= m['x'] <= b['x1']] or letters
            target = min(inside, key=lambda b: abs((b['x0'] + b['x1']) / 2 - m['x']))
        target['marks'].append(m['s'])
    return bases


def _dedupe(row):
    """מוריד עותקי צל: כותרות בדפים מצוירות כמה פעמים בהיסט זעיר.

    בלי זה "לק״י" יוצא 'ללללקקקק' ופסוק מנוקד בכותרת יוצא 'קקקָָָָקרררָ'.

    הסף נמדד ברוחב האות ולא בגודל הגופן, אחרת אות כפולה אמיתית נמחקת
    ו"המצוות" הופך ל"המצות". בפועל ההפרש בין עותקי צל קטן מחצי רוחב אות,
    ובין שתי אותיות זהות עוקבות הוא רוחב אות שלם.
    """
    out = []
    for g in sorted(row, key=lambda g: -g['x']):
        w = g['x1'] - g['x0']
        limit = 0.45 * w if w > 0.1 else 0.4
        if any(p['s'] == g['s'] and abs(p['x'] - g['x']) < limit for p in out[-4:]):
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


def _holam_male(text):
    """מחזיר חולם מלא לוי"ו שלו.

    הגופנים בדפים אינם עקביים במיקום החולם: באחד הוא מצויר בשפה השמאלית
    של האות שלו וכבר בתחומי הבאה, ובאחר בשפה הימנית. לכן המיקום לבדו לא
    מכריע אם ב"מוֹעֵד" החולם שייך למ' או לו'.

    מה שכן מכריע הוא הכתיב: ו' חשופה — בלי תנועה ובלי דגש — שבאה מיד
    אחרי חולם היא אֵם הקריאה שלו. ו' עיצורית תמיד נושאת תנועה או שווא
    משלה, ולכן אין כאן ניחוש.

    "הַיּוֹם" יוצא "הַיֹוּם": הדגש של י' נחת על הו' והחולם נשאר על הי'.
    גם כאן אין ניחוש — שורוק אינו יכול לבוא מיד אחרי חולם.
    """
    text = re.sub(r'ֹ(וּ)(?![ְ-ׇ])', 'ּוֹ', text)
    # הדגש שביניהם ("עַמּוֹ") שייך לאות שלפני, ונשאר במקומו.
    return re.sub(r'ֹ([ּׁׂ]*)(ו)(?![ְ-ׇ])', r'\1\2ֹ', text)


def _unmirror(text):
    """סוגריים בשורה עברית מצוירים הפוך. מחזירים אותם לתו הלוגי."""
    heb = sum(1 for c in text if 'א' <= c <= 'ת')
    lat = sum(1 for c in text if c.isascii() and c.isalpha())
    return text.translate(MIRROR) if heb > lat else text


def _spaced(bases):
    """מרכיב את השורה, ומחליט על רווחים לפי המרחק בפועל.

    הרווחים שכתובים בקובץ אינם תמיד נכונים — יש בו רווח בתוך מילה
    ("פ תרון") וגם מילים שנדבקו. שני המקרים נחתכים לפי המרחק בפועל:
    רווח כתוב שרוחבו אפס אינו רווח, ומרחק גדול בלי רווח כתוב כן מפריד.

    הסף למרחק גדול נמדד לכל שורה בנפרד, כי רוחב הרווח משתנה עם היישור
    לשוליים; אבל הסף למרחק אפס מוחלט, כדי שקטע מוצר בשורה — שהרווחים
    בו צרים מהשאר — לא יתפרק למילה אחת ארוכה.
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

    real = [g for g, w, a in zip(gaps, written, glyphs)
            if w and g > 0.06 * max(a['size'], 1)]
    typical = sorted(real)[len(real) // 2] if len(real) >= 3 else None

    parts = []
    for n, g in enumerate(glyphs):
        if n:
            gap, has = gaps[n - 1], written[n - 1]
            wide = 0.06 * max(glyphs[n - 1]['size'], 1)
            space = (has and gap > wide) or (typical and gap > 0.6 * typical)
            if space:
                parts.append(' ')
        parts.append(g['s'] + ''.join(sorted(g['marks'], key=unicodedata.combining)))
    return ''.join(parts)


def lines(page, expand):
    """שורות העמוד, בסדר קריאה.

    השורות נבנות מהאותיות בלבד, והניקוד מצורף אליהן אחר כך. הסיבה: יש
    גופנים שמציירים סימן בגובה שונה מהאות שלו — הקמץ של ך' סופית, למשל,
    מצויר כמעט חמש נקודות מעל הבסיס. חלוקה לשורות שמתייחסת גם לניקוד
    הייתה זורקת אותו לשורה השכנה, ו"כְמַעֲשֶׂיךָ" היה יוצא "כְמַעֲשֶׂיך".
    """
    gs = _glyphs(page, expand)
    if not gs:
        return []
    bases = [g for g in gs if unicodedata.category(g['s'][0]) != 'Mn']
    marks = [g for g in gs if unicodedata.category(g['s'][0]) == 'Mn']
    if not bases:
        return []

    rows, cur = [], []
    for g in sorted(bases, key=lambda g: (round(g['y'] / Y_TOLERANCE), -g['x'])):
        if cur and abs(g['y'] - cur[0]['y']) > Y_TOLERANCE:
            rows.append(cur)
            cur = []
        cur.append(g)
    rows.append(cur)

    span = [(min(g['x0'] for g in r), max(g['x1'] for g in r), r[0]['y'], r) for r in rows]
    for m in marks:
        near = [s for s in span if s[0] - 1 <= m['x'] <= s[1] + 1] or span
        lo, hi, y, row = min(near, key=lambda s: abs(s[2] - m['y']))
        row.append(m)

    out = []
    for row in rows:
        bases = sorted(_attach_marks(_dedupe(row)), key=lambda g: -g['x'])
        text = _spaced(bases)
        text = _unmirror(_unreverse_ltr(_holam_male(text))).strip()
        if text:
            out.append({'text': text, 'y': row[0]['y'],
                        'x0': min(b['x0'] for b in bases),
                        'x1': max(b['x1'] for b in bases),
                        'size': max(b['size'] for b in bases)})
    return out
