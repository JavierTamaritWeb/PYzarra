"""Imágenes soltadas sobre el icono del Dock (abrir_archivos.py).

La parte de Cocoa (el delegado) no se puede probar sin una app de verdad;
aquí va la lógica pura: qué se acepta, la cola y lo que recibe la web.
"""

import base64
import re
from pathlib import Path

import pytest

from pyzarra import abrir_archivos

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def cola_limpia():
    abrir_archivos.vaciar()
    yield
    abrir_archivos.vaciar()


@pytest.fixture
def imagenes(tmp_path):
    rutas = {}
    for nombre, datos in [("a.png", b"\x89PNG"), ("b.jpg", b"JPG1"),
                          ("c.JPEG", b"JPG2"), ("d.gif", b"GIF"), ("e.txt", b"x")]:
        ruta = tmp_path / nombre
        ruta.write_bytes(datos)
        rutas[nombre] = ruta
    return rutas


class TestFiltrar:
    def test_acepta_png_y_jpeg_sin_importar_mayusculas(self, imagenes):
        validas = abrir_archivos.filtrar_imagenes(imagenes.values())
        assert [r.name for r in validas] == ["a.png", "b.jpg", "c.JPEG"]

    def test_descarta_inexistentes_carpetas_y_argumentos_raros(self, tmp_path):
        carpeta = tmp_path / "fotos.png"
        carpeta.mkdir()
        assert abrir_archivos.filtrar_imagenes(
            [tmp_path / "no.png", carpeta, "-psn_0_12345", "", None]) == []

    def test_descarta_las_demasiado_grandes(self, imagenes, monkeypatch):
        monkeypatch.setattr(abrir_archivos, "TAMANO_MAXIMO", 3)
        assert abrir_archivos.filtrar_imagenes([imagenes["a.png"]]) == []


class TestCola:
    def test_vaciar_devuelve_nombre_mime_y_base64(self, imagenes):
        assert abrir_archivos.encolar([imagenes["a.png"], imagenes["c.JPEG"]]) == 2
        assert abrir_archivos.vaciar() == [
            {"name": "a.png", "mime": "image/png",
             "data_b64": base64.b64encode(b"\x89PNG").decode()},
            {"name": "c.JPEG", "mime": "image/jpeg",
             "data_b64": base64.b64encode(b"JPG2").decode()},
        ]

    def test_vaciar_deja_la_cola_vacia(self, imagenes):
        abrir_archivos.encolar([imagenes["a.png"]])
        abrir_archivos.vaciar()
        assert abrir_archivos.vaciar() == []

    def test_varias_tandas_se_acumulan_en_orden(self, imagenes):
        abrir_archivos.encolar([imagenes["b.jpg"]])
        abrir_archivos.encolar([imagenes["a.png"], imagenes["d.gif"]])
        assert [i["name"] for i in abrir_archivos.vaciar()] == ["b.jpg", "a.png"]

    def test_una_imagen_borrada_entretanto_se_descarta(self, imagenes):
        abrir_archivos.encolar([imagenes["a.png"], imagenes["b.jpg"]])
        imagenes["a.png"].unlink()
        assert [i["name"] for i in abrir_archivos.vaciar()] == ["b.jpg"]

    def test_la_api_entrega_la_cola(self, api, imagenes):
        abrir_archivos.encolar([imagenes["b.jpg"]])
        assert [i["name"] for i in api.imagenes_pendientes()] == ["b.jpg"]
        assert api.imagenes_pendientes() == []


class TestEmpaquetado:
    """El Dock solo acepta el arrastre si el Info.plist declara los tipos."""

    def _spec(self) -> str:
        return (ROOT / "Pyzarra.spec").read_text(encoding="utf-8")

    def test_declara_png_y_jpeg_como_documentos(self):
        spec = self._spec()
        assert "CFBundleDocumentTypes" in spec
        assert '"public.png"' in spec and '"public.jpeg"' in spec

    def test_no_se_hace_la_app_por_defecto_para_las_fotos(self):
        assert '"LSHandlerRank": "Alternate"' in self._spec()

    def test_sin_argv_emulation(self):
        """Los archivos los recibe el delegado de Cocoa; con argv_emulation el
        bootloader se tragaba el del arranque."""
        assert "argv_emulation=False" in self._spec()

    def test_los_tipos_del_spec_coinciden_con_los_aceptados(self):
        uti = {"image/png": "public.png", "image/jpeg": "public.jpeg"}
        declarados = set(re.findall(r'"(public\.\w+)"', self._spec()))
        assert {uti[m] for m in abrir_archivos.IMAGENES.values()} == declarados

    def test_version_del_spec_coincide_con_pyproject(self):
        import tomllib

        version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
        assert f'VERSION = "{version}"' in self._spec()
