"""
Punto de entrada de la aplicacion.

Abre una ventana nativa que carga la web (HTML + CSS + JS vanilla).
La apariencia visual es IDENTICA a la del navegador.
"""

import sys
from pathlib import Path

import webview

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
    if sys.platform == "darwin":
        # En macOS, menu= se pierde (ver _instalar_menu_mac).
        webview.start(func=_instalar_menu_mac, args=(window,), debug=False)
    else:
        webview.start(menu=build_menu(), debug=False)


if __name__ == "__main__":
    main()
