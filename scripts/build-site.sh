#!/usr/bin/env bash
# מרכיב את תיקיית dist/ — רק מה שצריך להיות מוגש לגולשים.
#
# Cloudflare Pages מגיש את כל תיקיית הפלט, ובברירת המחדל (שורש הריפו) הוא הגיש
# גם את worker/ ואת scripts/. אין שם סודות — המפתחות שמורים בנפרד ב-Cloudflare
# ולא בקבצים — אבל אין סיבה שקוד השרת וכלי הבנייה יהיו נגישים מהאתר.
#
# הגדרות בפרויקט ב-Cloudflare Pages:
#   Build command:            bash scripts/build-site.sh
#   Build output directory:   dist
set -euo pipefail

cd "$(dirname "$0")/.."
rm -rf dist
mkdir -p dist

# קבצים בשורש. sitemap.xml ו-llms.txt אינם כאן — הם נוצרים למטה מ-js/data.js.
for f in index.html 404.html accessibility.html styles.css robots.txt \
         favicon.svg favicon.png CNAME _headers; do
  [ -e "$f" ] && cp "$f" dist/
done

# קובץ אימות הבעלות של Search Console (שמו משתנה)
for f in google*.html; do
  [ -e "$f" ] && cp "$f" dist/
done

# תיקיות התוכן
cp -r js tokens assets dist/

# README-ים פנימיים בתוך assets אינם חלק מהאתר
find dist/assets -name 'README.md' -delete

# עמוד HTML אמיתי לכל דף (dist/p/<שם>/), מפת האתר ו-llms.txt.
# נוצרים ולא נשמרים בגיט — מקור האמת היחיד הוא js/data.js.
node scripts/build-pages.js dist

echo "dist/ מוכן:"
du -sh dist | sed 's/^/  /'
find dist -type f | wc -l | sed 's/^/  קבצים: /'

# אימות: מה שאסור שיוגש
for bad in dist/worker dist/scripts dist/.github dist/README.md; do
  if [ -e "$bad" ]; then echo "שגיאה: $bad נכלל בפלט" >&2; exit 1; fi
done
# אימות: מה שחייב להיות
for need in dist/index.html dist/404.html dist/js/site.js dist/js/riddles.js dist/styles.css \
            dist/_headers dist/assets/fonts/fonts.css \
            dist/sitemap.xml dist/robots.txt dist/llms.txt dist/p/index.html; do
  if [ ! -e "$need" ]; then echo "שגיאה: $need חסר" >&2; exit 1; fi
done
# אימות: עמוד לכל דף שב-js/data.js
want=$(node -e 'global.window={};require("./js/data.js");
  const s=new Set();for(const f of window.PARASHA_DATA)for(const p of f.parshiot)s.add(p.name);
  console.log(s.size)')
got=$(find dist/p -mindepth 2 -name index.html | wc -l | tr -d ' ')
if [ "$want" != "$got" ]; then
  echo "שגיאה: נוצרו $got עמודי דף מתוך $want שב-js/data.js" >&2; exit 1
fi
echo "  אימות עבר ($got עמודי דף)"
