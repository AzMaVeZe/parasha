// כל הקבצים זמינים גם בתיקיית Google Drive המרוכזת:
window.DRIVE_FOLDER = 'https://drive.google.com/drive/folders/1waquTTctSg9xvaC6ehHtS4pLDhNDIP9l';

const B = id => 'http://www.box.net/shared/' + id;
// קובץ מקומי בארכיון האתר. שורה מקבלת כפתורי צפייה/הורדה רק אם הקובץ אכן קיים
// ב-assets/pdfs (נבדק בזמן טעינה), כך שאפשר להוסיף קבצים בהדרגה בלי לגעת בקוד.
const P = f => 'assets/pdfs/' + f;

window.PARASHA_DATA = [
 { id: 'bereshit', name: 'ספר בראשית', compilation: P('sefer-בראשית.pdf'), parshiot: [
  { name: 'בראשית', box: B('pztmqj0ulp') }, { name: 'נח', box: B('8fzottnpz9') }, { name: 'לך לך', box: B('7taibkmo3b') }, { name: 'וירא', box: B('hp2ovnivbq') }, { name: 'חיי שרה', box: B('uaf9u05b67') }, { name: 'תולדות', box: B('fa9s1rnhmj'), pdf: P('bereshit-תולדות.pdf') }, { name: 'ויצא', box: B('t6azco76b4') }, { name: 'וישלח', box: B('qsydaxq39q') }, { name: 'וישב', box: B('36zdx81vqr') }, { name: 'מקץ', box: B('divfe8qyb3') }, { name: 'ויגש', box: B('l7y1v36820') }, { name: 'ויחי', box: B('qa92ennyuc') } ] },
 { id: 'shmot', name: 'ספר שמות', compilation: P('sefer-שמות.pdf'), parshiot: [
  { name: 'שמות', box: B('xfgl8q1ql6') }, { name: 'וארא', box: B('j07xoxj06q') }, { name: 'בא', box: B('ihl79iempt') }, { name: 'בשלח', box: B('9k7hx5r0td') }, { name: 'יתרו', box: B('t319rsc6d5') }, { name: 'משפטים', box: B('mhz8ay1jrk') }, { name: 'תרומה', box: B('602bf5qjgf') }, { name: 'תצוה', box: B('vpxgn200cz') }, { name: 'כי תשא', box: B('0jtsjz47rn') }, { name: 'ויקהל', box: B('t6kxh7srlh') }, { name: 'פקודי', box: B('t6kxh7srlh') } ] },
 { id: 'vayikra', name: 'ספר ויקרא', compilation: P('sefer-ויקרא.pdf'), parshiot: [
  { name: 'ויקרא', box: B('htftjts84g') }, { name: 'צו', box: B('n3c3cqmgrj') }, { name: 'שמיני', box: B('zpnf59qvns') }, { name: 'תזריע', box: B('ux61fbljxp') }, { name: 'מצורע', box: B('ux61fbljxp') }, { name: 'אחרי מות', box: B('35l04pub1f') }, { name: 'קדושים', box: B('35l04pub1f') }, { name: 'אמור', box: B('m1nb9pl4h2') }, { name: 'בהר סיני', box: B('jdnp24jl98') }, { name: 'בחוקותי', box: B('jdnp24jl98') } ] },
 { id: 'bamidbar', name: 'ספר במדבר', parshiot: [
  { name: 'במדבר', box: B('d4l93mmm9v') }, { name: 'נשא', box: B('gjy2ifq026') }, { name: 'בהעלותך', box: B('g1tupdv2a4') }, { name: 'שלח לך', box: B('r83vpzrf1h') }, { name: 'קרח', box: B('2c53obrtmp') }, { name: 'חקת', box: B('ie6m3ej27c') }, { name: 'בלק', box: B('1xna6q7itd') }, { name: 'פינחס', box: B('d6mqsne71r') }, { name: 'מטות', box: B('1za94r0ral') }, { name: 'מסעי', box: B('1za94r0ral') } ] },
 { id: 'devarim', name: 'ספר דברים', parshiot: [
  { name: 'דברים', box: B('6q99obje57'), pdf: P('devarim-דברים.pdf') }, { name: 'ואתחנן', box: B('7pp4mr4qzn'), pdf: P('devarim-ואתחנן.pdf') }, { name: 'עקב', box: B('r0sc7opv2s') }, { name: 'ראה', box: B('qi7xhzafmj') }, { name: 'שופטים', box: B('7lh0akhdvd'), pdf: P('devarim-שופטים.pdf') }, { name: 'כי תצא', box: B('mkchdf5y6b') }, { name: 'כי תבוא', box: B('f0tht066j4') }, { name: 'ניצבים', box: B('t5fs6xj46m'), pdf: P('devarim-ניצבים-וילך.pdf'), note: 'כולל וילך' }, { name: 'וילך', box: B('t5fs6xj46m'), pdf: P('devarim-ניצבים-וילך.pdf'), note: 'עם ניצבים' }, { name: 'האזינו', box: B('z93ie1dfsq') }, { name: 'וזאת הברכה', box: B('jm08kfgamj') } ] },
 { id: 'chagim', name: 'חגים ומועדים', parshiot: [
  { name: 'ראש השנה', box: B('zygnmiucpj') }, { name: 'יום כיפור' }, { name: 'סוכות', box: B('0x9rly4uzc') }, { name: 'הושענא רבה', box: B('jm08kfgamj') }, { name: 'פורים', box: B('ezfumqd0o0') }, { name: 'פסח', box: B('eqdf28g8en') }, { name: 'ט"ו באב', box: B('6ys9a99z0t') } ] },
];
