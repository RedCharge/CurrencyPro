const CACHE_NAME = "currency-app-cache-v2";
const urlsToCache = [
  "/", 
  "/dashboard", 
  "/settings", 
  "/about",
  "/static/icon.png"   // add your app icon for notifications
];

// Install event → pre-cache essential routes
self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(urlsToCache);
    })
  );
  self.skipWaiting();
});

// Activate event → clear old caches
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch event → serve cached content or fetch and update
self.addEventListener("fetch", e => {
  const req = e.request;

  // Handle API calls (exchange rate, currencyfreaks, news)
  if (
    req.url.includes("exchangerate-api.com") ||
    req.url.includes("currencyfreaks.com") ||
    req.url.includes("newsapi.org")
  ) {
    e.respondWith(
      caches.open(CACHE_NAME).then(cache => {
        return fetch(req)
          .then(response => {
            cache.put(req, response.clone()); // update cache
            return response;
          })
          .catch(() => caches.match(req)); // fallback to cache if offline
      })
    );
    return;
  }

  // Default strategy: cache first, then network
  e.respondWith(
    caches.match(req).then(resp => {
      return resp || fetch(req);
    })
  );
});

// --- OPTIONAL: Listen for messages from app (to show notifications) ---
self.addEventListener("message", e => {
  if (e.data && e.data.type === "SHOW_NOTIFICATION") {
    self.registration.showNotification(e.data.title, {
      body: e.data.body,
      icon: "/static/icon.png"
    });
  }
});
