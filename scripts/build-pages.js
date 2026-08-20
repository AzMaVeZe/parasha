#!/usr/bin/env node
/* מייצר את העמודים הסטטיים של הארכיון מתוך js/data.js:
 *
 *   p/<שם>/index.html   עמוד אמיתי לכל דף — 62 עמודים
 *   p/index.html        מפת הארכיון: קישורים אמיתיים לכל הדפים
 *   sitemap.xml         כל העמודים שמותר לאנדקס
 *   llms.txt            תיאור האתר למערכות AI
 *
 * למה: האתר עצמו מנותב ב-hash (‎#p=<שם>‎). מנועי חיפוש אינם רואים מקטע כתובת
 * (fragment) כעמוד נפרד, ולכן 62 הדפים היו עמוד יחיד מבחינתם. העמודים כאן הם
 * כתובות אמיתיות שאפשר לאנדקס, לשתף ולצטט. כתובות ה-hash הישנות ממשיכות לעבוד
 * כשהיו — הן לא נגעו.
 *
 * להריץ:  node scripts/build-pages.js [תיקיית פלט]     (ברירת מחדל: dist)
 * רץ אוטומטית מתוך scripts/build-site.sh.
 */
'use strict';
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const out = path.resolve(process.argv[2] || path.join(root, 'dist'));

const SITE = 'https://parasha.azma.app';
const AUTHOR = 'אריאל ז\'יטניצקי';
const BRAND = 'בין הנכתב לנגלה';
const BRAND_FULL = 'בין הנכתב לנגלה — על פרשת השבוע';
const TAGLINE = 'דפי פרשת השבוע לצפייה, להורדה ולהדפסה לשולחן שבת ולהאזנה';

/* אותו CSP שיושב ב-index.html וב-_headers. שלושתם חייבים להישאר תואמים. */
const CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
  "font-src 'self'; img-src 'self' data:; media-src 'self'; " +
  "connect-src 'self' https://www.hebcal.com https://parasha-newsletter.azma.workers.dev; " +
  "frame-src 'self' https://open.spotify.com; object-src 'none'; base-uri 'self'; form-action 'self'";

/* ---------- טעינת הנתונים ---------- */
global.window = {};
require(path.join(root, 'js/data.js'));
require(path.join(root, 'js/pdf-manifest.js'));
require(path.join(root, 'js/riddles.js'));

const DATA = global.window.PARASHA_DATA;
const PDF_SET = new Set(global.window.PDF_FILES || []);
const RIDDLES = global.window.PARASHA_RIDDLES || {};
const SHOW_URL = global.window.SPOTIFY_SHOW_URL;

/* ---------- עזרים ---------- */
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// שם עברי -> מקטע כתובת. גרשיים יורדים ורווח הופך למקף, כמו בשמות קבצי ה-PDF:
// ט"ו באב -> טו-באב
const slug = name => name.replace(/["'׳״]/g, '').replace(/\s+/g, '-');

// js/site.js מרכיב את אותה כתובת בדפדפן. אם השניים ייפרדו, כל הקישורים
// בארכיון יובילו ל-404 — ולכן זו שגיאת בנייה ולא הערה בקוד.
const SLUG_SRC = "name.replace(/[\"'׳״]/g, '').replace(/\\s+/g, '-')";
if (!fs.readFileSync(path.join(root, 'js/site.js'), 'utf8').includes(SLUG_SRC)) {
  console.error('שגיאה: pageSlug ב-js/site.js אינו זהה ל-slug() כאן. הקישורים באתר יישברו.');
  process.exit(1);
}

// עברית בכתובת עובדת, אבל רק כשהיא מקודדת ב-percent. הכתובת המלאה נכנסת
// ל-canonical, ל-og:url ולמפת האתר; הקישורים בתוך העמודים יחסיים לשורש.
const pagePath = name => '/p/' + encodeURIComponent(slug(name)) + '/';
const pageUrl = name => SITE + pagePath(name);
const abs = p => SITE + '/' + encodeURI(p.replace(/^\//, ''));

const pdfExists = p => p && PDF_SET.has(p.replace('assets/pdfs/', ''));
const previewPath = p => p.replace('assets/pdfs/', 'assets/previews/').replace(/\.pdf$/i, '.jpg');
const fileHere = rel => fs.existsSync(path.join(root, rel));
const episodeId = url => { const m = /open\.spotify\.com\/episode\/([A-Za-z0-9]+)/.exec(url || ''); return m ? m[1] : null; };

const isChag = sefer => sefer.id === 'chagim';
const rowTitle = (sefer, p) => (isChag(sefer) ? p.name : 'פרשת ' + p.name);

/* ---------- רשימה שטוחה של כל הדפים ---------- */
const entries = [];
const seen = new Set();
for (const sefer of DATA) {
  for (const p of sefer.parshiot) {
    if (seen.has(p.name)) continue;          // אין כפילויות היום, אבל שלא תיווצר כתובת כפולה
    seen.add(p.name);
    const hasPdf = pdfExists(p.pdf);
    const preview = hasPdf && fileHere(previewPath(p.pdf)) ? previewPath(p.pdf) : null;
    entries.push({
      p, sefer, name: p.name, note: p.note || '',
      title: rowTitle(sefer, p),
      url: pageUrl(p.name),
      href: pagePath(p.name),
      pdf: hasPdf ? p.pdf : null,
      preview,
      episode: episodeId(p.spotify),
      riddle: RIDDLES[p.name] || null,
      // עמוד בלי דף אינו ראוי לאינדוקס — אין בו תוכן. הוא עדיין נוצר, כדי
      // שהניווט והקישורים לא ישברו, אבל מסומן noindex ואינו במפת האתר.
      indexable: hasPdf,
    });
  }
}
entries.forEach((e, i) => { e.prev = entries[i - 1] || null; e.next = entries[i + 1] || null; });

/* ---------- טקסטים ---------- */
function metaTitle(e) {
  const kind = isChag(e.sefer) ? 'דף לימוד' : 'דף לשולחן שבת';
  return e.title + ' — ' + kind + ' · ' + BRAND;
}
function metaDescription(e) {
  if (!e.pdf) return e.title + ' — ' + BRAND + ', דפי פרשת השבוע מאת ' + AUTHOR + '. הדף לפרשה זו יעלה בקרוב; הארכיון המלא באתר.';
  let d = 'דף ' + (isChag(e.sefer) ? '' : 'פרשת ') + e.name + ' מתוך "' + BRAND + '" מאת ' + AUTHOR +
    ' — לצפייה, להורדה ולהדפסה לשולחן שבת';
  d += e.episode ? ', ולהאזנה לפרק הפודקאסט.' : '.';
  return d;
}
function introText(e) {
  const parts = [];
  if (e.pdf) {
    parts.push('"' + e.title + '" — דף מתוך "' + BRAND_FULL + '", סדרת דפי פרשת השבוע של ' + AUTHOR + ': ' +
      'קריאה מחודשת בפסוקים, שאלות, מדרשים והרבה סימני שאלה. הדף מיועד לצפייה, להורדה ולהדפסה לשולחן שבת.');
    if (e.note) parts.push('הדף מוגש ' + e.note + '.');
    if (e.episode) parts.push('על הדף הזה יש גם פרק פודקאסט, להאזנה כאן או בספוטיפיי.');
  } else {
    parts.push('הדף ל' + e.name + ' טרם עלה לארכיון. שאר הדפים — כל חמשת חומשי תורה והחגים — נמצאים בארכיון המלא.');
  }
  return parts;
}

/* ---------- רכיבי HTML משותפים ---------- */
function iconSpan(name, size, extra) {
  return '<span class="icon" aria-hidden="true" style="--icon:url(\'/assets/icons/' + name +
    '.svg\');width:' + size + 'px;height:' + size + 'px' + (extra ? ';' + extra : '') + '"></span>';
}
const header = `<header class="site-header">
  <div class="container site-header__inner">
    <a href="/" class="wordmark">
      <span class="wordmark__title">${BRAND}</span>
      <span class="wordmark__sub">על פרשת השבוע · <span class="wordmark__byline">מאת ${AUTHOR}</span></span>
    </a>
    <nav class="site-nav" aria-label="ניווט ראשי">
      <a href="/">הארכיון</a>
      <a href="/p/">כל הדפים</a>
    </nav>
  </div>
</header>`;

const footer = `<footer class="site-footer">
  <div class="container site-footer__inner">
    <div>
      <div class="site-footer__brand">${BRAND_FULL}</div>
      <div class="site-footer__byline">מאת ${AUTHOR}</div>
    </div>
    <div style="display:flex;gap:16px;flex-wrap:wrap">
      <a href="/">הארכיון המלא</a>
      <a href="/p/">כל הדפים</a>
      <a href="/accessibility.html">הצהרת נגישות</a>
    </div>
  </div>
</footer>`;

function head(o) {
  const robots = o.noindex
    ? 'noindex, follow'
    : 'index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1';
  const image = o.image || abs('assets/og-image.png');
  return `<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="${esc(CSP)}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>${esc(o.title)}</title>
<meta name="description" content="${esc(o.description)}">
<meta name="author" content="${esc(AUTHOR)}">
<meta name="robots" content="${robots}">
<link rel="canonical" href="${esc(o.url)}">
<meta property="og:type" content="${o.ogType || 'website'}">
<meta property="og:site_name" content="${esc(BRAND_FULL)}">
<meta property="og:title" content="${esc(o.ogTitle || o.title)}">
<meta property="og:description" content="${esc(o.description)}">
<meta property="og:url" content="${esc(o.url)}">
<meta property="og:image" content="${esc(image)}">
<meta property="og:image:alt" content="${esc(o.imageAlt || BRAND_FULL)}">
<meta property="og:locale" content="he_IL">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(o.ogTitle || o.title)}">
<meta name="twitter:description" content="${esc(o.description)}">
<meta name="twitter:image" content="${esc(abs('assets/og-image.png'))}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.png" type="image/png" sizes="48x48">
<link rel="stylesheet" href="/styles.css">
<script type="application/ld+json">
${JSON.stringify(o.jsonld, null, 1)}
</script>
</head>
<body>
<a href="#main-content" class="skip-link">דלג לתוכן הראשי</a>
${header}`;
}

/* ---------- צמתים משותפים ל-JSON-LD ---------- */
const personNode = {
  '@type': 'Person',
  '@id': SITE + '/#author',
  name: AUTHOR,
  url: SITE + '/',
  jobTitle: 'כותב דפי פרשת השבוע',
  sameAs: ['https://ariel-parasha.blogspot.com/'].concat(SHOW_URL ? [SHOW_URL] : []),
};
const websiteNode = {
  '@type': 'WebSite',
  '@id': SITE + '/#website',
  url: SITE + '/',
  name: BRAND_FULL,
  alternateName: BRAND,
  description: TAGLINE + ' — הארכיון המלא לפי חמשת חומשי תורה, חגים ומועדים.',
  inLanguage: 'he-IL',
  author: { '@id': SITE + '/#author' },
  publisher: { '@id': SITE + '/#author' },
};
const podcastNode = SHOW_URL ? {
  '@type': 'PodcastSeries',
  '@id': SITE + '/#podcast',
  name: BRAND + ' — הפודקאסט',
  description: 'פרקי פודקאסט על דפי פרשת השבוע של ' + AUTHOR + '.',
  url: SHOW_URL,
  webFeed: SHOW_URL,
  inLanguage: 'he-IL',
  author: { '@id': SITE + '/#author' },
} : null;
const baseGraph = () => [websiteNode, personNode].concat(podcastNode ? [podcastNode] : []);

/* ---------- עמוד דף בודד ---------- */
function parashaPage(e) {
  const url = e.url;
  const pdfUrl = e.pdf ? abs(e.pdf) : null;
  const previewUrl = e.preview ? abs(e.preview) : null;
  const seferAnchor = '/#' + e.sefer.id;

  /* --- JSON-LD --- */
  const graph = baseGraph();
  graph.push({
    '@type': 'BreadcrumbList',
    '@id': url + '#breadcrumb',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'הארכיון', item: SITE + '/' },
      { '@type': 'ListItem', position: 2, name: 'כל הדפים', item: SITE + '/p/' },
      { '@type': 'ListItem', position: 3, name: e.title },
    ],
  });
  const webPage = {
    '@type': 'WebPage',
    '@id': url + '#webpage',
    url: url,
    name: metaTitle(e),
    description: metaDescription(e),
    inLanguage: 'he-IL',
    isPartOf: { '@id': SITE + '/#website' },
    breadcrumb: { '@id': url + '#breadcrumb' },
    about: { '@type': 'Thing', name: e.title },
  };
  if (previewUrl) webPage.primaryImageOfPage = { '@id': url + '#primaryimage' };
  graph.push(webPage);

  if (previewUrl) {
    graph.push({
      '@type': 'ImageObject',
      '@id': url + '#primaryimage',
      url: previewUrl,
      contentUrl: previewUrl,
      caption: 'העמוד הראשון של ' + e.title,
      width: 720,
    });
  }
  if (pdfUrl) {
    graph.push({
      '@type': 'Article',
      '@id': url + '#article',
      headline: e.title,
      name: metaTitle(e),
      description: metaDescription(e),
      inLanguage: 'he-IL',
      articleSection: e.sefer.name,
      isPartOf: { '@id': SITE + '/#website' },
      mainEntityOfPage: { '@id': url + '#webpage' },
      author: { '@id': SITE + '/#author' },
      publisher: { '@id': SITE + '/#author' },
      about: { '@type': 'Thing', name: e.title },
      keywords: [e.title, e.name, 'פרשת השבוע', 'דף לשולחן שבת', e.sefer.name].join(', '),
      associatedMedia: { '@id': pdfUrl },
      image: previewUrl || undefined,
    });
    graph.push({
      '@type': 'DigitalDocument',
      '@id': pdfUrl,
      name: e.title + ' (PDF)',
      url: pdfUrl,
      contentUrl: pdfUrl,
      encodingFormat: 'application/pdf',
      inLanguage: 'he-IL',
      author: { '@id': SITE + '/#author' },
    });
  }
  if (e.episode && podcastNode) {
    const epUrl = 'https://open.spotify.com/episode/' + e.episode;
    graph.push({
      '@type': 'PodcastEpisode',
      '@id': url + '#episode',
      name: 'פודקאסט — ' + e.title,
      url: epUrl,
      inLanguage: 'he-IL',
      partOfSeries: { '@id': SITE + '/#podcast' },
      author: { '@id': SITE + '/#author' },
      associatedMedia: { '@type': 'MediaObject', contentUrl: epUrl },
    });
  }

  /* --- גוף העמוד --- */
  let main = '';
  main += `<main class="parasha-page container" id="main-content">
  <nav class="parasha-page__back" aria-label="מיקום בארכיון">
    ${iconSpan('chevron-left', 16, 'transform:scaleX(-1)')}
    <a href="/">הארכיון</a>
    <span aria-hidden="true">·</span>
    <a href="/p/">כל הדפים</a>
    <span aria-hidden="true">·</span>
    <a href="${esc(seferAnchor)}">${esc(e.sefer.name)}</a>
  </nav>
  <div class="parasha-page__head">
    <div>
      <div class="parasha-page__kicker">${esc(e.sefer.name)}</div>
      <h1>${esc(e.title)}</h1>
    </div>${e.note ? `
    <span class="parasha-row__note">${esc(e.note)}</span>` : ''}
  </div>

  <div class="parasha-page__grid">
    <div class="parasha-page__main">`;

  introText(e).forEach(t => { main += `\n      <p>${esc(t)}</p>`; });

  if (e.pdf) {
    if (e.preview) {
      main += `\n      <div class="parasha-page__doc">
        <a href="${esc(encodeURI('/' + e.pdf))}">
          <img class="parasha-page__preview" src="${esc(encodeURI('/' + e.preview))}"
               alt="העמוד הראשון של ${esc(e.title)}" width="720" loading="lazy">
        </a>
      </div>`;
    }
    main += `\n      <div class="parasha-page__actions">
        <a class="btn btn--primary" href="${esc(encodeURI('/' + e.pdf))}">${iconSpan('eye', 17)}צפייה בדף (PDF)</a>
        <a class="btn btn--secondary" href="${esc(encodeURI('/' + e.pdf))}" download>${iconSpan('download', 17)}הורדה</a>
        <a class="btn btn--ghost" href="/#p=${esc(encodeURIComponent(e.name))}">${iconSpan('book-open', 17)}לעמוד הדף באתר (תגובות)</a>
      </div>`;
  } else if (e.p.box) {
    main += `\n      <div class="parasha-page__actions">
        <a class="btn btn--secondary" href="${esc(e.p.box)}" target="_blank" rel="noopener noreferrer">${iconSpan('external-link', 17)}פתיחה ב-Box</a>
      </div>`;
  }

  if (e.riddle) {
    const r = e.riddle;
    const flat = s => s.replace(/\s+/g, ' ').trim();
    const img = r.img ? `<img class="riddle-box__img" src="${esc(encodeURI('/assets/riddles/' + r.img))}"
          alt="החידה כפי שהיא מופיעה בדף ${esc(e.name)}: ${esc(flat(r.q))}" loading="lazy">` : '';
    const text = (!r.img || r.withText)
      ? r.q.split('\n').map(line => `<p style="margin:0 0 6px">${esc(line)}</p>`).join('\n          ')
      : '';
    main += `\n      <section class="riddle-box" style="margin-top:8px">
        <h2 class="riddle-box__title">${iconSpan('lightbulb', 17)}חידה לשולחן שבת — ${esc(e.name)}</h2>
        <div class="riddle-box__body">
          ${img}${text}
        </div>
      </section>`;
  }

  main += `\n    </div>

    <aside class="parasha-page__aside">`;

  if (e.episode) {
    main += `
      <div class="parasha-page__podcast">
        <div class="podcast">
          <div class="podcast__title">האזנה לפודקאסט</div>
          <iframe src="https://open.spotify.com/embed/episode/${esc(e.episode)}?utm_source=generator"
                  title="נגן ספוטיפיי — פודקאסט על ${esc(e.title)}" height="152" loading="lazy"
                  style="border-radius:12px" allow="encrypted-media"></iframe>
          <a class="podcast__link" href="https://open.spotify.com/episode/${esc(e.episode)}" target="_blank" rel="noopener noreferrer">פתיחת הפרק בספוטיפיי<span class="visually-hidden"> (נפתח בחלון חדש)</span></a>
        </div>
      </div>`;
  } else if (SHOW_URL) {
    main += `
      <div class="parasha-page__podcast">
        <div class="podcast">
          <div class="podcast__title">הפודקאסט</div>
          <a class="podcast__showlink" href="${esc(SHOW_URL)}" target="_blank" rel="noopener noreferrer">כל פרקי "${esc(BRAND)}" בספוטיפיי<span class="visually-hidden"> (נפתח בחלון חדש)</span></a>
        </div>
      </div>`;
  }

  if (e.sefer.compilation && pdfExists(e.sefer.compilation)) {
    main += `
      <div class="side-card">
        <h2 class="side-card__title">האסופה המלאה</h2>
        <p style="margin:8px 0 0"><a href="${esc(encodeURI('/' + e.sefer.compilation))}" download>כל דפי ${esc(e.sefer.name)} בקובץ אחד (PDF)</a></p>
      </div>`;
  }

  main += `
      <nav class="side-card" aria-label="דפים סמוכים">
        <h2 class="side-card__title">דפים נוספים</h2>
        <ul style="list-style:none;margin:8px 0 0;padding:0;display:flex;flex-direction:column;gap:6px">`;
  if (e.prev) main += `\n          <li>הקודם: <a href="${esc(e.prev.href)}">${esc(e.prev.title)}</a></li>`;
  if (e.next) main += `\n          <li>הבא: <a href="${esc(e.next.href)}">${esc(e.next.title)}</a></li>`;
  main += `\n          <li><a href="/p/">כל ${entries.length} הדפים</a></li>
          <li><a href="/">הארכיון, החיפוש והרשמה לקבלת הדף בדוא"ל</a></li>
        </ul>
      </nav>
    </aside>
  </div>
</main>`;

  return head({
    title: metaTitle(e),
    ogTitle: e.title + ' — ' + BRAND,
    description: metaDescription(e),
    url: url,
    ogType: 'article',
    image: previewUrl,
    imageAlt: 'העמוד הראשון של ' + e.title,
    noindex: !e.indexable,
    jsonld: { '@context': 'https://schema.org', '@graph': graph },
  }) + '\n' + main + '\n' + footer + '\n</body>\n</html>\n';
}

/* ---------- מפת הארכיון: /p/ ---------- */
function indexPage() {
  const url = SITE + '/p/';
  const graph = baseGraph();
  graph.push({
    '@type': 'CollectionPage',
    '@id': url + '#webpage',
    url: url,
    name: 'כל הדפים — ' + BRAND_FULL,
    description: 'מפת הארכיון: קישור לכל אחד מ-' + entries.length + ' דפי פרשת השבוע והחגים של ' + AUTHOR + '.',
    inLanguage: 'he-IL',
    isPartOf: { '@id': SITE + '/#website' },
    mainEntity: { '@id': url + '#list' },
  });
  graph.push({
    '@type': 'ItemList',
    '@id': url + '#list',
    name: 'דפי פרשת השבוע והחגים',
    numberOfItems: entries.length,
    itemListOrder: 'https://schema.org/ItemListOrderAscending',
    itemListElement: entries.map((e, i) => ({
      '@type': 'ListItem', position: i + 1, name: e.title, url: e.url,
    })),
  });

  let main = `<main class="site-main container" id="main-content" style="padding-block:32px 64px">
  <div class="parasha-page__head">
    <div>
      <div class="parasha-page__kicker">${esc(BRAND_FULL)}</div>
      <h1>כל הדפים</h1>
    </div>
  </div>
  <p style="max-width:70ch">כל ${entries.length} דפי פרשת השבוע והחגים של ${esc(AUTHOR)}, לפי סדר הארכיון. לכל דף עמוד משלו, ובו הדף לצפייה ולהורדה, פרק הפודקאסט אם קיים, והחידה שבדף.</p>
`;
  for (const sefer of DATA) {
    const list = entries.filter(e => e.sefer === sefer);
    if (!list.length) continue;
    main += `\n  <section class="sefer-section" id="${esc(sefer.id)}">
    <div class="section-header">
      <div>
        <h2>${esc(sefer.name)}</h2>
        <div class="section-header__subtitle">${list.length} דפים</div>
      </div>
    </div>
    <ul class="sefer-section__list">`;
    for (const e of list) {
      main += `
      <li class="parasha-row${e.pdf ? ' parasha-row--has-pdf' : ''}">
        <a class="parasha-row__link" href="${esc(e.url)}">
          <span class="parasha-row__head">
            ${iconSpan('file-text', 18).replace('class="icon"', 'class="icon parasha-row__icon"')}
            <span class="parasha-row__name">${esc(e.name)}</span>${e.note ? `<span class="parasha-row__note">${esc(e.note)}</span>` : ''}
          </span>
          <span class="parasha-row__meta">
            ${e.pdf ? '<span class="parasha-row__metaitem">דף לצפייה</span>' : '<span class="parasha-row__soon">בקרוב</span>'}
            ${e.episode ? '<span class="parasha-row__metaitem">פודקאסט</span>' : ''}
          </span>
        </a>
      </li>`;
    }
    main += `\n    </ul>
  </section>`;
  }
  main += '\n</main>';

  return head({
    title: 'כל הדפים — ' + BRAND_FULL,
    description: 'מפת הארכיון: כל ' + entries.length + ' דפי פרשת השבוע והחגים מאת ' + AUTHOR + ' — לכל דף עמוד משלו, לצפייה, להורדה ולהאזנה.',
    url: url,
    jsonld: { '@context': 'https://schema.org', '@graph': graph },
  }) + '\n' + main + '\n' + footer + '\n</body>\n</html>\n';
}

/* ---------- sitemap.xml ---------- */
function sitemap() {
  const urls = [
    { loc: SITE + '/', changefreq: 'weekly', priority: '1.0' },
    { loc: SITE + '/p/', changefreq: 'weekly', priority: '0.8' },
  ];
  entries.filter(e => e.indexable).forEach(e => {
    urls.push({ loc: e.url, changefreq: 'yearly', priority: '0.7' });
  });
  urls.push({ loc: SITE + '/accessibility.html', changefreq: 'yearly', priority: '0.3' });

  return '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<!-- נוצר ע"י scripts/build-pages.js — לא לערוך ידנית -->\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    urls.map(u => '  <url>\n    <loc>' + esc(u.loc) + '</loc>\n' +
      '    <changefreq>' + u.changefreq + '</changefreq>\n' +
      '    <priority>' + u.priority + '</priority>\n  </url>').join('\n') +
    '\n</urlset>\n';
}

/* ---------- llms.txt ---------- */
function llmsTxt() {
  const L = [];
  L.push('# ' + BRAND_FULL);
  L.push('');
  L.push('> ' + TAGLINE + '. אתר הארכיון של דפי פרשת השבוע שכתב ' + AUTHOR +
    ' והפיץ בדוא"ל לאורך השנים: קריאה מחודשת בפסוקים, שאלות, מדרשים וחידות. ' +
    entries.length + ' דפים — חמשת חומשי תורה, חגים ומועדים. עברית.');
  L.push('');
  L.push('האתר סטטי וללא מנוי. לכל דף עמוד HTML משלו תחת /p/, ולצדו קובץ ה-PDF המלא של הדף.');
  L.push('התוכן פתוח לציטוט ולהפניה, בבקשה עם ייחוס ל' + AUTHOR + ' וקישור לעמוד הדף.');
  L.push('');
  L.push('## עיקרי האתר');
  L.push('');
  L.push('- [הארכיון](' + SITE + '/): עמוד הבית, חיפוש והפרשה הקרובה');
  L.push('- [כל הדפים](' + SITE + '/p/): מפת הארכיון, קישור לכל ' + entries.length + ' הדפים');
  if (SHOW_URL) L.push('- [הפודקאסט](' + SHOW_URL + '): פרקים על דפי הפרשה');
  L.push('- [הצהרת נגישות](' + SITE + '/accessibility.html)');
  L.push('- [הבלוג הישן](https://ariel-parasha.blogspot.com/): הארכיון שקדם לאתר');
  L.push('');
  for (const sefer of DATA) {
    const list = entries.filter(e => e.sefer === sefer);
    if (!list.length) continue;
    L.push('## ' + sefer.name);
    L.push('');
    for (const e of list) {
      const bits = [];
      if (e.pdf) bits.push('PDF: ' + abs(e.pdf)); else bits.push('הדף טרם עלה');
      if (e.episode) bits.push('פודקאסט: https://open.spotify.com/episode/' + e.episode);
      L.push('- [' + e.title + '](' + e.url + '): ' + bits.join(' · '));
    }
    L.push('');
  }
  return L.join('\n');
}

/* ---------- כתיבה ---------- */
function write(rel, content) {
  const file = path.join(out, rel);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
}

let pages = 0;
for (const e of entries) {
  write(path.join('p', slug(e.name), 'index.html'), parashaPage(e));
  pages++;
}
write(path.join('p', 'index.html'), indexPage());
write('sitemap.xml', sitemap());
write('llms.txt', llmsTxt());

const indexable = entries.filter(e => e.indexable).length;
console.log('build-pages: ' + pages + ' עמודי דף (' + indexable + ' לאינדוקס), p/index.html, sitemap.xml, llms.txt → ' + path.relative(root, out) + '/');
if (pages !== 62) console.warn('  שימו לב: נוצרו ' + pages + ' עמודים ולא 62 — האם js/data.js השתנה?');
