/**
 * בין הנכתב לנגלה — Worker לרשימת התפוצה.
 *
 * אחראי על:
 *  POST /subscribe    — הרשמה (מייל + יום מועדף), שולח מייל אישור (double opt-in)
 *  GET  /confirm      — אישור ההרשמה מתוך המייל
 *  GET  /unsubscribe  — הסרה מהרשימה
 *  cron               — כל יום שני וחמישי: שולח את דף הפרשה הקרובה לנרשמים של אותו יום
 *
 * סודות (wrangler secret put):  RESEND_API_KEY
 * משתנים (wrangler.toml vars):  SITE_URL, FROM_EMAIL, REPLY_TO, BRAND
 * אחסון:                        KV binding בשם SUBSCRIBERS
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

    /* --- אבחון: /status?key=<ADMIN_KEY> --- */
    if (url.pathname === '/status') {
      if (!env.ADMIN_KEY || url.searchParams.get('key') !== env.ADMIN_KEY) {
        return json({ error: 'unauthorized' }, 401, origin);
      }
      const out = {
        config: {
          hasResendKey: !!env.RESEND_API_KEY,
          fromEmail: env.FROM_EMAIL || null,
          siteUrl: env.SITE_URL || null,
          workerUrl: env.WORKER_URL || null,
          workerUrlLooksSet: !/YOUR-SUBDOMAIN/.test(env.WORKER_URL || 'YOUR-SUBDOMAIN'),
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
      if (!env.ADMIN_KEY || url.searchParams.get('key') !== env.ADMIN_KEY) {
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
      if (!env.ADMIN_KEY || url.searchParams.get('key') !== env.ADMIN_KEY) {
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
