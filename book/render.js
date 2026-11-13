const { chromium } = require('playwright');
(async () => {
  const B = require('path').join(__dirname, 'build');
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  for (const s of process.argv.slice(2)) {
    const p = await b.newPage();
    p.on('pageerror', e => console.log('ERR', e.message));
    await p.goto('file://' + B + '/out/' + s + '.html');
    // ספר שלם לוקח זמן: מחכים ש-Paged.js יודיע שסיים (PagedConfig.after), ולדוגמאות הישנות — לעמוד הראשון
    await p.waitForFunction(() => window.__pagedDone || (!('PagedConfig' in window) && document.querySelectorAll('.pagedjs_page').length > 0), null, { timeout: 900000 });
    await p.waitForTimeout(2500);
    // עמוד שפותח פרק (או "על המחבר"): בלי כותרת רצה ומספר עמוד — הכותרת הגדולה כבר שם
    await p.evaluate(() => document.querySelectorAll('.pagedjs_page').forEach(pg => {
      if (pg.querySelector('.ch-head, .about h2, .legend, .intro h2, .toc h2'))
        pg.querySelectorAll('.pagedjs_margin-top .pagedjs_margin-content').forEach(e => { e.style.visibility = 'hidden' })
    }))
    const n = await p.evaluate(() => document.querySelectorAll('.pagedjs_page').length);
    await p.pdf({ path: B + '/out/' + s + '.pdf', preferCSSPageSize: true, printBackground: true });
    // בוקפוד: מספר העמודים בכפולה של 4 — עמודים ריקים בסוף (book/pad.py)
    const padded = require('child_process').execFileSync('python3', [require('path').join(__dirname, 'pad.py'), B + '/out/' + s + '.pdf']).toString().trim()
    console.log(s, 'pages', n, padded);
  }
  await b.close();
})();
