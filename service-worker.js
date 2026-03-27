const CACHE_NAME = 'worklog-pwa-v2';

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/js/app.js',
  '/js/config.js',
  '/pages/home.html',
  '/pages/login.html',
  '/pages/register.html',
  '/pages/list.html',
  '/pages/detail.html',
  '/pages/edit.html',
  '/pages/sync.html',
  '/pages/mypage.html',
  '/pages/admin/users.html',
  '/pages/admin/dashboard.html',
  '/assets/icon-192.png',
  '/assets/icon-512.png',
];

// Install: cache static assets (個別失敗を無視してinstallを完了させる)
self.addEventListener('install', (event) => {
  console.log('[SW] install start');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // addAll は1つでも失敗するとinstall失敗になるため、個別にfetchしてエラーを無視
      const promises = STATIC_ASSETS.map((url) =>
        fetch(url)
          .then((res) => {
            if (res.ok) {
              return cache.put(url, res);
            }
            console.warn('[SW] cache skip (not ok):', url, res.status);
          })
          .catch((err) => {
            console.warn('[SW] cache skip (fetch error):', url, err.message);
          })
      );
      return Promise.all(promises);
    }).then(() => {
      console.log('[SW] install done, skipWaiting');
      return self.skipWaiting();
    })
  );
});

// Activate: delete old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] activate');
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => {
            console.log('[SW] delete old cache:', key);
            return caches.delete(key);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: cache-first strategy (skip API requests)
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // APIリクエストはキャッシュしない
  if (url.pathname.includes('/api/') || url.pathname.endsWith('.cgi')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(event.request).then((response) => {
        if (event.request.method === 'GET' && response.status === 200) {
          const cloned = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, cloned);
          });
        }
        return response;
      }).catch(() => {
        // オフライン時: キャッシュにない場合は何もしない
        return new Response('offline', { status: 503, statusText: 'Service Unavailable' });
      });
    })
  );
});
