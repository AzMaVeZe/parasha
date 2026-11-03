const { chromium } = require('playwright');
(async () => {
  const B = require('path').join(__dirname, 'build');
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  for (const s of process.argv.slice(2)) {
    const p = await b.newPage();
    p.on('pageerror', e => console.log('ERR', e.message));
    await p.goto('file://' + B + '/out/' + s + '.html');
    await p.waitForFunction(() => document.querySelectorAll('.pagedjs_page').length > 0 && window.PagedPolyfill && document.fonts.status === 'loaded', null, { timeout: 60000 });
    await p.waitForTimeout(2500);
    const n = await p.evaluate(() => document.querySelectorAll('.pagedjs_page').length);
    await p.pdf({ path: B + '/out/' + s + '.pdf', preferCSSPageSize: true, printBackground: true });
    console.log(s, 'pages', n);
  }
  await b.close();
})();
