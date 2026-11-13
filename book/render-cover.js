// book/build/out/cover.html ← cover.pdf, בגודל המדויק שנקבע ב-@page (book/cover.py)
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const out = path.join(__dirname, 'build', 'out');
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage();
  await p.goto('file://' + path.join(out, 'cover.html'));
  await p.evaluate(() => document.fonts.ready);
  await p.pdf({ path: path.join(out, 'cover.pdf'), preferCSSPageSize: true, printBackground: true });
  await b.close();
  console.log(require('child_process').execFileSync('python3', [path.join(__dirname, 'crop_cover.py')]).toString().trim());
})();
