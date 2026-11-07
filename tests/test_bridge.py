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
    assert escena["elements"][0]["type"] == "rect", (
        "el almacén queda con el dibujo de Python, también tras el pagehide de la recarga")
    assert json.loads(r["local"]["sketchwire.tabs"])["active"] == "viejo"
    assert r["local"]["sketchwire.prefs"] == '{"a":1}'
    assert r["reloads"] == 1, "recarga una vez para que app.js lea lo restaurado"


def test_almacen_con_datos_al_arrancar_manda_el_almacen():
    r = correr("lleno")
    guardadas = dict(r["saves"])
    assert guardadas["sketchwire.library"] == "[]"
    # El autosave que app.js guarda al recargar es el del almacén, que aquí
    # es la verdad: espejarlo a disco es correcto (y es lo que ya había).
    assert set(guardadas) <= {"sketchwire.library", "sketchwire.autosave"}
    if "sketchwire.autosave" in guardadas:
        assert guardadas["sketchwire.autosave"] == r["local"]["sketchwire.autosave"]
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


# ---------- Imágenes soltadas sobre el icono del Dock ----------

def test_imagenes_de_la_cola_se_sueltan_en_el_lienzo_al_estar_listo():
    r = correr("imagenes")
    assert r["llamadasPendientes"] == 1, "el puente recoge la cola UNA vez, al estar listo"
    assert r["quedanEnCola"] == 0
    assert len(r["drops"]) == 1, "todas las imágenes van en UN drop (app.js las pone en cascada)"
    drop = r["drops"][0]
    assert drop["type"] == "drop"
    assert drop["files"] == [
        {"name": "foto.png", "type": "image/png", "size": 8},
        {"name": "otra.jpg", "type": "image/jpeg", "size": 3},
    ], "los bytes de Python llegan como File con su tipo (app.js filtra por MIME)"
    # Centro de la parte visible: lienzo (100..1100 × 50..750) recortado por
    # su contenedor con scroll (0..800 × 0..600).
    assert (drop["clientX"], drop["clientY"]) == (450, 325)


def test_un_aviso_de_python_antes_de_estar_listo_no_recoge_nada():
    """Python avisa al soltar con la app abierta; si la web aún no decidió si
    recarga, recoger sería insertar la imagen en una página que va a morir."""
    r = correr("imagenes")
    assert r["avisoTempranoEsPromesa"]
    assert r["llamadasPendientes"] == 1, "solo la recogida de cuando está listo"


def test_si_el_puente_recarga_las_imagenes_esperan_en_python():
    r = correr("imagenes-con-recarga")
    assert r["reloads"] == 1
    assert r["drops"] == [], "nada se inserta en la página que se va a recargar"
    assert r["llamadasPendientes"] == 0
    assert r["quedanEnCola"] == 2, "la cola sigue intacta para la página recargada"


def test_sin_imagenes_no_se_simula_ningun_drop():
    assert correr("primer-arranque")["drops"] == []
