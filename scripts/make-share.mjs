#!/usr/bin/env node
/* תמונות השיתוף (og:image) — מה שווטסאפ, פייסבוק וטלגרם מציגים כששולחים קישור.
 *
 *   assets/og-image.png       לאתר כולו (דף הבית, /p/, עמודים בלי תמונה משלהם)
 *   assets/share/<שם>.jpg     לכל פרשה וחג, לפי slug של העמוד (/p/<שם>/)
 *
 * 1200×630, היחס שווטסאפ מציג כתמונה גדולה. העיצוב של כרטיסי הפודקאסט
 * (scripts/make-covers.mjs) בפריסה רוחבית: קרם מימין עם שם הפרשה, פסוק הפתיחה
 * והשנה; פאנל כחול משמאל ובו העמוד הראשון של הדף עצמו (assets/previews).
 *
 * הרצה (נדרש playwright):  node scripts/make-share.mjs
 * אחרי הוספת כרטיס ב-make-covers.mjs או דף חדש — להריץ שוב ולבנות.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { SHEETS } from './sheets.mjs';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const W = 1200, H = 630;
const BRAND = 'בין הנכתב לנגלה';
const BYLINE = 'אריאל ז\'יטניצקי';
const NAVY = '#14294D', CREAM = '#F7F2E7', GOLD = '#D4A93C', GOLD_TEXT = '#8F6A10';

// אותו slug כמו ב-scripts/build-pages.js וב-js/site.js
const slug = name => name.replace(/["'׳״]/g, '').replace(/\s+/g, '-');
const fileUrl = rel => pathToFileURL(path.join(root, rel)).href;

const ctx = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, 'js/data.js'), 'utf8'), ctx);
const pages = [];
for (const sefer of ctx.window.PARASHA_DATA) {
  for (const p of sefer.parshiot) {
    const stem = p.pdf ? path.basename(p.pdf, '.pdf') : null;
    const preview = stem && fs.existsSync(path.join(root, 'assets/previews', stem + '.jpg'))
      ? 'assets/previews/' + stem + '.jpg' : null;
    pages.push({
      name: p.name, book: sefer.name, preview,
      chag: sefer.id === 'chagim',
      ...(SHEETS[p.name] || {}),
    });
  }
}

const serif = "font-family:'Frank Ruhl Libre',Georgia,serif";

/* דף הנייר: העמוד הראשון של הדף, נוטה מעט ונחתך בתחתית הפאנל */
const sheet = (src, w, rot, extra = '') =>
  `<img src="${fileUrl(src)}" style="width:${w}px;display:block;border-radius:4px;transform:rotate(${rot}deg);box-shadow:0 18px 40px rgba(0,0,0,.35);${extra}">`;

const shell = (start, end) => `<div style="width:${W}px;height:${H}px;display:flex;background:${CREAM};font-family:'Assistant',Arial,sans-serif;overflow:hidden">
  <div style="flex:1 1 0;min-width:0;box-sizing:border-box;padding:54px 64px 50px;display:flex;flex-direction:column;justify-content:space-between">${start}</div>
  <div style="flex:0 0 470px;box-sizing:border-box;background:${NAVY};position:relative;overflow:hidden">${end}</div>
</div>`;

const topRow = (left, right) => `<div style="display:flex;justify-content:space-between;align-items:center;gap:20px">
  <div style="font-size:27px;font-weight:700;color:${NAVY}">${left}</div>
${right ? `  <div style="font-size:22px;font-weight:600;color:${GOLD_TEXT};border:2px solid #B8860B;border-radius:999px;padding:4px 22px;white-space:nowrap">${right}</div>` : ''}
</div>`;

const bottomRow = year => `<div style="display:flex;align-items:center;gap:14px;font-size:25px">
  <span style="color:${NAVY};font-weight:600">${BYLINE}</span>${year ? `
  <span style="color:${GOLD}">•</span><span style="color:${GOLD_TEXT};font-weight:600">${year}</span>` : ''}
  <span style="margin-right:auto;color:#6B6758;font-size:21px;direction:ltr">parasha.azma.app</span>
</div>`;

function pageCard(pg) {
  // בחג השם של "הספר" הוא "חגים ומועדים" — כותרת, בלי תגית שחוזרת עליה
  const start = `${pg.chag ? topRow(pg.book, '') : topRow('פרשת השבוע', pg.book)}
  <div style="display:flex;flex-direction:column;gap:22px">
    <div data-fit style="${serif};font-size:150px;font-weight:900;line-height:1;color:${NAVY};white-space:nowrap">${pg.name}</div>${pg.verse ? `
    <div style="border-inline-start:5px solid ${GOLD};padding-inline-start:20px;${serif};font-size:32px;font-weight:500;line-height:1.35;color:#26241E">${pg.verse}</div>` : `
    <div style="font-size:30px;color:#4A4636">${BRAND} — ${pg.chag ? 'דף לשולחן החג' : 'דף לשולחן שבת'}</div>`}
  </div>
  ${bottomRow(pg.year)}`;
  const end = pg.preview
    ? `<div style="position:absolute;top:58px;inset-inline:0;display:flex;justify-content:center">${sheet(pg.preview, 340, -2.5)}</div>`
    : `<div style="position:absolute;inset:0;display:flex;align-items:center;padding:52px;${serif};font-size:58px;font-weight:900;line-height:1.15;color:${CREAM}">${BRAND}</div>`;
  return shell(start, end);
}

function siteCard() {
  const fan = ['bereshit-בראשית', 'shmot-שמות', 'devarim-שופטים']
    .map(s => 'assets/previews/' + s + '.jpg').filter(p => fs.existsSync(path.join(root, p)));
  const pos = [
    'top:96px;right:150px;z-index:1', 'top:70px;right:70px;z-index:2', 'top:44px;right:-10px;z-index:3'];
  const rot = [6, 1, -4];
  const start = `${topRow('לק"י', 'פרשת השבוע')}
  <div style="display:flex;flex-direction:column;gap:20px">
    <div style="${serif};font-size:96px;font-weight:900;line-height:1.05;color:${NAVY}">${BRAND}</div>
    <div style="border-inline-start:5px solid ${GOLD};padding-inline-start:20px;font-size:30px;line-height:1.4;color:#26241E">דפי פרשת השבוע והחגים — לצפייה, להורדה, להדפסה לשולחן שבת ולהאזנה</div>
  </div>
  ${bottomRow('')}`;
  const end = fan.map((p, i) => `<div style="position:absolute;${pos[i]}">${sheet(p, 300, rot[i])}</div>`).join('');
  return shell(start, end);
}

const { chromium } = await import('playwright');
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
const page = await browser.newPage({ viewport: { width: W, height: H } });
const tmp = path.join(os.tmpdir(), 'parasha-share.html');
const fonts = fileUrl('assets/fonts/fonts.css');

async function shoot(html, out, type) {
  // מקובץ ולא מ-setContent: דף about:blank אינו רשאי לטעון קבצים מ-file://
  fs.writeFileSync(tmp, `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
    <link rel="stylesheet" href="${fonts}"><style>body{margin:0}</style></head><body>${html}</body></html>`);
  await page.goto(pathToFileURL(tmp).href);
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(i => i.decode().catch(() => {})));
    // שם ארוך (שמחת תורה, ט"ו באב) מוקטן עד שהוא נכנס בשורה אחת
    for (const el of document.querySelectorAll('[data-fit]')) {
      let size = parseFloat(getComputedStyle(el).fontSize);
      while (el.scrollWidth > el.parentElement.clientWidth && size > 60) el.style.fontSize = (size -= 4) + 'px';
    }
  });
  await page.screenshot(type === 'png' ? { path: out } : { path: out, type: 'jpeg', quality: 86 });
  const kb = Math.round(fs.statSync(out).size / 1024);
  console.log('✓', path.relative(root, out), kb + 'KB');
}

fs.mkdirSync(path.join(root, 'assets/share'), { recursive: true });
await shoot(siteCard(), path.join(root, 'assets/og-image.png'), 'png');
for (const pg of pages) await shoot(pageCard(pg), path.join(root, 'assets/share', slug(pg.name) + '.jpg'), 'jpeg');
await browser.close();
