const CACHE_NAME = 'twinsync-v2';
const ASSETS = [
    '/',
    '/index.html',
    '/css/styles.css',
    '/js/app.js',
    '/manifest.json'
];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS).catch(err => {
                console.log('SW asset caching issue (can be ignored in dev):', err);
            });
        })
    );
});

self.addEventListener('fetch', (e) => {
    // Only cache static assets and ignore API endpoints
    if (e.request.url.includes('/api/') || e.request.url.includes('socket.io')) {
        return fetch(e.request);
    }
    
    e.respondWith(
        caches.match(e.request).then((response) => {
            return response || fetch(e.request);
        })
    );
});
