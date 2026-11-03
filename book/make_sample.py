"""Sample chapter (בהעלותך) for the book, from the text extracted from the PDF.

Paragraphs broken by the two-column layout are joined, the image caption that slipped into the text
is dropped, and the four footnotes are put back as real footnotes. Footnote positions are a guess:
the markers are lost in the extraction. Output: one HTML per trim size, paginated by Paged.js.
"""
import json, html, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build')
P = json.load(open(f'{ROOT}/assets/sheet-text/bamidbar-בהעלותך.json', encoding='utf-8'))['paragraphs']
FN = {  # footnote texts (paragraph index in the extraction)
    'hirsch': P[16], 'onesh': P[30], 'berk': P[31], 'chagiga': P[32],
}
def fn(k):
    return f'<span class="fn">{html.escape(FN[k])}</span>'

def para(*idx):
    return ' '.join(P[i] for i in idx)

# (kind, text-html)
body = [
    ('p', html.escape(P[0])),
    ('q', html.escape(P[1])),
    ('p', html.escape(P[2])),
    ('q', html.escape(P[3])),
    ('p', html.escape(P[4])),
    ('q', html.escape(P[5])),
    ('p', html.escape(para(6, 7))),
    ('p', html.escape(para(8, 9, 10, 11, 12))),
    ('p', html.escape(para(13, 14)) + fn('hirsch')),
    ('p', html.escape(P[15]).replace('שנתייחדה למשה,', 'שנתייחדה למשה,' + fn('onesh'), 1) + ' ' + html.escape(P[17])),
    ('p', html.escape(P[18])),
    ('p', html.escape(P[19].replace(' הנביא עמוס, גוסטב דורה', ''))),
    ('p', html.escape(P[20]) + fn('berk')),
    ('q', html.escape(P[21])),
    ('p', html.escape(P[22]) + fn('chagiga')),
    ('q', html.escape(P[23])),
    ('p', html.escape(P[24])),
]
# the aggadah, line by line, with Ariel's commentary between the lines
for i in [25, 26, 27, 28]:
    body.append(('d' if P[i].startswith('-') or i == 25 else 'p', html.escape(P[i])))
body.append(('p', html.escape(para(29, 33))))
for i in range(34, 45):
    body.append(('d' if P[i].startswith('-') else ('q' if i == 44 else 'p'), html.escape(P[i])))

SIZES = {
    # name: (width, height, top, bottom, inner, outer, font pt)
    '17x24': ('170mm', '240mm', '20mm', '22mm', '22mm', '17mm', '11.5pt'),
    '14.8x21': ('148mm', '210mm', '16mm', '19mm', '19mm', '14mm', '10.5pt'),
}

DESIGNS = {
    # א — מה שראית: פרנק רוהל, פסוקים בדוד, כותרות בצד החיצוני
    'a': '',
    # ב — קלאסי: הכל בפרנק רוהל, פתיחת פרק גדולה עם קו כפול, כותרות ומספרי עמודים במרכז
    'b': '''
@page :right { @top-left { content: none } @bottom-left { content: none }
  @top-center { content: string(chapter); font: 9pt 'Frank Ruhl Libre'; letter-spacing: .05em; direction: rtl }
  @bottom-center { content: counter(page); font: 9.5pt 'Frank Ruhl Libre' } }
@page :left { @top-right { content: none } @bottom-right { content: none }
  @top-center { content: "בין הנכתב לנגלה"; font: 9pt 'Frank Ruhl Libre'; letter-spacing: .05em; direction: rtl }
  @bottom-center { content: counter(page); font: 9.5pt 'Frank Ruhl Libre' } }
@page :first { @top-center { content: none } }
.ch-head { margin: 34mm 0 12mm }
.ch-kicker { font: 10pt 'Frank Ruhl Libre'; letter-spacing: .3em }
h1 { font-size: 2.6em; font-weight: 500 }
.ch-year { font: 11pt 'Frank Ruhl Libre' }
.ch-rule { width: 40mm; border-top: 0.5pt solid #222; height: 1.6pt; border-bottom: 0.5pt solid #222; margin-top: 6mm }
.ch-head + p::first-line { font-weight: 700 }
p.q, p.d { font-family: 'Frank Ruhl Libre', serif }
p.q { font-size: .96em; margin: 3mm 10mm }
''',
    # ג — מודרני: כותרות באסיסטנט, גוף בדוד, פסוקים עם פס בצד כמו באתר, מספר עמוד למעלה
    'c': '''
@page :right { @bottom-left { content: none }
  @top-left { content: counter(page) "   |   " string(chapter); font: 8.5pt 'Assistant'; color: #333; direction: rtl } }
@page :left { @bottom-right { content: none }
  @top-right { content: counter(page) "   |   בין הנכתב לנגלה"; font: 8.5pt 'Assistant'; color: #333; direction: rtl } }
html { font-family: 'David Libre', serif; line-height: 1.68 }
.ch-head { text-align: right; margin: 22mm 0 10mm; border-bottom: 1.2pt solid #111; padding-bottom: 4mm }
.ch-kicker { font: 700 9pt 'Assistant'; letter-spacing: .12em; color: #555 }
h1 { font-family: 'Assistant'; font-weight: 700; font-size: 2.3em; margin: 1mm 0 0 }
.ch-year { font: 10pt 'Assistant'; color: #555 }
.ch-rule { display: none }
p { text-indent: 0; margin-bottom: 1.6mm }
p.q { font-family: 'Frank Ruhl Libre', serif; margin: 3mm 0 3mm 4mm; padding-right: 4mm; border-right: 1.6pt solid #888 }
p.d { font-family: 'Assistant'; font-weight: 400; font-size: .95em; margin-right: 4mm }
.fn { font-family: 'Assistant' }
''',
}

def page_html(size='17x24', design='c'):   # הוחלט: 17×24, עיצוב ג
    w, h, top, bot, inner, outer, fs = SIZES[size]
    paras = []
    for kind, t in body:
        cls = {'p': '', 'q': ' class="q"', 'd': ' class="d"'}[kind]
        paras.append(f'<p{cls}>{t}</p>')
    return f'''<!doctype html>
<html lang="he"><head><meta charset="utf-8">
<title>בין הנכתב לנגלה — פרק לדוגמה</title>
<link rel="stylesheet" href="file://{BUILD}/fonts/book-fonts.css">
<style>
@page {{ size: {w} {h}; margin: {top} {outer} {bot} {outer};
  @footnote {{ border-top: 0.4pt solid #888; padding-top: 2mm; margin-top: 3mm; }} }}
/* ספר עברי נפתח מימין: עמוד אי-זוגי (Paged.js קורא לו :right) הוא העמוד השמאלי
   בכפולה, והשדרה מימינו. השוליים הפנימיים — לכיוון השדרה — רחבים יותר. */
@page :right {{ margin-right: {inner}; margin-left: {outer};
  @top-left {{ content: string(chapter); font: 8.5pt 'Assistant'; color:#555; direction: rtl }}
  @bottom-left {{ content: counter(page); font: 9pt 'Frank Ruhl Libre' }} }}
@page :left  {{ margin-left: {inner}; margin-right: {outer};
  @top-right {{ content: "בין הנכתב לנגלה"; font: 8.5pt 'Assistant'; color:#555; direction: rtl }}
  @bottom-right {{ content: counter(page); font: 9pt 'Frank Ruhl Libre' }} }}
@page :first {{ @top-left {{ content: none }} @top-right {{ content: none }} }}
html {{ font-family: 'Frank Ruhl Libre', serif; font-size: {fs}; line-height: 1.6; color: #111;
  font-variant-ligatures: common-ligatures; }}
body {{ margin: 0 }}
/* Paged.js מזהה גלישה לעמוד הבא רק כשהעמודות זורמות משמאל לימין, ולכן המסמך
   עצמו LTR, והתוכן — וגם השוליים והכותרות — RTL */
.chapter, .pagedjs_margin-content {{ direction: rtl }}
.chapter {{ string-set: chapter attr(data-title) }}

.ch-head {{ text-align: center; margin: 18mm 0 9mm }}
.ch-kicker {{ font: 9pt 'Assistant'; letter-spacing: .08em; color: #555 }}
h1 {{ font-weight: 700; font-size: 2.1em; margin: 2mm 0 1mm; line-height: 1.2 }}
.ch-year {{ font: 10pt 'Assistant'; color: #555 }}
.ch-rule {{ width: 18mm; height: 0; border-top: 0.6pt solid #444; margin: 5mm auto 0 }}
p {{ margin: 0; text-align: justify; text-indent: 1.2em; hyphens: none; orphans: 2; widows: 2 }}
.ch-head + p, .q + p, .d + p, p.first {{ text-indent: 0 }}
p.q {{ font-family: 'David Libre', 'Frank Ruhl Libre', serif; font-size: 1.04em; line-height: 1.7;
  margin: 2.2mm 6mm 2.2mm 6mm; text-indent: 0; text-align: justify }}
p.d {{ text-indent: 0; margin: 1.2mm 6mm 1.2mm 0; font-family: 'David Libre', serif; font-weight: 500 }}
.fn {{ float: footnote; direction: rtl; font-size: 8.3pt; line-height: 1.45; text-indent: 0; text-align: right }}
::footnote-call {{ font-size: .65em; vertical-align: super; line-height: 0 }}
.pagedjs_footnote_area, .pagedjs_footnote_content {{ direction: rtl }}
{DESIGNS[design]}
</style></head><body>
<section class="chapter" data-title="פרשת בהעלותך">
<header class="ch-head"><div class="ch-kicker">ספר במדבר</div><h1>פרשת בהעלותך</h1><div class="ch-year">תשס״ט</div><div class="ch-rule"></div></header>
{chr(10).join(paras)}
</section>
<script src="file://{HERE}/vendor/paged.polyfill.js"></script>
</body></html>'''

os.makedirs(f'{BUILD}/out', exist_ok=True)
for s in SIZES:
    open(f'{BUILD}/out/sample-{s}.html', 'w', encoding='utf-8').write(page_html(s))
for d in 'abc':
    open(f'{BUILD}/out/design-{d}-17x24.html', 'w', encoding='utf-8').write(page_html('17x24', d))
open(f'{BUILD}/out/chapter.html', 'w', encoding='utf-8').write(page_html())   # הגודל והעיצוב שנבחרו
print('ok', len(body), 'blocks')
