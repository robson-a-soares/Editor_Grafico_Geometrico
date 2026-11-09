"""Classe base das ferramentas (padrão Strategy: o canvas delega os eventos do
mouse à ferramenta ativa)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt

from ..core import geometry as geo


@dataclass
class ToolEvent:
    x: float          # coordenadas do mundo
    y: float
    sx: float         # coordenadas do ecrã (pixels)
    sy: float
    button: object
    shift: bool
    ctrl: bool
    alt: bool
    px: float         # tamanho de um pixel em unidades do mundo


class Tool:
    name = "tool"
    label = "Ferramenta"
    shortcut = ""
    icon = ""
    cursor = Qt.CursorShape.ArrowCursor
    hint = ""

    def __init__(self, canvas):
        self.canvas = canvas

    @property
    def ctl(self):
        return self.canvas.ctl

    @property
    def doc(self):
        return self.canvas.ctl.doc

    def snap(self, x: float, y: float) -> tuple[float, float]:
        if self.ctl.snap_to_grid:
            g = self.doc.grid_size
            return geo.snap(x, g), geo.snap(y, g)
        return x, y

    # ciclo de vida
    def activate(self) -> None:
        self.canvas.setCursor(self.cursor)

    def deactivate(self) -> None:
        self.cancel()

    def cancel(self) -> None:
        pass

    # eventos
    def press(self, ev: ToolEvent) -> None:
        pass

    def move(self, ev: ToolEvent, dragging: bool) -> None:
        pass

    def release(self, ev: ToolEvent) -> None:
        pass

    def double_click(self, ev: ToolEvent) -> None:
        pass

    def key_press(self, key: int, shift: bool) -> bool:
        return False

    def draw_overlay(self, r, px: float) -> None:
        pass
