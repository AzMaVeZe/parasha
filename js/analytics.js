/* סטטיסטיקת ביקורים — Cloudflare Web Analytics.
 *
 * מה נאסף: כמה ביקורים, באילו עמודים, מאיזו מדינה ומאיזה סוג מכשיר. בלי עוגיות,
 * בלי טביעת אצבע, ובלי שום דבר שמזהה קורא. הנתונים גלויים רק בחשבון Cloudflare
 * של אריאל: dash.cloudflare.com ‹ Analytics & Logs ‹ Web Analytics.
 *
 * TOKEN הוא מזהה האתר ב-Web Analytics (לא סוד: הוא מופיע בכל עמוד ממילא).
 * כל עוד הוא ריק — שום דבר לא נטען. ראו docs/operations.md, "סטטיסטיקת ביקורים".
 *
 * המעבר בין דפים בתוך האתר (#p=...) נספר אוטומטית: הסקריפט של Cloudflare
 * מזהה ניווט בתוך עמוד אחד. */
(function () {
  'use strict';
  var TOKEN = '588427f3469f4e889f9192211a90b7a4';
  if (!TOKEN) return;
  var s = document.createElement('script');
  s.defer = true;
  s.src = 'https://static.cloudflareinsights.com/beacon.min.js';
  s.setAttribute('data-cf-beacon', JSON.stringify({ token: TOKEN }));
  document.head.appendChild(s);
})();
