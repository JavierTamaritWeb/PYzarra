"""
Puente JavaScript -> Python de Pizarra.

Cada metodo publico se llama desde JS asi:

    const resultado = await window.pywebview.api.save_file("wireframe.png", b64);

Reglas:
- Los metodos que empiezan por "_" NO se exponen a JavaScript.
- Argumentos y retornos deben ser tipos JSON-serializables (str, int, list, dict, bool, None).
"""

import base64
import re
from pathlib import Path

APP_NAME = "Pyzarra"

# Solo se persisten claves de la app (sketchwire.autosave, .prefs, .library)
_KEY_RE = re.compile(r"^[\w.-]+$")


def _default_data_dir() -> Path:
    home = Path.home()
    mac_dir = home / "Library" / "Application Support"
    if mac_dir.is_dir():
        return mac_dir / APP_NAME
    return home / f".{APP_NAME.lower()}"


class Api:
    def __init__(self, data_dir: Path | None = None):
        self._dir = Path(data_dir) if data_dir else _default_data_dir()

    # ---------- Exportar: dialogo nativo de Guardar ----------
    def save_file(self, suggested_name: str, content_b64: str) -> str | None:
        """Pide destino con un dialogo nativo y escribe los bytes (base64)."""
        import webview

        ventana = webview.windows[0]
        destino = ventana.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=suggested_name
        )
        if not destino:
            return None
        ruta = Path(destino if isinstance(destino, str) else destino[0])
        ruta.write_bytes(base64.b64decode(content_b64))
        return str(ruta)

    # ---------- Importar: dialogo nativo de Abrir ----------
    def open_file(self, extensions: list[str] | None = None) -> dict | None:
        """Pide un archivo y devuelve {"name": ..., "content": texto}."""
        import webview

        tipos = None
        if extensions:
            limpias = ";".join(f"*{e}" for e in extensions)
            tipos = (f"Archivos ({limpias})",)

        ventana = webview.windows[0]
        resultado = ventana.create_file_dialog(webview.OPEN_DIALOG, file_types=tipos or ())
        if not resultado:
            return None
        ruta = Path(resultado[0])
        return {"name": ruta.name, "content": ruta.read_text(encoding="utf-8")}

    # ---------- Persistencia en disco (sustituye a localStorage) ----------
    def save_state(self, key: str, value: str) -> bool:
        """Guarda un valor (string JSON) en un archivo por clave."""
        if not _KEY_RE.match(key):
            return False
        self._dir.mkdir(parents=True, exist_ok=True)
        self._state_path(key).write_text(value, encoding="utf-8")
        return True

    def load_state(self) -> dict:
        """Devuelve {clave: valor} con todo el estado guardado."""
        if not self._dir.is_dir():
            return {}
        estado = {}
        for archivo in self._dir.glob("*.json"):
            clave = archivo.stem
            estado[clave] = archivo.read_text(encoding="utf-8")
        return estado

    def delete_state(self, key: str) -> bool:
        """Borra una clave guardada (espejo de localStorage.removeItem)."""
        if not _KEY_RE.match(key):
            return False
        ruta = self._state_path(key)
        if ruta.is_file():
            ruta.unlink()
        return True

    # ---------- metodos privados: NO visibles desde JS ----------
    def _state_path(self, key: str) -> Path:
        return self._dir / f"{key}.json"
