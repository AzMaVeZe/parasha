"""קורא קובץ הגהה (Word) שאריאל החזיר, ושומר את השינויים שלו כזוגות: הנוסח בספר ← הנוסח של אריאל.

  python3 book/import_proof.py <קובץ.docx> <שם>      # ← book/author_edits/<שם>.json

בכל פסקה שיש בה שינוי של אריאל (מעקב שינויים):
- base  — הנוסח שהספר מפיק היום (רשימת פסקאות): השינויים שלי (Claude) מתקבלים, של אריאל נדחים.
- final — הנוסח של אריאל: השינויים של שנינו מתקבלים. (שינוי שלי שאריאל לא דחה – נחשב מקובל.)
פיצול ואיחוד של פסקאות (סימן פסקה במעקב שינויים) נשמרים: base ו-final יכולים להיות באורך שונה.
build_book.author_edits מחליף רצף פסקאות שזהה ל-base ברצף final. ההערות של אריאל בשוליים
נשמרות בנפרד (comments), כדי לענות עליהן – הן לא משנות את הטקסט.
"""
import json
import os
import re
import sys
import zipfile

from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
HERE = os.path.dirname(os.path.abspath(__file__))


def is_claude(author):
    return (author or '').startswith('Claude')


def paragraphs(docx):
    """לכל פסקה ב-Word: (base, final, אריאל שינה?, הערות של אריאל, מצב סימן הפסקה).
    מצב הסימן: None, 'ins' (אריאל פיצל כאן פסקה) או 'del' (אריאל איחד אותה עם הבאה)."""
    z = zipfile.ZipFile(docx)
    doc = etree.fromstring(z.read('word/document.xml'))
    com = etree.fromstring(z.read('word/comments.xml')) if 'word/comments.xml' in z.namelist() else None
    comments = {}
    if com is not None:
        for c in com.iter(W + 'comment'):
            comments[c.get(W + 'id')] = (is_claude(c.get(W + 'author')),
                                         ''.join(t.text or '' for t in c.iter(W + 't')))
    for p in doc.find(W + 'body').iter(W + 'p'):
        base, final, ariel, cids = [], [], False, []
        for el in p.iter():
            if el.tag in (W + 't', W + 'delText'):
                kind, mine = None, True
                a = el.getparent()
                while a is not None and a is not p:
                    if a.tag in (W + 'ins', W + 'del'):
                        kind, mine = a.tag[len(W):], is_claude(a.get(W + 'author'))
                        break
                    a = a.getparent()
                t = el.text or ''
                if kind is None:
                    base.append(t); final.append(t)
                elif mine:                       # שינוי שלי: מתקבל בשני הנוסחים
                    if kind == 'ins':
                        base.append(t); final.append(t)
                else:                            # שינוי של אריאל
                    ariel = True
                    (final if kind == 'ins' else base).append(t)
            elif el.tag == W + 'commentRangeStart':
                cids.append(el.get(W + 'id'))
        mark = None
        for k in ('ins', 'del'):
            m = p.find(f'{W}pPr/{W}rPr/{W}{k}')
            if m is not None and not is_claude(m.get(W + 'author')):
                mark, ariel = k, True
        notes = [(c, comments[c][1]) for c in cids if c in comments and not comments[c][0]]
        yield ''.join(base), ''.join(final), ariel, notes, mark


def norm(t):
    return re.sub(r'\s+', ' ', t).strip()


def units(paras):
    """מקבץ פסקאות שסימני הפסקה ביניהן השתנו (פיצול/איחוד), ומחזיר לכל מקבץ:
    (פסקאות לפני, פסקאות אחרי, אריאל שינה?). פסקה רגילה היא מקבץ של אחת."""
    group = []
    for item in paras:
        group.append(item)
        if item[4] is None:                      # סימן פסקה רגיל – סוף מקבץ
            yield group
            group = []
    if group:
        yield group


def split(group, which):
    out, cur = [], ''
    for base, final, ariel, notes, mark in group:
        cur += base if which == 'base' else final
        # ב-base קיים סימן שאריאל מחק; ב-final קיים סימן שאריאל הוסיף
        if mark is None or (which == 'base' and mark == 'del') or (which == 'final' and mark == 'ins'):
            out.append(norm(cur)); cur = ''
    if cur:
        out.append(norm(cur))
    return [x for x in out if x]


def main():
    docx, name = sys.argv[1], sys.argv[2]
    edits, notes = [], []
    for group in units(paragraphs(docx)):
        b, f = split(group, 'base'), split(group, 'final')
        if any(g[2] for g in group) and b != f and b:
            edits.append({'base': b, 'final': f})
        for g in group:
            for cid, text in g[3]:
                notes.append({'paragraph': norm(g[0])[:120], 'comment': text})
    os.makedirs(os.path.join(HERE, 'author_edits'), exist_ok=True)
    out = os.path.join(HERE, 'author_edits', name + '.json')
    json.dump({'edits': edits, 'comments': notes}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{out}: {len(edits)} שינויים, {len(notes)} הערות של אריאל')


if __name__ == '__main__':
    main()
