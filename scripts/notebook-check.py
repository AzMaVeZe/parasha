#!/usr/bin/env python3
"""מעלה את טקסט הדפים ל-NotebookLM ומריץ עליו בדיקת הגהה.

למה: הטקסט שב-`scripts/sheet-text/` חולץ אוטומטית מקובצי ה-PDF. הוא עבר
בדיקות שיטתיות — כללי כתיב, הצלבה מול מנוע חילוץ שני, פסוקים שחוזרים בשני
דפים — אבל עין שקוראת את התוכן עצמו תופסת דברים אחרים: משפט שנקטע, ציטוט
שנשמט, שם פרשן שנחתך.

הסקריפט רץ **על המחשב שלך**, לא בסביבת Claude Code: הוא צריך את חשבון
הגוגל שלך, ו-NotebookLM חסום מהסביבה המרוחקת. אותו קובץ עובד ב-macOS
וב-Windows — הוא Python בלבד, בלי תלות במעטפת.

    הכנה חד-פעמית
    ──────────────
    pip install "notebooklm-py[cookies]"
    notebooklm login --browser-cookies chrome      # או msedge / chromium

    הרצה
    ────
    python scripts/notebook-check.py --list              # אילו מחברות יש
    python scripts/notebook-check.py -n <id>             # העלאה + בדיקה
    python scripts/notebook-check.py -n <id> --ask-only  # רק לשאול שוב

התשובות נשמרות גם כקובץ מקומי וגם כהערות בתוך המחברת — כך אפשר לקרוא
אותן מאפליקציית NotebookLM בנייד, בלי גישה למחשב.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import unicodedata
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_DIR = os.path.join(ROOT, 'scripts', 'sheet-text')
UPLOAD_DIR = os.path.join(ROOT, 'scripts', 'notebook-upload')
ANSWERS = os.path.join(ROOT, 'scripts', 'notebook-answers.md')

BOOKS = {
    'bereshit': 'בראשית', 'shmot': 'שמות', 'vayikra': 'ויקרא',
    'bamidbar': 'במדבר', 'devarim': 'דברים', 'chagim': 'חגים ומועדים',
}

# כל שאלה נשאלת בשיחה נפרדת (--new), כדי שתשובה אחת לא תגרור את הבאה.
QUESTIONS = [
    ('משפטים שבורים',
     'המקורות כאן הם טקסט שחולץ אוטומטית מדפי פרשת שבוע. עבור עליהם וחפש '
     'מקומות שבהם המשפט אינו קריא: מילים שנדבקו זו לזו, מילה שנשברה באמצע, '
     'אות שחסרה, או סדר מילים הפוך. צטט את המשפט המדויק וציין את שם הפרשה. '
     'אם בפרשה מסוימת לא מצאת דבר — אל תכתוב עליה כלום.'),
    ('ציטוטים מהמקורות',
     'אתר ציטוטים מנוקדים מהתנ"ך שמופיעים בטקסט. לכל אחד בדוק אם הנוסח '
     'והניקוד תואמים את הפסוק המקורי. ציין רק ציטוטים שיש בהם בעיה: שם '
     'הפרשה, הנוסח שמופיע, והנוסח הנכון.'),
    ('רצף הרעיון',
     'האם יש מקום שבו הטקסט קופץ באמצע רעיון, כאילו נשמטה פסקה? האם יש '
     'פסקה כפולה או חוזרת? ציין את שם הפרשה ואת המילים שלפני ואחרי הקפיצה.'),
    ('שמות ומונחים',
     'רשום שמות של פרשנים, ספרים ומקורות שמוזכרים בטקסט ונראים משובשים או '
     'חלקיים — ראשי תיבות שנחתכו, או שם שנכתב בשתי צורות שונות.'),
]

CLI = None


def run(args, capture=True):
    """מריץ את ה-CLI של notebooklm ומחזיר את הפלט."""
    cmd = ([CLI] if isinstance(CLI, str) else list(CLI)) + args
    try:
        p = subprocess.run(cmd, capture_output=capture, text=True,
                           encoding='utf-8', errors='replace')
    except FileNotFoundError:
        sys.exit('לא נמצא הכלי notebooklm. התקנה:\n'
                 '  pip install "notebooklm-py[cookies]"')
    if p.returncode != 0:
        err = ((p.stderr or '') + (p.stdout or '')).strip()
        if 'No module named' in err:
            sys.exit('החבילה אינה מותקנת. התקנה:\n'
                     '  pip install "notebooklm-py[cookies]"')
        if 'auth' in err.lower() or 'cookie' in err.lower():
            sys.exit(f'{err}\n\nהתחברות:\n'
                     '  notebooklm login --browser-cookies chrome')
        sys.exit(f'הפקודה נכשלה: notebooklm {" ".join(args[:3])}\n{err}')
    return (p.stdout or '').strip()


def find_cli():
    """הכלי מותקן כפקודה, אבל ב-Windows הוא לא תמיד נכנס ל-PATH."""
    exe = shutil.which('notebooklm')
    return exe if exe else [sys.executable, '-m', 'notebooklm']


def strip_nikud(s):
    return ''.join(c for c in s if not unicodedata.combining(c))


def load_sheets():
    if not os.path.isdir(TEXT_DIR):
        sys.exit(f'לא נמצאה תיקיית הטקסט: {TEXT_DIR}\n'
                 'הריצו קודם: python scripts/extract-sheet-text.py')
    sheets = []
    for fn in sorted(os.listdir(TEXT_DIR)):
        if not fn.endswith('.json'):
            continue
        stem = fn[:-5]
        book, _, name = stem.partition('-')
        with open(os.path.join(TEXT_DIR, fn), encoding='utf-8') as f:
            paragraphs = json.load(f)['paragraphs']
        sheets.append((book, (name or stem).replace('-', ' '), paragraphs))
    return sheets


def build_uploads(per_sheet):
    """כותב קובצי טקסט קריאים. מחזיר רשימת (נתיב, כותרת).

    ברירת המחדל היא קובץ לכל ספר — שישה מקורות. זה נכנס בנוחות במגבלת
    המקורות של כל חשבון, וגם עוזר: המודל רואה דפים סמוכים יחד.
    """
    sheets = load_sheets()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    for old in os.listdir(UPLOAD_DIR):
        os.remove(os.path.join(UPLOAD_DIR, old))

    out = []
    if per_sheet:
        for book, name, paras in sheets:
            title = f'{BOOKS.get(book, book)} — {name}'
            path = os.path.join(UPLOAD_DIR, f'{book}-{name}.txt')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f'{title}\n{"=" * 40}\n\n' + '\n\n'.join(paras) + '\n')
            out.append((path, title))
    else:
        for book, book_name in BOOKS.items():
            group = [s for s in sheets if s[0] == book]
            if not group:
                continue
            title = f'טקסט הדפים — {book_name}'
            path = os.path.join(UPLOAD_DIR, f'{book}.txt')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f'{title}\n{"=" * 40}\n')
                for _, name, paras in group:
                    f.write(f'\n\n### {name}\n\n' + '\n\n'.join(paras))
                f.write('\n')
            out.append((path, title))
    return out


def notebooks():
    try:
        data = json.loads(run(['list', '--json']) or '[]')
    except json.JSONDecodeError:
        sys.exit('לא הצלחתי לקרוא את רשימת המחברות. בדקו: notebooklm auth check')
    return data.get('notebooks', data) if isinstance(data, dict) else data


def pick_notebook(arg):
    if arg:
        return arg
    books = notebooks()
    if not books:
        sys.exit('אין מחברות בחשבון. צרו אחת:\n  notebooklm create "פרשת השבוע"')
    guess = [b for b in books if 'פרש' in strip_nikud(str(b.get('title', '')))]
    if len(guess) == 1:
        print(f'משתמש במחברת "{guess[0].get("title")}"')
        return guess[0].get('id')
    print('בחרו מחברת והריצו שוב עם ‎-n <id>:\n')
    for b in books:
        print(f'  {b.get("id")}  {b.get("title")}')
    sys.exit(0)


def existing_titles(nb):
    """כותרות המקורות שכבר במחברת, כדי לא להעלות אותו דבר פעמיים."""
    try:
        data = json.loads(run(['source', 'list', '-n', nb, '--json']) or '[]')
    except (json.JSONDecodeError, SystemExit):
        return set()
    rows = data.get('sources', data) if isinstance(data, dict) else data
    return {str(r.get('title', '')) for r in rows if isinstance(r, dict)}


def main():
    ap = argparse.ArgumentParser(description='בדיקת טקסט הדפים ב-NotebookLM')
    ap.add_argument('-n', '--notebook', help='מזהה המחברת')
    ap.add_argument('--list', action='store_true', help='הצגת המחברות שבחשבון')
    ap.add_argument('--per-sheet', action='store_true',
                    help='מקור לכל דף (55) במקום מקור לכל ספר (6)')
    ap.add_argument('--ask-only', action='store_true',
                    help='רק לשאול, בלי להעלות מקורות')
    ap.add_argument('--build-only', action='store_true',
                    help='רק להכין את הקבצים, בלי לגעת ב-NotebookLM')
    args = ap.parse_args()

    global CLI
    CLI = find_cli()

    if args.build_only:
        files = build_uploads(args.per_sheet)
        print(f'{len(files)} קבצים מוכנים ב-{UPLOAD_DIR}')
        return

    if args.list:
        for b in notebooks():
            print(f'{b.get("id")}  {b.get("title")}')
        return

    run(['auth', 'check', '--json'])        # ייכשל עם הסבר אם אין הזדהות
    nb = pick_notebook(args.notebook)

    if not args.ask_only:
        files = build_uploads(args.per_sheet)
        have = existing_titles(nb)
        for path, title in files:
            if title in have:
                print(f'כבר במחברת, מדלג: {title}')
                continue
            print(f'מעלה: {title}')
            run(['source', 'add', path, '--type', 'file',
                 '--title', title, '-n', nb, '--timeout', '180'])

    print('\nשואל את המחברת — כל שאלה לוקחת כדקה.\n')
    parts = [f'# בדיקת טקסט הדפים ב-NotebookLM\n\n{date.today():%d/%m/%Y}\n']
    for title, question in QUESTIONS:
        print(f'— {title}')
        answer = run(['ask', question, '-n', nb, '--new', '--yes',
                      '--save-as-note'])
        parts.append(f'\n## {title}\n\n**נשאל:** {question}\n\n{answer}\n')

    with open(ANSWERS, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))
    print(f'\nהתשובות נשמרו ב-{ANSWERS}')
    print('וגם כהערות בתוך המחברת — אפשר לקרוא אותן מהאפליקציה בנייד.')


if __name__ == '__main__':
    main()
