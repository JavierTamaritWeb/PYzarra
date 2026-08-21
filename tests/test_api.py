"""
Tests de la logica Python (api.py).

Aqui va TODO lo que se pueda probar sin abrir una ventana.
Los dialogos nativos se simulan con monkeypatch.
"""

import base64
import json

import pytest


class TestPersistencia:
    def test_save_y_load_hacen_round_trip(self, api):
        assert api.save_state("sketchwire.prefs", '{"canvasBg":"#fff"}')
        assert api.load_state() == {"sketchwire.prefs": '{"canvasBg":"#fff"}'}

    def test_varias_claves(self, api):
        api.save_state("sketchwire.autosave", "{}")
        api.save_state("sketchwire.library", '{"v":1,"items":[]}')
        estado = api.load_state()
        assert set(estado) == {"sketchwire.autosave", "sketchwire.library"}

    def test_sobrescribir_una_clave(self, api):
        api.save_state("sketchwire.prefs", "viejo")
        api.save_state("sketchwire.prefs", "nuevo")
        assert api.load_state()["sketchwire.prefs"] == "nuevo"

    def test_delete_state_borra_la_clave(self, api):
        api.save_state("sketchwire.prefs", "x")
        assert api.delete_state("sketchwire.prefs")
        assert api.load_state() == {}

    def test_delete_de_clave_inexistente_no_falla(self, api):
        assert api.delete_state("sketchwire.nada")

    def test_load_sin_datos_devuelve_dict_vacio(self, api):
        assert api.load_state() == {}

    def test_clave_peligrosa_se_rechaza(self, api):
        """Una clave con / podria escribir fuera del directorio de datos."""
        assert not api.save_state("../fuera", "x")
        assert not api.delete_state("../fuera")

    def test_soporta_mas_de_un_mib(self, api):
        """La biblioteca ya no tiene el tope de 1 MiB de localStorage."""
        grande = "x" * (2 * 1024 * 1024)
        assert api.save_state("sketchwire.library", grande)
        assert len(api.load_state()["sketchwire.library"]) == 2 * 1024 * 1024

    def test_unicode(self, api):
        api.save_state("sketchwire.prefs", '{"texto":"José Ñoño 🌱"}')
        assert "🌱" in api.load_state()["sketchwire.prefs"]


class _VentanaFalsa:
    """Simula webview.windows[0] sin abrir ventana."""

    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.llamadas = []

    def create_file_dialog(self, *args, **kwargs):
        self.llamadas.append((args, kwargs))
        return self.respuesta


@pytest.fixture
def ventana(monkeypatch):
    """Instala una ventana falsa; configurar .respuesta en cada test."""
    import webview

    v = _VentanaFalsa(None)
    monkeypatch.setattr(webview, "windows", [v])
    return v


class TestSaveFile:
    def test_escribe_los_bytes_correctos(self, api, ventana, tmp_path):
        destino = tmp_path / "wireframe.png"
        ventana.respuesta = str(destino)
        contenido = b"\x89PNG fake"
        b64 = base64.b64encode(contenido).decode()

        resultado = api.save_file("wireframe.png", b64)

        assert resultado == str(destino)
        assert destino.read_bytes() == contenido

    def test_sugiere_el_nombre(self, api, ventana, tmp_path):
        ventana.respuesta = str(tmp_path / "x.svg")
        api.save_file("boceto.svg", base64.b64encode(b"<svg/>").decode())
        assert ventana.llamadas[0][1].get("save_filename") == "boceto.svg"

    def test_cancelar_devuelve_none(self, api, ventana):
        ventana.respuesta = None
        assert api.save_file("wireframe.png", "") is None

    def test_acepta_respuesta_en_tupla(self, api, ventana, tmp_path):
        """Algunas plataformas devuelven una tupla en vez de un string."""
        destino = tmp_path / "w.json"
        ventana.respuesta = (str(destino),)
        api.save_file("w.json", base64.b64encode(b"{}").decode())
        assert destino.read_bytes() == b"{}"


class TestOpenFile:
    def test_devuelve_nombre_y_contenido(self, api, ventana, tmp_path):
        origen = tmp_path / "dibujo.json"
        origen.write_text('{"elements":[]}', encoding="utf-8")
        ventana.respuesta = (str(origen),)

        resultado = api.open_file([".json"])

        assert resultado == {"name": "dibujo.json", "content": '{"elements":[]}'}

    def test_cancelar_devuelve_none(self, api, ventana):
        ventana.respuesta = None
        assert api.open_file([".json"]) is None

    def test_sin_filtro_tambien_funciona(self, api, ventana, tmp_path):
        origen = tmp_path / "a.json"
        origen.write_text("{}", encoding="utf-8")
        ventana.respuesta = (str(origen),)
        assert api.open_file() is not None


class TestPuenteJavaScript:
    """
    pywebview solo expone a JS los metodos publicos.
    Estos tests protegen ese contrato.
    """

    def _metodos_publicos(self, api) -> set[str]:
        return {
            n
            for n in dir(api)
            if not n.startswith("_") and callable(getattr(api, n))
        }

    def test_metodos_esperados_estan_expuestos(self, api):
        publicos = self._metodos_publicos(api)
        assert {"save_file", "open_file", "save_state", "load_state", "delete_state"} <= publicos

    def test_metodos_privados_no_se_exponen(self, api):
        assert "_state_path" not in self._metodos_publicos(api)

    def test_todo_lo_publico_es_serializable(self, api):
        """
        pywebview envia los datos a JS como JSON.
        Si un metodo devuelve algo raro, el puente falla en silencio.
        """
        api.save_state("sketchwire.prefs", "{}")
        json.dumps(api.load_state())
        json.dumps(api.save_state("sketchwire.a", "1"))
        json.dumps(api.delete_state("sketchwire.a"))
