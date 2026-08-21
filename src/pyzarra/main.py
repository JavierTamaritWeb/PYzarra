"""
Punto de entrada de la aplicacion.

Abre una ventana nativa que carga la web (HTML + CSS + JS vanilla).
La apariencia visual es IDENTICA a la del navegador.
"""

from pathlib import Path

import webview

from pyzarra.api import Api

# Carpeta donde vive la web. Funciona tanto en desarrollo
# como dentro del .app empaquetado.
WEB_DIR = Path(__file__).parent / "web"
INDEX = WEB_DIR / "index.html"


def main() -> None:
    api = Api()

    webview.create_window(
        title="Pizarra — Bocetos Web",
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
    webview.start(debug=False)


if __name__ == "__main__":
    main()
