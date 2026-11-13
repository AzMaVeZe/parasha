"""תיקוני טקסט משותפים לאתר ("קריאת הדף כטקסט") ולספר.

מה שנמצא בסבב ההגהה (נובמבר 2026) ונוגע לטקסט עצמו של הדף — לא לעריכה של הספר:
- FIXES: תיקונים מדויקים לכל דף. אותיות זרות מכיתובים מסובבים, אנגלית שהתהפכה בחילוץ, שאריות של
  רשימת התפוצה ושל עימוד הדף, ותיקון עובדתי שאריאל אישר (רבקה).
- dagesh: דגש כפול על אותה אות.
- tanakh: ניקוד הפסוקים מול נוסח מנוקד תקני (Tanach with Nikkud, נחלת הכלל, מ-tanach.us דרך ספריא).
  כל מילה מנוקדת בדף מוחלפת במילה המקבילה בנוסח, אם האותיות זהות. כך מתוקנים דגש שזז לאות שכנה,
  ניקוד חסר (וארא) ומילים שהתפרקו. ה', אֱ-לֹהִים והפיסוק של הדף נשארים כפי שהם.

שימוש: apply(name, text) על כל פסקה והערה. האתר: scripts/extract-sheet-text.py. הספר: book/build_book.py.
"""
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '.cache', 'tanakh')
NIK = '֑-ׇ'
NIKUD = re.compile('[%s]' % NIK)
HEB = 'א-ת'

# (דף, נוסח בדף, נוסח מתוקן)
FIXES = {
    # אותיות זרות מכיתובים מסובבים שליד הטקסט (כפי שהן יוצאות בחילוץ הנוכחי)
    'bereshit-מקץ': [(' ream', ''), ('ראובן: uf)1', 'ראובן:'), (' y pR te', ''), (' 8s 2ni 9g', ''), (' ( A do oL le', ''), (' eB e R n', ''),
                    (' gm e', ''), (' 17lets', '')],
    'bereshit-ויחי': [(' rfaJ', ''), (' mo b B ht eel', ''), (' gisi uS', ''), (' sn s d', ''), (' alul ts B biar', ''),
                     (' eo n)', ''), (' 9 Canaan', ''), ('ועוד ועוד...) שאלות', 'ועוד ועוד... שאלות')],
    'shmot-שמות': [(' 32es D', ''), ("n 'המספר המקראי", "'המספר המקראי")],
    'shmot-תצוה': [('scaraáM', 'Máscara'), ('הסיוע של רחל ליעקב', 'הסיוע של רבקה ליעקב')],   # רבקה: אושר ע"י אריאל
    'vayikra-שמיני': [('.it squander can we or it invest can We', 'We can invest it or we can squander it.')],
    'bereshit-נח': [(')out first in first – FIFO(.', '(first in first out – FIFO).'),
                    ('(out last in last – LIFO).', '(last in last out – LIFO).')],
    'bereshit-וישב': [('Ltd Goats&Sheeps Lavan.', 'Lavan Goats&Sheeps Ltd.')],
    'bereshit-וישלח': [(' Wrestling Jacob Angel the with)Rembrandt( ', ' ')],     # כיתוב תמונה
    'shmot-וארא': [('Strategically Thinking', 'Thinking Strategically'),
                   ('Conflict of Strategy The(.', 'The Strategy of Conflict).')],
    'shmot-יתרו': [('Tat for Tit', 'Tit for Tat')],
    'vayikra-ויקרא': [('Dijkstra.W Edsger', 'Edsger W. Dijkstra')],
    'vayikra-צו': [('Friedman.D Stewart.', 'Stewart D. Friedman.')],
    'devarim-שופטים': [('Review Business Harvard', 'Harvard Business Review'), ('Week Business', 'Business Week'),
                       (')Stories Success Such Be Can Failures Why(.', '(Why Failures Can Be Such Success Stories).')],
    'devarim-כי-תצא': [('(%0.5)', '(0.5%)'), ('%0.75', '0.75%'),
                       ('עצמו. נבדוק מה מתחלק בשבע והמספר הוא 5861674 ', '')],   # פתרון חידה בהערה 18
    'chagim-ראש-השנה': [(': [כתובת מייל]', '.'),
                        ('---------- message Forwarded ---------- >mailto:[כתובת מייל]< Heler Yaniv:From '
                         '2009/9/15:Date (גאולת ישמעאל (ראש השנה:Subject:To', '')],   # כותרת של מייל מועבר
    'bamidbar-נשא': [('- המשך בעמוד הבא - ', '')],
}


# הכותרת התחתונה של המייל: "מותר להעביר הלאה. להוספה/הסרה מרשימת התפוצה נא לעדכן אותי [כתובת מייל]. אשמח לשמוע"
MAILING = re.compile(
    r'(?:(?:מותר\s*(?:\([^)]*\)\s*)?)?להעביר הלאה(?: בשמחה)?[^|.\n]{0,4}[|.]?\s*)?'
    r'(?:המעוניינים להצטרף לרשימת התפוצה או להיגרע ממנה,|להוספה(?:/| או )ל?הסרה מרשימת התפוצה)'
    r'[^\[]{0,30}\[כתובת מייל\]\.?\s*(?:\|\s*)?(?:(?:וככלל )?אשמח לשמוע(?: \d(?!\d))?)?')


# דפים שבהם כיתוב מסובב ליד הטקסט נכנס לשורות כאותיות לטיניות. הצורה המדויקת משתנה בין גרסאות של
# ספריית ה-PDF ("c o" / "mo b B ht eel"), ולכן כלל כללי — ורק בדפים האלה, כי בדפים אחרים יש
# משתנים מתמטיים אמיתיים (X, r, a,b).
GARBAGE_SHEETS = {'bereshit-ויחי', 'bereshit-מקץ', 'shmot-שמות'}
LATIN_RUN = re.compile(r"[A-Za-z0-9().,'’]+(?: +[A-Za-z0-9().,'’]+)*")


def _bad(tok):
    w = re.sub(r"[^A-Za-z0-9]", '', tok)
    if not w or w.isdigit():
        return None                                    # מספר או סימן: לא קובע
    if re.search(r'\d', w):
        return True                                    # 17lets, 8s
    letters = re.sub(r'\d', '', w)
    if len(letters) <= 2:
        return True                                    # c, o, ht
    return not re.fullmatch(r'[A-Z]?[a-z]+|[A-Z]+', letters)   # rfaJ, pR


def latin_garbage(name, text):
    if name not in GARBAGE_SHEETS:
        return text

    def sub(m):
        kinds = [k for k in (_bad(t) for t in m.group().split()) if k is not None]
        if not kinds or not any(kinds) or sum(kinds) < len(kinds) / 2:
            return m.group()
        g = m.group()
        a = re.search(r'[A-Za-z0-9]', g).start()
        b = len(g) - re.search(r'[A-Za-z0-9]', g[::-1]).start()
        return g[:a] + g[b:]
    text = LATIN_RUN.sub(sub, text)
    return re.sub(r'  +', ' ', text)


def fixes(name, text, log=None):
    text = MAILING.sub('', text).strip()
    for old, new in FIXES.get(name, []):
        if old in text:
            text = text.replace(old, new)
            if log is not None:
                log.append((name, old, new))
    return text


def dagesh(t):
    """דגש כפול על אותה אות ← אחד ("וַיִנָּּחֵם")."""
    return re.sub('\u05BC([\u0591-\u05BB\u05BD-\u05C7]*)\u05BC', '\u05BC\\1', t)


# ---------------------------------------------------------------- ניקוד הפסוקים מול נוסח תקני
BOOKS = ['Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy', 'Joshua', 'Judges', 'I Samuel', 'II Samuel',
         'I Kings', 'II Kings', 'Isaiah', 'Jeremiah', 'Ezekiel', 'Hosea', 'Joel', 'Amos', 'Obadiah', 'Jonah',
         'Micah', 'Nahum', 'Habakkuk', 'Zephaniah', 'Haggai', 'Zechariah', 'Malachi', 'Psalms', 'Proverbs', 'Job',
         'Song of Songs', 'Ruth', 'Lamentations', 'Ecclesiastes', 'Esther', 'Daniel', 'Ezra', 'Nehemiah',
         'I Chronicles', 'II Chronicles']
FINAL = str.maketrans('ךםןףץ', 'כמנפצ')
_INDEX = None


def skel(w):
    return re.sub('[^%s]' % HEB, '', w).translate(FINAL)


def _book(name):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, name + '.json')
    if not os.path.exists(f):
        url = ('https://www.sefaria.org/api/v3/texts/' + urllib.parse.quote(name)
               + '?version=' + urllib.parse.quote('hebrew|Tanach with Nikkud') + '&return_format=text_only')
        req = urllib.request.Request(url, headers={'User-Agent': 'parasha-site-build'})
        d = json.load(urllib.request.urlopen(req, timeout=60))
        v = d['versions'][0]
        assert v['license'] == 'Public Domain', v['license']
        json.dump(v['text'], open(f, 'w'), ensure_ascii=False)
    return json.load(open(f))


def _index():
    """כל מילות התנ"ך ברצף אחד, ואינדקס של שלשות שלד (אותיות בלבד) → מקום."""
    global _INDEX
    if _INDEX is None:
        words, tri = [], {}
        for b in BOOKS:
            for ch in _book(b):
                for v in ch:
                    v = re.sub(r'\{[פס]\}|׃|\[.*?\]', ' ', v)
                    for w in re.split(r'[\s־]+', v):
                        if skel(w):
                            words.append(unicodedata.normalize('NFC', re.sub(r'[^%s%s]' % (HEB, NIK), '', w)))
        sk = [skel(w) for w in words]
        for i in range(len(sk) - 2):
            tri.setdefault((sk[i], sk[i + 1], sk[i + 2]), []).append(i)
        _INDEX = (words, sk, tri)
    return _INDEX


TOKEN = re.compile(r'[%s%s]+' % (HEB, NIK))


# דגש, נקודת שׁ/שׂ, מתג ורפה — מה שמותר להוסיף או להזיז. תנועה אחרת — לא: אז זו כנראה מילה מפסוק אחר
FREE = set('\u05BC\u05C1\u05C2\u05BD\u05BF')


def clusters(w):
    out = []
    for c in unicodedata.normalize('NFC', w):
        if re.match('[%s]' % HEB, c):
            out.append([c, set()])
        elif out and NIKUD.match(c):
            out[-1][1].add(c)
    return out


def compatible(old, new):
    """ההחלפה רק משלימה ניקוד חסר או מתקנת דגש/נקודה. תנועה שונה (אַל/אֶל) או מילה בלי ניקוד (כתיב) — לא."""
    a, b = clusters(old), clusters(new)
    if len(a) != len(b) or not NIKUD.search(new):
        return False
    return all(x[0] == y[0] and (x[1] - FREE) <= (y[1] - FREE) for x, y in zip(a, b))


def vayi(t):
    """דגש שזז מהיו"ד של וַיִּ לאות שאחריה: "וַיִשְּׁלַח" ← "וַיִּשְׁלַח" (לא בת׳ — ב"וַיִּתֵּן" שני הדגשים נכונים)."""
    return re.sub('(?<![%s])ו\u05B7י\u05B4([א-שׁ])([\u05B0-\u05BB]*)\u05BC' % HEB,
                  lambda m: 'ו\u05B7י\u05B4\u05BC' + m.group(1) + m.group(2), t)


def tanakh(text, log=None):
    """ניקוד של כל רצף מילים מנוקדות בטקסט, מול המקום המתאים בתנ"ך."""
    words, sk, tri = _index()
    toks = [m for m in TOKEN.finditer(text)]
    voc = [bool(NIKUD.search(m.group())) for m in toks]
    out, last, i = [], 0, 0
    reps = {}
    while i < len(toks):
        if not voc[i]:
            i += 1
            continue
        j = i
        # רצף: מילים מנוקדות, ה׳, ומילה קצרה בלי ניקוד שבאה בין שתי מנוקדות ("לא", "כי")
        # רצף נגמר גם במרכאה: '"פסוק אחד", "פסוק שני"' הם שני מקומות שונים בתנ"ך
        while j < len(toks) and (voc[j] or skel(toks[j].group()) in ('ה',)
                                 or (len(skel(toks[j].group())) <= 3 and j + 1 < len(toks) and voc[j + 1])) \
                and not (j > i and re.search('["״]', text[toks[j - 1].end():toks[j].start()])):
            j += 1
        run = toks[i:j]
        rs = [skel(t.group()) for t in run]
        # מיקום: הצבעה של שלשות
        votes = {}
        for k in range(len(rs) - 2):
            for pos in tri.get((rs[k], rs[k + 1], rs[k + 2]), [])[:50]:
                votes[pos - k] = votes.get(pos - k, 0) + 1
        if votes:
            start, n = max(votes.items(), key=lambda x: x[1])
            if n >= (2 if len(rs) >= 5 else 1):
                p = max(0, start - 2)
                for t in run:
                    s = skel(t.group())
                    w = t.group()
                    if len(s) < 2:
                        continue
                    hit = next((q for q in range(p, min(p + 12, len(sk))) if sk[q] == s), None)
                    if hit is None:
                        continue
                    p = hit + 1
                    good = words[hit]
                    if good != unicodedata.normalize('NFC', w) and skel(good) == s and compatible(w, good):
                        reps[t.start()] = (t.end(), good, w)
        i = j
    for st in sorted(reps):
        en, good, w = reps[st]
        out.append(text[last:st])
        out.append(good)
        last = en
        if log is not None:
            log.append((w, good))
    out.append(text[last:])
    return ''.join(out)


def apply(name, text, log=None):
    text = fixes(name, latin_garbage(name, text), log)
    text = text.replace('\u05BA', '\u05B9')          # חולם חסר לו ← חולם, לאחידות
    text = vayi(dagesh(text))
    if NIKUD.search(text):
        text = tanakh(text, log)
    return text
