#!/usr/bin/env python3
"""המקורות שבכל דף, מול ספריא.

שני שלבים, ובין שניהם עין אנושית:

  find <שם קובץ>   מציע מקורות לדף, לפי סדר הופעתם: מראי מקום מפורשים
                   (find-refs של ספריא) ומובאות בלי מראה מקום (חיפוש טקסט).
                   כותב ל-scripts/sources/<שם>.json, רק אם הקובץ עוד לא קיים:
                   קובץ שכבר נבדק ותוקן ביד לא נדרס.
  fetch [שם ...]   לכל קובץ שנבדק ב-scripts/sources/, מוריד מספריא את הטקסט העברי של
                   כל מקור וכותב ל-assets/sources/<שם>.json. זה מה שהאתר מציג.
                   בלי שמות: כל הקבצים.

הזיהוי האוטומטי נכון בערך בארבעה מתוך חמישה מקורות. לכן "find" אינו מגיע
לאתר: רק רשימה שנבדקה ב-scripts/sources/ עוברת ב-"fetch".

API ציבורי, בלי מפתח: https://developers.sefaria.org/reference/getting-started
"""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_DIR = os.path.join(ROOT, 'assets', 'sheet-text')
CURATED_DIR = os.path.join(ROOT, 'scripts', 'sources')
OUT_DIR = os.path.join(ROOT, 'assets', 'sources')
S = 'https://www.sefaria.org'
UA = {'User-Agent': 'parasha-site-sources/1.0', 'Content-Type': 'application/json'}

NIQQUD = re.compile(r'[֑-ׇ]')
SHEM = re.compile(r'י[\u05B0-\u05C7]*ה[\u05B0-\u05C7]*ו[\u05B0-\u05C7]*ה[\u05B0-\u05C7]*(?![\u05D0-\u05EA])')
TEAMIM = re.compile(r'[\u0591-\u05AF\u05BD\u05C0\u05C6]')   # טעמים, מתג, פסק, נון הפוכה
# מכאן ואילך בדף: החידה, הפתרון והחתימה. אין שם מקורות.
TAIL = re.compile(r'פתרון החידה|חידת השבוע|לקינוח:|שבת שלום|רשימת התפוצה|מותר להעביר')


PRIMARY = ['Tanakh/Torah', 'Tanakh', 'Mishnah', 'Tosefta', 'Talmud/Bavli', 'Talmud', 'Midrash']


def PRIMARY_RANK(path):
    for i, p in enumerate(PRIMARY):
        if path.startswith(p) and 'Commentary' not in path:
            return i
    return len(PRIMARY)


def call(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(4):
        try:
            req = urllib.request.Request(S + path, data=data, headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def words(s):
    return re.sub(r'[^א-ת ]', ' ', NIQQUD.sub('', s)).split()


def search(ws, size=5):
    r = call('/api/search-wrapper/es8', {
        'query': ' '.join(ws), 'type': 'text', 'field': 'naive_lemmatizer', 'size': size,
        'slop': 8, 'source_proj': True, 'sort_fields': ['pagesheetrank'], 'sort_method': 'score',
        'sort_reverse': False, 'sort_score_missing': 0.04, 'filters': [], 'filter_fields': [], 'aggs': []})
    return [h['_source'] for h in r['hits']['hits']]


def find_refs(text):
    task = call('/api/find-refs', {'text': {'title': '', 'body': text}, 'lang': 'he'})
    for _ in range(60):
        a = call('/api/async/' + task['task_id'])
        if a.get('ready'):
            return [x for x in a['result']['body']['results'] if x.get('refs')]
        time.sleep(2)
    return []


def is_quote(p):
    p = p.strip()
    return (len(NIQQUD.findall(p)) > len(p) * 0.15) or p[:1] in '"״'


def merge_refs(refs):
    """Numbers 11:26, Numbers 11:27 ... ← Numbers 11:26-29, כשהם רצופים באותו פרק."""
    out = []
    for r in refs:
        m = re.match(r'^(.*?)(\d+[ab]?):(\d+)$', r)
        if out and m and out[-1][0] == m.group(1) + m.group(2) and int(m.group(3)) - out[-1][2] in (0, 1, 2):
            out[-1][2] = int(m.group(3))
        elif m:
            out.append([m.group(1) + m.group(2), int(m.group(3)), int(m.group(3))])
        else:
            out.append([r, None, None])
    return [a if b is None else (f'{a}:{b}' if b == c else f'{a}:{b}-{c}') for a, b, c in out]


def find(name):
    src = os.path.join(TEXT_DIR, name + '.json')
    paras = json.load(open(src, encoding='utf-8'))['paragraphs']
    found = []
    # מובאות שנשברו לכמה שורות (שני טורים) מתאחדות לגוש אחד
    blocks, cur = [], None
    for i, p in enumerate(paras):
        if TAIL.search(p):
            paras = paras[:i]
            break
        if is_quote(p):
            if cur and cur['end'] == i - 1:
                cur['text'] += ' ' + p
                cur['end'] = i
            else:
                cur = {'start': i, 'end': i, 'text': p}
                blocks.append(cur)
    # find-refs פעם אחת על כל הדף (כל קריאה אסינכרונית ולוקחת שניות), ואז כל
    # מראה מקום משויך לפסקה שלו לפי המיקום שלו בטקסט
    starts, pos = [], 0
    for p in paras:
        starts.append(pos)
        pos += len(p) + 1
    for x in find_refs('\n'.join(paras)):
        i = max(k for k, st in enumerate(starts) if st <= x['startChar'])
        found.append({'para': i, 'how': 'מראה מקום', 'ref': x['refs'][0], 'anchor': x['text']})
    for b in blocks:
        ws = words(b['text'])
        if len(ws) < 4:
            continue
        hits = []
        for k in range(0, max(1, len(ws) - 4), 10):
            h = search(ws[k:k + 12], size=8)
            if h:
                # פסוק מצוטט גם באלף פירושים. המקור עצמו קודם לכל מי שמצטט אותו.
                hits.append(min(h, key=lambda s: PRIMARY_RANK(s.get('path', '')))['ref'])
        if hits:
            found.append({'para': b['start'], 'how': 'מובאה', 'ref': merge_refs(hits)[0] if len(set(merge_refs(hits))) == 1 else ' | '.join(merge_refs(hits)),
                          'snippet': b['text'][:80]})
    found.sort(key=lambda x: x['para'])
    return found


def he_text(ref):
    r = call('/api/v3/texts/' + urllib.parse.quote(ref) + '?version=hebrew&return_format=text_only')
    v = r['versions'][0]
    t = v['text']

    def flat(x):
        if isinstance(x, list):
            return [s for y in x for s in flat(y)]
        return [x] if x else []
    # טעמי המקרא יורדים (הניקוד נשאר, כמו בפסוקים שבדפים), וכך גם סימני
    # הפרשה הפתוחה והסתומה {פ} {ס} שבנוסח המסורה.
    segs = [re.sub(r'\s*\{[פס]\}\s*', ' ', TEAMIM.sub('', html.unescape(re.sub(r'<[^>]+>', '', s)))).strip()
            for s in flat(t)]
    # שם ה' נכתב בדפים ה'. כך גם כאן, ולא שם המפורש כפי שהוא בנוסח המסורה.
    segs = [SHEM.sub('ה׳', s) for s in segs]
    return {'ref': r['ref'], 'heRef': r['heRef'], 'he': [s for s in segs if s],
            'version': v.get('versionTitle', ''), 'license': v.get('license', ''),
            'url': 'https://www.sefaria.org.il/' + urllib.parse.quote(r['ref'].replace(' ', '_'), safe=':,') + '?lang=he'}


def fetch(names):
    os.makedirs(OUT_DIR, exist_ok=True)
    for n in names:
        cur = json.load(open(os.path.join(CURATED_DIR, n + '.json'), encoding='utf-8'))
        out = []
        for s in cur['sources']:
            t = he_text(s['ref'])
            t['para'] = s['para']
            if s.get('anchor'):
                t['anchor'] = s['anchor']
            if s.get('note'):
                t['note'] = s['note']
            out.append(t)
            print(f"  {t['heRef']}  ({len(t['he'])} קטעים, {t['version']}, {t['license']})")
        res = {'sources': out}
        if cur.get('sheet'):
            res['sheet'] = cur['sheet']
        with open(os.path.join(OUT_DIR, n + '.json'), 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
            f.write('\n')
        print(f'{n}: {len(out)} מקורות')
    write_manifest()


def write_manifest():
    """js/sources-manifest.js: לאילו דפים יש מקורות, כדי שהאתר לא יבקש קובץ שאינו קיים."""
    names = sorted(f[:-5] for f in os.listdir(OUT_DIR) if f.endswith('.json'))
    with open(os.path.join(ROOT, 'js', 'sources-manifest.js'), 'w', encoding='utf-8') as f:
        f.write('// נוצר אוטומטית ע"י scripts/sefaria-sources.py fetch — לא לערוך ידנית\n')
        f.write('window.SOURCE_FILES = [\n' + ''.join(f" '{n}.json',\n" for n in names) + '];\n')


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == 'find':
        os.makedirs(CURATED_DIR, exist_ok=True)
        for n in sys.argv[2:]:
            dst = os.path.join(CURATED_DIR, n + '.json')
            res = find(n)
            for x in res:
                print(x['para'], x['how'], '|', x['ref'], '|', (x.get('anchor') or x.get('snippet'))[:60])
            if os.path.exists(dst):
                print(f'{dst} כבר קיים ולא נדרס')
                continue
            with open(dst, 'w', encoding='utf-8') as f:
                json.dump({'reviewed': False, 'sources': res}, f, ensure_ascii=False, indent=1)
                f.write('\n')
    elif len(sys.argv) >= 2 and sys.argv[1] == 'fetch':
        # בלי שמות: רק רשימות שנבדקו ("reviewed" אינו false). טיוטה של find לא מגיעה לאתר.
        names = sys.argv[2:] or sorted(
            f[:-5] for f in os.listdir(CURATED_DIR) if f.endswith('.json')
            and json.load(open(os.path.join(CURATED_DIR, f), encoding='utf-8')).get('reviewed') is not False)
        fetch(names)
    else:
        sys.exit(__doc__)
