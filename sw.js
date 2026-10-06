// Dinner Saver offline cache (f1472bb6). Network first, so updates show straight away; the cache covers no signal at the shops.
const CACHE = "dinner-saver-f1472bb6";
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(["./", "./index.html", "./manifest.webmanifest", "./icon-192.png"]))); self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(fetch(e.request).then(r => { if (r.ok || r.type === "opaque") { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); } return r; })
    .catch(() => caches.match(e.request).then(m => m || (e.request.mode === "navigate" ? caches.match("./index.html") : undefined))));
});
