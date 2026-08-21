"""
Configuracion compartida de pytest.

Este archivo lo carga pytest solo. No hay que importarlo.
"""

import sys
from pathlib import Path

import pytest

# Permite "from pyzarra import ..." sin instalar el paquete
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture
def api(tmp_path):
    """Una instancia limpia de la API, guardando estado en un dir temporal."""
    from pyzarra.api import Api

    return Api(data_dir=tmp_path / "estado")


@pytest.fixture
def web_dir() -> Path:
    """Carpeta donde vive la web."""
    return ROOT / "src" / "pyzarra" / "web"
