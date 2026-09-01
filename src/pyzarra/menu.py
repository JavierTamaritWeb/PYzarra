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
            ("Nueva pizarra", "btn-tab-new"),
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


# --- macOS ---------------------------------------------------------------
#
# El set_app_menu de pywebview no retiene los objetos que hacen de target
# de cada NSMenuItem, asi que macOS los da por muertos y pinta todas las
# opciones en gris. Instalamos el menu directamente con AppKit guardando
# referencias fuertes y desactivando la auto-validacion de items.

_targets_vivos = []  # referencias fuertes a los targets de los items


def instalar_menu_cocoa() -> None:
    """Anade MENU_LAYOUT a la barra de menus nativa. Llamar en el hilo
    principal de Cocoa (AppHelper.callAfter) con la app ya arrancada."""
    import threading

    import AppKit
    import objc

    class _Target(AppKit.NSObject):
        def initConAccion_(self, accion):
            self = objc.super(_Target, self).init()
            if self is None:
                return None
            self._accion = accion
            return self

        def disparar_(self, sender):
            # Fuera del hilo principal, como hace pywebview.
            threading.Thread(target=self._accion).start()

    barra = AppKit.NSApp.mainMenu()
    for titulo, entradas in MENU_LAYOUT:
        submenu = AppKit.NSMenu.alloc().initWithTitle_(titulo)
        submenu.setAutoenablesItems_(False)
        for entrada in entradas:
            if entrada is None:
                submenu.addItem_(AppKit.NSMenuItem.separatorItem())
                continue
            etiqueta, button_id = entrada
            target = _Target.alloc().initConAccion_(_click(button_id))
            _targets_vivos.append(target)
            item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                etiqueta, "disparar:", ""
            )
            item.setTarget_(target)
            item.setEnabled_(True)
            submenu.addItem_(item)
        entrada_barra = AppKit.NSMenuItem.alloc().init()
        entrada_barra.setTitle_(titulo)
        entrada_barra.setSubmenu_(submenu)
        barra.addItem_(entrada_barra)
