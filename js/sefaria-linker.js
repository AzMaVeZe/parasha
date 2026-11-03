/* רץ רק בתוך p/<שם>/sources.html. טוען את ה-Linker של ספריא ומפעיל אותו בלי
   ליצור קישורים: מה שהוא עושה בעמוד הזה הוא לדווח לספריא אילו מקורות הדף מצטט. */
(function () {
  var s = document.createElement('script');
  s.src = 'https://www.sefaria.org/linker.v3.js';
  s.charset = 'utf-8';
  s.onload = function () {
    if (window.sefaria && sefaria.link) {
      sefaria.link({ mode: 'link', excludeFromLinking: 'body', interfaceLang: 'hebrew', contentLang: 'hebrew' });
    }
  };
  document.head.appendChild(s);
})();
