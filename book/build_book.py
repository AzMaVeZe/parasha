"""הספר "אללה פרשה" כולו: שער, הקדמה, תוכן עניינים, הפרשות לפי הסדר, והחגים בסוף.

  python3 book/build_book.py [עיצוב] [--sample] [--size 17x24|b5]

עיצוב: c (ברירת המחדל, ג), c1, c2. עם --sample: רק העמודים הראשונים ושני פרקים, לדוגמה.
הפלט: book/build/out/book-<עיצוב>[-sample].html, ו-book/render.js הופך אותו ל-PDF.

הטקסט: assets/sheet-text (מה שחולץ מה-PDF). זו טיוטה אוטומטית — ניקוי לפי כללים:
- מה שאחרי החידה, הפתרון והחתימה נחתך (החידות לא נכנסות לספר).
- שורות כותרת של עמודי הדף ("לק"י פרשת תרומה תשס"ט") וכיתובי תמונות באנגלית יורדים.
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build')

TITLE = 'אללה פרשה'
AUTHOR = "אריאל ז'יטניצקי"

NIKUD = re.compile(r'[֑-ׇ]')
TAIL = re.compile(r'פתרון החידה|חידת השבוע|חידה לשבוע|לקינוח|והפעם חידה|את חידת השבוע|שבת שלום|רשימת התפוצה|'
                  r'מותר להעביר|להעביר הלאה|\[כתובת מייל\]')
HEADER = re.compile(r'^(לק"י\s*)?(שבת\s+)?(פרשת|פרשות)\s.{1,25}\s(תש[^\s]{1,4})$|^תש[^\s]{1,4}\s+שבת\s+פרשת\s.{1,25}$')
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


def clean(paras):
    out = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if TAIL.search(p):
            break
        if HEADER.match(p) or re.fullmatch(r'\d{1,2}', p) or re.fullmatch(r"אריאל ז'יטניצקי\.?", p):
            continue
        # כיתובי תמונות שהשתרבבו לטקסט — כמעט תמיד באנגלית ("Vidal Henri by Cain, Gardens...")
        lat, heb = len(re.findall(r'[A-Za-z]', p)), len(re.findall(r'[\u05D0-\u05EA]', p))
        if lat > 8 and lat > heb:
            continue
        out.append(p)
    # שורות שנשברו בין טורים: פסקה בלי סימן סוף מתחברת לבאה, אם שתיהן מאותו סוג
    joined = []
    for p in out:
        if joined and not ENDS.search(joined[-1]) and is_quote(joined[-1]) == is_quote(p) and not p.startswith('-'):
            joined[-1] = joined[-1] + ' ' + p
        else:
            joined.append(p)
    return joined


def chapters():
    y = years()
    parts = []
    for sefer in toc_data():
        seen, chs = {}, []
        for p in sefer['parshiot']:
            if not p['pdf']:
                continue
            key = p['pdf']
            if key in seen:                       # דף אחד לשתי פרשות (ויקהל-פקודי וכו')
                seen[key]['names'].append(p['name'])
                continue
            f = os.path.join(ROOT, p['pdf'].replace('assets/pdfs/', 'assets/sheet-text/').replace('.pdf', '.json'))
            if not os.path.exists(f):
                continue
            t = json.load(open(f, encoding='utf-8'))
            ch = {'names': [p['name']], 'year': y.get(p['name'], ''), 'paras': clean(t['paragraphs']),
                  'notes': t.get('footnotes', []), 'chag': sefer['id'] == 'chagim', 'id': 'ch-%d' % len(parts) + '-%d' % len(chs)}
            seen[key] = ch
            chs.append(ch)
        if chs:
            parts.append({'name': sefer['name'], 'chag': sefer['id'] == 'chagim', 'chapters': chs})
    return parts


def ch_title(ch):
    if ch['chag']:
        return ' ו'.join(ch['names'])
    return ('פרשות ' if len(ch['names']) > 1 else 'פרשת ') + '–'.join(ch['names'])


DESIGNS = {
    # ג — כפי שנבחר: כותרות באסיסטנט, גוף בדוד, פסוקים בפרנק רוהל עם פס בצד
    'c': '''
.ch-head { text-align: right; margin: 20mm 0 9mm; border-bottom: 1.2pt solid #111; padding-bottom: 4mm }
.ch-kicker { font: 700 9pt 'Assistant'; letter-spacing: .12em; color: #555 }
.ch-head h2 { font-family: 'Assistant'; font-weight: 700; font-size: 2.3em; margin: 1mm 0 0 }
.ch-year { font: 10pt 'Assistant'; color: #555 }
p.q { font-family: 'Frank Ruhl Libre', serif; margin: 3mm 0 3mm 4mm; padding-right: 4mm; border-right: 1.6pt solid #888 }
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
  @top-left { content: counter(page) "   |   " string(chapter); font: 8.5pt 'Assistant'; color: #333; direction: rtl } }
@page :left { margin-left: INNER; margin-right: OUTER;
  @top-right { content: counter(page) "   |   TITLE"; font: 8.5pt 'Assistant'; color: #333; direction: rtl } }
@page :blank { @top-left { content: none } @top-right { content: none } }
@page front { @top-left { content: none } @top-right { content: none } }
@page opener { @top-left { content: none } @top-right { content: none } }
html { font-family: 'David Libre', serif; font-size: 11.5pt; line-height: 1.68; color: #111 }
body { margin: 0 }
/* Paged.js מזהה גלישה לעמוד הבא רק כשהעמודות זורמות משמאל לימין: המסמך LTR, התוכן RTL */
.book, .pagedjs_margin-content, .pagedjs_footnote_area { direction: rtl }
p { margin: 0 0 1.6mm; text-align: justify; hyphens: none; orphans: 2; widows: 2 }
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
.notes { margin-top: 6mm; border-top: .5pt solid #999; padding-top: 2mm }
.notes h4 { font: 700 9pt 'Assistant'; margin: 0 0 1mm; color: #333 }
.notes ol { list-style: none; margin: 0; padding: 0 }
.notes li { font-family: 'Assistant'; font-size: 8.6pt; line-height: 1.5; margin-bottom: .8mm; text-align: justify }
.notes .n { font-weight: 700; margin-inline-end: 1.5mm }
'''


def build(design='c', sample=False, size='17x24'):
    parts = chapters()
    if sample:
        parts = [{**parts[0], 'chapters': parts[0]['chapters'][:2]}]
    toc = []
    for part in chapters():
        toc.append(f'<h3>{esc(part["name"])}</h3><ol>' + ''.join(
            f'<li><a href="#{c["id"]}">{esc(ch_title(c))}</a></li>' for c in part['chapters']) + '</ol>')
    body = []
    for part in parts:
        body.append(f'<section class="part"><h2>{esc(part["name"])}</h2></section>')
        for ch in part['chapters']:
            title = ch_title(ch)
            kicker = part['name']
            h = [f'<section class="chapter" id="{ch["id"]}" data-title="{esc(title)}">',
                 f'<header class="ch-head"><div class="ch-kicker">{esc(kicker)}</div><h2>{esc(title)}</h2>'
                 + (f'<div class="ch-year">{esc(ch["year"])}</div>' if ch['year'] else '') + '</header>']
            for i, p in enumerate(ch['paras']):
                cls = 'q' if is_quote(p) else ('d' if p.startswith('-') else ('first' if i == 0 else ''))
                h.append(f'<p class="{cls}">{esc(p)}</p>' if cls else f'<p>{esc(p)}</p>')
            if ch['notes']:
                h.append('<aside class="notes"><h4>הערות</h4><ol>' + ''.join(
                    f'<li><span class="n">{esc(str(n.get("n") or ""))}</span>{esc(n["text"])}</li>' for n in ch['notes'])
                    + '</ol></aside>')
            h.append('</section>')
            body.append('\n'.join(h))
    front = f'''
<section class="front title-page"><h1>{esc(TITLE)}</h1><div class="sub">דפים לפרשת השבוע ולחגים</div><div class="author">{esc(AUTHOR)}</div></section>
<section class="front imprint"><p class="placeholder">[עמוד הזכויות: שנת הוצאה, ISBN, זכויות יוצרים — יושלם לפני ההגשה]</p></section>
<section class="intro"><h2>הקדמה</h2><p class="placeholder">[ההקדמה של אריאל — תיכתב בהמשך]</p></section>
<section class="toc"><h2>תוכן העניינים</h2>{"".join(toc)}</section>'''
    sz, top, bottom, inner, outer = SIZES[size]
    css = (BASE_CSS.replace('TITLE', TITLE).replace('SIZE', sz).replace('TOP', top).replace('BOTTOM', bottom)
           .replace('INNER', inner).replace('OUTER', outer)) + DESIGNS[design]
    return f'''<!doctype html>
<html lang="he"><head><meta charset="utf-8"><title>{esc(TITLE)}</title>
<link rel="stylesheet" href="file://{BUILD}/fonts/book-fonts.css">
<style>{css}</style></head><body><div class="book">
{front}
{chr(10).join(body)}
</div><script>window.PagedConfig = {{ after: () => {{ window.__pagedDone = true }} }}</script>
<script src="file://{HERE}/vendor/paged.polyfill.js"></script></body></html>'''


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    design = args[0] if args else 'c'
    sample = '--sample' in sys.argv
    size = sys.argv[sys.argv.index('--size') + 1] if '--size' in sys.argv else '17x24'
    args = [a for a in args if a not in SIZES]
    os.makedirs(os.path.join(BUILD, 'out'), exist_ok=True)
    name = f'book-{design}' + ('-sample' if sample else '') + ('' if size == '17x24' else '-' + size)
    open(os.path.join(BUILD, 'out', name + '.html'), 'w', encoding='utf-8').write(build(design, sample, size))
    n = sum(len(p['chapters']) for p in chapters())
    print(name, '—', n, 'chapters in the TOC')
