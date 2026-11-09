"""Janela principal: menus, barras de ferramentas, painéis e as três cenas
(ecrã inicial, editor e ajuda)."""

from __future__ import annotations

import os

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (QApplication, QDockWidget, QFileDialog, QLabel, QMainWindow, QMenu,
                               QMessageBox, QProgressDialog, QStackedWidget, QToolBar, QVBoxLayout,
                               QWidget)

from .. import APP_NAME, FILE_EXT, FILE_FILTER, ORG_NAME, __version__
from ..controller import EditorController
from ..core.examples import EXAMPLES
from ..render.exporter import export_gif, render_image, save_image
from .canvas import Canvas
from .export_dialogs import GifExportDialog, ImageExportDialog
from .help_screen import HelpScreen
from .icons import icon
from .layers_panel import LayersPanel
from .properties_panel import PropertiesPanel
from .start_screen import StartScreen
from .widgets import ColorButton, PaletteBar

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif")
PAGE_START, PAGE_EDITOR, PAGE_HELP = 0, 1, 2


class MainWindow(QMainWindow):
    def __init__(self, ctl: EditorController | None = None):
        super().__init__()
        self.ctl = ctl or EditorController()
        self.settings = QSettings(ORG_NAME, "EditorGeometrico")
        self.setWindowIcon(icon("logo"))
        self.setAcceptDrops(True)
        self.resize(1440, 880)
        self.setMinimumSize(900, 600)
        self._previous_page = PAGE_START
        self._gl_warned = False

        self.canvas = Canvas(self.ctl)
        self.start = StartScreen()
        self.help = HelpScreen()
        editor_page = QWidget()
        lay = QVBoxLayout(editor_page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.start)
        self.stack.addWidget(editor_page)
        self.stack.addWidget(self.help)
        self.setCentralWidget(self.stack)

        self._make_actions()
        self._make_menus()
        self._make_toolbars()
        self._make_docks()
        self._make_status()
        self._connect()
        self._update_title()
        self._update_history_actions()
        self.show_start()

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------
    def _act(self, text, slot, shortcut=None, icon_name=None, checkable=False, tip=None,
             canvas_only=False) -> QAction:
        a = QAction(text, self)
        if icon_name:
            a.setIcon(icon(icon_name))
        if shortcut:
            keys = shortcut if isinstance(shortcut, (list, tuple)) else [shortcut]
            a.setShortcuts([QKeySequence(k) for k in keys])
        a.setCheckable(checkable)
        if tip:
            a.setToolTip(tip)
            a.setStatusTip(tip)
        elif shortcut:
            a.setToolTip(f"{text.replace('&', '').replace('…', '')} ({a.shortcut().toString()})")
        if canvas_only:
            # teclas simples só funcionam com o foco no canvas (não interferem com campos de texto)
            a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            self.canvas.addAction(a)
        else:
            self.addAction(a)
        if checkable:
            a.toggled.connect(slot)
        else:
            a.triggered.connect(lambda _checked=False: slot())
        return a

    def _make_actions(self) -> None:
        c = self.ctl
        A = self._act
        # Ficheiro
        self.a_new = A("&Novo", self.new_project, "Ctrl+N", "new")
        self.a_open = A("&Abrir…", self.open_project, "Ctrl+O", "open")
        self.a_save = A("&Guardar", self.save, "Ctrl+S", "save")
        self.a_save_as = A("Guardar &como…", self.save_as, "Ctrl+Shift+S")
        self.a_import = A("&Importar imagem…", self.import_image, "Ctrl+I", "image",
                          tip="Importar imagem PNG/JPG (Ctrl+I)")
        self.a_export = A("&Exportar imagem…", self.export_image, "Ctrl+E", "export",
                          tip="Exportar imagem PNG/JPG (Ctrl+E)")
        self.a_gif = A("Exportar animação &GIF…", self.export_gif, "Ctrl+Shift+E", "gif",
                       tip="Exportar a animação como GIF (Ctrl+Shift+E)")
        self.a_home = A("Ecrã &inicial", self.show_start, None, "home")
        self.a_quit = A("&Sair", self.close, "Ctrl+Q")
        # Editar
        self.a_undo = A("&Desfazer", c.undo, "Ctrl+Z", "undo")
        self.a_redo = A("&Refazer", c.redo, ["Ctrl+Y", "Ctrl+Shift+Z"], "redo")
        self.a_cut = A("Cor&tar", c.cut_selection, "Ctrl+X", canvas_only=True)
        self.a_copy = A("&Copiar", c.copy_selection, "Ctrl+C", canvas_only=True)
        self.a_paste = A("C&olar", c.paste, "Ctrl+V", canvas_only=True)
        self.a_dup = A("D&uplicar", c.duplicate_selection, "Ctrl+D", "duplicate")
        self.a_del = A("&Apagar", c.delete_selection, "Delete", "delete", canvas_only=True)
        self.a_all = A("Selecionar &tudo", c.select_all, "Ctrl+A", canvas_only=True)
        # Objeto
        self.a_group = A("&Agrupar", c.group_selection, "Ctrl+G", "group")
        self.a_ungroup = A("&Desagrupar", c.ungroup_selection, "Ctrl+Shift+G", "ungroup")
        self.a_front = A("Trazer para a &frente", lambda: c.reorder("front"), "Ctrl+Shift+Up", "front")
        self.a_forward = A("A&vançar", lambda: c.reorder("forward"), "Ctrl+Up")
        self.a_backward = A("&Recuar", lambda: c.reorder("backward"), "Ctrl+Down")
        self.a_back = A("Enviar para &trás", lambda: c.reorder("back"), "Ctrl+Shift+Down", "back")
        self.a_rot_m = A("Rodar −15°", lambda: c.rotate_selection(-15), ",", canvas_only=True)
        self.a_rot_p = A("Rodar +15°", lambda: c.rotate_selection(15), ".", "rotate", canvas_only=True)
        self.a_bigger = A("Aumentar 10 %", lambda: c.scale_selection(1.1), ["+", "="], canvas_only=True)
        self.a_smaller = A("Diminuir 10 %", lambda: c.scale_selection(1 / 1.1), "-", canvas_only=True)
        self.a_flip_h = A("Espelhar &horizontal", lambda: c.flip_selection(True), "Shift+H", "flip_h",
                          canvas_only=True)
        self.a_flip_v = A("Espelhar &vertical", lambda: c.flip_selection(False), "Shift+V", "flip_v",
                          canvas_only=True)
        self.a_reset_tf = A("Repor transformação", c.reset_transform)
        for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, 1), ("Down", 0, -1)):
            A(f"Mover {key}", lambda dx=dx, dy=dy: c.nudge(dx, dy), key, canvas_only=True)
            A(f"Mover {key} 10", lambda dx=dx, dy=dy: c.nudge(10 * dx, 10 * dy), f"Shift+{key}", canvas_only=True)
        # Camadas
        self.a_layer_new = A("&Nova camada", c.add_layer, "Ctrl+Shift+N", "add")
        self.a_layer_dup = A("&Duplicar camada", c.duplicate_layer, None, "duplicate")
        self.a_layer_del = A("&Apagar camada", c.delete_layer, None, "delete")
        self.a_layer_up = A("&Subir camada", lambda: c.move_layer(+1), None, "up")
        self.a_layer_down = A("D&escer camada", lambda: c.move_layer(-1), None, "down")
        # Ver
        self.a_fit = A("&Ajustar à janela", self.canvas.fit_view, "Ctrl+0", "fit")
        self.a_100 = A("Zoom &100 %", self.canvas.zoom_100, "Ctrl+1")
        self.a_zin = A("Apro&ximar", lambda: self.canvas.zoom_step(1.25), ["Ctrl++", "Ctrl+="])
        self.a_zout = A("A&fastar", lambda: self.canvas.zoom_step(0.8), "Ctrl+-")
        self.a_grid = A("Mostrar &grelha", self._toggle_grid, "G", "grid", checkable=True, canvas_only=True)
        self.a_snap = A("Ajustar à g&relha", self._toggle_snap, "Shift+G", "magnet", checkable=True,
                        canvas_only=True)
        self.a_minimap = A("&Minimapa (2.º viewport)", self._toggle_minimap, "M", "minimap", checkable=True,
                           canvas_only=True)
        self.a_aspect = A("Manter &proporção (janela→visor sem distorção)", self._toggle_aspect, None,
                          "aspect", checkable=True,
                          tip="Desligue para ver a distorção quando a janela muda de forma (demonstração)")
        self.a_clip = A("&Recortar à prancheta", self._toggle_clip, None, checkable=True,
                        tip="Esconde o que fica fora da prancheta (como na imagem exportada)")
        self.a_clip.setChecked(c.clip_to_artboard)
        self.a_grid.setChecked(c.show_grid)
        self.a_snap.setChecked(c.snap_to_grid)
        self.a_minimap.setChecked(c.show_minimap)
        self.a_aspect.setChecked(True)
        # Animação
        self.a_play = A("&Reproduzir / parar", c.toggle_animation, "F5", "play",
                        tip="Reproduzir ou parar a animação (F5)")
        self.a_anim_reset = A("Voltar ao &início (t = 0)", c.reset_animation, "Shift+F5")
        # Ajuda
        self.a_help = A("&Ajuda e atalhos", self.show_help, "F1", "help")
        self.a_about = A("&Sobre", self.about)
        # Ferramentas
        self.tool_group = QActionGroup(self)
        self.tool_actions: dict[str, QAction] = {}
        for name, tool in self.canvas.tools.items():
            a = A(f"{tool.label}", lambda n=name: self.canvas.set_tool(n), tool.shortcut, tool.icon,
                  tip=f"{tool.label} ({tool.shortcut})\n{tool.hint}", canvas_only=True)
            a.setCheckable(True)
            self.tool_group.addAction(a)
            self.tool_actions[name] = a
        self.tool_actions["select"].setChecked(True)

    def _make_menus(self) -> None:
        mb = self.menuBar()
        m = mb.addMenu("&Ficheiro")
        m.addActions([self.a_new, self.a_open])
        ex = m.addMenu(icon("layers"), "&Exemplos")
        for i, (name, desc, _b) in enumerate(EXAMPLES):
            a = ex.addAction(f"{name} — {desc}")
            a.triggered.connect(lambda _c=False, k=i: self.open_example(k))
        self.recent_menu = m.addMenu("Abrir &recente")
        self.recent_menu.aboutToShow.connect(self._fill_recent)
        m.addSeparator()
        m.addActions([self.a_save, self.a_save_as])
        m.addSeparator()
        m.addActions([self.a_import, self.a_export, self.a_gif])
        m.addSeparator()
        m.addActions([self.a_home, self.a_quit])

        m = mb.addMenu("&Editar")
        m.addActions([self.a_undo, self.a_redo])
        m.addSeparator()
        m.addActions([self.a_cut, self.a_copy, self.a_paste, self.a_dup, self.a_del])
        m.addSeparator()
        m.addAction(self.a_all)

        m = mb.addMenu("&Objeto")
        m.addActions([self.a_group, self.a_ungroup])
        m.addSeparator()
        m.addActions([self.a_front, self.a_forward, self.a_backward, self.a_back])
        m.addSeparator()
        m.addActions([self.a_rot_m, self.a_rot_p, self.a_bigger, self.a_smaller, self.a_flip_h, self.a_flip_v,
                      self.a_reset_tf])

        m = mb.addMenu("&Camadas")
        m.addActions([self.a_layer_new, self.a_layer_dup, self.a_layer_del])
        m.addSeparator()
        m.addActions([self.a_layer_up, self.a_layer_down])
        m.addSeparator()
        self.move_menu = m.addMenu("&Mover seleção para…")
        self.move_menu.aboutToShow.connect(lambda: self._fill_move_menu(self.move_menu))

        m = mb.addMenu("&Ver")
        m.addActions([self.a_fit, self.a_100, self.a_zin, self.a_zout])
        m.addSeparator()
        m.addActions([self.a_grid, self.a_snap, self.a_minimap, self.a_clip, self.a_aspect])
        self.view_menu = m

        m = mb.addMenu("&Animação")
        m.addActions([self.a_play, self.a_anim_reset])
        m.addSeparator()
        m.addAction(self.a_gif)

        m = mb.addMenu("A&juda")
        m.addActions([self.a_help, self.a_about])

        tools_menu = mb.addMenu("Ferra&mentas")
        tools_menu.addActions(list(self.tool_actions.values()))

    def _make_toolbars(self) -> None:
        tb = QToolBar("Ferramentas")
        tb.setObjectName("tools")
        tb.setOrientation(Qt.Orientation.Vertical)
        tb.setMovable(False)
        tb.setIconSize(tb.iconSize() * 1.15)
        for name in ("select", "hand"):
            tb.addAction(self.tool_actions[name])
        tb.addSeparator()
        for name in ("rect", "ellipse", "triangle", "line", "polygon", "freehand", "ngon", "star"):
            tb.addAction(self.tool_actions[name])
        tb.addSeparator()
        tb.addAction(self.a_import)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tb)
        self.tools_bar = tb

        top = QToolBar("Principal")
        top.setObjectName("main")
        top.setMovable(False)
        top.addActions([self.a_new, self.a_open, self.a_save])
        top.addSeparator()
        top.addActions([self.a_undo, self.a_redo])
        top.addSeparator()
        top.addActions([self.a_group, self.a_ungroup, self.a_front, self.a_back, self.a_flip_h, self.a_flip_v])
        top.addSeparator()
        top.addAction(self.a_play)
        top.addActions([self.a_export, self.a_gif])
        top.addSeparator()
        top.addActions([self.a_fit, self.a_grid, self.a_snap, self.a_minimap, self.a_aspect])
        top.addSeparator()
        lbl = QLabel(" Cores ")
        lbl.setObjectName("muted")
        top.addWidget(lbl)
        self.fill_default = ColorButton(self.ctl.fill_color, "Cor de preenchimento")
        self.fill_default.setToolTip("Cor de preenchimento: aplica-se à seleção e às formas novas")
        self.stroke_default = ColorButton(self.ctl.stroke_color, "Cor do contorno")
        self.stroke_default.setToolTip("Cor do contorno: aplica-se à seleção e às formas novas")
        top.addWidget(self.fill_default)
        top.addWidget(self.stroke_default)
        self.a_auto = QAction("Auto", self)
        self.a_auto.setCheckable(True)
        self.a_auto.setChecked(self.ctl.auto_colors)
        self.a_auto.setToolTip("Cores automáticas: cada forma nova recebe a próxima cor da paleta")
        self.a_auto.toggled.connect(lambda on: setattr(self.ctl, "auto_colors", on))
        top.addAction(self.a_auto)
        self.palette = PaletteBar()
        top.addWidget(self.palette)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, top)
        self.main_bar = top

    def _make_docks(self) -> None:
        self.layers = LayersPanel(self.ctl)
        self.props = PropertiesPanel(self.ctl)
        self.dock_layers = QDockWidget("Camadas", self)
        self.dock_layers.setObjectName("dock_layers")
        self.dock_layers.setWidget(self.layers)
        self.dock_props = QDockWidget("Propriedades", self)
        self.dock_props.setObjectName("dock_props")
        self.dock_props.setWidget(self.props)
        for d in (self.dock_layers, self.dock_props):
            d.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable
                          | QDockWidget.DockWidgetFeature.DockWidgetClosable)
            d.setMinimumWidth(370)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_layers)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_props)
        self.splitDockWidget(self.dock_layers, self.dock_props, Qt.Orientation.Vertical)
        self.resizeDocks([self.dock_layers, self.dock_props], [300, 520], Qt.Orientation.Vertical)
        self.resizeDocks([self.dock_layers], [380], Qt.Orientation.Horizontal)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.dock_layers.toggleViewAction())
        self.view_menu.addAction(self.dock_props.toggleViewAction())

    def _make_status(self) -> None:
        sb = self.statusBar()
        self.hint_label = QLabel()
        self.coords_label = QLabel("x: —  y: —")
        self.view_label = QLabel()
        self.zoom_label = QLabel()
        sb.addWidget(self.hint_label, 1)
        sb.addPermanentWidget(self.coords_label)
        sb.addPermanentWidget(self.view_label)
        sb.addPermanentWidget(self.zoom_label)

    def _connect(self) -> None:
        c = self.ctl
        c.message.connect(lambda m: self.statusBar().showMessage(m, 6000))
        c.fileStateChanged.connect(self._update_title)
        c.historyChanged.connect(self._update_history_actions)
        c.animationChanged.connect(self._on_animation)
        c.selectionChanged.connect(self._update_selection_actions)
        self.canvas.cursorMoved.connect(lambda x, y: self.coords_label.setText(f"x: {x:8.1f}   y: {y:8.1f}"))
        self.canvas.viewChanged.connect(self._update_view_labels)
        self.canvas.toolChanged.connect(self._on_tool_changed)
        self.canvas.contextMenuRequested.connect(self._context_menu)
        self.canvas.glFailed.connect(self._gl_failed)
        self.start.newRequested.connect(self.new_project)
        self.start.openRequested.connect(self.open_project)
        self.start.exampleRequested.connect(self.open_example)
        self.start.helpRequested.connect(self.show_help)
        self.start.quitRequested.connect(self.close)
        self.help.backRequested.connect(self._help_back)
        self.fill_default.colorChosen.connect(self._default_fill)
        self.stroke_default.colorChosen.connect(self._default_stroke)
        self.palette.fillPicked.connect(self._default_fill)
        self.palette.strokePicked.connect(self._default_stroke)
        self._update_selection_actions()

    # ------------------------------------------------------------------
    # Cenas
    # ------------------------------------------------------------------
    def _set_editor_chrome(self, visible: bool) -> None:
        for w in (self.tools_bar, self.main_bar, self.dock_layers, self.dock_props):
            w.setVisible(visible)
        self.statusBar().setVisible(visible)

    def show_start(self) -> None:
        self.ctl.stop_animation()
        self.stack.setCurrentIndex(PAGE_START)
        self._set_editor_chrome(False)

    def show_editor(self) -> None:
        self.stack.setCurrentIndex(PAGE_EDITOR)
        self._set_editor_chrome(True)
        self.canvas.setFocus()
        self._on_tool_changed(self.canvas.tool.name)

    def show_help(self) -> None:
        if self.stack.currentIndex() != PAGE_HELP:
            self._previous_page = self.stack.currentIndex()
        self.ctl.stop_animation()
        self.stack.setCurrentIndex(PAGE_HELP)
        self._set_editor_chrome(False)

    def _help_back(self) -> None:
        if self._previous_page == PAGE_EDITOR:
            self.show_editor()
        else:
            self.show_start()

    # ------------------------------------------------------------------
    # Ficheiros
    # ------------------------------------------------------------------
    def _last_dir(self) -> str:
        return str(self.settings.value("last_dir", os.path.expanduser("~")))

    def _remember(self, path: str) -> None:
        self.settings.setValue("last_dir", os.path.dirname(path))
        recent = [p for p in (self.settings.value("recent", []) or []) if p != path]
        self.settings.setValue("recent", ([path] + recent)[:8])

    def _fill_recent(self) -> None:
        self.recent_menu.clear()
        recent = [p for p in (self.settings.value("recent", []) or []) if os.path.exists(p)]
        if not recent:
            a = self.recent_menu.addAction("(vazio)")
            a.setEnabled(False)
        for p in recent:
            self.recent_menu.addAction(os.path.basename(p), lambda _c=False, path=p: self.open_project(path))

    def maybe_save(self) -> bool:
        if not self.ctl.dirty:
            return True
        r = QMessageBox.question(
            self, "Alterações por guardar", "O projeto tem alterações que ainda não foram guardadas.\nGuardar agora?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if r == QMessageBox.StandardButton.Save:
            return self.save()
        return r == QMessageBox.StandardButton.Discard

    def new_project(self) -> None:
        if self.maybe_save():
            self.ctl.new_document()
            self.show_editor()
            self.statusBar().showMessage("Projeto novo. Escolha uma ferramenta à esquerda e desenhe na prancheta.", 6000)

    def open_project(self, path: str | None = None) -> None:
        if not self.maybe_save():
            return
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, "Abrir projeto", self._last_dir(), FILE_FILTER)
            if not path:
                return
        try:
            self.ctl.open_file(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Abrir projeto", f"Não foi possível abrir o ficheiro:\n{e}")
            return
        self._remember(path)
        self.show_editor()

    def open_example(self, index: int) -> None:
        if not self.maybe_save():
            return
        name, desc, build = EXAMPLES[index]
        self.ctl.set_document(build())
        self.show_editor()
        self.statusBar().showMessage(f"Exemplo '{name}': {desc}. Prima F5 para ver a animação.", 8000)

    def save(self) -> bool:
        if not self.ctl.file_path:
            return self.save_as()
        return self._save_to(self.ctl.file_path)

    def save_as(self) -> bool:
        start = self.ctl.file_path or os.path.join(self._last_dir(), "desenho" + FILE_EXT)
        path, _f = QFileDialog.getSaveFileName(self, "Guardar projeto", start, FILE_FILTER)
        if not path:
            return False
        if not os.path.splitext(path)[1]:
            path += FILE_EXT
        return self._save_to(path)

    def _save_to(self, path: str) -> bool:
        try:
            self.ctl.save_file(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Guardar", f"Não foi possível guardar:\n{e}")
            return False
        self._remember(path)
        return True

    def import_image(self, path: str | None = None) -> None:
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, "Importar imagem", self._last_dir(),
                                                   "Imagens (*.png *.jpg *.jpeg *.bmp *.gif)")
            if not path:
                return
        if self.stack.currentIndex() != PAGE_EDITOR:
            self.show_editor()
        try:
            self.ctl.import_image(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Importar imagem", f"Não foi possível abrir a imagem:\n{e}")
            return
        self.settings.setValue("last_dir", os.path.dirname(path))
        self.canvas.set_tool("select")

    def export_image(self) -> None:
        dlg = ImageExportDialog(self.ctl, self)
        if not dlg.exec():
            return
        base = os.path.splitext(os.path.basename(self.ctl.file_path or "desenho"))[0]
        path, _f = QFileDialog.getSaveFileName(self, "Exportar imagem", os.path.join(self._last_dir(), base + ".png"),
                                               "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)")
        if not path:
            return
        if not os.path.splitext(path)[1]:
            path += ".png"
        w, h = dlg.image_size()
        transparent = dlg.transparent.isChecked() and path.lower().endswith(".png")
        try:
            self.canvas.makeCurrent()
            img = render_image(self.canvas.renderer, self.ctl.doc, dlg.region(), w, h, transparent=transparent)
            self.canvas.doneCurrent()
            save_image(img, path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Exportar imagem", f"Falhou a exportação:\n{e}")
            return
        self.settings.setValue("last_dir", os.path.dirname(path))
        self.statusBar().showMessage(f"Imagem exportada ({w}×{h}): {path}", 8000)

    def export_gif(self) -> None:
        if not self.ctl.has_animation():
            r = QMessageBox.question(self, "Exportar GIF",
                                     "Nenhum objeto tem animação, por isso o GIF ficará parado.\n"
                                     "Defina animações em Propriedades → Animação. Exportar mesmo assim?")
            if r != QMessageBox.StandardButton.Yes:
                return
        dlg = GifExportDialog(self.ctl, self)
        if not dlg.exec():
            return
        base = os.path.splitext(os.path.basename(self.ctl.file_path or "animacao"))[0]
        path, _f = QFileDialog.getSaveFileName(self, "Exportar animação GIF",
                                               os.path.join(self._last_dir(), base + ".gif"), "GIF animado (*.gif)")
        if not path:
            return
        if not path.lower().endswith(".gif"):
            path += ".gif"
        self.ctl.stop_animation()
        prog = QProgressDialog("A desenhar os quadros da animação…", "Cancelar", 0, 100, self)
        prog.setWindowTitle("Exportar GIF")
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        prog.setMinimumDuration(0)

        def progress(i, n):
            prog.setMaximum(n)
            prog.setValue(i)
            QApplication.processEvents()
            self.canvas.makeCurrent()
            return not prog.wasCanceled()

        try:
            self.canvas.makeCurrent()
            n = export_gif(self.canvas.renderer, self.ctl.doc, path, dlg.width_.value(), dlg.duration.value(),
                           dlg.fps.value(), region=dlg.region(), progress=progress)
            self.canvas.doneCurrent()
        except Exception as e:  # noqa: BLE001
            prog.close()
            QMessageBox.warning(self, "Exportar GIF", f"Falhou a exportação:\n{e}")
            return
        prog.close()
        if n:
            self.settings.setValue("last_dir", os.path.dirname(path))
            self.statusBar().showMessage(f"GIF exportado com {n} quadros: {path}", 8000)
        else:
            self.statusBar().showMessage("Exportação do GIF cancelada.", 5000)

    # ------------------------------------------------------------------
    # Reações
    # ------------------------------------------------------------------
    def _update_title(self) -> None:
        name = os.path.basename(self.ctl.file_path) if self.ctl.file_path else "Sem título"
        self.setWindowTitle(f"{name}[*] — {APP_NAME}")
        self.setWindowModified(self.ctl.dirty)

    def _update_history_actions(self) -> None:
        h = self.ctl.history
        self.a_undo.setEnabled(h.can_undo())
        self.a_redo.setEnabled(h.can_redo())
        self.a_undo.setText(f"&Desfazer {h.undo_label()}".strip())
        self.a_redo.setText(f"&Refazer {h.redo_label()}".strip())

    def _update_selection_actions(self) -> None:
        has = bool(self.ctl.selection)
        for a in (self.a_cut, self.a_copy, self.a_dup, self.a_del, self.a_front, self.a_forward, self.a_backward,
                  self.a_back, self.a_flip_h, self.a_flip_v, self.a_reset_tf, self.a_ungroup):
            a.setEnabled(has)
        self.a_group.setEnabled(len(self.ctl.selection) >= 2)

    def _update_view_labels(self) -> None:
        cam = self.canvas.camera
        left, right, bottom, top = cam.window()
        sx, sy = cam.scale_factors()
        uniform = "uniforme" if not cam.is_distorted() else "DISTORCIDA"
        self.view_label.setText(f"Janela {right - left:.0f}×{top - bottom:.0f} → visor {cam.vw}×{cam.vh} px "
                                f"· escala {sx:.2f}/{sy:.2f} ({uniform})")
        self.zoom_label.setText(f"Zoom {cam.zoom * 100:.0f}%")

    def _on_tool_changed(self, name: str) -> None:
        a = self.tool_actions.get(name)
        if a is not None and not a.isChecked():
            a.setChecked(True)
        tool = self.canvas.tools[name]
        self.hint_label.setText(f"{tool.label}: {tool.hint}")

    def _on_animation(self, playing: bool) -> None:
        self.a_play.setIcon(icon("stop" if playing else "play"))
        self.a_play.setText("&Parar animação" if playing else "&Reproduzir animação")

    def _toggle_grid(self, on: bool) -> None:
        self.ctl.show_grid = on
        self.ctl.viewOptionsChanged.emit()

    def _toggle_snap(self, on: bool) -> None:
        self.ctl.snap_to_grid = on
        self.ctl.viewOptionsChanged.emit()
        self.statusBar().showMessage("Ajustar à grelha: " + ("ligado" if on else "desligado"), 3000)

    def _toggle_minimap(self, on: bool) -> None:
        self.ctl.show_minimap = on
        self.ctl.viewOptionsChanged.emit()

    def _toggle_clip(self, on: bool) -> None:
        self.ctl.clip_to_artboard = on
        self.ctl.viewOptionsChanged.emit()

    def _toggle_aspect(self, on: bool) -> None:
        self.canvas.set_keep_aspect(on)
        if not on:
            self.statusBar().showMessage("Demonstração: redimensione a janela para ver o desenho esticar "
                                         "(escala diferente em x e y).", 8000)

    def _default_fill(self, rgba) -> None:
        self.ctl.fill_color = tuple(rgba)
        self.ctl.auto_colors = False
        self.a_auto.setChecked(False)
        self.fill_default.set_rgba(rgba)
        self.ctl.apply_fill(rgba)

    def _default_stroke(self, rgba) -> None:
        self.ctl.stroke_color = tuple(rgba)
        self.stroke_default.set_rgba(rgba)
        self.ctl.apply_stroke(rgba)

    def _fill_move_menu(self, menu: QMenu) -> None:
        menu.clear()
        for layer in reversed(self.ctl.doc.layers):
            a = menu.addAction(layer.name, lambda _c=False, L=layer: self.ctl.move_selection_to_layer(L))
            a.setEnabled(bool(self.ctl.selection))

    def _context_menu(self, global_pos) -> None:
        m = QMenu(self)
        if self.ctl.selection:
            m.addActions([self.a_cut, self.a_copy, self.a_paste, self.a_dup, self.a_del])
            m.addSeparator()
            m.addActions([self.a_group, self.a_ungroup])
            order = m.addMenu("Ordem")
            order.addActions([self.a_front, self.a_forward, self.a_backward, self.a_back])
            tf = m.addMenu("Transformar")
            tf.addActions([self.a_rot_m, self.a_rot_p, self.a_bigger, self.a_smaller, self.a_flip_h,
                           self.a_flip_v, self.a_reset_tf])
            mv = m.addMenu("Mover para a camada")
            self._fill_move_menu(mv)
        else:
            m.addActions([self.a_paste, self.a_all])
            m.addSeparator()
            m.addActions([self.a_import, self.a_fit])
        m.addSeparator()
        m.addAction(self.a_play)
        m.exec(global_pos)

    def _gl_failed(self, error: str) -> None:
        if self._gl_warned:
            return
        self._gl_warned = True
        QMessageBox.critical(self, "OpenGL",
                             "Não foi possível iniciar o OpenGL neste computador:\n"
                             f"{error}\n\nFeche o editor e abra-o com a opção --software-gl "
                             "(OpenGL por software, mais lento mas compatível).")

    def about(self) -> None:
        info = self.canvas.renderer.info or {}
        QMessageBox.about(self, f"Sobre — {APP_NAME}",
                          f"<h3>{APP_NAME} {__version__}</h3>"
                          "<p>Trabalho Prático Final de Computação Gráfica — Grupo 5.<br>"
                          "Editor gráfico e modelador geométrico 2D.</p>"
                          "<p>Python · PyOpenGL · PySide6 (Qt) · NumPy · Pillow</p>"
                          f"<p>OpenGL: {info.get('versao', '—')}<br>{info.get('renderizador', '')}</p>")

    # ------------------------------------------------------------------
    # Arrastar ficheiros para a janela e fechar
    # ------------------------------------------------------------------
    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e) -> None:
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            low = path.lower()
            if low.endswith((FILE_EXT, ".json")):
                self.open_project(path)
                return
            if low.endswith(IMAGE_EXTS):
                self.import_image(path)

    def closeEvent(self, e) -> None:
        if self.maybe_save():
            self.ctl.stop_animation()
            e.accept()
        else:
            e.ignore()
