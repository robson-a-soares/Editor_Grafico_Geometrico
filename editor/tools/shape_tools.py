"""Ferramentas de criação de formas por arrasto."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt

from ..core import geometry as geo
from ..core.shapes import EllipseShape, PathShape, RectShape, RegularPolygonShape, TriangleShape
from ..render.renderer import ACCENT
from .base import Tool, ToolEvent

PREVIEW_FILL = (0.36, 0.56, 1.0, 0.25)


class BoxShapeTool(Tool):
    """Arrastar desenha a forma na caixa definida (Shift = proporcional, Alt = do centro)."""

    cursor = Qt.CursorShape.CrossCursor
    hint = "Arraste para desenhar · Shift: proporções iguais · Alt: a partir do centro · clique: tamanho padrão"
    default_size = 120.0

    def __init__(self, canvas):
        super().__init__(canvas)
        self.dragging = False
        self.start = self.cur = (0.0, 0.0)
        self.shift = self.alt = False

    def make(self, w: float, h: float):
        raise NotImplementedError

    def cancel(self) -> None:
        self.dragging = False

    def press(self, ev: ToolEvent) -> None:
        self.start = self.cur = self.snap(ev.x, ev.y)
        self.dragging = True
        self.shift, self.alt = ev.shift, ev.alt

    def move(self, ev: ToolEvent, dragging: bool) -> None:
        if self.dragging:
            self.cur = self.snap(ev.x, ev.y)
            self.shift, self.alt = ev.shift, ev.alt
            self.canvas.update()

    def box(self):
        (x0, y0), (x1, y1) = self.start, self.cur
        dx, dy = x1 - x0, y1 - y0
        if self.shift:
            m = max(abs(dx), abs(dy))
            dx, dy = math.copysign(m, dx or 1), math.copysign(m, dy or 1)
        if self.alt:
            return x0, y0, 2 * abs(dx), 2 * abs(dy)
        return x0 + dx / 2, y0 + dy / 2, abs(dx), abs(dy)

    def release(self, ev: ToolEvent) -> None:
        if not self.dragging:
            return
        self.dragging = False
        cx, cy, w, h = self.box()
        if w < 4 * ev.px and h < 4 * ev.px:  # clique simples: tamanho padrão
            cx, cy = self.start
            w = h = self.default_size
        w, h = max(w, 1.0), max(h, 1.0)
        shape = self.make(w, h)
        shape.transform.tx, shape.transform.ty = cx, cy
        shape.style = self.ctl.new_style()
        self.ctl.add_shape(shape)
        self.canvas.set_tool("select")

    def draw_overlay(self, r, px: float) -> None:
        if not self.dragging:
            return
        cx, cy, w, h = self.box()
        if w <= 0 or h <= 0:
            return
        pts = [(cx + x, cy + y) for x, y in self.make(w, h).outline()]
        r.fill_polygon(pts, PREVIEW_FILL)
        r.polyline(pts, ACCENT, px, 1.5, True)


class RectTool(BoxShapeTool):
    name, label, shortcut, icon = "rect", "Retângulo", "R", "rect"

    def make(self, w, h):
        return RectShape(w, h)


class EllipseTool(BoxShapeTool):
    name, label, shortcut, icon = "ellipse", "Elipse", "E", "ellipse"

    def make(self, w, h):
        return EllipseShape(w / 2, h / 2)


class TriangleTool(BoxShapeTool):
    name, label, shortcut, icon = "triangle", "Triângulo", "T", "triangle"

    def make(self, w, h):
        return TriangleShape(w, h)


class RadialShapeTool(Tool):
    """Arrastar a partir do centro: raio e orientação (Shift = passos de 15°)."""

    cursor = Qt.CursorShape.CrossCursor
    hint = "Arraste a partir do centro · Shift: ângulo em passos de 15° · lados/pontas no painel Propriedades"
    sides = 6
    inner = 0.0

    def __init__(self, canvas):
        super().__init__(canvas)
        self.dragging = False
        self.center = self.cur = (0.0, 0.0)
        self.shift = False

    def cancel(self) -> None:
        self.dragging = False

    def press(self, ev: ToolEvent) -> None:
        self.center = self.cur = self.snap(ev.x, ev.y)
        self.dragging = True

    def move(self, ev: ToolEvent, dragging: bool) -> None:
        if self.dragging:
            self.cur = (ev.x, ev.y)
            self.shift = ev.shift
            self.canvas.update()

    def params(self):
        dx, dy = self.cur[0] - self.center[0], self.cur[1] - self.center[1]
        radius = math.hypot(dx, dy)
        ang = math.degrees(math.atan2(dy, dx)) - 90.0 if radius > 0 else 0.0
        if self.shift:
            ang = round(ang / 15.0) * 15.0
        return radius, ang

    def release(self, ev: ToolEvent) -> None:
        if not self.dragging:
            return
        self.dragging = False
        radius, ang = self.params()
        if radius < 4 * ev.px:
            radius, ang = 60.0, 0.0
        shape = RegularPolygonShape(self.sides, radius, self.inner)
        shape.transform.tx, shape.transform.ty = self.center
        shape.transform.rotation = ang
        shape.style = self.ctl.new_style()
        self.ctl.add_shape(shape)
        self.canvas.set_tool("select")

    def draw_overlay(self, r, px: float) -> None:
        if not self.dragging:
            return
        radius, ang = self.params()
        if radius <= 0:
            return
        cs, sn = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        pts = [(self.center[0] + x * cs - y * sn, self.center[1] + x * sn + y * cs)
               for x, y in geo.regular_polygon_points(self.sides, radius, self.inner)]
        r.fill_polygon([self.center] + pts + [pts[0]], PREVIEW_FILL)
        r.polyline(pts, ACCENT, px, 1.5, True)


class NgonTool(RadialShapeTool):
    name, label, shortcut, icon = "ngon", "Polígono regular", "N", "ngon"
    sides, inner = 6, 0.0


class StarTool(RadialShapeTool):
    name, label, shortcut, icon = "star", "Estrela", "S", "star"
    sides, inner = 5, 0.45


class LineTool(Tool):
    name, label, shortcut, icon = "line", "Linha", "L", "line"
    cursor = Qt.CursorShape.CrossCursor
    hint = "Arraste para desenhar a linha · Shift: ângulos de 15°"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.dragging = False
        self.start = self.cur = (0.0, 0.0)

    def cancel(self) -> None:
        self.dragging = False

    def press(self, ev: ToolEvent) -> None:
        self.start = self.cur = self.snap(ev.x, ev.y)
        self.dragging = True

    def _end(self, ev: ToolEvent):
        x, y = self.snap(ev.x, ev.y)
        if ev.shift:
            dx, dy = geo.snap_angle(x - self.start[0], y - self.start[1], 15.0)
            x, y = self.start[0] + dx, self.start[1] + dy
        return x, y

    def move(self, ev: ToolEvent, dragging: bool) -> None:
        if self.dragging:
            self.cur = self._end(ev)
            self.canvas.update()

    def release(self, ev: ToolEvent) -> None:
        if not self.dragging:
            return
        self.dragging = False
        x1, y1 = self._end(ev)
        x0, y0 = self.start
        if math.hypot(x1 - x0, y1 - y0) < 4 * ev.px:
            x1, y1 = x0 + 120, y0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        shape = PathShape([(x0 - cx, y0 - cy), (x1 - cx, y1 - cy)], closed=False)
        shape.transform.tx, shape.transform.ty = cx, cy
        shape.style = self.ctl.new_style(filled=False)
        self.ctl.add_shape(shape)
        self.canvas.set_tool("select")

    def draw_overlay(self, r, px: float) -> None:
        if self.dragging:
            r.polyline([self.start, self.cur], ACCENT, px, 2.0, False)
