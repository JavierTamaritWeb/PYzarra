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


def main() -> None:
    api = Api()

    webview.create_window(
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
    webview.start(menu=build_menu(), debug=False)


if __name__ == "__main__":
    main()
