// כל הקבצים זמינים גם בתיקיית Google Drive המרוכזת:
window.DRIVE_FOLDER = 'https://drive.google.com/drive/folders/1waquTTctSg9xvaC6ehHtS4pLDhNDIP9l';

// טופס Google Forms להרשמה לרשימת התפוצה (להדביק את קישור הטופס בין הגרשיים):
window.SUBSCRIBE_FORM_URL = '';
// מערכת תגובות מבוססת Google Forms עם איסוף אימייל מאומת:
// COMMENTS_FORM_URL — קישור לטופס התגובה; COMMENTS_CSV_URL — קישור ה-CSV של גיליון
// התשובות אחרי "פרסום באינטרנט" (קובץ ‹ שיתוף ‹ פרסום באינטרנט ‹ CSV).
window.COMMENTS_FORM_URL = '';
window.COMMENTS_CSV_URL = '';

const B = id => 'https://www.box.net/shared/' + id;
// קובץ מקומי בארכיון האתר. שורה מקבלת כפתורי צפייה/הורדה רק אם הקובץ אכן קיים
// ב-assets/pdfs (נבדק בזמן טעינה), כך שאפשר להוסיף קבצים בהדרגה בלי לגעת בקוד.
const P = f => 'assets/pdfs/' + f;

window.PARASHA_DATA = [
 { id: 'bereshit', name: 'ספר בראשית', compilation: P('sefer-בראשית.pdf'), parshiot: [
  { name: 'בראשית', box: B('pztmqj0ulp'), pdf: P('bereshit-בראשית.pdf') },
  { name: 'נח', box: B('8fzottnpz9'), pdf: P('bereshit-נח.pdf') },
  { name: 'לך לך', box: B('7taibkmo3b'), pdf: P('bereshit-לך-לך.pdf') },
  { name: 'וירא', box: B('hp2ovnivbq'), pdf: P('bereshit-וירא.pdf') },
  { name: 'חיי שרה', box: B('uaf9u05b67'), pdf: P('bereshit-חיי-שרה.pdf') },
  { name: 'תולדות', box: B('fa9s1rnhmj'), pdf: P('bereshit-תולדות.pdf') },
  { name: 'ויצא', box: B('t6azco76b4'), pdf: P('bereshit-ויצא.pdf') },
  { name: 'וישלח', box: B('qsydaxq39q'), pdf: P('bereshit-וישלח.pdf') },
  { name: 'וישב', box: B('36zdx81vqr'), pdf: P('bereshit-וישב.pdf') },
  { name: 'מקץ', box: B('divfe8qyb3'), pdf: P('bereshit-מקץ.pdf') },
  { name: 'ויגש', box: B('l7y1v36820'), pdf: P('bereshit-ויגש.pdf') },
  { name: 'ויחי', box: B('qa92ennyuc'), pdf: P('bereshit-ויחי.pdf') } ] },
 { id: 'shmot', name: 'ספר שמות', compilation: P('sefer-שמות.pdf'), parshiot: [
  { name: 'שמות', box: B('xfgl8q1ql6'), pdf: P('shmot-שמות.pdf') },
  { name: 'וארא', box: B('j07xoxj06q'), pdf: P('shmot-וארא.pdf') },
  { name: 'בא', box: B('ihl79iempt'), pdf: P('shmot-בא.pdf') },
  { name: 'בשלח', box: B('9k7hx5r0td'), pdf: P('shmot-בשלח.pdf') },
  { name: 'יתרו', box: B('t319rsc6d5'), pdf: P('shmot-יתרו.pdf') },
  { name: 'משפטים', box: B('mhz8ay1jrk'), pdf: P('shmot-משפטים.pdf') },
  { name: 'תרומה', box: B('602bf5qjgf'), pdf: P('shmot-תרומה.pdf') },
  { name: 'תצוה', box: B('vpxgn200cz'), pdf: P('shmot-תצוה.pdf'), note: 'עם פורים' },
  { name: 'כי תשא', box: B('0jtsjz47rn'), pdf: P('shmot-כי-תשא.pdf') },
  { name: 'ויקהל', box: B('t6kxh7srlh'), pdf: P('shmot-ויקהל-פקודי.pdf'), note: 'עם פקודי' },
  { name: 'פקודי', box: B('t6kxh7srlh'), pdf: P('shmot-ויקהל-פקודי.pdf'), note: 'עם ויקהל' } ] },
 { id: 'vayikra', name: 'ספר ויקרא', compilation: P('sefer-ויקרא.pdf'), parshiot: [
  { name: 'ויקרא', box: B('htftjts84g'), pdf: P('vayikra-ויקרא.pdf') },
  { name: 'צו', box: B('n3c3cqmgrj'), pdf: P('vayikra-צו.pdf') },
  { name: 'שמיני', box: B('zpnf59qvns'), pdf: P('vayikra-שמיני.pdf') },
  { name: 'תזריע', box: B('ux61fbljxp'), pdf: P('vayikra-תזריע-מצורע.pdf'), note: 'עם מצורע' },
  { name: 'מצורע', box: B('ux61fbljxp'), pdf: P('vayikra-תזריע-מצורע.pdf'), note: 'עם תזריע' },
  { name: 'אחרי מות', box: B('35l04pub1f'), pdf: P('vayikra-אחרי-מות-קדושים.pdf'), note: 'עם קדושים' },
  { name: 'קדושים', box: B('35l04pub1f'), pdf: P('vayikra-אחרי-מות-קדושים.pdf'), note: 'עם אחרי מות' },
  { name: 'אמור', box: B('m1nb9pl4h2'), pdf: P('vayikra-אמור.pdf') },
  { name: 'בהר סיני', box: B('jdnp24jl98'), pdf: P('vayikra-בהר-בחוקותי.pdf'), note: 'עם בחוקותי' },
  { name: 'בחוקותי', box: B('jdnp24jl98'), pdf: P('vayikra-בהר-בחוקותי.pdf'), note: 'עם בהר' } ] },
 { id: 'bamidbar', name: 'ספר במדבר', parshiot: [
  { name: 'במדבר', box: B('d4l93mmm9v'), pdf: P('bamidbar-במדבר.pdf') },
  { name: 'נשא', box: B('gjy2ifq026'), pdf: P('bamidbar-נשא.pdf') },
  { name: 'בהעלותך', box: B('g1tupdv2a4'), pdf: P('bamidbar-בהעלותך.pdf') },
  { name: 'שלח לך', box: B('r83vpzrf1h'), pdf: P('bamidbar-שלח-לך.pdf') },
  { name: 'קרח', box: B('2c53obrtmp'), pdf: P('bamidbar-קרח.pdf') },
  { name: 'חקת', box: B('ie6m3ej27c'), pdf: P('bamidbar-חקת.pdf') },
  { name: 'בלק', box: B('1xna6q7itd'), pdf: P('bamidbar-בלק.pdf') },
  { name: 'פינחס', box: B('d6mqsne71r'), pdf: P('bamidbar-פינחס.pdf') },
  { name: 'מטות', box: B('1za94r0ral'), pdf: P('bamidbar-מטות-מסעי.pdf'), note: 'עם מסעי' },
  { name: 'מסעי', box: B('1za94r0ral'), pdf: P('bamidbar-מטות-מסעי.pdf'), note: 'עם מטות' } ] },
 { id: 'devarim', name: 'ספר דברים', parshiot: [
  { name: 'דברים', box: B('6q99obje57'), pdf: P('devarim-דברים.pdf') },
  { name: 'ואתחנן', box: B('7pp4mr4qzn'), pdf: P('devarim-ואתחנן.pdf') },
  { name: 'עקב', box: B('r0sc7opv2s'), pdf: P('devarim-עקב.pdf'), note: 'עם ט"ו באב' },
  { name: 'ראה', box: B('qi7xhzafmj'), pdf: P('devarim-ראה.pdf') },
  { name: 'שופטים', box: B('7lh0akhdvd'), pdf: P('devarim-שופטים.pdf') },
  { name: 'כי תצא', box: B('mkchdf5y6b'), pdf: P('devarim-כי-תצא.pdf') },
  { name: 'כי תבוא', box: B('f0tht066j4'), pdf: P('devarim-כי-תבוא.pdf') },
  { name: 'ניצבים', box: B('t5fs6xj46m'), pdf: P('devarim-ניצבים-וילך.pdf'), note: 'כולל וילך' },
  { name: 'וילך', box: B('t5fs6xj46m'), pdf: P('devarim-ניצבים-וילך.pdf'), note: 'עם ניצבים' },
  { name: 'האזינו', box: B('z93ie1dfsq'), pdf: P('devarim-האזינו.pdf') },
  { name: 'וזאת הברכה', box: B('jm08kfgamj'), pdf: P('devarim-וזאת-הברכה.pdf'), note: 'עם הושענא רבה' } ] },
 { id: 'chagim', name: 'חגים ומועדים', parshiot: [
  { name: 'ראש השנה', box: B('zygnmiucpj'), pdf: P('chagim-ראש-השנה.pdf') },
  { name: 'יום כיפור' },
  { name: 'סוכות', box: B('0x9rly4uzc'), pdf: P('chagim-סוכות.pdf') },
  { name: 'הושענא רבה', box: B('jm08kfgamj'), pdf: P('devarim-וזאת-הברכה.pdf'), note: 'עם וזאת הברכה' },
  { name: 'פורים', box: B('ezfumqd0o0'), pdf: P('chagim-פורים.pdf') },
  { name: 'פסח', box: B('eqdf28g8en'), pdf: P('chagim-פסח.pdf') },
  { name: 'ט"ו באב', box: B('6ys9a99z0t'), pdf: P('chagim-טו-באב.pdf') } ] },
];
