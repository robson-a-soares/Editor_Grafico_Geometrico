"""Textos do próprio Qt em português europeu.

Os botões padrão (OK/Cancelar, Guardar/Descartar, Sim/Não), o seletor de cores e os
menus de contexto dos campos de texto vêm do Qt em inglês. Este tradutor responde a
esses textos em português de Portugal/Moçambique; o que não estiver na tabela passa para
a tradução oficial do Qt (português do Brasil), se existir, e por fim fica o original.
"""

from __future__ import annotations

from PySide6.QtCore import QLibraryInfo, QTranslator

_PT = {
    "QPlatformTheme": {
        "OK": "OK", "Save": "Guardar", "Save All": "Guardar tudo", "Open": "Abrir",
        "&Yes": "&Sim", "Yes to &All": "Sim para &todos", "&No": "&Não", "N&o to All": "Nã&o para todos",
        "Abort": "Abortar", "Retry": "Tentar de novo", "Ignore": "Ignorar", "Close": "Fechar",
        "Cancel": "Cancelar", "Discard": "Descartar", "Help": "Ajuda", "Apply": "Aplicar", "Reset": "Repor",
        "Restore Defaults": "Repor predefinições", "Don't Save": "Não guardar",
        "Close without Saving": "Fechar sem guardar",
    },
    "QColorDialog": {
        "Hu&e:": "&Matiz:", "&Sat:": "&Sat:", "&Val:": "&Val:", "&Red:": "Ve&rmelho:", "&Green:": "&Verde:",
        "Bl&ue:": "Az&ul:", "A&lpha channel:": "&Opacidade:", "&HTML:": "&HTML:",
        "&Basic colors": "Cores &básicas", "&Custom colors": "Cores &personalizadas",
        "&Add to Custom Colors": "&Adicionar às cores personalizadas",
        "&Pick Screen Color": "&Escolher cor do ecrã", "Select Color": "Escolher cor",
        "Cursor at %1, %2\nPress ESC to cancel": "Cursor em %1, %2\nPrima Esc para cancelar",
    },
    "QLineEdit": {
        "&Undo": "&Desfazer", "&Redo": "&Refazer", "Cu&t": "Cor&tar", "&Copy": "&Copiar", "&Paste": "Co&lar",
        "Delete": "Eliminar", "Select All": "Selecionar tudo",
    },
    "QWidgetTextControl": {
        "&Undo": "&Desfazer", "&Redo": "&Refazer", "Cu&t": "Cor&tar", "&Copy": "&Copiar", "&Paste": "Co&lar",
        "Delete": "Eliminar", "Select All": "Selecionar tudo",
    },
    "QAbstractSpinBox": {"&Select All": "&Selecionar tudo", "&Step up": "&Aumentar", "Step &down": "&Diminuir"},
    "QMessageBox": {"Show Details...": "Mostrar detalhes…", "Hide Details...": "Ocultar detalhes…"},
}


class _PortugueseTranslator(QTranslator):
    def translate(self, context, source, disambiguation=None, n=-1):  # noqa: ARG002
        table = _PT.get(context)
        # None = "sem tradução": o Qt passa ao tradutor seguinte (um texto vazio apagaria o original)
        return table.get(source) if table else None


def install_translations(app) -> None:
    """Instala a tradução oficial do Qt (se existir) e, por cima, a tabela em português europeu."""
    keep = []
    base = QTranslator(app)
    if base.load("qtbase_pt_BR", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        app.installTranslator(base)
        keep.append(base)
    pt = _PortugueseTranslator(app)
    app.installTranslator(pt)   # o último instalado é consultado primeiro
    keep.append(pt)
    app._translators = keep     # mantém as referências vivas
