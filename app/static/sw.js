// Service Worker for ROX Quant PWA
const CACHE_NAME = 'rox-quant-v1';
const urlsToCache = [
  '/',
  '/static/css/all.min.css',
  '/static/js/main.js',
  '/static/js/keyboard_commander.js',
  '/static/js/watchlist.js',
  '/static/js/auth_ui.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // 返回缓存或网络请求
        return response || fetch(event.request);
      })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
