// OpenPath engine: rules, path matching and the 4-week plan. No DOM access.
// Ported from reference/openpath_prototype.html without changing behaviour.
// QUESTIONS and PATHS come from data/*.json (the server reads the same files).

export const CHECKED = '22 Nov 2026';
export function L(ta, en){ return { ta: ta, en: en }; }

/* ---------------- skills; questions and paths are loaded from JSON ---------------- */
export const SKILL = {
  numbers:L('எண்கள், கணக்கு','Numbers and accounts'), mechanical:L('இயந்திரம், பழுது நீக்குதல்','Machines and repair'),
  electrical:L('மின்சார வேலை','Electrical work'), care:L('பிறரைக் கவனித்தல்','Caring for people'),
  people:L('மக்களுடன் பேசுதல்','Talking with people'), outdoors:L('வயல், இயற்கை','Farms and outdoors'),
  craft:L('கைவேலை, வடிவமைப்பு','Craft and design'), science:L('அறிவியல்','Science'), computers:L('கணினி','Computers')
};
export const QUESTIONS = [];
// kind: iti | diploma | degree. tech: AICTE technical course. prof: professional degree (7.5% quota courses). usual: one of the five careers most students already name.
export const PATHS = [];
export const PATH = {};

let loaded = null;
// Fetches the two JSON files once (from the service-worker cache when offline) and builds PATH.
export function loadData(base){
  if (loaded) return loaded;
  base = base || 'data/';
  loaded = Promise.all([fetch(base + 'questions.json'), fetch(base + 'paths.json')])
    .then(function(rs){
      rs.forEach(function(r){ if (!r.ok) throw new Error('Could not load ' + r.url + ' (' + r.status + ')'); });
      return Promise.all(rs.map(function(r){ return r.json(); }));
    })
    .then(function(d){ setData(d[0], d[1]); });
  return loaded;
}
export function setData(questions, paths){
  QUESTIONS.length = 0; questions.forEach(function(q){ QUESTIONS.push(q); });
  PATHS.length = 0; paths.forEach(function(p){ PATHS.push(p); });
  Object.keys(PATH).forEach(function(k){ delete PATH[k]; });
  PATHS.forEach(function(p){ PATH[p.id] = p; });
}

export function skillsFrom(answers){
  var sk = {};
  QUESTIONS.forEach(function(q){
    var o = q.opts.filter(function(x){ return x.id === answers[q.id]; })[0];
    if (o) Object.keys(o.tags).forEach(function(k){ sk[k] = (sk[k] || 0) + o.tags[k]; });
  });
  return sk;
}
export function primaryTag(p){ return Object.keys(p.tags).sort(function(a, b){ return p.tags[b] - p.tags[a]; })[0]; }
// recommend() takes the profile only so tests can prove it is ignored: gender is never read here.
export function recommend(answers, profile){
  var sk = skillsFrom(answers);
  var scored = PATHS.map(function(p, i){
    var s = 0; Object.keys(p.tags).forEach(function(k){ s += p.tags[k] * (sk[k] || 0); });
    return { path:p, score:s, i:i };
  });
  var cmp = function(a, b){ return b.score - a.score || a.i - b.i; };
  scored.sort(cmp);
  var pool = scored.slice(), picks = [], usual = 0, prim = {};
  while (picks.length < 3 && pool.length) {
    var best = null, bestVal = -1e9;
    pool.forEach(function(c){
      if (c.path.usual && usual >= 1) return;
      var v = c.score - (prim[primaryTag(c.path)] ? 2 : 0);
      if (v > bestVal) { bestVal = v; best = c; }
    });
    if (!best) break;
    picks.push(best); pool.splice(pool.indexOf(best), 1);
    if (best.path.usual) usual++;
    prim[primaryTag(best.path)] = true;
  }
  if (!picks.some(function(c){ return c.path.kind !== 'degree'; })) {
    var voc = pool.filter(function(c){ return c.path.kind !== 'degree' && !c.path.usual; })[0];
    if (voc) { pool.splice(pool.indexOf(voc), 1); pool.push(picks.pop()); picks.push(voc); pool.sort(cmp); }
  }
  var wild = pool.filter(function(c){ return !c.path.usual && !prim[primaryTag(c.path)]; })[0] || pool.filter(function(c){ return !c.path.usual; })[0] || null;
  return { picks:picks, wild:wild, skills:sk };
}

/* ---------------- schemes as rules ---------------- */
// Each check returns true, false, null (we need an answer), 'likely', 'future' (met later if she stays on track) or 'path' (depends on the course she picks).
export const INC = { lt1:1, '1to2.5':2.5, '2.5to4.5':4.5, '4.5to8':8, gt8:99 };
export function incomeAtMost(p, lakh){ if (p.income == null || p.income === 'unknown') return null; return INC[p.income] <= lakh; }
export function schoolOK(p, types){
  if (p.school == null || p.since6 == null) return null;
  if (types.indexOf(p.school) < 0 || p.since6 !== true) return false;
  return (p.cls != null && p.cls < 12) ? 'future' : true;
}
export function obcDnt(p){ var c = p.community; if (c == null || c === 'NA') return null; if (c === 'DNC') return true; if (c === 'BC' || c === 'MBC') return 'likely'; return false; }
export function comm(p, want){ if (p.community == null || p.community === 'NA') return null; return p.community === want; }
export function needPath(test){ return function(p, path){ return path ? test(path) : 'path'; }; }
export function C(code, label, fn, extra){ var c = { code:code, label:label, fn:fn }; if (extra) Object.keys(extra).forEach(function(k){ c[k] = extra[k]; }); return c; }
export const STAY = L('12ஆம் வகுப்பு வரை இதே வகைப் பள்ளியில் படி','keep studying in the same kind of school till Class 12');

export const SCHEMES = [
  { id:'pudhumai', name:L('புதுமைப் பெண் திட்டம்','Pudhumai Penn'), by:'Govt of Tamil Nadu', when:'entry',
    benefit:L('பட்டம், டிப்ளமோ அல்லது ITI படிக்கும்போது மாதம் ₹1,000','₹1,000 a month during a degree, diploma or ITI'),
    checks:[
      C('gender in [girl, third]', L('மாணவி அல்லது மூன்றாம் பாலினத்தவர்','girl or third-gender student'), function(p){ return p.gender == null ? null : (p.gender === 'girl' || p.gender === 'third'); }),
      C('school in [govt, aided] && since_class6', L('6 முதல் 12 வரை அரசு அல்லது அரசு உதவி பெறும் பள்ளியில் படிப்பு','Class 6 to 12 in a government or government-aided school'), function(p){ return schoolOK(p, ['govt','aided']); }, { future:STAY })
    ], docs:['aadhaar','bank'],
    source:{ label:'Deccan Herald (2022); The News Minute (Dec 2024 extension)', url:'https://www.thenewsminute.com/tamil-nadu/stalin-to-inaugurate-extension-of-pudhumai-penn-scheme-for-school-girls' } },
  { id:'pudhalvan', name:L('தமிழ்ப் புதல்வன் திட்டம்','Tamil Pudhalvan'), by:'Govt of Tamil Nadu', when:'entry',
    benefit:L('உயர்கல்வி படிக்கும்போது மாதம் ₹1,000','₹1,000 a month during higher education'),
    checks:[
      C('gender in [boy, third]', L('மாணவர் அல்லது மூன்றாம் பாலினத்தவர்','boy or third-gender student'), function(p){ return p.gender == null ? null : (p.gender === 'boy' || p.gender === 'third'); }),
      C('school in [govt, aided] && since_class6', L('6 முதல் 12 வரை அரசு அல்லது அரசு உதவி பெறும் பள்ளியில் படிப்பு','Class 6 to 12 in a government or government-aided school'), function(p){ return schoolOK(p, ['govt','aided']); }, { future:STAY }),
      C('medium == tamil', L('தமிழ் வழியில் படிப்பு','studied in Tamil medium'), function(p){ return p.medium == null ? null : p.medium === 'tamil'; })
    ], docs:['aadhaar','bank'],
    source:{ label:'DT Next, Aug 2024', url:'https://www.dtnext.in/news/tamilnadu/cm-stalin-inaugurates-tamil-puthalvan-scheme-rs-1000-monthly-aid-to-be-given-to-college-boys-798766' } },
  { id:'quota75', name:L('அரசுப் பள்ளி மாணவர்களுக்கு 7.5% இட ஒதுக்கீடு','7.5% seats for government school students'), by:'Govt of Tamil Nadu', when:'entry',
    benefit:L('பொறியியல், மருத்துவம் போன்ற படிப்புகளில் 7.5% இடங்கள், கல்விக் கட்டண விலக்குடன்','7.5% of seats in engineering, medicine and other professional courses, with a tuition fee waiver'),
    checks:[
      C('school == govt && since_class6', L('6 முதல் 12 வரை அரசுப் பள்ளியில் படிப்பு','Class 6 to 12 in a government school'), function(p){ return schoolOK(p, ['govt']); }, { future:STAY }),
      C('course.professional', L('பொறியியல், மருத்துவம் போன்ற தொழில்முறைப் படிப்பு','a professional course such as engineering or medicine'), needPath(function(c){ return c.prof; }), { ifText:L('பொறியியல் அல்லது மருத்துவம் தேர்ந்தால்','if you choose engineering or medicine') })
    ], docs:[],
    source:{ label:'Directorate of Technical Education, Tamil Nadu', url:'https://dte.tn.gov.in/reservation-scheme' } },
  { id:'firstgrad', name:L('முதல் பட்டதாரி கல்விக் கட்டணச் சலுகை','First graduate tuition fee concession'), by:'Govt of Tamil Nadu', when:'entry',
    benefit:L('ஒற்றைச் சாளரக் கலந்தாய்வு மூலம் பொறியியலில் சேரும் முதல் தலைமுறைப் பட்டதாரிகளுக்கு ஆண்டுக்கு ₹27,500 வரை','Up to ₹27,500 a year off tuition for first-generation graduates who join engineering through counselling'),
    checks:[
      C('first_graduate == true', L('குடும்பத்தில் முதல் பட்டதாரி','first graduate in the family'), function(p){ return p.firstGen === true ? true : p.firstGen === false ? false : null; }),
      C('course == engineering (single-window counselling)', L('கலந்தாய்வு மூலம் பொறியியல் சேர்க்கை','engineering admission through single-window counselling'), needPath(function(c){ return c.id === 'engineering'; }), { ifText:L('பொறியியல் தேர்ந்தால்','if you choose engineering') })
    ], docs:[],
    source:{ label:'Directorate of Technical Education, Tamil Nadu', url:'https://dte.tn.gov.in/schemes-engineering-students' } },
  { id:'csss', name:L('மத்திய கல்லூரி உதவித்தொகை (CSSS)','Central Sector Scholarship (CSSS)'), by:'Govt of India', when:'entry',
    benefit:L('பட்டப் படிப்பின் முதல் மூன்று ஆண்டுகளுக்கு ஆண்டுக்கு ₹12,000','₹12,000 a year for the first three years of a degree'),
    checks:[
      C('class12_percentile > 80', L('+2 மதிப்பெண் வாரியத்தின் முதல் 20%-க்குள்','Class 12 marks in your board’s top 20%'), function(p){ if (p.cls != null && p.cls < 12) return 'future'; return p.top20 === true ? true : p.top20 === false ? false : null; }, { future:L('+2 மதிப்பெண் முதல் 20%-க்குள் வந்தால்','if your Class 12 marks are in the top 20%') }),
      C('family_income <= 4.5 lakh', L('குடும்ப வருமானம் ₹4.5 லட்சத்துக்குள்','family income up to ₹4.5 lakh'), function(p){ return incomeAtMost(p, 4.5); }),
      C('course.kind == degree (regular)', L('நேரடி பட்டப் படிப்பு (டிப்ளமோ இல்லை)','a regular degree, not a diploma'), needPath(function(c){ return c.kind === 'degree'; }), { ifText:L('பட்டப் படிப்பு தேர்ந்தால்','if you choose a degree') })
    ], docs:['income','aadhaar','bank'],
    source:{ label:'National Scholarship Portal, CSSS FAQ', url:'https://scholarships.gov.in/public/schemeGuidelines/FAQ_DOHE_CSSS.pdf' } },
  { id:'pragati', name:L('AICTE பிரகதி உதவித்தொகை','AICTE Pragati scholarship'), by:'AICTE, Govt of India', when:'entry',
    benefit:L('கட்டணத்துக்கு ₹30,000 வரை, மேலும் 10 மாதங்களுக்கு மாதம் ₹2,000','Up to ₹30,000 for fees, plus ₹2,000 a month for 10 months'),
    checks:[
      C('gender == girl', L('மாணவி','girl student'), function(p){ return p.gender == null ? null : p.gender === 'girl'; }),
      C('family_income <= 8 lakh', L('குடும்ப வருமானம் ₹8 லட்சத்துக்குள்','family income up to ₹8 lakh'), function(p){ return incomeAtMost(p, 8); }),
      C('course.aicte_technical && first_year', L('AICTE அங்கீகாரம் பெற்ற தொழில்நுட்ப டிப்ளமோ அல்லது பட்டம்','an AICTE-approved technical diploma or degree'), needPath(function(c){ return c.tech; }), { ifText:L('தொழில்நுட்ப டிப்ளமோ அல்லது பட்டம் தேர்ந்தால்','if you choose a technical diploma or degree') })
    ], docs:['income','aadhaar','bank'],
    source:{ label:'AICTE Pragati guidelines', url:'https://aicte.gov.in/sites/default/files/pragatisaksham.pdf' } },
  { id:'yasasvi_pre', name:L('PM யசஸ்வி: 9, 10ஆம் வகுப்பு உதவித்தொகை','PM YASASVI pre-matric (OBC, EBC, DNT)'), by:'Govt of India', when:'9-10',
    benefit:L('9, 10ஆம் வகுப்பில் ஆண்டுக்கு ₹4,000','₹4,000 a year in Class 9 and 10'),
    checks:[
      C('community in OBC/DNT', L('OBC அல்லது சீர்மரபினர் (DNT) சமூகம்','OBC or DNT community'), obcDnt),
      C('family_income <= 2.5 lakh', L('குடும்ப வருமானம் ₹2.5 லட்சத்துக்குள்','family income up to ₹2.5 lakh'), function(p){ return incomeAtMost(p, 2.5); }),
      C('school == govt', L('அரசுப் பள்ளியில் படிப்பு','studying in a government school'), function(p){ return p.school == null ? null : p.school === 'govt'; })
    ], docs:['income','community','aadhaar','bank'],
    source:{ label:'PIB backgrounder, Oct 2024', url:'https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/oct/doc20241023421901.pdf' } },
  { id:'yasasvi_post', name:L('PM யசஸ்வி: 10-க்குப் பிந்தைய உதவித்தொகை','PM YASASVI post-matric (OBC, EBC, DNT)'), by:'Govt of India', when:'11+',
    benefit:L('10ஆம் வகுப்புக்குப் பின் ஆண்டுக்கு ₹5,000 முதல் ₹20,000','₹5,000 to ₹20,000 a year after Class 10'),
    checks:[
      C('community in OBC/DNT', L('OBC அல்லது சீர்மரபினர் (DNT) சமூகம்','OBC or DNT community'), obcDnt),
      C('family_income <= 2.5 lakh', L('குடும்ப வருமானம் ₹2.5 லட்சத்துக்குள்','family income up to ₹2.5 lakh'), function(p){ return incomeAtMost(p, 2.5); })
    ], docs:['income','community','aadhaar','bank'],
    source:{ label:'PIB backgrounder, Oct 2024', url:'https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/oct/doc20241023421901.pdf' } },
  { id:'sc_pre', name:L('SC மாணவர்களுக்கான 9, 10ஆம் வகுப்பு உதவித்தொகை','Pre-matric scholarship for SC students'), by:'Govt of India', when:'9-10',
    benefit:L('9, 10ஆம் வகுப்பில் ஆண்டு உதவித்தொகை','A yearly scholarship in Class 9 and 10'),
    checks:[
      C('community == SC', L('SC சமூகம்','SC community'), function(p){ return comm(p, 'SC'); }),
      C('family_income <= 2.5 lakh', L('குடும்ப வருமானம் ₹2.5 லட்சத்துக்குள்','family income up to ₹2.5 lakh'), function(p){ return incomeAtMost(p, 2.5); })
    ], docs:['income','community','aadhaar','bank'],
    source:{ label:'Ministry of Social Justice & Empowerment', url:'https://socialjustice.gov.in/schemes/23' } },
  { id:'sc_post', name:L('SC மாணவர்களுக்கான 10-க்குப் பிந்தைய உதவித்தொகை','Post-matric scholarship for SC students'), by:'Govt of India', when:'11+',
    benefit:L('11ஆம் வகுப்பு முதல் கட்டணமும் ஆண்டு உதவியும்','Fees and a yearly allowance from Class 11 onwards'),
    checks:[
      C('community == SC', L('SC சமூகம்','SC community'), function(p){ return comm(p, 'SC'); }),
      C('family_income <= 2.5 lakh', L('குடும்ப வருமானம் ₹2.5 லட்சத்துக்குள்','family income up to ₹2.5 lakh'), function(p){ return incomeAtMost(p, 2.5); })
    ], docs:['income','community','aadhaar','bank'],
    source:{ label:'National Scholarship Portal', url:'https://scholarships.gov.in/' } },
  { id:'st_post', name:L('ST மாணவர்களுக்கான 10-க்குப் பிந்தைய உதவித்தொகை','Post-matric scholarship for ST students'), by:'Govt of India', when:'11+',
    benefit:L('11ஆம் வகுப்பு முதல் கட்டணமும் ஆண்டு உதவியும்','Fees and a yearly allowance from Class 11 onwards'),
    checks:[
      C('community == ST', L('ST சமூகம்','ST community'), function(p){ return comm(p, 'ST'); }),
      C('family_income <= 2.5 lakh', L('குடும்ப வருமானம் ₹2.5 லட்சத்துக்குள்','family income up to ₹2.5 lakh'), function(p){ return incomeAtMost(p, 2.5); })
    ], docs:['income','community','aadhaar','bank'],
    source:{ label:'National Scholarship Portal', url:'https://scholarships.gov.in/' } }
];
export const SCHEME = {}; SCHEMES.forEach(function(s){ SCHEME[s.id] = s; });

export function timing(when, cls){
  if (cls == null) return null;
  if (when === '9-10') return cls <= 10 ? 'now' : 'past';
  if (when === '11+') return cls >= 11 ? 'now' : 'later';
  return cls >= 13 ? 'now' : 'later';
}
export function evaluate(s, p, path){
  var trace = s.checks.map(function(c){ return { c:c, r:c.fn(p, path || null) }; });
  var rs = trace.map(function(x){ return x.r; });
  var tm = timing(s.when, p.cls);
  var status;
  if (rs.indexOf(false) >= 0 || tm === 'past') status = 'no';
  else if (tm == null || rs.indexOf(null) >= 0) status = 'ask';
  else if (rs.indexOf('path') >= 0) status = 'if';
  else if (tm === 'later' || rs.indexOf('future') >= 0) status = 'later';
  else status = rs.indexOf('likely') >= 0 ? 'likely' : 'yes';
  var missing = s.docs.filter(function(d){ return !(p.docs && p.docs[d] === true); });
  return { s:s, status:status, trace:trace, timing:tm, likely:rs.indexOf('likely') >= 0, missing:missing };
}
export function evaluateAll(p, path){ return SCHEMES.map(function(s){ return evaluate(s, p, path); }); }

export const DOCS = {
  aadhaar:{ name:L('ஆதார் அட்டை','Aadhaar card'), how:L('அருகிலுள்ள ஆதார் அல்லது இ-சேவை மையம்','Nearest Aadhaar or e-Sevai centre') },
  bank:{ name:L('ஆதாருடன் இணைந்த வங்கிக் கணக்கு','Bank account linked to Aadhaar'), how:L('அருகிலுள்ள வங்கி அல்லது அஞ்சலகம் (IPPB)','Nearest bank branch or post office (IPPB)') },
  income:{ name:L('வருமானச் சான்றிதழ்','Income certificate'), how:L('இ-சேவை மையம் வழியாக வட்டாட்சியர் அலுவலகம்','Taluk office, through the e-Sevai centre') },
  community:{ name:L('சாதிச் சான்றிதழ்','Community certificate'), how:L('இ-சேவை மையம் வழியாக வட்டாட்சியர் அலுவலகம்','Taluk office, through the e-Sevai centre') }
};
export const BLOCKER = { bank:'Bank account (Aadhaar)', income:'Income certificate', community:'Community certificate', aadhaar:'Aadhaar update', nopath:'No path yet' };

/* ---------------- plan ---------------- */
export function relevantMissing(evals){
  var seen = {}, out = [];
  evals.forEach(function(e){ if (['yes','likely','later'].indexOf(e.status) >= 0) e.missing.forEach(function(d){ if (!seen[d]) { seen[d] = 1; out.push(d); } }); });
  var order = ['bank','income','community','aadhaar'];
  return out.sort(function(a, b){ return order.indexOf(a) - order.indexOf(b); });
}
export const DOC_TASK = {
  bank:L('ஆதாருடன் இணைந்த வங்கிக் கணக்கைத் தொடங்கு','Open a bank account linked to Aadhaar'),
  income:L('இ-சேவை மையத்தில் வருமானச் சான்றிதழுக்கு விண்ணப்பி','Apply for an income certificate at the e-Sevai centre'),
  community:L('இ-சேவை மையத்தில் சாதிச் சான்றிதழுக்கு விண்ணப்பி','Apply for a community certificate at the e-Sevai centre'),
  aadhaar:L('ஆதார் அட்டை பதிவு செய்','Get your Aadhaar card made')
};
export function makePlan(path, p, evals){
  var weeks = [[], [], [], []], n = 0;
  function add(w, text){ weeks[w].push({ id:'t' + (++n), text:text }); }
  add(0, L(path.name.ta + ' வேலை பற்றி DIKSHA-வில் ஒரு சிறு பாடம் பார்', 'Watch a short DIKSHA lesson about the work of a ' + path.name.en.toLowerCase()));
  add(0, L('இன்னும் இரண்டு கதைகள் கேள்','Listen to two more stories'));
  add(1, L('தினமும் 20 நிமிடம் ' + path.subject.ta + ' பயிற்சி செய் (DIKSHA)', 'Practise ' + path.subject.en + ' for 20 minutes a day (DIKSHA)'));
  relevantMissing(evals).forEach(function(d, i){ add(i < 2 ? 1 : 2, DOC_TASK[d]); });
  add(2, path.visit);
  var cls = p.cls || 10;
  if (cls <= 10 && path.after === 12 && path.group) add(3, L('பெற்றோர், ஆசிரியருடன் பேசி 11ஆம் வகுப்பில் ' + path.group.ta + ' பிரிவைத் தேர்வு செய்','Decide with your parents and teacher: ' + path.group.en + ' group in Class 11'));
  else if (cls <= 10 && path.after === 10) add(3, L('பெற்றோருடன் பேசி 10-க்குப் பின் விண்ணப்பிக்கும் இடங்களின் பட்டியல் தயார் செய்','Make a list of the ITIs or polytechnics to apply to, with your parents'));
  else add(3, L('பெற்றோர், ஆசிரியருடன் பேசி விண்ணப்பிக்கும் கல்லூரிகளைத் தேர்வு செய்','Choose the colleges to apply to, with your parents and teacher'));
  return weeks;
}
export function nextDecision(path, p){
  var cls = p.cls || 10, out = [];
  if (cls === 10) out.push(L('10ஆம் வகுப்புப் பொதுத் தேர்வு: மார்ச்–ஏப்ரல் 2027 (எதிர்பார்ப்பு)','Class 10 public exam: March to April 2027 (expected)'));
  if (cls <= 10 && path.after === 10) out.push(L('10ஆம் வகுப்பு முடிவுகளுக்குப் பின் அரசு ITI / பாலிடெக்னிக்கில் விண்ணப்பி (வழக்கமாக மே–ஜூன்)','Apply to a Government ITI or polytechnic after Class 10 results (usually May to June)'));
  else if (cls <= 10) out.push(L('10ஆம் வகுப்பு முடிவுகளுக்குப் பின் 11ஆம் வகுப்புப் பிரிவைத் தேர்வு செய் (வழக்கமாக மே)','Choose your Class 11 group after Class 10 results (usually May)'));
  else if (cls <= 12) out.push(L('+2 முடிவுகளுக்குப் பின் விண்ணப்பி (வழக்கமாக மே–ஜூன்)','Apply after Class 12 results (usually May to June)'));
  else out.push(L('உதவித்தொகை விண்ணப்பம் திறந்ததும் நினைவூட்டல் வரும்','You get a reminder when scholarship applications open'));
  return out;
}

/* ---------------- class 10-B (sample data; the server seeds the same rows) ---------------- */
export const CLASSMATES = [
  ['10B-01','Anitha R','nursing',5,'bank'], ['10B-02','Karthik S','bike',8,null], ['10B-03','Divya M','labtech',3,'income'],
  ['10B-04','Ravi P',null,0,'nopath'], ['10B-05','Meena K','civil',6,null], ['10B-06','Arun K','solar',4,'aadhaar'],
  ['10B-08','Priya V','accounts',7,null], ['10B-09','Suresh T','mobile',2,'bank'], ['10B-10','Kaviya B','garment',5,null],
  ['10B-11','Vignesh R',null,0,'nopath'], ['10B-12','Deepa L','teacher',6,null], ['10B-13','Manoj G','copa',8,null],
  ['10B-14','Lakshmi N','pharma',4,'income'], ['10B-15','Sathish V','agri',3,null], ['10B-16','Revathi S','graphic',5,'community'],
  ['10B-17','Balaji M','engineering',2,'bank'], ['10B-18','Nandhini P','labtech',6,null], ['10B-19','Gokul A','solar',7,null],
  ['10B-20','Janani R',null,0,'nopath'], ['10B-21','Harish K','bike',5,null], ['10B-22','Pavithra D','nursing',8,null],
  ['10B-23','Dinesh S','civil',3,'income'], ['10B-24','Sowmya T','accounts',6,null], ['10B-25','Ajay V','mobile',1,null]
];

/* ---------------- profiles ---------------- */
export function blankProfile(){ return { gender:null, cls:null, school:null, since6:null, medium:null, community:null, income:null, firstGen:null, top20:null, docs:{ aadhaar:null, bank:null, income:null, community:null } }; }
export const KAVYA = { answers:{ home:'accounts', school:'science', style:'help' },
  profile:{ gender:'girl', cls:10, school:'govt', since6:true, medium:'tamil', community:'MBC', income:'1to2.5', firstGen:true, top20:null, docs:{ aadhaar:true, bank:false, income:false, community:true } } };
export function clone(o){ return JSON.parse(JSON.stringify(o)); }

/* ---------------- what the phone may send (built from the prototype's syncPayload) ---------------- */
// Only progress and the one blocker. Never gender, class, school, community, income, documents or answers.
export function progressOf(answers, pathId, plan, done, profile){
  var path = pathId ? PATH[pathId] : null, evals = evaluateAll(profile, path), miss = relevantMissing(evals);
  var all = plan ? [].concat.apply([], plan) : [], n = all.filter(function(t){ return done[t.id]; }).length;
  var answered = QUESTIONS.every(function(q){ return answers[q.id]; });
  var step = !answered ? 'discover' : !path ? 'paths' : 'plan';
  var blocker = !path ? 'no_path_yet' : miss[0] === 'bank' ? 'bank_account_aadhaar' : miss[0] ? miss[0] + '_certificate' : null;
  if (miss[0] === 'aadhaar') blocker = 'aadhaar';
  return { step:step, path:path ? path.id : null, plan_done:plan ? n + '/' + all.length : null, blocker:blocker };
}
