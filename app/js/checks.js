// Live checks that run in the browser: 47 rule tests, the gender swap, timing, and network calls in the student flow.
// Sets window.OPENPATH_CHECKS. The network counter (window.NET) is installed by an inline script in index.html before any module loads.
import { blankProfile, SCHEME, SCHEMES, PATH, PATHS, QUESTIONS, evaluate, evaluateAll, recommend, makePlan, relevantMissing, KAVYA, clone } from './engine.js';

function P(o){ var b = blankProfile(); b.docs = { aadhaar:true, bank:true, income:true, community:true }; Object.keys(o).forEach(function(k){ b[k] = o[k]; }); return b; }
export const CASES = [
  ['pudhumai','Girl, govt school since Class 6, joining college', P({gender:'girl', cls:13, school:'govt', since6:true}), null, 'yes'],
  ['pudhumai','Girl in Class 10, govt school since Class 6', P({gender:'girl', cls:10, school:'govt', since6:true}), null, 'later'],
  ['pudhumai','Boy, govt school, joining college', P({gender:'boy', cls:13, school:'govt', since6:true}), null, 'no'],
  ['pudhumai','Girl from a private school', P({gender:'girl', cls:13, school:'private', since6:true}), null, 'no'],
  ['pudhumai','Girl who joined govt school after Class 6', P({gender:'girl', cls:13, school:'govt', since6:false}), null, 'no'],
  ['pudhumai','Girl from a govt-aided school (Dec 2024 extension)', P({gender:'girl', cls:13, school:'aided', since6:true}), null, 'yes'],
  ['pudhumai','Third-gender student, govt school', P({gender:'third', cls:13, school:'govt', since6:true}), null, 'yes'],
  ['pudhumai','Gender not answered', P({cls:13, school:'govt', since6:true}), null, 'ask'],
  ['pudhalvan','Boy, govt school, Tamil medium, joining college', P({gender:'boy', cls:13, school:'govt', since6:true, medium:'tamil'}), null, 'yes'],
  ['pudhalvan','Boy, govt-aided school, Tamil medium', P({gender:'boy', cls:13, school:'aided', since6:true, medium:'tamil'}), null, 'yes'],
  ['pudhalvan','Boy, govt school, English medium', P({gender:'boy', cls:13, school:'govt', since6:true, medium:'english'}), null, 'no'],
  ['pudhalvan','Girl, govt school, Tamil medium', P({gender:'girl', cls:13, school:'govt', since6:true, medium:'tamil'}), null, 'no'],
  ['pudhalvan','Boy in Class 12, on track', P({gender:'boy', cls:12, school:'govt', since6:true, medium:'tamil'}), null, 'later'],
  ['quota75','Govt school since Class 6, engineering', P({cls:13, school:'govt', since6:true}), 'engineering', 'yes'],
  ['quota75','Govt-aided school, engineering', P({cls:13, school:'aided', since6:true}), 'engineering', 'no'],
  ['quota75','Govt school, nursing diploma (not covered)', P({cls:13, school:'govt', since6:true}), 'nursing', 'no'],
  ['quota75','Class 10, no course chosen yet', P({cls:10, school:'govt', since6:true}), null, 'if'],
  ['firstgrad','First graduate, engineering via counselling', P({cls:13, firstGen:true}), 'engineering', 'yes'],
  ['firstgrad','Not a first graduate', P({cls:13, firstGen:false}), 'engineering', 'no'],
  ['firstgrad','First-graduate status not answered', P({cls:13}), 'engineering', 'ask'],
  ['firstgrad','First graduate, B.Com (not covered)', P({cls:13, firstGen:true}), 'accounts', 'no'],
  ['csss','Top 20%, income ₹2.5–4.5 lakh, regular degree', P({cls:13, top20:true, income:'2.5to4.5'}), 'accounts', 'yes'],
  ['csss','Top 20%, income ₹4.5–8 lakh', P({cls:13, top20:true, income:'4.5to8'}), 'accounts', 'no'],
  ['csss','Top 20%, diploma (diplomas excluded)', P({cls:13, top20:true, income:'1to2.5'}), 'labtech', 'no'],
  ['csss','Not in top 20%', P({cls:13, top20:false, income:'lt1'}), 'accounts', 'no'],
  ['csss','Class 10, degree path, income under ₹1 lakh', P({cls:10, income:'lt1'}), 'accounts', 'later'],
  ['pragati','Girl, income ₹4.5–8 lakh, AICTE diploma', P({gender:'girl', cls:13, income:'4.5to8'}), 'civil', 'yes'],
  ['pragati','Boy, AICTE diploma', P({gender:'boy', cls:13, income:'lt1'}), 'civil', 'no'],
  ['pragati','Girl, income over ₹8 lakh', P({gender:'girl', cls:13, income:'gt8'}), 'civil', 'no'],
  ['pragati','Girl, nursing (not an AICTE course)', P({gender:'girl', cls:13, income:'lt1'}), 'nursing', 'no'],
  ['yasasvi_pre','MBC, Class 10, govt school, ₹1–2.5 lakh', P({cls:10, school:'govt', community:'MBC', income:'1to2.5'}), null, 'likely'],
  ['yasasvi_pre','DNC, Class 9, govt school, under ₹1 lakh', P({cls:9, school:'govt', community:'DNC', income:'lt1'}), null, 'yes'],
  ['yasasvi_pre','MBC, Class 10, private school', P({cls:10, school:'private', community:'MBC', income:'lt1'}), null, 'no'],
  ['yasasvi_pre','MBC, Class 10, income ₹2.5–4.5 lakh', P({cls:10, school:'govt', community:'MBC', income:'2.5to4.5'}), null, 'no'],
  ['yasasvi_pre','MBC, Class 11 (past Class 10)', P({cls:11, school:'govt', community:'MBC', income:'lt1'}), null, 'no'],
  ['yasasvi_pre','OC student', P({cls:10, school:'govt', community:'OC', income:'lt1'}), null, 'no'],
  ['yasasvi_post','BC, Class 11, under ₹1 lakh', P({cls:11, community:'BC', income:'lt1'}), null, 'likely'],
  ['yasasvi_post','BC, Class 10 (from Class 11)', P({cls:10, community:'BC', income:'lt1'}), null, 'later'],
  ['yasasvi_post','SC student (separate SC scheme)', P({cls:11, community:'SC', income:'lt1'}), null, 'no'],
  ['sc_pre','SC, Class 9, ₹1–2.5 lakh', P({cls:9, community:'SC', income:'1to2.5'}), null, 'yes'],
  ['sc_pre','SC, Class 10, income not known', P({cls:10, community:'SC', income:'unknown'}), null, 'ask'],
  ['sc_pre','SC, Class 12 (past Class 10)', P({cls:12, community:'SC', income:'lt1'}), null, 'no'],
  ['sc_post','SC, Class 12, ₹1–2.5 lakh', P({cls:12, community:'SC', income:'1to2.5'}), null, 'yes'],
  ['sc_post','SC, college, income ₹2.5–4.5 lakh', P({cls:13, community:'SC', income:'2.5to4.5'}), null, 'no'],
  ['st_post','ST, Class 11, under ₹1 lakh', P({cls:11, community:'ST', income:'lt1'}), null, 'yes'],
  ['st_post','ST, Class 10 (from Class 11)', P({cls:10, community:'ST', income:'lt1'}), null, 'later'],
  ['st_post','Community not shared', P({cls:11, community:'NA', income:'lt1'}), null, 'ask']
];
export function rng(seed){ return function(){ seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function pick(r, arr){ return arr[Math.floor(r() * arr.length)]; }
export function randomProfile(r){
  return { gender:pick(r, ['girl','boy','third']), cls:pick(r, [9,10,11,12,13]), school:pick(r, ['govt','aided','private']), since6:r() < 0.7, medium:pick(r, ['tamil','english']),
    community:pick(r, ['SC','ST','BC','MBC','DNC','OC','NA']), income:pick(r, ['lt1','1to2.5','2.5to4.5','4.5to8','gt8','unknown']), firstGen:pick(r, [true,false,'unknown']), top20:pick(r, [true,false,null]),
    docs:{ aadhaar:r() < 0.9, bank:r() < 0.6, income:r() < 0.5, community:r() < 0.6 } };
}
export function randomAnswers(r){ var a = {}; QUESTIONS.forEach(function(q){ a[q.id] = pick(r, q.opts).id; }); return a; }

let TESTS = null;
export function lastChecks(){ return TESTS; }

export function runChecks(){
  var results = CASES.map(function(c){ var got = evaluate(SCHEME[c[0]], c[2], c[3] ? PATH[c[3]] : null).status; return { scheme:SCHEME[c[0]].name.en, name:c[1], expect:c[4], got:got, pass:got === c[4] }; });
  var passed = results.filter(function(x){ return x.pass; }).length;
  var r = rng(2026), N = 1000, changed = 0;
  for (var i = 0; i < N; i++) {
    var a = randomAnswers(r), p1 = randomProfile(r), p2 = clone(p1);
    p2.gender = p1.gender === 'girl' ? 'boy' : 'girl';
    var ids = function(rec){ return rec.picks.map(function(c){ return c.path.id; }).concat(rec.wild ? [rec.wild.path.id] : []).join(','); };
    if (ids(recommend(a, p1)) !== ids(recommend(a, p2))) changed++;
  }
  var r2 = rng(7), M = 10000, profiles = [];
  for (var j = 0; j < M; j++) profiles.push([randomProfile(r2), pick(r2, PATHS.concat([null]))]);
  var t0 = performance.now();
  for (var k = 0; k < M; k++) evaluateAll(profiles[k][0], profiles[k][1]);
  var ms = performance.now() - t0;
  // Only calls made during this synchronous student-flow check count. The data load at start, voice and sync happen outside it.
  var NET = window.NET || { calls: 0 };
  var before = NET.calls;
  var flow = recommend(KAVYA.answers, KAVYA.profile), chosen = flow.picks[0].path, ev = evaluateAll(KAVYA.profile, chosen);
  makePlan(chosen, KAVYA.profile, ev); relevantMissing(ev); evaluateAll(KAVYA.profile, null);
  var calls = NET.calls - before;
  var prevKB = TESTS ? TESTS.kb : null;
  TESTS = { results:results, passed:passed, total:results.length, N:N, changed:changed, M:M, ms:ms, perMs:ms / M, calls:calls, kb:prevKB, schemes:SCHEMES.length, paths:PATHS.length, rules:SCHEMES.reduce(function(a, s){ return a + s.checks.length; }, 0) };
  publish();
  return TESTS;
}
function publish(){
  var t = TESTS;
  window.OPENPATH_CHECKS = { passed:t.passed, total:t.total, genderSwapChanged:t.changed, genderSwapN:t.N, evalMsTotal:+t.ms.toFixed(1), evalProfiles:t.M, networkCallsInFlow:t.calls, appKB:t.kb, schemes:t.schemes, paths:t.paths, ruleChecks:t.rules };
}

// App size: the total bytes the service worker precached. Null until the service worker has installed.
export function measureAppSize(){
  if (!('caches' in window)) return Promise.resolve(null);
  return caches.keys().then(function(keys){
    var ours = keys.filter(function(k){ return /^op-v\d+$/.test(k); }).sort(function(a, b){ return +b.slice(4) - +a.slice(4); });
    if (!ours.length) return null;
    return caches.open(ours[0]).then(function(c){ return c.keys().then(function(reqs){
      return Promise.all(reqs.map(function(q){ return c.match(q).then(function(res){ return res ? res.blob().then(function(b){ return b.size; }) : 0; }); }));
    }); }).then(function(sizes){ return Math.round(sizes.reduce(function(a, b){ return a + b; }, 0) / 1024); });
  }).then(function(kb){
    if (TESTS) { TESTS.kb = kb; publish(); }
    return kb;
  }).catch(function(){ return null; });
}
