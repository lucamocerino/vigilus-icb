const CACHE_NAME = 'sentinella-v2'
const TILE_CACHE = 'sentinella-tiles-v1'
const MAX_TILES = 500

const PRECACHE = ['/', '/index.html']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME && k !== TILE_CACHE).map(k => caches.delete(k)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)

  // Don't intercept cross-origin API requests
  if (url.origin !== self.location.origin) {
    if (url.hostname.includes('basemaps.cartocdn.com')) {
      // Cache-first for map tiles
      event.respondWith(
        caches.open(TILE_CACHE).then(async cache => {
          const cached = await cache.match(event.request)
          if (cached) return cached
          const response = await fetch(event.request)
          if (response.ok) {
            cache.put(event.request, response.clone())
            const keys = await cache.keys()
            if (keys.length > MAX_TILES) {
              await cache.delete(keys[0])
            }
          }
          return response
        }).catch(() => caches.match(event.request).then(r => r || Response.error()))
      )
    }
    return
  }

  // Network-first for API — always return a valid Response
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/ws/')) {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match(event.request).then(cached =>
          cached || new Response(JSON.stringify({ error: 'offline' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          })
        )
      )
    )
    return
  }

  // Cache-first for static assets
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  )
})
