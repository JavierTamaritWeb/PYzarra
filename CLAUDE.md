# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos

```bash
uv sync                                  # instalar (crea .venv; no hace falta activarlo)
uv run pyzarra                           # ejecutar la app (ventana nativa pywebview)
uv run pytest                            # todos los tests
uv run pytest tests/test_api.py -v       # un archivo
uv run pytest -k "corrupto"              # un test por nombre
uv run ruff check src tests              # lint
./build-mac.sh                           # empaquetar dist/Pyzarra.app (limpia, compila, firma ad-hoc)
```

## Qué es esto

App de escritorio: **pywebview** abre una ventana nativa que carga `src/pyzarra/web/index.html` por `file://`. En macOS el motor es **WKWebView**. Tres piezas Python:

- `main.py` — crea la ventana. Empaquetada, la web vive en `sys._MEIPASS/pyzarra/web`; esa ruta debe coincidir con `datas=` de `Pyzarra.spec`. En macOS el menú se instala con un workaround (ver abajo).
- `api.py` — el puente JS→Python (`window.pywebview.api.*`). Solo métodos públicos se exponen; argumentos y retornos JSON-serializables. Persistencia en disco por clave (`~/Library/Application Support/Pyzarra/<clave>.json`), con escritura atómica (`.tmp` + rename) y carga tolerante a archivos corruptos.
- `menu.py` — barra de menús nativa que dispara botones de la web por su id (`document.getElementById(...).click()`). La lógica sigue en JS. En macOS `set_app_menu` de pywebview no funciona (pierde el menú y los targets): se reinstala con AppKit tras `window.events.shown`, guardando referencias fuertes y con auto-validación desactivada. Los ids de `MENU_LAYOUT` están pineados por tests contra `index.html`.

## La web es un BUILD, no se edita a mano (salvo dos excepciones)

`src/pyzarra/web/` es el `dist/` minificado del proyecto fuente
**`/Users/imac_mini_javi/Documents/WEB/FRONTEND_TOOLS/pizarra`** (JS sin minificar en `src/js/`, SCSS en `src/scss/`, tests node + e2e Playwright propios). Flujo para cualquier cambio de la web:

1. Editar en `pizarra` (`src/js/`, `src/scss/`) y pasar sus suites: `npm test` y `npx playwright test`.
2. `npm run build` (gulp) regenera `css/styles.css` y `dist/`.
3. Copiar `dist/js/*.js` y `dist/css/styles.css` aquí, y re-aplicar el único rebranding: `pizarra-biblioteca.json` → `pyzarra-biblioteca.json` en `js/app.js`.
4. **Traer al `index.html` propio cualquier cambio de markup** de pizarra (filas del panel, modales, Ayuda, badge). Comprobarlo con el diff normalizado; lo único que debe quedar es el logo «Py/Pi», las rutas `img/`, `bridge.js` y el manifest:
   ```bash
   norm() { sed -E 's/\?v=[0-9.]+//g; s/v[0-9]+\.[0-9]+\.[0-9]+/vX/g' "$1"; }
   diff <(norm ../pizarra/index.html) <(norm src/pyzarra/web/index.html) | grep -E "^[<>]" | grep -v "bridge.js\|manifest\|js/\|img/\|Pyzarra\|Pizarra"
   ```
   Si falta un id que `app.js` pide, `init()` revienta a mitad y los mandos cableados después dejan de funcionar sin ningún aviso (v4.15.1, «Limpiar todo»); `tests/test_web.py::TestIdsDelBuild` lo detecta.
5. `uv run pytest` valida la integración.

Las dos excepciones, propias de pyzarra (NO vienen del build):

- `web/index.html` — versión propia: carga `js/bridge.js` **primero** (orden load-bearing, pineado por tests) y no lleva `<link rel="manifest">` (WKWebView lo rechaza por CORS bajo `file://`).
- `web/js/bridge.js` — el ÚNICO JS añadido en la migración. Tres intercepciones sin tocar los archivos originales: `<a download>.click()` → diálogo nativo de Guardar; `<input type=file>.click()` → diálogo de Abrir; `localStorage` con claves `sketchwire.*` → espejo en disco vía `api.py`. Si localStorage llega vacío pero Python tiene datos, restaura y recarga UNA vez (guarda anti-bucle: verifica que la escritura se quedó + marca en `sessionStorage`). **Lo normal es que llegue vacío**: pywebview arranca WKWebView en modo privado y no persiste localStorage, así que la copia de Python es la única verdad. app.js, al no encontrar nada, crea una pestaña nueva y autoguarda una escena vacía ANTES de `pywebviewready`; esas escrituras pendientes de claves que Python ya tiene se DESCARTAN, y durante la recarga que sigue a la restauración se IGNORAN las escrituras de las claves restauradas — app.js, aún vivo con su escena vacía, la guarda «ahora» al oír `pagehide` (v4.13.1: por las dos vías el dibujo guardado se borraba en cada arranque). Guardado en `tests/test_bridge.py`, que ejecuta el bridge.js real bajo node (`tests/bridge_harness.js`). En un navegador normal no hace nada. Regla pineada por test: los JS originales no contienen la palabra `pywebview`.

## Trampas conocidas de WKWebView (la app real, no el navegador)

- Recorta descendientes `position:fixed` por el `overflow` de un ancestro (Chrome no). Fue la causa de las barras flotantes «escondidas detrás del canvas»: por eso una barra arrastrada se cuelga de `.app`, fuera de la columna con scroll.
- Rechaza peticiones (manifest, fetch) bajo `file://` por CORS («Origin null»).
- Probar solo en Chrome no basta: reproducir con el WebKit de Playwright cuando el bug sea «solo en la app».

## Empaquetado

`dist/Pyzarra.app` **queda obsoleto en silencio**: solo se actualiza al ejecutar `./build-mac.sh`. Tras empaquetar, verificar que el bundle lleva lo último:

```bash
cmp src/pyzarra/web/js/app.js dist/Pyzarra.app/Contents/Resources/pyzarra/web/js/app.js
```

En desarrollo `uv run pyzarra` usa `src/` directamente y siempre está al día.

## Convenciones

- Todo en castellano: comentarios, tests, mensajes de commit (ver `git log`).
- Versiones fijadas con `==` en `pyproject.toml` (hay test que lo exige); `uv.lock`, `.python-version` y la versión mínima de uv van a git.
- Rutas de la web siempre **relativas** (`css/...`, nunca `/css/...`): una absoluta rompe el `.app` (hay test).
