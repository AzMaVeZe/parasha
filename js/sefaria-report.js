/* דיווח לספריא על המקורות שבדף. טוען, אחרי שהעמוד סיים להיטען, את
   sources.html של הדף ב-iframe נסתר; שם רץ ה-Linker של ספריא, על רשימת המקורות
   בלבד. הסבר מלא ב-scripts/build-pages.js (sourcesReportPage). */
(function () {
  function report() {
    var f = document.createElement('iframe');
    f.src = 'sources';   // sources.html; Cloudflare מגיש אותו בלי הסיומת
    f.hidden = true;
    f.setAttribute('aria-hidden', 'true');
    f.tabIndex = -1;
    f.title = '';
    document.body.appendChild(f);
  }
  function later() {
    if ('requestIdleCallback' in window) requestIdleCallback(report, { timeout: 5000 });
    else setTimeout(report, 2000);
  }
  if (document.readyState === 'complete') later();
  else window.addEventListener('load', later);
})();
