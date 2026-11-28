// OpenPath for teachers. Polls /api/class every 3 seconds. Shows only what students' phones share:
// roll number, first name (students who joined on the phone), path, plan progress, next step, one blocker and last use.
// Never community, income, gender, documents held, answers or scheme eligibility.
(function(){
  'use strict';
  var CODE_KEY = 'op.teacher.code';
  var S = { tab: 'overview', data: null, filter: 'all', sort: 'roll', q: '', open: null, detail: null, flash: {}, keys: {}, chat: [], failures: 0, timer: null };

  /* ---------------- helpers ---------------- */
  function $(id){ return document.getElementById(id); }
  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }[c]; }); }
  function bi(x, inline){ return x ? esc(x.en) + (x.ta ? (inline ? ' <span class="ta">' : '<span class="ta tb">') + esc(x.ta) + '</span>' : '') : '–'; }
  function code(){ try { return localStorage.getItem(CODE_KEY) || ''; } catch (e) { return ''; } }
  function setCode(v){ try { if (v) localStorage.setItem(CODE_KEY, v); else localStorage.removeItem(CODE_KEY); } catch (e) {} }
  function two(n){ return ('0' + n).slice(-2); }
  function hm(iso){ var d = new Date(iso); return two(d.getHours()) + ':' + two(d.getMinutes()); }
  function ago(iso){
    if (!iso) return 'never';
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return 'just now';
    if (s < 3600) return Math.round(s / 60) + ' min ago';
    if (s < 86400) return Math.round(s / 3600) + ' h ago';
    var d = Math.floor(s / 86400); return d === 1 ? 'yesterday' : d + ' days ago';
  }
  function toast(msg){ var t = $('toast'); t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(function(){ t.hidden = true; }, 2600); }
  function api(path, opts){
    opts = opts || {};
    opts.cache = 'no-store';
    opts.headers = Object.assign({ 'X-Teacher-Code': code() }, opts.headers || {});
    return fetch(path, opts).then(function(r){
      if (r.ok) return r.json();
      var e = new Error('HTTP ' + r.status); e.status = r.status; throw e;
    });
  }
  function needWords(g){ return g.count + ' ' + (g.count === 1 ? g.need.en[0] : g.need.en[1]); }
  function needTa(g){ return g.count + ' பேருக்கு ' + g.need.ta; }
  function label(status){ var L = S.data && S.data.status_labels; return L && L[status] ? L[status] : { en: status, ta: '' }; }
  function blockerLabel(key){
    var g = S.data && S.data.summary.groups.filter(function(x){ return x.blocker === key; })[0];
    return g ? g.label : null;
  }
  function who(list, max){
    var names = list.map(function(s){ return '<button class="btn link" data-open="' + esc(s.roll) + '">' + esc(s.name) + '</button>'; });
    if (max && names.length > max) return names.slice(0, max).join(', ') + ' and ' + (names.length - max) + ' more';
    return names.join(', ');
  }

  /* ---------------- sign-in ---------------- */
  function showSignin(msg){
    stopPolling();
    $('app').hidden = true; $('signin').hidden = false;
    $('signinMsg').hidden = !msg; $('signinMsg').textContent = msg || '';
    setTimeout(function(){ $('code').focus(); }, 0);
  }
  function explain(e){
    if (e && e.status === 401) return 'That class code is not right.';
    if (e && e.status === 429) return 'Too many tries. Wait a minute and try again.';
    if (e && e.status === 503) return 'The server has no class code yet. Add TEACHER_CODE (or DEMO_PASSCODE) in the Render dashboard.';
    return 'Could not reach the server. The free server may be waking up; try again in a minute.';
  }
  function signIn(){
    return api('/api/class').then(function(j){
      $('signin').hidden = true; $('app').hidden = false;
      S.data = j; S.failures = 0;
      $('updated').textContent = 'Updated ' + two(new Date().getHours()) + ':' + two(new Date().getMinutes()) + ':' + two(new Date().getSeconds());
      renderAll(); startPolling();
    }).catch(function(e){ showSignin(code() ? explain(e) : ''); });
  }
  $('signinForm').addEventListener('submit', function(ev){ ev.preventDefault(); setCode($('code').value.trim()); signIn(); });
  $('signout').addEventListener('click', function(){ setCode(null); S.chat = []; closeDrawer(); showSignin(''); });

  /* ---------------- polling ---------------- */
  function startPolling(){ stopPolling(); S.timer = setInterval(poll, 3000); }
  function stopPolling(){ if (S.timer) clearInterval(S.timer); S.timer = null; }
  function poll(){
    api('/api/class').then(function(j){
      S.failures = 0; $('notice').hidden = true;
      S.data = j; markFlashes(); renderAll(true);
      $('updated').textContent = 'Updated ' + two(new Date().getHours()) + ':' + two(new Date().getMinutes()) + ':' + two(new Date().getSeconds());
      if (S.open) loadDetail(S.open);
    }).catch(function(e){
      if (e.status === 401 || e.status === 503) { showSignin(explain(e)); return; }
      S.failures++;
      $('notice').hidden = false;
      $('notice').textContent = 'Could not reach the server' + (S.failures > 1 ? ' (' + S.failures + ' tries)' : '') + '. The free server may be waking up; this keeps trying every 3 seconds.';
    });
  }
  // A live student's row turns ochre for a moment when her phone sends something new.
  function markFlashes(){
    var now = {};
    S.data.students.forEach(function(s){ if (s.live) now[s.roll] = [s.path, s.plan_done, s.blocker, s.step, s.last_event_at].join('|'); });
    S.flash = {};
    Object.keys(now).forEach(function(r){ if (S.keys[r] !== undefined && S.keys[r] !== now[r]) S.flash[r] = true; });
    S.keys = now;
    if (Object.keys(S.flash).length) setTimeout(function(){ document.querySelectorAll('tr.flash').forEach(function(t){ t.classList.remove('flash'); }); }, 900);
  }

  /* ---------------- tabs ---------------- */
  document.querySelector('.tabs').addEventListener('click', function(ev){
    var b = ev.target.closest('[data-tab]'); if (!b) return; go(b.dataset.tab);
  });
  function go(tab){
    S.tab = tab;
    document.querySelectorAll('.tabs [data-tab]').forEach(function(b){ b.setAttribute('aria-selected', String(b.dataset.tab === tab)); });
    ['overview', 'students', 'actions', 'ask'].forEach(function(t){ $('v-' + t).hidden = t !== tab; });
    renderAll();
    if (tab === 'ask') setTimeout(function(){ $('askInput').focus(); }, 0);
  }
  function renderAll(fromPoll){
    if (!S.data) return;
    $('school').textContent = S.data.school;
    if (S.tab === 'overview') renderOverview();
    if (S.tab === 'students') renderStudents();
    if (S.tab === 'actions' && !(fromPoll && document.activeElement && $('v-actions').contains(document.activeElement))) renderActions();
    if (S.tab === 'ask' && !fromPoll) renderAskIntro();
  }

  /* ---------------- overview ---------------- */
  function fig(value, en, ta, warn){ return '<div class="fig' + (warn ? ' alert' : '') + '"><b>' + value + '</b><span>' + esc(en) + ' <span class="ta">' + esc(ta) + '</span></span></div>'; }
  function renderOverview(){
    var d = S.data, m = d.summary;
    var max = Math.max.apply(null, m.path_mix.map(function(p){ return p.count; }).concat([1]));
    var h = '<div class="figs">' +
      fig(m.chose_path + ' of ' + m.total, 'chose a path', 'பாதை தேர்ந்தெடுத்தனர்') +
      fig(m.on_track, 'on track or done', 'சரியாகப் போகின்றனர்') +
      fig(m.need_help, 'need help with a document', 'ஆவண உதவி தேவை', m.need_help > 0) +
      fig(m.inactive, 'no update for 7+ days', '7 நாளுக்கு மேல் புதுப்பிப்பு இல்லை', m.inactive > 0) + '</div>';
    h += '<div class="grid2"><section class="box"><div class="box-head"><h2>This week <span class="ta">இந்த வாரம்</span></h2><button class="btn link" data-goto="actions">All actions</button></div>' +
      (m.groups.length ? m.groups.map(function(g){
        return '<div class="group"><b>' + esc(needWords(g)) + ' <span class="ta">' + esc(needTa(g)) + '</span></b>' +
          '<span class="who">' + who(g.students, 4) + '</span><span>' + esc(g.action.en) + '</span></div>';
      }).join('') : '<p class="note">Nobody is blocked this week.</p>') + '</section>';
    h += '<section class="box" id="feed"><h2>Live from the phones <span class="ta">போன்களிலிருந்து</span></h2>' +
      (d.feed.length ? '<ul class="feed">' + d.feed.slice(0, 8).map(function(f){
        return '<li><time datetime="' + esc(f.ts) + '">' + hm(f.ts) + '</time><span><button class="btn link" data-open="' + esc(f.roll) + '">' + esc(f.name) + '</button> ' + esc(f.text.en) + '</span></li>';
      }).join('') + '</ul>' : '<p class="note">Nothing yet. When a student\'s phone syncs, it shows here within seconds.</p>') + '</section>';
    h += '<section class="box"><h2>Paths chosen <span class="ta">தேர்ந்தெடுத்த பாதைகள்</span></h2><ul class="bars">' + m.path_mix.map(function(p){
        return '<li><span>' + esc(p.name.en) + '</span><span class="barline"><i style="width:' + Math.round(100 * p.count / max) + '%"></i></span><span>' + p.count + '</span></li>';
      }).join('') + '</ul><p class="note">' + m.not_started + ' have not chosen yet. Paths are never filtered by gender.</p></section>';
    h += '<section class="box"><h2>Coming up <span class="ta">அடுத்து வருபவை</span></h2><ul class="dl">' + m.deadlines.map(function(x){
        return '<li><span>' + bi(x.text) + '</span><span>' + x.count + ' students</span></li>';
      }).join('') + '</ul></section></div>';
    h += '<div class="cols"><details class="box" open><summary>What the phone sent <span class="ta">போன் அனுப்பியது</span></summary><pre id="lastEvent">' +
      (d.last_event ? esc(JSON.stringify(d.last_event, null, 2)) : 'Nothing yet.') + '</pre></details>' +
      '<div class="box"><h2>What never leaves the phone</h2><p class="note">Community, family income, gender, the documents she holds, marks, her answers, scheme eligibility and her voice recording. Her voice answer is sent only to be turned into text, and is not stored. A student who joins on the phone sends her first name.</p></div></div>';
    $('v-overview').innerHTML = h;
  }

  /* ---------------- students ---------------- */
  var FILTERS = [['all', 'All'], ['needs_help', 'Needs help'], ['not_started', 'Not started'], ['inactive', 'No update 7+ days'], ['done', 'Plan done'], ['new', 'New']];
  function matches(s){
    var f = S.filter;
    if (f === 'needs_help' && !(s.blocker && s.blocker !== 'no_path_yet')) return false;
    if (f === 'not_started' && s.status !== 'not_started') return false;
    if (f === 'inactive' && !(s.days_since_active != null && s.days_since_active >= 7)) return false;
    if (f === 'done' && s.status !== 'done') return false;
    if (f === 'new' && !s.new) return false;
    var q = S.q.trim().toLowerCase();
    return !q || s.name.toLowerCase().indexOf(q) >= 0 || s.roll.toLowerCase().indexOf(q) >= 0;
  }
  function count(f){ var keep = S.filter, k = S.q; S.filter = f; S.q = ''; var n = S.data.students.filter(matches).length; S.filter = keep; S.q = k; return n; }
  function renderStudents(){
    $('filters').innerHTML = FILTERS.map(function(f){ return '<button data-filter="' + f[0] + '" aria-pressed="' + (S.filter === f[0]) + '">' + f[1] + ' (' + count(f[0]) + ')</button>'; }).join('');
    var list = S.data.students.filter(matches).slice();
    var by = { roll: function(a, b){ return a.roll < b.roll ? -1 : 1; }, name: function(a, b){ return a.name.localeCompare(b.name); },
      progress: function(a, b){ return b.progress_pct - a.progress_pct; },
      active: function(a, b){ return (a.days_since_active == null ? 1e9 : a.days_since_active) - (b.days_since_active == null ? 1e9 : b.days_since_active); } }[S.sort];
    list.sort(by);
    if (!list.length) { $('studentList').innerHTML = '<div class="tbl"><p class="empty">No students match.</p></div>'; return; }
    $('studentList').innerHTML = '<div class="tbl"><table><thead><tr><th>Student</th><th>Path</th><th>Progress</th><th>Status</th><th>Blocker</th><th>Last update</th></tr></thead><tbody>' +
      list.map(function(s){
        var st = label(s.status), blk = s.blocker ? blockerLabel(s.blocker) : null;
        return '<tr data-roll="' + esc(s.roll) + '" tabindex="0"' + (s.live ? ' class="live' + (S.flash[s.roll] ? ' flash' : '') + '"' : '') + '>' +
          '<td><b>' + esc(s.name) + '</b>' + (s.new ? '<span class="tag-new">(new)</span>' : '') + (s.live ? '<span class="tag-live">(live)</span>' : '') + '<span class="ta">' + esc(s.roll) + '</span></td>' +
          '<td class="c-path">' + (s.path_name ? bi(s.path_name) : '<span class="muted">Not chosen</span>') + '</td>' +
          '<td class="c-prog">' + (s.total ? '<div class="prog"><span class="barline"><i style="width:' + s.progress_pct + '%"></i></span><span class="small">Plan ' + s.done + '/' + s.total + '</span></div>' : '<span class="muted">' + (s.step === 'paths' ? 'Choosing a path' : 'Discover') + '</span>') + '</td>' +
          '<td class="st st-' + s.status + '">' + esc(s.status === 'inactive' ? 'No update for ' + s.days_since_active + ' days' : st.en) + '</td>' +
          '<td' + (blk && s.blocker !== 'no_path_yet' ? ' class="blk"' : '') + '>' + (blk ? esc(blk.en) : '–') + '</td>' +
          '<td class="time">' + ago(s.last_event_at) + '</td></tr>';
      }).join('') + '</tbody></table></div>';
  }
  $('filters').addEventListener('click', function(ev){ var b = ev.target.closest('[data-filter]'); if (!b) return; S.filter = b.dataset.filter; renderStudents(); });
  $('search').addEventListener('input', function(){ S.q = this.value; renderStudents(); });
  $('sort').addEventListener('change', function(){ S.sort = this.value; renderStudents(); });
  $('studentList').addEventListener('keydown', function(ev){ var tr = ev.target.closest('tr[data-roll]'); if (tr && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); openDrawer(tr.dataset.roll); } });

  /* ---------------- student drawer ---------------- */
  function openDrawer(roll){ S.open = roll; S.detail = null; $('drawer').hidden = false; $('drawerBg').hidden = false; $('drawer').innerHTML = '<p class="note">Loading…</p>'; loadDetail(roll); }
  function closeDrawer(){ S.open = null; $('drawer').hidden = true; $('drawerBg').hidden = true; }
  function loadDetail(roll){
    api('/api/student/' + encodeURIComponent(roll)).then(function(d){ if (S.open === roll) { S.detail = d; renderDrawer(d); } }).catch(function(){});
  }
  function renderDrawer(d){
    var st = label(d.status);
    var h = '<header><div><h2>' + esc(d.name) + '</h2><p class="muted">' + esc(d.roll) + (d.new ? ' · new on the phone' : '') + (d.live ? ' · live' : '') + ' · last update ' + ago(d.last_event_at) + '</p>' +
      '<p class="st st-' + d.status + '">' + bi(st, true) + '</p></div><button class="btn quiet" id="closeDrawer" type="button">Close</button></header>';
    h += '<section><h3>Path <span class="ta">பாதை</span></h3>' + (d.path_name ? '<p><b>' + bi(d.path_name, true) + '</b></p><p class="note">' + bi(d.route) + '</p>' : '<p class="muted">Not chosen yet.</p>') + '</section>';
    h += '<section><h3>Plan <span class="ta">திட்டம்</span></h3>';
    if (d.total) {
      h += '<div class="prog"><span class="barline"><i style="width:' + d.progress_pct + '%"></i></span><span class="small">' + d.done + ' of ' + d.total + ' steps</span></div>';
      if (d.weeks) h += '<ul class="weeks">' + d.weeks.map(function(w, i){ var p = w.split('/'), pct = +p[1] ? Math.round(100 * p[0] / p[1]) : 0; return '<li><span>Week ' + (i + 1) + '</span><span class="barline"><i style="width:' + pct + '%"></i></span><span class="small">' + esc(w) + '</span></li>'; }).join('') + '</ul>';
    }
    h += '<div class="next"><span class="small">Next step</span><br><b>' + bi(d.next_step, true) + '</b></div></section>';
    if (d.help) {
      h += '<section><h3>How you can help <span class="ta">நீங்கள் உதவலாம்</span></h3><div class="help"><b>' + bi(d.help.label, true) + '</b><span>' + esc(d.help.action.en) + '</span>' +
        (d.help.where ? '<span class="small">Where: ' + esc(d.help.where.en) + '</span>' : '') + '</div>' +
        '<details><summary>Message for her parents</summary><pre>' + esc(d.help.parent.ta + '\n\n' + d.help.parent.en) + '</pre><button class="btn quiet" type="button" data-copy="' + esc(d.help.parent.ta + '\n\n' + d.help.parent.en) + '">Copy message</button></details></section>';
    }
    h += '<section><h3>Coming up <span class="ta">அடுத்து</span></h3><ul class="dl">' + d.deadlines.map(function(x){ return '<li><span>' + bi(x) + '</span></li>'; }).join('') + '</ul>' +
      (d.visit ? '<p class="note">Visit idea: ' + esc(d.visit.en) + '</p>' : '') + '</section>';
    h += '<section><h3>Activity from her phone <span class="ta">செயல்பாடு</span></h3>' + (d.history.length ? '<ul class="hist">' + d.history.slice(0, 12).map(function(x){ return '<li><time>' + hm(x.ts) + '</time>' + esc(x.text.en) + '</li>'; }).join('') + '</ul>' : '<p class="note">No activity from the phone yet.</p>') + '</section>';
    h += '<section><h3>What her phone shares</h3><ul class="shares">' + d.shared.en.map(function(x){ return '<li>' + esc(x) + '</li>'; }).join('') + '</ul><p class="note">Never shared: ' + esc(d.never.en) + '.</p></section>';
    $('drawer').innerHTML = h;
  }
  $('drawerBg').addEventListener('click', closeDrawer);
  document.addEventListener('keydown', function(ev){ if (ev.key === 'Escape' && S.open) closeDrawer(); });

  /* ---------------- actions ---------------- */
  function renderActions(){
    var g = S.data.summary.groups;
    $('v-actions').innerHTML = g.length ? g.map(function(x){
      var msg = x.parent.ta + '\n\n' + x.parent.en;
      return '<article class="box action" id="act-' + esc(x.blocker) + '"><h2>' + esc(needWords(x)) + '<span class="ta">' + esc(needTa(x)) + '</span></h2>' +
        '<p>' + esc(x.action.en) + '</p><p class="ta">' + esc(x.action.ta) + '</p>' +
        (x.where ? '<p class="note">Where: ' + esc(x.where.en) + '</p>' : '') +
        '<ul class="names">' + x.students.map(function(s){ return '<li><button class="btn link" data-open="' + esc(s.roll) + '">' + esc(s.name) + '</button> <span class="small">' + esc(s.roll) + '</span></li>'; }).join('') + '</ul>' +
        '<details><summary>Message for parents (Tamil and English)</summary><pre>' + esc(msg) + '</pre></details>' +
        '<div class="row"><button class="btn quiet" type="button" data-copy="' + esc(msg) + '">Copy parent message</button><button class="btn quiet" type="button" data-print="act-' + esc(x.blocker) + '">Print this list</button></div></article>';
    }).join('') : '<div class="box"><p>Nobody is blocked this week.</p></div>';
  }

  /* ---------------- ask ---------------- */
  function renderAskIntro(){
    var lang = $('askLang').value, sug = S.data.suggestions || [];
    $('suggest').innerHTML = sug.map(function(x){ return '<button type="button" data-ask="' + esc(x[lang]) + '">' + esc(x[lang]) + '</button>'; }).join('');
    renderChat();
  }
  function renderChat(){
    var lang = $('askLang').value;
    $('chat').innerHTML = S.chat.map(function(m){
      var h = '<div class="q">' + esc(m.q) + '</div>';
      if (m.pending) return h + '<div class="a"><span class="muted">Thinking…</span></div>';
      if (m.error) return h + '<div class="a"><span class="warn">' + esc(m.error) + '</span></div>';
      var a = m.a, meta = a.source === 'rules' ? 'Answered from your class data.' : a.source === 'llm' ? 'Answered by Sarvam-105B from your class data and the scheme notes. Check before acting.' : '';
      return h + '<div class="a"><div class="text">' + esc(a.answer) + '</div>' +
        (a.suggestions ? '<div class="suggest">' + a.suggestions.map(function(x){ return '<button type="button" data-ask="' + esc(x[lang]) + '">' + esc(x[lang]) + '</button>'; }).join('') + '</div>' : '') +
        (a.used && a.used.length ? '<div class="meta">Based on: ' + who(a.used, 8) + '</div>' : '') +
        (a.sources && a.sources.length ? '<div class="meta">Sources: ' + a.sources.map(function(s){ return '<a href="' + esc(s.url) + '" target="_blank" rel="noopener">' + esc(s.label) + '</a>'; }).join(' · ') + '</div>' : '') +
        (meta ? '<div class="meta">' + meta + '</div>' : '') + '</div>';
    }).join('');
    var c = $('chat'); if (c.lastElementChild) c.lastElementChild.scrollIntoView({ block: 'nearest' });
  }
  function askQ(q){
    q = (q || '').trim(); if (!q) return;
    var m = { q: q, pending: true }; S.chat.push(m); renderChat();
    api('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q, lang: $('askLang').value }) })
      .then(function(a){ m.pending = false; m.a = a; renderChat(); })
      .catch(function(e){ m.pending = false; m.error = e.status === 429 ? 'Too many questions in a minute. Wait a little.' : 'Could not get an answer. Try again.'; renderChat(); });
  }
  $('askForm').addEventListener('submit', function(ev){ ev.preventDefault(); var i = $('askInput'); askQ(i.value); i.value = ''; });
  $('askLang').addEventListener('change', renderAskIntro);

  /* ---------------- shared clicks ---------------- */
  document.addEventListener('click', function(ev){
    var t = ev.target;
    var open = t.closest('[data-open]'); if (open) { openDrawer(open.dataset.open); return; }
    var row = t.closest('tr[data-roll]'); if (row) { openDrawer(row.dataset.roll); return; }
    if (t.closest('#closeDrawer')) { closeDrawer(); return; }
    var g = t.closest('[data-goto]'); if (g) { go(g.dataset.goto); return; }
    var a = t.closest('[data-ask]'); if (a) { askQ(a.dataset.ask); return; }
    var c = t.closest('[data-copy]');
    if (c) {
      var text = c.dataset.copy;
      (navigator.clipboard && navigator.clipboard.writeText ? navigator.clipboard.writeText(text) : Promise.reject()).then(function(){ toast('Copied. Paste it into WhatsApp or SMS.'); }, function(){ toast('Select the message and copy it.'); });
      return;
    }
    var p = t.closest('[data-print]');
    if (p) {
      var card = $(p.dataset.print); card.classList.add('print-me'); document.body.classList.add('printing');
      window.print();
      setTimeout(function(){ card.classList.remove('print-me'); document.body.classList.remove('printing'); }, 500);
    }
  });
  $('reset').addEventListener('click', function(){
    if (!window.confirm('Put the class back to the 25 sample students? Live rows from phones will be cleared.')) return;
    api('/api/reset', { method: 'POST' }).then(function(){ S.keys = {}; closeDrawer(); poll(); toast('Demo reset.'); })
      .catch(function(e){ toast(e.status === 401 ? 'Reset needs the class code.' : 'Could not reset: the server did not answer.'); });
  });

  /* ---------------- start ---------------- */
  if (code()) signIn(); else showSignin('');
})();
