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
     imagenes          como primer-arranque, con dos imágenes soltadas en el
                       Dock esperando en la cola de Python
     imagenes-con-recarga  como vacio-con-python (el puente recarga), con
                       imágenes en la cola: NO deben insertarse antes de recargar
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

const conImagenes = escenario.startsWith('imagenes');
const python = (escenario === 'primer-arranque' || escenario === 'imagenes') ? {}
  : { 'sketchwire.autosave': ESCENA_PYTHON, 'sketchwire.tabs': TABS_PYTHON, 'sketchwire.prefs': '{"a":1}' };
const localInicial = escenario === 'lleno'
  ? { 'sketchwire.autosave': ESCENA_VACIA, 'sketchwire.tabs': TABS_NUEVAS } : {};

const saves = [];
const listeners = {};

// Cola de imágenes de Python (abrir_archivos.vaciar): se entrega una vez.
let colaImagenes = conImagenes ? [
  { name: 'foto.png', mime: 'image/png', data_b64: Buffer.from('PNGDATOS').toString('base64') },
  { name: 'otra.jpg', mime: 'image/jpeg', data_b64: Buffer.from('JPG').toString('base64') },
] : [];
let llamadasPendientes = 0;

// DOM mínimo: el lienzo registra los `drop` que recibe.
const drops = [];
const mainCanvas = {
  getBoundingClientRect: () => ({ left: 100, top: 50, right: 1100, bottom: 750 }),
  parentElement: { getBoundingClientRect: () => ({ left: 0, top: 0, right: 800, bottom: 600 }) },
  dispatchEvent(ev) {
    drops.push({
      type: ev.type,
      files: ev.dataTransfer.files.map(f => ({ name: f.name, type: f.type, size: f.size })),
      clientX: ev.clientX, clientY: ev.clientY,
    });
    return true;
  },
};
function File(partes, name, opts) {
  this.name = name; this.type = (opts && opts.type) || '';
  this.size = partes.reduce((n, p) => n + p.length, 0);
}
function DataTransfer() {
  const files = [];
  this.files = files;
  this.items = { add: f => files.push(f) };
}
function DragEvent(type, init) { Object.assign(this, init); this.type = type; }

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
    imagenes_pendientes: () => {
      llamadasPendientes++;
      const lista = colaImagenes; colaImagenes = [];
      return Promise.resolve(lista);
    },
  } },
};
const ctx = {
  window, Storage, console,
  document: { getElementById: id => (id === 'main-canvas' ? mainCanvas : null), createElement: () => ({}) },
  URL: { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} },
  Blob: function () {}, FileReader: function () {}, DataTransfer, DragEvent,
  atob: b => Buffer.from(b, 'base64').toString('binary'),
  HTMLAnchorElement: { prototype: { click() {} } },
  HTMLInputElement: { prototype: { click() {} } },
  Promise, setTimeout, Event: function () {}, File,
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

// Python avisa (imagen soltada con la app abierta) ANTES de que el puente
// esté listo: no debe recoger nada todavía.
const avisoTemprano = window.__pyzarraImagenes();

(listeners.pywebviewready || []).forEach(fn => fn());
setTimeout(() => {
  // Si el puente pidió recargar, app.js (aún vivo, con su escena vacía en
  // memoria) oye `pagehide` y guarda «ahora» el autosave: es lo que borraba
  // el dibujo en disco en cada arranque real.
  if (window.location.reloads) {
    window.localStorage.setItem('sketchwire.autosave', ESCENA_VACIA);
  }
}, 5);
setTimeout(() => {
  process.stdout.write(JSON.stringify({
    saves,
    local: window.localStorage._dump(),
    reloads: window.location.reloads,
    drops,
    llamadasPendientes,
    quedanEnCola: colaImagenes.length,
    avisoTempranoEsPromesa: typeof (avisoTemprano && avisoTemprano.then) === 'function',
  }));
}, 20);
