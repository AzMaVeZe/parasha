// יישור אנכי (כמו vertical justification ב-InDesign): עמוד שהרווחים סביב הפסוקים הוציאו אותו מהגריד
// (חצי שורה ריקה בתחתית) — החסר מתחלק בין הרווחים שסביב הפסוקים שבאותו עמוד, והשורה האחרונה יורדת לתחתית.
// רץ אחרי שכל העמודים נבנו, ורק מוסיף רווח בתוך מה שנשאר ריק בעמוד — לכן אינו מזיז טקסט בין עמודים.
window.PagedPolyfill.registerHandlers(class extends window.Paged.Handler {
  afterRendered() {
    document.querySelectorAll('.pagedjs_page').forEach(page => {
      const area = page.querySelector('.pagedjs_page_content');
      const ps = area ? [...area.querySelectorAll('.chapter p')] : [];
      if (!ps.length) return;
      // רווח שנפל לראש העמוד (פסוק, או הטקסט שאחריו, שפותח עמוד) — מתבטל: ראש העמוד תמיד על השורה הראשונה
      if (parseFloat(getComputedStyle(ps[0]).marginTop) > 0 && !area.querySelector('.ch-head')) ps[0].style.marginTop = '0';
      if (!area.querySelector('.chapter[data-split-to]') || area.querySelector('.notes')) return;
      const body = ps.find(p => !p.classList.contains('q'));
      if (!body) return;
      const lh = parseFloat(getComputedStyle(body).lineHeight);
      const spaced = ps.filter((p, i) => i > 0 && parseFloat(getComputedStyle(p).marginTop) > 0);
      if (!spaced.length) return;
      const gap = (area.getBoundingClientRect().bottom - ps[ps.length - 1].getBoundingClientRect().bottom) / lh;
      const f = gap - Math.floor(gap + 0.05);
      if (f < 0.1) return;
      spaced.forEach(p => { p.style.marginTop = (parseFloat(getComputedStyle(p).marginTop) + f * lh / spaced.length) + 'px' });
    });
  }
});
