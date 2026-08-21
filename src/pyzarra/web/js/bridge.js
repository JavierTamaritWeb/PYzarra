/*
 * bridge.js — puente con pywebview. UNICO archivo JS nuevo de la migracion.
 *
 * Se carga ANTES que el resto de scripts (el parche de localStorage debe
 * estar instalado antes de que app.js lea el autoguardado).
 *
 * En un navegador normal window.pywebview nunca aparece y la web
 * funciona exactamente igual que antes.
 *
 * Tres intercepciones, sin editar ningun archivo existente:
 *   1. <a download>.click()        -> dialogo nativo de Guardar (api.save_file)
 *   2. <input type=file>.click()   -> dialogo nativo de Abrir  (api.open_file)
 *   3. localStorage sketchwire.*   -> espejo en disco          (api.save_state)
 */
(function () {
  "use strict";

  var ready = false;
  var pendingWrites = {}; // escrituras de localStorage antes de pywebviewready

  function api() {
    return window.pywebview && window.pywebview.api;
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
    });
  };

  /* ---------- 3. Persistencia: espejar localStorage en disco ---------- */

  function esClaveApp(k) {
    return typeof k === "string" && k.indexOf("sketchwire.") === 0;
  }

  var origSetItem = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) {
    if (this === window.localStorage && esClaveApp(k)) {
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
      delete pendingWrites[k];
      if (ready && api()) api().delete_state(k);
    }
    return origRemoveItem.call(this, k);
  };

  window.addEventListener("pywebviewready", function () {
    ready = true;
    api().load_state().then(function (estado) {
      estado = estado || {};
      // Si localStorage se borro (fragil bajo file://) pero Python tiene
      // datos, restauramos y recargamos UNA vez.
      var restaurado = false;
      Object.keys(estado).forEach(function (k) {
        if (esClaveApp(k) && window.localStorage.getItem(k) === null && !(k in pendingWrites)) {
          origSetItem.call(window.localStorage, k, estado[k]);
          restaurado = true;
        }
      });
      // Volcar escrituras que ocurrieron antes de estar listos
      Object.keys(pendingWrites).forEach(function (k) {
        api().save_state(k, pendingWrites[k]);
      });
      pendingWrites = {};
      if (restaurado && !window.__bridgeReloaded) {
        window.__bridgeReloaded = true;
        window.location.reload();
      }
    }).catch(function (e) {
      console.error("[bridge] fallo al cargar estado:", e);
    });
  });
})();
