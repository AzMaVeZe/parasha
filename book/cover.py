"""כריכת "יש קמח" לבוקפוד: עמוד אחד — חזית, שדרה וגב — כ-PDF.

  python3 book/cover.py [--size b5|17x24|a5] [--pages N] [--paper 0.1] [--no-bleed]
  node book/render-cover.js        # ← book/build/out/cover.pdf

לפי הנחיות בוקפוד:
- עמוד אחד, ומשמאל לימין: חזית, שדרה, גב. כך נראית כריכה של ספר שנפתח מימין
  ("כיוון קריאה: ימין לשמאל"), כשפורשים אותה ומסתכלים מבחוץ.
- רוחב השדרה = מספר העמודים × עובי הדף. נייר עץ לבן 80 גרם: 0.1 מ"מ לעמוד, לפי
  הדוגמה שלהם (200 עמודים ← 20 מ"מ). מספר העמודים מעוגל למעלה לכפולה של 4. את הרוחב
  המדויק בודקים בכלי התצוגה המקדימה בעת ההעלאה, ומעדכנים כאן אם צריך.
- גלישה (bleed) של 3.2 מ"מ בדיוק מכל צד — ואז מסמנים בטופס שהקובץ כולל גלישה.
- בלי סימני חיתוך. הטקסט נשאר 8 מ"מ לפחות בתוך קו החיתוך, ובשדרה 2 מ"מ מכל צד.
- מקום פנוי לברקוד בגב (בוקפוד: 1.5 × 4 ס"מ).
"""
import html
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
SIZES = {'b5': (165, 235), '17x24': (170, 240), 'a5': (148, 210)}

TITLE = 'יש קמח'
SUB = 'שיחת חולין על פרשת השבוע'
AUTHOR = "אריאל ז׳יטניצקי"
# הצבעים של האתר ושל כרטיסי הפודקאסט (tokens/colors.css)
NAVY, CREAM, GOLD, INK = '#14294D', '#F7F2E7', '#B8860B', '#26241E'


def arg(name, default):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def book_pages():
    pdf = os.path.join(BUILD, 'out', 'book-c.pdf')   # הספר ב-B5 (build_book.py, ברירת המחדל)
    if not os.path.exists(pdf):
        return 300
    out = subprocess.check_output(['pdfinfo', pdf], text=True)
    return int([l for l in out.splitlines() if l.startswith('Pages:')][0].split()[1])


def main():
    w, h = SIZES[arg('--size', 'b5')]
    pages = int(arg('--pages', book_pages()))
    pages += (-pages) % 4
    paper = float(arg('--paper', '0.1'))
    bleed = 0 if '--no-bleed' in sys.argv else 3.2
    spine = round(pages * paper, 1)
    W, H = 2 * w + spine + 2 * bleed, h + 2 * bleed
    e = lambda s: html.escape(s)
    page = f'''<!doctype html><html lang="he"><head><meta charset="utf-8">
<link rel="stylesheet" href="file://{BUILD}/fonts/book-fonts.css">
<style>
/* הדף גדול במילימטר, ו-crop_cover.py חותך למידה המדויקת — Chromium מעגל גודל דף לנקודות שלמות */
@page {{ size: {W + 1}mm {H + 1}mm; margin: 0 }}
html, body {{ margin: 0; width: {W + 1}mm; height: {H + 1}mm }}
body {{ position: relative; background: {CREAM}; font-family: 'Assistant'; -webkit-print-color-adjust: exact; print-color-adjust: exact }}
.panel {{ position: absolute; top: 0; height: {H}mm }}
/* משמאל לימין: חזית | שדרה | גב. כל לוח כולל את הגלישה שבצד החיצוני שלו. */
.front {{ left: 0; width: {w + bleed}mm }}
.spine {{ left: {w + bleed}mm; width: {spine}mm; background: {NAVY} }}
.back  {{ left: {w + bleed + spine}mm; width: {w + bleed}mm }}
.navy  {{ position: absolute; left: 0; right: 0; bottom: 0; height: {bleed + h * 0.34}mm; background: {NAVY} }}
.front .inner {{ position: absolute; left: {bleed + 12}mm; right: 12mm; top: {bleed + 14}mm; bottom: {bleed + 12}mm; direction: rtl }}
.back .inner  {{ position: absolute; left: 12mm; right: {bleed + 12}mm; top: {bleed + 16}mm; bottom: {bleed + 12}mm; direction: rtl }}
.kicker {{ font: 700 11pt 'Assistant'; color: {NAVY}; letter-spacing: .04em }}
.pill {{ position: absolute; left: 0; top: -1mm; border: .6mm solid {GOLD}; color: {GOLD}; border-radius: 6mm; padding: 1mm 4mm; font: 700 9.5pt 'Assistant' }}
h1 {{ font-family: 'Frank Ruhl Libre'; font-weight: 700; color: {NAVY}; font-size: 54pt; line-height: 1; margin: {h * 0.17}mm 0 0; text-align: right }}
.bar {{ margin-top: 7mm; border-right: 1.2mm solid {GOLD}; padding-right: 4mm; font: 400 14pt 'Frank Ruhl Libre'; color: {INK} }}
.author {{ position: absolute; right: 0; bottom: 6mm; color: {CREAM}; font: 700 18pt 'Assistant' }}
.site {{ position: absolute; right: 0; bottom: 0; color: {GOLD}; font: 700 9.5pt 'Assistant'; direction: ltr }}
.spine .text {{ position: absolute; left: 50%; top: 50%; width: {H - 2 * bleed - 36}mm; height: {spine}mm;
  transform: translate(-50%, -50%) rotate(-90deg); display: flex; align-items: center; justify-content: space-between;
  color: {CREAM}; direction: rtl }}
/* השדרה נקראת מלמעלה למטה, וראשי האותיות פונים לחזית: כשהספר מונח על גבו והחזית למעלה, השם קריא */
.spine .t {{ font: 700 {min(20, max(7, spine * 0.62))}pt 'Frank Ruhl Libre' }}
.spine .a {{ font: 700 {min(11, max(6, spine * 0.36))}pt 'Assistant'; color: {GOLD} }}
.blurb {{ font: 400 11.5pt 'David Libre'; line-height: 1.6; color: {INK}; text-align: justify; max-width: {w - 30}mm }}
.blurb.ph {{ color: #8a8577 }}
.barcode {{ position: absolute; left: 0; bottom: 0; width: 45mm; height: 22mm; background: #fff; border: .3mm dashed #999;
  display: flex; align-items: center; justify-content: center; font: 7pt 'Assistant'; color: #999 }}
</style></head><body>
<section class="panel front"><div class="navy"></div><div class="inner">
  <div class="kicker"></div><div class="pill">תורה וחגים</div>
  <h1>{e(TITLE)}</h1>
  <div class="bar">{e(SUB)}</div>
  <div class="author">{e(AUTHOR)}</div>
</div></section>
<section class="panel spine"><div class="text"><span class="t">{e(TITLE)}</span><span class="a">{e(AUTHOR)}</span></div></section>
<section class="panel back"><div class="navy"></div><div class="inner">
  <p class="blurb ph">[טקסט הגב: כמה שורות על הספר ועל הדפים, ומשפט על המחבר — יכתוב אריאל]</p>
  <div class="site">parasha.azma.app</div>
  <div class="barcode">מקום לברקוד</div>
</div></section>
</body></html>'''
    os.makedirs(os.path.join(BUILD, 'out'), exist_ok=True)
    open(os.path.join(BUILD, 'out', 'cover.html'), 'w', encoding='utf-8').write(page)
    open(os.path.join(BUILD, 'out', 'cover.size'), 'w').write(f'{W} {H}')
    print(f'cover: {w}×{h} מ"מ, {pages} עמודים, שדרה {spine} מ"מ, גלישה {bleed} → {W:.1f}×{H:.1f} מ"מ')


if __name__ == '__main__':
    main()
