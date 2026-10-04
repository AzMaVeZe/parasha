#!/usr/bin/env node
/* תמונות שער לפרקי הפודקאסט, בעיצוב הקיים של סדרת "בין הנכתב לנגלה" בספוטיפיי:
 * קרם למעלה (פרשת השבוע, תגית הספר, כותרת, פסוק הפתיחה עם פס זהב), ופאנל כחול
 * למטה (שם הכותב והשנה).
 *
 * כל הטקסט נכתב כאן ב-HTML עם הגופנים של האתר ולא בתוך איור: מודלי תמונה
 * משבשים עברית, וכך הכתיב והניקוד נשארים נכונים.
 *
 * הפסוק והשנה מ-scripts/sheets.mjs. line הוא משפט אופציונלי לפאנל הכחול
 * (משפט מפתח או תמיהה מהדף, או שאלה שנוסחה לפי התוכן) ונכנס רק אחרי אישור
 * של אריאל. בלעדיו הפאנל מציג את שם הסדרה.
 *
 * הרצה:
 *   node scripts/make-covers.mjs                 PNG ב-3000×3000 ל-assets/covers/ (נדרש playwright)
 *   node scripts/make-covers.mjs --dc <תיקייה>   לוחות .dc.html ל-Claude Design
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { SHEETS } from './sheets.mjs';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const BYLINE = 'אריאל ז\'יטניצקי';
const SIZE = 1000;                       // פיקסלים לוגיים; הייצוא מוכפל פי 3

// כרטיס לכל דף שב-js/data.js: דף אחד יכול לשמש שתי פרשות (ויקהל–פקודי), ואז
// הכותרת מחברת את שתיהן והפסוק הוא של הראשונה. LINES — המשפט לפאנל הכחול,
// לפי שם הקובץ; נכנס רק אחרי שאריאל אישר אותו.
const LINES = {};
const ctx = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, 'js/data.js'), 'utf8'), ctx);
const COVERS = [];
for (const sefer of ctx.window.PARASHA_DATA) {
  for (const p of sefer.parshiot) {
    if (!p.pdf) continue;
    const file = path.basename(p.pdf, '.pdf');
    const seen = COVERS.find(c => c.file === file);
    if (seen) {
      if (sefer.id !== 'chagim' && seen.book === sefer.name) seen.title += '–' + p.name;
      continue;
    }
    COVERS.push({ file, title: p.name.replace(/(?<=[א-ת])"(?=[א-ת])/g, '״'), book: sefer.id === 'chagim' ? '' : sefer.name,
      ...SHEETS[p.name], line: LINES[file] || '' });
  }
}

/* הכרטיס עצמו: סגנון inline בלבד, כדי שיהיה ניתן לעריכה בלוח העיצוב */
const card = c => `<div style="width:${SIZE}px;height:${SIZE}px;box-sizing:border-box;display:flex;flex-direction:column;background:#F7F2E7;font-family:'Assistant',Arial,sans-serif;overflow:hidden">
  <div style="flex:1 1 0;display:flex;flex-direction:column;justify-content:space-between;padding:72px 76px 56px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <div style="font-size:36px;font-weight:700;color:#14294D;letter-spacing:.01em">${c.book ? 'פרשת השבוע' : 'חגים ומועדים'}</div>
${c.book ? `      <div style="font-size:28px;font-weight:600;color:#8F6A10;border:2px solid #B8860B;border-radius:999px;padding:6px 28px">${c.book}</div>` : ''}
    </div>
    <div style="display:flex;flex-direction:column;gap:34px">
      <div style="font-family:'Frank Ruhl Libre',Georgia,serif;font-size:200px;font-weight:900;line-height:1;color:#14294D;white-space:nowrap" data-fit>${c.title}</div>
      ${c.verse ? `<div style="border-inline-start:6px solid #D4A93C;padding-inline-start:24px;font-family:'Frank Ruhl Libre',Georgia,serif;font-size:42px;font-weight:500;line-height:1.35;color:#26241E">${c.verse}</div>` : ''}
    </div>
  </div>
  <div style="flex:0 0 344px;box-sizing:border-box;background:#14294D;padding:60px 76px 56px;display:flex;flex-direction:column;justify-content:flex-end;gap:34px">
    ${c.line
      ? `<div style="font-family:'Frank Ruhl Libre',Georgia,serif;font-size:60px;font-weight:700;line-height:1.28;color:#F7F2E7;text-wrap:balance">${c.line}</div>`
      : `<div style="font-family:'Frank Ruhl Libre',Georgia,serif;font-size:72px;font-weight:900;line-height:1.1;color:#F7F2E7">בין הנכתב לנגלה</div>`}
    <div style="display:flex;align-items:center;gap:18px;font-size:32px">
      <span style="color:#DCE4F0">${BYLINE}</span>
${c.year ? `      <span style="color:#D4A93C">•</span>
      <span style="color:#D4A93C;font-weight:600">${c.year}</span>` : ''}
    </div>
  </div>
</div>`;

/* לוח Design Component: אותו כרטיס, עם הגופנים מ-Google Fonts */
const dc = c => `<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>שער הפרק — ${c.title}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700&family=Frank+Ruhl+Libre:wght@500;700;900&display=swap">
<style>
body{margin:0}
</style>
</helmet>
${card(c)}
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview":{"width":${SIZE},"height":${SIZE}}}'>
class Component extends DCLogic {
  renderVals() { return {}; }
}
</script>
</body>
</html>
`;

const dcIdx = process.argv.indexOf('--dc');
if (dcIdx > -1) {
  const dir = path.resolve(process.argv[dcIdx + 1] || '.');
  fs.mkdirSync(path.join(dir, 'project'), { recursive: true });
  const names = COVERS.map((c, i) => ({ name: (i ? `Cover${i + 1}` : 'Main') + '.dc.html', c }));
  for (const { name, c } of names) fs.writeFileSync(path.join(dir, 'project', name), dc(c));
  console.log(names.map(n => n.name).join('\n'));
} else {
  const { chromium } = await import('playwright');
  const out = path.join(root, 'assets/covers');
  fs.mkdirSync(out, { recursive: true });
  const fonts = pathToFileURL(path.join(root, 'assets/fonts/fonts.css')).href;
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  const ctx = await browser.newContext({ viewport: { width: SIZE, height: SIZE }, deviceScaleFactor: 3 });
  for (const c of COVERS) {
    const p = await ctx.newPage();
    // מקובץ ולא מ-setContent: דף about:blank אינו רשאי לטעון גופנים מ-file://
    const tmp = path.join(os.tmpdir(), 'parasha-cover.html');
    fs.writeFileSync(tmp, `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
      <link rel="stylesheet" href="${fonts}"><style>body{margin:0}</style></head><body>${card(c)}</body></html>`);
    await p.goto(pathToFileURL(tmp).href);
    await p.evaluate(async () => {
      await document.fonts.ready;
      // שם ארוך (אחרי מות–קדושים) מוקטן עד שהוא נכנס בשורה אחת
      for (const el of document.querySelectorAll('[data-fit]')) {
        let size = parseFloat(getComputedStyle(el).fontSize);
        while (el.scrollWidth > el.parentElement.clientWidth && size > 80) el.style.fontSize = (size -= 6) + 'px';
      }
    });
    await p.waitForTimeout(300);
    await p.screenshot({ path: path.join(out, c.file + '.png') });
    await p.close();
    console.log('✓', c.file);
  }
  await browser.close();
}
