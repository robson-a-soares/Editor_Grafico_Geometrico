"""Polígono livre (clique a clique), mão livre e mão (deslocar a vista)."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt

from ..core import geometry as geo
from ..core.shapes import PathShape
from ..render.renderer import ACCENT
from .base import Tool, ToolEvent


def _centered(points):
    cx, cy = geo.centroid_of_bbox(points)
    return [(x - cx, y - cy) for x, y in points], (cx, cy)


class PolygonTool(Tool):
    name, label, shortcut, icon = "polygon", "Polígono livre", "P", "polygon"
    cursor = Qt.CursorShape.CrossCursor
    hint = "Clique para cada vértice · duplo clique, Enter ou clique no 1.º ponto para fechar · Backspace: desfazer ponto · Esc: cancelar"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.points: list[tuple[float, float]] = []
        self.cursor_pos = None

    def cancel(self) -> None:
        self.points = []
        self.canvas.update()

    def press(self, ev: ToolEvent) -> None:
        p = self.snap(ev.x, ev.y)
        if len(self.points) >= 3:
            sx, sy = self.canvas.camera.world_to_screen(*self.points[0])
            if math.hypot(sx - ev.sx, sy - ev.sy) < 9:
                self.finish()
                return
        if not self.points or math.hypot(p[0] - self.points[-1][0], p[1] - self.points[-1][1]) > ev.px:
            self.points.append(p)
        self.canvas.update()

    def move(self, ev: ToolEvent, dragging: bool) -> None:
        self.cursor_pos = self.snap(ev.x, ev.y)
        if self.points:
            self.canvas.update()

    def double_click(self, ev: ToolEvent) -> None:
        self.finish()

    def key_press(self, key: int, shift: bool) -> bool:
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.finish()
            return True
        if key == Qt.Key.Key_Escape:
            self.cancel()
            return True
        if key == Qt.Key.Key_Backspace and self.points:
            self.points.pop()
            self.canvas.update()
            return True
        return False

    def finish(self) -> None:
        pts = geo.dedupe(self.points, closed=True)
        self.points = []
        if len(pts) < 3:
            self.canvas.update()
            self.ctl.message.emit("Um polígono precisa de pelo menos 3 pontos.")
            return
        local, (cx, cy) = _centered(pts)
        shape = PathShape(local, closed=True)
        shape.transform.tx, shape.transform.ty = cx, cy
        shape.style = self.ctl.new_style()
        self.ctl.add_shape(shape, "Criar polígono")
        self.canvas.set_tool("select")

    def draw_overlay(self, r, px: float) -> None:
        if not self.points:
            return
        pts = list(self.points)
        if len(pts) >= 3:
            tris = geo.triangulate(geo.dedupe(pts))
            if tris:
                for t in tris:
                    r.fill_polygon([pts[i] for i in t], (0.36, 0.56, 1.0, 0.2))
        line = pts + ([self.cursor_pos] if self.cursor_pos else [])
        r.polyline(line, ACCENT, px, 1.5, False)
        for i, p in enumerate(pts):
            r.handle(p[0], p[1], px, 9.0 if i == 0 else 7.0, round_=i == 0)


class FreehandTool(Tool):
    name, label, shortcut, icon = "freehand", "Mão livre", "F", "freehand"
    cursor = Qt.CursorShape.CrossCursor
    hint = "Arraste para desenhar à mão livre (o traço é simplificado pelo algoritmo de Ramer–Douglas–Peucker)"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.points: list[tuple[float, float]] = []
        self.drawing = False

    def cancel(self) -> None:
        self.points = []
        self.drawing = False

    def press(self, ev: ToolEvent) -> None:
        self.points = [(ev.x, ev.y)]
        self.drawing = True

    def move(self, ev: ToolEvent, dragging: bool) -> None:
        if self.drawing:
            last = self.points[-1]
            if math.hypot(ev.x - last[0], ev.y - last[1]) > 1.5 * ev.px:
                self.points.append((ev.x, ev.y))
                self.canvas.update()

    def release(self, ev: ToolEvent) -> None:
        if not self.drawing:
            return
        self.drawing = False
        n0 = len(self.points)
        pts = geo.simplify_rdp(self.points, 1.2 * ev.px)
        self.points = []
        if len(pts) < 2:
            self.canvas.update()
            return
        local, (cx, cy) = _centered(pts)
        shape = PathShape(local, closed=False, name="Traço")
        shape.transform.tx, shape.transform.ty = cx, cy
        shape.style = self.ctl.new_style(filled=False)
        self.ctl.add_shape(shape, "Desenhar à mão livre")
        self.ctl.message.emit(f"Traço simplificado de {n0} para {len(pts)} pontos (Ramer–Douglas–Peucker)")

    def draw_overlay(self, r, px: float) -> None:
        if len(self.points) >= 2:
            r.polyline(self.points, ACCENT, px, 2.0, False)


class HandTool(Tool):
    name, label, shortcut, icon = "hand", "Mão (deslocar vista)", "H", "hand"
    cursor = Qt.CursorShape.OpenHandCursor
    hint = "Arraste para deslocar a vista · roda do mouse: zoom · também: botão do meio ou Espaço + arrastar"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.last = None

    def press(self, ev: ToolEvent) -> None:
        self.last = (ev.sx, ev.sy)
        self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)

    def move(self, ev: ToolEvent, dragging: bool) -> None:
        if dragging and self.last is not None:
            self.canvas.camera.pan(ev.sx - self.last[0], ev.sy - self.last[1])
            self.last = (ev.sx, ev.sy)
            self.canvas.view_changed()

    def release(self, ev: ToolEvent) -> None:
        self.last = None
        self.canvas.setCursor(self.cursor)
