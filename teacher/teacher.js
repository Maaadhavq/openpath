// Teacher dashboard: polls /api/class every 3 seconds. Shows progress and one blocker per student, never community, income or gender.
(function(){
  'use strict';
  var BLOCKER = { bank_account_aadhaar:'Bank account (Aadhaar)', income_certificate:'Income certificate', community_certificate:'Community certificate', aadhaar:'Aadhaar update', no_path_yet:'No path yet' };
  var NEED = {
    bank_account_aadhaar:['needs a bank account', 'need a bank account'], income_certificate:['needs an income certificate', 'need an income certificate'],
    community_certificate:['needs a community certificate', 'need a community certificate'], aadhaar:['needs an Aadhaar update', 'need an Aadhaar update'],
    no_path_yet:['has no path yet', 'have no path yet']
  };
  var ORDER = ['bank_account_aadhaar', 'income_certificate', 'community_certificate', 'aadhaar', 'no_path_yet'];
  var last = null, failures = 0;

  function $(id){ return document.getElementById(id); }
  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;' }[c]; }); }
  function hms(d){ return [d.getHours(), d.getMinutes(), d.getSeconds()].map(function(n){ return ('0' + n).slice(-2); }).join(':'); }
  function frac(s){ var m = /^(\d+)\/(\d+)$/.exec(s || ''); return m ? [+m[1], +m[2]] : null; }
  function progress(s){
    if (!s.path) return s.step === 'paths' ? 'Choosing a path' : 'Discover';
    var f = frac(s.plan_done);
    if (!f) return 'Plan';
    return f[1] > 0 && f[0] >= f[1] ? 'Plan done' : 'Plan ' + f[0] + '/' + f[1];
  }
  function key(s){ return [s.path, s.plan_done, s.blocker, s.step, s.last_event_at].join('|'); }

  function render(j){
    var st = j.students, n = st.length;
    var chose = st.filter(function(s){ return s.path; }).length;
    var finished = st.filter(function(s){ var f = frac(s.plan_done); return s.path && f && f[1] > 0 && f[0] >= f[1]; }).length;
    var counts = {}; st.forEach(function(s){ if (s.blocker) counts[s.blocker] = (counts[s.blocker] || 0) + 1; });
    var help = st.filter(function(s){ return s.blocker; }).length;
    $('school').textContent = j.school + ' · progress and blockers, live from the phones';
    $('figs').innerHTML = '<div class="fig"><b>' + chose + ' of ' + n + '</b><span>chose a path</span></div>' +
      '<div class="fig"><b>' + finished + '</b><span>finished the 4-week plan</span></div>' +
      '<div class="fig warn"><b>' + help + '</b><span>need help</span></div>';
    $('help').textContent = ORDER.filter(function(k){ return counts[k]; }).map(function(k){ return counts[k] + ' ' + NEED[k][counts[k] === 1 ? 0 : 1]; }).join(' · ');
    var prevLive = last ? last.students.filter(function(s){ return s.live; }).reduce(function(m, s){ m[s.roll] = key(s); return m; }, {}) : {};
    $('rows').innerHTML = st.map(function(s){
      var changed = last && s.live && prevLive[s.roll] !== undefined && prevLive[s.roll] !== key(s);
      var t = s.last_event_at ? hms(new Date(s.last_event_at)) : '–';
      return '<tr data-roll="' + esc(s.roll) + '"' + (s.live ? ' class="live' + (changed ? ' flash' : '') + '"' : '') + '>' +
        '<td>' + esc(s.name) + (s.live ? '<span class="livetag">(live)</span>' : '') + '</td>' +
        '<td>' + (s.path_name ? esc(s.path_name.en) + '<span class="ta">' + esc(s.path_name.ta) + '</span>' : 'Not chosen') + '</td>' +
        '<td>' + esc(progress(s)) + '</td>' +
        '<td' + (s.blocker ? ' class="blk"' : '') + '>' + (s.blocker ? esc(BLOCKER[s.blocker] || s.blocker) : '–') + '</td>' +
        '<td class="time">' + t + '</td></tr>';
    }).join('');
    // The changed row turns ochre, then fades back to its usual colour.
    var flashed = document.querySelectorAll('tr.flash');
    if (flashed.length) requestAnimationFrame(function(){ setTimeout(function(){ flashed.forEach(function(r){ r.classList.remove('flash'); }); }, 900); });
    $('lastEvent').textContent = j.last_event ? JSON.stringify(j.last_event, null, 2) : 'Nothing yet.';
    last = j;
  }

  function poll(){
    fetch('/api/class', { cache:'no-store' }).then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); }).then(function(j){
      failures = 0; $('notice').hidden = true;
      render(j);
      $('updated').textContent = 'Updated ' + hms(new Date());
    }).catch(function(){
      failures++;
      $('notice').hidden = false;
      $('notice').textContent = 'Could not reach the server' + (failures > 1 ? ' (' + failures + ' tries)' : '') + '. The free server may be waking up; this keeps trying every 3 seconds.';
    });
  }

  function passcode(force){
    var p = null;
    try { p = localStorage.getItem('op.teacher.passcode'); } catch (e) {}
    if (!p || force) {
      p = window.prompt('Demo passcode');
      if (!p) return null;
      try { localStorage.setItem('op.teacher.passcode', p); } catch (e) {}
    }
    return p;
  }
  function reset(force){
    var p = passcode(force); if (!p) return;
    fetch('/api/reset', { method:'POST', headers:{ 'X-Demo-Passcode': p } }).then(function(r){
      if (r.status === 401) { try { localStorage.removeItem('op.teacher.passcode'); } catch (e) {} if (!force) return reset(true); window.alert('Wrong passcode.'); return; }
      if (!r.ok) throw new Error(r.status);
      last = null; poll();
    }).catch(function(){ window.alert('Could not reset: the server did not answer.'); });
  }

  $('reset').addEventListener('click', function(){ reset(false); });
  poll();
  setInterval(poll, 3000);
})();
