"""
Tests de la web.

Estos tests atrapan el error MAS COMUN de pywebview:
la ventana se abre en blanco porque falta un archivo
o porque una ruta es absoluta.
"""

import re

import pytest

# Los 19 scripts originales de la app, en su orden de carga (config primero,
# app ultimo). bridge.js es el unico anadido de la migracion y va ANTES.
SCRIPTS_ORIGINALES = [
    "js/config.js",
    "js/sketchy.js",
    "js/freehand.js",
    "js/arc.js",
    "js/curve-path.js",
    "js/shape-rotation.js",
    "js/regular-polygon.js",
    "js/trapezoid.js",
    "js/hatch.js",
    "js/airbrush.js",
    "js/flood.js",
    "js/eraser.js",
    "js/building.js",
    "js/garden.js",
    "js/solid.js",
    "js/renderer.js",
    "js/exporter.js",
    "js/templates.js",
    "js/app.js",
]


class TestArchivosExisten:
    def test_carpeta_web_existe(self, web_dir):
        assert web_dir.is_dir()

    @pytest.mark.parametrize(
        "ruta",
        ["index.html", "css/styles.css", "js/bridge.js"] + SCRIPTS_ORIGINALES,
    )
    def test_archivo_existe(self, web_dir, ruta):
        assert (web_dir / ruta).is_file(), f"Falta {ruta}"

    def test_index_no_esta_vacio(self, web_dir):
        assert len((web_dir / "index.html").read_text()) > 100


class TestRutasRelativas:
    """
    Una ruta absoluta como /css/styles.css funciona en el navegador
    con servidor, pero ROMPE dentro del .app.
    """

    def _html(self, web_dir) -> str:
        return (web_dir / "index.html").read_text(encoding="utf-8")

    def test_css_no_usa_ruta_absoluta(self, web_dir):
        malas = re.findall(r'href="(/[^/][^"]*)"', self._html(web_dir))
        assert not malas, f"Rutas absolutas en CSS: {malas}"

    def test_js_no_usa_ruta_absoluta(self, web_dir):
        malas = re.findall(r'src="(/[^/][^"]*)"', self._html(web_dir))
        assert not malas, f"Rutas absolutas en JS: {malas}"

    def test_sin_query_strings_de_cache(self, web_dir):
        """?v=1.2.3 no sirve en file:// y rompe la comprobacion de enlaces."""
        assert "?v=" not in self._html(web_dir)

    def test_todos_los_archivos_enlazados_existen(self, web_dir):
        html = self._html(web_dir)
        enlaces = re.findall(r'(?:href|src)="([^"]+)"', html)

        locales = [
            e for e in enlaces
            if not e.startswith(("http://", "https://", "//", "#", "data:"))
        ]

        faltan = [e for e in locales if not (web_dir / e).exists()]
        assert not faltan, f"Enlazados pero no existen: {faltan}"


class TestOrdenDeScripts:
    """El orden de carga es load-bearing: config primero, app ultimo."""

    def _html(self, web_dir) -> str:
        return (web_dir / "index.html").read_text(encoding="utf-8")

    def _scripts(self, web_dir) -> list[str]:
        return re.findall(r'<script src="([^"]+)"></script>', self._html(web_dir))

    def test_bridge_se_carga_primero(self, web_dir):
        """
        El parche de localStorage de bridge.js debe instalarse ANTES
        de que app.js lea el autoguardado.
        """
        assert self._scripts(web_dir)[0] == "js/bridge.js"

    def test_los_scripts_originales_mantienen_su_orden(self, web_dir):
        assert self._scripts(web_dir)[1:] == SCRIPTS_ORIGINALES


class TestPuenteEnJavaScript:
    def _bridge(self, web_dir) -> str:
        return (web_dir / "js" / "bridge.js").read_text(encoding="utf-8")

    def test_espera_al_evento_pywebviewready(self, web_dir):
        """
        window.pywebview.api NO existe al cargar la pagina.
        Sin esta espera, la app falla al arrancar.
        """
        assert "pywebviewready" in self._bridge(web_dir)

    def test_usa_la_api_de_pywebview(self, web_dir):
        assert "pywebview.api" in self._bridge(web_dir)

    @pytest.mark.parametrize(
        "metodo",
        ["save_file", "open_file", "save_state", "load_state", "delete_state"],
    )
    def test_bridge_llama_metodos_que_existen_en_python(self, web_dir, metodo):
        """Cada metodo que usa bridge.js debe existir en api.py."""
        from pyzarra.api import Api

        assert metodo in self._bridge(web_dir)
        assert callable(getattr(Api(), metodo, None))

    def test_los_js_originales_no_se_tocaron(self, web_dir):
        """La regla de la migracion: cero ediciones al JS existente."""
        for ruta in [
            "js/app.js", "js/exporter.js", "js/config.js", "js/renderer.js",
        ]:
            js = (web_dir / ruta).read_text(encoding="utf-8")
            assert "pywebview" not in js, f"{ruta} fue modificado"


class TestPyprojectToml:
    def _toml(self) -> dict:
        import tomllib
        from pathlib import Path

        ruta = Path(__file__).parent.parent / "pyproject.toml"
        return tomllib.loads(ruta.read_text(encoding="utf-8"))

    def test_pyproject_es_valido(self):
        assert self._toml()["project"]["name"] == "pyzarra"

    def test_todas_las_versiones_estan_fijadas(self):
        """
        Sin '==' una libreria puede actualizarse sola
        y romper la app sin avisar.
        """
        deps = self._toml()["project"]["dependencies"]
        sueltas = [d for d in deps if "==" not in d]
        assert not sueltas, f"Sin version fija: {sueltas}"

    def test_pywebview_esta_declarado(self):
        deps = self._toml()["project"]["dependencies"]
        assert any(d.startswith("pywebview") for d in deps)


class TestVersionDeUv:
    """
    La version de la HERRAMIENTA uv tambien se controla.
    Si no, cada persona del equipo puede usar un uv distinto
    y generar un uv.lock incompatible.
    """

    def _toml(self) -> dict:
        import tomllib
        from pathlib import Path

        ruta = Path(__file__).parent.parent / "pyproject.toml"
        return tomllib.loads(ruta.read_text(encoding="utf-8"))

    def test_uv_tiene_version_minima_declarada(self):
        assert "required-version" in self._toml()["tool"]["uv"]

    def test_existe_python_version(self):
        from pathlib import Path

        ruta = Path(__file__).parent.parent / ".python-version"
        assert ruta.is_file(), "Falta .python-version"

    def test_python_version_coincide_con_pyproject(self):
        """
        Si .python-version dice 3.11 pero pyproject exige >=3.13,
        uv creara un entorno que no cumple. Fallo silencioso.
        """
        from pathlib import Path

        fijado = Path(__file__).parent.parent / ".python-version"
        version = fijado.read_text(encoding="utf-8").strip()
        requiere = self._toml()["project"]["requires-python"]

        minimo = requiere.replace(">=", "").strip()
        may_f, min_f = (int(x) for x in version.split(".")[:2])
        may_r, min_r = (int(x) for x in minimo.split(".")[:2])

        assert (may_f, min_f) >= (may_r, min_r), (
            f".python-version ({version}) es menor que requires-python ({requiere})"
        )


class TestMenuNativo:
    """La barra de menus dispara botones de la web: deben existir."""

    def test_cada_entrada_apunta_a_un_boton_real(self, web_dir):
        from pyzarra.menu import MENU_LAYOUT

        html = (web_dir / "index.html").read_text(encoding="utf-8")
        faltan = [
            boton
            for _, entradas in MENU_LAYOUT
            for entrada in entradas
            if entrada is not None
            for _, boton in [entrada]
            if f'id="{boton}"' not in html
        ]
        assert not faltan, f"El menu apunta a botones inexistentes: {faltan}"

    def test_el_menu_se_construye(self):
        from pyzarra.menu import build_menu

        menus = build_menu()
        assert len(menus) >= 3
        titulos = [m.title for m in menus]
        assert "Archivo" in titulos and "Edición" in titulos
