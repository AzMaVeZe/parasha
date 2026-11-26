"""גרסת ההגהה של הספר כקובץ Word, לעריכה של אריאל.

  python3 book/docx_proof.py        # ← book/build/out/יש-קמח-הגהה.docx

אותו טקסט כמו book-c-proof (build_book.edit), ובשני סוגי סימון שמובנים ב-Word:
- שינוי שעשיתי בעריכה (EDITS) ← "מעקב שינויים": אפשר לקבל או לדחות כל אחד (סקירה ← קבל/דחה).
- מקום לבדיקה (CHECKS) ← מסגרת מקווקוות ורקע אפור בהיר (נראים גם בשחור-לבן), ובהערה בשוליים — הסיבה.
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
    rPr.append(rPr.makeelement(qn('w:sz'), {qn('w:val'): str(int(size * 2))}))
    rPr.append(rPr.makeelement(qn('w:szCs'), {qn('w:val'): str(int(size * 2))}))
    if highlight:   # הסדר לפי הסכֵמה של Word: sz, szCs, highlight, bdr, rtl
        # מודפס גם בשחור-לבן: רקע אפור בהיר ומסגרת מקווקוות סביב הטקסט (כמו ב-PDF)
        rPr.append(rPr.makeelement(qn('w:highlight'), {qn('w:val'): 'lightGray'}))
        rPr.append(rPr.makeelement(qn('w:bdr'), {qn('w:val'): 'dashed', qn('w:sz'): '6', qn('w:space'): '0', qn('w:color'): '000000'}))
    if rtl:
        rPr.append(rPr.makeelement(qn('w:rtl'), {}))


W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


class Footnotes:
    """הערות שוליים אמיתיות של Word (footnotes.xml): ההערה יושבת במקום שבו המספר שלה הופיע בדף.
    Word ממספר אותן ברצף לאורך הקובץ (סימן מותאם עם המספר המקורי לא נתמך ב-LibreOffice, ולכן לא);
    הטקסט של כל הערה – כמו בספר, כולל הסימונים."""

    def __init__(self, doc):
        from lxml import etree
        self.doc, self.etree = doc, etree
        self.root = etree.fromstring(
            f'<w:footnotes xmlns:w="{W_NS}">'
            '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>'
            '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
            '</w:footnotes>')
        self.next = 1
        self.texts = {}                           # מספר ההערה בפרק ← הטקסט (מתעדכן לכל פרק)

    def reference(self, p_el, n, size):
        """ריצת הפניה בפסקה, והערה חדשה בקובץ ההערות. מחזיר False אם אין טקסט להערה."""
        text = self.texts.get(n)
        if text is None:
            return False
        fid = str(self.next)
        self.next += 1
        r = p_el.makeelement(qn('w:r'), {})
        rPr = r.makeelement(qn('w:rPr'), {})
        rPr.append(rPr.makeelement(qn('w:vertAlign'), {qn('w:val'): 'superscript'}))
        r.append(rPr)
        r.append(r.makeelement(qn('w:footnoteReference'), {qn('w:id'): fid}))
        p_el.append(r)
        fn = self.etree.SubElement(self.root, qn('w:footnote'), {qn('w:id'): fid})
        fp = self.etree.SubElement(fn, qn('w:p'))
        pPr = self.etree.SubElement(fp, qn('w:pPr'))
        self.etree.SubElement(pPr, qn('w:bidi'))
        self.etree.SubElement(pPr, qn('w:jc'), {qn('w:val'): 'both'})
        ref = self.etree.SubElement(fp, qn('w:r'))
        rp = self.etree.SubElement(ref, qn('w:rPr'))
        self.etree.SubElement(rp, qn('w:vertAlign'), {qn('w:val'): 'superscript'})
        self.etree.SubElement(ref, qn('w:footnoteRef'))
        sp = self.etree.SubElement(fp, qn('w:r'))
        t = self.etree.SubElement(sp, qn('w:t'))
        t.text = ' '
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        write_runs(fp, text, FONT, 10)
        return True

    def save(self):
        from docx.opc.constants import RELATIONSHIP_TYPE as RT
        from docx.opc.packuri import PackURI
        from docx.opc.part import Part
        part = Part(PackURI('/word/footnotes.xml'),
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml',
                    self.etree.tostring(self.root, xml_declaration=True, encoding='UTF-8', standalone=True),
                    self.doc.part.package)
        self.doc.part.relate_to(part, RT.FOOTNOTES)


FOOT = [None]                                     # Footnotes של הקובץ הנוכחי


def write_runs(p_el, text, font, size):
    """ריצות טקסט (עם מעקב שינויים) לתוך אלמנט פסקה – להערות השוליים. מקום לבדיקה: הדגשה והסיבה בסוגריים."""
    has_latin = bool(re.search('[A-Za-z]', house.plain(text)))
    for seg, chk, rev in segments(text):
        for piece, is_heb in split_script(seg):
            rtl = bool(is_heb) and not has_latin
            r = p_el.makeelement(qn('w:r'), {})
            rpr(r, font, size, False, rtl, highlight=chk is not None)
            t = r.makeelement(qn('w:delText' if rev == 'del' else 'w:t'), {})
            t.text = piece
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            r.append(t)
            if rev in ('ins', 'del'):
                _rev[0] += 1
                wrap = p_el.makeelement(qn('w:' + rev), {qn('w:id'): str(_rev[0]), qn('w:author'): AUTHOR, qn('w:date'): NOW})
                wrap.append(r)
                p_el.append(wrap)
            else:
                p_el.append(r)
        if chk is not None:
            r = p_el.makeelement(qn('w:r'), {})
            rpr(r, font, size - 1, True, True)
            t = r.makeelement(qn('w:t'), {})
            t.text = f' [{chk}]'
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            r.append(t)
            p_el.append(r)


def rtl_para(p, align=None):
    pPr = p._p.get_or_add_pPr()
    pPr.append(pPr.makeelement(qn('w:bidi'), {}))
    if align is not None:
        p.alignment = align


def write(doc, p, text, font=FONT, size=12, bold=False):
    """פסקה עם סימונים: ריצות לפי כתב, מעקב שינויים, הדגשה + הערה למקומות לבדיקה, והערות שוליים."""
    has_latin = bool(re.search('[A-Za-z]', house.plain(text)))
    pending = {}          # סיבה ← ריצות (להערה אחת על כל קטע לבדיקה)
    for seg0, chk, rev in segments(text):
        bits = re.split(house.FN + '(.*?)' + house.FE, seg0)
        for k, seg in enumerate(bits):
            if k % 2:                              # מספר הערה ← הערת שוליים של Word במקום הזה
                n = int(seg) if seg.isdigit() else seg
                if not (FOOT[0] and FOOT[0].reference(p._p, n, size)):
                    run = p.add_run(seg)
                    rpr(run._r, font, size, bold, False)
                    run.font.superscript = True
                continue
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

    FOOT[0] = Footnotes(doc)
    heading(doc, B.TITLE, 0)
    para(doc, B.SUBTITLE, size=14)
    para(doc, 'גרסת הגהה לעריכה. השינויים שעשיתי בעריכה מופיעים כ"מעקב שינויים" — אפשר לקבל או לדחות כל אחד '
              '(סקירה ← קבל / דחה). מקומות שדורשים בדיקה שלך מול הדף מוקפים במסגרת מקווקוות על רקע אפור, והסיבה בהערה בשוליים. '
              'כללי הבית (גרשיים, מקף עברי, כתיב) כבר הוחלו. כל מה שתשנה כאן ייכנס לספר.', size=11)
    heading(doc, 'על שם הספר', 1)
    para(doc, B.NAME_NOTE)
    heading(doc, 'הקדמה', 1)
    para(doc, '[ההקדמה — תיכתב בהמשך]')
    para(doc, house.mark('chg', B.INTRO_YEARS, ''))
    for part in parts:
        heading(doc, part['name'], 1, page_break=True)
        for ch in part['chapters']:
            heading(doc, ch['title'], 2, page_break=True)
            FOOT[0].texts = {n['n']: n['text'] for n in ch['notes'] if n.get('placed')}
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
            rest = [n for n in ch['notes'] if not n.get('placed')]
            if rest:                               # הערות שלא נמצא להן מקום בטקסט – ברשימה בסוף הפרק
                h = doc.add_paragraph()
                rtl_para(h)
                run = h.add_run('הערות (לא נמצא מקומן בטקסט)')
                rpr(run._r, FONT, 11, bold=True, rtl=True)
                for n in rest:
                    num = str(n.get('n') or '')
                    para(doc, (num + '. ' if num else '') + n['text'], size=10)
    heading(doc, 'על המחבר', 1, page_break=True)
    para(doc, B.about_text())
    FOOT[0].save()
    out = os.path.join(B.BUILD, 'out', 'יש-קמח-הגהה.docx')
    doc.save(out)
    print(out)


if __name__ == '__main__':
    main()
