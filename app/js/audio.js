// Plays the pre-made Tamil clips (made once with Bulbul by scripts/gen_audio.py and shipped in /audio).
// One <audio> element; clips always start from a user tap, so autoplay rules are met.
let index = null;      // keys that have a clip, from audio/index.json
let queue = [];
let el = null;

export function initAudio(){
  el = document.getElementById('clip');
  if (el) el.addEventListener('ended', next);
  return fetch('/audio/index.json').then(function(r){ return r.ok ? r.json() : null; })
    .then(function(j){ index = j && Array.isArray(j.keys) ? new Set(j.keys) : new Set(); })
    .catch(function(){ index = new Set(); });
}
export function hasClip(key){ return !!(index && index.has(key)); }

// Plays the clips that exist, in order. Returns how many will play.
export function playClips(keys){
  stopClips();
  queue = keys.filter(hasClip);
  if (!queue.length || !el) return 0;
  var n = queue.length;
  next();
  return n;
}
function next(){
  if (!el || !queue.length) return;
  var key = queue.shift();
  el.src = '/audio/' + key + '.mp3';
  var p = el.play();
  if (p && p.catch) p.catch(function(){ queue = []; });
}
export function stopClips(){
  queue = [];
  if (el) { try { el.pause(); } catch (e) {} }
}
