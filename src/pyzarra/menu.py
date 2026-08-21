"""
Barra de menus nativa de macOS/Windows/Linux.

Cada entrada dispara el boton correspondiente de la interfaz web
(por su id en index.html), asi la logica sigue viviendo en el JS
y el menu nunca se desincroniza de lo que hace la app.
"""

from webview.menu import Menu, MenuAction, MenuSeparator

# (titulo del menu, [(etiqueta, id del boton en index.html) | None]);
# None pinta un separador.
MENU_LAYOUT = [
    (
        "Archivo",
        [
            ("Abrir proyecto…", "btn-import"),
            ("Exportar…", "btn-export"),
            None,
            ("Importar biblioteca…", "btn-library-import"),
            ("Exportar biblioteca", "btn-library-export"),
            None,
            ("Limpiar lienzo", "btn-clear"),
        ],
    ),
    (
        "Edición",
        [
            ("Deshacer", "btn-undo"),
            ("Rehacer", "btn-redo"),
            None,
            ("Duplicar selección", "btn-duplicate-sel"),
            ("Eliminar selección", "btn-delete-sel"),
            None,
            ("Agrupar", "btn-group"),
            ("Desagrupar", "btn-ungroup"),
            None,
            ("Copiar como imagen", "btn-copy-image"),
        ],
    ),
    (
        "Lienzo",
        [
            ("Ajustar zoom al contenido", "btn-zoom-fit"),
            ("Mostrar/ocultar panel", "btn-panel-toggle"),
            ("Plantillas…", "btn-templates"),
            ("Guardar pieza…", "btn-save-piece"),
        ],
    ),
    (
        "Ayuda",
        [
            ("Atajos y trucos…", "btn-help"),
        ],
    ),
]


def _click(button_id: str):
    """Devuelve la accion que pulsa ese boton de la web."""

    def accion():
        import webview

        if webview.windows:
            webview.windows[0].evaluate_js(
                f'document.getElementById("{button_id}")?.click()'
            )

    return accion


def build_menu() -> list[Menu]:
    menus = []
    for titulo, entradas in MENU_LAYOUT:
        items = []
        for entrada in entradas:
            if entrada is None:
                items.append(MenuSeparator())
            else:
                etiqueta, button_id = entrada
                items.append(MenuAction(etiqueta, _click(button_id)))
        menus.append(Menu(titulo, items))
    return menus
