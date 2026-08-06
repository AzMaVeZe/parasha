#!/usr/bin/env node
/* מייצר assets/parashot.json — מפת דפים שה-Worker קורא בזמן שליחה.
   להריץ אחרי שינוי ב-js/data.js:  node scripts/build-parashot-json.js */
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');

global.window = {};
require(path.join(root, 'js/data.js'));

const out = {};
for (const sefer of global.window.PARASHA_DATA) {
  for (const p of sefer.parshiot) {
    if (out[p.name]) continue;
    out[p.name] = {
      sefer: sefer.name,
      isChag: sefer.id === 'chagim',
      hasPdf: !!p.pdf,
      hasPodcast: !!p.spotify,
    };
  }
}

fs.writeFileSync(path.join(root, 'assets/parashot.json'), JSON.stringify(out, null, 1) + '\n');
console.log('wrote assets/parashot.json (' + Object.keys(out).length + ' entries)');
