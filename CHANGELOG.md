# Changelog

Historial de versiones de **Pyzarra**, la app de escritorio (pywebview) de
[pizarra](https://github.com/JavierTamaritWeb/pizarra). La web embebida es un
build de ese proyecto: cada versión indica con cuál va al día, y sus novedades
de dibujo se detallan en el
[CHANGELOG de pizarra](https://github.com/JavierTamaritWeb/pizarra/blob/main/CHANGELOG.md).
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [4.7.0] — 2026-09-01

Web al día con pizarra **3.21.0**.

### Añadido

- Quinta forma de punta de flecha: **Media** — un ala sola, el rasgo de un
  «1» escrito a mano. Para la flecha recta, la curva y la flecha semicírculo.

## [4.6.0] — 2026-09-01

Web al día con pizarra **3.20.0**.

### Añadido

- **Flecha semicírculo** (⤾) en la sección Dibujo: el arco de 180° del
  Semicírculo pero con punta — nace donde acaba el arrastre, `D` la invierte,
  «Doble punta» pone las dos y la forma se elige entre Clásica, Maciza, Barra
  o Punto.

## [4.5.0] — 2026-09-01

Web al día con pizarra **3.19.0**.

### Añadido

- **Triángulo irregular** (⊿) en Formas: isósceles o escaleno a elegir en
  «Ajustes de la forma».

## [4.4.1] — 2026-09-01

Web al día con pizarra **3.18.1**: el texto corto del renombrado de pestañas
se limita a 12 caracteres.

## [4.4.0] — 2026-09-01

Web al día con pizarra **3.18.0**.

### Cambiado

- **Nomenclatura automática de pestañas**: toda pestaña se muestra
  «Pizarra N» o «Pizarra N - nombre»; el número es la posición (se renumera
  solo) y el doble clic edita únicamente el nombre corto.

## [4.3.0] — 2026-09-01

Web al día con pizarra **3.17.0**.

### Añadido

- **Pestañas de pizarra**: varios documentos en la misma ventana, cada uno con
  su dibujo, su zoom y su nombre, restaurados al reabrir.

## [4.2.0] — 2026-08-30

Web al día con pizarra **3.16.0**.

### Añadido

- **Alumbrado deportivo** en el catálogo de Iluminación.

## [4.1.0] — 2026-08-30

Web al día con pizarra **3.15.0**.

### Añadido

- Botón **«Iluminación»** en Edificios, con su catálogo de farolas.

## [4.0.1] — 2026-08-29

Web al día con pizarra **3.14.2**.

### Corregido

- La flecha dibujada sobre una imagen ya no salta al soltarla.

## [4.0.0] — 2026-08-21

Primera versión de escritorio. Hereda la numeración 4.x para marcar el salto
de plataforma sobre la web 3.x.

### Añadido

- **Migración a pywebview**: ventana nativa (WKWebView en macOS) que carga la
  web por `file://`, con estructura `src/`, `uv` y `pytest`.
- **`api.py`**, el puente JS→Python: persistencia por clave en
  `~/Library/Application Support/Pyzarra/`, con escritura atómica y carga
  tolerante a archivos corruptos.
- **`bridge.js`**, el único JS añadido sobre el build: diálogos nativos de
  Guardar y Abrir, espejo del `localStorage` en disco y restauración con
  guarda anti-bucle.
- **Barra de menús nativa** (Archivo, Edición, Lienzo, Ayuda) conectada a los
  botones de la web; en macOS se instala con AppKit tras mostrarse la ventana
  (workaround de `set_app_menu`).
- **Empaquetado** a `Pyzarra.app` con PyInstaller (`./build-mac.sh`), icono
  propio y firma ad-hoc.
- Rebranding a **Pyzarra** (logo, título, ayuda, archivo de biblioteca).

### Corregido

- Las barras flotantes arrastradas ya no se ocultan detrás del lienzo
  (WKWebView recorta `position:fixed` por el `overflow` de un ancestro).
- Arranque sin errores CORS bajo `file://` (sin `<link rel="manifest">`).
