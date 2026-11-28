// Screens, sheets and render for the student app. Ported from the Round 2 prototype; the rules live in engine.js.
import { CHECKED, L, SKILL, QUESTIONS, PATHS, PATH, loadData, skillsFrom, recommend, SCHEMES, SCHEME, evaluate, evaluateAll,
  DOCS, relevantMissing, makePlan, nextDecision, blankProfile, KAVYA, clone, progressOf } from './engine.js';
import { esc, bi, joinL, catL, STR } from './strings.js';
import { runChecks, lastChecks, measureAppSize } from './checks.js';
import { initAudio, playClips, stopClips } from './audio.js';
import { startRecording, stopRecording, cancelRecording, isRecording, sendTalk } from './voice.js';
import { initSync, enqueue, queueCount, syncedAt, clearQueue, netFailed } from './sync.js';

const KAVYA_ROLL = '10B-07';      // Kavya's roll number in class 10-B
let APP_VERSION = null;           // the service-worker cache name, e.g. op-v3
let EVAL = null;                  // data/eval_results.json, if it exists

/* ---------------- icons ---------------- */
var ICON = {
  ledger:'<rect x="5" y="3" width="14" height="18" rx="1.5"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  wrench:'<path d="M14.5 4.5a4 4 0 0 0-5 5L4 15l3 3 5.5-5.5a4 4 0 0 0 5-5l-2.5 2.5-2.5-.5-.5-2.5z"/>',
  care:'<circle cx="8" cy="7" r="2.5"/><circle cx="16" cy="8.5" r="2"/><path d="M3.5 19c.5-4 2.5-6 4.5-6s4 2 4.5 6M12.5 19c.4-3 1.8-4.5 3.5-4.5s3.1 1.5 3.5 4.5"/>',
  sprout:'<path d="M12 21v-9"/><path d="M12 12c0-4 3-6 7-6 0 4-3 6-7 6zM12 14c0-3-2.5-5-6-5 0 3 2.5 5 6 5z"/>',
  needle:'<path d="M5 19 18 6"/><circle cx="18.5" cy="5.5" r="1.5"/><path d="M5 19c3 1 6-1 7-4s4-4 7-3"/>',
  abacus:'<rect x="4" y="4" width="16" height="16" rx="1.5"/><path d="M4 9h16M4 15h16"/><circle cx="8" cy="9" r="1.3"/><circle cx="11" cy="9" r="1.3"/><circle cx="14" cy="15" r="1.3"/><circle cx="17" cy="15" r="1.3"/>',
  flask:'<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4A2 2 0 0 0 19 18l-5-9V3"/><path d="M7.5 15h9"/>',
  screen:'<rect x="3" y="4" width="18" height="12" rx="1.5"/><path d="M9 20h6M12 16v4"/>',
  speech:'<path d="M4 5h16v10H9l-4 4v-4H4z"/>',
  brush:'<path d="M14 4l6 6-8 8-3-3z"/><path d="M9 15c-3 0-4 2-4 5 3 0 5-1 5-4"/>',
  hammer:'<path d="M14 6l4 4M5 19l9-9"/><path d="M12 4l3-1 6 6-1 3-3-3-2 2-3-3z"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  mic:'<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/>',
  stop:'<rect x="6" y="6" width="12" height="12" rx="1.5"/>',
  speaker:'<path d="M4 9h4l5-4v14l-5-4H4z"/><path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a7.5 7.5 0 0 1 0 11"/>',
  lock:'<rect x="5" y="11" width="14" height="10" rx="1.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  gear:'<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
  compass:'<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
  route:'<circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 18h6a3 3 0 0 0 0-6h-4a3 3 0 0 1 0-6h6"/>',
  calendar:'<rect x="4" y="5" width="16" height="15" rx="1.5"/><path d="M4 10h16M9 3v4M15 3v4"/>',
  shield:'<path d="M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
  play:'<path d="M8 5l11 7-11 7z"/>',
  wifi:'<path d="M2 9a15 15 0 0 1 20 0M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0"/><circle cx="12" cy="19" r="1"/>'
};
function ic(name){ return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[name] + '</svg>'; }

var PIN_SVG = {
  sun:'<svg viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="9" fill="var(--ochre)"/><path d="M24 5v6M24 37v6M5 24h6M37 24h6M10.6 10.6l4.2 4.2M33.2 33.2l4.2 4.2M10.6 37.4l4.2-4.2M33.2 14.8l4.2-4.2" stroke="var(--ochre)" stroke-width="3" stroke-linecap="round" fill="none"/></svg>',
  star:'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 6l5.3 11.6 12.7 1.3-9.5 8.6 2.7 12.5L24 33.6 12.8 40l2.7-12.5L6 18.9l12.7-1.3z" fill="var(--green)"/></svg>',
  leaf:'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M10 38C10 20 22 9 40 8c0 18-11 30-30 30z" fill="var(--green)"/><path d="M12 36 32 16" stroke="var(--surface)" stroke-width="2.5" fill="none"/></svg>',
  fish:'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M6 24c6-9 18-12 28-4l8-6v20l-8-6C24 36 12 33 6 24z" fill="var(--ink)"/><circle cx="16" cy="22" r="2" fill="var(--surface)"/></svg>',
  moon:'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M30 6a18 18 0 1 0 12 30A15 15 0 0 1 30 6z" fill="var(--muted)"/></svg>',
  flower:'<svg viewBox="0 0 48 48" aria-hidden="true"><g fill="var(--ochre)"><circle cx="24" cy="13" r="7"/><circle cx="35" cy="22" r="7"/><circle cx="31" cy="35" r="7"/><circle cx="17" cy="35" r="7"/><circle cx="13" cy="22" r="7"/></g><circle cx="24" cy="26" r="5" fill="var(--green)"/></svg>'
};
var PIN_NAME = { sun:L('சூரியன்','sun'), star:L('நட்சத்திரம்','star'), leaf:L('இலை','leaf'), fish:L('மீன்','fish'), moon:L('நிலா','moon'), flower:L('பூ','flower') };
var PIN_CODE = { kavya:['sun','leaf','star'], anbu:['fish','moon','flower'] };

/* ---------------- state ---------------- */
var S;
function store(k, v){ try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
function recall(k){ try { var v = localStorage.getItem(k); return v == null ? null : JSON.parse(v); } catch (e) { return null; } }
function freshState(){
  return { lang:recall('op.lang') || 'bi', screen:'lock', who:null, user:null, greet:null, pin:[], pinMsg:null, reg:null, answers:{}, profile:blankProfile(),
    path:null, plan:null, done:{}, story:null, sheet:null, panel:'rules', prevScreen:null };
}
S = freshState();
// Students who joined on this phone: [{ roll, name, pin }]. Kept only on this phone; the name is never sent anywhere.
function joined(){ return recall('op.students') || []; }
function joinedStudent(roll){ return joined().filter(function(x){ return x.roll === roll; })[0] || null; }
function rollOf(who){ return who === 'kavya' ? KAVYA_ROLL : /^10B-\d{2}$/.test(who || '') ? who : null; }
function pinOf(who){ if (PIN_CODE[who]) return PIN_CODE[who]; var x = joinedStudent(who); return x ? x.pin : null; }
// Each student's progress stays on this phone under op.state.<roll>, behind her picture PIN.
function saveStudent(){
  var roll = rollOf(S.who);
  if (!roll || !S.user) return;
  store('op.state.' + roll, { answers:S.answers, profile:S.profile, path:S.path, plan:S.plan, done:S.done, screen:S.screen === 'checks' ? S.prevScreen : S.screen });
}
function restoreStudent(roll){
  var saved = roll ? recall('op.state.' + roll) : null;
  if (!saved) return false;
  S.answers = saved.answers || {}; S.profile = saved.profile || blankProfile(); S.path = saved.path && PATH[saved.path] ? saved.path : null;
  S.plan = S.path ? saved.plan : null; S.done = saved.done || {};
  return saved.screen && saved.screen !== 'lock' ? saved.screen : 'discover';
}

/* voice state for the current question; never stored */
var V;
function resetVoice(){ V = { state:'idle', qid:null, transcript:null, suggestion:null, fake:false, note:null }; }
resetVoice();

function currentPath(){ return S.path ? PATH[S.path] : null; }
function qIndex(){ for (var i = 0; i < QUESTIONS.length; i++) if (!S.answers[QUESTIONS[i].id]) return i; return QUESTIONS.length; }
function isOnline(){ return navigator.onLine !== false && !netFailed(); }
function narrow(){ try { return window.matchMedia('(max-width:920px), (display-mode: standalone)').matches; } catch (e) { return false; } }

/* ---------------- actions ---------------- */
function answer(qid, oid){
  S.answers[qid] = oid; resetVoice(); render();
  var qi = qIndex();
  if (qi < QUESTIONS.length) playClips(['q_' + QUESTIONS[qi].id]); else stopClips();
}
function choosePath(id){
  S.path = id; var path = PATH[id];
  S.plan = makePlan(path, S.profile, evaluateAll(S.profile, path)); S.done = {};
  S.screen = 'plan'; render(); scrollTop(); toast(L('திட்டம் தயார்: ' + path.name.ta, 'Plan ready for ' + path.name.en + '.'));
  playClips(['plan_ready']);
}
function reroute(){
  if (!S.plan) return;
  for (var w = 0; w < 4; w++) {
    var open = S.plan[w].filter(function(t){ return !S.done[t.id]; });
    if (open.length) {
      if (w === 3) { toast(L('இது கடைசி வாரம். 3 நாளில் மீண்டும் நினைவூட்டுவோம்.', 'This is the last week. We will remind you again in 3 days.')); return; }
      S.plan[w] = S.plan[w].filter(function(t){ return S.done[t.id]; });
      S.plan[w + 1] = open.concat(S.plan[w + 1]);
      render(); toast(L(open.length + ' படி வாரம் ' + (w + 2) + '-க்கு மாற்றப்பட்டது.', 'Plan updated: ' + open.length + ' step' + (open.length > 1 ? 's' : '') + ' moved to week ' + (w + 2) + '.')); return;
    }
  }
  toast(L('எல்லாப் படிகளும் முடிந்தன.', 'Every step is done.'));
}

/* ---------------- toast ---------------- */
var toastTimer = null;
function toast(msg){
  var t = document.getElementById('toast');
  t.textContent = typeof msg === 'string' ? msg : S.lang === 'en' ? msg.en : S.lang === 'ta' ? msg.ta : msg.ta + ' / ' + msg.en;
  t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(function(){ t.hidden = true; }, 3800);
}

/* ---------------- phone screens ---------------- */
function statusLine(){
  var on = isOnline(), n = queueCount(), at = syncedAt(), parts = [];
  parts.push('<span class="inline' + (on ? '' : ' off') + '" id="netState">' + bi(on ? STR.online : STR.offline) + '</span>');
  if (n) parts.push('<span class="inline wait" id="syncState">' + bi(STR.waiting(n)) + '</span>');
  else if (at) parts.push('<span class="inline" id="syncState">' + bi(STR.synced(at)) + '</span>');
  return parts.join('');
}
function phTop(){
  return '<div class="ph-row"><div class="brand">OpenPath' + (S.user ? '<small>' + esc(S.user) + '</small>' : '') + '</div>' +
    '<div class="ph-tools">' +
    '<button class="iconbtn" data-act="lang" aria-label="Switch language">' + (S.lang === 'en' ? 'தமிழ்' : 'EN') + '</button>' +
    '<button class="iconbtn" data-act="settings" aria-label="Settings">' + ic('gear') + '</button>' +
    (S.user ? '<button class="iconbtn" data-act="lock" aria-label="Lock and switch user">' + ic('lock') + '</button>' : '') + '</div></div>' +
    '<div class="ph-status" id="phStatus">' + statusLine() + '</div>';
}
function scrLock(){
  if (!S.who) {
    var people = [['kavya','K','Kavya',L('மாணவி, 10ஆம் வகுப்பு','Student, Class 10')], ['anbu','A','Anbu',L('அண்ணன், ITI மாணவர்','Elder brother, ITI student')]];
    return '<div class="stack"><h2 class="h">' + bi(L('இந்த போனை யார் பயன்படுத்துகிறீர்கள்?','Who is using this phone?')) + '</h2>' +
      '<p class="note">' + bi(L('ஒரே போனில் ஒவ்வொருவருக்கும் படக் குறியீட்டுடன் தனி சுயவிவரம்.','On a shared family phone, each person gets a private profile with a picture PIN.')) + '</p>' +
      '<div class="who">' + people.map(function(x){ return '<button data-act="who" data-id="' + x[0] + '"><span class="avatar">' + x[1] + '</span><span><b>' + x[2] + '</b>' + bi(x[3]) + '</span></button>'; }).join('') +
      joined().map(function(x){ var n = x.roll.slice(4); return '<button data-act="who" data-id="' + esc(x.roll) + '"><span class="avatar">' + esc(n) + '</span><span><b>' + esc(x.name || ('Roll ' + n)) + '</b>' + bi(L('மாணவர், 10-B · ரோல் ' + n, 'Student, Class 10-B · roll ' + n)) + '</span></button>'; }).join('') +
      '<button data-act="who" data-id="new"><span class="avatar">+</span><span>' + bi(L('புதிய மாணவர்','New student')) + '</span></button></div></div>';
  }
  if (S.who === 'new') return scrRegister();
  var initial = S.who === 'anbu' ? 'A' : S.who === 'kavya' ? 'K' : esc(S.who.slice(4));
  return '<div class="stack center"><span class="avatar big">' + initial + '</span>' +
    '<h2 class="h">' + bi(L('உன் படக் குறியீட்டைத் தொடு','Tap your picture PIN')) + '</h2>' +
    '<div class="dots">' + [0, 1, 2].map(function(i){ return '<span class="dot ' + (S.pin.length > i ? 'on' : '') + '"></span>'; }).join('') + '</div>' +
    '<div class="pinpad">' + Object.keys(PIN_SVG).map(function(k){ return '<button class="pin" data-act="pin" data-id="' + k + '" aria-label="' + PIN_NAME[k].en + '">' + PIN_SVG[k] + '<span>' + esc(S.lang === 'en' ? PIN_NAME[k].en : PIN_NAME[k].ta) + '</span></button>'; }).join('') + '</div>' +
    (S.pinMsg ? '<p class="warn">' + bi(S.pinMsg) + '</p>' : '') +
    (S.who === 'kavya' ? '<p class="hint">Demo PIN for Kavya: sun, leaf, star</p>' : '') +
    '<button class="link" data-act="who-back">' + bi(L('வேறு நபர்','Someone else')) + '</button></div>';
}
function pinpad(){
  return '<div class="dots">' + [0, 1, 2].map(function(i){ return '<span class="dot ' + (S.pin.length > i ? 'on' : '') + '"></span>'; }).join('') + '</div>' +
    '<div class="pinpad">' + Object.keys(PIN_SVG).map(function(k){ return '<button class="pin" data-act="pin" data-id="' + k + '" aria-label="' + PIN_NAME[k].en + '">' + PIN_SVG[k] + '<span>' + esc(S.lang === 'en' ? PIN_NAME[k].en : PIN_NAME[k].ta) + '</span></button>'; }).join('') + '</div>';
}
// A student new to this phone: her roll number (sent with her progress), an optional first name (kept on this phone) and a picture PIN.
function scrRegister(){
  var R = S.reg;
  if (R.step === 'roll') {
    return '<div class="stack"><h2 class="h">' + bi(L('புதிய மாணவர்','New student')) + '</h2>' +
      '<p class="note">' + bi(L('இந்த போனில் உனக்கென ஒரு தனி சுயவிவரம், படக் குறியீட்டுடன்.','Your own private profile on this phone, with a picture PIN.')) + '</p>' +
      '<div class="field"><label class="label" for="regRoll">' + bi(L('வகுப்பு 10-B-யில் உன் ரோல் எண்','Your roll number in Class 10-B')) + '</label><input class="inp" id="regRoll" inputmode="numeric" maxlength="2" autocomplete="off" value="' + esc(R.roll) + '"></div>' +
      '<div class="field"><label class="label" for="regName">' + bi(L('உன் பெயர் (விருப்பம்)','Your first name (optional)')) + '</label><input class="inp" id="regName" maxlength="24" autocomplete="off" value="' + esc(R.name) + '"></div>' +
      (R.msg ? '<p class="warn">' + bi(R.msg) + '</p>' : '') +
      '<p class="note">' + bi(L('உன் பெயரும் விவரங்களும் இந்த போனில் மட்டுமே இருக்கும். ஆசிரியர் உன் ரோல் எண்ணையும் முன்னேற்றத்தையும் மட்டுமே பார்ப்பார்.','Your name and details stay on this phone. Your teacher sees only your roll number and your progress.')) + '</p>' +
      '<div class="row"><button class="btn" data-act="reg-next">' + bi(L('தொடர்','Continue')) + '</button></div>' +
      '<button class="link start" data-act="who-back">' + bi(L('வேறு நபர்','Someone else')) + '</button></div>';
  }
  return '<div class="stack center"><span class="avatar big">' + esc(R.roll.slice(4)) + '</span>' +
    '<h2 class="h">' + bi(L('உன் படக் குறியீட்டுக்கு 3 படங்களைத் தொடு','Tap 3 pictures for your PIN')) + '</h2>' +
    '<p class="note">' + bi(L('இவற்றை நினைவில் வை. அடுத்த முறை இவற்றைத் தொட்டுத் திறக்கலாம்.','Remember them. Next time, tap the same 3 to open your profile.')) + '</p>' +
    pinpad() + '<button class="link" data-act="reg-back">' + bi(STR.back) + '</button></div>';
}
function voiceBlock(q){
  var mine = V.qid === q.id, on = isOnline(), h = '';
  if (!on && !(mine && V.state === 'recording')) {
    h += '<button class="speak" data-act="speak" data-q="' + q.id + '" aria-disabled="true">' + ic('mic') + bi(STR.speak) + '</button>';
    return h + '<p class="vstate">' + bi(STR.voiceOffline) + '</p>';
  }
  var rec = mine && V.state === 'recording', busy = mine && V.state === 'busy';
  h += '<button class="speak' + (rec ? ' rec' : '') + '" data-act="speak" data-q="' + q.id + '"' + (busy ? ' aria-disabled="true"' : '') + ' aria-label="' + (rec ? 'Stop recording' : 'Answer by voice') + '">' +
    ic(rec ? 'stop' : 'mic') + bi(rec ? STR.stop : STR.speak) + '</button>';
  if (rec) h += '<p class="vstate">' + bi(STR.recording) + ' <b id="vTimer">0:00</b></p>';
  else if (busy) h += '<p class="vstate">' + bi(STR.understanding) + '</p>';
  else if (mine && V.state === 'result') {
    h += '<p class="heard"><span class="inline">' + bi(STR.heard) + '</span> <span class="q">“' + esc(V.transcript || '') + '”</span>' + (V.fake ? ' <span class="sim inline">' + bi(STR.simulated) + '</span>' : '') + '</p>';
    h += '<p class="vstate">' + bi(strongSuggestion() ? STR.confirm : STR.notCaught) + '</p>';
  } else h += '<p class="vstate">' + bi(V.note && mine ? V.note : STR.voiceHint) + '</p>';
  return h;
}
function strongSuggestion(){ return V.state === 'result' && V.suggestion && V.suggestion.confidence >= 0.5 ? V.suggestion.option_id : null; }
function scrDiscover(){
  var g = S.greet;
  var h = '<div class="msg">' + bi(L('வணக்கம்' + (g ? ' ' + g.ta : '') + '! மூன்று சிறு கேள்விகள். பேசலாம், அல்லது படத்தைத் தொடலாம்.', 'Hello' + (g ? ' ' + g.en : '') + '! Three short questions. Speak, or tap a picture.')) + '</div>';
  var qi = qIndex();
  QUESTIONS.forEach(function(q, i){
    if (i > qi) return;
    var cur = i === qi;
    h += '<div class="msg"' + (cur ? ' id="curQ"' : '') + '><div class="qrow"><div>' + bi(q.q) + '</div><button class="iconbtn" data-act="say" data-q="' + i + '" aria-label="Read the question aloud">' + ic('speaker') + '</button></div></div>';
    if (!cur) {
      var o = q.opts.filter(function(x){ return x.id === S.answers[q.id]; })[0];
      h += '<div class="msg me">' + bi(o.label) + '</div>';
    } else {
      var sug = V.qid === q.id ? strongSuggestion() : null;
      h += voiceBlock(q);
      h += '<div class="tiles">' + q.opts.map(function(o){ return '<button class="tile' + (sug === o.id ? ' suggested' : '') + '" data-act="ans" data-q="' + q.id + '" data-o="' + o.id + '"' + (sug === o.id ? ' aria-describedby="sugNote"' : '') + '>' + ic(o.icon) + '<span>' + bi(o.label) + '</span></button>'; }).join('') + '</div>';
    }
  });
  if (qi === QUESTIONS.length) {
    h += '<div class="msg">' + bi(L('நன்றி! இப்போது சில விவரங்கள். இவை இந்த போனில் மட்டுமே இருக்கும்.','Thank you! Now a few details. They stay on this phone only.')) + '</div>' +
      '<button class="btn" data-act="go" data-s="details">' + bi(L('தொடர்','Continue')) + '</button>';
  } else if (S.who === 'kavya') {
    h += '<button class="link" data-act="sample-answers">Use Kavya’s sample answers</button>';
  }
  return h;
}
var ROWS = [
  { k:'gender', q:L('பாலினம்','Gender'), o:[['girl',L('பெண்','Girl')],['boy',L('ஆண்','Boy')],['third',L('மூன்றாம் பாலினம்','Third gender')]] },
  { k:'cls', q:L('வகுப்பு','Class'), o:[[9,L('9','9')],[10,L('10','10')],[11,L('11','11')],[12,L('12','12')],[13,L('கல்லூரி / ITI முதல் ஆண்டு','College or ITI, year 1')]] },
  { k:'school', q:L('பள்ளி','School'), o:[['govt',L('அரசு','Government')],['aided',L('அரசு உதவி பெறும்','Government-aided')],['private',L('தனியார்','Private')]] },
  { k:'since6', q:L('6ஆம் வகுப்பு முதல் இதே வகைப் பள்ளியா?','Same kind of school since Class 6?'), o:[[true,L('ஆம்','Yes')],[false,L('இல்லை','No')]] },
  { k:'medium', q:L('பயிற்று மொழி','Medium of study'), o:[['tamil',L('தமிழ்','Tamil')],['english',L('ஆங்கிலம்','English')]] },
  { k:'community', q:L('சமூகம்','Community'), o:[['SC',L('SC','SC')],['ST',L('ST','ST')],['BC',L('BC','BC')],['MBC',L('MBC','MBC')],['DNC',L('DNC','DNC')],['OC',L('OC','OC')],['NA',L('சொல்ல விருப்பமில்லை','Prefer not to say')]] },
  { k:'income', q:L('குடும்ப ஆண்டு வருமானம்','Family income a year'), o:[['lt1',L('₹1 லட்சத்துக்குள்','Under ₹1 lakh')],['1to2.5',L('₹1–2.5 லட்சம்','₹1–2.5 lakh')],['2.5to4.5',L('₹2.5–4.5 லட்சம்','₹2.5–4.5 lakh')],['4.5to8',L('₹4.5–8 லட்சம்','₹4.5–8 lakh')],['gt8',L('₹8 லட்சத்துக்கு மேல்','Over ₹8 lakh')],['unknown',L('தெரியாது','Not sure')]] },
  { k:'firstGen', q:L('உன் குடும்பத்தில் முதல் பட்டதாரி நீதானா?','Will you be the first graduate in your family?'), o:[[true,L('ஆம்','Yes')],[false,L('இல்லை','No')],['unknown',L('தெரியாது','Not sure')]] },
  { k:'top20', q:L('+2 மதிப்பெண் உன் வாரியத்தின் முதல் 20%-க்குள்?','Class 12 marks in your board’s top 20%?'), show:function(p){ return p.cls != null && p.cls >= 12; }, o:[[true,L('ஆம்','Yes')],[false,L('இல்லை','No')],['unknown',L('தெரியாது','Not sure')]] }
];
function scrDetails(){
  var p = S.profile;
  var h = '<h2 class="h">' + bi(L('உன்னைப் பற்றி சில விவரங்கள்','A few details about you')) + '</h2>' +
    '<div class="banner">' + ic('lock') + '<div>' + bi(L('இவை இந்த போனில் மட்டுமே இருக்கும். ஆசிரியருக்கோ எங்கள் சர்வருக்கோ அனுப்பப்படாது.','These stay on this phone. They are never sent to your teacher or to our server.')) + '</div></div>';
  ROWS.forEach(function(r){
    if (r.show && !r.show(p)) return;
    h += '<div class="field"><span class="label">' + bi(r.q) + '</span><div class="seg">' + r.o.map(function(o){
      var on = p[r.k] === o[0];
      return '<button data-act="set" data-k="' + r.k + '" data-v="' + esc(JSON.stringify(o[0])) + '" aria-pressed="' + on + '">' + bi(o[1]) + '</button>';
    }).join('') + '</div></div>';
  });
  h += '<div class="field"><span class="label">' + bi(L('உன்னிடம் உள்ள ஆவணங்கள்','Documents you have')) + '</span><div class="seg">' + Object.keys(DOCS).map(function(d){
    return '<button data-act="doc" data-d="' + d + '" aria-pressed="' + (p.docs[d] === true) + '">' + bi(DOCS[d].name) + '</button>';
  }).join('') + '</div></div>';
  h += '<div class="row">' + (S.who === 'kavya' ? '<button class="btn ghost" data-act="sample-profile">Fill Kavya’s sample details</button>' : '') +
    '<button class="btn" data-act="go" data-s="skills">' + bi(L('தொடர்','Continue')) + '</button></div>';
  return h;
}
function topSkills(){
  var sk = skillsFrom(S.answers);
  return Object.keys(sk).sort(function(a, b){ return sk[b] - sk[a]; }).slice(0, 3);
}
function scrSkills(){
  if (qIndex() < QUESTIONS.length) return emptyState(L('முதலில் மூன்று கேள்விகளுக்குப் பதில் சொல்','Answer the three questions first'), 'discover');
  var from = {};
  QUESTIONS.forEach(function(q){ var o = q.opts.filter(function(x){ return x.id === S.answers[q.id]; })[0]; Object.keys(o.tags).forEach(function(k){ (from[k] = from[k] || []).push(o.label); }); });
  return '<h2 class="h">' + bi(L('நீ ஏற்கனவே பயன்படுத்தும் திறன்கள்','Skills you already use')) + '</h2>' +
    '<p class="note">' + bi(L('மதிப்பெண்களிலிருந்து அல்ல, உன் தினசரி வேலைகளிலிருந்து கண்டறியப்பட்டது.','Found from what you do every day, not from your marks.')) + '</p>' +
    topSkills().map(function(k){ return '<div class="card"><span class="h3">' + bi(SKILL[k]) + '</span><p class="meta">' + bi(catL(L('இதிலிருந்து: ','From: '), joinL(from[k]))) + '</p></div>'; }).join('') +
    '<div class="row"><button class="btn" data-act="go" data-s="paths">' + bi(L('ஆம், இது நான்','Yes, that’s me')) + '</button><button class="btn quiet" data-act="redo">' + bi(L('மீண்டும் பதில் சொல்','Answer again')) + '</button></div>';
}
function emptyState(msg, target){
  return '<div class="card"><p class="why">' + bi(msg) + '</p><button class="btn" data-act="go" data-s="' + target + '">' + bi(L('அங்கே செல்','Go there')) + '</button></div>';
}
function scrPaths(){
  if (qIndex() < QUESTIONS.length) return emptyState(L('முதலில் மூன்று கேள்விகளுக்குப் பதில் சொல்','Answer the three questions first'), 'discover');
  var rec = recommend(S.answers, S.profile), sk = rec.skills;
  var list = rec.picks.map(function(c){ return { c:c, wild:false }; });
  if (rec.wild) list.push({ c:rec.wild, wild:true });
  var h = '<h2 class="h">' + bi(L('உனக்கான பாதைகள்','Paths for you')) + '</h2>' +
    '<p class="note">' + bi(L('3 பொருத்தமான பாதைகள், 1 வித்தியாசமான வாய்ப்பு. பாலினத்தைப் பார்த்துப் பாதைகள் தேர்வு செய்யப்படுவதில்லை.','3 good fits and 1 wildcard. Gender is never used to pick paths.')) + '</p>';
  list.forEach(function(x){
    var p = x.c.path, chosen = S.path === p.id;
    var match = Object.keys(p.tags).filter(function(k){ return sk[k]; }).sort(function(a, b){ return p.tags[b] * sk[b] - p.tags[a] * sk[a]; }).slice(0, 2).map(function(k){ return SKILL[k]; });
    h += '<article class="card' + (chosen ? ' chosen' : '') + '" data-path="' + p.id + '">' +
      '<div class="row"><span class="chip ' + (x.wild ? 'wild' : 'ok') + '">' + bi(x.wild ? L('வித்தியாசமான வாய்ப்பு','Wildcard') : L('பொருத்தமானது','Good fit')) + '</span></div>' +
      '<span class="h3">' + bi(p.name) + '</span><p class="meta">' + bi(p.route) + '</p>' +
      (match.length ? '<p class="why">' + bi(catL(L('பொருந்துவது: ','Matches: '), joinL(match))) + '</p>' : '<p class="why">' + bi(L('நீ இன்னும் யோசிக்காத ஒரு வழி','A road you may not have thought about')) + '</p>') +
      (S.story === p.id ? '<blockquote class="story">' + bi(p.story) + '<small>Illustrative story; real ones are recorded in Tamil in the pilot.</small></blockquote>' : '') +
      '<div class="row"><button class="btn ghost" data-act="story" data-id="' + p.id + '">' + ic('play') + bi(L('கதை கேள்','Play story')) + '</button>' +
      '<button class="btn" data-act="choose" data-id="' + p.id + '">' + bi(chosen ? L('தேர்ந்தெடுத்தது','Chosen') : L('இதைத் தேர்ந்தெடு','Choose this')) + '</button></div></article>';
  });
  return h;
}
function scrPlan(){
  var path = currentPath();
  if (!path) return emptyState(L('முதலில் ஒரு பாதையைத் தேர்ந்தெடு','Choose a path first'), 'paths');
  var all = [].concat.apply([], S.plan), done = all.filter(function(t){ return S.done[t.id]; }).length;
  var h = '<h2 class="h">' + bi(L('உன் 4 வாரத் திட்டம்','Your 4-week plan')) + '</h2><p class="note">' + bi(path.name) + '</p>';
  nextDecision(path, S.profile).forEach(function(d){ h += '<div class="banner ochre">' + ic('calendar') + '<div>' + bi(d) + '</div></div>'; });
  S.plan.forEach(function(week, w){
    h += '<div class="week"><h4>' + bi(L('வாரம் ' + (w + 1), 'Week ' + (w + 1))) + '</h4>' + (week.length ? week.map(function(t){
      var d = !!S.done[t.id];
      return '<label class="task' + (d ? ' done' : '') + '"><input type="checkbox" data-act="task" data-id="' + t.id + '"' + (d ? ' checked' : '') + '><span>' + bi(t.text) + '</span></label>';
    }).join('') : '<p class="note">' + bi(L('இந்த வாரம் எதுவும் இல்லை','Nothing left this week')) + '</p>') + '</div>';
  });
  h += '<div class="row between" style="align-items:center"><span class="note" id="planDone">' + done + '/' + all.length + ' ' + (S.lang === 'en' ? 'done' : S.lang === 'ta' ? 'முடிந்தது' : 'முடிந்தது · done') + '</span>' +
    '<button class="btn quiet" data-act="reroute">' + bi(L('ஒரு படி தவறியதா?','Missed a step?')) + '</button></div>';
  return h;
}
var STATUS = {
  yes:{ cls:'ok', label:L('இப்போது தகுதி','Eligible now') }, likely:{ cls:'ok', label:L('தகுதி இருக்கலாம்','Likely eligible') },
  later:{ cls:'', label:L('பின்னர் தகுதி','Eligible later') }, 'if':{ cls:'', label:L('படிப்பைப் பொறுத்து','Depends on course') },
  ask:{ cls:'warn', label:L('ஒரு பதில் தேவை','Needs an answer') }, no:{ cls:'no', label:L('பொருந்தாது','Not for you') }
};
function reasonOf(e){
  var s = e.s;
  if (e.status === 'no') {
    if (e.timing === 'past') return L('9, 10ஆம் வகுப்புகளுக்கு மட்டும்','Only for Class 9 and 10');
    var f = e.trace.filter(function(x){ return x.r === false; })[0];
    return catL(L('தேவை: ','Requires: '), f.c.label);
  }
  if (e.status === 'ask') { var u = e.trace.filter(function(x){ return x.r === null; })[0]; return u ? catL(L('விவரங்கள் பக்கத்தில் பதில் சொல்: ','Answer on the details screen: '), u.c.label) : L('உன் வகுப்பைச் சொல்','Tell us your class'); }
  if (e.status === 'if') { var pc = e.trace.filter(function(x){ return x.r === 'path'; })[0]; return catL(L('தகுதி: ','Eligible '), pc.c.ifText); }
  var parts = [];
  if (e.status === 'later') parts.push(s.when === '11+' ? L('11ஆம் வகுப்பு முதல்','From Class 11') : L('பட்டம், டிப்ளமோ அல்லது ITI-யில் சேரும்போது','When you join a degree, diploma or ITI'));
  e.trace.forEach(function(x){ if (x.r === 'future' && x.c.future) parts.push(x.c.future); });
  if (e.likely) parts.push(L('BC/MBC: உன் சமூகம் மத்திய OBC பட்டியலில் உள்ளதா என உறுதிசெய்','BC/MBC: confirm your community is on the central OBC list'));
  if (!parts.length) parts.push(L('எல்லா நிபந்தனைகளும் பொருந்துகின்றன','All conditions met'));
  return L(parts.map(function(x){ return x.ta; }).join(' · '), parts.map(function(x){ return x.en; }).join(' · '));
}
function schemeCard(e){
  var st = STATUS[e.status], s = e.s, now = e.status === 'yes' || e.status === 'likely';
  var miss = (now || e.status === 'later') && e.missing.length ? '<p class="missing">' + bi(catL(L('இல்லாத ஆவணம்: ','Missing: '), joinL(e.missing.map(function(d){ return DOCS[d].name; })))) + '</p>' : '';
  return '<article class="card" data-scheme="' + s.id + '" data-status="' + e.status + '"><div class="row"><span class="chip ' + st.cls + '">' + bi(st.label) + '</span></div><span class="h3">' + bi(s.name) + '</span>' +
    '<p class="benefit">' + bi(s.benefit) + '</p><p class="reason">' + bi(reasonOf(e)) + '</p>' + miss +
    '<p class="src">' + esc(s.by) + ' · <a href="' + s.source.url + '" target="_blank" rel="noopener">' + esc(s.source.label) + '</a> · checked ' + CHECKED + '</p>' +
    (now ? '<button class="btn" data-act="ready" data-id="' + s.id + '">' + bi(L('விண்ணப்பத்துக்குத் தயாராகு','Get ready to apply')) + '</button>' : '') + '</article>';
}
function scrSupport(){
  var evals = evaluateAll(S.profile, currentPath());
  var g = { now:[], later:[], ifp:[], ask:[], no:[] };
  evals.forEach(function(e){ ({ yes:g.now, likely:g.now, later:g.later, 'if':g.ifp, ask:g.ask, no:g.no })[e.status].push(e); });
  var h = '<h2 class="h">' + bi(L('உனக்குக் கிடைக்கும் உதவி','Support you can get')) + '</h2>' +
    '<div class="banner">' + ic('shield') + '<div>' + bi(L('சோதிக்கப்பட்ட விதிகளால் இந்த போனிலேயே சரிபார்க்கப்பட்டது. இணையம் தேவையில்லை.','Checked on this phone by tested rules. No internet needed.')) + '</div></div>';
  function sec(title, arr){ return arr.length ? '<p class="group-h">' + bi(title) + '</p>' + arr.map(schemeCard).join('') : ''; }
  h += sec(L('இப்போது','Now'), g.now) + sec(L('பின்னர்','Later, if you stay on track'), g.later) + sec(L('நீ தேர்ந்தெடுக்கும் படிப்பைப் பொறுத்து','Depends on the course you choose'), g.ifp) + sec(L('ஒரு பதில் தேவை','Needs one more answer'), g.ask);
  if (g.no.length) h += '<details class="group"><summary>' + bi(L('உனக்குப் பொருந்தாதவை (' + g.no.length + ')', 'Not for you (' + g.no.length + '), with the reason')) + '</summary>' + g.no.map(schemeCard).join('') + '</details>';
  return h;
}
function scrChecks(){
  return '<button class="link start" data-act="checks-back">' + bi(STR.back) + '</button><div class="pbody embed">' + panelChecks() + '</div>';
}
function sheetReady(id){
  var s = SCHEME[id], e = evaluate(s, S.profile, currentPath());
  return '<div class="sheet-bg" data-act="close-sheet"><div class="sheet" data-stop="1" role="dialog" aria-label="Get ready to apply">' +
    '<span class="h3">' + bi(s.name) + '</span><p class="note">' + bi(L('விண்ணப்பப் பட்டியல் இந்த போனில் சேமிக்கப்பட்டது','Checklist saved on this phone')) + '</p>' +
    s.docs.map(function(d){ var have = S.profile.docs[d] === true; return '<div class="doc"><div><b>' + bi(DOCS[d].name) + '</b>' + (have ? '' : '<span class="en">' + esc(DOCS[d].how.en) + '</span>') + '</div><span class="' + (have ? 'have' : 'need') + '">' + bi(have ? L('உள்ளது','Have it') : L('இல்லை','Missing')) + '</span></div>'; }).join('') +
    '<div class="banner">' + ic('shield') + '<div>' + bi(L('இந்தத் திரையை உன் ஆசிரியர் அல்லது இ-சேவை பணியாளரிடம் காட்டு. அவர்கள் அதிகாரப்பூர்வ இணையதளத்தில் விண்ணப்பிப்பார்கள்.','Show this screen to your teacher or the e-Sevai operator. They submit it on the official portal.')) + '</div></div>' +
    (e.likely ? '<p class="missing">' + bi(L('BC/MBC: உன் சமூகம் மத்திய OBC பட்டியலில் உள்ளதா என ஆசிரியரிடம் உறுதிசெய்','BC/MBC: check with your teacher that your community is on the central OBC list')) + '</p>' : '') +
    '<button class="btn" data-act="close-sheet">' + bi(L('சரி','Done')) + '</button></div></div>';
}
function sheetSettings(){
  var langs = [['bi', STR.langBi], ['ta', STR.langTa], ['en', STR.langEn]];
  return '<div class="sheet-bg" data-act="close-sheet"><div class="sheet" data-stop="1" role="dialog" aria-label="Settings">' +
    '<span class="h3">' + bi(STR.settings) + '</span>' +
    '<div class="field"><span class="label">' + bi(STR.language) + '</span><div class="seg">' + langs.map(function(x){ return '<button data-act="setlang" data-v="' + x[0] + '" aria-pressed="' + (S.lang === x[0]) + '">' + bi(x[1]) + '</button>'; }).join('') + '</div></div>' +
    '<div class="field"><label class="label" for="passcode">' + bi(STR.passcode) + '</label><div class="row"><input class="inp" id="passcode" inputmode="numeric" autocomplete="off" value="' + esc(recall('op.passcode') || '') + '"><button class="btn" data-act="save-passcode">' + bi(STR.save) + '</button></div></div>' +
    '<div class="row"><button class="btn quiet" data-act="open-checks">' + bi(STR.checks) + '</button><button class="btn quiet" data-act="reset">' + bi(STR.resetDemo) + '</button></div>' +
    '<p class="note"><span class="inline">' + bi(STR.version) + '</span>: ' + (APP_VERSION ? esc(APP_VERSION) : bi(STR.notInstalled)) + '</p>' +
    '<button class="btn" data-act="close-sheet">' + bi(STR.close) + '</button></div></div>';
}
function phNav(){
  var tabs = [['discover','compass',L('கண்டறி','Discover')], ['paths','route',L('பாதைகள்','Paths')], ['plan','calendar',L('திட்டம்','Plan')], ['support','shield',L('உதவி','Support')]];
  var group = { discover:'discover', details:'discover', skills:'discover', paths:'paths', plan:'plan', support:'support' }[S.screen];
  return tabs.map(function(t){ return '<button data-act="go" data-s="' + t[0] + '"' + (group === t[0] ? ' aria-current="page"' : '') + '>' + ic(t[1]) + '<span class="ta">' + esc(t[2].ta) + '</span><span class="en">' + esc(t[2].en) + '</span></button>'; }).join('');
}

/* ---------------- side panel (laptop width) ---------------- */
var MARK = { 'true':['yes','yes'], 'false':['no','no'], 'null':['ask','?'], likely:['likely','likely'], future:['later','later'], path:['if','if course'] };
function panelRules(){
  var path = currentPath(), evals = evaluateAll(S.profile, path);
  return '<h2>How it decides</h2><p class="note">Every result comes from rules written as code, with a source and a check date. The language model only matches a spoken answer to one of the pictures, and she confirms it with a tap. The language model never decides who is eligible. Showing ' + (S.greet ? esc(S.greet.en) + '’s' : S.user ? 'this student’s' : 'Kavya’s') + ' current answers' + (path ? ' and the chosen path (' + esc(path.name.en) + ')' : '') + '.</p>' +
    evals.map(function(e){
      var st = STATUS[e.status];
      return '<details class="scheme"><summary><span>' + esc(e.s.name.en) + '</span><span class="chip ' + st.cls + '">' + esc(st.label.en) + '</span></summary>' +
        '<ul class="trace">' + e.trace.map(function(x){ var m = MARK[String(x.r)]; return '<li><span class="mark ' + m[0] + '">' + m[1] + '</span><span>' + esc(x.c.label.en) + ' <code>' + esc(x.c.code) + '</code></span></li>'; }).join('') +
        '<li><span class="mark ' + (e.timing === 'past' ? 'no' : e.timing === 'now' ? 'yes' : e.timing ? 'later' : 'ask') + '">' + (e.timing || '?') + '</span><span>timing <code>applies: ' + esc(e.s.when) + '</code></span></li></ul>' +
        '<p class="src">' + esc(e.s.source.label) + ' · checked ' + CHECKED + '</p></details>';
    }).join('');
}
function fmtMs(ms){ return ms == null ? '–' : (ms / 1000).toFixed(1) + ' s'; }
function pct(x){ return x == null ? '–' : Math.round(x * 1000) / 10 + '%'; }
function speechChecks(){
  var e = EVAL;
  if (!e) return '<h3 class="h3">Measured on real Tamil speech</h3><div class="check"><span class="big">–</span><p>Not measured yet.</p><small>The eval script writes these numbers after it runs on our Tamil recordings.</small></div>';
  var lat = e.latency_ms || {}, tot = lat.total || {};
  return '<h3 class="h3">Measured on real Tamil speech</h3>' +
    '<p class="note">' + esc(e.date) + ' · ' + e.recordings + ' recordings · ' + e.speakers + ' speakers. The speakers were adults.' + (e.fake ? ' <b class="sim">Simulated voice: not a real measurement.</b>' : '') + '</p>' +
    '<div class="checks">' +
    '<div class="check"><span class="big">' + pct(e.cer) + '</span><p>character error rate of the speech-to-text (Saaras v4) against what each speaker read out.</p><small>Lower is better.</small></div>' +
    '<div class="check"><span class="big">' + e.correct + '/' + e.recordings + '</span><p>answers matched to the right picture (Sarvam-105B, with the keyword fallback).</p><small>' + pct(e.no_suggestion_rate) + ' got no suggestion, so the student just taps.</small></div>' +
    '<div class="check"><span class="big">' + fmtMs(tot.p50) + '</span><p>median time from the end of speaking to the suggestion; 90th percentile ' + fmtMs(tot.p90) + '.</p><small>Measured from the client, including the network.</small></div>' +
    '<div class="check"><span class="big">₹' + (e.cost_per_conversation_inr == null ? '–' : e.cost_per_conversation_inr.toFixed(2)) + '</span><p>estimated cost of one Discover conversation (3 spoken answers), before GST.</p><small>' + esc(e.cost_basis || '') + '</small></div>' +
    '</div>';
}
function panelChecks(){
  var t = lastChecks() || runChecks();
  return '<h2>Checks</h2><p class="note">These run on this device each time the app opens. Nothing here is typed in by hand.</p><div class="checks">' +
    '<div class="check"><span class="big ' + (t.passed === t.total ? '' : 'bad') + '" id="ckRules">' + t.passed + '/' + t.total + '</span><p>rule tests pass. Each case was written from the scheme criteria in the linked sources.</p><small>' + t.schemes + ' schemes, ' + t.rules + ' rule checks, each with a source and check date.</small></div>' +
    '<div class="check"><span class="big ' + (t.changed ? 'bad' : '') + '">' + t.changed + '</span><p>of ' + t.N.toLocaleString('en-IN') + ' random students got different paths when only their gender was flipped.</p><small>Path matching never reads gender. This test fails if anyone adds it.</small></div>' +
    '<div class="check"><span class="big">' + (t.ms < 1000 ? Math.round(t.ms) + ' ms' : (t.ms / 1000).toFixed(1) + ' s') + '</span><p>to check all ' + t.schemes + ' schemes for ' + t.M.toLocaleString('en-IN') + ' random students on this device.</p><small>About ' + (t.perMs * 1000).toFixed(0) + ' microseconds per student, with no server.</small></div>' +
    '<div class="check"><span class="big">' + t.calls + '</span><p>network calls during a full student flow: discover, paths, plan and eligibility.</p><small>Turn on airplane mode, or go offline in DevTools: it keeps working.</small></div>' +
    '<div class="check"><span class="big">' + (t.kb == null ? '–' : t.kb + ' KB') + '</span><p>for the whole app kept on the phone for offline use: rules, ' + t.paths + ' paths, both languages, the Tamil voice clips and these tests.</p><small>' + (t.kb == null ? 'Measured once the app is installed for offline use.' : 'The total the service worker stores.') + '</small></div>' +
    '</div>' + speechChecks() + '<button class="btn quiet" data-act="rerun">Run the checks again</button>' +
    '<details class="group"><summary>See all ' + t.total + ' rule tests</summary><div class="tbl-wrap cases"><table><thead><tr><th>Scheme</th><th>Case</th><th>Expected</th><th>Got</th><th></th></tr></thead><tbody>' +
    t.results.map(function(x){ return '<tr><td>' + esc(x.scheme) + '</td><td>' + esc(x.name) + '</td><td>' + x.expect + '</td><td>' + x.got + '</td><td class="' + (x.pass ? 'pass' : 'fail') + '">' + (x.pass ? 'pass' : 'FAIL') + '</td></tr>'; }).join('') +
    '</tbody></table></div></details>';
}

/* ---------------- render ---------------- */
function renderTop(){ var s = document.getElementById('phStatus'); if (s) s.innerHTML = statusLine(); }
function render(){
  // keep what a student is typing on the register screen if the screen redraws (for example when the network comes back)
  if (S.reg && S.reg.step === 'roll') { var tr = document.getElementById('regRoll'), tn = document.getElementById('regName'); if (tr) S.reg.roll = tr.value; if (tn) S.reg.name = tn.value; }
  var root = document.getElementById('root');
  root.classList.toggle('lang-en', S.lang === 'en'); root.classList.toggle('lang-ta', S.lang === 'ta');
  document.documentElement.lang = S.lang === 'en' ? 'en' : 'ta';
  document.getElementById('phTop').innerHTML = phTop();
  var body = { lock:scrLock, discover:scrDiscover, details:scrDetails, skills:scrSkills, paths:scrPaths, plan:scrPlan, support:scrSupport, checks:scrChecks }[S.screen]();
  var b = document.getElementById('phBody'); b.innerHTML = body;
  if (S.screen === 'discover') {
    b.scrollTop = b.scrollHeight;
    var cq = document.getElementById('curQ');
    if (narrow() && cq && qIndex() > 0) cq.scrollIntoView({ block:'start' });
  }
  var nav = document.getElementById('phNav'); nav.hidden = S.screen === 'lock'; nav.innerHTML = S.screen === 'lock' ? '' : phNav();
  var sheet = document.getElementById('sheet'), typed = document.getElementById('passcode');
  var keep = typed ? typed.value : null;
  sheet.innerHTML = S.sheet === 'settings' ? sheetSettings() : S.sheet ? sheetReady(S.sheet) : '';
  if (keep != null && document.getElementById('passcode')) document.getElementById('passcode').value = keep;
  var tabs = [['rules','How it decides'], ['checks','Checks']];
  document.getElementById('tabs').innerHTML = tabs.map(function(t){ return '<button role="tab" data-act="panel" data-id="' + t[0] + '" aria-selected="' + (S.panel === t[0]) + '">' + t[1] + '</button>'; }).join('') +
    '<a class="tlink" href="/teacher/" target="_blank" rel="noopener">Open the live teacher dashboard</a>';
  document.getElementById('pbody').innerHTML = { rules:panelRules, checks:panelChecks }[S.panel]();
  saveStudent();
  queueProgress();
}
function scrollTop(){ var b = document.getElementById('phBody'); b.scrollTop = 0; if (narrow()) window.scrollTo(0, 0); }
function go(screen){ S.screen = screen; render(); if (screen !== 'discover') scrollTop(); }
// After every change, queue what the teacher may see (progress and one blocker) if it changed. Only Kavya's roll syncs in this demo.
function queueProgress(){
  var roll = rollOf(S.who);
  if (!roll || !S.user) return;
  enqueue(roll, progressOf(S.answers, S.path, S.plan, S.done, S.profile));
}

/* ---------------- voice ---------------- */
function onSpeak(qid){
  if (!isOnline()) { V = { state:'idle', qid:qid, note:STR.voiceOffline }; render(); playClips(['voice_offline']); toast(STR.voiceOffline); return; }
  if (V.state === 'busy') return;
  if (isRecording()) { finishRecording(); return; }
  stopClips();
  V = { state:'recording', qid:qid };
  render();
  startRecording({ maxSeconds:20, onTick:function(sec){ var t = document.getElementById('vTimer'); if (t) t.textContent = '0:' + String(Math.floor(sec)).padStart(2, '0'); }, onLimit:finishRecording })
    .catch(function(err){
      V = { state:'idle', qid:qid, note:STR.micBlocked }; render();
      toast(err && (err.name === 'NotAllowedError' || err.name === 'SecurityError') ? STR.micBlocked : STR.voiceFailed);
    });
}
function finishRecording(){
  var qid = V.qid;
  stopRecording().then(function(rec){
    if (!rec || rec.seconds < 0.8) { V = { state:'idle', qid:qid, note:STR.tooShort }; render(); return; }
    V = { state:'busy', qid:qid }; render();
    return sendTalk(rec.wav, qid, recall('op.passcode') || '').then(function(res){
      if (S.answers[qid] || V.qid !== qid) return;       // she already tapped an answer
      V = { state:'result', qid:qid, transcript:res.transcript, suggestion:res.suggestion, fake:!!res.fake };
      render();
      var oid = strongSuggestion();
      if (oid) playClips(['heard_prefix', 'opt_' + qid + '_' + oid, 'confirm']); else playClips(['not_caught']);
    });
  }).catch(function(err){
    V = { state:'idle', qid:qid }; render();
    var st = err && err.status;
    toast(st === 401 ? STR.needPasscode : st === 429 ? STR.tooMany : STR.voiceFailed);
  });
}

/* ---------------- profiles on this phone ---------------- */
function openProfile(who){
  var rec = who === 'kavya' ? null : joinedStudent(who);
  S.user = who === 'kavya' ? 'Kavya' : (rec && rec.name) || 'Roll ' + who.slice(4);
  S.greet = who === 'kavya' ? L('காவ்யா', 'Kavya') : rec && rec.name ? L(rec.name, rec.name) : null;
  S.answers = {}; S.profile = blankProfile(); S.path = null; S.plan = null; S.done = {}; S.pin = []; S.reg = null; resetVoice();
  go(restoreStudent(rollOf(who)) || 'discover');
  if (S.screen === 'discover' && qIndex() < QUESTIONS.length) playClips(qIndex() === 0 ? ['greeting', 'q_' + QUESTIONS[0].id] : ['q_' + QUESTIONS[qIndex()].id]);
}
function registerRoll(){
  var R = S.reg, r = document.getElementById('regRoll'), nm = document.getElementById('regName');
  R.roll = r ? r.value.trim() : R.roll; R.name = nm ? nm.value.trim().slice(0, 24) : R.name;
  var num = /^\d{1,2}$/.test(R.roll) ? +R.roll : 0;
  if (num < 1 || num > 99) { R.msg = L('1 முதல் 99 வரை உள்ள உன் ரோல் எண்ணை உள்ளிடு.', 'Enter your roll number, from 1 to 99.'); render(); return; }
  var roll = '10B-' + String(num).padStart(2, '0');
  if (roll === KAVYA_ROLL || joinedStudent(roll)) { R.msg = L('ரோல் ' + roll.slice(4) + '-க்கு இந்த போனில் ஏற்கனவே சுயவிவரம் உள்ளது.', 'Roll ' + roll.slice(4) + ' already has a profile on this phone.'); render(); return; }
  R.roll = roll; R.step = 'pin'; R.msg = null; S.pin = []; render();
}
function finishRegister(){
  var R = S.reg, pin = S.pin.slice();
  store('op.students', joined().concat([{ roll:R.roll, name:R.name || null, pin:pin }]));
  var names = pin.map(function(k){ return PIN_NAME[k]; });
  S.who = R.roll;
  openProfile(R.roll);
  toast(L('உன் படக் குறியீடு: ' + names.map(function(x){ return x.ta; }).join(', ') + '. நினைவில் வை.', 'Your picture PIN is ' + names.map(function(x){ return x.en; }).join(', ') + '. Remember it.'));
}

/* ---------------- events ---------------- */
document.addEventListener('click', function(ev){
  var el = ev.target.closest('[data-act]'); if (!el) return;
  if (el.dataset.act === 'close-sheet' && ev.target.closest('[data-stop]') && !ev.target.closest('button')) return;
  var a = el.dataset.act;
  if (a === 'who') {
    if (el.dataset.id === 'new') { S.who = 'new'; S.reg = { step:'roll', roll:'', name:'', msg:null }; S.pin = []; S.pinMsg = null; render(); return; }
    S.who = el.dataset.id; S.pin = []; S.pinMsg = null; render(); return;
  }
  if (a === 'who-back') { S.who = null; S.reg = null; S.pin = []; S.pinMsg = null; render(); return; }
  if (a === 'reg-next') { registerRoll(); return; }
  if (a === 'reg-back') { S.reg.step = 'roll'; S.reg.msg = null; S.pin = []; render(); return; }
  if (a === 'pin') {
    S.pin.push(el.dataset.id); S.pinMsg = null;
    if (S.pin.length === 3) {
      if (S.who === 'new') { finishRegister(); return; }
      var want = pinOf(S.who), ok = want && want.join() === S.pin.join();
      if (!ok) { S.pin = []; S.pinMsg = L('சரியில்லை. மீண்டும் முயற்சி செய்.','Not quite. Try again.'); render(); return; }
      if (S.who === 'anbu') { S.who = null; S.pin = []; render(); toast(L('அன்புவின் சுயவிவரம் திறந்தது. காவ்யாவின் பதில்கள் அவருக்குத் தெரியாது. இந்த டெமோவுக்கு காவ்யாவைப் பயன்படுத்து.', 'Anbu’s profile opened. Kavya’s answers stay hidden from him. For this demo, use Kavya.')); return; }
      openProfile(S.who);
      return;
    }
    render(); return;
  }
  if (a === 'lock') { cancelRecording(); stopClips(); resetVoice(); S.screen = 'lock'; S.who = null; S.user = null; S.greet = null; S.reg = null; S.pin = []; S.sheet = null; render(); return; }
  if (a === 'lang') { S.lang = S.lang === 'en' ? 'bi' : 'en'; store('op.lang', S.lang); render(); return; }
  if (a === 'setlang') { S.lang = el.dataset.v; store('op.lang', S.lang); render(); return; }
  if (a === 'ans') { answer(el.dataset.q, el.dataset.o); return; }
  if (a === 'say') { if (!playClips(['q_' + QUESTIONS[+el.dataset.q].id])) toast(STR.noAudio); return; }
  if (a === 'speak') { onSpeak(el.dataset.q); return; }
  if (a === 'sample-answers') { S.answers = clone(KAVYA.answers); resetVoice(); stopClips(); render(); return; }
  if (a === 'sample-profile') { S.profile = clone(KAVYA.profile); if (S.path) S.plan = makePlan(currentPath(), S.profile, evaluateAll(S.profile, currentPath())); render(); return; }
  if (a === 'set') {
    var v = JSON.parse(el.dataset.v), k = el.dataset.k;
    S.profile[k] = S.profile[k] === v ? null : v;
    if (S.path) S.plan = makePlan(currentPath(), S.profile, evaluateAll(S.profile, currentPath()));
    render(); return;
  }
  if (a === 'doc') { var d = el.dataset.d; S.profile.docs[d] = S.profile.docs[d] === true ? false : true; render(); return; }
  if (a === 'go') { go(el.dataset.s); if (el.dataset.s === 'support') playClips(['support_intro']); return; }
  if (a === 'redo') { S.answers = {}; resetVoice(); go('discover'); return; }
  if (a === 'story') { var id = el.dataset.id; S.story = S.story === id ? null : id; render(); if (S.story) { if (!playClips(['path_' + id, 'story_' + id])) toast(STR.noAudio); } else stopClips(); return; }
  if (a === 'choose') { choosePath(el.dataset.id); return; }
  if (a === 'reroute') { reroute(); return; }
  if (a === 'ready') { S.sheet = el.dataset.id; render(); return; }
  if (a === 'settings') { S.sheet = 'settings'; render(); return; }
  if (a === 'save-passcode') { var inp = document.getElementById('passcode'); store('op.passcode', inp && inp.value.trim() ? inp.value.trim() : null); toast(STR.saved); return; }
  if (a === 'open-checks') { S.sheet = null; if (narrow()) { S.prevScreen = S.screen === 'checks' ? S.prevScreen : S.screen; go('checks'); } else { S.panel = 'checks'; render(); } return; }
  if (a === 'checks-back') { go(S.prevScreen || 'lock'); return; }
  if (a === 'close-sheet') { S.sheet = null; render(); return; }
  if (a === 'panel') { S.panel = el.dataset.id; render(); return; }
  if (a === 'rerun') { runChecks(); render(); toast(L('சோதனைகள் மீண்டும் ஓடின.', 'Checks ran again.')); return; }
  if (a === 'reset') {
    cancelRecording(); stopClips(); resetVoice();
    try { Object.keys(localStorage).forEach(function(k){ if (k.indexOf('op.state.') === 0) localStorage.removeItem(k); }); } catch (e) {}
    store('op.students', null);
    clearQueue();
    S = freshState(); render(); toast(L('டெமோ மீட்டமைக்கப்பட்டது.', 'Demo reset.')); return;
  }
});
document.addEventListener('change', function(ev){
  var el = ev.target; if (el.dataset && el.dataset.act === 'task') { S.done[el.dataset.id] = el.checked; render(); }
});
window.addEventListener('online', render);
window.addEventListener('offline', function(){ if (isRecording()) { cancelRecording(); resetVoice(); } render(); });

/* ---------------- start ---------------- */
function boot(){
  return loadData().then(function(){
    runChecks();
    render();
    initSync({ onChange:renderTop });
    initAudio();
    fetch('/data/eval_results.json', { cache:'no-store' }).then(function(r){ return r.ok ? r.json() : null; }).then(function(j){ EVAL = j; if (S.panel === 'checks' || S.screen === 'checks') render(); }).catch(function(){});
    registerSW();
  }).catch(function(err){
    document.getElementById('phBody').innerHTML = '<p class="warn">Could not start: ' + esc(err && err.message || err) + '</p>';
  });
}
function registerSW(){
  if (!('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register('/sw.js').then(function(){ return navigator.serviceWorker.ready; }).then(function(){
    return caches.keys();
  }).then(function(keys){
    var ours = keys.filter(function(k){ return /^op-v\d+$/.test(k); }).sort(function(a, b){ return +b.slice(4) - +a.slice(4); });
    APP_VERSION = ours[0] || null;
    return measureAppSize();
  }).then(function(){ if (S.panel === 'checks' || S.screen === 'checks' || S.sheet === 'settings') render(); }).catch(function(){});
}

window.OPENPATH = { S:function(){ return S; }, evaluate:evaluate, evaluateAll:evaluateAll, recommend:recommend, SCHEMES:SCHEMES, PATHS:PATHS,
  QUESTIONS:QUESTIONS, makePlan:makePlan, relevantMissing:relevantMissing, nextDecision:nextDecision, progressOf:progressOf, ready:boot() };
