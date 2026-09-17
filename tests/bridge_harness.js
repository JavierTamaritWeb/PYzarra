'use strict';
/* Arnés mínimo para ejecutar bridge.js fuera de WKWebView y reproducir la
   carrera del arranque (v4.13.1): app.js escribe en localStorage ANTES de
   `pywebviewready`, y el puente decide qué gana, si el almacén o Python.

   Uso: node bridge_harness.js <ruta bridge.js> <escenario>
   Escenarios:
     vacio-con-python  almacén vacío al arrancar, app.js autoguarda una
                       escena vacía y Python tiene el dibujo → Python gana
     lleno             el almacén ya traía datos → el almacén gana
     primer-arranque   almacén y Python vacíos → lo pendiente va a disco
   Escribe en stdout un JSON con lo observado. */
const fs = require('fs');
const vm = require('vm');

const [bridgePath, escenario] = process.argv.slice(2);

function makeStorage(inicial) {
  const data = new Map(Object.entries(inicial || {}));
  const st = {
    getItem: k => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => { data.set(k, String(v)); },
    removeItem: k => { data.delete(k); },
    key: i => Array.from(data.keys())[i] ?? null,
    get length() { return data.size; },
    _dump: () => Object.fromEntries(data),
  };
  return st;
}

function Storage() {}
Storage.prototype.setItem = function (k, v) { return this._raw.setItem(k, v); };
Storage.prototype.removeItem = function (k) { return this._raw.removeItem(k); };
function wrap(raw) {
  const s = Object.create(Storage.prototype);
  s._raw = raw;
  s.getItem = raw.getItem; s.key = raw.key; s._dump = raw._dump;
  Object.defineProperty(s, 'length', { get: () => raw.length });
  return s;
}

const ESCENA_PYTHON = JSON.stringify({ elements: [{ type: 'rect', x: 1, y: 2, w: 3, h: 4 }], settings: {} });
const ESCENA_VACIA = JSON.stringify({ elements: [], settings: {} });
const TABS_PYTHON = JSON.stringify({ v: 1, active: 'viejo', order: [{ id: 'viejo', label: '' }] });
const TABS_NUEVAS = JSON.stringify({ v: 1, active: 'nuevo', order: [{ id: 'nuevo', label: '' }] });

const python = escenario === 'primer-arranque' ? {}
  : { 'sketchwire.autosave': ESCENA_PYTHON, 'sketchwire.tabs': TABS_PYTHON, 'sketchwire.prefs': '{"a":1}' };
const localInicial = escenario === 'lleno'
  ? { 'sketchwire.autosave': ESCENA_VACIA, 'sketchwire.tabs': TABS_NUEVAS } : {};

const saves = [];
const listeners = {};
const window = {
  localStorage: wrap(makeStorage(localInicial)),
  sessionStorage: wrap(makeStorage({})),
  addEventListener: (ev, fn) => { (listeners[ev] = listeners[ev] || []).push(fn); },
  location: { reloads: 0, reload() { this.reloads++; } },
  pywebview: { api: {
    load_state: () => Promise.resolve({ ...python }),
    save_state: (k, v) => { saves.push([k, v]); return Promise.resolve(); },
    delete_state: () => Promise.resolve(),
    save_file: () => Promise.resolve(), open_file: () => Promise.resolve(null),
  } },
};
const ctx = {
  window, Storage, console,
  document: { getElementById: () => null, createElement: () => ({}) },
  URL: { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} },
  Blob: function () {}, FileReader: function () {}, DataTransfer: function () {},
  HTMLAnchorElement: { prototype: { click() {} } },
  HTMLInputElement: { prototype: { click() {} } },
  Promise, setTimeout, Event: function () {}, File: function () {},
  btoa: s => s, unescape: s => s, encodeURIComponent: s => s, decodeURIComponent: s => s,
};
ctx.globalThis = ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(bridgePath, 'utf8'), ctx, { filename: 'bridge.js' });

// Lo que hace app.js al arrancar sin datos: pestaña nueva y autosave vacío,
// ANTES de que pywebview esté listo.
if (escenario !== 'lleno') {
  window.localStorage.setItem('sketchwire.tabs', TABS_NUEVAS);
  window.localStorage.setItem('sketchwire.autosave', ESCENA_VACIA);
}
// Una clave que Python no tiene: siempre debe llegar a disco.
window.localStorage.setItem('sketchwire.library', '[]');

(listeners.pywebviewready || []).forEach(fn => fn());
setTimeout(() => {
  process.stdout.write(JSON.stringify({
    saves,
    local: window.localStorage._dump(),
    reloads: window.location.reloads,
  }));
}, 20);
