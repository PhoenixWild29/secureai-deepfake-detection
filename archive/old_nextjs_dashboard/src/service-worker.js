/**
 * Service Worker for Offline Capabilities and Caching
 * Implements comprehensive caching strategies for assets and API responses
 */

// Service Worker version
const SW_VERSION = '1.0.0';
const CACHE_NAME = `secureai-dashboard-${SW_VERSION}`;

// Cache strategies
const CACHE_STRATEGIES = {
  CACHE_FIRST: 'cache-first',
  NETWORK_FIRST: 'network-first',
  STALE_WHILE_REVALIDATE: 'stale-while-revalidate',
  NETWORK_ONLY: 'network-only',
  CACHE_ONLY: 'cache-only',
};

// Cache configuration
const CACHE_CONFIG = {
  // Static assets cache
  STATIC_CACHE: {
    name: `${CACHE_NAME}-static`,
    maxEntries: 100,
    maxAgeSeconds: 30 * 24 * 60 * 60, // 30 days
  },
  
  // API responses cache
  API_CACHE: {
    name: `${CACHE_NAME}-api`,
    maxEntries: 200,
    maxAgeSeconds: 5 * 60, // 5 minutes
  },
  
  // Images cache
  IMAGES_CACHE: {
    name: `${CACHE_NAME}-images`,
    maxEntries: 50,
    maxAgeSeconds: 7 * 24 * 60 * 60, // 7 days
  },
  
  // Fonts cache
  FONTS_CACHE: {
    name: `${CACHE_NAME}-fonts`,
    maxEntries: 20,
    maxAgeSeconds: 365 * 24 * 60 * 60, // 1 year
  },
};

// Routes and their caching strategies
const ROUTE_STRATEGIES = {
  // Static assets
  '/_next/static/': CACHE_STRATEGIES.CACHE_FIRST,
  '/static/': CACHE_STRATEGIES.CACHE_FIRST,
  '/assets/': CACHE_STRATEGIES.CACHE_FIRST,
  
  // API routes
  '/api/': CACHE_STRATEGIES.NETWORK_FIRST,
  '/api/auth/': CACHE_STRATEGIES.NETWORK_ONLY,
  '/api/dashboard/': CACHE_STRATEGIES.STALE_WHILE_REVALIDATE,
  
  // Images
  '/images/': CACHE_STRATEGIES.CACHE_FIRST,
  '/img/': CACHE_STRATEGIES.CACHE_FIRST,
  
  // Fonts
  '/fonts/': CACHE_STRATEGIES.CACHE_FIRST,
  
  // Pages
  '/': CACHE_STRATEGIES.STALE_WHILE_REVALIDATE,
  '/dashboard/': CACHE_STRATEGIES.STALE_WHILE_REVALIDATE,
};

// Offline fallback pages
const OFFLINE_FALLBACKS = {
  '/': '/offline.html',
  '/dashboard/': '/offline-dashboard.html',
  '/api/': '/offline-api.json',
};

// Service Worker installation
self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  
  event.waitUntil(
    Promise.all([
      // Pre-cache essential assets
      caches.open(CACHE_CONFIG.STATIC_CACHE.name).then(cache => {
        return cache.addAll([
          '/',
          '/dashboard/',
          '/manifest.json',
          '/favicon.ico',
        ]);
      }),
      
      // Skip waiting to activate immediately
      self.skipWaiting(),
    ])
  );
});

// Service Worker activation
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  
  event.waitUntil(
    Promise.all([
      // Clean up old caches
      cleanupOldCaches(),
      
      // Take control of all clients
      self.clients.claim(),
    ])
  );
});

// Fetch event handler
self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip chrome-extension and other non-http requests
  if (!url.protocol.startsWith('http')) {
    return;
  }
  
  // Determine caching strategy based on URL
  const strategy = getCachingStrategy(url.pathname);
  
  event.respondWith(
    handleRequest(request, strategy)
  );
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('Background sync triggered:', event.tag);
  
  if (event.tag === 'dashboard-sync') {
    event.waitUntil(syncDashboardData());
  }
  
  if (event.tag === 'api-sync') {
    event.waitUntil(syncApiRequests());
  }
});

// Push notifications
self.addEventListener('push', (event) => {
  console.log('Push notification received');
  
  if (event.data) {
    const data = event.data.json();
    
    event.waitUntil(
      self.registration.showNotification(data.title, {
        body: data.body,
        icon: data.icon || '/icon-192x192.png',
        badge: data.badge || '/badge-72x72.png',
        tag: data.tag,
        data: data.data,
        actions: data.actions,
        requireInteraction: data.requireInteraction,
        silent: data.silent,
      })
    );
  }
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked');
  
  event.notification.close();
  
  if (event.action) {
    // Handle specific action
    handleNotificationAction(event.action, event.notification.data);
  } else {
    // Default click behavior
    event.waitUntil(
      clients.openWindow(event.notification.data?.url || '/')
    );
  }
});

// Handle requests based on caching strategy
async function handleRequest(request, strategy) {
  const url = new URL(request.url);
  
  try {
    switch (strategy) {
      case CACHE_STRATEGIES.CACHE_FIRST:
        return await cacheFirst(request);
      
      case CACHE_STRATEGIES.NETWORK_FIRST:
        return await networkFirst(request);
      
      case CACHE_STRATEGIES.STALE_WHILE_REVALIDATE:
        return await staleWhileRevalidate(request);
      
      case CACHE_STRATEGIES.NETWORK_ONLY:
        return await networkOnly(request);
      
      case CACHE_STRATEGIES.CACHE_ONLY:
        return await cacheOnly(request);
      
      default:
        return await networkFirst(request);
    }
  } catch (error) {
    console.error('Request handling failed:', error);
    
    // Return offline fallback if available
    const fallback = getOfflineFallback(url.pathname);
    if (fallback) {
      return await caches.match(fallback);
    }
    
    // Return generic offline page
    return await caches.match('/offline.html');
  }
}

// Cache first strategy
async function cacheFirst(request) {
  const cache = await getCache(request);
  const cachedResponse = await cache.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    throw error;
  }
}

// Network first strategy
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await getCache(request);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cache = await getCache(request);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    throw error;
  }
}

// Stale while revalidate strategy
async function staleWhileRevalidate(request) {
  const cache = await getCache(request);
  const cachedResponse = await cache.match(request);
  
  // Fetch from network in background
  const networkPromise = fetch(request).then(response => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => {
    // Ignore network errors for background updates
  });
  
  // Return cached response immediately if available
  if (cachedResponse) {
    return cachedResponse;
  }
  
  // Wait for network response if no cache
  return await networkPromise;
}

// Network only strategy
async function networkOnly(request) {
  return await fetch(request);
}

// Cache only strategy
async function cacheOnly(request) {
  const cache = await getCache(request);
  const cachedResponse = await cache.match(request);
  
  if (!cachedResponse) {
    throw new Error('No cached response available');
  }
  
  return cachedResponse;
}

// Get appropriate cache for request
async function getCache(request) {
  const url = new URL(request.url);
  
  if (url.pathname.includes('/_next/static/') || url.pathname.includes('/static/')) {
    return await caches.open(CACHE_CONFIG.STATIC_CACHE.name);
  }
  
  if (url.pathname.includes('/api/')) {
    return await caches.open(CACHE_CONFIG.API_CACHE.name);
  }
  
  if (url.pathname.match(/\.(jpg|jpeg|png|gif|webp|svg)$/)) {
    return await caches.open(CACHE_CONFIG.IMAGES_CACHE.name);
  }
  
  if (url.pathname.match(/\.(woff|woff2|ttf|eot)$/)) {
    return await caches.open(CACHE_CONFIG.FONTS_CACHE.name);
  }
  
  return await caches.open(CACHE_CONFIG.STATIC_CACHE.name);
}

// Determine caching strategy for URL
function getCachingStrategy(pathname) {
  for (const [pattern, strategy] of Object.entries(ROUTE_STRATEGIES)) {
    if (pathname.startsWith(pattern)) {
      return strategy;
    }
  }
  
  return CACHE_STRATEGIES.NETWORK_FIRST;
}

// Get offline fallback for URL
function getOfflineFallback(pathname) {
  for (const [pattern, fallback] of Object.entries(OFFLINE_FALLBACKS)) {
    if (pathname.startsWith(pattern)) {
      return fallback;
    }
  }
  
  return null;
}

// Clean up old caches
async function cleanupOldCaches() {
  const cacheNames = await caches.keys();
  const currentCaches = Object.values(CACHE_CONFIG).map(config => config.name);
  
  const deletePromises = cacheNames
    .filter(cacheName => !currentCaches.includes(cacheName))
    .map(cacheName => caches.delete(cacheName));
  
  await Promise.all(deletePromises);
}

// Sync dashboard data
async function syncDashboardData() {
  try {
    // Get pending dashboard updates from IndexedDB
    const pendingUpdates = await getPendingUpdates();
    
    for (const update of pendingUpdates) {
      try {
        await fetch(update.url, {
          method: update.method,
          headers: update.headers,
          body: update.body,
        });
        
        // Remove from pending updates
        await removePendingUpdate(update.id);
      } catch (error) {
        console.error('Failed to sync dashboard update:', error);
      }
    }
  } catch (error) {
    console.error('Dashboard sync failed:', error);
  }
}

// Sync API requests
async function syncApiRequests() {
  try {
    // Get pending API requests from IndexedDB
    const pendingRequests = await getPendingApiRequests();
    
    for (const request of pendingRequests) {
      try {
        await fetch(request.url, {
          method: request.method,
          headers: request.headers,
          body: request.body,
        });
        
        // Remove from pending requests
        await removePendingApiRequest(request.id);
      } catch (error) {
        console.error('Failed to sync API request:', error);
      }
    }
  } catch (error) {
    console.error('API sync failed:', error);
  }
}

// Handle notification actions
function handleNotificationAction(action, data) {
  switch (action) {
    case 'view':
      clients.openWindow(data.url || '/');
      break;
    case 'dismiss':
      // Notification already closed
      break;
    default:
      clients.openWindow('/');
  }
}

// IndexedDB helpers (simplified)
async function getPendingUpdates() {
  // Implementation would depend on your IndexedDB setup
  return [];
}

async function removePendingUpdate(id) {
  // Implementation would depend on your IndexedDB setup
}

async function getPendingApiRequests() {
  // Implementation would depend on your IndexedDB setup
  return [];
}

async function removePendingApiRequest(id) {
  // Implementation would depend on your IndexedDB setup
}

// Message handling for communication with main thread
self.addEventListener('message', (event) => {
  const { type, data } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
    
    case 'CACHE_URLS':
      cacheUrls(data.urls);
      break;
    
    case 'CLEAR_CACHE':
      clearCache(data.cacheName);
      break;
    
    case 'GET_CACHE_STATS':
      getCacheStats().then(stats => {
        event.ports[0].postMessage(stats);
      });
      break;
  }
});

// Cache URLs
async function cacheUrls(urls) {
  const cache = await caches.open(CACHE_CONFIG.STATIC_CACHE.name);
  await cache.addAll(urls);
}

// Clear cache
async function clearCache(cacheName) {
  if (cacheName) {
    await caches.delete(cacheName);
  } else {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map(name => caches.delete(name)));
  }
}

// Get cache statistics
async function getCacheStats() {
  const cacheNames = await caches.keys();
  const stats = {};
  
  for (const cacheName of cacheNames) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    stats[cacheName] = {
      size: keys.length,
      urls: keys.map(request => request.url),
    };
  }
  
  return stats;
}

console.log('Service Worker loaded successfully');
