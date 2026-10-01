#!/usr/bin/env node
/* מרכיב תמונות שער (1200×630, הגודל של og:image) מאיור + כותרת בגופני האתר.
 *
 * האיורים נוצרים בנפרד, בלי שום כיתוב — מודלי תמונה משבשים עברית. הכותרת
 * נכתבת כאן ב-HTML עם הגופנים המתארחים של האתר, ולכן הניקוד והכתיב תקינים.
 *
 *   איור גולמי:   scripts/cover-art/<שם-קובץ>.jpg   (16:9, מומלץ 2K)
 *   תוצר:         assets/covers/<שם-קובץ>.jpg
 *
 * הרצה:  node scripts/make-covers.mjs        (נדרש playwright)
 *
 * פריסה: האיור ממלא את הרוחב, השליש הימני שלו שקט בכוונה — שם יושבת הכותרת,
 * כי עברית נקראת מימין. מעבר צבע כהה מהצד הימני מבטיח קריאות על כל איור.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');

const COVERS = [
  { file: 'bereshit-בראשית', title: 'בראשית',  kicker: 'ספר בראשית' },
  { file: 'bereshit-נח',     title: 'נח',      kicker: 'ספר בראשית' },
];

const page = c => `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<link rel="stylesheet" href="${pathToFileURL(path.join(root, 'assets/fonts/fonts.css'))}">
<style>
*{box-sizing:border-box;margin:0}
body{width:1200px;height:630px;overflow:hidden;position:relative;background:#14294D;
  font-family:'Assistant',Arial,sans-serif;color:#F7F2E7}
.art{position:absolute;inset:0;background:url('${pathToFileURL(path.join(root, 'scripts/cover-art', c.file + '.jpg'))}') center/cover no-repeat}
/* מעבר מהצד הימני, באותו כחול של האתר — מבטיח שהכותרת קריאה */
.shade{position:absolute;inset:0;
  background:linear-gradient(270deg,#14294D 0%,rgba(20,41,77,.92) 24%,rgba(20,41,77,.55) 46%,rgba(20,41,77,0) 70%)}
.text{position:absolute;top:0;bottom:0;right:84px;width:430px;display:flex;flex-direction:column;
  justify-content:center;align-items:flex-start;gap:14px}
.laky{font-weight:600;font-size:26px;letter-spacing:.06em;color:#D4A93C}
.kicker{font-size:26px;color:#D4A93C;letter-spacing:.04em}
h1{font-family:'Frank Ruhl Libre',Georgia,serif;font-weight:900;font-size:128px;line-height:1.02;color:#F7F2E7}
.rule{width:150px;height:3px;background:#B8860B;margin-block:6px}
.by{font-size:30px;color:#F7F2E7}
.site{font-size:22px;color:#DCE4F0;opacity:.85}
</style></head><body>
<div class="art"></div><div class="shade"></div>
<div class="text">
  <div class="laky">לק"י</div>
  <div class="kicker">פרשת השבוע · ${c.kicker}</div>
  <h1>${c.title}</h1>
  <div class="rule"></div>
  <div class="by">אריאל ז'יטניצקי</div>
  <div class="site">בין הנכתב לנגלה</div>
</div>
</body></html>`;

fs.mkdirSync(path.join(root, 'assets/covers'), { recursive: true });
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
const ctx = await browser.newContext({ viewport: { width: 1200, height: 630 } });
for (const c of COVERS) {
  const art = path.join(root, 'scripts/cover-art', c.file + '.jpg');
  if (!fs.existsSync(art)) { console.log('חסר איור, מדלג:', c.file); continue; }
  const p = await ctx.newPage();
  const tmp = path.join(root, 'scripts/cover-art', '.compose.html');
  fs.writeFileSync(tmp, page(c));
  await p.goto(pathToFileURL(tmp).href);
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(400);
  await p.screenshot({ path: path.join(root, 'assets/covers', c.file + '.jpg'), type: 'jpeg', quality: 88 });
  fs.unlinkSync(tmp);
  await p.close();
  console.log('✓', c.file);
}
await browser.close();
