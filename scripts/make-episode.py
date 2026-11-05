#!/usr/bin/env python3
"""מכין פרק פודקאסט לפרשה: סקירה קולית מ-NotebookLM, כרטיס, ותיאור לספוטיפיי.

הדרך שבה נוצרו הפרקים עד היום: במחברת "פרשת השבוע", שבה נמצאים כל הדפים,
מסמנים רק את הדף של השבוע ומבקשים סקירה קולית - שני מנחים שמנתחים ודנים
ברעיונות שבדף. הסקריפט עושה את אותו הדבר, ומוסיף את מה שצריך להעלאה:

    scripts/episodes/   (או התיקייה שב---out, למשל ב-Google Drive)
        פרשת וארא - בין הנכתב לנגלה.m4a   הסקירה הקולית
        פרשת וארא - כרטיס.png             כרטיס הפרק (מ-assets/covers, 3000×3000)
        פרשת וארא - תיאור.txt             כותרת ותיאור, עם הקישור לעמוד הדף באתר

את הפרק מעלים ל-Spotify for Creators ביד, ושולחים לClaude את הקישור - הוא
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
    python scripts/make-episode.py --book שמות          # כל ספר שמות, פרק לכל פרשה
    python scripts/make-episode.py --book שמות --out "<תיקייה ב-Google Drive>"

    # סקירות שכבר נוצרו במחברת (ביד, ב-Studio) - רק להוריד, בלי ליצור מחדש:
    python scripts/make-episode.py --audio                   # אילו סקירות יש, ולאיזו פרשה
    python scripts/make-episode.py --existing --book בראשית  # הורדה לכל פרשה בלי פרק באתר
    python scripts/make-episode.py --existing ויצא --artifact <id>

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
# לאן נשמרים הפרקים. ברירת המחדל בתוך הריפו (מחוץ ל-git); עם --out או
# PARASHA_EPISODES_DIR אפשר לכוון לתיקייה של Google Drive במחשב, וכך הקבצים
# עולים לאחסון מעצמם.
OUT = os.environ.get('PARASHA_EPISODES_DIR') or os.path.join(ROOT, 'scripts', 'episodes')
BRAND = 'בין הנכתב לנגלה'
BOOKS = {'בראשית': 'bereshit', 'שמות': 'shmot', 'ויקרא': 'vayikra',
         'במדבר': 'bamidbar', 'דברים': 'devarim', 'חגים': 'chagim'}
SITE = 'https://parasha.azma.app'

# הבקשה ל-NotebookLM. אפשר להחליף ב---prompt.
# אותו נוסח מופיע ב-docs/podcast-prompt.md, להעתקה ידנית ל-NotebookLM.
PROMPT = ('פרק פודקאסט בעברית: שני מנחים בשיחה, שמנתחים ודנים ברעיונות שמופיעים בדף של '
          '{title} - רק בדף הזה, מתוך המקור שסומן. פתחו בשאלה או בתמיהה שהדף מעלה, '
          'עקבו אחרי מהלך הטיעון של הכותב שלב אחר שלב, הביאו את הפסוקים, המדרשים '
          'והפרשנים שהוא מצטט, והגיעו למסקנה שלו. מותר לשאול ולהתווכח, אבל לא להוסיף '
          'פרשנות או עובדות שאינן בדף. הדף נכתב על ידי אריאל ז\'יטניצקי, '
          'מתוך הסדרה "בין הנכתב לנגלה".')

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
    return ' ' + re.sub(r'[\s_\-–—.,:;!?/|()\[\]]+', ' ', s).strip() + ' '


def load_pages():
    """הפרשות לפי הסדר שב-js/data.js: שם, כותרת, קובץ הדף, והאם כבר יש פרק."""
    src = open(os.path.join(ROOT, 'js', 'data.js'), encoding='utf-8').read()
    pages, chag, book = [], False, None
    for line in src.splitlines():
        b = re.search(r"\{ id: '(\w+)'", line)
        if b:
            book = b.group(1)
            chag = book == 'chagim'
        m = re.search(r"name: '([^']+)'.*?pdf: P\('([^']+)\.pdf'\)", line)
        if m and 'parshiot' not in line:
            name = m.group(1)
            pages.append({
                'name': name, 'stem': m.group(2),
                'title': name if chag else 'פרשת ' + name,
                'has_episode': 'spotify:' in line,
                'book': book,
            })
    # דף אחד לשתי פרשות (ויקהל-פקודי): הכותרת מחברת את שתיהן
    for p in pages:
        names = [q['name'] for q in pages if q['stem'] == p['stem'] and q['book'] == p['book']]
        if len(names) > 1 and not chag_of(p):
            p['title'] = 'פרשת ' + '-'.join(names)
    return pages


def chag_of(page):
    return page['book'] == 'chagim'


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

    דף משותף (ויקהל-פקודי) נמצא לפי כל אחד מהשמות. אם יש יותר ממקור אחד
    מתאים - לא מנחשים: מציגים את האפשרויות, ומריצים שוב עם --source."""
    keys = [norm(page['name']), norm(page['stem'].split('-', 1)[-1]), norm(page['stem'])]
    hits = [s for s in srcs if any(k in norm(str(s.get('title', ''))) for k in keys)]
    # "ספר בראשית" (קובץ החומש) אינו הדף של פרשת בראשית
    hits = [s for s in hits if ' ספר ' not in norm(str(s.get('title', '')))] or hits
    return hits


def make(page, nb, src_id, prompt, length, out):
    # שם הפרשה בראש שם כל קובץ, כולם באותה תיקייה - כך הם מסודרים
    # ונמצאים בחיפוש באחסון: "פרשת וארא - בין הנכתב לנגלה.m4a"
    base = os.path.join(out, page['title'])
    audio = f'{base} - {BRAND}.m4a'
    if os.path.exists(audio):
        print(f'  כבר קיים: {audio}')
        return True
    os.makedirs(out, exist_ok=True)

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
    extras(page, base)
    print(f'  מוכן: {audio}')
    return True


def audio_artifacts(nb):
    """הסקירות הקוליות המוכנות שבמחברת, כל אחת עם הבקשה שממנה נוצרה."""
    _, out = run(['artifact', 'list', '-n', nb, '--type', 'audio', '--json'])
    arts = [a for a in as_rows(out, 'artifacts')
            if str(a.get('status', '')).lower() in ('', 'completed', 'complete', 'ready', 'done')]
    for a in arts:
        code, p = run(['artifact', 'get-prompt', str(a.get('id')), '-n', nb, '--json'], check=False)
        try:
            a['prompt'] = json.loads(p).get('prompt') or '' if code == 0 else ''
        except (json.JSONDecodeError, AttributeError):
            a['prompt'] = ''
    return arts


def find_audio(page, arts):
    """הסקירה של הפרשה, לפי שם הפרשה בכותרת הסקירה או בבקשה שממנה נוצרה.

    כמו במקורות: אם יש יותר מהתאמה אחת - לא מנחשים."""
    keys = {norm(page['name']), norm(page['title'])}
    return [a for a in arts
            if any(k in norm(str(a.get('title', ''))) or k in norm(str(a.get('prompt', '')))
                   for k in keys)]


def fetch(page, nb, art_id, out):
    """מוריד סקירה שכבר נוצרה במחברת, ומכין לידה כרטיס ותיאור."""
    base = os.path.join(out, page['title'])
    audio = f'{base} - {BRAND}.m4a'
    if os.path.exists(audio):
        print(f'  כבר קיים: {audio}')
        return
    os.makedirs(out, exist_ok=True)
    print('  מוריד את הסקירה הקיימת…')
    run(['download', 'audio', '-n', nb, '-a', art_id, '--force', audio])
    extras(page, base)
    print(f'  מוכן: {audio}')


def extras(page, base):
    """כרטיס הפרק ותיאור לספוטיפיי, ליד קובץ השמע."""
    cover = os.path.join(ROOT, 'assets', 'covers', page['stem'] + '.png')
    if os.path.exists(cover):
        shutil.copy(cover, f'{base} - כרטיס.png')
    url = f'{SITE}/p/{page["name"].replace(chr(34), "").replace(" ", "-")}/'
    with open(f'{base} - תיאור.txt', 'w', encoding='utf-8') as f:
        f.write(f'כותרת:\n{page["title"]}\n\n'
                f'תיאור:\n{page["title"]} - מתוך "בין הנכתב לנגלה", דפי פרשת השבוע של אריאל ז\'יטניצקי.\n'
                f'הדף המלא לצפייה, להורדה ולהדפסה: {url}\n')


def main():
    ap = argparse.ArgumentParser(description='פרק פודקאסט לפרשה מתוך NotebookLM')
    ap.add_argument('names', nargs='*', help='שמות פרשות, כמו "לך לך"')
    ap.add_argument('--from', dest='start', help='להתחיל מפרשה זו')
    ap.add_argument('--count', type=int, default=1, help='כמה פרשות מ---from (ברירת מחדל 1)')
    ap.add_argument('--book', help='כל הפרשות של ספר, למשל --book שמות (מדלג על מה שכבר יש לו פרק)')
    ap.add_argument('--out', default=OUT, help='תיקיית השמירה, למשל תיקייה ב-Google Drive')
    ap.add_argument('--prompt-file', help='קובץ טקסט עם הבקשה ל-NotebookLM ({title} = שם הפרשה)')
    ap.add_argument('-n', '--notebook', help='מזהה המחברת (ברירת מחדל: "פרשת השבוע")')
    ap.add_argument('--source', help='מזהה המקור, כשהחיפוש לפי שם מוצא יותר מאחד')
    ap.add_argument('--sources', action='store_true', help='הצגת המקורות שבמחברת')
    ap.add_argument('--prompt', default=PROMPT, help='הבקשה לסקירה; {title} יוחלף בשם הפרשה')
    ap.add_argument('--length', default='default', choices=['short', 'default', 'long'])
    ap.add_argument('--existing', action='store_true',
                    help='להוריד סקירה שכבר נוצרה במחברת, במקום ליצור חדשה')
    ap.add_argument('--artifact', help='מזהה הסקירה, כשבמצב --existing נמצאה יותר מאחת')
    ap.add_argument('--audio', action='store_true',
                    help='הצגת הסקירות הקוליות שבמחברת, ולאיזו פרשה כל אחת שייכת')
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

    arts = audio_artifacts(nb) if (args.existing or args.audio) else []
    if args.audio:
        for a in sorted(arts, key=lambda a: str(a.get('created_at') or '')):
            owners = [p['title'] for p in pages if find_audio(p, [a])]
            day = str(a.get('created_at') or '')[:10]
            print(f'  {a.get("id")}  {day}  {a.get("title")}'
                  f'  ←  {", ".join(dict.fromkeys(owners)) or "לא זוהתה פרשה"}')
        return

    if args.prompt_file:
        with open(args.prompt_file, encoding='utf-8') as f:
            args.prompt = f.read().strip()

    if args.book:
        book = BOOKS.get(args.book.replace('ספר', '').strip())
        if not book:
            sys.exit(f'לא מכיר את הספר "{args.book}". אחד מ: {", ".join(BOOKS)}')
        chosen, seen = [], set()
        for p in pages:
            if p['book'] != book or p['stem'] in seen:
                continue
            seen.add(p['stem'])
            if p['has_episode']:
                print(f'{p["title"]}: כבר יש פרק באתר, מדלג')
                continue
            chosen.append(p)
    elif args.start:
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
        if args.existing:
            found = [{'id': args.artifact}] if args.artifact else find_audio(page, arts)
            if len(found) != 1:
                print('  לא מצאתי במחברת סקירה קולית לדף הזה.' if not found else
                      '  נמצאה יותר מסקירה אחת. בחרו והריצו שוב עם --artifact <id>:')
                for a in found:
                    print(f'    {a.get("id")}  {str(a.get("created_at") or "")[:10]}  {a.get("title")}')
                continue
            fetch(page, nb, found[0]['id'], args.out)
            continue
        hits =[{'id': args.source}] if args.source else find_source(page, srcs)
        if len(hits) != 1:
            print('  לא מצאתי במחברת מקור אחד ויחיד לדף הזה.' if not hits else
                  '  נמצא יותר ממקור אחד. בחרו והריצו שוב עם --source <id>:')
            for s in hits:
                print(f'    {s.get("id")}  {s.get("title")}')
            continue
        if not make(page, nb, hits[0]['id'], args.prompt, args.length, args.out):
            break


if __name__ == '__main__':
    main()
