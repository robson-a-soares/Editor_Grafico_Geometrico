"""Pequenos widgets reutilizáveis: botão de cor e paleta rápida."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QColorDialog, QDoubleSpinBox, QHBoxLayout, QSizePolicy, QSpinBox,
                               QToolButton, QWidget)

from ..controller import PALETTE, hex_to_rgba


def rgba_to_qcolor(rgba) -> QColor:
    r, g, b, a = (list(rgba) + [1.0])[:4]
    return QColor.fromRgbF(max(0, min(1, r)), max(0, min(1, g)), max(0, min(1, b)), max(0, min(1, a)))


def qcolor_to_rgba(c: QColor) -> tuple:
    return (c.redF(), c.greenF(), c.blueF(), c.alphaF())


def _paint_swatch(p: QPainter, rect: QRectF, rgba, radius: float = 4.0) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    # xadrez por baixo para mostrar transparência
    s = 5.0
    y = rect.top()
    row = 0
    while y < rect.bottom():
        x = rect.left() + (s if row % 2 else 0)
        while x < rect.right():
            p.fillRect(QRectF(x, y, min(s, rect.right() - x), min(s, rect.bottom() - y)), QColor("#CCCCCC"))
            x += 2 * s
        y += s
        row += 1
    p.setBrush(rgba_to_qcolor(rgba))
    p.drawRoundedRect(rect, radius, radius)
    p.setPen(QPen(QColor("#596070"), 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(rect, radius, radius)


class ColorButton(QToolButton):
    """Mostra uma cor; ao clicar abre o seletor com pré-visualização ao vivo."""

    colorPreview = Signal(tuple)
    colorChosen = Signal(tuple)
    colorCanceled = Signal()

    def __init__(self, rgba=(1, 1, 1, 1), title: str = "Escolher cor", parent=None):
        super().__init__(parent)
        self._rgba = tuple(rgba)
        self.title = title
        self.setFixedSize(QSize(48, 24))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self.pick)

    def rgba(self) -> tuple:
        return self._rgba

    def set_rgba(self, rgba) -> None:
        self._rgba = tuple(rgba)
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        _paint_swatch(p, r, self._rgba if self.isEnabled() else (0.3, 0.3, 0.3, 1))
        p.end()

    def pick(self) -> None:
        dlg = QColorDialog(rgba_to_qcolor(self._rgba), self.window())
        dlg.setWindowTitle(self.title)
        dlg.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)
        dlg.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        dlg.currentColorChanged.connect(lambda c: self.colorPreview.emit(qcolor_to_rgba(c)))
        if dlg.exec():
            rgba = qcolor_to_rgba(dlg.selectedColor())
            self.set_rgba(rgba)
            self.colorChosen.emit(rgba)
        else:
            self.colorCanceled.emit()


class PaletteBar(QWidget):
    """Paleta rápida: clique = preenchimento, botão direito = contorno."""

    fillPicked = Signal(tuple)
    strokePicked = Signal(tuple)
    COLORS = PALETTE + ["#FFFFFF", "#C9CED8", "#6B7280", "#1D2433", "#000000"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setToolTip("Paleta: clique = cor de preenchimento · botão direito = cor do contorno")
        self.setFixedHeight(26)
        self.setFixedWidth(len(self.COLORS) * 19 + 4)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _rect(self, i: int) -> QRectF:
        return QRectF(2 + i * 19, 4, 16, 18)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        for i, c in enumerate(self.COLORS):
            _paint_swatch(p, self._rect(i), hex_to_rgba(c), 3)
        p.end()

    def mousePressEvent(self, e) -> None:
        for i, c in enumerate(self.COLORS):
            if self._rect(i).contains(e.position()):
                rgba = hex_to_rgba(c)
                if e.button() == Qt.MouseButton.RightButton:
                    self.strokePicked.emit(rgba)
                else:
                    self.fillPicked.emit(rgba)
                return


def dspin(lo: float, hi: float, step: float = 1.0, decimals: int = 1, suffix: str = "") -> QDoubleSpinBox:
    w = QDoubleSpinBox()
    w.setRange(lo, hi)
    w.setSingleStep(step)
    w.setDecimals(decimals)
    w.setSuffix(suffix)
    w.setKeyboardTracking(False)
    w.setAccelerated(True)
    w.setMinimumWidth(70)
    return w


def ispin(lo: int, hi: int, suffix: str = "") -> QSpinBox:
    w = QSpinBox()
    w.setRange(lo, hi)
    w.setSuffix(suffix)
    w.setKeyboardTracking(False)
    w.setMinimumWidth(60)
    return w


def hbox(*widgets, stretch: bool = False) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    for x in widgets:
        lay.addWidget(x)
    if stretch:
        lay.addStretch(1)
    return w
