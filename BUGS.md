# BUGS.md — Registro de errores corregidos en Pyzarra

Errores propios de la app de escritorio (no de la web, que tiene su propio
[BUGS.md en pizarra](https://github.com/JavierTamaritWeb/pizarra/blob/main/BUGS.md)).
Cada entrada: síntoma, causa, arreglo y la **guardia** que falla si vuelve.

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
