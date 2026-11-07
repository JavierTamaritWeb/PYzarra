# BUGS.md — Registro de errores corregidos en Pyzarra

Errores propios de la app de escritorio (no de la web, que tiene su propio
[BUGS.md en pizarra](https://github.com/JavierTamaritWeb/pizarra/blob/main/BUGS.md)).
Cada entrada: síntoma, causa, arreglo y la **guardia** que falla si vuelve.

### v4.17.2 — El diálogo de Guardar salía en inglés

- **Síntoma:** al exportar, el diálogo nativo decía «Save file», «Save As»,
  «Where», «Cancel» y «Save», aunque toda la app está en castellano.
- **Causa:** dos fuentes distintas. El título es un texto de pywebview
  (`global.saveFile`), que trae sus textos en inglés si no se le pasa
  `localization`. El resto lo pinta macOS según las localizaciones del
  bundle: el `.app` no declaraba ninguna (ni `CFBundleDevelopmentRegion` ni
  carpeta `.lproj`), así que AppKit caía al inglés.
- **Arreglo:** `main.py` pasa `localization=LOCALIZACION` (todas las claves de
  pywebview en español) en las dos ramas de `webview.start`; `Pyzarra.spec`
  declara `CFBundleDevelopmentRegion: "es"`, `CFBundleLocalizations: ["es"]` y
  mete `assets/es.lproj/` en `Contents/Resources`. Solo afecta al `.app`: con
  `uv run pyzarra` los botones dependen del bundle de Python.
- **Guardia:** `tests/test_web.py::TestEspanol` (ninguna clave de pywebview sin
  traducir, `localization` en las dos llamadas, región y `.lproj` en el spec).
  Comprobación del bundle: `NSBundle.bundleWithPath_("dist/Pyzarra.app")
  .preferredLocalizations()` debe dar `es`.
- **Para que no se repita:** cualquier texto nativo nuevo (diálogos, menús,
  alertas) sale de pywebview o de AppKit, no de la web: traducirlo en
  `LOCALIZACION` o comprobar que AppKit lo localiza con `es.lproj`.

### v4.17.2 — Exportar dos veces chocaba con «el archivo ya existe»

- **Síntoma:** el diálogo de Guardar proponía siempre «wireframe»; la segunda
  exportación en la misma carpeta pedía reemplazar el archivo anterior.
- **Causa:** `exporter.js` (pizarra) pone un nombre fijo, `wireframe.<ext>`, a
  toda exportación sin nombre propio, y `api.save_file` lo pasaba tal cual al
  diálogo, que además se abría donde macOS recordaba, sin que Python supiera
  qué archivos había allí.
- **Arreglo:** `api.save_file` cambia «wireframe» por el primer
  `exportadoN<ext>` libre (`nombre_libre`) en la carpeta donde abre el
  diálogo, que fija explícitamente: la última usada (guardada en
  `ultima-carpeta-exportar.txt`, no `.json`, para que `load_state` no la
  devuelva como clave) o el Escritorio. Los nombres propios se respetan.
- **Guardia:** `tests/test_api.py::TestNombreExportado` (empieza en 1, salta los
  existentes de la misma extensión, el diálogo se abre donde se contó, recuerda
  la carpeta, la carpeta no se cuela en el estado, vuelve al Escritorio si la
  recordada desaparece).
- **Para que no se repita:** el nombre se calcula en Python, no en la web
  (el JS es un build de pizarra); si se fija la carpeta del diálogo, contar
  SIEMPRE en esa misma carpeta.

### v4.17.1 — Una imagen pasada por argumento se insertaba dos veces

- **Síntoma:** `uv run pyzarra foto.png` metía la foto dos veces en el lienzo.
- **Causa:** en macOS, NSApplication ya entrega los argumentos de la línea de
  órdenes como archivos a abrir (`application:openFiles:`), y `main.py`
  además encolaba `sys.argv`.
- **Arreglo:** en macOS solo encola el delegado; `sys.argv` se encola solo en
  Windows y Linux.
- **Guardia:** `tests/test_web.py::TestCacheDeLaWeb::test_en_mac_los_argumentos_no_se_encolan_dos_veces`.

### v4.17.1 — Soltar imágenes en el Dock no hacía nada en el `.app`

- **Síntoma:** en la 4.17.0, arrastrar un PNG al icono de Pyzarra no
  insertaba nada. En desarrollo (`uv run pyzarra`) sí funcionaba.
- **Causa:** el `.app` ejecutaba un `bridge.js` **antiguo** de la caché de
  WebKit, sin `__pyzarraImagenes`. pywebview sirve la web desde
  `http://127.0.0.1:42001` (puerto fijo con `private_mode=False`); intenta
  mandar cabeceras anti-caché, pero `bottle.static_file` devuelve una
  respuesta nueva y se pierden, así que con el almacén persistente WebKit
  daba por buena la copia vieja por su `Last-Modified`. Afectaba a cualquier
  actualización de la web. macOS sí avisaba a la app y la imagen se encolaba:
  la web nunca la recogía.
- **Arreglo:** `main.py` vacía en cada arranque SOLO la caché HTTP de WebKit
  (disco, memoria, fetch) antes de cargar la página; `localStorage` no se
  toca. De paso: en macOS los argumentos ya no se encolan aparte (NSApplication
  los entrega como archivos a abrir y la imagen entraba dos veces).
- **Guardia:** `tests/test_web.py::TestCacheDeLaWeb` y la prueba real con
  `open -a dist/Pyzarra.app foto.png` (app abierta y cerrada). Diagnóstico
  rápido con la app abierta: `curl -sI http://127.0.0.1:42001/js/bridge.js`.

### v4.17.0 — (evitado) `evaluate_js` desde el hilo principal cuelga la app

- **Riesgo:** el delegado de Cocoa (`application:openFiles:`) corre en el
  hilo principal; `window.evaluate_js` de pywebview en Cocoa encola el trabajo
  en ese mismo hilo y espera bloqueado el resultado: llamarlo desde el
  delegado deja la app colgada para siempre.
- **Cómo se evita:** `abrir_archivos.avisar_a_la_web` lanza `evaluate_js` en un
  hilo aparte. Regla: nunca llamar a `evaluate_js` desde código que corre en el
  hilo principal (delegados, targets de menú de AppKit, `AppHelper.callAfter`).

### v4.15.2 — Arrancar la app seguía dejando el disco en blanco por otra vía

- **Síntoma:** al arrancar la 4.15.1 con un dibujo en disco, seis segundos
  después el autosave estaba vacío y las preferencias en las de fábrica.
- **Causa:** pywebview arranca WKWebView en **modo privado** (`private_mode`
  por defecto): `localStorage` no persiste entre arranques y, bajo `file://`,
  ni siquiera conservó la restauración a través de la recarga. Tras recargar,
  app.js volvía a arrancar sin nada, el puente ya no podía recargar (guarda
  anti-bucle) y el lienzo vacío acababa espejado en disco en cuanto app.js
  guardaba algo. El parche de la 4.13.1 cubría las dos vías conocidas, pero
  el suelo —un almacén que no se queda con nada— seguía ahí.
- **Arreglo:** `webview.start(..., private_mode=False)`: almacén persistente,
  como en un navegador; el espejo en disco pasa a ser red de seguridad. El
  puente admite además una segunda recarga antes de rendirse.
- **Guardia:** `tests/test_web.py::TestVentana` (pinea `private_mode=False` en
  toda llamada a `webview.start`) y la prueba real de dos arranques seguidos
  con un dibujo sembrado en disco, que lo conserva.

### v4.15.1 — «Limpiar todo» (y más botones) dejaron de funcionar en la app

- **Síntoma:** en la app 4.15.0 el botón «Limpiar todo» no hacía nada, y
  otros mandos tampoco (varios modales no se cerraban con su botón). En el
  navegador la misma versión de la web funcionaba.
- **Causa:** el `index.html` propio de pyzarra no es el del build: cada cambio
  de markup en pizarra hay que traerlo a mano. La 3.29.0 de pizarra añadió al
  panel las filas del estilo del texto de las formas (`row-label-color`,
  `label-font`, `label-align`…) y esa copia se olvidó. `init()` de `app.js`
  cablea los ids en orden, y al llegar a `$('label-color').addEventListener`
  lanzó `TypeError: null is not an object`: todo lo cableado después
  («Limpiar todo», los cierres de modal…) se quedó sin handler, y cada
  repintado volvía a fallar en `syncPanelSections`. La app no avisa: una
  ventana nativa no enseña la consola.
- **Arreglo:** traído el markup que faltaba (y dos líneas de la Ayuda del
  borrador que también se habían quedado atrás desde la 3.25.0).
- **Guardia:** `tests/test_web.py::TestIdsDelBuild` — extrae del `app.js` del
  build todos los ids que pide (`X("id")` con el alias de `getElementById`) y
  exige que existan en el `index.html` propio. Fallaba con los siete ids
  antes del arreglo. Además, el paso de sincronía de `CLAUDE.md` incluye ya
  el `diff` normalizado entre los dos `index.html`.

### v4.13.1 — Arrancar la app borraba el dibujo guardado

- **Síntoma:** al arrancar el bundle, el autosave y las pestañas en disco
  quedaban en blanco: el dibujo de la sesión anterior desaparecía.
- **Causa:** WKWebView bajo pywebview no persiste `localStorage`, así que la
  web arranca vacía; app.js crea una pestaña nueva y autoguarda una escena
  vacía. `bridge.js` restauraba la copia de Python y recargaba, pero esa
  escena vacía llegaba al disco por dos vías: las escrituras pendientes de
  antes de `pywebviewready` se volcaban por encima de lo restaurado, y al
  recargar app.js —aún vivo con su escena vacía— la guardaba «ahora» al oír
  `pagehide`, y el puente la espejaba.
- **Arreglo:** si el almacén llegó vacío, la copia de Python gana para las
  claves que tenga: lo pendiente de esas claves se descarta y, mientras dura
  la recarga, sus escrituras se ignoran; solo llega a disco lo que Python no
  tenía.
- **Guardia:** `tests/test_bridge.py` (arnés node `tests/bridge_harness.js`
  que ejecuta el `bridge.js` real en tres escenarios, `pagehide` incluido).
