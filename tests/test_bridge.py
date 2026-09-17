"""bridge.js bajo un arnés node: la carrera del arranque (v4.13.1).

WKWebView bajo pywebview no persiste localStorage entre arranques, así que
la web arranca con el almacén vacío, app.js crea una pestaña nueva y
autoguarda una escena vacía ANTES de `pywebviewready`, y el puente tiene
que decidir: manda la copia de Python. Antes volcaba esa escena vacía a
disco y el dibujo guardado desaparecía.

El arnés (tests/bridge_harness.js) ejecuta el bridge.js real con un
localStorage, un sessionStorage y un pywebview.api simulados, y devuelve
lo observado en JSON. Se salta si no hay `node`.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "src" / "pyzarra" / "web"
HARNESS = Path(__file__).with_name("bridge_harness.js")

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="hace falta node")


def correr(escenario: str) -> dict:
    out = subprocess.run(
        ["node", str(HARNESS), str(WEB / "js" / "bridge.js"), escenario],
        capture_output=True, text=True, check=True, timeout=30,
    )
    return json.loads(out.stdout)


def test_almacen_vacio_con_datos_en_python_gana_python_y_recarga_una_vez():
    r = correr("vacio-con-python")
    guardadas = dict(r["saves"])
    assert "sketchwire.autosave" not in guardadas, (
        "el autosave vacío que app.js fabricó al arrancar NO debe pisar el dibujo en disco")
    assert "sketchwire.tabs" not in guardadas, "ni las pestañas nuevas a las guardadas"
    assert guardadas == {"sketchwire.library": "[]"}, "solo llega a disco lo que Python no tenía"
    escena = json.loads(r["local"]["sketchwire.autosave"])
    assert escena["elements"][0]["type"] == "rect", "el almacén queda con el dibujo de Python"
    assert json.loads(r["local"]["sketchwire.tabs"])["active"] == "viejo"
    assert r["local"]["sketchwire.prefs"] == '{"a":1}'
    assert r["reloads"] == 1, "recarga una vez para que app.js lea lo restaurado"


def test_almacen_con_datos_al_arrancar_manda_el_almacen():
    r = correr("lleno")
    guardadas = dict(r["saves"])
    assert guardadas == {"sketchwire.library": "[]"}
    assert json.loads(r["local"]["sketchwire.tabs"])["active"] == "nuevo", (
        "lo que ya había en el almacén no se toca")
    # Python tenía prefs y el almacén no: esa sí se restaura, y recarga.
    assert r["local"]["sketchwire.prefs"] == '{"a":1}'
    assert r["reloads"] == 1


def test_primer_arranque_sin_nada_en_python_vuelca_lo_pendiente():
    r = correr("primer-arranque")
    guardadas = dict(r["saves"])
    assert set(guardadas) == {"sketchwire.tabs", "sketchwire.autosave", "sketchwire.library"}
    assert r["reloads"] == 0
