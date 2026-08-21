# Pyzarra

App de escritorio que carga tu web (HTML + CSS + JS vanilla) en una ventana nativa.
**La apariencia visual es identica a la del navegador.**

---

## 1. Instalar `uv` (una sola vez)

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Comprobar:
```bash
uv --version
```

Este proyecto exige **uv 0.12.0 o superior**.
Si tienes uno mas viejo, uv te avisa y no continua. Actualiza con:
```bash
uv self update
```

---

## 2. Instalar el proyecto

Desde la carpeta del proyecto:

```bash
uv sync
```

Esto hace 3 cosas solo:
1. Crea el entorno virtual en `.venv/`
2. Instala las librerias del `pyproject.toml`
3. Crea `uv.lock` con las versiones exactas

**No hace falta activar el entorno.** `uv` lo hace por ti.

---

## 3. Ejecutar

```bash
uv run pyzarra
```

O tambien:
```bash
uv run python -m pyzarra.main
```

---

## 4. Pasar los tests

```bash
uv run pytest
```

Los tests comprueban:
- La logica de `api.py`
- Que los metodos privados NO se exponen a JavaScript
- Que existen `index.html`, CSS y JS
- Que las rutas son relativas (si no, el .app se abre en blanco)
- Que el JS espera al evento `pywebviewready`
- Que todas las librerias tienen version fija

Con informe de cobertura:
```bash
uv run pytest --cov=pyzarra --cov-report=term-missing
```

---

## Comandos utiles

| Que quiero | Comando |
|---|---|
| Anadir una libreria | `uv add nombre-libreria` |
| Quitar una libreria | `uv remove nombre-libreria` |
| Anadir libreria de desarrollo | `uv add --dev nombre-libreria` |
| Ver librerias instaladas | `uv pip list` |
| Actualizar el lock | `uv lock --upgrade` |
| Instalar exacto que el lock | `uv sync --frozen` |
| Pasar los tests | `uv run pytest` |
| Un solo test | `uv run pytest tests/test_api.py -v` |

---

## Estructura

```
pyzarra/
├── pyproject.toml          <- ficha del proyecto + librerias + version de uv
├── uv.lock                 <- versiones exactas (lo crea uv)
├── .python-version         <- version de Python fijada (3.11)
├── .gitignore
├── README.md
├── Pyzarra.spec              <- config del .app de Mac
├── build-mac.sh
├── tests/
│   ├── conftest.py         <- fixtures compartidas
│   ├── test_api.py         <- logica Python
│   └── test_web.py         <- archivos web + rutas
└── src/
    └── pyzarra/
        ├── __init__.py
        ├── main.py         <- abre la ventana
        ├── api.py          <- LOGICA en Python
        └── web/            <- TU WEB, tal cual
            ├── index.html
            ├── css/style.css
            ├── js/app.js
            └── assets/
```

---

## Como conectar JavaScript con Python

**En Python** (`api.py`) — creas un metodo:
```python
class Api:
    def saludar(self, nombre: str) -> str:
        return f"Hola, {nombre}"
```

**En JavaScript** (`app.js`) — lo llamas:
```javascript
const texto = await window.pywebview.api.saludar("Javi");
```

**Regla clave:** espera siempre al evento `pywebviewready` antes de usar la API.

---

## Migrar tu proyecto actual

1. Copia tu HTML, CSS y JS dentro de `src/pyzarra/web/`
2. Renombra tu HTML principal a `index.html`
3. Usa **rutas relativas** (`css/style.css`, NO `/css/style.css`)
4. Mueve la logica que necesite disco, red o sistema a `api.py`

Si usas Gulp/SCSS: compila a `src/pyzarra/web/css/` y listo.

---

## Requisitos por sistema operativo

| Sistema | Motor web | Instalar algo |
|---|---|---|
| Windows | WebView2 (Edge) | Normalmente ya viene en Win 10/11 |
| macOS | WebKit | Nada, ya viene |
| Linux | GTK + WebKit2 | `sudo apt install python3-gi gir1.2-webkit2-4.1` |

---

## Empaquetar en .exe / .app

```bash
uv add --dev pyinstaller
uv run pyinstaller --noconfirm --windowed --name "Pyzarra" \
  --add-data "src/pyzarra/web:pyzarra/web" \
  src/pyzarra/main.py
```

En Windows cambia `:` por `;` en `--add-data`.


---

## Que versiones estan controladas

| Que | Donde | Valor |
|---|---|---|
| Librerias | `pyproject.toml` | `pywebview==5.3.2` |
| Versiones exactas de TODO | `uv.lock` | lo genera uv |
| Version de Python | `.python-version` | `3.11` |
| Version de la herramienta uv | `pyproject.toml` -> `[tool.uv]` | `>=0.12.0` |

Los 4 archivos deben subirse a git. Incluido `uv.lock`.
