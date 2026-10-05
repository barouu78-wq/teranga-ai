// Teranga AI — service worker : site utilisable hors ligne.
// Ressources statiques : cache d'abord (mise à jour en arrière-plan).
// Pages : réseau d'abord, copie gardée ; hors ligne → copie ou page /offline.
// Jamais en cache : chat, voix, API, jeton CSRF, proxy d'images.
const VERSION = 'teranga-v2';
const STATIC_CACHE = VERSION + '-static';
const PAGES_CACHE = VERSION + '-pages';
const MAX_PAGES = 40;
// Scripts sans empreinte : hors ligne, la page versionnée (?v=…) retombe sur
// cette copie grâce à ignoreSearch, dès la première visite.
const PRECACHE = ['/offline', '/static/site.css', '/static/theme.js', '/static/home.js', '/static/trip-planner.js',
  '/static/share-page.js', '/static/offline.js', '/icon.svg', '/icon-192.png', '/manifest.webmanifest'];
// Pages gardées dès l'installation : l'accueil et l'annuaire des lieux.
const PRECACHE_PAGES = ['/', '/lieux'];
const NEVER_CACHE = ['/chat', '/tts', '/stt', '/realtime-call', '/csrf', '/api/', '/image-proxy', '/explorer-image', '/exchange-rates', '/sw.js'];
const STATIC_PREFIXES = ['/static/', '/icon', '/og.', '/favicon.ico', '/manifest.webmanifest'];

self.addEventListener('install', event => {
  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then(cache => cache.addAll(PRECACHE)),
      // Pages rangées avec les pages pour que l'app s'ouvre hors ligne.
      caches.open(PAGES_CACHE).then(cache => cache.addAll(PRECACHE_PAGES)),
    ]).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(key => !key.startsWith(VERSION)).map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

async function trimPages() {
  const cache = await caches.open(PAGES_CACHE);
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - MAX_PAGES; i++) await cache.delete(keys[i]);
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);
  const network = fetch(request).then(response => {
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  }).catch(() => cached || cache.match(request, { ignoreSearch: true }));
  // Fichier versionné (?v=…) pas encore en cache : réseau, et hors ligne la
  // dernière copie connue du même fichier.
  return cached || network;
}

async function networkFirstPage(request) {
  const cache = await caches.open(PAGES_CACHE);
  try {
    const response = await fetch(request);
    if (response && response.ok && response.type === 'basic') {
      await cache.put(request, response.clone());
      trimPages();
    }
    return response;
  } catch (_) {
    const cached = await cache.match(request, { ignoreSearch: false });
    if (cached) return cached;
    const offline = await caches.match('/offline');
    return offline || new Response('Hors ligne', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
  }
}

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (NEVER_CACHE.some(prefix => url.pathname === prefix || url.pathname.startsWith(prefix))) return;
  if (request.mode === 'navigate') {
    event.respondWith(networkFirstPage(request));
    return;
  }
  if (STATIC_PREFIXES.some(prefix => url.pathname.startsWith(prefix))) {
    event.respondWith(staleWhileRevalidate(request));
  }
});
