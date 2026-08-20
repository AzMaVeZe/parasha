# ספר הפעלה

## להוסיף דף חדש

1. לשים את ה-PDF ב-`assets/pdfs/` בשם `<ספר>-<פרשה>.pdf` (למשל `devarim-ראה.pdf`)
2. `bash scripts/build-pdf-manifest.sh` — מעדכן את רשימת הקבצים הקיימים
3. `python3 scripts/build-previews.py` — מרנדר את העמוד הראשון לתצוגה מקדימה
4. `node scripts/build-parashot-json.js` — מעדכן את המפתח שה-Worker קורא לדיוור
5. לוודא שיש רשומה מתאימה ב-`js/data.js` עם `pdf: P('...')`
6. commit + push. Cloudflare פורס תוך פחות מדקה.

עמוד הדף הסטטי (`/p/<שם>/`), מפת האתר ו-`llms.txt` נוצרים מחדש בכל בנייה מתוך
`js/data.js` — אין מה לעדכן ידנית, ואין קובץ `sitemap.xml` בריפו. לבדיקה מקומית:

```bash
bash scripts/build-site.sh && cd dist && python3 -m http.server 8000
```

הבנייה נכשלת אם מספר העמודים שנוצרו אינו תואם למספר הדפים ב-`js/data.js`.

הכפתורים "צפייה"/"הורדה" מופיעים רק כשהקובץ באמת קיים במניפסט, ולכן אפשר להוסיף בהדרגה.

## להוסיף פודקאסט

ב-`js/data.js`, להוסיף לשורה של הפרשה:

```js
spotify: 'https://open.spotify.com/episode/XXXXXXXX'
```

בלי הפרמטר `?si=...` — הוא מזהה מעקב, ואינו נחוץ. הנגן והתגית "פודקאסט" בכרטיס מופיעים אוטומטית.

## לאשר תגובה

תגובה חדשה שולחת מייל ל-`OWNER_EMAIL` עם כפתורי **אישור ופרסום** / **דחייה**. אפשר גם:

```
https://parasha-newsletter.azma.workers.dev/admin?key=<ADMIN_KEY>
```

רשימה של הממתינות ושל המפורסמות, עם כפתור הסרה לכל אחת. שום תגובה לא מופיעה באתר לפני אישור.

## דיוור

רץ אוטומטית שני/חמישי/שישי ב-04:00 UTC (07:00 שעון קיץ). כל נרשם מקבל רק ביום שבחר. שליחה ידנית:

```
https://parasha-newsletter.azma.workers.dev/send?day=mon&key=<ADMIN_KEY>
```

המייל כולל עד שני כרטיסים — החג הקרוב ופרשת השבת — כל אחד עם קישור לדף ולפודקאסט אם יש. דף בלי PDF לא נשלח, ואם אין שום דף מתאים המייל לא יוצא בכלל.

## להחליף גופן

לערוך את `FAMILIES` ב-`scripts/build-fonts.py` ולהריץ את ה-Action **"עדכון גופנים"** (Actions ‹ Run workflow). הוא מוריד, כותב את `fonts.css`, מוחק קבצים שיצאו משימוש, ודוחף. אם משהו חסר — הוא נכשל ולא דוחף.

אחר כך לעדכן את `--font-body` / `--font-display` ב-`tokens/typography.css`.

## לפרוס את ה-Worker

```
cd worker
npx wrangler deploy
```

סודות (לא בקוד): `RESEND_API_KEY`, `ADMIN_KEY`, `OWNER_EMAIL`.

```
npx wrangler secret list          # רואים שמות, לא ערכים
npx wrangler secret put ADMIN_KEY
```

בדיקות: `node worker/test/comments.test.mjs` — 24 בדיקות מול KV ו-Resend מדומים, בלי פריסה.

## כשמשהו לא עובד

**סדר הבדיקה, מהזול ליקר:**

1. `https://<worker>/status?key=<ADMIN_KEY>` — מפתחות, כתובות, סטטוס הדומיין ב-Resend, נרשמים, מוני תגובות
2. `https://<worker>/testmail?to=<כתובת>&key=<ADMIN_KEY>` — מנסה לשלוח באמת ומחזיר את שגיאת Resend מילה במילה
3. `https://parasha.azma.app/js/data.js?nocache=1` — לוודא איזו גרסה מוגשת בפועל. פרמטר שונה בכל פעם, אחרת הדפדפן מגיש מהמטמון
4. `npx wrangler tail` — לוגים חיים מה-Worker

**"משהו השתבש בשליחה"** — כמעט תמיד הדומיין לא מאומת ב-Resend. `/status` מציג `fromDomainVerified`.

**האתר לא מתעדכן** — לבדוק שהפריסה ב-Cloudflare באמת עברה, ולוודא מול `?nocache=` איזו גרסה מוגשת. אל תניח שזה מטמון בדפדפן לפני שווידאת.

## הגדרות שצריך לשמור עליהן

**Cloudflare Pages** — Build command `bash scripts/build-site.sh`, Build output directory `dist`. בלי זה מוגש כל הריפו.

**GoDaddy DNS** — הרשומה `parasha` היא CNAME. **אסור** ליצור רשומה כלשהי שנגמרת ב-`.parasha` — DNS אוסר על רשומות-בת מתחת ל-CNAME, וזה מפיל את האתר לגמרי. רשומות Resend יושבות על השורש (`send`, `resend._domainkey`, `_dmarc`).
