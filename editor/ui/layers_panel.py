"""Painel de camadas: árvore camadas → objetos → filhos dos grupos."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QMenu, QSlider, QToolButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ..core.document import Layer
from ..core.shapes import GroupShape
from .icons import icon

ROLE = Qt.ItemDataRole.UserRole
KIND_ICON = {"retangulo": "rect", "elipse": "ellipse", "triangulo": "triangle", "poligono_regular": "ngon",
             "caminho": "polygon", "imagem": "image", "grupo": "group"}


class LayersPanel(QWidget):
    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl
        self._building = False
        self._items: dict[str, QTreeWidgetItem] = {}
        self._collapsed: set[str] = set()
        self._pending = False

        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(6)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                  | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.tree.setIndentation(14)
        self.tree.header().setStretchLastSection(False)
        self.tree.setColumnWidth(1, 26)
        self.tree.setColumnWidth(2, 26)
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        v.addWidget(self.tree, 1)

        row = QHBoxLayout()
        row.setSpacing(2)
        for name, tip, slot in (("add", "Nova camada", ctl.add_layer),
                                ("duplicate", "Duplicar camada", ctl.duplicate_layer),
                                ("up", "Subir camada", lambda: ctl.move_layer(+1)),
                                ("down", "Descer camada", lambda: ctl.move_layer(-1)),
                                ("delete", "Apagar camada", ctl.delete_layer)):
            b = QToolButton()
            b.setIcon(icon(name))
            b.setToolTip(tip)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)

        op = QHBoxLayout()
        self.op_label = QLabel("Opacidade da camada")
        self.op_label.setObjectName("muted")
        self.op_slider = QSlider(Qt.Orientation.Horizontal)
        self.op_slider.setRange(0, 100)
        self.op_value = QLabel("100%")
        self.op_value.setMinimumWidth(36)
        op.addWidget(self.op_label)
        op.addWidget(self.op_slider, 1)
        op.addWidget(self.op_value)
        v.addLayout(op)

        self.tree.itemSelectionChanged.connect(self._on_tree_selection)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemExpanded.connect(lambda it: self._collapsed.discard(self._key(it)))
        self.tree.itemCollapsed.connect(lambda it: self._collapsed.add(self._key(it)))
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.op_slider.valueChanged.connect(self._on_opacity)
        ctl.structureChanged.connect(self.schedule_rebuild)
        ctl.documentReplaced.connect(self._on_doc_replaced)
        ctl.selectionChanged.connect(self._sync_selection)
        ctl.objectsChanged.connect(self._sync_opacity)
        self.rebuild()

    # ------------------------------------------------------------------
    def _key(self, item: QTreeWidgetItem) -> str:
        data = item.data(0, ROLE)
        return data[1] if data else ""

    def _on_doc_replaced(self) -> None:
        self._collapsed.clear()
        self.schedule_rebuild()

    def schedule_rebuild(self) -> None:
        if not self._pending:
            self._pending = True
            QTimer.singleShot(0, self.rebuild)

    def rebuild(self) -> None:
        self._pending = False
        self._building = True
        self.tree.clear()
        self._items.clear()
        doc = self.ctl.doc
        active = doc.active_layer_id
        bold = QFont()
        bold.setBold(True)
        for layer in reversed(doc.layers):
            it = QTreeWidgetItem([layer.name, "", ""])
            it.setData(0, ROLE, ("layer", layer.id))
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
            it.setIcon(0, icon("layers"))
            it.setFont(0, bold)
            it.setIcon(1, icon("eye" if layer.visible else "eye_off"))
            it.setIcon(2, icon("lock" if layer.locked else "unlock"))
            it.setToolTip(0, f"{layer.name} — {len(layer.objects)} objeto(s)"
                             + ("  (camada ativa: os objetos novos são criados aqui)" if layer.id == active else ""))
            if layer.id == active:
                it.setForeground(0, QBrush(QColor("#8FB3FF")))
                it.setText(0, f"{layer.name}  ●")
            self.tree.addTopLevelItem(it)
            self._items[layer.id] = it
            self._add_children(it, layer.objects)
            it.setExpanded(layer.id not in self._collapsed)
        self._building = False
        self._sync_selection()
        self._sync_opacity()

    def _add_children(self, parent_item: QTreeWidgetItem, objects) -> None:
        for s in reversed(objects):
            it = QTreeWidgetItem([s.name, "", ""])
            it.setData(0, ROLE, ("obj", s.id))
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
            if getattr(s, "is_star", False):
                icon_name = "star"
            elif s.kind == "caminho" and not s.closed:
                icon_name = "line" if len(s.points) == 2 else "freehand"
            else:
                icon_name = KIND_ICON.get(s.kind, "rect")
            it.setIcon(0, icon(icon_name))
            it.setIcon(1, icon("eye" if s.visible else "eye_off"))
            it.setIcon(2, icon("lock" if s.locked else "unlock"))
            if s.anim.active():
                it.setToolTip(0, f"{s.name} (animado)")
                it.setForeground(0, QBrush(QColor("#9BE8B0")))
            parent_item.addChild(it)
            self._items[s.id] = it
            if isinstance(s, GroupShape):
                self._add_children(it, s.children)
                it.setExpanded(s.id not in self._collapsed and len(s.children) <= 12)

    # ------------------------------------------------------------------
    def _sync_selection(self) -> None:
        if self._building or self._pending:
            return
        self._building = True
        self.tree.clearSelection()
        first = None
        for s in self.ctl.selection:
            it = self._items.get(s.id)
            if it is not None:
                it.setSelected(True)
                p = it.parent()
                while p is not None:
                    p.setExpanded(True)
                    p = p.parent()
                first = first or it
        if first is not None:
            self.tree.scrollToItem(first)
        self._building = False

    def _sync_opacity(self) -> None:
        layer = self.ctl.doc.active_layer()
        self.op_slider.blockSignals(True)
        self.op_slider.setValue(round(layer.opacity * 100))
        self.op_slider.blockSignals(False)
        self.op_value.setText(f"{round(layer.opacity * 100)}%")
        self.op_label.setText(f"Opacidade de '{layer.name}'" if len(layer.name) < 14 else "Opacidade")

    def _target(self, item: QTreeWidgetItem):
        data = item.data(0, ROLE)
        if not data:
            return None
        kind, oid = data
        if kind == "layer":
            return self.ctl.doc.layer_by_id(oid)
        return self.ctl.doc.find(oid)

    def _on_tree_selection(self) -> None:
        if self._building:
            return
        objs, layers = [], []
        for it in self.tree.selectedItems():
            t = self._target(it)
            if isinstance(t, Layer):
                layers.append(t)
            elif t is not None:
                objs.append(t)
        if objs:
            layer = self.ctl.doc.layer_of(objs[0])
            self.ctl.set_selection(objs)
            if layer is not None:
                self.ctl.set_active_layer(layer)
        elif layers:
            self.ctl.clear_selection()
            self.ctl.set_active_layer(layers[0])

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        t = self._target(item)
        if t is None or column not in (1, 2):
            return
        if isinstance(t, Layer):
            if column == 1:
                self.ctl.set_layer_flag(t, visible=not t.visible)
            else:
                self.ctl.set_layer_flag(t, locked=not t.locked)
        else:
            if column == 1:
                t.visible = not t.visible
                self.ctl.notify_structure("Visibilidade")
            else:
                t.locked = not t.locked
                self.ctl.notify_structure("Bloqueio")

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._building or column != 0:
            return
        t = self._target(item)
        if t is not None:
            self.ctl.rename(t, item.text(0).replace("●", "").strip())

    def _on_opacity(self, v: int) -> None:
        self.op_value.setText(f"{v}%")
        self.ctl.set_layer_opacity(self.ctl.doc.active_layer(), v / 100.0)

    def _context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if item is None:
            return
        t = self._target(item)
        m = QMenu(self)
        if isinstance(t, Layer):
            m.addAction(icon("add"), "Nova camada", self.ctl.add_layer)
            m.addAction(icon("duplicate"), "Duplicar camada", self.ctl.duplicate_layer)
            m.addAction(icon("delete"), "Apagar camada", self.ctl.delete_layer)
        else:
            if t not in self.ctl.selection:
                self.ctl.set_selection([t])
            sub = m.addMenu(icon("layers"), "Mover para a camada")
            for layer in reversed(self.ctl.doc.layers):
                sub.addAction(layer.name, lambda checked=False, L=layer: self.ctl.move_selection_to_layer(L))
            m.addAction(icon("front"), "Trazer para a frente", lambda: self.ctl.reorder("front"))
            m.addAction(icon("back"), "Enviar para trás", lambda: self.ctl.reorder("back"))
            m.addAction(icon("duplicate"), "Duplicar", self.ctl.duplicate_selection)
            m.addAction(icon("delete"), "Apagar", self.ctl.delete_selection)
        m.exec(self.tree.viewport().mapToGlobal(pos))
