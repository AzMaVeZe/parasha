#!/usr/bin/env python3
"""מכין פרק פודקאסט לפרשה: סקירה קולית מ-NotebookLM, כרטיס, ותיאור לספוטיפיי.

הדרך שבה נוצרו הפרקים עד היום: במחברת "פרשת השבוע", שבה נמצאים כל הדפים,
מסמנים רק את הדף של השבוע ומבקשים סקירה קולית — שני מנחים שמנתחים ודנים
ברעיונות שבדף. הסקריפט עושה את אותו הדבר, ומוסיף את מה שצריך להעלאה:

    scripts/episodes/<דף>/
        <דף>.m4a        הסקירה הקולית
        cover.png       כרטיס הפרק (מ-assets/covers, 3000×3000)
        description.txt כותרת ותיאור, עם הקישור לעמוד הדף באתר

את הפרק מעלים ל-Spotify for Creators ביד, ושולחים לClaude את הקישור — הוא
נכנס לאתר (js/data.js). **כדאי לשמוע כל פרק לפני שהוא עולה:** הוא יוצא בשמך,
וסקירה אוטומטית עלולה לטעות בקריאה או בפרשנות.

הסקריפט רץ **על המחשב שלך** (macOS / Windows): הוא צריך את חשבון הגוגל שלך,
ו-NotebookLM חסום מהסביבה המרוחקת. ההתקנה זהה לזו של notebook-check.py:

    pip install "notebooklm-py[cookies]"
    notebooklm login --browser-cookies chrome

    python scripts/make-episode.py --sources            # אילו דפים יש במחברת
    python scripts/make-episode.py "לך לך"              # פרק אחד
    python scripts/make-episode.py "לך לך" וירא "חיי שרה"
    python scripts/make-episode.py --from "לך לך" --count 3

ל-NotebookLM יש מכסה יומית של סקירות קוליות. כשהיא נגמרת הסקריפט עוצר,
ומה שכבר הוכן נשאר; למחרת מריצים שוב, ופרקים שכבר הורדו מדולגים.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'scripts', 'episodes')
SITE = 'https://parasha.azma.app'

# הבקשה ל-NotebookLM. אפשר להחליף ב---prompt.
PROMPT = ('שני מנחים מנתחים ודנים ברעיונות שמופיעים בדף של {title} — רק בדף הזה. '
          'עקבו אחרי מהלך הטיעון של הכותב, הביאו את הפסוקים והמקורות שהוא מצטט, '
          'ואל תוסיפו פרשנות שאינה בדף. הדף נכתב על ידי אריאל ז\'יטניצקי.')

CLI = None


def run(args, check=True):
    """מריץ את notebooklm ומחזיר (קוד יציאה, פלט)."""
    cmd = ([CLI] if isinstance(CLI, str) else list(CLI)) + args
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
    except FileNotFoundError:
        sys.exit('לא נמצא הכלי notebooklm. התקנה:\n  pip install "notebooklm-py[cookies]"')
    out = (p.stdout or '').strip()
    if check and p.returncode != 0:
        err = ((p.stderr or '') + out).strip()
        if 'auth' in err.lower() or 'cookie' in err.lower():
            sys.exit(f'{err}\n\nהתחברות:\n  notebooklm login --browser-cookies chrome')
        sys.exit(f'הפקודה נכשלה: notebooklm {" ".join(args[:3])}\n{err}')
    return p.returncode, out or (p.stderr or '').strip()


def find_cli():
    exe = shutil.which('notebooklm')
    return exe if exe else [sys.executable, '-m', 'notebooklm']


def as_rows(text, key):
    try:
        data = json.loads(text or '[]')
    except json.JSONDecodeError:
        return []
    rows = data.get(key, data) if isinstance(data, dict) else data
    return [r for r in rows if isinstance(r, dict)]


def norm(s):
    """לחיפוש: בלי ניקוד, גרשיים, סיומת וסימני הפרדה."""
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c))
    s = re.sub(r'\.(pdf|txt|docx?)$', '', s, flags=re.I)
    s = re.sub(r'["\'׳״]', '', s)
    return ' ' + re.sub(r'[\s_\-–—.,()]+', ' ', s).strip() + ' '


def load_pages():
    """הפרשות לפי הסדר שב-js/data.js: שם, כותרת, קובץ הדף, והאם כבר יש פרק."""
    src = open(os.path.join(ROOT, 'js', 'data.js'), encoding='utf-8').read()
    pages, chag = [], False
    for line in src.splitlines():
        if "id: 'chagim'" in line:
            chag = True
        m = re.search(r"name: '([^']+)'.*?pdf: P\('([^']+)\.pdf'\)", line)
        if m and 'parshiot' not in line:
            name = m.group(1)
            pages.append({
                'name': name, 'stem': m.group(2),
                'title': name if chag else 'פרשת ' + name,
                'has_episode': 'spotify:' in line,
            })
    return pages


def notebook_id(arg):
    if arg:
        return arg
    _, out = run(['list', '--json'])
    books = as_rows(out, 'notebooks')
    hits = [b for b in books if 'פרשת השבוע' in norm(str(b.get('title', '')))]
    if len(hits) == 1:
        return hits[0].get('id')
    print('לא מצאתי מחברת אחת בשם "פרשת השבוע". בחרו והריצו שוב עם ‎-n <id>:\n')
    for b in books:
        print(f'  {b.get("id")}  {b.get("title")}')
    sys.exit(1)


def sources(nb):
    _, out = run(['source', 'list', '-n', nb, '--json'])
    return as_rows(out, 'sources')


def find_source(page, srcs):
    """הדף של הפרשה מבין מקורות המחברת, לפי שם הפרשה בכותרת המקור.

    דף משותף (ויקהל–פקודי) נמצא לפי כל אחד מהשמות. אם יש יותר ממקור אחד
    מתאים — לא מנחשים: מציגים את האפשרויות, ומריצים שוב עם --source."""
    keys = [norm(page['name']), norm(page['stem'].split('-', 1)[-1]), norm(page['stem'])]
    hits = [s for s in srcs if any(k in norm(str(s.get('title', ''))) for k in keys)]
    # "ספר בראשית" (קובץ החומש) אינו הדף של פרשת בראשית
    hits = [s for s in hits if ' ספר ' not in norm(str(s.get('title', '')))] or hits
    return hits


def make(page, nb, src_id, prompt, length):
    folder = os.path.join(OUT, page['stem'])
    audio = os.path.join(folder, page['stem'] + '.m4a')
    if os.path.exists(audio):
        print(f'  כבר קיים: {os.path.relpath(audio, ROOT)}')
        return True
    os.makedirs(folder, exist_ok=True)

    print(f'  יוצר סקירה קולית (כמה דקות)…')
    code, out = run(['generate', 'audio', '-n', nb, '-s', src_id,
                     '--format', 'deep-dive', '--length', length, '--language', 'he',
                     '--wait', '--timeout', '1800', '--json',
                     prompt.format(title=page['title'])], check=False)
    if code != 0:
        if 'RATE_LIMITED' in out or 'rate limit' in out.lower():
            print('  המכסה היומית של NotebookLM נגמרה. מריצים שוב מחר.')
            return False
        sys.exit(f'  היצירה נכשלה:\n{out}')
    try:
        task = json.loads(out).get('task_id')
    except (json.JSONDecodeError, AttributeError):
        task = None

    print('  מוריד…')
    dl = ['download', 'audio', '-n', nb, '--force', audio]
    run(dl[:2] + (['-a', task] if task else ['--latest']) + dl[2:])

    cover = os.path.join(ROOT, 'assets', 'covers', page['stem'] + '.png')
    if os.path.exists(cover):
        shutil.copy(cover, os.path.join(folder, 'cover.png'))
    url = f'{SITE}/p/{page["name"].replace(chr(34), "").replace(" ", "-")}/'
    with open(os.path.join(folder, 'description.txt'), 'w', encoding='utf-8') as f:
        f.write(f'כותרת:\n{page["title"]}\n\n'
                f'תיאור:\n{page["title"]} — מתוך "בין הנכתב לנגלה", דפי פרשת השבוע של אריאל ז\'יטניצקי.\n'
                f'הדף המלא לצפייה, להורדה ולהדפסה: {url}\n')
    print(f'  מוכן: {os.path.relpath(folder, ROOT)}')
    return True


def main():
    ap = argparse.ArgumentParser(description='פרק פודקאסט לפרשה מתוך NotebookLM')
    ap.add_argument('names', nargs='*', help='שמות פרשות, כמו "לך לך"')
    ap.add_argument('--from', dest='start', help='להתחיל מפרשה זו')
    ap.add_argument('--count', type=int, default=1, help='כמה פרשות מ---from (ברירת מחדל 1)')
    ap.add_argument('-n', '--notebook', help='מזהה המחברת (ברירת מחדל: "פרשת השבוע")')
    ap.add_argument('--source', help='מזהה המקור, כשהחיפוש לפי שם מוצא יותר מאחד')
    ap.add_argument('--sources', action='store_true', help='הצגת המקורות שבמחברת')
    ap.add_argument('--prompt', default=PROMPT, help='הבקשה לסקירה; {title} יוחלף בשם הפרשה')
    ap.add_argument('--length', default='default', choices=['short', 'default', 'long'])
    args = ap.parse_args()

    global CLI
    CLI = find_cli()
    pages = load_pages()
    by_name = {norm(p['name']): p for p in pages}

    nb = notebook_id(args.notebook)
    srcs = sources(nb)
    if args.sources:
        for s in srcs:
            print(f'  {s.get("id")}  {s.get("title")}')
        return

    if args.start:
        first = by_name.get(norm(args.start))
        if not first:
            sys.exit(f'לא מכיר את הפרשה "{args.start}".')
        i = pages.index(first)
        chosen, seen = [], set()
        for p in pages[i:]:
            if p['stem'] in seen or p['has_episode']:
                continue
            seen.add(p['stem'])
            chosen.append(p)
            if len(chosen) == args.count:
                break
    else:
        chosen = []
        for n in args.names:
            p = by_name.get(norm(n))
            if not p:
                sys.exit(f'לא מכיר את הפרשה "{n}". השמות כמו באתר, למשל "לך לך".')
            chosen.append(p)
    if not chosen:
        sys.exit('לא נבחרו פרשות. למשל: python scripts/make-episode.py "לך לך"')

    for page in chosen:
        print(f'\n{page["title"]}')
        if page['has_episode']:
            print('  לפרשה כבר יש פרק באתר. ממשיך בכל זאת.')
        hits = [{'id': args.source}] if args.source else find_source(page, srcs)
        if len(hits) != 1:
            print('  לא מצאתי במחברת מקור אחד ויחיד לדף הזה.' if not hits else
                  '  נמצא יותר ממקור אחד. בחרו והריצו שוב עם --source <id>:')
            for s in hits:
                print(f'    {s.get("id")}  {s.get("title")}')
            continue
        if not make(page, nb, hits[0]['id'], args.prompt, args.length):
            break


if __name__ == '__main__':
    main()
