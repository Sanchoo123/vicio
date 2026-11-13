/* Vício: recebe as notificações do robô (Web Push) e abre a app no sítio certo ao tocar.
   Não guarda nada em cache: a app vai sempre buscar a versão mais recente. */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('push', e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = {title: 'Vício', body: e.data ? e.data.text() : ''}; }
  e.waitUntil((async () => {
    await self.registration.showNotification(d.title || 'Vício', {
      body: d.body || '',
      icon: 'icons/icon-192.png',
      badge: 'icons/icon-192.png',
      data: {url: d.url || './'},
      tag: d.tag || undefined,
    });
    // número no ícone da app = avisos por ver
    try {
      const n = (await self.registration.getNotifications()).length;
      if (self.navigator.setAppBadge) await self.navigator.setAppBadge(n);
    } catch (_) {}
  })());
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || './', self.registration.scope).href;
  e.waitUntil((async () => {
    const inApp = url.startsWith(self.registration.scope);
    const wins = await self.clients.matchAll({type: 'window', includeUncontrolled: true});
    if (inApp && wins.length) {
      const w = wins[0];
      await w.focus();
      w.postMessage({open: url});
      return;
    }
    await self.clients.openWindow(url);
  })());
});
