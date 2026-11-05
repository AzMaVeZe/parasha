"""הספר "אללה פרשה" כולו: שער, הקדמה, תוכן עניינים, הפרשות לפי הסדר, והחגים בסוף.

  python3 book/build_book.py [עיצוב] [--sample] [--size b5|17x24]   (ברירת מחדל: b5)

עיצוב: c (ברירת המחדל, ג), c1, c2. עם --sample: רק העמודים הראשונים ושני פרקים, לדוגמה.
הפלט: book/build/out/book-<עיצוב>[-sample].html, ו-book/render.js הופך אותו ל-PDF.

הטקסט: assets/sheet-text (מה שחולץ מה-PDF). זו טיוטה אוטומטית — ניקוי לפי כללים:
- מה שאחרי החידה, הפתרון והחתימה נחתך (החידות לא נכנסות לספר). החידות מזוהות גם לפי הנוסח
  שלהן ב-js/riddles.js, כשאין לפניהן "חידה:"; חידה בחצי השני של הדף — ממנה והלאה הכל יורד.
- שורות כותרת של עמודי הדף ("לק"י פרשת תרומה תשס"ט", "תש"עשבת פרשת וישלח") וכיתובי תמונות
  באנגלית יורדים. תוספת בשורת הכותרת שבראש הדף ("(וקצת פורים)") נשארת ככותרת משנה.
- דף אחד בשני מקומות (וזאת הברכה / הושענא רבה) נכנס לספר פעם אחת.
- פסוק מנוקד שנדבק בחילוץ לטקסט שאחריו נחתך ממנו (split_quote), כך שרק הפסוק מעוצב כמובאה.
- שורות שנשברו בגלל שני הטורים מתחברות: פסקה שאינה נגמרת בסימן פיסוק מתחברת לבאה.
- הערות השוליים: בסוף כל פרק, ממוספרות כמו בדף. מקום הסימון בגוף הטקסט אבד בחילוץ,
  ולכן אינן בתחתית העמוד.
"""
import html
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import house                                   # noqa: E402
import sheet_fixes                             # noqa: E402
from house import mark, plain, render_marks    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build')

TITLE = 'אללה פרשה'
AUTHOR = "אריאל ז'יטניצקי"

NIKUD = re.compile(r'[֑-ׇ]')
TAIL = re.compile(r'פתרון החידה|חידת השבוע|חידה לשבוע|לקינוח|והפעם חידה|את חידת השבוע|שבת שלום|רשימת התפוצה|'
                  r'חידה לסיום|לסיום חידה|ונסיים בחידה|'
                  r'מותר להעביר|להעביר הלאה|\[כתובת מייל\]')
HEADER = re.compile(r'^(לק"י\s*)?(שבת\s+)?(פרשת|פרשות)\s.{1,25}\s(תש[^\s]{1,4})$|^תש[^\s]{1,4}?\s*שבת\s+(פרשת\s)?.{1,25}$')
ENDS = re.compile(r'[.:?!"״׃)\]…;\']\s*$')


def esc(s):
    return html.escape(s, quote=True)


def is_quote(p):
    return len(NIKUD.findall(p)) > len(p) * 0.08


def years():
    src = open(os.path.join(ROOT, 'scripts', 'sheets.mjs'), encoding='utf-8').read()
    return {m.group(1).replace('\\"', '"'): m.group(2)
            for m in re.finditer(r'"((?:[^"\\]|\\.)+)":\s*\{[^}]*year:\s*"([^"]*)"', src)}


def toc_data():
    js = "global.window={};require('./js/data.js');" \
         "console.log(JSON.stringify(window.PARASHA_DATA.map(s=>({id:s.id,name:s.name," \
         "parshiot:s.parshiot.map(p=>({name:p.name,pdf:p.pdf||null}))}))))"
    return json.loads(subprocess.check_output(['node', '-e', js], cwd=ROOT))


def split_quote(p):
    """פסוק מנוקד ואחריו טקסט רגיל שנדבקו בחילוץ לפסקה אחת ("...קָנִיתִי אִישׁ אֶת-ה'. עד עתה עסקנו...")
    נחתכים לשניים, בגבול המשפט שבו הניקוד נגמר. כך רק הפסוק מעוצב כמובאה."""
    sents = re.split(r'(?<=[.:׃;?!])\s+', p)
    if len(sents) < 2:
        return [p]
    voc = lambda t: len(NIKUD.findall(t)) > len(t) * 0.15
    groups = []
    for t in sents:
        if groups and voc(t) == groups[-1][0]:
            groups[-1][1].append(t)
        else:
            groups.append((voc(t), [t]))
    parts = [' '.join(g[1]) for g in groups]
    if len(parts) < 2 or min(len(x) for x in parts) < 12:
        return [p]
    return parts


YEAR = r'תש[א-ת]?["״\'][א-ת]'


def riddles():
    """החידות והפתרונות שבדפים (js/riddles.js) — כדי להוריד אותם מהספר גם כשאין לפניהם "חידה:"."""
    js = "global.window={};require('./js/riddles.js');console.log(JSON.stringify(window.PARASHA_RIDDLES))"
    data = json.loads(subprocess.check_output(['node', '-e', js], cwd=ROOT))
    return [t for r in data.values() for t in (r.get('q'), r.get('a')) if t]


def words(t):
    return re.sub(r'[^א-תA-Za-z0-9]+', ' ', NIKUD.sub('', t)).split()


def shingles(t, n=4):
    w = words(t)
    return {tuple(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


RIDDLE_SH = None


def is_riddle(p):
    """פסקה שרובה (חצי מרצפי ארבע המילים שבה ויותר) לקוח מחידה או מפתרון."""
    global RIDDLE_SH
    if RIDDLE_SH is None:
        RIDDLE_SH = [(shingles(t), ' '.join(words(t))) for t in riddles()]
    sh, flat = shingles(p), ' '.join(words(p))
    if len(flat) < 12:
        return False
    return any(len(sh & rs) >= 0.5 * len(sh) or (len(words(p)) < 4 and flat in rf) for rs, rf in RIDDLE_SH)


def fuzzy(w):
    return re.sub('[וי]', '', w)


def opening(p, names):
    """שורת הכותרת שבראש הדף ("תש"עשבת פרשת וישלח", "פרשת תצוה (וקצת פורים) תשס"ט").

    לפרק בספר יש כבר כותרת ושנה, ולכן: אם השורה רק חוזרת עליהן — None (יורדת). אם יש בה
    תוספת משל אריאל — מוחזרת השורה בלי מה שחוזר (שנה, "פרשת X"), ומוצגת ככותרת משנה.
    פסקה שאינה שורת כותרת — False."""
    if len(p) > 70 or len(p.split()) > 9 or is_quote(p):
        return False
    if not (re.search(YEAR + r'|לק"י|^(שבת\s+)?(פרשת|פרשות)\s', p) or not ENDS.search(p)):
        return False
    keep = {fuzzy(w) for n in names for w in n.split()}
    name = lambda w: fuzzy(re.sub(r'^ו', '', w)) in keep or fuzzy(w) in keep
    key = lambda w: re.fullmatch(r'ו?(שבת|פרשת|פרשות)', w)
    dash = lambda w: w in ('-', '–')
    t = re.sub(r'לק"י|\*|' + YEAR, ' ', p).split()
    # מההתחלה: "שבת פרשת ויקהל פקודי", "תשעה באב"
    i = 0
    while i < len(t) and (key(t[i]) or name(t[i]) or dash(t[i])):
        i += 1
    t = t[i:]
    # מהסוף: "- פרשת נשא", "ופרשת עקב", "– ושבת וזאת הברכה"
    j = len(t)
    while j and name(t[j - 1]):
        j -= 1
    if j < len(t) and j and key(t[j - 1]):
        j -= 1
        while j and (key(t[j - 1]) or dash(t[j - 1])):
            j -= 1
        t = t[:j]
    while t and dash(t[-1]):
        t.pop()
    if not t or ('(' not in ' '.join(t) and len([w for w in t if not name(w)]) <= 1):   # "ויהי מקץ"
        return None
    return ' '.join(t)


def clean(paras, names=()):
    out, subs = [], []
    for i, p in enumerate(paras):
        p = p.strip()
        if not p:
            continue
        if i < 2 and not out:
            o = opening(p, names)
            if o is None:
                continue
            if o:
                subs.append(o)
                continue
        if i and is_riddle(p):
            # חידה בחצי השני של הדף: ממנה והלאה הכל חידה (התמונה, הרמז) וחתימה
            if i >= len(paras) / 2:
                break
            continue
        if TAIL.search(p):
            break
        if HEADER.match(p) or re.fullmatch(r'\d{1,2}', p) or re.fullmatch(r"אריאל ז'יטניצקי\.?", p):
            continue
        for piece in split_quote(p):
            # כיתובי תמונות שהשתרבבו לטקסט — כמעט תמיד באנגלית ("Vidal Henri by Cain, Gardens...")
            lat, heb = len(re.findall(r'[A-Za-z]', piece)), len(re.findall(r'[\u05D0-\u05EA]', piece))
            if lat > 8 and lat > heb:
                # הכיתוב יורד, אבל עברית שנדבקה אליו ("שבין השאר כתב: Wrestling Jacob") נשארת
                rest = re.sub(r"(?:[A-Za-z][A-Za-z.,'()]*\s*){2,}", '', piece).strip()
                if len(re.findall(r'[\u05D0-\u05EA]{2,}', rest)) >= 2 and 'mailto' not in piece:
                    out.append(mark('chk', rest, 'הוסר כאן כיתוב תמונה באנגלית — לבדוק שלא חסר טקסט'))
                continue
            out.append(piece)
    # שורות שנשברו בין טורים: פסקה בלי סימן סוף מתחברת לבאה, אם שתיהן מאותו סוג
    joined = []
    for p in out:
        if joined and not ENDS.search(plain(joined[-1])) and is_quote(plain(joined[-1])) == is_quote(plain(p)) \
                and not p.startswith('-'):
            joined[-1] = joined[-1] + ' ' + p
        else:
            joined.append(p)
    return joined, subs


def chapters():
    y = years()
    parts, used = [], set()
    for sefer in toc_data():
        seen, chs = {}, []
        for p in sefer['parshiot']:
            if not p['pdf']:
                continue
            key = p['pdf']
            if key in seen:                       # דף אחד לשתי פרשות (ויקהל-פקודי וכו')
                seen[key]['names'].append(p['name'])
                continue
            if key in used:                       # הושענא רבה: אותו דף כמו וזאת הברכה — פעם אחת בספר
                continue
            used.add(key)
            f = os.path.join(ROOT, p['pdf'].replace('assets/pdfs/', 'assets/sheet-text/').replace('.pdf', '.json'))
            if not os.path.exists(f):
                continue
            t = json.load(open(f, encoding='utf-8'))
            names = [q['name'] for q in sefer['parshiot'] if q['pdf'] == key]
            paras, subs = clean(t['paragraphs'], names)
            ch = {'names': [p['name']], 'year': y.get(p['name'], ''), 'paras': paras, 'subs': subs,
                  'notes': [n for n in t.get('footnotes', []) if 'החידה' not in n['text']],
                  'chag': sefer['id'] == 'chagim', 'id': 'ch-%d' % len(parts) + '-%d' % len(chs)}
            seen[key] = ch
            chs.append(ch)
        if chs:
            parts.append({'name': sefer['name'], 'chag': sefer['id'] == 'chagim', 'chapters': chs})
    return parts


def hebnum(n):
    if n in (15, 16):
        return {15: 'טו', 16: 'טז'}[n]
    return ('' if n < 10 else 'יכלמנ'[n // 10 - 1]) + ('' if n % 10 == 0 else 'אבגדהוזחט'[n % 10 - 1])


def verses(book, ch, a, b):
    """פסוקים מהנוסח המנוקד התקני, עם מספר פסוק, בלי שם מפורש."""
    text = sheet_fixes._book(book)[ch - 1]
    out = []
    for n in range(a, b + 1):
        v = re.sub(r'\{[פס]\}|׃', ' ', text[n - 1]).strip()
        v = house.shem(v)
        v = re.sub(r'(?<![א-ת])(א[ְ-ּ]*)(ל[֑-ׇ]*ה[֑-ׇ]*[יו])', r'\1-\2', v)   # אֱ-לֹהֶיךָ
        out.append(f'<b>{hebnum(n)}</b> {esc(v)}')
    return ' '.join(out)


def shoftim_table():
    """הטבלה שבדף שופטים (במדבר לה מול דברים יט) נשזרה בחילוץ שורה בשורה. נבנית מחדש מהנוסח התקני."""
    why = esc('הטבלה נבנתה מחדש מנוסח מנוקד תקני; ההדגשות שבדף לא הועברו — לבדוק מול הדף')
    return ('<table class="parallel"><thead><tr><th>במדבר לה (מסעי)</th><th>דברים יט (שופטים)</th></tr></thead>'
            f'<tbody><tr><td>{verses("Numbers", 35, 9, 34)}</td><td>{verses("Deuteronomy", 19, 2, 10)}</td></tr></tbody>'
            f'</table><p class="table-why">[{why}]</p>')


def edit(parts):
    """העריכה שאריאל אישר (book/house.py): שינויי תוכן, כללי בית, וסימון מקומות לבדיקה."""
    chs = [c for p in parts for c in p['chapters']]
    for c in chs:
        c['title'] = ch_title(c)
    for e in house.apply_edits(chs):
        print('עריכה לא הוחלה:', e, file=sys.stderr)
    for c in chs:
        paras, prev = [], ''
        for p in c['paras']:
            paras.append(house.house(p, plain(prev).rstrip().endswith(':'), is_quote(plain(p))))
            prev = p
        c['paras'] = [p for p in paras if plain(p).strip() or house.MO in p]
        for n in c['notes']:
            n['text'] = house.house(n['text'])
        if c['title'] == 'פרשת שופטים':
            i = next(k for k, p in enumerate(c['paras']) if 'רוצח בשגגה' in p)
            c['paras'][i] = 'רוצח בשגגה / סימני שאלה וסימני קריאה'      # בלי כותרות הטורים שנדבקו אליה
            j = i + 1
            while j < len(c['paras']) and is_quote(plain(c['paras'][j])):
                j += 1
            c['paras'][i + 1:j] = ['\x00TABLE']
        house.checks(c, is_quote)
    return parts


def ch_title(ch):
    if ch['chag']:
        return ' ו'.join(ch['names'])
    return ('פרשות ' if len(ch['names']) > 1 else 'פרשת ') + '–'.join(ch['names'])


PROOF_CSS = '''
mark.chg { background: #c9f0c0; color: inherit }
del { color: #b3261e }
mark.chk { background: #ffe95c; color: inherit }
.why, .table-why { display: inline; font: 7.5pt 'Assistant'; color: #9a4d00; text-indent: 0 }
.legend { padding-top: 60mm; text-align: right }
.legend h2 { font-family: 'Assistant'; font-size: 1.6em }
'''


DESIGNS = {
    # ג — כפי שנבחר: כותרות באסיסטנט, גוף בדוד, פסוקים בפרנק רוהל עם פס בצד
    'c': '''
.ch-head { text-align: right; margin: 20mm 0 9mm; border-bottom: 1.2pt solid #111; padding-bottom: 4mm }
.ch-kicker { font: 700 9pt 'Assistant'; letter-spacing: .12em; color: #555 }
.ch-head h2 { font-family: 'Assistant'; font-weight: 700; font-size: 2.3em; margin: 1mm 0 0 }
.ch-year { font: 10pt 'Assistant'; color: #555 }
p.q { font-family: 'Frank Ruhl Libre', serif; margin: .5lh 0 .5lh 4mm; padding-right: 4mm; border-right: 1.6pt solid #555 }
''',
    # ג1 — אוורירי: פתיחת פרק נמוכה בעמוד, שם הפרשה דק וגדול, פסוקים על רקע אפור בהיר
    'c1': '''
.ch-head { text-align: right; margin: 48mm 0 12mm }
.ch-kicker { font: 400 9pt 'Assistant'; letter-spacing: .25em; color: #666; border-top: .6pt solid #999; padding-top: 2mm; display: inline-block }
.ch-head h2 { font-family: 'Assistant'; font-weight: 400; font-size: 3em; margin: 2mm 0 0; letter-spacing: -.01em }
.ch-year { font: 400 10pt 'Assistant'; color: #666; margin-top: 1mm }
p.q { font-family: 'Frank Ruhl Libre', serif; margin: 3.5mm 0; padding: 2.5mm 4mm; background: #f1f1f1; border-radius: 1mm }
''',
    # ג2 — דחוס ובולט: פס עבה מעל שם הפרשה, מילות פתיחה מודגשות, פסוקים עם פס עבה ומודגש
    'c2': '''
.ch-head { text-align: right; margin: 14mm 0 8mm; border-top: 4pt solid #111; padding-top: 3mm }
.ch-kicker { font: 800 8.5pt 'Assistant'; letter-spacing: .1em; color: #111 }
.ch-head h2 { font-family: 'Assistant'; font-weight: 800; font-size: 2.1em; margin: 0 }
.ch-year { font: 700 9.5pt 'Assistant'; color: #555 }
.chapter > p.first::first-line { font-weight: 700 }
p.q { font-family: 'Frank Ruhl Libre', serif; margin: 3mm 0 3mm 6mm; padding-right: 3.5mm; border-right: 3pt solid #111; font-size: .98em }
''',
}

# גודל הספר. בבוקפוד יש מוכנים A5, B5 (16.5×23.5), 13.5×21 ו-A4; 17×24 הוא "התאמה אישית".
SIZES = {'17x24': ('170mm 240mm', '20mm', '22mm', '22mm', '17mm'),
         'b5': ('165mm 235mm', '19mm', '21mm', '21mm', '16mm')}

BASE_CSS = '''
@page { size: SIZE; margin: TOP OUTER BOTTOM OUTER;
  @footnote { border-top: 0.4pt solid #888; padding-top: 2mm; margin-top: 3mm; } }
/* ספר עברי נפתח מימין: עמוד אי-זוגי (Paged.js קורא לו :right) הוא השמאלי בכפולה, והשדרה מימינו */
@page :right { margin-right: INNER; margin-left: OUTER;
  /* המספר בצד החיצוני (שמאל): כיוון LTR בתיבה הזו, כך שהמספר בא ראשון משמאל */
  @top-left { content: counter(page) "   |   " string(chapter); font: 8.5pt 'Assistant'; color: #000; direction: ltr; unicode-bidi: isolate } }
@page :left { margin-left: INNER; margin-right: OUTER;
  @top-right { content: counter(page) "   |   TITLE"; font: 8.5pt 'Assistant'; color: #000; direction: rtl } }
@page :blank { @top-left { content: none } @top-right { content: none } }
@page front { @top-left { content: none } @top-right { content: none } }
@page opener { @top-left { content: none } @top-right { content: none } }
html { font-family: 'David Libre', serif; font-size: 11.5pt; line-height: 1.68; color: #000 }
body { margin: 0 }
/* Paged.js מזהה גלישה לעמוד הבא רק כשהעמודות זורמות משמאל לימין: המסמך LTR, התוכן RTL */
.book, .pagedjs_margin-content, .pagedjs_footnote_area { direction: rtl }
/* בלי רווח בין פסקאות אלא הזחה, ומרווחים בשורות שלמות (lh) — כך תחתית כל עמוד מלא באותו גובה */
p { margin: 0; text-indent: 1.2em; text-align: justify; hyphens: none; orphans: 2; widows: 2 }
p.first, p.q, p.q + p, p.d, p.li, .ch-head + p, table + p, .about p, .intro p, .front p { text-indent: 0 }
p.li { padding-right: 3.4mm; text-indent: -3.4mm }
table.parallel { width: 100%; border-collapse: collapse; margin: .5lh 0; font-family: 'Frank Ruhl Libre', serif; font-size: 9.6pt; line-height: 1.55 }
table.parallel th { font: 700 9pt 'Assistant'; border-bottom: .8pt solid #000; padding: 1mm 2mm; text-align: right }
table.parallel td { vertical-align: top; padding: 1.5mm 2mm; text-align: justify; width: 50% }
table.parallel td + td, table.parallel th + th { border-right: .5pt solid #555 }
.table-why { display: none }
.about { break-before: right }
.about h2 { font-family: 'Assistant'; font-weight: 700; font-size: 1.9em; margin: 20mm 0 8mm }
.toc-part { break-inside: avoid }
.toc h3 { break-after: avoid }
p.d { font-family: 'Assistant'; font-size: .95em; margin-right: 4mm }
.front { page: front; break-after: page; text-align: center }
.title-page { padding-top: 62mm }
.title-page h1 { font-family: 'Assistant'; font-weight: 800; font-size: 34pt; margin: 0; letter-spacing: -.01em }
.title-page .sub { font: 400 12pt 'Assistant'; color: #444; margin-top: 4mm }
.title-page .author { font: 700 13pt 'Assistant'; margin-top: 70mm }
.imprint { padding-top: 150mm; font: 9pt 'Assistant'; color: #555; text-align: right }
.intro { break-before: right }
.intro h2, .toc h2 { font-family: 'Assistant'; font-weight: 700; font-size: 1.9em; margin: 20mm 0 8mm }
.placeholder { color: #777; font-style: normal }
.toc { break-before: right; text-align: right }
.toc h3 { font: 700 10pt 'Assistant'; letter-spacing: .1em; color: #555; margin: 6mm 0 1.5mm; border-bottom: .5pt solid #bbb; padding-bottom: 1mm }
.toc ol { list-style: none; margin: 0; padding: 0; columns: 2; column-gap: 10mm }
.toc li { display: flex; gap: 2mm; font-size: 10.5pt; line-height: 1.75; break-inside: avoid }
.toc li a { color: inherit; text-decoration: none; flex: 1; display: flex }
.toc li a::after { content: target-counter(attr(href), page); margin-inline-start: auto; font-family: 'Assistant'; font-size: 9.5pt; color: #444 }
.part { page: opener; break-before: right; break-after: page; text-align: center; padding-top: 85mm }
.part h2 { font-family: 'Assistant'; font-weight: 800; font-size: 26pt; margin: 0 }
.chapter { break-before: page; string-set: chapter attr(data-title) }
.ch-sub { font: 400 12pt 'Assistant'; color: #333; margin-top: 1mm }
.notes { margin-top: 6mm; border-top: .5pt solid #999; padding-top: 2mm }
.notes h4 { font: 700 9pt 'Assistant'; margin: 0 0 1mm; color: #333 }
.notes ol { list-style: none; margin: 0; padding: 0; columns: 2; column-gap: 6mm }
.notes li { font-family: 'Assistant'; font-size: 8.6pt; line-height: 1.5; margin-bottom: .8mm; text-align: justify; break-inside: avoid-column }
.notes .n { font-weight: 700; margin-inline-end: 1.5mm }
'''


LATIN = re.compile(r"(?<![\ue000A-Za-z])[A-Za-z][A-Za-z0-9 .,;:'’&%()/\-]*[A-Za-z0-9.)]")


def para_html(p, proof):
    """פסקה: אנגלית בבידוד LTR (שלא תתהפך), ואז הסימונים."""
    p = LATIN.sub(lambda m: '\u2066' + m.group() + '\u2069', p)
    return render_marks(esc(p), proof)


def build(design='c', sample=False, size='b5', proof=False, lh=None):   # הוחלט: B5, הגודל המוכן של בוקפוד
    house.NOTES.clear()
    parts = edit(chapters())
    toc = []
    for part in parts:
        toc.append(f'<div class="toc-part"><h3>{esc(part["name"])}</h3><ol>' + ''.join(
            f'<li><a href="#{c["id"]}">{esc(ch_title(c))}</a></li>' for c in part['chapters']) + '</ol></div>')
    if sample:
        parts = [{**parts[0], 'chapters': parts[0]['chapters'][:2]}]
    body = []
    for part in parts:
        body.append(f'<section class="part"><h2>{esc(part["name"])}</h2></section>')
        for ch in part['chapters']:
            title = ch_title(ch)
            kicker = part['name']
            h = [f'<section class="chapter" id="{ch["id"]}" data-title="{esc(title)}">',
                 f'<header class="ch-head"><div class="ch-kicker">{esc(kicker)}</div><h2>{esc(title)}</h2>'
                 + ''.join(f'<div class="ch-sub">{esc(t)}</div>' for t in ch['subs'])
                 + (f'<div class="ch-year">{esc(ch["year"])}</div>' if ch['year'] else '') + '</header>']
            for i, p in enumerate(ch['paras']):
                if p == '\x00TABLE':
                    h.append(shoftim_table())
                    continue
                pl = plain(p)
                cls = ('q' if is_quote(pl) else 'd' if pl.startswith(('-', '–')) else
                       'li' if pl.startswith(('•', '·')) else 'first' if i == 0 else '')
                h.append(f'<p class="{cls}">{para_html(p, proof)}</p>' if cls else f'<p>{para_html(p, proof)}</p>')
            if ch['notes']:
                h.append('<aside class="notes"><h4>הערות</h4><ol>' + ''.join(
                    f'<li><span class="n">{esc(str(n.get("n") or ""))}</span>{para_html(n["text"], proof)}</li>'
                    for n in ch['notes']) + '</ol></aside>')
            h.append('</section>')
            body.append('\n'.join(h))
    front = f'''
<section class="front title-page"><h1>{esc(TITLE)}</h1><div class="sub">דפים לפרשת השבוע ולחגים</div><div class="author">{esc(AUTHOR)}</div></section>
<section class="front imprint"><p class="placeholder">[עמוד הזכויות: שנת הוצאה, ISBN, זכויות יוצרים — יושלם לפני ההגשה]</p></section>
<section class="intro"><h2>הקדמה</h2><p class="placeholder">[ההקדמה של אריאל — תיכתב בהמשך]</p></section>
<section class="toc"><h2>תוכן העניינים</h2>{"".join(toc)}</section>'''
    about = ('<section class="about"><h2>על המחבר</h2>'
             '<p class="placeholder">[כמה שורות על אריאל — יכתוב אריאל]</p></section>')
    legend = ('<section class="front legend"><h2>גרסת הגהה</h2><p><mark class="chg">ירוק</mark> — נוסח שהשתנה בעריכה '
              '(הנוסח הקודם <del>מחוק</del> לפניו). <mark class="chk">צהוב</mark> — מקום שדורש בדיקה שלך מול הדף, '
              'והסיבה <span class="why">[בסוגריים]</span>. כללי הבית (גרשיים, מקף, כתיב) הוחלו בלי סימון.</p></section>'
              if proof else '')
    sz, top, bottom, inner, outer = SIZES[size]
    css = (BASE_CSS.replace('TITLE', TITLE).replace('SIZE', sz).replace('TOP', top).replace('BOTTOM', bottom)
           .replace('INNER', inner).replace('OUTER', outer)) + DESIGNS[design] + (PROOF_CSS if proof else '')
    if lh:
        css += f'\nhtml {{ line-height: {lh} }}' 
    return f'''<!doctype html>
<html lang="he"><head><meta charset="utf-8"><title>{esc(TITLE)}</title>
<link rel="stylesheet" href="file://{BUILD}/fonts/book-fonts.css">
<style>{css}</style></head><body><div class="book">
{legend}{front}
{chr(10).join(body)}
{about}
</div><script>window.PagedConfig = {{ after: () => {{ window.__pagedDone = true }} }}</script>
<script src="file://{HERE}/vendor/paged.polyfill.js"></script></body></html>'''


if __name__ == '__main__':
    flags = {'--size': 'b5', '--lh': None}
    argv = sys.argv[1:]
    for k in flags:
        if k in argv:
            flags[k] = argv[argv.index(k) + 1]
            del argv[argv.index(k):argv.index(k) + 2]
    args = [a for a in argv if not a.startswith('--')]
    design = args[0] if args else 'c'
    sample, proof, size, lh = '--sample' in argv, '--proof' in argv, flags['--size'], flags['--lh']
    os.makedirs(os.path.join(BUILD, 'out'), exist_ok=True)
    name = (f'book-{design}' + ('-sample' if sample else '') + ('' if size == 'b5' else '-' + size)
            + ('-proof' if proof else '') + (f'-lh{lh}' if lh else ''))
    open(os.path.join(BUILD, 'out', name + '.html'), 'w', encoding='utf-8').write(build(design, sample, size, proof, lh))
    print(name)
