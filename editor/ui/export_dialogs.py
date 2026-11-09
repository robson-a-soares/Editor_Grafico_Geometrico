"""Diálogos de opções para exportar imagem e GIF animado."""

from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel,
                               QVBoxLayout)

from ..render.exporter import export_region, size_for
from .widgets import dspin, ispin


class ImageExportDialog(QDialog):
    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl
        self.setWindowTitle("Exportar imagem")
        v = QVBoxLayout(self)
        f = QFormLayout()
        self.area = QComboBox()
        self.area.addItem("Prancheta inteira", "prancheta")
        self.area.addItem("Todo o conteúdo", "conteudo")
        if ctl.selection:
            self.area.addItem("Só a seleção", "selecao")
        self.scale = dspin(0.1, 8.0, 0.5, 2, "×")
        self.scale.setValue(1.0)
        self.transparent = QCheckBox("Fundo transparente (só PNG)")
        self.transparent.setChecked(ctl.doc.background[3] < 0.5)
        self.size_label = QLabel()
        self.size_label.setObjectName("muted")
        f.addRow("Área", self.area)
        f.addRow("Escala", self.scale)
        f.addRow("Tamanho final", self.size_label)
        f.addRow("", self.transparent)
        v.addLayout(f)
        note = QLabel("A imagem é desenhada fora do ecrã (framebuffer OpenGL) na resolução escolhida.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        v.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.area.currentIndexChanged.connect(self._update)
        self.scale.valueChanged.connect(self._update)
        self._update()

    def region(self):
        return export_region(self.ctl.doc, self.area.currentData(), self.ctl.selection)

    def image_size(self):
        return size_for(self.region(), self.scale.value())

    def _update(self) -> None:
        w, h = self.image_size()
        self.size_label.setText(f"{w} × {h} px")


class GifExportDialog(QDialog):
    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl
        self.setWindowTitle("Exportar animação GIF")
        v = QVBoxLayout(self)
        f = QFormLayout()
        self.area = QComboBox()
        self.area.addItem("Prancheta inteira", "prancheta")
        self.area.addItem("Todo o conteúdo", "conteudo")
        self.width_ = ispin(120, 1600, " px")
        self.width_.setValue(int(min(720, ctl.doc.width)))
        self.duration = dspin(0.5, 30, 0.5, 1, " s")
        self.duration.setValue(4.0)
        self.fps = ispin(5, 30, " fps")
        self.fps.setValue(20)
        self.info = QLabel()
        self.info.setObjectName("muted")
        f.addRow("Área", self.area)
        f.addRow("Largura", self.width_)
        f.addRow("Duração", self.duration)
        f.addRow("Quadros por segundo", self.fps)
        f.addRow("", self.info)
        v.addLayout(f)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        for w in (self.width_, self.duration, self.fps):
            w.valueChanged.connect(self._update)
        self.area.currentIndexChanged.connect(self._update)
        self._update()

    def region(self):
        return export_region(self.ctl.doc, self.area.currentData(), None)

    def _update(self) -> None:
        r = self.region()
        h = round(self.width_.value() * (r[3] - r[2]) / (r[1] - r[0]))
        n = round(self.duration.value() * self.fps.value())
        self.info.setText(f"{self.width_.value()} × {h} px · {n} quadros · repete em ciclo")
