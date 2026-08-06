/* פרשת השבוע — רינדור האתר מתוך PARASHA_DATA (ללא תלות בספריות) */
(function () {
  'use strict';

  const data = window.PARASHA_DATA;

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
  const cardCountEls = new Map(); // שם דף -> אלמנט מונה התגובות בכרטיס
  const pdfExists = url => (manifest ? manifest.has(url.replace('assets/pdfs/', '')) : true);
  // אינדקס לניתוב: שם דף -> {p, sefer}
  const pageIndex = new Map();
  data.forEach(s => s.parshiot.forEach(p => { if (!pageIndex.has(p.name)) pageIndex.set(p.name, { p, sefer: s }); }));

  /* ---------- פודקאסט לכל דף: קובץ מקומי (NotebookLM) או ספוטיפיי ---------- */
  const audioManifest = Array.isArray(window.AUDIO_FILES) ? new Set(window.AUDIO_FILES) : null;
  function spotifyEpisodeId(url) {
    const m = /open\.spotify\.com\/episode\/([A-Za-z0-9]+)/.exec(url || '');
    return m ? m[1] : null;
  }
  function fileAudioSrcFor(p) {
    if (p.audio) return /^https?:/.test(p.audio) ? p.audio : 'assets/audio/' + p.audio;
    if (p.pdf) return p.pdf.replace('assets/pdfs/', 'assets/audio/').replace(/\.pdf$/i, '.m4a');
    return null;
  }
  function fileAudioAvailable(src) {
    if (!src) return false;
    if (/^https?:/.test(src)) return true;
    return audioManifest ? audioManifest.has(src.replace('assets/audio/', '')) : false;
  }
  function hasPodcast(p) {
    return !!spotifyEpisodeId(p.spotify) || fileAudioAvailable(fileAudioSrcFor(p));
  }

  // בונה נגן פודקאסט (ספוטיפיי מוטמע או קובץ מקומי); מחזיר null אם אין מקור
  function buildPodcast(p, title) {
    const spotifyId = spotifyEpisodeId(p.spotify);
    const fileSrc = fileAudioSrcFor(p);
    if (!spotifyId && !fileAudioAvailable(fileSrc)) return null;
    const wrap = el('div', 'podcast');
    wrap.append(el('div', 'podcast__title', 'האזנה לפודקאסט'));
    if (spotifyId) {
      const frame = document.createElement('iframe');
      frame.src = 'https://open.spotify.com/embed/episode/' + spotifyId + '?utm_source=generator';
      frame.title = 'נגן ספוטיפיי — פודקאסט על ' + title;
      frame.loading = 'lazy';
      frame.height = 152;
      frame.style.borderRadius = '12px';
      frame.allow = 'encrypted-media; clipboard-write; fullscreen; picture-in-picture';
      wrap.append(frame);
      const openLink = el('a', 'podcast__link', 'פתיחה בספוטיפיי');
      openLink.href = p.spotify;
      openLink.target = '_blank';
      openLink.rel = 'noopener noreferrer';
      openLink.append(el('span', 'visually-hidden', ' (נפתח בחלון חדש)'));
      wrap.append(openLink);
    } else {
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.preload = 'none';
      audio.src = encodeURI(fileSrc);
      audio.setAttribute('aria-label', 'פודקאסט על ' + title);
      wrap.append(audio);
    }
    return wrap;
  }

  /* ---------- כרטיס פרשה (קישור לעמוד הדף) ---------- */
  function metaItem(iconName, text, color) {
    const s = el('span', 'parasha-row__metaitem');
    const ic = icon(iconName, 15);
    if (color) ic.style.color = color;
    s.append(ic, document.createTextNode(text));
    return s;
  }
  function parashaRow(sefer, p) {
    const li = el('li', 'parasha-row');
    const link = el('a', 'parasha-row__link');
    link.href = '#p=' + encodeURIComponent(p.name);
    link.setAttribute('aria-label', 'עמוד ' + rowTitle(sefer, p));
    li.append(link);

    const head = el('div', 'parasha-row__head');
    const rowIcon = icon('file-text', 18);
    rowIcon.classList.add('parasha-row__icon');
    head.append(rowIcon, el('span', 'parasha-row__name', p.name));
    if (p.note) head.append(el('span', 'parasha-row__note', p.note));
    link.append(head);

    const meta = el('div', 'parasha-row__meta');
    link.append(meta);

    const pdfOk = p.pdf && pdfExists(p.pdf);
    if (pdfOk) { li.classList.add('parasha-row--has-pdf'); meta.append(metaItem('file-text', 'דף לצפייה', 'var(--gold-700)')); }
    else if (p.box) meta.append(metaItem('external-link', 'Box'));
    else meta.append(el('span', 'parasha-row__soon', 'בקרוב'));

    if (hasPodcast(p)) meta.append(metaItem('headphones', 'פודקאסט', '#1DB954'));

    if (window.SUBSCRIBE_API) {
      const c = metaItem('mail', '0');
      c.hidden = true;
      cardCountEls.set(p.name, c);
      meta.append(c);
    }
    return li;
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
  const norm = s => (s || '').replace(/[֑-ׇֽֿׁׂׅׄ]/g, '')
    .replace(/["'׳״]/g, '').replace(/[־–—-]/g, ' ').replace(/\s+/g, ' ').trim();
  let searchWasActive = false;

  function runSearch() {
    const q = norm(search.value);

    // מקלידים בזמן שעמוד דף פתוח? הארכיון מוסתר, אז הסינון "לא עושה כלום".
    // חוזרים לארכיון (בלי קפיצת עוגן) כדי שהתוצאות באמת ייראו.
    if (q && !pageEl.hidden) {
      history.replaceState(null, '', location.pathname + location.search);
      closeParashaPage();
    }

    let total = 0;
    data.forEach(sefer => {
      const section = document.getElementById(sefer.id);
      let visible = 0;
      section.querySelectorAll('.parasha-row').forEach(row => {
        const name = row.querySelector('.parasha-row__name');
        const note = row.querySelector('.parasha-row__note');
        const hay = norm(name.textContent + ' ' + (note ? note.textContent : ''));
        const hit = !q || hay.includes(q);
        row.style.display = hit ? '' : 'none';
        if (hit) visible++;
      });
      section.style.display = visible ? '' : 'none';
      total += visible;
    });
    emptyState.hidden = !(q && total === 0);
    if (!emptyState.hidden) {
      emptyState.textContent = 'לא נמצאה פרשה בשם "' + search.value.trim() + '" — אפשר לנסות שם אחר.';
    }
    searchStatus.textContent = q ? (total ? 'נמצאו ' + total + ' דפים' : 'לא נמצאו תוצאות') : '';

    // הארכיון יושב הרחק מתחת להירו (בנייד ~1800px), ולכן בלי גלילה נראה כאילו
    // החיפוש לא מגיב. גוללים אליו פעם אחת, כשמתחילים לחפש.
    if (q && !searchWasActive) {
      sectionsRoot.scrollIntoView({ block: 'start', behavior: 'smooth' });
    }
    searchWasActive = !!q;
  }

  search.addEventListener('input', runSearch);
  search.addEventListener('keydown', e => {
    if (e.key === 'Escape' && search.value) { search.value = ''; runSearch(); }
  });

  /* ---------- הכפתור הראשי בהירו ---------- */
  let heroName = 'שופטים';   // שם הדף המוצג בהירו (ברירת מחדל עד טעינת Hebcal)
  const goToParasha = name => { location.hash = '#p=' + encodeURIComponent(name); };
  document.getElementById('hero-example').addEventListener('click', () => goToParasha(heroName));

  /* ---------- פרשת השבוע / החג הקרוב (Hebcal) ---------- */
  // מסיר ניקוד וטעמים בלבד — בלי מקף עברי (U+05BE), כדי ש"ניצבים־וילך" יישאר מפוצל
  const stripNikud = s => (s || '').replace(/[֑-ׇֽֿׁׂׅׄ]/g, '');
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

  function hebDateText(dt) {
    return '· ' + dt.toLocaleDateString('he-IL', { weekday: 'long', day: 'numeric', month: 'long' })
      + ' · ' + new Intl.DateTimeFormat('he-u-ca-hebrew', { day: 'numeric', month: 'long', year: 'numeric' }).format(dt);
  }
  function buildBadge(kind, heName, dt) {
    const badge = el('div', 'hero-badge');
    badge.append(el('span', 'hero-badge__kind', kind + ':'));
    badge.append(el('span', 'hero-badge__name', heName));
    badge.append(el('span', 'hero-badge__date', hebDateText(dt)));
    return badge;
  }
  function buildPreviewCard(hit) {
    const entry = hit.p;
    const title = rowTitle(hit.sefer, entry);
    const href = '#p=' + encodeURIComponent(entry.name);
    const card = el('div', 'hero-preview');
    const bar = el('div', 'hero-preview__bar');
    bar.append(el('span', 'hero-preview__title', 'הצצה לדף ' + entry.name));
    const more = el('a', 'hero-preview__more', 'לעמוד הדף ←');
    more.href = href;
    bar.append(more);
    // תמונת העמוד הראשון (קישור לעמוד הדף) — iframe של PDF לא נתמך באנדרואיד
    const imgLink = el('a', 'hero-preview__imglink');
    imgLink.href = href;
    imgLink.setAttribute('aria-label', 'לעמוד ' + title);
    const img = document.createElement('img');
    img.className = 'hero-preview__img';
    img.src = encodeURI(entry.pdf.replace('assets/pdfs/', 'assets/previews/').replace(/\.pdf$/i, '.jpg'));
    img.alt = 'העמוד הראשון של דף ' + title;
    img.addEventListener('error', () => { card.remove(); });
    imgLink.append(img);
    card.append(bar, imgLink);
    // נגן הפודקאסט מתחת לתצוגה המקדימה; אם אין פרק לדף הזה — קישור לסדרה
    const pod = buildPodcast(entry, title);
    if (pod) {
      pod.classList.add('hero-preview__podcast');
      card.append(pod);
    } else if (window.SPOTIFY_SHOW_URL) {
      const wrap = el('div', 'hero-preview__podcast');
      const a = el('a', 'podcast__title podcast__showlink', 'האזנה לפודקאסט');
      a.href = window.SPOTIFY_SHOW_URL;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.append(el('span', 'visually-hidden', ' (נפתח בחלון חדש)'));
      wrap.append(a);
      card.append(wrap);
    }
    return card;
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
        const holItem = items.find(i => i.category === 'holiday' && i.date >= today);

        const mk = (it, cat) => ({
          cat, it, hit: findEntry(it.hebrew),
          heName: stripNikud(it.hebrew).replace(/^פרשת\s+/, ''),
          dt: new Date(it.date + 'T12:00:00'),
        });
        // מועמדים: החג הקרוב (רק אם יש לו דף) + פרשת השבת הקרובה. מסירים כפילות של אותו קובץ.
        const candidates = [];
        if (holItem) {
          const c = mk(holItem, 'holiday');
          if (c.hit && c.hit.p.pdf && pdfExists(c.hit.p.pdf)) candidates.push(c);
        }
        if (par) {
          const c = mk(par, 'parashat');
          if (!candidates.some(x => x.hit && c.hit && x.hit.p.name === c.hit.p.name)) candidates.push(c);
        }
        if (!candidates.length) return;
        candidates.sort((a, b) => (a.it.date < b.it.date ? -1 : 1));
        const featured = candidates.slice(0, 2);

        // תגיות — אחת לכל דף מוצג (שם קנוני מהאתר כשקיים)
        const badges = document.getElementById('hero-badges');
        featured.forEach(c => badges.append(buildBadge(
          c.cat === 'parashat' ? 'פרשת השבוע' : 'החג הקרוב',
          c.hit ? c.hit.p.name : c.heName, c.dt)));
        badges.hidden = false;

        // חידה — לפי הפרשה אם קיימת, אחרת לפי הפריט הראשון
        const parCand = featured.find(c => c.cat === 'parashat') || featured[0];
        const prevHit = prevPar ? findEntry(prevPar.hebrew) : null;
        setRiddle(parCand.hit ? parCand.hit.p.name : null, prevHit ? prevHit.p.name : null);

        // כרטיסים בהירו — עד שניים, כל אחד עם הפודקאסט שלו
        const side = document.getElementById('hero-side');
        const quote = side.querySelector('.pasuk-quote');
        let firstCard = null, cardCount = 0;
        featured.forEach(c => {
          if (c.hit && c.hit.p.pdf && pdfExists(c.hit.p.pdf)) {
            side.append(buildPreviewCard(c.hit));
            cardCount++;
            if (!firstCard) firstCard = c;
          }
        });
        if (firstCard) {
          if (quote) quote.hidden = true;
          heroName = firstCard.hit.p.name;
          document.getElementById('hero-cta-label').textContent =
            'לדף ' + (firstCard.cat === 'parashat' ? 'פרשת ' : '') + firstCard.hit.p.name;
        }
        // שני דפים בדסקטופ — פריסה מוערמת (טקסט למעלה, שני כרטיסים זה לצד זה)
        if (cardCount === 2) document.querySelector('.hero').classList.add('hero--stack');
      }).catch(() => {});
  })();

  /* ---------- קישור לתוכנית המלאה בספוטיפיי ---------- */
  if (window.SPOTIFY_SHOW_URL) {
    document.querySelectorAll('[data-spotify-show]').forEach(a => { a.href = window.SPOTIFY_SHOW_URL; });
    document.getElementById('spotify-card').hidden = false;
    document.getElementById('header-podcast').hidden = false;
  }

  /* ---------- הרשמה לרשימת התפוצה (Worker + Resend) ---------- */
  (function initSubscribe() {
    const form = document.getElementById('subscribe-form');
    const fallback = document.getElementById('subscribe-fallback');
    const openBtn = document.getElementById('subscribe-open');
    const modal = document.getElementById('subscribe-modal');
    const api = (window.SUBSCRIBE_API || '').replace(/\/$/, '');
    if (!api) { openBtn.hidden = true; fallback.hidden = false; return; }

    /* פתיחה/סגירה של חלון ההרשמה */
    let lastFocusedSub = null;
    function openSub() {
      lastFocusedSub = document.activeElement;
      modal.hidden = false;
      document.body.style.overflow = 'hidden';
      document.getElementById('sub-email').focus();
    }
    function closeSub() {
      modal.hidden = true;
      document.body.style.overflow = '';
      if (lastFocusedSub && document.contains(lastFocusedSub)) lastFocusedSub.focus();
    }
    openBtn.addEventListener('click', openSub);
    document.getElementById('subscribe-close').addEventListener('click', closeSub);
    modal.addEventListener('click', e => { if (e.target === modal) closeSub(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && !modal.hidden) closeSub(); });
    modal.addEventListener('keydown', e => {
      if (e.key !== 'Tab') return;
      const f = modal.querySelectorAll('a[href], button, input');
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });

    const msg = document.getElementById('subscribe-msg');
    const submit = document.getElementById('subscribe-submit');
    const setMsg = (text, kind) => {
      msg.textContent = text;
      msg.className = kind ? 'subscribe-msg subscribe-msg--' + kind : '';
    };

    form.addEventListener('submit', e => {
      e.preventDefault();
      const email = form.email.value.trim();
      const day = form.querySelector('input[name="day"]:checked').value;
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
        setMsg('נראה שכתובת הדוא"ל אינה תקינה — אפשר לבדוק שוב?', 'error');
        form.email.focus();
        return;
      }
      submit.disabled = true;
      setMsg('רגע…', null);
      fetch(api + '/subscribe', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ email: email, day: day, website: form.website.value }),
      })
        .then(r => r.json().then(d => ({ ok: r.ok, d: d })).catch(() => ({ ok: false, d: {} })))
        .then(res => {
          if (!res.ok) {
            const code = res.d && res.d.error;
            if (code === 'mail_failed') {
              setMsg('ההרשמה נקלטה, אך שליחת מייל האישור נכשלה. נסו שוב מאוחר יותר.', 'error');
              return;
            }
            if (code === 'invalid_email') { setMsg('כתובת הדוא"ל אינה תקינה.', 'error'); return; }
            throw new Error(code || 'failed');
          }
          if (res.d.state === 'already') setMsg('הכתובת כבר רשומה — הכול מסודר.', 'ok');
          else if (res.d.state === 'updated') setMsg('יום הקבלה עודכן. תודה!', 'ok');
          else {
            setMsg('כמעט סיימנו — שלחנו אליכם מייל לאישור ההרשמה.', 'ok');
            form.reset();
            setTimeout(() => { if (!modal.hidden) closeSub(); }, 3500);
          }
        })
        .catch(() => setMsg('משהו השתבש בשליחה. אפשר לנסות שוב בעוד רגע.', 'error'))
        .finally(() => { submit.disabled = false; });
    });
  })();

  /* ---------- תגובות: טופס באתר + מודרציה ב-Worker ---------- */
  // התגובות נשמרות ב-Cloudflare Worker. תגובה חדשה נכנסת כ"ממתינה", אריאל מאשר
  // אותה במייל, ורק אז היא מופיעה. כתובות המייל של המגיבים נשארות בצד השרת.
  const COMMENTS_API = window.SUBSCRIBE_API || '';
  const commentsCache = new Map();   // שם פרשה -> [{name, date, text}]

  function fetchComments(name) {
    if (commentsCache.has(name)) return Promise.resolve(commentsCache.get(name));
    return fetch(COMMENTS_API + '/comments?parasha=' + encodeURIComponent(name))
      .then(r => (r.ok ? r.json() : Promise.reject(new Error('http ' + r.status))))
      .then(items => {
        const list = Array.isArray(items) ? items : [];
        commentsCache.set(name, list);
        return list;
      });
  }

  function renderCommentList(list, items) {
    list.textContent = '';
    items.forEach(c => {
      const item = el('li', 'comment');
      const head = el('div', 'comment__head');
      head.append(el('span', 'comment__name', c.name || 'אנונימי'));
      const d = new Date(c.date);
      if (!isNaN(d)) head.append(el('span', 'comment__date', d.toLocaleDateString('he-IL', { day: 'numeric', month: 'long', year: 'numeric' })));
      item.append(head, el('div', 'comment__body', c.text));
      list.append(item);
    });
  }

  // רינדור תגובות הדף בתוך עמוד הפרשה
  let currentParasha = null;
  function renderPageComments(name) {
    currentParasha = name;
    const write = document.getElementById('pc-write');
    const form = document.getElementById('pc-form');
    const note = document.getElementById('pc-note');
    const list = document.getElementById('pc-list');
    const titleEl = document.getElementById('pc-title');
    list.textContent = '';
    titleEl.textContent = 'תגובות';
    form.hidden = true;
    write.setAttribute('aria-expanded', 'false');
    document.getElementById('pc-msg').textContent = '';

    if (!COMMENTS_API) {
      write.hidden = true;
      note.textContent = 'מערכת התגובות תופעל בקרוב.';
      return;
    }
    write.hidden = false;
    note.textContent = 'טוען תגובות…';
    fetchComments(name).then(items => {
      if (currentParasha !== name) return;        // המשתמש עבר לדף אחר בינתיים
      titleEl.textContent = items.length ? 'תגובות (' + items.length + ')' : 'תגובות';
      note.textContent = items.length ? '' : 'עדיין אין תגובות לדף הזה — שמחים להיות הראשונים לשמוע מכם.';
      renderCommentList(list, [...items].reverse());
    }).catch(() => {
      if (currentParasha !== name) return;
      note.textContent = 'לא הצלחנו לטעון את התגובות כרגע. אפשר לכתוב תגובה — היא תוצג כאן לאחר אישור.';
    });
  }

  // טופס כתיבת התגובה
  (function initCommentForm() {
    const write = document.getElementById('pc-write');
    const form = document.getElementById('pc-form');
    if (!write || !form) return;
    const cancel = document.getElementById('pc-cancel');
    const submit = document.getElementById('pc-submit');
    const msg = document.getElementById('pc-msg');
    const setMsg = (t, kind) => { msg.textContent = t; msg.className = 'comment-form__msg' + (kind ? ' is-' + kind : ''); };

    const toggle = open => {
      form.hidden = !open;
      write.setAttribute('aria-expanded', String(open));
      if (open) document.getElementById('pc-text').focus();
      else { setMsg(''); write.focus(); }
    };
    write.addEventListener('click', () => toggle(form.hidden));
    cancel.addEventListener('click', () => toggle(false));

    form.addEventListener('submit', e => {
      e.preventDefault();
      const text = document.getElementById('pc-text').value.trim();
      if (!text) { setMsg('אפשר לכתוב כמה מילים?', 'error'); return; }
      submit.disabled = true;
      setMsg('שולח…');
      fetch(COMMENTS_API + '/comments', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          parasha: currentParasha,
          name: document.getElementById('pc-name').value.trim(),
          email: document.getElementById('pc-email').value.trim(),
          website: document.getElementById('pc-website').value,
          text,
        }),
      })
        .then(r => r.json().then(d => ({ ok: r.ok, d })))
        .then(res => {
          if (res.ok) {
            setMsg('תודה! התגובה נשלחה ותופיע כאן אחרי שאריאל יקרא אותה.', 'ok');
            form.reset();
            setTimeout(() => { if (!form.hidden) toggle(false); }, 4000);
            return;
          }
          const errors = {
            rate_limited: 'נשלחו כמה תגובות ברצף. אפשר לנסות שוב בעוד כמה דקות.',
            too_long: 'התגובה ארוכה מדי — עד 2000 תווים.',
            invalid_email: 'כתובת הדוא"ל אינה תקינה.',
            empty: 'אפשר לכתוב כמה מילים?',
          };
          setMsg(errors[res.d && res.d.error] || 'משהו השתבש בשליחה. אפשר לנסות שוב בעוד רגע.', 'error');
        })
        .catch(() => setMsg('משהו השתבש בשליחה. אפשר לנסות שוב בעוד רגע.', 'error'))
        .finally(() => { submit.disabled = false; });
    });
  })();

  // מונה התגובות בכרטיסים — קריאה אחת שמחזירה את כל המונים
  if (COMMENTS_API) {
    fetch(COMMENTS_API + '/comments')
      .then(r => (r.ok ? r.json() : {}))
      .then(index => {
        cardCountEls.forEach((elx, name) => {
          const n = Number(index[name]) || 0;
          if (n > 0) { elx.hidden = false; elx.lastChild.nodeValue = String(n); }
        });
      })
      .catch(() => {});
  }

  /* ---------- עמוד הדף (ניתוב לפי #p=) ---------- */
  const heroSection = document.querySelector('.hero');
  const archiveMain = document.getElementById('main-content');
  const pageEl = document.getElementById('parasha-page');
  const SITE_TITLE = 'בין הנכתב לנגלה — על פרשת השבוע מאת אריאל ז\'יטניצקי';

  function printPdf(url) {
    const f = document.createElement('iframe');
    f.style.position = 'fixed'; f.style.right = '-9999px'; f.style.width = '0'; f.style.height = '0';
    f.src = encodeURI(url);
    f.onload = () => { try { f.contentWindow.focus(); f.contentWindow.print(); } catch (e) { window.open(encodeURI(url), '_blank', 'noopener'); } };
    document.body.append(f);
  }

  function openParashaPage(name) {
    const entry = pageIndex.get(name);
    if (!entry) { closeParashaPage(); return; }
    const { p, sefer } = entry;
    const title = rowTitle(sefer, p);
    document.getElementById('parasha-page-kicker').textContent = sefer.name;
    document.getElementById('parasha-page-title').textContent = title;
    const noteEl = document.getElementById('parasha-page-note');
    noteEl.textContent = p.note || '';
    noteEl.hidden = !p.note;

    const doc = document.getElementById('parasha-page-doc');
    const actions = document.getElementById('parasha-page-actions');
    const podcastEl = document.getElementById('parasha-page-podcast');
    doc.textContent = ''; actions.textContent = ''; podcastEl.textContent = '';

    if (p.pdf && pdfExists(p.pdf)) {
      const img = document.createElement('img');
      img.className = 'parasha-page__preview';
      img.src = encodeURI(p.pdf.replace('assets/pdfs/', 'assets/previews/').replace(/\.pdf$/i, '.jpg'));
      img.alt = 'העמוד הראשון של ' + title;
      img.addEventListener('click', () => viewPdf(title, p.pdf));
      img.addEventListener('error', () => { img.style.display = 'none'; });
      doc.append(img);
      actions.append(
        button({ variant: 'primary', icon: 'eye', label: 'צפייה מלאה', ariaLabel: 'צפייה מלאה בדף ' + title, onClick: () => viewPdf(title, p.pdf) }),
        button({ variant: 'secondary', href: encodeURI(p.pdf), download: true, icon: 'download', label: 'הורדה', ariaLabel: 'הורדת ' + title + ' (PDF)' }),
        button({ variant: 'ghost', icon: 'printer', label: 'הדפסה', ariaLabel: 'הדפסת ' + title, onClick: () => printPdf(p.pdf) })
      );
    } else if (p.box) {
      actions.append(button({ variant: 'secondary', href: p.box, external: true, icon: 'external-link', label: 'פתיחה ב-Box' }));
    } else {
      doc.append(el('p', 'parasha-page__soon', 'הדף לפרשה זו יעלה בקרוב.'));
    }

    const pod = buildPodcast(p, title);
    if (pod) podcastEl.append(pod);

    renderPageComments(p.name);

    // כרטיס ההרשמה עובר לעמוד הדף (אותו אלמנט — בלי כפילות מזהים)
    const subCard = document.getElementById('subscribe-card');
    if (subCard) document.querySelector('.parasha-page__aside').append(subCard);

    heroSection.hidden = true;
    archiveMain.hidden = true;
    pageEl.hidden = false;
    document.title = title + ' — ' + SITE_TITLE;
    window.scrollTo(0, 0);
    document.getElementById('parasha-back').focus();
  }
  function closeParashaPage() {
    if (pageEl.hidden) return;
    const subCard = document.getElementById('subscribe-card');
    if (subCard) document.querySelector('.sidebar').append(subCard);   // החזרה לסרגל
    pageEl.hidden = true;
    heroSection.hidden = false;
    archiveMain.hidden = false;
    document.title = SITE_TITLE;
  }
  function handleRoute() {
    const m = /^#p=(.+)$/.exec(location.hash);
    if (m) openParashaPage(decodeURIComponent(m[1]));
    else closeParashaPage();
  }
  window.addEventListener('hashchange', handleRoute);
  handleRoute();

  /* ---------- חזרה למעלה ---------- */
  const toTop = document.getElementById('to-top');
  window.addEventListener('scroll', () => { toTop.hidden = window.scrollY < 600; }, { passive: true });
  toTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();
