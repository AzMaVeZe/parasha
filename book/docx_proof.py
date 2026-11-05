"""גרסת ההגהה של הספר כקובץ Word, לעריכה של אריאל.

  python3 book/docx_proof.py        # ← book/build/out/אללה-פרשה-הגהה.docx

אותו טקסט כמו book-c-proof (build_book.edit), ובשני סוגי סימון שמובנים ב-Word:
- שינוי שעשיתי בעריכה (EDITS) ← "מעקב שינויים": אפשר לקבל או לדחות כל אחד (סקירה ← קבל/דחה).
- מקום לבדיקה (CHECKS) ← הדגשה צהובה, ובהערה בשוליים — הסיבה.
כללי הבית (גרשיים, מקף, כתיב) כבר מוחלים, בלי סימון.

עברית ב-Word (ראו hebrew-document-generator): כל פסקה עם <w:bidi/>, הטקסט מפוצל לריצות לפי כתב,
גופן ו-szCs לכל ריצה, ו-<w:rtl/> רק על ריצות עבריות בפסקה בלי אותיות לטיניות.
"""
import datetime
import os
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_TABLE_DIRECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_book as B   # noqa: E402
import house             # noqa: E402

FONT, VERSE_FONT = 'David', 'FrankRuehl'
AUTHOR = 'Claude (עריכה)'
NOW = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
HEB = re.compile(r'[֐-׿יִ-ﭏ]')
_rev = [0]


# ---------------------------------------------------------------- טקסט עם סימונים ← קטעים
def segments(text):
    """[(טקסט, סיבת-בדיקה או None, 'ins' / 'del' / None)] לפי הסימונים של house."""
    out, stack, buf = [], [], ''

    def ctx():
        chk = next((house.NOTES[i] for k, i in reversed(stack) if k == 'chk'), None)
        ins = 'ins' if any(k == 'chg' for k, _ in stack) else None
        return chk, ins

    def flush():
        nonlocal buf
        if buf:
            out.append((buf,) + ctx())
            buf = ''
    i = 0
    while i < len(text):
        c = text[i]
        if c == house.MO:
            flush()
            j = text.index(house.MS, i)
            m = re.fullmatch(r'([a-z]+)(\d+)', text[i + 1:j])
            kind, idx = m.group(1), int(m.group(2))
            if kind == 'chg' and house.NOTES[idx].strip():
                out.append((house.NOTES[idx], ctx()[0], 'del'))
            stack.append((kind, idx))
            i = j + 1
            continue
        if c == house.MC:
            flush()
            stack.pop()
            i += 1
            continue
        buf += c
        i += 1
    flush()
    return [(t.replace('⁦', '').replace('⁩', ''), chk, rev) for t, chk, rev in out]


def _strong(ch):
    if HEB.match(ch):
        return True
    if ch.isascii() and ch.isalnum():
        return False
    return None


def split_script(text, default_rtl=True):
    segs, buf, kind_now = [], '', None
    for ch in text:
        s = _strong(ch)
        kind = s if s is not None else (kind_now if kind_now is not None else default_rtl)
        if kind_now is None or kind == kind_now:
            buf, kind_now = buf + ch, kind
        else:
            segs.append((buf, kind_now))
            buf, kind_now = ch, kind
    if buf:
        segs.append((buf, kind_now))
    # רווח בסוף ריצה LTR לפני ריצה עברית עובר לריצה העברית (Word חותך אותו)
    for k in range(len(segs) - 1):
        if segs[k][1] is False and segs[k + 1][1] is True and segs[k][0].endswith(' '):
            st = segs[k][0].rstrip(' ')
            segs[k + 1] = (segs[k][0][len(st):] + segs[k + 1][0], True)
            segs[k] = (st, False)
    return [s for s in segs if s[0]]


# ---------------------------------------------------------------- Word
def rpr(r, font, size, bold=False, rtl=False, highlight=False):
    rPr = r.find(qn('w:rPr'))
    if rPr is None:
        rPr = r.makeelement(qn('w:rPr'), {})
        r.insert(0, rPr)
    rPr.append(rPr.makeelement(qn('w:rFonts'), {qn('w:ascii'): font, qn('w:hAnsi'): font, qn('w:cs'): font}))
    if bold:
        rPr.append(rPr.makeelement(qn('w:b'), {}))
        rPr.append(rPr.makeelement(qn('w:bCs'), {}))
    if highlight:
        rPr.append(rPr.makeelement(qn('w:highlight'), {qn('w:val'): 'yellow'}))
    rPr.append(rPr.makeelement(qn('w:sz'), {qn('w:val'): str(int(size * 2))}))
    rPr.append(rPr.makeelement(qn('w:szCs'), {qn('w:val'): str(int(size * 2))}))
    if rtl:
        rPr.append(rPr.makeelement(qn('w:rtl'), {}))


def rtl_para(p, align=None):
    pPr = p._p.get_or_add_pPr()
    pPr.append(pPr.makeelement(qn('w:bidi'), {}))
    if align is not None:
        p.alignment = align


def write(doc, p, text, font=FONT, size=12, bold=False):
    """פסקה עם סימונים: ריצות לפי כתב, מעקב שינויים, והדגשה + הערה למקומות לבדיקה."""
    has_latin = bool(re.search('[A-Za-z]', house.plain(text)))
    pending = {}          # סיבה ← ריצות (להערה אחת על כל קטע לבדיקה)
    for seg, chk, rev in segments(text):
        for piece, is_heb in split_script(seg):
            rtl = bool(is_heb) and not has_latin
            if rev in ('ins', 'del'):
                _rev[0] += 1
                wrap = p._p.makeelement(qn('w:' + rev), {qn('w:id'): str(_rev[0]), qn('w:author'): AUTHOR,
                                                       qn('w:date'): NOW})
                r = wrap.makeelement(qn('w:r'), {})
                rpr(r, font, size, bold, rtl, highlight=chk is not None)
                t = r.makeelement(qn('w:delText' if rev == 'del' else 'w:t'), {})
                t.text = piece
                t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                r.append(t)
                wrap.append(r)
                p._p.append(wrap)
            else:
                run = p.add_run(piece)
                rpr(run._r, font, size, bold, rtl, highlight=chk is not None)
                if chk is not None:
                    pending.setdefault(chk, []).append(run)
    for why, runs in pending.items():
        doc.add_comment(runs, text=why, author=AUTHOR, initials='C')


def para(doc, text, kind='', size=12):
    p = doc.add_paragraph()
    rtl_para(p, WD_ALIGN_PARAGRAPH.JUSTIFY)
    pf = p.paragraph_format
    pf.space_after = Pt(4)
    pf.line_spacing = 1.3
    if kind == 'q':
        pPr = p._p.get_or_add_pPr()
        ind = pPr.find(qn('w:ind'))
        if ind is None:
            ind = pPr.makeelement(qn('w:ind'), {})
            pPr.append(ind)
        ind.set(qn('w:start'), str(int(Cm(0.8).twips)))          # בצד ימין (התחלת שורה בעברית)
        write(doc, p, text, VERSE_FONT, size)
    elif kind == 'li':
        pPr = p._p.get_or_add_pPr()
        ind = pPr.makeelement(qn('w:ind'), {qn('w:start'): str(int(Cm(0.5).twips)),
                                            qn('w:hanging'): str(int(Cm(0.5).twips))})
        pPr.append(ind)
        write(doc, p, text, FONT, size)
    else:
        write(doc, p, text, FONT, size)
    return p


def heading(doc, text, level, page_break=False):
    p = doc.add_heading(level=level)
    rtl_para(p, WD_ALIGN_PARAGRAPH.RIGHT)
    p.paragraph_format.page_break_before = page_break
    run = p.add_run(text)
    rpr(run._r, FONT, {0: 26, 1: 20, 2: 16}[level], bold=True, rtl=True)
    return p


def shoftim_table(doc):
    def verses(book, ch, a, b):
        text = B.sheet_fixes._book(book)[ch - 1]
        out = []
        for n in range(a, b + 1):
            v = re.sub(r'\{[פס]\}|׃', ' ', text[n - 1]).strip()
            v = house.shem(v)
            v = re.sub(r'(?<![א-ת])(א[ְ-ּ]*)(ל[֑-ׇ]*ה[֑-ׇ]*[יו])', r'\1-\2', v)
            out.append(B.hebnum(n) + ' ' + v)
        return ' '.join(out)
    t = doc.add_table(rows=2, cols=2)
    t.style = 'Table Grid'
    t.table_direction = WD_TABLE_DIRECTION.RTL
    t.alignment = WD_TABLE_ALIGNMENT.RIGHT
    cells = [('במדבר לה (מסעי)', verses('Numbers', 35, 9, 34)), ('דברים יט (שופטים)', verses('Deuteronomy', 19, 2, 10))]
    for j, (head, body) in enumerate(cells):
        for i, (txt, bold, font, size) in enumerate(((head, True, FONT, 11), (body, False, VERSE_FONT, 10.5))):
            p = t.rows[i].cells[j].paragraphs[0]
            rtl_para(p)
            write(doc, p, txt, font, size, bold)
    p = doc.add_paragraph()
    rtl_para(p)
    write(doc, p, house.mark('chk', 'הטבלה נבנתה מחדש מנוסח מנוקד תקני.',
                             'ההדגשות שבדף לא הועברו — לבדוק מול הדף'), FONT, 10)


def main():
    house.NOTES.clear()
    parts = B.edit(B.chapters())
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(16.5), Cm(23.5)
    sec.top_margin, sec.bottom_margin = Cm(1.9), Cm(2.1)
    sec.left_margin = sec.right_margin = Cm(1.8)
    sec._sectPr.append(sec._sectPr.makeelement(qn('w:bidi'), {}))
    st = doc.styles['Normal']
    st.font.name, st.font.size = FONT, Pt(12)
    st.element.rPr.rFonts.set(qn('w:cs'), FONT)

    heading(doc, B.TITLE, 0)
    para(doc, 'גרסת הגהה לעריכה. השינויים שעשיתי בעריכה מופיעים כ"מעקב שינויים" — אפשר לקבל או לדחות כל אחד '
              '(סקירה ← קבל / דחה). מקומות שדורשים בדיקה שלך מול הדף מודגשים בצהוב, והסיבה בהערה בשוליים. '
              'כללי הבית (גרשיים, מקף עברי, כתיב) כבר הוחלו. כל מה שתשנה כאן ייכנס לספר.', size=11)
    para(doc, '[ההקדמה — תיכתב בהמשך]')
    for part in parts:
        heading(doc, part['name'], 1, page_break=True)
        for ch in part['chapters']:
            heading(doc, ch['title'], 2, page_break=True)
            for sub in ch['subs']:
                para(doc, sub, size=13)
            if ch['year']:
                para(doc, ch['year'], size=11)
            for p in ch['paras']:
                if p == '\x00TABLE':
                    shoftim_table(doc)
                    continue
                pl = house.plain(p)
                kind = 'q' if B.is_quote(pl) else 'li' if pl.startswith(('•', '·')) else ''
                para(doc, p, kind)
            if ch['notes']:
                h = doc.add_paragraph()
                rtl_para(h)
                run = h.add_run('הערות')
                rpr(run._r, FONT, 11, bold=True, rtl=True)
                for n in ch['notes']:
                    num = str(n.get('n') or '')
                    para(doc, (num + '. ' if num else '') + n['text'], size=10)
    heading(doc, 'על המחבר', 1, page_break=True)
    para(doc, '[כמה שורות על אריאל — יכתוב אריאל]')
    out = os.path.join(B.BUILD, 'out', 'אללה-פרשה-הגהה.docx')
    doc.save(out)
    print(out)


if __name__ == '__main__':
    main()
