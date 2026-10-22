/* מעבר לשרת הרשימה דרך הכתובת של האתר עצמו.
 *
 * למה: הדפדפן פנה ישירות ל-parasha-newsletter.azma.workers.dev, ושירותי סינון
 * (משמר הבית של בזק, סינון של חברות סלולר) חוסמים כתובות workers.dev. הבקשה
 * נתקעה, ההרשמה לא הגיעה לשרת, והטופס נשאר על "רגע…". כאן הדפדפן פונה ל-
 * parasha.azma.app/api/..., ו-Cloudflare מעביר את הבקשה לשרת מבפנים — בלי
 * לעבור דרך הסינון של הגולש.
 *
 * זו Pages Function: היא עולה אוטומטית עם האתר, בלי wrangler deploy.
 * /api/subscribe → <שרת>/subscribe, וכן הלאה לכל הנתיבים. */
const UPSTREAM = 'https://parasha-newsletter.azma.workers.dev';

export async function onRequest({ request }) {
  const url = new URL(request.url);
  const target = UPSTREAM + (url.pathname.replace(/^\/api/, '') || '/') + url.search;

  const headers = new Headers(request.headers);
  headers.delete('host');
  // כתובת ה-IP של הגולש, להגבלת הקצב של התגובות. בלעדיה כל הפניות היו
  // נראות לשרת כאילו באו מאותו מקום.
  headers.set('x-parasha-client-ip', request.headers.get('cf-connecting-ip') || '');

  const init = { method: request.method, headers, redirect: 'manual' };
  if (request.method !== 'GET' && request.method !== 'HEAD') init.body = await request.arrayBuffer();

  try {
    const res = await fetch(target, init);
    return new Response(res.body, res);
  } catch (e) {
    return new Response(JSON.stringify({ error: 'upstream_unreachable' }), {
      status: 502, headers: { 'content-type': 'application/json; charset=utf-8' },
    });
  }
}
