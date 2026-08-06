# רשימת התפוצה — Cloudflare Worker + Resend

Worker קטן שמטפל בהרשמה לרשימת התפוצה ושולח את דף הפרשה בכל יום שני וחמישי,
לפי היום שכל נרשם בחר. האתר עצמו נשאר סטטי — **מפתח ה-API של Resend נשמר
כסוד ב-Cloudflare ולעולם לא מגיע לדפדפן**.

## מה ה-Worker עושה

| נתיב | פעולה |
|---|---|
| `POST /subscribe` | קולט מייל + יום מועדף, שומר כ"ממתין" ושולח מייל אישור |
| `GET /confirm` | מאשר את ההרשמה מתוך הקישור במייל (double opt-in) |
| `GET /unsubscribe` | מסיר מהרשימה (גם One-Click של Gmail) |
| `GET /send?day=mon&key=…` | שליחה ידנית לבדיקה |
| cron | שני + חמישי: מזהה את הפרשה/החג הקרוב ושולח |

מיילים שנשלחים כוללים קישור הסרה וכותרת `List-Unsubscribe` — נדרש לפי חוק
התקשורת (תיקון 40) ומשפר מסירוּת.

---

## התקנה (פעם אחת, ~20 דקות)

### 1. Resend — אימות דומיין ומפתח חדש
1. ב-[resend.com](https://resend.com) → **Domains** → **Add Domain** → הזינו את הדומיין שלכם.
2. הוסיפו אצל ספק הדומיין את רשומות ה-DNS ש-Resend מציג (SPF/DKIM). האימות לוקח דקות עד שעות.
3. → **API Keys** → **Create API Key** (הרשאת *Sending access*). העתיקו — הוא מוצג פעם אחת.
   > אם מפתח קודם נחשף אי־פעם — מחקו אותו כאן.

### 2. Cloudflare — הכנה
```bash
cd worker
npx wrangler login                      # פותח דפדפן להתחברות
npx wrangler kv namespace create SUBSCRIBERS
```
העתיקו את ה-`id` שהתקבל אל `wrangler.toml` תחת `kv_namespaces`.

### 3. עדכון `wrangler.toml`
```toml
FROM_EMAIL = "פרשת השבוע <parasha@הדומיין-שלכם>"   # חייב להיות בדומיין שאומת
REPLY_TO   = "כתובת-לתשובות@הדומיין-שלכם"           # אופציונלי
```

### 4. סודות ופריסה
```bash
npx wrangler secret put RESEND_API_KEY   # הדביקו את המפתח מ-Resend
npx wrangler secret put ADMIN_KEY        # מחרוזת אקראית שתמציאו, לשליחה ידנית
npx wrangler deploy
```
בסוף הפריסה מתקבלת כתובת כמו
`https://parasha-newsletter.<שם-המשתמש>.workers.dev`.

### 5. חיבור סופי
1. ב-`wrangler.toml` הזינו את הכתובת שהתקבלה ב-`WORKER_URL` והריצו `npx wrangler deploy` שוב
   (הכתובת נחוצה לקישורי האישור וההסרה שבמיילים).
2. ב-`js/data.js` שבשורש האתר:
   ```js
   window.SUBSCRIBE_API = 'https://parasha-newsletter.<שם-המשתמש>.workers.dev';
   ```
3. commit + push — טופס ההרשמה יופיע באתר.

---

## בדיקה

```bash
# הרשמה (יגיע מייל אישור)
curl -X POST https://<worker>/subscribe \
  -H 'content-type: application/json' \
  -d '{"email":"your@email.com","day":"mon"}'

# אחרי אישור במייל — שליחה ידנית של הדיוור
curl "https://<worker>/send?day=mon&key=<ADMIN_KEY>"

# מי רשום
npx wrangler kv key list --binding SUBSCRIBERS
```

## תחזוקה
- **הוספת דף/פודקאסט**: להריץ `node scripts/build-parashot-json.js` ולדחוף —
  ה-Worker קורא את `assets/parashot.json` מהאתר בכל שליחה, בלי פריסה מחדש.
- **שינוי שעת השליחה**: `crons` ב-`wrangler.toml` (בשעון UTC) ואז `wrangler deploy`.
- **לוגים חיים**: `npx wrangler tail`.

## עלות
Cloudflare Workers: 100,000 בקשות/יום בחינם. Resend: 3,000 מיילים/חודש בחינם
(100/יום). לרשימה קטנה — חינם לחלוטין.
