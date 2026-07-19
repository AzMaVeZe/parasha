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
      if (opts.external) { b.target = '_blank'; b.rel = 'noopener noreferrer'; }
      if (opts.download) b.setAttribute('download', '');
    } else {
      b.type = 'button';
      if (opts.onClick) b.addEventListener('click', opts.onClick);
    }
    if (opts.ariaLabel) b.setAttribute('aria-label', opts.ariaLabel + (opts.external ? ' (נפתח בחלון חדש)' : ''));
    else if (opts.external) b.setAttribute('aria-label', opts.label + ' (נפתח בחלון חדש)');
    if (opts.icon) b.append(icon(opts.icon, opts.iconSize || 15));
    b.append(document.createTextNode(opts.label));
    return b;
  }

  /* ---------- מודאל צפייה ---------- */
  const modal = document.getElementById('pdf-modal');
  const modalTitle = document.getElementById('pdf-modal-title');
  const modalFrame = modal.querySelector('iframe');
  const modalDownload = document.getElementById('pdf-modal-download');
  let lastFocused = null;

  // במסכי מגע/צרים iframe של PDF שבור (בעיקר iOS) — פותחים בלשונית חדשה
  const preferNewTab = () => window.matchMedia('(pointer: coarse)').matches || window.innerWidth < 700;

  function viewPdf(title, url) {
    if (preferNewTab()) { window.open(encodeURI(url), '_blank', 'noopener'); return; }
    openPdf(title, url);
  }

  function openPdf(title, url) {
    lastFocused = document.activeElement;
    modalTitle.textContent = title;
    modalFrame.src = encodeURI(url);
    modalFrame.title = title;
    modalDownload.href = encodeURI(url);
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    document.getElementById('pdf-modal-close').focus();
  }
  function closePdf() {
    modal.hidden = true;
    modalFrame.src = 'about:blank';
    document.body.style.overflow = '';
    if (lastFocused && document.contains(lastFocused)) lastFocused.focus();
  }
  modal.addEventListener('click', e => { if (e.target === modal) closePdf(); });
  document.getElementById('pdf-modal-close').addEventListener('click', closePdf);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !modal.hidden) closePdf(); });
  // מלכודת פוקוס בתוך הדיאלוג
  modal.addEventListener('keydown', e => {
    if (e.key !== 'Tab') return;
    const f = modal.querySelectorAll('a[href], button, iframe');
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  /* זמינות קבצים: מניפסט סטטי (js/pdf-manifest.js); HEAD רק כשאין מניפסט */
  const manifest = Array.isArray(window.PDF_FILES) ? new Set(window.PDF_FILES) : null;
  const availability = new Map();
  function checkPdf(url) {
    if (manifest) return Promise.resolve(manifest.has(url.replace('assets/pdfs/', '')));
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

  const rowTitle = (sefer, p) => (sefer.id === 'chagim' ? p.name : 'פרשת ' + p.name);
  const rowActions = new Map(); // שם שורה -> אזור הכפתורים שלה (לכפתור התגובות)

  /* ---------- פודקאסט (NotebookLM) לכל דף ---------- */
  const audioManifest = Array.isArray(window.AUDIO_FILES) ? new Set(window.AUDIO_FILES) : null;
  function audioSrcFor(p) {
    if (p.audio) return /^https?:/.test(p.audio) ? p.audio : 'assets/audio/' + p.audio;
    if (p.pdf) return p.pdf.replace('assets/pdfs/', 'assets/audio/').replace(/\.pdf$/i, '.m4a');
    return null;
  }
  function audioAvailable(src) {
    if (!src) return false;
    if (/^https?:/.test(src)) return true;
    return audioManifest ? audioManifest.has(src.replace('assets/audio/', '')) : false;
  }
  function addAudio(sefer, p, row, actions) {
    const src = audioSrcFor(p);
    if (!audioAvailable(src)) return;
    const player = el('div', 'parasha-row__player');
    player.hidden = true;
    const audio = document.createElement('audio');
    audio.controls = true;
    audio.preload = 'none';
    audio.src = encodeURI(src);
    audio.setAttribute('aria-label', 'פודקאסט על ' + rowTitle(sefer, p));
    player.append(audio);
    const btn = button({
      variant: 'ghost', sm: true, icon: 'headphones', label: 'האזנה',
      ariaLabel: 'האזנה לפודקאסט על ' + rowTitle(sefer, p),
      onClick: () => {
        const opening = player.hidden;
        player.hidden = !opening;
        btn.setAttribute('aria-expanded', String(opening));
        if (opening) audio.play().catch(() => {});
      },
    });
    btn.setAttribute('aria-expanded', 'false');
    actions.append(btn);
    row.append(player);
  }

  /* ---------- שורת פרשה ---------- */
  function parashaRow(sefer, p) {
    const row = el('li', 'parasha-row');
    const rowIcon = icon('file-text', 18);
    rowIcon.classList.add('parasha-row__icon');
    row.append(rowIcon);

    const name = el('span', 'parasha-row__name', p.name);
    row.append(name);
    if (p.note) row.append(el('span', 'parasha-row__note', p.note));

    const actions = el('span', 'parasha-row__actions');
    row.append(actions);
    rowActions.set(p.name, actions);

    function showFallback() {
      if (p.box) {
        actions.append(button({ variant: 'ghost', sm: true, href: p.box, external: true, icon: 'external-link', label: 'Box', ariaLabel: 'דף ' + p.name + ' בקישור Box הישן' }));
      } else {
        actions.append(el('span', 'parasha-row__soon', 'בקרוב'));
      }
    }

    if (p.pdf) {
      checkPdf(p.pdf).then(ok => {
        if (ok) {
          row.classList.add('parasha-row--has-pdf');
          actions.append(
            button({ variant: 'secondary', sm: true, icon: 'eye', label: 'צפייה', ariaLabel: 'צפייה בדף ' + rowTitle(sefer, p), onClick: () => viewPdf(rowTitle(sefer, p), p.pdf) }),
            button({ variant: 'ghost', sm: true, href: encodeURI(p.pdf), download: true, icon: 'download', label: 'הורדה', ariaLabel: 'הורדת דף ' + rowTitle(sefer, p) + ' (PDF)' })
          );
        } else {
          showFallback();
        }
      });
    } else {
      showFallback();
    }
    addAudio(sefer, p, row, actions);
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
        if (ok) header.append(button({ variant: 'gold', sm: true, href: encodeURI(sefer.compilation), download: true, icon: 'download', label: 'האסופה המלאה (PDF)', ariaLabel: 'הורדת אסופת ' + sefer.name + ' המלאה (PDF)' }));
      });
    }
    section.append(header);

    const list = el('ul', 'sefer-section__list');
    sefer.parshiot.forEach(p => list.append(parashaRow(sefer, p)));
    section.append(list);
    return section;
  }

  const sectionsRoot = document.getElementById('sections');
  data.forEach(sefer => sectionsRoot.append(seferSection(sefer)));

  const emptyState = el('div', 'search-empty');
  emptyState.hidden = true;
  sectionsRoot.append(emptyState);

  /* ---------- חיפוש ---------- */
  const search = document.getElementById('search');
  const searchStatus = document.getElementById('search-status');
  const norm = s => (s || '').replace(/["'׳״]/g, '').replace(/[־–—-]/g, ' ').replace(/\s+/g, ' ').trim();
  search.addEventListener('input', () => {
    const q = norm(search.value);
    let total = 0;
    data.forEach(sefer => {
      const section = document.getElementById(sefer.id);
      let visible = 0;
      section.querySelectorAll('.parasha-row').forEach(row => {
        const hit = !q || norm(row.querySelector('.parasha-row__name').textContent).includes(q);
        row.style.display = hit ? '' : 'none';
        if (hit) visible++;
      });
      section.style.display = visible ? '' : 'none';
      total += visible;
    });
    emptyState.hidden = !(q && total === 0);
    if (!emptyState.hidden) {
      emptyState.textContent = 'לא נמצאה פרשה בשם "' + search.value.trim() + '" — נסו שם אחר, או מצאו את הקובץ בתיקיית הדרייב.';
    }
    searchStatus.textContent = q ? (total ? 'נמצאו ' + total + ' דפים' : 'לא נמצאו תוצאות') : '';
  });

  /* ---------- הכפתור הראשי בהירו ---------- */
  const example = data.find(s => s.id === 'devarim').parshiot.find(p => p.name === 'שופטים');
  let heroTarget = null;   // נקבע כשנמצא דף לפרשה הקרובה
  let heroBoxUrl = null;   // fallback לקישור Box של הפרשה הקרובה
  document.getElementById('hero-example').addEventListener('click', () => {
    if (heroBoxUrl) { window.open(heroBoxUrl, '_blank', 'noopener'); return; }
    const t = heroTarget || { title: 'פרשת שופטים', pdf: example.pdf };
    checkPdf(t.pdf).then(ok => {
      if (ok) viewPdf(t.title, t.pdf);
      else window.open(driveFolder, '_blank', 'noopener');
    });
  });

  /* ---------- פרשת השבוע / החג הקרוב (Hebcal) ---------- */
  const stripNikud = s => (s || '').replace(/[֑-ׇ]/g, '');
  // התאמה מדויקת בלבד, אחרי נרמול — התאמה חלקית תפסה בעבר את "בא" מתוך "תשעה באב"
  const normName = s => stripNikud(s || '').replace(/["'׳״]/g, '').replace(/[־–—-]/g, ' ').replace(/\s+/g, ' ').trim();
  // גישור בין הכתיב החסר של Hebcal לשמות באתר, וכינויי חגים
  const NAME_ALIASES = {
    'שפטים': 'שופטים', 'נצבים': 'ניצבים', 'בהעלתך': 'בהעלותך', 'אמר': 'אמור',
    'מצרע': 'מצורע', 'קדשים': 'קדושים', 'בחקתי': 'בחוקותי', 'בהר': 'בהר סיני',
    'סכות': 'סוכות', 'יום כפור': 'יום כיפור', 'שמחת תורה': 'וזאת הברכה', 'הושענא רבא': 'הושענא רבה',
  };
  const entryByName = new Map();
  data.forEach(s => s.parshiot.forEach(p => entryByName.set(normName(p.name), { p, sefer: s })));
  function findEntry(name) {
    const base = stripNikud(name).replace(/^פרשת\s+/, '').trim();
    // מועמדים: השם המלא, ואז כל מקטע של שם מחובר (ניצבים־וילך ← ניצבים)
    const candidates = [normName(base), ...base.split(/[־–—-]/).map(normName)];
    for (const c of candidates) {
      const key = NAME_ALIASES[c] ? normName(NAME_ALIASES[c]) : c;
      if (entryByName.has(key)) return entryByName.get(key);
    }
    return null;
  }

  function setRiddle(currentName, prevName) {
    const riddles = window.PARASHA_RIDDLES || {};
    const cur = riddles[currentName];
    if (!cur) return; // נשארת חידת ברירת המחדל
    document.getElementById('riddle-title').textContent = 'חידה לשולחן שבת — ' + currentName;
    document.getElementById('riddle-body').textContent = cur.q;
    const prev = prevName && riddles[prevName];
    if (prev) {
      const details = document.getElementById('riddle-prev');
      details.hidden = false;
      document.getElementById('riddle-prev-summary').textContent = 'הפתרון לחידה של שבוע שעבר (' + prevName + ')';
      document.getElementById('riddle-prev-q').textContent = prev.q;
      document.getElementById('riddle-prev-a').textContent = prev.a;
    }
  }

  (function loadUpcoming() {
    const iso = d => d.toISOString().slice(0, 10);
    const start = new Date(Date.now() - 9 * 864e5), end = new Date(Date.now() + 15 * 864e5);
    const today = iso(new Date());
    fetch('https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&s=on&il=on&start=' + iso(start) + '&end=' + iso(end))
      .then(r => r.json())
      .then(j => {
        const items = (j.items || []).filter(i =>
          (i.category === 'parashat' || i.category === 'holiday') && !stripNikud(i.hebrew).startsWith('ערב '));
        const parshiot = items.filter(i => i.category === 'parashat');
        const par = parshiot.find(i => i.date >= today);
        const prevPar = [...parshiot].reverse().find(i => i.date < today);
        const hol = items.find(i => i.category === 'holiday' && i.date >= today && (!par || i.date <= par.date));
        // חג מוצג רק אם יש לו דף באתר; אחרת — פרשת השבת הקרובה
        let pick = null;
        if (hol) {
          const h = findEntry(hol.hebrew);
          if (h && h.p.pdf) pick = hol;
        }
        if (!pick) pick = par;
        if (!pick) return;
        const heName = stripNikud(pick.hebrew).replace(/^פרשת\s+/, '');
        const dt = new Date(pick.date + 'T12:00:00');
        const kind = pick.category === 'parashat' ? 'פרשת השבוע' : 'החג הקרוב';

        document.getElementById('hero-badge-kind').textContent = kind + ':';
        document.getElementById('hero-badge-name').textContent = heName;
        document.getElementById('hero-badge-date').textContent = '· '
          + dt.toLocaleDateString('he-IL', { weekday: 'long', day: 'numeric', month: 'long' }) + ' · '
          + new Intl.DateTimeFormat('he-u-ca-hebrew', { day: 'numeric', month: 'long', year: 'numeric' }).format(dt);
        document.getElementById('hero-badge').hidden = false;

        const hit = findEntry(pick.hebrew);
        const prevHit = prevPar ? findEntry(prevPar.hebrew) : null;
        setRiddle(hit ? hit.p.name : null, prevHit ? prevHit.p.name : null);
        if (!hit) return;
        const entry = hit.p;
        const title = rowTitle(hit.sefer, entry);
        const label = document.getElementById('hero-cta-label');
        if (entry.pdf) {
          checkPdf(entry.pdf).then(ok => {
            if (!ok) return;
            heroTarget = { title: title, pdf: entry.pdf };
            label.textContent = 'לדף ' + (kind === 'פרשת השבוע' ? 'פרשת ' : '') + heName;
            const side = document.getElementById('hero-side');
            const quote = side.querySelector('.pasuk-quote');
            const card = el('div', 'hero-preview');
            const bar = el('div', 'hero-preview__bar');
            bar.append(el('span', 'hero-preview__title', 'הצצה לדף ' + heName));
            bar.append(button({ variant: 'ghost', sm: true, icon: 'eye', label: 'לדף המלא', ariaLabel: 'צפייה בדף ' + title + ' המלא', onClick: () => viewPdf(title, entry.pdf) }));
            // תמונת העמוד הראשון — iframe של PDF לא נתמך באנדרואיד ולא ממורכז ב-iOS
            const img = document.createElement('img');
            img.className = 'hero-preview__img';
            img.src = encodeURI(entry.pdf.replace('assets/pdfs/', 'assets/previews/').replace(/\.pdf$/i, '.jpg'));
            img.alt = 'העמוד הראשון של דף ' + title;
            img.addEventListener('click', () => viewPdf(title, entry.pdf));
            img.addEventListener('error', () => { card.remove(); if (quote) quote.hidden = false; });
            card.append(bar, img);
            if (quote) quote.hidden = true;
            side.append(card);
          });
        } else if (entry.box) {
          heroBoxUrl = entry.box;
          label.textContent = 'לדף ' + heName + ' (Box)';
        }
      }).catch(() => {});
  })();

  /* ---------- קישורי דרייב ---------- */
  document.querySelectorAll('[data-drive-folder]').forEach(a => { a.href = driveFolder; });

  /* ---------- הרשמה: Google Forms עם fallback לדוא"ל ---------- */
  (function initSubscribe() {
    const btn = document.getElementById('subscribe-btn');
    const fallback = document.getElementById('subscribe-fallback');
    if (window.SUBSCRIBE_FORM_URL) {
      btn.href = window.SUBSCRIBE_FORM_URL;
      fallback.hidden = true;
    } else {
      btn.hidden = true;
      fallback.hidden = false;
      document.getElementById('copy-email').addEventListener('click', () => {
        navigator.clipboard.writeText('ariel.zitnitski@gmail.com').then(() => {
          document.getElementById('copy-email').textContent = 'הועתק!';
          setTimeout(() => { document.getElementById('copy-email').textContent = 'העתקת הכתובת'; }, 2000);
        }).catch(() => {});
      });
    }
  })();

  /* ---------- תגובות לכל דף בנפרד: Google Forms (אימייל מאומת) + גיליון מפורסם ---------- */
  const commentsEnabled = !!window.COMMENTS_FORM_URL;
  const commentsByName = new Map(); // שם שורה -> [{name, date, text}]
  let commentsLoaded = null;

  function commentFormUrl(rowName) {
    let url = window.COMMENTS_FORM_URL;
    if (window.COMMENTS_ENTRY_PARASHA) {
      url += (url.includes('?') ? '&' : '?') + 'usp=pp_url&'
        + window.COMMENTS_ENTRY_PARASHA + '=' + encodeURIComponent(rowName);
    }
    return url;
  }

  function loadComments() {
    if (commentsLoaded) return commentsLoaded;
    commentsLoaded = !window.COMMENTS_CSV_URL ? Promise.resolve() :
      fetch(window.COMMENTS_CSV_URL)
        .then(r => r.text())
        .then(text => {
          const rows = parseCsv(text);
          if (!rows.length) return;
          // איתור עמודות לפי הכותרות; ברירת מחדל: חותמת זמן, אימייל, פרשה, שם, תגובה
          const header = rows[0].map(h => h.trim());
          const col = (label, fallback) => { const i = header.findIndex(h => h.includes(label)); return i >= 0 ? i : fallback; };
          const iDate = 0, iParasha = col('פרשה', 2), iName = col('שם', 3), iText = col('תגובה', 4);
          rows.slice(1).forEach(r => {
            const text2 = (r[iText] || '').trim();
            const key = (r[iParasha] || '').trim();
            if (!text2 || !key) return;
            if (!commentsByName.has(key)) commentsByName.set(key, []);
            commentsByName.get(key).push({ name: (r[iName] || 'אנונימי').trim(), date: r[iDate], text: text2 });
          });
        })
        .catch(() => {});
    return commentsLoaded;
  }

  const commentsModal = document.getElementById('comments-modal');
  const commentsList = document.getElementById('comments-modal-list');
  const commentsNote = document.getElementById('comments-modal-note');
  let commentsLastFocused = null;

  function openComments(rowName) {
    commentsLastFocused = document.activeElement;
    document.getElementById('comments-modal-title').textContent = 'תגובות — ' + rowName;
    document.getElementById('comments-write').href = commentFormUrl(rowName);
    commentsList.textContent = '';
    commentsNote.textContent = 'טוען תגובות…';
    commentsModal.hidden = false;
    document.body.style.overflow = 'hidden';
    document.getElementById('comments-modal-close').focus();
    loadComments().then(() => {
      const items = commentsByName.get(rowName) || [];
      if (!items.length) {
        commentsNote.textContent = 'עדיין אין תגובות לדף הזה — שמחים להיות הראשונים לשמוע מכם.';
        return;
      }
      commentsNote.textContent = '';
      [...items].reverse().forEach(c => {
        const item = el('li', 'comment');
        const head = el('div', 'comment__head');
        head.append(el('span', 'comment__name', c.name));
        const d = new Date(c.date);
        if (!isNaN(d)) head.append(el('span', 'comment__date', d.toLocaleDateString('he-IL', { day: 'numeric', month: 'long', year: 'numeric' })));
        item.append(head, el('div', 'comment__body', c.text));
        commentsList.append(item);
      });
    });
  }
  function closeComments() {
    commentsModal.hidden = true;
    document.body.style.overflow = '';
    if (commentsLastFocused && document.contains(commentsLastFocused)) commentsLastFocused.focus();
  }
  commentsModal.addEventListener('click', e => { if (e.target === commentsModal) closeComments(); });
  document.getElementById('comments-modal-close').addEventListener('click', closeComments);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !commentsModal.hidden) closeComments(); });
  commentsModal.addEventListener('keydown', e => {
    if (e.key !== 'Tab') return;
    const f = commentsModal.querySelectorAll('a[href], button');
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  // כפתור תגובות בכל שורה (עם מונה כשהתגובות נטענות)
  if (commentsEnabled) {
    loadComments().then(() => {
      rowActions.forEach((actions, rowName) => {
        const count = (commentsByName.get(rowName) || []).length;
        actions.append(button({
          variant: 'ghost', sm: true, icon: 'mail',
          label: count ? 'תגובות (' + count + ')' : 'תגובות',
          ariaLabel: 'תגובות לדף ' + rowName + (count ? ' — ' + count + ' תגובות' : ''),
          onClick: () => openComments(rowName),
        }));
      });
    });
  }

  // מפרק CSV מינימלי עם תמיכה במרכאות
  function parseCsv(text) {
    const rows = [];
    let row = [], field = '', inQ = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (inQ) {
        if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
        else if (c === '"') inQ = false;
        else field += c;
      } else if (c === '"') inQ = true;
      else if (c === ',') { row.push(field); field = ''; }
      else if (c === '\n' || c === '\r') {
        if (c === '\r' && text[i + 1] === '\n') i++;
        row.push(field); field = '';
        if (row.some(f => f !== '')) rows.push(row);
        row = [];
      } else field += c;
    }
    row.push(field);
    if (row.some(f => f !== '')) rows.push(row);
    return rows;
  }

  /* ---------- חזרה למעלה ---------- */
  const toTop = document.getElementById('to-top');
  window.addEventListener('scroll', () => { toTop.hidden = window.scrollY < 600; }, { passive: true });
  toTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();
