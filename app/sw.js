// OpenPath service worker: keeps the whole student app on the phone so it works in airplane mode.
// Bump the number on every deploy, otherwise phones keep the old version.
const CACHE = 'op-v2';

const CORE = [
  '/', '/index.html', '/app.css', '/manifest.webmanifest',
  '/js/engine.js', '/js/strings.js', '/js/ui.js', '/js/voice.js', '/js/sync.js', '/js/audio.js', '/js/checks.js',
  '/data/questions.json', '/data/paths.json', '/data/prompts.json',
  '/icons/icon-192.png', '/icons/icon-512.png', '/icons/maskable-512.png'
];
// These may not exist yet (no measurements, or no clips made); a missing one must not break the install.
const OPTIONAL = ['/data/eval_results.json', '/audio/index.json'];

self.addEventListener('install', function(event){
  event.waitUntil(caches.open(CACHE).then(function(cache){
    return cache.addAll(CORE.map(function(u){ return new Request(u, { cache: 'reload' }); })).then(function(){
      return Promise.all(OPTIONAL.map(function(u){ return addIfThere(cache, u); }));
    }).then(function(){
      // Every clip listed in audio/index.json (made by scripts/gen_audio.py).
      return cache.match('/audio/index.json').then(function(res){ return res ? res.json() : { keys: [] }; }).then(function(idx){
        return Promise.all((idx.keys || []).map(function(k){ return addIfThere(cache, '/audio/' + k + '.mp3'); }));
      });
    });
  }).then(function(){ return self.skipWaiting(); }));
});
function addIfThere(cache, url){
  return fetch(new Request(url, { cache: 'reload' })).then(function(res){ return res.ok ? cache.put(url, res) : null; }).catch(function(){ return null; });
}

self.addEventListener('activate', function(event){
  event.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.filter(function(k){ return k !== CACHE; }).map(function(k){ return caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});

self.addEventListener('fetch', function(event){
  var req = event.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // The API and the teacher dashboard always go to the network.
  if (url.pathname.indexOf('/api/') === 0 || url.pathname.indexOf('/teacher') === 0) return;
  if (req.mode === 'navigate') {
    event.respondWith(caches.match('/index.html').then(function(hit){ return hit || fetch(req); }));
    return;
  }
  // Static files: cache first, then the network.
  event.respondWith(caches.match(req, { ignoreSearch: true }).then(function(hit){ return hit || fetch(req); }));
});
