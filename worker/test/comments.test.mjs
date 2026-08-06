import mod from '../src/index.js';

// KV מדומה
const store = new Map();
const KV = {
  async get(k, t) { const v = store.get(k); return v === undefined ? null : (t === 'json' ? JSON.parse(v) : v); },
  async put(k, v) { store.set(k, v); },
  async delete(k) { store.delete(k); },
  async list({ prefix }) { return { keys: [...store.keys()].filter(k => k.startsWith(prefix)).map(name => ({ name })) }; },
};
const env = { SUBSCRIBERS: KV, SITE_URL: 'https://parasha.azma.app', WORKER_URL: 'https://w.dev',
  FROM_EMAIL: 'x <p@azma.app>', RESEND_API_KEY: 'test', ADMIN_KEY: 'K', OWNER_EMAIL: 'a@b.com', BRAND: 'בין הנכתב לנגלה' };

const mails = [];
globalThis.fetch = async (url, init) => {
  if (String(url).includes('parashot.json')) return new Response(JSON.stringify({ 'ראה': {}, 'עקב': {} }));
  if (String(url).includes('api.resend.com')) { mails.push(JSON.parse(init.body)); return new Response('{"id":"1"}'); }
  throw new Error('unexpected ' + url);
};
const call = (url, init = {}) => mod.fetch(new Request(url, init), env);
const post = (b, ip = '1.1.1.1') => call('https://w.dev/comments', { method: 'POST', headers: { 'content-type': 'application/json', 'cf-connecting-ip': ip }, body: JSON.stringify(b) });

let fails = 0;
const ok = (label, cond, extra) => { console.log((cond ? '  ok  ' : 'FAIL  ') + label, extra ?? ''); if (!cond) fails++; };

// 1. תגובה תקינה
let r = await post({ parasha: 'ראה', name: 'יעל', email: 'y@x.com', text: 'דף נהדר' });
ok('POST מוצלח', r.status === 200, r.status);
ok('נשלח מייל מודרציה', mails.length === 1);
ok('המייל כולל קישור אישור', /action=approve/.test(mails[0]?.html || ''));
ok('המייל הולך לבעלים', mails[0]?.to?.[0] === 'a@b.com');

// 2. עוד לא מופיעה לציבור
r = await call('https://w.dev/comments?parasha=' + encodeURIComponent('ראה'));
ok('לפני אישור — רשימה ריקה', JSON.stringify(await r.json()) === '[]');

// 3. פרשה שאינה קיימת
ok('פרשה לא מוכרת נדחית', (await post({ parasha: 'לא קיימת', text: 'x' }, '2.2.2.2')).status === 400);
// 4. honeypot
r = await post({ parasha: 'ראה', text: 'spam', website: 'bot' }, '3.3.3.3');
ok('honeypot מחזיר ok בלי לשמור', r.status === 200 && mails.length === 1);
// 5. ריק / ארוך מדי / מייל פסול
ok('טקסט ריק נדחה', (await post({ parasha: 'ראה', text: '  ' }, '4.4.4.4')).status === 400);
ok('טקסט ארוך נדחה', (await post({ parasha: 'ראה', text: 'x'.repeat(2001) }, '5.5.5.5')).status === 400);
ok('מייל פסול נדחה', (await post({ parasha: 'ראה', text: 'x', email: 'nope' }, '6.6.6.6')).status === 400);
// 6. הגבלת קצב
const ip = '9.9.9.9';
for (let i = 0; i < 3; i++) await post({ parasha: 'עקב', text: 'c' + i }, ip);
ok('התגובה הרביעית נחסמת', (await post({ parasha: 'עקב', text: 'c4' }, ip)).status === 429);

// 7. אישור
const id = JSON.parse(store.get([...store.keys()].find(k => k.startsWith('cpend:') && JSON.parse(store.get(k)).name === 'יעל'))).id;
r = await call(`https://w.dev/moderate?id=${id}&action=approve&key=K`);
ok('אישור מחזיר דף', r.status === 200);
r = await call('https://w.dev/comments?parasha=' + encodeURIComponent('ראה'));
const pub = await r.json();
ok('התגובה מופיעה אחרי אישור', pub.length === 1 && pub[0].text === 'דף נהדר');
ok('המייל לא נשלח לדפדפן', !JSON.stringify(pub).includes('y@x.com') && pub[0].email === undefined, JSON.stringify(pub));
ok('המזהה לא נשלח לדפדפן', pub[0].id === undefined);
r = await call('https://w.dev/comments');
ok('מונה הכרטיסים מתעדכן', (await r.json())['ראה'] === 1);
ok('הממתינה נמחקה', !store.has('cpend:' + id));
ok('אישור כפול לא מכפיל', (await call(`https://w.dev/moderate?id=${id}&action=approve&key=K`)).status === 200
  && JSON.parse(store.get('capp:ראה')).length === 1);

// 8. הרשאות
ok('/moderate בלי מפתח נחסם', /אין הרשאה/.test(await (await call(`https://w.dev/moderate?id=${id}&action=approve`)).text()));
ok('/admin בלי מפתח נחסם', /אין הרשאה/.test(await (await call('https://w.dev/admin')).text()));
const admin = await (await call('https://w.dev/admin?key=K')).text();
ok('/admin מציג ממתינות ומפורסמות', admin.includes('ממתינות לאישור') && admin.includes('דף נהדר'));
ok('/admin חסום למנועי חיפוש', admin.includes('noindex'));

// 8ב. מפתח ניהול שנשמר עם רווח/שורה בסוף עדיין עובד
{
  const envWs = { ...env, ADMIN_KEY: 'K\n' };
  const r2 = await mod.fetch(new Request('https://w.dev/admin?key=K'), envWs);
  ok('מפתח עם ירידת שורה עדיין מאמת', !/אין הרשאה/.test(await r2.text()));
  const r3 = await mod.fetch(new Request('https://w.dev/status?key=%20K%20'), envWs);
  ok('גם המפתח שנשלח נגזם', r3.status === 200, r3.status);
  const r4 = await mod.fetch(new Request('https://w.dev/status?key=wrong'), envWs);
  ok('/status מדווח שהסוד מוגדר', (await r4.json()).adminKeyConfigured === true);
  const r5 = await mod.fetch(new Request('https://w.dev/status?key=x'), { ...env, ADMIN_KEY: '' });
  ok('/status מדווח שהסוד חסר', (await r5.json()).adminKeyConfigured === false);
}

// 9. הסרה
await call(`https://w.dev/moderate?id=${id}&action=delete&parasha=${encodeURIComponent('ראה')}&key=K`);
ok('הסרה מנקה את הרשימה', JSON.parse(store.get('capp:ראה')).length === 0);
ok('הסרה מנקה את המונה', JSON.parse(store.get('cindex'))['ראה'] === undefined);

console.log(fails ? `\n${fails} כשלונות` : '\nכל הבדיקות עברו');
process.exit(fails ? 1 : 0);
