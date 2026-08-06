/**
 * בין הנכתב לנגלה — Worker לרשימת התפוצה.
 *
 * אחראי על:
 *  POST /subscribe    — הרשמה (מייל + יום מועדף), שולח מייל אישור (double opt-in)
 *  GET  /confirm      — אישור ההרשמה מתוך המייל
 *  GET  /unsubscribe  — הסרה מהרשימה
 *  cron               — כל יום שני וחמישי: שולח את דף הפרשה הקרובה לנרשמים של אותו יום
 *
 * וגם על התגובות:
 *  POST /comments     — שליחת תגובה; נכנסת כ"ממתינה" ושולחת לאריאל מייל אישור
 *  GET  /comments     — התגובות המאושרות (?parasha=… לדף בודד, בלי פרמטר = מונים לכרטיסים)
 *  GET  /moderate     — אישור/דחייה מתוך המייל (דורש ADMIN_KEY)
 *  GET  /admin        — דף ניהול בעברית לכל התגובות (דורש ADMIN_KEY)
 *
 * סודות (wrangler secret put):  RESEND_API_KEY, ADMIN_KEY
 * משתנים (wrangler.toml vars):  SITE_URL, FROM_EMAIL, REPLY_TO, BRAND, OWNER_EMAIL
 * אחסון:                        KV binding בשם SUBSCRIBERS
 *
 * מפתחות ב-KV:
 *   sub:<email>        — נרשם לרשימת התפוצה
 *   capp:<parasha>     — מערך התגובות המאושרות של פרשה (מה שהאתר קורא)
 *   cpend:<id>         — תגובה בודדת הממתינה לאישור
 *   cindex             — { "<parasha>": <מספר תגובות מאושרות> } למוני הכרטיסים
 * כתובות המייל של המגיבים נשמרות רק ברשומה ובדף הניהול — לעולם לא ב-capp/cindex,
 * כלומר לעולם לא מגיעות לדפדפן של הקוראים.
 */

const DAYS = { mon: 'שני', thu: 'חמישי', fri: 'שישי בבוקר' };
const DAY_OF_WEEK = { 1: 'mon', 4: 'thu', 5: 'fri' };   // getUTCDay -> קוד היום

/* ---------- עזרים ---------- */

const json = (obj, status = 200, origin = '*') =>
  new Response(JSON.stringify(obj), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'access-control-allow-origin': origin,
      'cache-control': 'no-store',
    },
  });

const page = (title, body) =>
  new Response(
    `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title>
<style>body{font-family:system-ui,'Segoe UI',Arial,sans-serif;background:#F7F2E7;color:#26241E;
display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:24px}
.box{background:#fff;border:1px solid #E0D5BC;border-radius:12px;padding:32px 36px;max-width:520px;text-align:center;
box-shadow:0 1px 3px rgba(38,36,30,.07)}h1{color:#14294D;font-size:24px;margin:0 0 12px}
p{line-height:1.7;margin:0 0 16px}a{color:#1B3A6B}</style></head>
<body><div class="box"><h1>${esc(title)}</h1>${body}</div></body></html>`,
    { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' } }
  );

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

const validEmail = e => typeof e === 'string' && e.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e);
const keyFor = email => 'sub:' + email.trim().toLowerCase();

function allowedOrigin(request, env) {
  const site = (env.SITE_URL || '').replace(/\/$/, '');
  try {
    const o = new URL(site).origin;
    return request.headers.get('origin') === o ? o : o;
  } catch { return '*'; }
}

/* ---------- Resend ---------- */

async function sendEmail(env, { to, subject, html, headers }) {
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      authorization: 'Bearer ' + env.RESEND_API_KEY,
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      from: env.FROM_EMAIL,
      to: [to],
      reply_to: env.REPLY_TO || undefined,
      subject,
      html,
      headers,
    }),
  });
  if (!res.ok) throw new Error('resend ' + res.status + ' ' + (await res.text()).slice(0, 200));
  return res.json();
}

/* ---------- תבניות מייל ---------- */

const shell = (env, inner, unsubUrl) => `
<div dir="rtl" style="font-family:'Segoe UI',Arial,sans-serif;background:#F7F2E7;padding:24px">
  <div style="max-width:600px;margin:0 auto;background:#fff;border:1px solid #E0D5BC;border-radius:12px;overflow:hidden">
    <div style="background:#14294D;color:#F7F2E7;padding:18px 24px">
      <div style="font-size:20px;font-weight:700">${esc(env.BRAND || 'בין הנכתב לנגלה')}</div>
      <div style="font-size:13px;color:#D4A93C;margin-top:2px">על פרשת השבוע · מאת אריאל ז'יטניצקי</div>
    </div>
    <div style="padding:24px;color:#26241E;line-height:1.75;font-size:16px">${inner}</div>
    <div style="padding:14px 24px;border-top:1px solid #EFE7D5;font-size:12px;color:#6B675A">
      קיבלת מייל זה כי נרשמת לרשימת התפוצה של ${esc(env.BRAND || 'בין הנכתב לנגלה')}.
      ${unsubUrl ? `<a href="${esc(unsubUrl)}" style="color:#6B675A">להסרה מהרשימה</a>` : ''}
    </div>
  </div>
</div>`;

/* ---------- לוח שנה: הפרשה/החג הקרוב ---------- */

// מסיר ניקוד וטעמים בלבד — בלי מקף עברי (U+05BE), כדי ש"ניצבים־וילך" יישאר מפוצל
const stripNikud = s => (s || '').replace(/[֑-ׇֽֿׁׂׅׄ]/g, '');
const normName = s => stripNikud(s || '').replace(/["'׳״]/g, '')
  .replace(/[־–—-]/g, ' ').replace(/\s+/g, ' ').trim();
const ALIASES = {
  'שפטים': 'שופטים', 'נצבים': 'ניצבים', 'בהעלתך': 'בהעלותך', 'אמר': 'אמור',
  'מצרע': 'מצורע', 'קדשים': 'קדושים', 'בחקתי': 'בחוקותי', 'בהר': 'בהר סיני',
  'סכות': 'סוכות', 'יום כפור': 'יום כיפור', 'שמחת תורה': 'וזאת הברכה', 'הושענא רבא': 'הושענא רבה',
};

function resolveName(hebrew, index) {
  const base = stripNikud(hebrew).replace(/^פרשת\s+/, '').trim();
  const candidates = [normName(base), ...base.split(/[־–—-]/).map(normName)];
  const byNorm = new Map(Object.keys(index).map(n => [normName(n), n]));
  for (const c of candidates) {
    const key = ALIASES[c] ? normName(ALIASES[c]) : c;
    if (byNorm.has(key)) return byNorm.get(key);
  }
  return null;
}

async function upcoming(env) {
  const index = await (await fetch(env.SITE_URL.replace(/\/$/, '') + '/assets/parashot.json')).json();
  const iso = d => d.toISOString().slice(0, 10);
  const today = iso(new Date());
  const end = iso(new Date(Date.now() + 15 * 864e5));
  const j = await (await fetch(
    `https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&s=on&il=on&start=${today}&end=${end}`)).json();

  const items = (j.items || []).filter(i =>
    (i.category === 'parashat' || i.category === 'holiday') && !stripNikud(i.hebrew).startsWith('ערב '));
  const par = items.find(i => i.category === 'parashat');
  const hol = items.find(i => i.category === 'holiday' && (!par || i.date <= par.date));

  const picks = [];
  if (hol) {
    const n = resolveName(hol.hebrew, index);
    if (n && index[n].hasPdf) picks.push({ name: n, date: hol.date, kind: 'החג הקרוב', meta: index[n] });
  }
  if (par) {
    const n = resolveName(par.hebrew, index);
    if (n && index[n].hasPdf && !picks.some(p => p.name === n)) {
      picks.push({ name: n, date: par.date, kind: 'פרשת השבוע', meta: index[n] });
    }
  }
  return picks;
}

/* ---------- שליחה מתוזמנת ---------- */

async function sendWeekly(env, day) {
  const picks = await upcoming(env);
  if (!picks.length) return { sent: 0, reason: 'no sheet for the upcoming date' };

  const site = env.SITE_URL.replace(/\/$/, '');
  const blocks = picks.map(p => {
    const title = p.meta.isChag ? p.name : 'פרשת ' + p.name;
    const url = site + '/#p=' + encodeURIComponent(p.name);
    return `
      <div style="border:1px solid #EFE7D5;border-radius:10px;padding:16px 18px;margin-bottom:14px">
        <div style="font-size:13px;color:#8F6A10;font-weight:600">${esc(p.kind)}</div>
        <div style="font-size:21px;font-weight:700;color:#14294D;margin:2px 0 10px">${esc(title)}</div>
        <a href="${esc(url)}" style="display:inline-block;background:#1B3A6B;color:#fff;text-decoration:none;
           padding:10px 20px;border-radius:6px;font-weight:600">לדף ולהורדה</a>
        ${p.meta.hasPodcast
          ? `<a href="${esc(url)}" style="display:inline-block;margin-inline-start:8px;color:#1DB954;
               text-decoration:none;padding:10px 4px;font-weight:600">🎧 להאזנה לפודקאסט</a>`
          : ''}
      </div>`;
  }).join('');

  const list = await env.SUBSCRIBERS.list({ prefix: 'sub:' });
  let sent = 0, failed = 0;
  for (const k of list.keys) {
    const rec = await env.SUBSCRIBERS.get(k.name, 'json');
    if (!rec || rec.status !== 'active' || rec.day !== day) continue;
    const unsub = `${(env.WORKER_URL || '').replace(/\/$/, '')}/unsubscribe?token=${encodeURIComponent(rec.token)}`;
    try {
      await sendEmail(env, {
        to: rec.email,
        subject: picks.map(p => (p.meta.isChag ? p.name : 'פרשת ' + p.name)).join(' · ') + ' — בין הנכתב לנגלה',
        html: shell(env, `<p>שבוע טוב,</p>${blocks}<p style="margin-top:18px">שבת שלום,<br>אריאל</p>`, unsub),
        headers: unsub ? { 'List-Unsubscribe': `<${unsub}>`, 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click' } : undefined,
      });
      sent++;
    } catch (e) {
      failed++;
      console.error('send failed', rec.email, e.message);
    }
  }
  return { sent, failed, sheets: picks.map(p => p.name) };
}

/* ---------- תגובות ---------- */

const APPROVED_KEY = name => 'capp:' + name;
const PENDING_KEY = id => 'cpend:' + id;
const INDEX_KEY = 'cindex';
const MAX_COMMENT = 2000;
const MAX_NAME = 60;

const ownerEmail = env => (env.OWNER_EMAIL || '').trim();

// wrangler secret put שומר לפעמים רווח או ירידת שורה בסוף הערך שהודבק, ואז
// ההשוואה נכשלת בלי סימן. משווים גזום משני הצדדים.
const adminKey = env => (env.ADMIN_KEY || '').trim();
const adminOk = (url, env) => {
  const k = adminKey(env);
  return !!k && (url.searchParams.get('key') || '').trim() === k;
};

// מה שנשלח לדפדפן — בלי מייל, בלי מזהה, בלי כתובת IP
const publicComment = c => ({ name: c.name, text: c.text, date: c.date });

async function readIndex(env) {
  return (await env.SUBSCRIBERS.get(INDEX_KEY, 'json')) || {};
}

async function approveComment(env, rec) {
  const list = (await env.SUBSCRIBERS.get(APPROVED_KEY(rec.parasha), 'json')) || [];
  if (list.some(c => c.id === rec.id)) return list.length;          // אישור כפול — לא מכפילים
  list.push({ id: rec.id, name: rec.name, text: rec.text, date: rec.date });
  await env.SUBSCRIBERS.put(APPROVED_KEY(rec.parasha), JSON.stringify(list));
  const index = await readIndex(env);
  index[rec.parasha] = list.length;
  await env.SUBSCRIBERS.put(INDEX_KEY, JSON.stringify(index));
  await env.SUBSCRIBERS.delete(PENDING_KEY(rec.id));
  return list.length;
}

async function deleteApproved(env, parasha, id) {
  const list = (await env.SUBSCRIBERS.get(APPROVED_KEY(parasha), 'json')) || [];
  const next = list.filter(c => c.id !== id);
  await env.SUBSCRIBERS.put(APPROVED_KEY(parasha), JSON.stringify(next));
  const index = await readIndex(env);
  if (next.length) index[parasha] = next.length; else delete index[parasha];
  await env.SUBSCRIBERS.put(INDEX_KEY, JSON.stringify(index));
}

async function listPending(env) {
  const out = [];
  const list = await env.SUBSCRIBERS.list({ prefix: 'cpend:' });
  for (const k of list.keys) {
    const rec = await env.SUBSCRIBERS.get(k.name, 'json');
    if (rec) out.push(rec);
  }
  out.sort((a, b) => (a.date < b.date ? 1 : -1));
  return out;
}

/* ---------- Worker ---------- */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = allowedOrigin(request, env);
    const site = (env.SITE_URL || '').replace(/\/$/, '');

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'access-control-allow-origin': origin,
          'access-control-allow-methods': 'POST, GET, OPTIONS',
          'access-control-allow-headers': 'content-type',
          'access-control-max-age': '86400',
        },
      });
    }

    /* --- הרשמה --- */
    if (url.pathname === '/subscribe' && request.method === 'POST') {
      let body;
      try { body = await request.json(); } catch { return json({ error: 'bad json' }, 400, origin); }
      const email = (body.email || '').trim().toLowerCase();
      const day = DAYS[body.day] ? body.day : null;
      if (body.website) return json({ ok: true }, 200, origin);        // honeypot — בוטים
      if (!validEmail(email)) return json({ error: 'invalid_email' }, 400, origin);
      if (!day) return json({ error: 'invalid_day' }, 400, origin);

      const key = keyFor(email);
      const existing = await env.SUBSCRIBERS.get(key, 'json');
      if (existing && existing.status === 'active') {
        if (existing.day !== day) {
          await env.SUBSCRIBERS.put(key, JSON.stringify({ ...existing, day }));
          return json({ ok: true, state: 'updated' }, 200, origin);
        }
        return json({ ok: true, state: 'already' }, 200, origin);
      }

      const token = crypto.randomUUID();
      // רשומה ממתינה נמחקת מעצמה אחרי 30 יום אם לא אושרה
      await env.SUBSCRIBERS.put(key, JSON.stringify({
        email, day, token, status: 'pending', createdAt: new Date().toISOString(),
      }), { expirationTtl: 60 * 60 * 24 * 30 });

      const confirmUrl = `${env.WORKER_URL}/confirm?token=${encodeURIComponent(token)}&e=${encodeURIComponent(email)}`;
      try {
        await sendEmail(env, {
          to: email,
          subject: 'אישור הרשמה — בין הנכתב לנגלה',
          html: shell(env, `
            <p>שלום,</p>
            <p>ביקשת לקבל את דף פרשת השבוע בכל יום <strong>${DAYS[day]}</strong>.</p>
            <p>לאישור ההרשמה יש ללחוץ על הכפתור:</p>
            <p><a href="${esc(confirmUrl)}" style="display:inline-block;background:#8F6A10;color:#fff;
               text-decoration:none;padding:11px 22px;border-radius:6px;font-weight:600">אישור ההרשמה</a></p>
            <p style="font-size:14px;color:#6B675A">אם לא ביקשת להירשם — אפשר פשוט להתעלם מהמייל הזה.</p>`),
        });
      } catch (e) {
        // ההרשמה נשמרה כ"ממתינה", אבל מייל האישור נכשל — מדווחים במפורש כדי שיהיה מה לאבחן
        console.error('confirm mail failed', e.message);
        return json({ error: 'mail_failed', detail: e.message.slice(0, 300) }, 502, origin);
      }
      return json({ ok: true, state: 'pending' }, 200, origin);
    }

    /* --- אישור --- */
    if (url.pathname === '/confirm') {
      const token = url.searchParams.get('token');
      const email = (url.searchParams.get('e') || '').trim().toLowerCase();
      const rec = email ? await env.SUBSCRIBERS.get(keyFor(email), 'json') : null;
      if (!rec || !token || rec.token !== token) {
        return page('הקישור אינו תקף', '<p>ייתכן שהקישור פג או שכבר נעשה בו שימוש. אפשר להירשם שוב מהאתר.</p>'
          + (site ? `<p><a href="${esc(site)}">לאתר</a></p>` : ''));
      }
      await env.SUBSCRIBERS.put(keyFor(email), JSON.stringify({ ...rec, status: 'active', confirmedAt: new Date().toISOString() }));
      return page('ההרשמה אושרה', `<p>מעכשיו תקבלו את דף פרשת השבוע בכל יום <strong>${DAYS[rec.day]}</strong>.</p>`
        + (site ? `<p><a href="${esc(site)}">לאתר</a></p>` : ''));
    }

    /* --- הסרה --- */
    if (url.pathname === '/unsubscribe') {
      const token = url.searchParams.get('token');
      if (token) {
        const list = await env.SUBSCRIBERS.list({ prefix: 'sub:' });
        for (const k of list.keys) {
          const rec = await env.SUBSCRIBERS.get(k.name, 'json');
          if (rec && rec.token === token) {
            await env.SUBSCRIBERS.delete(k.name);
            break;
          }
        }
      }
      if (request.method === 'POST') return new Response('ok');   // List-Unsubscribe One-Click
      return page('הוסרת מהרשימה', '<p>לא יישלחו אליך עוד מיילים. תודה, ומוזמן/ת תמיד לחזור.</p>'
        + (site ? `<p><a href="${esc(site)}">לאתר</a></p>` : ''));
    }

    /* --- תגובות: קריאה --- */
    // ?parasha=<שם>  → מערך התגובות המאושרות של אותה פרשה
    // בלי פרמטר      → מפת מונים { "<פרשה>": <מספר> } למוני הכרטיסים בארכיון
    if (url.pathname === '/comments' && request.method === 'GET') {
      const name = (url.searchParams.get('parasha') || '').trim();
      const headers = {
        'content-type': 'application/json; charset=utf-8',
        'access-control-allow-origin': origin,
        // דקה של מטמון — תגובה מאושרת מופיעה כמעט מיד, בלי להעיר את ה-Worker בכל טעינה
        'cache-control': 'public, max-age=60',
      };
      if (!name) {
        return new Response(JSON.stringify(await readIndex(env)), { headers });
      }
      const list = (await env.SUBSCRIBERS.get(APPROVED_KEY(name), 'json')) || [];
      return new Response(JSON.stringify(list.map(publicComment)), { headers });
    }

    /* --- תגובות: שליחה --- */
    if (url.pathname === '/comments' && request.method === 'POST') {
      let body;
      try { body = await request.json(); } catch { return json({ error: 'bad json' }, 400, origin); }
      if (body.website) return json({ ok: true, state: 'pending' }, 200, origin);   // honeypot

      const parasha = (body.parasha || '').trim();
      const name = (body.name || '').trim().slice(0, MAX_NAME) || 'אנונימי';
      const email = (body.email || '').trim().toLowerCase();
      const text = (body.text || '').trim();

      if (!text) return json({ error: 'empty' }, 400, origin);
      if (text.length > MAX_COMMENT) return json({ error: 'too_long' }, 400, origin);
      if (email && !validEmail(email)) return json({ error: 'invalid_email' }, 400, origin);

      // הפרשה חייבת להיות אחת מאלה שבאתר — אחרת אפשר להציף את ה-KV במפתחות שרירותיים
      let index;
      try {
        index = await (await fetch(site + '/assets/parashot.json', { cf: { cacheTtl: 3600 } })).json();
      } catch { return json({ error: 'unavailable' }, 503, origin); }
      if (!Object.prototype.hasOwnProperty.call(index, parasha)) {
        return json({ error: 'unknown_parasha' }, 400, origin);
      }

      // הגבלת קצב: 3 תגובות לכתובת IP בחמש דקות
      const ip = request.headers.get('cf-connecting-ip') || 'unknown';
      const rateKey = 'crate:' + ip;
      const hits = Number(await env.SUBSCRIBERS.get(rateKey)) || 0;
      if (hits >= 3) return json({ error: 'rate_limited' }, 429, origin);
      await env.SUBSCRIBERS.put(rateKey, String(hits + 1), { expirationTtl: 300 });

      const id = crypto.randomUUID();
      const rec = { id, parasha, name, email, text, date: new Date().toISOString() };
      // ממתינה שלא אושרה נמחקת מעצמה אחרי 90 יום
      await env.SUBSCRIBERS.put(PENDING_KEY(id), JSON.stringify(rec), { expirationTtl: 60 * 60 * 24 * 90 });

      // מייל אישור לאריאל — כישלון שליחה לא מפיל את התגובה, היא כבר שמורה
      const owner = ownerEmail(env);
      if (owner && adminKey(env)) {
        const link = a => `${env.WORKER_URL}/moderate?id=${encodeURIComponent(id)}&action=${a}&key=${encodeURIComponent(adminKey(env))}`;
        try {
          await sendEmail(env, {
            to: owner,
            subject: 'תגובה חדשה ממתינה לאישור — ' + parasha,
            html: shell(env, `
              <p><strong>${esc(name)}</strong> כתב/ה תגובה על <strong>${esc(parasha)}</strong>:</p>
              <blockquote style="margin:0 0 16px;padding:12px 16px;background:#F7F2E7;border-inline-start:3px solid #D4A93C;
                border-radius:6px;white-space:pre-wrap">${esc(text)}</blockquote>
              ${email ? `<p style="font-size:14px;color:#6B675A">מייל ליצירת קשר: ${esc(email)}</p>` : ''}
              <p>
                <a href="${esc(link('approve'))}" style="display:inline-block;background:#2E6B3E;color:#fff;
                   text-decoration:none;padding:11px 22px;border-radius:6px;font-weight:600">אישור ופרסום</a>
                &nbsp;
                <a href="${esc(link('reject'))}" style="display:inline-block;background:#fff;color:#8A2B2B;
                   border:1px solid #8A2B2B;text-decoration:none;padding:10px 20px;border-radius:6px">דחייה</a>
              </p>
              <p style="font-size:14px;color:#6B675A">
                <a href="${esc(env.WORKER_URL)}/admin?key=${encodeURIComponent(adminKey(env))}">לכל התגובות</a>
              </p>`),
          });
        } catch (e) { console.error('moderation mail failed', e.message); }
      }

      return json({ ok: true, state: 'pending' }, 200, origin);
    }

    /* --- תגובות: אישור/דחייה מתוך המייל --- */
    if (url.pathname === '/moderate') {
      if (!adminOk(url, env)) {
        return page('אין הרשאה', '<p>הקישור אינו תקף.</p>');
      }
      const id = url.searchParams.get('id') || '';
      const action = url.searchParams.get('action');
      const back = `<p><a href="${esc(env.WORKER_URL)}/admin?key=${encodeURIComponent(adminKey(env))}">לדף הניהול</a></p>`;

      if (action === 'delete') {
        const parasha = url.searchParams.get('parasha') || '';
        await deleteApproved(env, parasha, id);
        return page('התגובה הוסרה', '<p>התגובה נמחקה מהאתר.</p>' + back);
      }

      const rec = await env.SUBSCRIBERS.get(PENDING_KEY(id), 'json');
      if (!rec) return page('התגובה כבר טופלה', '<p>ייתכן שכבר אישרת או דחית אותה.</p>' + back);

      if (action === 'reject') {
        await env.SUBSCRIBERS.delete(PENDING_KEY(id));
        return page('התגובה נדחתה', '<p>התגובה לא תפורסם.</p>' + back);
      }
      if (action === 'approve') {
        await approveComment(env, rec);
        return page('התגובה אושרה', `<p>התגובה של ${esc(rec.name)} מופיעה עכשיו בדף <strong>${esc(rec.parasha)}</strong>.</p>`
          + (site ? `<p><a href="${esc(site)}/#p=${encodeURIComponent(rec.parasha)}">לדף הפרשה</a></p>` : '') + back);
      }
      return page('פעולה לא מוכרת', '<p>יש להשתמש בקישורים שבמייל.</p>' + back);
    }

    /* --- דף ניהול התגובות: /admin?key=<ADMIN_KEY> --- */
    if (url.pathname === '/admin') {
      if (!adminOk(url, env)) {
        return page('אין הרשאה', '<p>נדרש מפתח ניהול.</p>');
      }
      const k = encodeURIComponent(adminKey(env));
      const pending = await listPending(env);
      const index = await readIndex(env);

      const card = (c, buttons) => `
        <div style="background:#fff;border:1px solid #E0D5BC;border-radius:10px;padding:16px 18px;margin-bottom:12px;text-align:right">
          <div style="font-weight:700;color:#14294D">${esc(c.name)}<span style="font-weight:400;color:#6B675A"> · ${esc(c.parasha)}</span></div>
          <div style="font-size:13px;color:#6B675A;margin-bottom:8px">${esc(String(c.date).slice(0, 16).replace('T', ' '))}${c.email ? ' · ' + esc(c.email) : ''}</div>
          <div style="white-space:pre-wrap;line-height:1.7;margin-bottom:12px">${esc(c.text)}</div>
          ${buttons}
        </div>`;
      const btn = (href, label, bg, fg, border) =>
        `<a href="${esc(href)}" style="display:inline-block;background:${bg};color:${fg};border:1px solid ${border};
          text-decoration:none;padding:7px 16px;border-radius:6px;font-size:14px;margin-inline-end:8px">${esc(label)}</a>`;

      let html = `<h2 style="color:#14294D;font-size:19px;margin:0 0 12px">ממתינות לאישור (${pending.length})</h2>`;
      html += pending.length
        ? pending.map(c => card(c,
            btn(`${env.WORKER_URL}/moderate?id=${encodeURIComponent(c.id)}&action=approve&key=${k}`, 'אישור ופרסום', '#2E6B3E', '#fff', '#2E6B3E')
            + btn(`${env.WORKER_URL}/moderate?id=${encodeURIComponent(c.id)}&action=reject&key=${k}`, 'דחייה', '#fff', '#8A2B2B', '#8A2B2B')
          )).join('')
        : '<p style="color:#6B675A">אין תגובות שממתינות.</p>';

      html += `<h2 style="color:#14294D;font-size:19px;margin:28px 0 12px">מפורסמות באתר</h2>`;
      const names = Object.keys(index).sort();
      if (!names.length) html += '<p style="color:#6B675A">עדיין אין תגובות מאושרות.</p>';
      for (const n of names) {
        const list = (await env.SUBSCRIBERS.get(APPROVED_KEY(n), 'json')) || [];
        html += list.map(c => card({ ...c, parasha: n },
          btn(`${env.WORKER_URL}/moderate?id=${encodeURIComponent(c.id)}&action=delete&parasha=${encodeURIComponent(n)}&key=${k}`,
            'הסרה מהאתר', '#fff', '#8A2B2B', '#8A2B2B')
        )).join('');
      }
      return new Response(
        `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>ניהול תגובות</title><style>body{font-family:system-ui,'Segoe UI',Arial,sans-serif;background:#F7F2E7;
color:#26241E;margin:0;padding:24px}main{max-width:720px;margin:0 auto}h1{color:#14294D;font-size:24px;margin:0 0 4px}</style>
</head><body><main><h1>ניהול תגובות</h1>
<p style="color:#6B675A;margin:0 0 24px">בין הנכתב לנגלה · <a href="${esc(site)}" style="color:#1B3A6B">לאתר</a></p>
${html}</main></body></html>`,
        { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex' } }
      );
    }

    /* --- אבחון: /status?key=<ADMIN_KEY> --- */
    if (url.pathname === '/status') {
      if (!adminOk(url, env)) {
        // מבחין בין "הסוד לא הוגדר בכלל" לבין "הוגדר, אבל המפתח שנשלח שגוי",
        // בלי לחשוף את הערך עצמו
        return json({ error: 'unauthorized', adminKeyConfigured: !!adminKey(env) }, 401, origin);
      }
      const out = {
        config: {
          hasResendKey: !!env.RESEND_API_KEY,
          fromEmail: env.FROM_EMAIL || null,
          siteUrl: env.SITE_URL || null,
          workerUrl: env.WORKER_URL || null,
          workerUrlLooksSet: !/YOUR-SUBDOMAIN/.test(env.WORKER_URL || 'YOUR-SUBDOMAIN'),
          hasAdminKey: !!env.ADMIN_KEY,
          hasOwnerEmail: !!ownerEmail(env),
        },
challenges: {},
      };
      try {
        const r = await fetch(env.SITE_URL.replace(/\/$/, '') + '/assets/parashot.json');
        out.challenges.parashotJson = r.status;
      } catch (e) { out.challenges.parashotJson = 'ERR ' + e.message; }
      try {
        out.challenges.upcoming = (await upcoming(env)).map(p => p.name);
      } catch (e) { out.challenges.upcoming = 'ERR ' + e.message; }
      try {
        const list = await env.SUBSCRIBERS.list({ prefix: 'sub:' });
        const subs = [];
        for (const k of list.keys) {
          const rec = await env.SUBSCRIBERS.get(k.name, 'json');
          if (rec) subs.push({ email: rec.email.replace(/(.{2}).*(@.*)/, '$1***$2'), day: rec.day, status: rec.status });
        }
        out.subscribers = subs;
      } catch (e) { out.subscribers = 'ERR ' + e.message; }
      try {
        out.comments = { pending: (await listPending(env)).length, approved: await readIndex(env) };
      } catch (e) { out.comments = 'ERR ' + e.message; }
      // הסיבה הנפוצה ביותר לכישלון שליחה: הדומיין של FROM_EMAIL לא אומת ב-Resend
      try {
        const r = await fetch('https://api.resend.com/domains', {
          headers: { authorization: 'Bearer ' + env.RESEND_API_KEY },
        });
        const b = await r.json();
        out.resendDomains = r.ok
          ? (b.data || []).map(d => ({ name: d.name, status: d.status, region: d.region }))
          : { httpStatus: r.status, body: b };
        const fromDomain = (env.FROM_EMAIL || '').split('@').pop().replace(/>.*$/, '').trim();
        out.config.fromDomain = fromDomain;
        out.config.fromDomainVerified = Array.isArray(out.resendDomains)
          && out.resendDomains.some(d => d.name === fromDomain && d.status === 'verified');
      } catch (e) { out.resendDomains = 'ERR ' + e.message; }
      return json(out, 200, origin);
    }

    /* --- בדיקת שליחה אמיתית: /testmail?to=<כתובת>&key=<ADMIN_KEY> --- */
    // מחזיר את תשובת Resend כמות שהיא, כדי לראות את סיבת הכישלון המדויקת.
    if (url.pathname === '/testmail') {
      if (!adminOk(url, env)) {
        return json({ error: 'unauthorized' }, 401, origin);
      }
      const to = (url.searchParams.get('to') || '').trim().toLowerCase();
      if (!validEmail(to)) return json({ error: 'invalid_email' }, 400, origin);
      const r = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: { authorization: 'Bearer ' + env.RESEND_API_KEY, 'content-type': 'application/json' },
        body: JSON.stringify({
          from: env.FROM_EMAIL,
          to: [to],
          subject: 'בדיקת שליחה — בין הנכתב לנגלה',
          html: '<p dir="rtl">זו הודעת בדיקה. אם הגיעה, השליחה תקינה.</p>',
        }),
      });
      let body; try { body = await r.json(); } catch { body = await r.text(); }
      return json({ httpStatus: r.status, from: env.FROM_EMAIL, to, body }, 200, origin);
    }

    /* --- הרצה ידנית לבדיקה: /send?day=mon&key=<ADMIN_KEY> --- */
    if (url.pathname === '/send') {
      if (!adminOk(url, env)) {
        return json({ error: 'unauthorized' }, 401, origin);
      }
      const day = DAYS[url.searchParams.get('day')] ? url.searchParams.get('day') : 'mon';
      return json(await sendWeekly(env, day), 200, origin);
    }

    return json({ error: 'not_found' }, 404, origin);
  },

  /* Cron: שני, חמישי ושישי בבוקר (מוגדר ב-wrangler.toml ב-UTC) */
  async scheduled(event, env, ctx) {
    const day = DAY_OF_WEEK[new Date(event.scheduledTime).getUTCDay()];
    if (!day) return;
    ctx.waitUntil(sendWeekly(env, day).then(r => console.log('weekly', day, JSON.stringify(r))));
  },
};

export { resolveName, normName, validEmail };
