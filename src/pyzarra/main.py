"""
Punto de entrada de la aplicacion.

Abre una ventana nativa que carga la web (HTML + CSS + JS vanilla).
La apariencia visual es IDENTICA a la del navegador.
"""

import sys
from pathlib import Path

import webview

from pyzarra import abrir_archivos
from pyzarra.api import Api
from pyzarra.menu import build_menu

# Carpeta donde vive la web. Empaquetado con PyInstaller, los datos
# viven en sys._MEIPASS (ver datas= en Pyzarra.spec); en desarrollo,
# junto a este archivo.
if getattr(sys, "frozen", False):
    WEB_DIR = Path(sys._MEIPASS) / "pyzarra" / "web"
else:
    WEB_DIR = Path(__file__).parent / "web"
INDEX = WEB_DIR / "index.html"


def _instalar_menu_mac(window) -> None:
    """
    Workaround para macOS: el backend Cocoa de pywebview (5.3.2) borra el
    menu pasado a webview.start() al mostrar la primera ventana
    (first_show -> _clear_main_menu). Lo reinstalamos en el hilo principal
    una vez la ventana esta visible.
    """
    from PyObjCTools import AppHelper

    from pyzarra.menu import instalar_menu_cocoa

    window.events.shown.wait()
    AppHelper.callAfter(instalar_menu_cocoa)


def _vaciar_cache_web_mac(espera: float = 3.0) -> None:
    """
    Vacia la cache HTTP de WebKit (disco, memoria, fetch) antes de cargar la
    web. NO toca localStorage ni nada mas del almacen: solo la cache.

    Por que: pywebview sirve la web desde un servidor local fijo
    (http://127.0.0.1:42001, puerto fijo con private_mode=False) y sus
    cabeceras anti-cache se pierden (bottle.static_file devuelve una
    respuesta nueva). Con el almacen persistente, WebKit reutilizaba los JS
    de una version anterior por su Last-Modified: el .app nuevo corria el
    bridge.js viejo (v4.17.0, soltar en el Dock no hacia nada). Cada arranque
    debe ejecutar exactamente la web que lleva dentro.

    El borrado es asincrono: se gira el run loop hasta que termina (o
    `espera` segundos) para que acabe ANTES de que la ventana pida nada.
    """
    try:
        import Foundation
        import WebKit

        tipos = Foundation.NSSet.setWithArray_([
            WebKit.WKWebsiteDataTypeDiskCache,
            WebKit.WKWebsiteDataTypeMemoryCache,
            WebKit.WKWebsiteDataTypeFetchCache,
        ])
        hecho = []
        WebKit.WKWebsiteDataStore.defaultDataStore().removeDataOfTypes_modifiedSince_completionHandler_(
            tipos, Foundation.NSDate.distantPast(), lambda: hecho.append(True)
        )
        limite = Foundation.NSDate.dateWithTimeIntervalSinceNow_(espera)
        bucle = Foundation.NSRunLoop.currentRunLoop()
        while not hecho and Foundation.NSDate.date().compare_(limite) < 0:
            bucle.runUntilDate_(Foundation.NSDate.dateWithTimeIntervalSinceNow_(0.05))
    except Exception:  # noqa: BLE001 — sin cache limpia la app sigue arrancando
        pass


def main() -> None:
    api = Api()

    window = webview.create_window(
        title="Pyzarra",
        url=str(INDEX),
        js_api=api,          # <-- puente JavaScript -> Python
        width=1200,
        height=800,
        min_size=(800, 600),
        resizable=True,
        confirm_close=False,
    )

    # debug=True abre las DevTools (inspeccionar elemento).
    # Ponlo en True mientras desarrollas.
    # private_mode=False (v4.15.2): pywebview arranca WKWebView en modo privado
    # por defecto y NO persiste localStorage entre arranques ni, bajo file://,
    # de forma fiable a través de una recarga. La web guarda todo su estado en
    # localStorage y bridge.js lo espeja a disco; con el almacén efímero cada
    # arranque dependía de la restauración del puente, y app.js (que arranca
    # antes de `pywebviewready`) veía siempre un lienzo vacío y acababa
    # pisando el disco con él. Con el almacén persistente la app se comporta
    # como en un navegador y el espejo en disco queda de red de seguridad.
    if sys.platform == "darwin":
        _vaciar_cache_web_mac()
        # Soltar imagenes sobre el icono del Dock (application:openFiles:).
        # Tambien cubre `uv run pyzarra foto.png`: NSApplication entrega los
        # argumentos como archivos a abrir, asi que NO se encolan aparte (se
        # duplicaban).
        abrir_archivos.instalar_receptor_cocoa()
        # En macOS, menu= se pierde (ver _instalar_menu_mac).
        webview.start(func=_instalar_menu_mac, args=(window,), debug=False, private_mode=False)
    else:
        # Imagenes pasadas como argumentos: la web las recoge al estar lista.
        abrir_archivos.encolar(sys.argv[1:])
        webview.start(menu=build_menu(), debug=False, private_mode=False)


if __name__ == "__main__":
    main()
