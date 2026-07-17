/* פרשת השבוע — רינדור האתר מתוך PARASHA_DATA (ללא תלות בספריות) */
(function () {
  'use strict';

  const data = window.PARASHA_DATA;
  const driveFolder = window.DRIVE_FOLDER;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function icon(name, size) {
    const s = el('span', 'icon');
    s.setAttribute('aria-hidden', 'true');
    s.style.setProperty('--icon', "url('assets/icons/" + name + ".svg')");
    if (size) { s.style.width = size + 'px'; s.style.height = size + 'px'; }
    return s;
  }

  function button(opts) {
    const isLink = !!opts.href;
    const b = el(isLink ? 'a' : 'button', 'btn btn--' + (opts.variant || 'primary') + (opts.sm ? ' btn--sm' : ''));
    if (isLink) {
      b.href = opts.href;
      if (opts.external) { b.target = '_blank'; b.rel = 'noopener'; }
      if (opts.download) b.setAttribute('download', '');
    } else {
      b.type = 'button';
      if (opts.onClick) b.addEventListener('click', opts.onClick);
    }
    if (opts.icon) b.append(icon(opts.icon, opts.iconSize || 15));
    b.append(document.createTextNode(opts.label));
    return b;
  }

  /* ---------- מודאל צפייה ---------- */
  const modal = document.getElementById('pdf-modal');
  const modalTitle = modal.querySelector('.pdf-modal__title');
  const modalFrame = modal.querySelector('iframe');
  const modalDownload = document.getElementById('pdf-modal-download');

  function openPdf(name, url) {
    modalTitle.textContent = 'פרשת ' + name;
    modalFrame.src = encodeURI(url);
    modalDownload.href = encodeURI(url);
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function closePdf() {
    modal.hidden = true;
    modalFrame.src = 'about:blank';
    document.body.style.overflow = '';
  }
  modal.addEventListener('click', e => { if (e.target === modal) closePdf(); });
  document.getElementById('pdf-modal-close').addEventListener('click', closePdf);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !modal.hidden) closePdf(); });

  /* בדיקה אילו קבצים אכן קיימים בארכיון המקומי — כפתורי צפייה/הורדה מופיעים רק להם */
  const availability = new Map();
  function checkPdf(url) {
    if (!availability.has(url)) {
      availability.set(url, fetch(encodeURI(url), { method: 'HEAD' }).then(r => r.ok).catch(() => false));
    }
    return availability.get(url);
  }

  /* ---------- ניווט עליון ---------- */
  const nav = document.getElementById('site-nav');
  data.forEach(sefer => {
    const a = el('a', null, sefer.name.replace('ספר ', ''));
    a.href = '#' + sefer.id;
    nav.append(a);
  });

  /* ---------- שורת פרשה ---------- */
  function parashaRow(p) {
    const row = el('div', 'parasha-row');
    const rowIcon = icon('file-text', 18);
    rowIcon.classList.add('parasha-row__icon');
    row.append(rowIcon);

    const name = el('span', 'parasha-row__name', p.name);
    row.append(name);
    if (p.note) row.append(el('span', 'parasha-row__note', p.note));

    const actions = el('span', 'parasha-row__actions');
    row.append(actions);

    function showFallback() {
      if (p.box) {
        actions.append(button({ variant: 'ghost', sm: true, href: p.box, external: true, icon: 'external-link', label: 'Box' }));
      } else {
        actions.append(el('span', 'parasha-row__soon', 'בקרוב'));
      }
    }

    if (p.pdf) {
      checkPdf(p.pdf).then(ok => {
        if (ok) {
          row.classList.add('parasha-row--has-pdf');
          actions.append(
            button({ variant: 'secondary', sm: true, icon: 'eye', label: 'צפייה', onClick: () => openPdf(p.name, p.pdf) }),
            button({ variant: 'ghost', sm: true, href: encodeURI(p.pdf), download: true, icon: 'download', label: 'הורדה' })
          );
        } else {
          showFallback();
        }
      });
    } else {
      showFallback();
    }
    return row;
  }

  /* ---------- מדור ספר ---------- */
  function seferSection(sefer) {
    const section = el('section', 'sefer-section');
    section.id = sefer.id;

    const header = el('div', 'section-header');
    const headText = el('div');
    headText.append(el('h2', null, sefer.name), el('div', 'section-header__subtitle', sefer.parshiot.length + ' דפים'));
    header.append(headText);
    if (sefer.compilation) {
      checkPdf(sefer.compilation).then(ok => {
        if (ok) header.append(button({ variant: 'gold', sm: true, href: encodeURI(sefer.compilation), download: true, icon: 'download', label: 'האסופה המלאה (PDF)' }));
      });
    }
    section.append(header);

    const list = el('div', 'sefer-section__list');
    sefer.parshiot.forEach(p => list.append(parashaRow(p)));
    section.append(list);
    return section;
  }

  const sectionsRoot = document.getElementById('sections');
  data.forEach(sefer => sectionsRoot.append(seferSection(sefer)));

  /* ---------- חיפוש ---------- */
  const search = document.getElementById('search');
  search.addEventListener('input', () => {
    const q = search.value.trim();
    data.forEach(sefer => {
      const section = document.getElementById(sefer.id);
      let visible = 0;
      section.querySelectorAll('.parasha-row').forEach(row => {
        const hit = !q || row.querySelector('.parasha-row__name').textContent.includes(q);
        row.style.display = hit ? '' : 'none';
        if (hit) visible++;
      });
      section.style.display = visible ? '' : 'none';
    });
  });

  /* ---------- כפתור הדוגמה בהירו ---------- */
  const example = data.find(s => s.id === 'devarim').parshiot.find(p => p.name === 'שופטים');
  document.getElementById('hero-example').addEventListener('click', () => {
    checkPdf(example.pdf).then(ok => {
      if (ok) openPdf(example.name, example.pdf);
      else window.open(driveFolder, '_blank', 'noopener');
    });
  });

  /* ---------- קישורי דרייב ---------- */
  document.querySelectorAll('[data-drive-folder]').forEach(a => { a.href = driveFolder; });

  /* ---------- הרשמה בדוא"ל ---------- */
  document.getElementById('subscribe-form').addEventListener('submit', e => {
    e.preventDefault();
    const email = document.getElementById('subscribe-email').value.trim();
    location.href = 'mailto:ariel.zitnitski@gmail.com'
      + '?subject=' + encodeURIComponent('הרשמה לדף פרשת השבוע')
      + '&body=' + encodeURIComponent('אשמח לקבל את הדף השבועי לכתובת: ' + email);
  });
})();
