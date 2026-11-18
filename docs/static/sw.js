var CACHE = "plataforma-escolar-v1";
var BASICOS = ["/static/estilos.css", "/static/escudo.png", "/static/icono-192.png", "/sin-conexion"];

self.addEventListener("install", function (evento) {
  evento.waitUntil(caches.open(CACHE).then(function (cache) {
    return cache.addAll(BASICOS);
  }));
  self.skipWaiting();
});

self.addEventListener("activate", function (evento) {
  evento.waitUntil(caches.keys().then(function (nombres) {
    var borrar = [];
    for (var i = 0; i < nombres.length; i++) {
      if (nombres[i] !== CACHE) {
        borrar.push(caches.delete(nombres[i]));
      }
    }
    return Promise.all(borrar);
  }));
  self.clients.claim();
});

self.addEventListener("fetch", function (evento) {
  var pedido = evento.request;
  if (pedido.method !== "GET") {
    return;
  }
  if (pedido.mode === "navigate") {
    evento.respondWith(fetch(pedido).catch(function () {
      return caches.match("/sin-conexion");
    }));
    return;
  }
  if (pedido.url.indexOf("/static/") !== -1) {
    evento.respondWith(caches.match(pedido).then(function (guardado) {
      if (guardado) {
        return guardado;
      }
      return fetch(pedido);
    }));
  }
});
