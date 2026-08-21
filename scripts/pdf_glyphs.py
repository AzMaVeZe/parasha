"""מתקן את פענוח העברית ב-PDF של הדפים, בלי לנחש.

הרקע: הגופנים בקבצים מוטמעים כתת-קבוצה ובלי טבלת ToUnicode. במקומה יש
‎/Encoding עם ‎/Differences — טבלה שמצמידה לכל קוד תו שם גליף. הבעיה היא
ששמות הגליפים העבריים אינם תקניים (‎/memfinal, ‎/qamats, ‎/betwithdagesh),
ו-MuPDF אינו מכיר אותם, ולכן פולט את קוד התו הגולמי. כך "אנשים" יצא
"אנשי\\x02" וכל הניקוד יצא תווי בקרה.

הפתרון כאן אינו הסקה סטטיסטית אלא קריאה של הטבלה שכבר קיימת בקובץ:
לפני החילוץ כל שם גליף עברי מוחלף בשם התקני ‎/uniXXXX, ש-MuPDF כן מכיר.
המיפוי ודאי — הוא כתוב בקובץ עצמו.

צירופים של אות וניקוד (‎/betwithdagesh) אינם ניתנים לביטוי בשם ‎/uniXXXX
יחיד, ולכן הם מקבלים קוד זמני באזור השימוש הפרטי ומפוענחים חזרה לרצף
אחרי החילוץ.

    from pdf_glyphs import open_fixed
    doc, unknown = open_fixed('assets/pdfs/ראה.pdf')
"""

import re
import tempfile

import pymupdf
from fontTools import agl

# אותיות עבריות. השמות הסופיים מופיעים בקבצים בשתי צורות — kaffinal ו-finalkaf.
LETTERS = {
    'alef': 'א', 'bet': 'ב', 'gimel': 'ג', 'dalet': 'ד',
    'he': 'ה', 'vav': 'ו', 'zayin': 'ז', 'het': 'ח',
    'tet': 'ט', 'yod': 'י', 'kaf': 'כ', 'lamed': 'ל',
    'mem': 'מ', 'nun': 'נ', 'samekh': 'ס', 'ayin': 'ע',
    'pe': 'פ', 'tsadi': 'צ', 'qof': 'ק', 'resh': 'ר',
    'shin': 'ש', 'tav': 'ת',
    'kaffinal': 'ך', 'finalkaf': 'ך',
    'memfinal': 'ם', 'finalmem': 'ם',
    'nunfinal': 'ן', 'finalnun': 'ן',
    'pefinal': 'ף', 'finalpe': 'ף',
    'tsadifinal': 'ץ', 'finaltsadi': 'ץ',
}

# ניקוד וטעמים
MARKS = {
    'sheva': 'ְ', 'hatafsegol': 'ֱ', 'hatafpatah': 'ֲ',
    'hatafqamats': 'ֳ', 'hiriq': 'ִ', 'tsere': 'ֵ',
    'segol': 'ֶ', 'patah': 'ַ', 'qamats': 'ָ',
    'holam': 'ֹ', 'qubuts': 'ֻ', 'qibuts': 'ֻ',
    'dagesh': 'ּ', 'mapiq': 'ּ',
    'shindot': 'ׁ', 'sindot': 'ׂ', 'rafe': 'ֿ',
}

GLYPHS = dict(LETTERS)
GLYPHS.update(MARKS)

# ‎/hyphenminus אינו בטבלת אדובי. בגופן המנוקד הגליף יושב באמצע גובה האות
# ‎(430–600 מתוך 0–1018) ולא בראשה, כלומר מקף רגיל ולא מקף עברי.
GLYPHS['hyphenminus'] = '-'

# גופני Symbol ו-Wingdings אינם עוברים דרך ‎/Differences אלא נפלטים כקודים
# באזור השימוש הפרטי. אלה כל אלה שמופיעים בדפים בפועל.
SYMBOLS = {
    '': '•',   # תבליט
    '': '←',   # חץ, בשרשראות כמו "חטא ← עונש ← זעקה"
    '': '→',
    '': '🙂',  # Wingdings J — סמיילי שנוצר מ-":)" בוורד
}


def resolve(name):
    """שם גליף → מחרוזת יוניקוד, או None אם אינו מוכר."""
    if name in GLYPHS:
        return GLYPHS[name]
    m = re.fullmatch(r'([a-z]+)with([a-z]+)', name)
    if m and m.group(1) in LETTERS:
        marks = ''
        for part in m.group(2).split('and'):
            if part not in MARKS:
                marks = None
                break
            marks += MARKS[part]
        if marks is not None:
            return LETTERS[m.group(1)] + marks
    # שמות תקניים (hyphenminus, quotedbl, uniXXXX) — לפי טבלת אדובי
    return agl.toUnicode(name) or None


# צירופים מקבלים קוד באזור השימוש הפרטי; החילוץ מחזיר אותם לרצף המקורי.
PUA_BASE = 0xE000


class _Pua:
    def __init__(self):
        self.seq = {}
        self.code = {}

    def get(self, s):
        if s not in self.code:
            c = chr(PUA_BASE + len(self.code))
            self.code[s] = c
            self.seq[c] = s
        return self.code[s]

    def expand(self, text):
        for c, s in self.seq.items():
            if c in text:
                text = text.replace(c, s)
        for c, s in SYMBOLS.items():
            if c in text:
                text = text.replace(c, s)
        return text


def open_fixed(path):
    """פותח PDF שבו שמות הגליפים העבריים הוחלפו בשמות תקניים.

    מחזיר (doc, expand, unknown):
      doc     — מסמך pymupdf שאפשר לחלץ ממנו טקסט כרגיל
      expand  — פונקציה שמחזירה צירופי אות+ניקוד לרצף המקורי
      unknown — שמות גליפים לא-עבריים שלא זוהו, לבדיקה
    """
    doc = pymupdf.open(path)
    pua = _Pua()
    unknown = set()
    for xref in range(1, doc.xref_length()):
        try:
            obj = doc.xref_object(xref)
        except Exception:
            continue
        if '/Differences' not in obj:
            continue
        changed = False

        def sub(m):
            nonlocal changed
            name = m.group(1)
            u = resolve(name)
            if u is None:
                # ‎/g123 ו-‎/glyph216: שמות בלי מידע. אין מה לגזור מהם.
                unknown.add(name)
                return m.group(0)
            changed = True
            c = u if len(u) == 1 else pua.get(u)
            return '/uni%04X' % ord(c)

        head, sep, tail = obj.partition('/Differences')
        end = tail.find(']')
        fixed = head + sep + re.sub(r'/([A-Za-z][A-Za-z0-9._]*)', sub, tail[:end]) + tail[end:]
        if changed:
            doc.update_object(xref, fixed)

    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    doc.save(tmp.name)
    doc.close()
    fixed_doc = pymupdf.open(tmp.name)
    fixed_doc._tmp_path = tmp.name
    return fixed_doc, pua.expand, unknown
