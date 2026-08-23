/* סרגל נגישות צף — ת"י 5568 / WCAG 2.1 AA.
 *
 * עצמאי לגמרי: בונה את הכפתור והחלונית בעצמו, ולכן מספיק לכלול את הקובץ
 * בכל עמוד (index, עמודי /p/ הסטטיים, 404, הצהרת הנגישות). ההעדפות נשמרות
 * ב-localStorage ומוחלות כמחלקות על <html>; העיצוב ב-styles.css.
 *
 * לקח מרכזי מהסקיל (wcag-accessibility-widget): מצב ניגודיות ממומש בדריסת
 * משתני הצבע ולא ב-CSS filter — filter על אב של position:fixed שובר את
 * העיגון של כל האלמנטים הצפים.
 */
(function () {
  'use strict';

  var MODES = [
    { key: 'contrast', cls: 'a11y-contrast', label: 'ניגודיות גבוהה' },
    { key: 'fontLg',   cls: 'a11y-font-lg',  label: 'הגדלת תצוגה', excludes: 'fontSm' },
    { key: 'fontSm',   cls: 'a11y-font-sm',  label: 'הקטנת תצוגה', excludes: 'fontLg' },
    { key: 'readable', cls: 'a11y-readable', label: 'גופן קריא' },
    { key: 'links',    cls: 'a11y-links',    label: 'הדגשת קישורים' },
    { key: 'headings', cls: 'a11y-headings', label: 'הדגשת כותרות' },
    { key: 'noAnim',   cls: 'a11y-no-anim',  label: 'עצירת אנימציות' },
    { key: 'keyboard', cls: 'a11y-keyboard', label: 'חיווי מקלדת מוגבר' }
  ];
  var STORE = 'a11y';

  function load() {
    try { return JSON.parse(localStorage.getItem(STORE)) || {}; }
    catch (e) { return {}; }
  }
  function save(s) {
    try { localStorage.setItem(STORE, JSON.stringify(s)); } catch (e) { /* פרטי */ }
  }

  var settings = load();

  function apply() {
    var html = document.documentElement;
    MODES.forEach(function (m) { html.classList.toggle(m.cls, !!settings[m.key]); });
  }
  apply();

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text) n.textContent = text;
    return n;
  }

  document.addEventListener('DOMContentLoaded', function () {
    var root = el('div', 'a11y');
    root.setAttribute('dir', 'rtl');

    var btn = el('button', 'a11y__btn');
    btn.type = 'button';
    btn.setAttribute('aria-label', 'תפריט נגישות');
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-controls', 'a11y-panel');
    // סמל הנגישות המקובל, כ-SVG מוטמע — אין תלות בקובץ חיצוני
    btn.innerHTML =
      '<svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" fill="currentColor">' +
      '<circle cx="12" cy="4.5" r="2.2"/>' +
      '<path d="M12 8c-.9 0-4.2-.5-6.3-1l-.5 1.9c1.7.4 3.9.8 5 .9v3.1l-2.2 6.7 1.9.7 2-6h.2l2 6 1.9-.7-2.2-6.7v-3.1c1.1-.1 3.3-.5 5-.9L18.3 7C16.2 7.5 12.9 8 12 8z"/></svg>';

    var panel = el('div', 'a11y__panel');
    panel.id = 'a11y-panel';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'הגדרות נגישות');

    panel.append(el('div', 'a11y__title', 'נגישות'));

    MODES.forEach(function (m) {
      var row = el('button', 'a11y__row');
      row.type = 'button';
      row.setAttribute('role', 'switch');
      row.setAttribute('aria-checked', settings[m.key] ? 'true' : 'false');
      row.append(el('span', '', m.label));
      var track = el('span', 'a11y__track');
      track.setAttribute('aria-hidden', 'true');
      track.append(el('span', 'a11y__thumb'));
      row.append(track);
      row.addEventListener('click', function () {
        settings[m.key] = !settings[m.key];
        if (settings[m.key] && m.excludes) settings[m.excludes] = false;
        save(settings); apply(); refresh();
      });
      row._mode = m;
      panel.append(row);
    });

    var reset = el('button', 'a11y__reset', 'איפוס ההגדרות');
    reset.type = 'button';
    reset.addEventListener('click', function () {
      settings = {}; save(settings); apply(); refresh();
    });
    panel.append(reset);

    var decl = el('a', 'a11y__decl', 'הצהרת הנגישות של האתר');
    decl.href = '/accessibility.html';
    panel.append(decl);

    function refresh() {
      panel.querySelectorAll('[role="switch"]').forEach(function (row) {
        row.setAttribute('aria-checked', settings[row._mode.key] ? 'true' : 'false');
      });
    }

    function setOpen(open) {
      panel.hidden = !open;
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) { refresh(); panel.querySelector('[role="switch"]').focus(); }
    }
    btn.addEventListener('click', function () { setOpen(panel.hidden); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !panel.hidden) { setOpen(false); btn.focus(); }
    });
    document.addEventListener('mousedown', function (e) {
      if (!panel.hidden && !root.contains(e.target)) setOpen(false);
    });

    root.append(btn, panel);
    document.body.append(root);
  });
})();
