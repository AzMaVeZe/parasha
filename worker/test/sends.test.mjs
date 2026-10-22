import mod from '../src/index.js';

// בדיקת יומן השליחות: כל שליחה נשמרת ב-log:sends ומוצגת ב-/status
const store = new Map();
const KV = {
  async get(k, t) { const v = store.get(k); return v === undefined ? null : (t === 'json' ? JSON.parse(v) : v); },
  async put(k, v) { store.set(k, v); },
  async delete(k) { store.delete(k); },
  async list({ prefix }) { return { keys: [...store.keys()].filter(k => k.startsWith(prefix)).map(name => ({ name })) }; },
};
const env = { SUBSCRIBERS: KV, SITE_URL: 'https://parasha.azma.app', WORKER_URL: 'https://w.dev',
  FROM_EMAIL: 'x <p@azma.app>', RESEND_API_KEY: 'test', ADMIN_KEY: 'K', BRAND: 'בין הנכתב לנגלה' };

let hebcalDown = false;
const mails = [];
globalThis.fetch = async (url, init) => {
  url = String(url);
  if (url.includes('parashot.json')) return new Response(JSON.stringify({ 'נח': { hasPdf: true } }));
  if (url.includes('hebcal.com')) {
    if (hebcalDown) throw new Error('hebcal unreachable');
    return new Response(JSON.stringify({ items: [{ category: 'parashat', hebrew: 'פרשת נח', date: '2026-10-24' }] }));
  }
  if (url.includes('api.resend.com/emails')) {
    const body = JSON.parse(init.body);
    if (body.to[0].startsWith('bad')) return new Response('{"message":"invalid"}', { status: 422 });
    mails.push(body); return new Response('{"id":"1"}');
  }
  if (url.includes('api.resend.com/domains')) return new Response('{"data":[]}');
  throw new Error('unexpected ' + url);
};

const sub = (email, day, status = 'active') =>
  store.set('sub:' + email, JSON.stringify({ email, day, status, token: 't-' + email }));
sub('yael@example.com', 'thu');
sub('bad@example.com', 'thu');
sub('dan@example.com', 'mon');
sub('new@example.com', 'thu', 'pending');

let fails = 0;
const ok = (label, cond, extra) => { console.log((cond ? '  ok  ' : 'FAIL  ') + label, extra ?? ''); if (!cond) fails++; };

// 1. שליחה מתוזמנת ביום חמישי (2026-10-22 04:00 UTC)
const waits = [];
await mod.scheduled({ scheduledTime: Date.UTC(2026, 9, 22, 4) }, env, { waitUntil: p => waits.push(p) });
await Promise.all(waits);
let log = JSON.parse(store.get('log:sends') || '[]');
ok('השליחה נרשמה', log.length === 1);
ok('נשלח לנרשם של יום חמישי', log[0]?.sent === 1 && mails.length === 1, JSON.stringify(log[0]));
ok('הכישלון נספר עם סיבה', log[0]?.failed === 1 && /invalid|422/.test(log[0]?.errors?.[0]?.error || ''));
ok('כתובת שנכשלה מוסתרת', log[0]?.errors?.[0]?.to === 'ba***@example.com');
ok('נספרו נרשמים של יום אחר ושלא אישרו', log[0]?.otherDay === 1 && log[0]?.notActive === 1);
ok('רשום הדף שנשלח', log[0]?.sheets?.[0] === 'נח');
ok('רשום שזו שליחה מתוזמנת', log[0]?.trigger === 'cron' && log[0]?.day === 'thu');

// 2. תקלה בדרך (Hebcal לא זמין) — גם היא נרשמת, במקום להיעלם
hebcalDown = true;
const r = await mod.fetch(new Request('https://w.dev/send?day=thu&key=K'), env);
ok('/send מחזיר את התוצאה', r.status === 200);
log = JSON.parse(store.get('log:sends'));
ok('תקלה נרשמת עם השגיאה', log[0]?.error === 'hebcal unreachable' && log[0]?.trigger === 'manual');
ok('הרשומה החדשה ראשונה', log.length === 2);

// 3. /status מציג את השליחות האחרונות
const st = await (await mod.fetch(new Request('https://w.dev/status?key=K'), env)).json();
ok('/status כולל את השליחות', Array.isArray(st.sends) && st.sends.length === 2);
ok('אין כתובת מלאה ב-/status', !JSON.stringify(st).includes('yael@example.com'));

// 4. היומן מוגבל ל-30 רשומות
for (let i = 0; i < 35; i++) await mod.fetch(new Request('https://w.dev/send?day=mon&key=K'), env);
ok('נשמרות 30 אחרונות בלבד', JSON.parse(store.get('log:sends')).length === 30);

console.log(fails ? `\n${fails} כשלונות` : '\nכל הבדיקות עברו');
process.exit(fails ? 1 : 0);
