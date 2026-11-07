"""
Imágenes soltadas sobre el icono de la app (Dock de macOS) o pasadas por
línea de órdenes (`uv run pyzarra foto.png`).

Flujo: macOS avisa al delegado de la aplicación (`application:openFiles:`),
tanto si la app ya estaba abierta como si el arrastre la arranca. Las rutas
válidas se ENCOLAN aquí y la web las RECOGE cuando está lista
(`Api.imagenes_pendientes`, que llama a `vaciar`). Con la app abierta,
además, se avisa a la web para que las recoja al momento.

Cola y no empuje: al arrancar la web aún no existe, y si el puente decide
recargar la página para restaurar el dibujo, una imagen insertada antes se
perdería con la recarga. La cola espera a que la web pida.

La web solo acepta PNG y JPEG (IMAGE_MIME de app.js), así que no se encola
otra cosa; los tipos aceptados en el Dock se declaran en `Pyzarra.spec`
(CFBundleDocumentTypes) y deben coincidir con IMAGENES.
"""

import base64
import threading
from pathlib import Path

IMAGENES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

# Una imagen mayor viaja en base64 por el puente y acaba dentro del JSON del
# proyecto; por encima de esto no compensa.
TAMANO_MAXIMO = 25 * 1024 * 1024

_pendientes: list[Path] = []
_cerrojo = threading.Lock()


def filtrar_imagenes(rutas) -> list[Path]:
    """Se queda con las rutas que son imágenes PNG/JPEG legibles y no enormes.

    Ignora lo demás sin fallar: argumentos que no son rutas (el `-psn_…` que
    macOS añadía antiguamente), carpetas, archivos que no existen, otros tipos.
    """
    validas = []
    for r in rutas:
        try:
            ruta = Path(r)
            if ruta.suffix.lower() not in IMAGENES or not ruta.is_file():
                continue
            if ruta.stat().st_size > TAMANO_MAXIMO:
                continue
        except (OSError, TypeError, ValueError):
            continue
        validas.append(ruta)
    return validas


def encolar(rutas) -> int:
    """Añade a la cola las imágenes válidas de `rutas`; devuelve cuántas."""
    validas = filtrar_imagenes(rutas)
    with _cerrojo:
        _pendientes.extend(validas)
    return len(validas)


def vaciar() -> list[dict]:
    """Devuelve las imágenes encoladas como {name, mime, data_b64} y vacía la cola.

    Una imagen que ya no se puede leer (la borraron entretanto) se descarta.
    """
    with _cerrojo:
        rutas = list(_pendientes)
        _pendientes.clear()
    imagenes = []
    for ruta in rutas:
        try:
            datos = ruta.read_bytes()
        except OSError:
            continue
        imagenes.append({
            "name": ruta.name,
            "mime": IMAGENES[ruta.suffix.lower()],
            "data_b64": base64.b64encode(datos).decode("ascii"),
        })
    return imagenes


def avisar_a_la_web() -> None:
    """Pide a la web que recoja la cola. Desde un hilo aparte, SIEMPRE.

    `evaluate_js` de pywebview en Cocoa encola el trabajo en el hilo principal
    y espera bloqueado el resultado: llamado desde el propio hilo principal
    (el delegado de la app vive ahí) se quedaría colgado para siempre. Además
    espera a que la página haya cargado, que es justo lo que queremos.
    Si la web aún no está lista, el puente ignora el aviso y recoge la cola
    él mismo al estarlo.
    """

    def _avisar():
        import webview

        try:
            if webview.windows:
                webview.windows[0].evaluate_js(
                    "window.__pyzarraImagenes && window.__pyzarraImagenes()"
                )
        except Exception:  # noqa: BLE001 — un aviso fallido no debe tumbar la app
            pass

    threading.Thread(target=_avisar, daemon=True).start()


def instalar_receptor_cocoa() -> None:
    """Enseña al delegado de la app de pywebview a abrir archivos (macOS).

    pywebview 5.3.2 no implementa `application:openFiles:` en su
    `BrowserView.AppDelegate`; se le añade el método a la clase antes de
    `webview.start`, que es cuando crea el delegado (antes de `app.run()`,
    así que también recibe el evento del arranque).
    """
    import AppKit
    import objc
    from webview.platforms.cocoa import BrowserView

    def application_openFiles_(self, app, rutas):
        encolar([str(r) for r in rutas])
        app.replyToOpenOrPrint_(AppKit.NSApplicationDelegateReplySuccess)
        avisar_a_la_web()

    objc.classAddMethods(
        BrowserView.AppDelegate,
        [objc.selector(application_openFiles_, selector=b"application:openFiles:",
                       signature=b"v@:@@")],
    )
