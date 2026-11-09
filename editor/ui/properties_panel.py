"""Painel de propriedades: documento, transformação (com inspetor de matrizes),
geometria, aparência, animação e filtros de imagem."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox,
                               QLabel, QLineEdit, QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget)

from ..core.shapes import GroupShape, ImageShape, RegularPolygonShape, leaves, parent_world_matrix
from ..render.textures import BUILTIN_TEXTURES, FILTER_LABELS, FILTERS
from .widgets import ColorButton, dspin, hbox, ispin

FILL_MODES = [("color", "Cor sólida"), ("texture", "Textura"), ("none", "Sem preenchimento")]


def _fmt_matrix(m) -> str:
    rows = m.rows()
    left, right = ("⎡", "⎢", "⎣"), ("⎤", "⎥", "⎦")
    out = []
    for i, r in enumerate(rows):
        out.append(f"{left[i]} {r[0]:8.3f} {r[1]:8.3f} {r[2]:9.2f} {right[i]}")
    return "\n".join(out)


class PropertiesPanel(QScrollArea):
    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl
        self._orig = None          # cores originais durante a pré-visualização do seletor
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root = QWidget()
        self.setWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(8, 6, 8, 8)
        v.setSpacing(4)
        self.header = QLabel()
        self.header.setWordWrap(True)
        self.header.setStyleSheet("font-weight: 600; padding: 2px 2px 4px 2px;")
        v.addWidget(self.header)

        self._build_document(v)
        self._build_object(v)
        self._build_transform(v)
        self._build_matrix(v)
        self._build_geometry(v)
        self._build_style(v)
        self._build_animation(v)
        self._build_image(v)
        v.addStretch(1)

        ctl.selectionChanged.connect(self.refresh)
        ctl.documentReplaced.connect(self.refresh)
        ctl.structureChanged.connect(self.refresh)
        ctl.objectsChanged.connect(self.refresh_values)
        self.refresh()

    # ------------------------------------------------------------------
    # Construção
    # ------------------------------------------------------------------
    def _build_document(self, v) -> None:
        self.doc_box = QGroupBox("Documento (prancheta)")
        f = QFormLayout(self.doc_box)
        self.doc_w = dspin(16, 10000, 10, 0, " px")
        self.doc_h = dspin(16, 10000, 10, 0, " px")
        self.doc_bg = ColorButton(title="Cor de fundo")
        self.doc_transparent = QCheckBox("Fundo transparente")
        self.doc_grid = dspin(2, 500, 1, 0, " px")
        self.doc_snap = QCheckBox("Ajustar à grelha (Shift+G)")
        f.addRow("Largura", self.doc_w)
        f.addRow("Altura", self.doc_h)
        f.addRow("Fundo", hbox(self.doc_bg, self.doc_transparent, stretch=True))
        f.addRow("Grelha", self.doc_grid)
        f.addRow("", self.doc_snap)
        tip = QLabel("Selecione um objeto para editar as suas propriedades. "
                     "Desenhe com as ferramentas à esquerda.")
        tip.setObjectName("muted")
        tip.setWordWrap(True)
        f.addRow(tip)
        v.addWidget(self.doc_box)
        self.doc_w.valueChanged.connect(lambda x: self._set_doc("width", x))
        self.doc_h.valueChanged.connect(lambda x: self._set_doc("height", x))
        self.doc_grid.valueChanged.connect(lambda x: self._set_doc("grid_size", x))
        self.doc_bg.colorPreview.connect(lambda c: self._doc_bg(c, False))
        self.doc_bg.colorChosen.connect(lambda c: self._doc_bg(c, True))
        self.doc_bg.colorCanceled.connect(self._doc_bg_cancel)
        self.doc_transparent.toggled.connect(self._doc_transparent)
        self.doc_snap.toggled.connect(self._doc_snap)

    def _build_object(self, v) -> None:
        self.obj_box = QGroupBox("Objeto")
        f = QFormLayout(self.obj_box)
        self.name_edit = QLineEdit()
        self.kind_label = QLabel()
        self.kind_label.setObjectName("muted")
        f.addRow("Nome", self.name_edit)
        f.addRow("Tipo", self.kind_label)
        v.addWidget(self.obj_box)
        self.name_edit.editingFinished.connect(self._rename)

    def _build_transform(self, v) -> None:
        self.tf_box = QGroupBox("Transformação geométrica")
        g = QGridLayout(self.tf_box)
        g.setHorizontalSpacing(6)
        self.tx = dspin(-100000, 100000, 1, 1)
        self.ty = dspin(-100000, 100000, 1, 1)
        self.width_ = dspin(0.1, 100000, 1, 1)
        self.height_ = dspin(0.1, 100000, 1, 1)
        self.rot = dspin(-3600, 3600, 1, 1, "°")
        self.sx = dspin(-100000, 100000, 1, 1, " %")
        self.sy = dspin(-100000, 100000, 1, 1, " %")
        self.shear = dspin(-80, 80, 1, 1, "°")
        rows = [("X", self.tx, "Y", self.ty), ("Largura", self.width_, "Altura", self.height_),
                ("Escala X", self.sx, "Escala Y", self.sy), ("Rotação", self.rot, "Cisalh.", self.shear)]
        for r, (l1, w1, l2, w2) in enumerate(rows):
            g.addWidget(QLabel(l1), r, 0)
            g.addWidget(w1, r, 1)
            g.addWidget(QLabel(l2), r, 2)
            g.addWidget(w2, r, 3)
        b_h = QPushButton("Espelhar ↔")
        b_v = QPushButton("Espelhar ↕")
        b_r = QPushButton("Repor")
        b_r.setToolTip("Rotação 0°, escala 100 %, cisalhamento 0 (mantém a posição)")
        g.addWidget(hbox(b_h, b_v, b_r), 4, 0, 1, 4)
        v.addWidget(self.tf_box)
        self.tx.valueChanged.connect(lambda x: self._set_tf("tx", x))
        self.ty.valueChanged.connect(lambda x: self._set_tf("ty", x))
        self.width_.valueChanged.connect(lambda x: self._set_tf("w", x))
        self.height_.valueChanged.connect(lambda x: self._set_tf("h", x))
        self.rot.valueChanged.connect(lambda x: self._set_tf("rotation", x))
        self.sx.valueChanged.connect(lambda x: self._set_tf("sx", x))
        self.sy.valueChanged.connect(lambda x: self._set_tf("sy", x))
        self.shear.valueChanged.connect(lambda x: self._set_tf("shear", x))
        b_h.clicked.connect(lambda: self.ctl.flip_selection(True))
        b_v.clicked.connect(lambda: self.ctl.flip_selection(False))
        b_r.clicked.connect(self.ctl.reset_transform)

    def _build_matrix(self, v) -> None:
        self.mx_box = QGroupBox("Matriz de transformação")
        lay = QVBoxLayout(self.mx_box)
        self.mx_mode = QComboBox()
        self.mx_mode.addItems(["Local:  M = T · R · Sh · S", "Mundo:  M_pai · M_local"])
        self.mx_label = QLabel()
        self.mx_label.setObjectName("matrix")
        self.mx_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.mx_info = QLabel()
        self.mx_info.setObjectName("muted")
        self.mx_info.setWordWrap(True)
        lay.addWidget(self.mx_mode)
        lay.addWidget(self.mx_label)
        lay.addWidget(self.mx_info)
        v.addWidget(self.mx_box)
        self.mx_mode.currentIndexChanged.connect(lambda _i: self.refresh_values())

    def _build_geometry(self, v) -> None:
        self.geo_box = QGroupBox("Geometria")
        f = QFormLayout(self.geo_box)
        self.sides = ispin(3, 40)
        self.inner = dspin(5, 95, 1, 0, " %")
        self.inner_label = QLabel("Raio interno")
        f.addRow("Lados / pontas", self.sides)
        f.addRow(self.inner_label, self.inner)
        v.addWidget(self.geo_box)
        self.sides.valueChanged.connect(lambda x: self._set_geom("sides", x))
        self.inner.valueChanged.connect(lambda x: self._set_geom("inner", x))

    def _build_style(self, v) -> None:
        self.st_box = QGroupBox("Aparência")
        f = QFormLayout(self.st_box)
        self.fill_mode = QComboBox()
        for _k, label in FILL_MODES:
            self.fill_mode.addItem(label)
        self.fill_btn = ColorButton(title="Cor de preenchimento")
        self.tex_combo = QComboBox()
        self.tex_repeat = dspin(0.1, 50, 0.5, 1, "×")
        self.stroke_btn = ColorButton(title="Cor do contorno")
        self.stroke_w = dspin(0, 200, 0.5, 1, " px")
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity_val = QLabel("100%")
        self.opacity_val.setMinimumWidth(34)
        f.addRow("Preenchimento", hbox(self.fill_mode, self.fill_btn))
        self.tex_row_label = QLabel("Textura")
        f.addRow(self.tex_row_label, hbox(self.tex_combo, self.tex_repeat))
        f.addRow("Contorno", hbox(self.stroke_btn, self.stroke_w, stretch=True))
        f.addRow("Opacidade", hbox(self.opacity, self.opacity_val))
        v.addWidget(self.st_box)
        self.fill_mode.currentIndexChanged.connect(self._set_fill_mode)
        self.fill_btn.colorPreview.connect(lambda c: self._color("fill", c, False))
        self.fill_btn.colorChosen.connect(lambda c: self._color("fill", c, True))
        self.fill_btn.colorCanceled.connect(self._color_cancel)
        self.stroke_btn.colorPreview.connect(lambda c: self._color("stroke", c, False))
        self.stroke_btn.colorChosen.connect(lambda c: self._color("stroke", c, True))
        self.stroke_btn.colorCanceled.connect(self._color_cancel)
        self.tex_combo.activated.connect(self._set_texture)
        self.tex_repeat.valueChanged.connect(lambda x: self._set_style("texture_repeat", x, "Repetição da textura"))
        self.stroke_w.valueChanged.connect(lambda x: self._set_style("stroke_width", x, "Espessura do contorno"))
        self.opacity.valueChanged.connect(self._set_opacity)

    def _build_animation(self, v) -> None:
        self.an_box = QGroupBox("Animação (F5 para reproduzir)")
        f = QFormLayout(self.an_box)
        self.an_rot = dspin(-1440, 1440, 5, 0, " °/s")
        self.an_pulse = dspin(0, 100, 1, 0, " %")
        self.an_pulse_f = dspin(0.05, 10, 0.1, 2, " Hz")
        self.an_ox = dspin(0, 5000, 5, 0, " px")
        self.an_oy = dspin(0, 5000, 5, 0, " px")
        self.an_of = dspin(0.02, 10, 0.05, 2, " Hz")
        self.an_hue = dspin(-720, 720, 5, 0, " °/s")
        f.addRow("Rodar", self.an_rot)
        f.addRow("Pulsar", hbox(self.an_pulse, self.an_pulse_f))
        f.addRow("Oscilar X / Y", hbox(self.an_ox, self.an_oy))
        f.addRow("Freq. oscilação", self.an_of)
        f.addRow("Ciclo de cor", self.an_hue)
        play = QPushButton("▶  Reproduzir / parar (F5)")
        play.clicked.connect(self.ctl.toggle_animation)
        f.addRow(play)
        v.addWidget(self.an_box)
        for w, attr in ((self.an_rot, "rotate"), (self.an_pulse, "pulse"), (self.an_pulse_f, "pulse_freq"),
                        (self.an_ox, "osc_x"), (self.an_oy, "osc_y"), (self.an_of, "osc_freq"),
                        (self.an_hue, "hue")):
            w.valueChanged.connect(lambda x, a=attr: self._set_anim(a, x))

    def _build_image(self, v) -> None:
        self.img_box = QGroupBox("Imagem digital — filtros")
        g = QGridLayout(self.img_box)
        for i, (key, label) in enumerate(FILTERS):
            b = QPushButton(label)
            b.clicked.connect(lambda _c=False, k=key: self._add_filter(k))
            g.addWidget(b, i // 2, i % 2)
        n = (len(FILTERS) + 1) // 2
        reset = QPushButton("Repor imagem original")
        reset.clicked.connect(self._reset_filters)
        g.addWidget(reset, n, 0, 1, 2)
        self.img_info = QLabel()
        self.img_info.setObjectName("muted")
        self.img_info.setWordWrap(True)
        g.addWidget(self.img_info, n + 1, 0, 1, 2)
        v.addWidget(self.img_box)

    # ------------------------------------------------------------------
    # Atualização a partir do modelo
    # ------------------------------------------------------------------
    def _single(self):
        sel = self.ctl.selection
        return sel[0] if len(sel) == 1 else None

    def _style_targets(self):
        return [leaf for s in self.ctl.editable_selection() for leaf in leaves(s)]

    def refresh(self) -> None:
        sel = self.ctl.selection
        n = len(sel)
        s = self._single()
        editable = all(self.ctl.doc.is_editable(x) for x in sel) if sel else True
        self.doc_box.setVisible(n == 0)
        self.obj_box.setVisible(s is not None)
        self.tf_box.setVisible(s is not None)
        self.mx_box.setVisible(s is not None)
        self.geo_box.setVisible(isinstance(s, RegularPolygonShape))
        self.st_box.setVisible(n >= 1)
        self.an_box.setVisible(n >= 1)
        imgs = [x for x in self._style_targets() if isinstance(x, ImageShape)]
        self.img_box.setVisible(bool(imgs))
        for box in (self.obj_box, self.tf_box, self.geo_box, self.st_box, self.an_box, self.img_box):
            box.setEnabled(editable)
        if n == 0:
            self.header.setText("Sem seleção — propriedades do documento")
        elif s is not None:
            extra = "" if editable else "  (bloqueado)"
            label = "Estrela" if getattr(s, "is_star", False) else s.label
            name = "" if s.name == label else f" — {s.name}"
            self.header.setText(f"{label}{name}{extra}")
        else:
            self.header.setText(f"{n} objetos selecionados — aparência e animação aplicam-se a todos")
        self._fill_texture_combo()
        self.refresh_values()

    @staticmethod
    def _set(w, value) -> None:
        if w.hasFocus():
            return
        w.blockSignals(True)
        w.setValue(value)
        w.blockSignals(False)

    def refresh_values(self) -> None:
        doc = self.ctl.doc
        sel = self.ctl.selection
        s = self._single()
        if not sel:
            self._set(self.doc_w, doc.width)
            self._set(self.doc_h, doc.height)
            self._set(self.doc_grid, doc.grid_size)
            self.doc_bg.set_rgba(doc.background[:3] + (1.0,))
            for cb, val in ((self.doc_transparent, doc.background[3] < 0.5), (self.doc_snap, self.ctl.snap_to_grid)):
                cb.blockSignals(True)
                cb.setChecked(val)
                cb.blockSignals(False)
            return
        if s is not None:
            if not self.name_edit.hasFocus():
                self.name_edit.setText(s.name)
            self.kind_label.setText(s.label + (f" com {len(s.children)} filhos" if isinstance(s, GroupShape) else ""))
            t = s.transform
            x0, y0, x1, y1 = s.local_bbox()
            self._set(self.tx, t.tx)
            self._set(self.ty, t.ty)
            self._set(self.width_, max(0.1, (x1 - x0) * abs(t.sx)))
            self._set(self.height_, max(0.1, (y1 - y0) * abs(t.sy)))
            self._set(self.rot, t.rotation)
            self._set(self.sx, t.sx * 100)
            self._set(self.sy, t.sy * 100)
            self._set(self.shear, math.degrees(math.atan(t.shear)))
            local = t.matrix()
            world = parent_world_matrix(s) @ local
            m = local if self.mx_mode.currentIndex() == 0 else world
            self.mx_label.setText(_fmt_matrix(m))
            det = m.m[0] * m.m[4] - m.m[1] * m.m[3]
            self.mx_info.setText(
                f"T({t.tx:.1f}, {t.ty:.1f}) · R({t.rotation:.1f}°) · Sh({t.shear:.2f}) · "
                f"S({t.sx:.2f}, {t.sy:.2f})\n"
                f"det = {det:.3f}  (área × {abs(det):.2f}{', espelhado' if det < 0 else ''})")
            if isinstance(s, RegularPolygonShape):
                self._set(self.sides, s.sides)
                self._set(self.inner, s.inner_ratio * 100 if s.is_star else 50)
                self.inner.setVisible(s.is_star)
                self.inner_label.setVisible(s.is_star)
        targets = self._style_targets()
        ref = targets[0] if targets else sel[0]
        st = ref.style
        modes = [k for k, _l in FILL_MODES]
        self.fill_mode.blockSignals(True)
        self.fill_mode.setCurrentIndex(modes.index(st.fill_mode) if st.fill_mode in modes else 0)
        self.fill_mode.setEnabled(st.fill_mode != "image" and ref.has_fill)
        self.fill_mode.blockSignals(False)
        self.fill_btn.set_rgba(st.fill)
        self.fill_btn.setEnabled(st.fill_mode != "image" and ref.has_fill)
        self.stroke_btn.set_rgba(st.stroke)
        self._set(self.stroke_w, st.stroke_width)
        tex_visible = st.fill_mode == "texture"
        self.tex_combo.setVisible(tex_visible)
        self.tex_repeat.setVisible(tex_visible)
        self.tex_row_label.setVisible(tex_visible)
        idx = self.tex_combo.findData(st.texture)
        if idx >= 0:
            self.tex_combo.setCurrentIndex(idx)
        self._set(self.tex_repeat, st.texture_repeat)
        op = round(sel[0].style.opacity * 100)
        self._set(self.opacity, op)
        self.opacity_val.setText(f"{op}%")
        a = sel[0].anim
        for w, val in ((self.an_rot, a.rotate), (self.an_pulse, a.pulse * 100), (self.an_pulse_f, a.pulse_freq),
                       (self.an_ox, a.osc_x), (self.an_oy, a.osc_y), (self.an_of, a.osc_freq), (self.an_hue, a.hue)):
            self._set(w, val)
        imgs = [x for x in targets if isinstance(x, ImageShape)]
        if imgs:
            f = imgs[0].filters
            self.img_info.setText("Filtros aplicados: " + (", ".join(FILTER_LABELS.get(k, k) for k in f) if f else "nenhum"))

    def _fill_texture_combo(self) -> None:
        self.tex_combo.blockSignals(True)
        self.tex_combo.clear()
        for key, label in BUILTIN_TEXTURES:
            self.tex_combo.addItem(label, f"builtin:{key}")
        img_n = 0
        for iid in self.ctl.doc.images:
            img_n += 1
            self.tex_combo.addItem(f"Imagem importada {img_n}", f"img:{iid}")
        self.tex_combo.addItem("Importar imagem como textura…", "__import__")
        self.tex_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Edição
    # ------------------------------------------------------------------
    def _set_doc(self, attr: str, value: float) -> None:
        setattr(self.ctl.doc, attr, float(value))
        self.ctl.notify_modified("Propriedades do documento")

    def _doc_bg(self, rgba, final: bool) -> None:
        if self._orig is None:
            self._orig = ("doc", self.ctl.doc.background)
        a = 0.0 if self.doc_transparent.isChecked() else 1.0
        self.ctl.doc.background = (rgba[0], rgba[1], rgba[2], a)
        if final:
            self._orig = None
        self.ctl.notify_modified("Cor de fundo" if final else None, now=final)

    def _doc_bg_cancel(self) -> None:
        if self._orig and self._orig[0] == "doc":
            self.ctl.doc.background = self._orig[1]
        self._orig = None
        self.ctl.notify_modified()

    def _doc_transparent(self, on: bool) -> None:
        r, g, b, _a = self.ctl.doc.background
        self.ctl.doc.background = (r, g, b, 0.0 if on else 1.0)
        self.ctl.notify_modified("Fundo transparente", now=True)

    def _doc_snap(self, on: bool) -> None:
        self.ctl.snap_to_grid = on
        self.ctl.viewOptionsChanged.emit()

    def _rename(self) -> None:
        s = self._single()
        if s is not None:
            self.ctl.rename(s, self.name_edit.text())

    def _set_tf(self, attr: str, value: float) -> None:
        s = self._single()
        if s is None or not self.ctl.doc.is_editable(s):
            return
        t = s.transform
        if attr in ("tx", "ty", "rotation"):
            setattr(t, attr, value)
        elif attr in ("sx", "sy"):
            v = value / 100.0
            setattr(t, attr, v if abs(v) > 1e-3 else math.copysign(1e-3, v or 1))
        elif attr == "shear":
            t.shear = math.tan(math.radians(value))
        elif attr in ("w", "h"):
            x0, y0, x1, y1 = s.local_bbox()
            base = (x1 - x0) if attr == "w" else (y1 - y0)
            if base > 1e-9:
                cur = t.sx if attr == "w" else t.sy
                setattr(t, "sx" if attr == "w" else "sy", math.copysign(value / base, cur))
        self.ctl.notify_modified("Transformar")

    def _set_geom(self, attr: str, value) -> None:
        s = self._single()
        if not isinstance(s, RegularPolygonShape):
            return
        if attr == "sides":
            s.sides = int(value)
        else:
            s.inner_ratio = max(0.05, value / 100.0)
        self.ctl.notify_modified("Geometria")

    def _set_fill_mode(self, idx: int) -> None:
        mode = FILL_MODES[idx][0]
        for s in self._style_targets():
            if s.has_fill and s.style.fill_mode != "image":
                s.style.fill_mode = mode
        self.ctl.notify_modified("Tipo de preenchimento", now=True)
        self.refresh_values()

    def _color(self, which: str, rgba, final: bool) -> None:
        targets = self._style_targets()
        if self._orig is None:
            self._orig = (which, [(s, s.style.fill, s.style.stroke, s.style.fill_mode, s.style.stroke_width)
                                  for s in targets])
        for s in targets:
            if which == "fill":
                if s.has_fill and s.style.fill_mode != "image":
                    s.style.fill = tuple(rgba)
                    s.style.fill_mode = "color"
            else:
                s.style.stroke = tuple(rgba)
                if s.style.stroke_width <= 0:
                    s.style.stroke_width = 2.0
        if final:
            self._orig = None
        self.ctl.notify_modified(("Cor de preenchimento" if which == "fill" else "Cor do contorno") if final else None,
                                 now=final)

    def _color_cancel(self) -> None:
        if self._orig and self._orig[0] in ("fill", "stroke"):
            for s, fill, stroke, mode, width in self._orig[1]:
                s.style.fill, s.style.stroke, s.style.fill_mode, s.style.stroke_width = fill, stroke, mode, width
        self._orig = None
        self.ctl.notify_modified()

    def _set_style(self, attr: str, value, label: str) -> None:
        for s in self._style_targets():
            setattr(s.style, attr, value)
        self.ctl.notify_modified(label)

    def _set_texture(self, idx: int) -> None:
        ref = self.tex_combo.itemData(idx)
        if ref == "__import__":
            path, _f = QFileDialog.getOpenFileName(self, "Importar imagem como textura", "",
                                                   "Imagens (*.png *.jpg *.jpeg *.bmp *.gif)")
            if not path:
                self.refresh_values()
                return
            try:
                ref = self.ctl.import_texture(path)
            except Exception as e:  # noqa: BLE001
                self.ctl.message.emit(f"Não foi possível abrir a imagem: {e}")
                return
            self._fill_texture_combo()
        for s in self._style_targets():
            if s.has_fill and s.style.fill_mode != "image":
                s.style.texture = ref
                s.style.fill_mode = "texture"
        self.ctl.notify_modified("Textura", now=True)
        self.refresh_values()

    def _set_opacity(self, v: int) -> None:
        self.opacity_val.setText(f"{v}%")
        for s in self.ctl.editable_selection():
            s.style.opacity = v / 100.0
        self.ctl.notify_modified("Opacidade")

    def _set_anim(self, attr: str, value: float) -> None:
        if attr == "pulse":
            value = value / 100.0
        for s in self.ctl.editable_selection():
            setattr(s.anim, attr, value)
        self.ctl.notify_modified("Animação")

    def _add_filter(self, key: str) -> None:
        imgs = [x for x in self._style_targets() if isinstance(x, ImageShape)]
        for s in imgs:
            s.filters.append(key)
        if imgs:
            self.ctl.notify_modified(f"Filtro: {FILTER_LABELS.get(key, key)}", now=True)
            self.refresh_values()

    def _reset_filters(self) -> None:
        imgs = [x for x in self._style_targets() if isinstance(x, ImageShape)]
        for s in imgs:
            s.filters = []
        if imgs:
            self.ctl.notify_modified("Repor imagem", now=True)
            self.refresh_values()
