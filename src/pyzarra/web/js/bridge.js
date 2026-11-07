/*
 * bridge.js — puente con pywebview. UNICO archivo JS nuevo de la migracion.
 *
 * Se carga ANTES que el resto de scripts (el parche de localStorage debe
 * estar instalado antes de que app.js lea el autoguardado).
 *
 * En un navegador normal window.pywebview nunca aparece y la web
 * funciona exactamente igual que antes.
 *
 * Cuatro intercepciones, sin editar ningun archivo existente:
 *   1. <a download>.click()        -> dialogo nativo de Guardar (api.save_file)
 *   2. <input type=file>.click()   -> dialogo nativo de Abrir  (api.open_file)
 *   3. localStorage sketchwire.*   -> espejo en disco          (api.save_state)
 *   4. imagenes soltadas en el Dock -> `drop` simulado sobre el lienzo
 *                                     (api.imagenes_pendientes)
 */
(function () {
  "use strict";

  var ready = false;
  var pendingWrites = {}; // escrituras de localStorage antes de pywebviewready
  // Claves restauradas desde Python y protegidas mientras dura la recarga:
  // app.js sigue vivo con la escena vacía que fabricó al arrancar, y al morir
  // la página (`pagehide`) la guarda «ahora»; esa escritura no debe pisar ni
  // el almacén ni el disco (v4.13.1).
  var protegidasEnRecarga = null;

  /* ¿Arranca la web con el almacén local VACÍO de claves de la app? Se mira
     aquí, antes de que app.js corra: WKWebView bajo pywebview no persiste
     localStorage entre arranques (modo privado por defecto), así que lo normal
     es que llegue vacío y la copia de Python sea la única verdad. app.js, al no
     encontrar nada, crea una pestaña nueva y autoguarda una escena vacía antes
     de que el puente esté listo; sin esta marca, ese autoguardado pendiente
     pisaba en disco el dibujo real (v4.13.1). */
  var almacenVacioAlArrancar = true;
  try {
    for (var i = 0; i < window.localStorage.length; i++) {
      if (esClaveApp(window.localStorage.key(i))) { almacenVacioAlArrancar = false; break; }
    }
  } catch (e) { /* localStorage inaccesible: se trata como vacío */ }

  function api() {
    return window.pywebview && window.pywebview.api;
  }

  /* Aviso visible reutilizando la región de toasts de la app (#toast-region).
     Sin esto, un fallo al guardar o abrir solo dejaba un console.error que
     nadie ve en una ventana nativa: la exportación fallaba EN SILENCIO. */
  function avisar(texto) {
    try {
      var region = document.getElementById("toast-region");
      if (!region) return;
      var toast = document.createElement("div");
      toast.className = "toast";
      toast.textContent = texto;
      region.appendChild(toast);
      setTimeout(function () { toast.remove(); }, 4000);
    } catch (e) { /* el aviso nunca debe romper nada */ }
  }

  /* ---------- 1. Exportar: interceptar <a download> ---------- */

  // exporter.js revoca el objectURL justo despues del click, asi que
  // recordamos cada Blob aqui para poder leerlo sin pasar por la URL.
  var blobByUrl = {};
  var origCreateObjectURL = URL.createObjectURL.bind(URL);
  URL.createObjectURL = function (obj) {
    var url = origCreateObjectURL(obj);
    if (obj instanceof Blob) blobByUrl[url] = obj;
    return url;
  };
  var origRevokeObjectURL = URL.revokeObjectURL.bind(URL);
  URL.revokeObjectURL = function (url) {
    delete blobByUrl[url];
    return origRevokeObjectURL(url);
  };

  function blobToB64(blob) {
    return new Promise(function (resolve, reject) {
      var r = new FileReader();
      r.onload = function () { resolve(String(r.result).split(",")[1]); };
      r.onerror = reject;
      r.readAsDataURL(blob);
    });
  }

  var origAnchorClick = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () {
    var a = this;
    if (!api() || !a.hasAttribute("download")) {
      return origAnchorClick.call(a);
    }
    var name = a.getAttribute("download") || "archivo";
    var href = a.href;
    var p;
    if (href.indexOf("data:") === 0) {
      var coma = href.indexOf(",");
      var cabecera = href.slice(0, coma);
      var cuerpo = href.slice(coma + 1);
      p = Promise.resolve(
        cabecera.indexOf(";base64") !== -1
          ? cuerpo
          : btoa(unescape(encodeURIComponent(decodeURIComponent(cuerpo))))
      );
    } else if (blobByUrl[href]) {
      p = blobToB64(blobByUrl[href]);
    } else {
      return origAnchorClick.call(a);
    }
    p.then(function (b64) {
      return api().save_file(name, b64);
    }).catch(function (e) {
      console.error("[bridge] fallo al guardar:", e);
      avisar("⚠ No se pudo guardar el archivo");
    });
  };

  /* ---------- 2. Importar: interceptar <input type=file> ---------- */

  var origInputClick = HTMLInputElement.prototype.click;
  HTMLInputElement.prototype.click = function () {
    var input = this;
    if (!api() || input.type !== "file") {
      return origInputClick.call(input);
    }
    var exts = (input.accept || "")
      .split(",")
      .map(function (s) { return s.trim(); })
      .filter(function (s) { return s.charAt(0) === "."; });
    api().open_file(exts.length ? exts : null).then(function (res) {
      var dt = new DataTransfer();
      if (res) dt.items.add(new File([res.content], res.name));
      try {
        input.files = dt.files;
      } catch (e) { /* algunos WebKit lo hacen de solo lectura */ }
      var ev = new Event("change", { bubbles: true });
      if (!input.files || !input.files.length) {
        // sin asignacion posible, pasamos el File en el propio evento
        Object.defineProperty(ev, "target", { value: { files: dt.files } });
      }
      input.dispatchEvent(ev);
    }).catch(function (e) {
      console.error("[bridge] fallo al abrir:", e);
      avisar("⚠ No se pudo abrir el archivo");
    });
  };

  /* ---------- 3. Persistencia: espejar localStorage en disco ---------- */

  function esClaveApp(k) {
    return typeof k === "string" && k.indexOf("sketchwire.") === 0;
  }

  var origSetItem = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) {
    if (this === window.localStorage && esClaveApp(k)) {
      if (protegidasEnRecarga && protegidasEnRecarga[k]) return;
      if (ready && api()) {
        api().save_state(k, String(v));
      } else {
        pendingWrites[k] = String(v);
      }
    }
    return origSetItem.call(this, k, v);
  };

  var origRemoveItem = Storage.prototype.removeItem;
  Storage.prototype.removeItem = function (k) {
    if (this === window.localStorage && esClaveApp(k)) {
      if (protegidasEnRecarga && protegidasEnRecarga[k]) return;
      delete pendingWrites[k];
      if (ready && api()) api().delete_state(k);
    }
    return origRemoveItem.call(this, k);
  };

  /* ---------- 4. Imagenes soltadas sobre el icono del Dock ---------- */

  // Python encola las imagenes (abrir_archivos.py) y la web las recoge. Hasta
  // que el puente decide si recarga, recoger seria insertarlas en una pagina
  // que va a morir: la imagen se perderia con la recarga.
  var listoParaImagenes = false;

  // Centro de la parte VISIBLE del lienzo, en coordenadas de ventana: es
  // donde caeria la imagen si se soltara a mano en mitad de la pantalla.
  function centroVisible(canvas) {
    var r = canvas.getBoundingClientRect();
    var caja = canvas.parentElement ? canvas.parentElement.getBoundingClientRect() : r;
    var izq = Math.max(r.left, caja.left), der = Math.min(r.right, caja.right);
    var arr = Math.max(r.top, caja.top), aba = Math.min(r.bottom, caja.bottom);
    if (der <= izq || aba <= arr) { izq = r.left; der = r.right; arr = r.top; aba = r.bottom; }
    return { x: (izq + der) / 2, y: (arr + aba) / 2 };
  }

  function aFile(img) {
    var bin = atob(img.data_b64);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new File([bytes], img.name, { type: img.mime });
  }

  // Se reutiliza el drop de archivos de app.js sobre #main-canvas (filtra
  // PNG/JPEG, inserta, escala, cascada si son varias, deja seleccionada y
  // apila Deshacer): un `drop` simulado con los archivos de Python.
  function soltarEnLienzo(lista) {
    var canvas = document.getElementById("main-canvas");
    if (!canvas) return 0;
    var dt = new DataTransfer();
    lista.forEach(function (img) { dt.items.add(aFile(img)); });
    var c = centroVisible(canvas);
    var init = { bubbles: true, cancelable: true, dataTransfer: dt, clientX: c.x, clientY: c.y };
    var ev = null;
    try { ev = new DragEvent("drop", init); } catch (e) { ev = null; }
    if (!ev || !ev.dataTransfer || !ev.dataTransfer.files ||
        ev.dataTransfer.files.length !== lista.length) {
      // Motor que no admite dataTransfer en un DragEvent sintetico: el
      // handler solo lee dataTransfer.files, clientX/Y y preventDefault.
      ev = new Event("drop", { bubbles: true, cancelable: true });
      Object.defineProperty(ev, "dataTransfer", { value: dt });
      Object.defineProperty(ev, "clientX", { value: c.x });
      Object.defineProperty(ev, "clientY", { value: c.y });
    }
    canvas.dispatchEvent(ev);
    return lista.length;
  }

  // Python la llama al soltar con la app abierta; el puente, al estar listo.
  window.__pyzarraImagenes = function () {
    if (!listoParaImagenes || !api() || !api().imagenes_pendientes) {
      return Promise.resolve(0);
    }
    return api().imagenes_pendientes().then(function (lista) {
      return lista && lista.length ? soltarEnLienzo(lista) : 0;
    }).catch(function (e) {
      console.error("[bridge] fallo al abrir imagenes:", e);
      avisar("⚠ No se pudo abrir la imagen");
      return 0;
    });
  };

  function abrirImagenesPendientes() {
    listoParaImagenes = true;
    window.__pyzarraImagenes();
  }

  window.addEventListener("pywebviewready", function () {
    ready = true;
    api().load_state().then(function (estado) {
      estado = estado || {};
      // Si localStorage llegó vacío pero Python tiene datos, la copia de
      // Python es la verdad: se restaura CADA clave que Python tenga —aunque
      // app.js ya la haya reescrito mientras el puente no estaba listo— y se
      // recarga UNA vez. La escritura pendiente de esas claves se descarta:
      // es la escena vacía que app.js fabricó al no encontrar nada, y
      // volcarla a disco destruía el dibujo guardado. Si el almacén traía
      // datos al arrancar, manda el almacén y lo pendiente se vuelca.
      var restaurado = false;
      var claveTestigo = null; // una clave restaurada, para verificar despues
      var restauradas = {};
      Object.keys(estado).forEach(function (k) {
        if (!esClaveApp(k)) return;
        var faltaba = window.localStorage.getItem(k) === null;
        if (faltaba || (almacenVacioAlArrancar && k in pendingWrites)) {
          origSetItem.call(window.localStorage, k, estado[k]);
          delete pendingWrites[k];
          restaurado = true;
          restauradas[k] = true;
          claveTestigo = k;
        }
      });
      // Volcar escrituras que ocurrieron antes de estar listos (las claves
      // que Python no tenía)
      Object.keys(pendingWrites).forEach(function (k) {
        api().save_state(k, pendingWrites[k]);
      });
      pendingWrites = {};
      // Guarda anti-bucle en DOS capas, porque window.__bridgeReloaded muere
      // con la propia recarga que protege:
      //   1. La escritura tiene que haberse QUEDADO en localStorage: si el
      //      almacen descarta escrituras (privado/roto), recargar volveria a
      //      encontrarlo vacio y a recargar, en bucle, para siempre.
      //   2. Una marca en sessionStorage, que si sobrevive a la recarga.
      var seAplico = false;
      try {
        seAplico = restaurado &&
          window.localStorage.getItem(claveTestigo) === estado[claveTestigo];
      } catch (e) { /* localStorage inaccesible: no recargar */ }
      // Hasta DOS recargas (v4.15.2): si el almacén no conservó la primera
      // restauración (file:// en WKWebView puede descartarla), se reintenta
      // una vez más antes de rendirse; más allá sería el bucle de siempre.
      var recargas = 0;
      try { recargas = Number(window.sessionStorage.getItem("bridge.reloaded")) || 0; }
      catch (e) { /* sessionStorage inaccesible: cuenta como recargado */ recargas = 99; }
      var yaRecargado = recargas >= 2;
      if (seAplico && !yaRecargado) {
        try { window.sessionStorage.setItem("bridge.reloaded", String(recargas + 1)); } catch (e) { }
        // Desde aquí hasta que la página muera, lo que app.js escriba en las
        // claves restauradas es su estado de arranque vacío: se ignora.
        protegidasEnRecarga = restauradas;
        window.location.reload();
        return; // las imagenes esperan en Python a la pagina recargada
      }
      abrirImagenesPendientes();
    }).catch(function (e) {
      console.error("[bridge] fallo al cargar estado:", e);
      abrirImagenesPendientes();
    });
  });
})();
