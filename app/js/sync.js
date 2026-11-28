// Offline sync queue. Holds progress snapshots in localStorage (op.queue) and sends them to /api/sync when online.
// An event carries only the roll number, step, path, plan progress (overall and per week), the kind of next step, one
// blocker and, for a student who joined on the phone, her first name: never the profile or answers.
// Sends: right after a change, at start, when the network comes back, when the app returns to the foreground,
// every 15 s, and after a failure at 2, 4 and 8 s (the radio often needs a few seconds after airplane mode goes off).
const QUEUE = 'op.queue', LAST = 'op.lastQueued', AT = 'op.syncedAt';
const FIELDS = ['step', 'path', 'plan_done', 'blocker', 'weeks', 'next_task', 'name'];
let onChange = function(){};
let failed = false, sending = false, timer = null, retry = null, fails = 0;

function load(k, d){ try { var v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }
function save(k, v){ try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
function uuid(){
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  var b = new Uint8Array(16); crypto.getRandomValues(b);
  return Array.prototype.map.call(b, function(x){ return ('0' + x.toString(16)).slice(-2); }).join('').replace(/^(.{8})(.{4})(.{4})(.{4})/, '$1-$2-$3-$4-');
}

export function initSync(opts){
  onChange = (opts && opts.onChange) || onChange;
  window.addEventListener('online', function(){ failed = false; fails = 0; flush(); });
  window.addEventListener('offline', function(){ onChange(); });
  document.addEventListener('visibilitychange', function(){ if (document.visibilityState === 'visible') flush(); });
  window.addEventListener('pageshow', function(){ flush(); });
  if (timer) clearInterval(timer);
  timer = setInterval(function(){ if (navigator.onLine !== false) flush(); }, 15000);
  flush();
}

// Adds a snapshot unless it is the same as the last one queued.
export function enqueue(student, progress, name){
  var p = { step: progress.step, path: progress.path, plan_done: progress.plan_done, blocker: progress.blocker,
    weeks: progress.weeks || null, next_task: progress.next_task || null, name: name || null };
  var last = load(LAST, null);
  if (last && last.student === student && FIELDS.every(function(k){ return JSON.stringify(last[k] == null ? null : last[k]) === JSON.stringify(p[k]); })) return false;
  var ev = { event_id: uuid(), student: student, ts: new Date().toISOString(), step: p.step, path: p.path, plan_done: p.plan_done, blocker: p.blocker };
  if (p.weeks) ev.weeks = p.weeks;
  if (p.next_task) ev.next_task = p.next_task;
  if (p.name) ev.name = p.name;
  var q = load(QUEUE, []); q.push(ev); save(QUEUE, q);
  save(LAST, { student: student, step: p.step, path: p.path, plan_done: p.plan_done, blocker: p.blocker, weeks: p.weeks, next_task: p.next_task, name: p.name });
  onChange();
  if (navigator.onLine !== false && !sending) setTimeout(flush, 0);   // send right away when online, so the teacher view stays live
  return true;
}

export function queueCount(){ return load(QUEUE, []).length; }
export function syncedAt(){
  var t = load(AT, null); if (!t) return null;
  var d = new Date(t); return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
}
export function netFailed(){ return failed; }
export function clearQueue(){ save(QUEUE, null); save(LAST, null); save(AT, null); onChange(); }

function retrySoon(){
  if (retry) return;
  var wait = Math.min(15000, 2000 * Math.pow(2, Math.max(0, fails - 1)));
  retry = setTimeout(function(){ retry = null; flush(); }, wait);
}

export function flush(){
  if (sending || navigator.onLine === false) return Promise.resolve();
  var q = load(QUEUE, []);
  if (!q.length) return Promise.resolve();
  sending = true;
  var batch = q.slice(0, 50), ctl = new AbortController(), stop = setTimeout(function(){ ctl.abort(); }, 30000);
  return fetch('/api/sync', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ events: batch }), signal: ctl.signal })
    .then(function(r){
      if (r.status === 422) { console.warn('sync: the server rejected a batch; dropping it'); return { accepted: batch.map(function(e){ return e.event_id; }), duplicates: [] }; }
      if (!r.ok) throw new Error('sync ' + r.status);
      return r.json();
    })
    .then(function(j){
      var gone = new Set((j.accepted || []).concat(j.duplicates || []));
      save(QUEUE, load(QUEUE, []).filter(function(e){ return !gone.has(e.event_id); }));
      save(AT, new Date().toISOString());
      failed = false; fails = 0;
      if (retry) { clearTimeout(retry); retry = null; }
    }, function(){ failed = true; fails++; })
    .then(function(){
      clearTimeout(stop);
      sending = false; onChange();
      if (failed) { if (navigator.onLine !== false) retrySoon(); return; }
      if (queueCount() && navigator.onLine !== false) return flush();
    });
}
