"""Ferramenta de seleção e transformação.

- Clique: seleciona (Shift acrescenta/retira). Arrastar no vazio: seleção por área.
- Arrastar um objeto: translação.
- Alças nos cantos/lados: escala (Shift = proporcional, Alt = a partir do centro).
- Alça redonda por cima: rotação (Shift = passos de 15°).
- Duplo clique num grupo: seleciona o filho sob o cursor.

Cada operação é uma matriz aplicada à matriz do mundo guardada no início
do arrasto:

    translação:  M' = T(d) · M0
    rotação:     M' = T(c) · R(θ) · T(−c) · M0
    escala (1 objeto, nos eixos dele):  M' = M0 · T(a) · S(fx, fy) · T(−a)
    escala (vários, nos eixos do mundo): M' = T(a) · S(fx, fy) · T(−a) · M0

e depois M' é convertida para os parâmetros do objeto (decomposição).
"""

from __future__ import annotations

import math

from PySide6.QtCore import Qt

from ..core import geometry as geo
from ..core import operations as ops
from ..core.matrix import Mat3, Transform
from ..core.picking import hit_test, objects_in_rect, shape_hit
from ..core.shapes import GroupShape, parent_world_matrix, world_matrix
from ..render.renderer import ACCENT
from .base import Tool, ToolEvent

# alças: (u, v) na caixa envolvente; 0 = mínimo, 1 = máximo
HANDLE_UV = [(0, 0), (0.5, 0), (1, 0), (1, 0.5), (1, 1), (0.5, 1), (0, 1), (0, 0.5)]
ROTATE = 8


class SelectTool(Tool):
    name = "select"
    label = "Selecionar"
    shortcut = "V"
    icon = "select"
    hint = "Clique para selecionar · arraste para mover · alças para escalar/rodar · Shift: múltipla"

    def __init__(self, canvas):
        super().__init__(canvas)
        self.mode = None          # "move" | "scale" | "rotate" | "band"
        self.start = (0.0, 0.0)
        self.current = (0.0, 0.0)
        self.moved = False
        self.click_shape = None
        self.angle_text = ""

    # ------------------------------------------------------------------
    # Geometria das alças
    # ------------------------------------------------------------------
    def frame(self):
        """(cantos em mundo, função uv→mundo, objeto único ou None)."""
        sel = self.ctl.editable_selection()
        if not sel:
            return None
        if len(sel) == 1:
            s = sel[0]
            w = world_matrix(s)
            x0, y0, x1, y1 = s.local_bbox()
            return ("single", s, w, (x0, y0, x1, y1))
        b = ops.selection_bbox(sel)
        return ("multi", sel, None, b)

    @staticmethod
    def uv_point(frame, u, v):
        kind, _s, w, (x0, y0, x1, y1) = frame
        p = (x0 + u * (x1 - x0), y0 + v * (y1 - y0))
        return w.apply(*p) if kind == "single" else p

    def handle_points(self, px: float):
        f = self.frame()
        if f is None:
            return None, []
        pts = [self.uv_point(f, u, v) for u, v in HANDLE_UV]
        top = pts[5]
        center = self.uv_point(f, 0.5, 0.5)
        dx, dy = top[0] - center[0], top[1] - center[1]
        if math.hypot(dx, dy) < 1e-9:
            dx, dy = (f[2].apply_vector(0, 1) if f[0] == "single" else (0, 1))
        n = math.hypot(dx, dy) or 1.0
        rot = (top[0] + dx / n * 26 * px, top[1] + dy / n * 26 * px)
        return f, pts + [rot]

    def handle_at(self, ev: ToolEvent):
        f, pts = self.handle_points(ev.px)
        if not pts:
            return None
        cam = self.canvas.camera
        best, best_d = None, 8.0
        for i, p in enumerate(pts):
            sx, sy = cam.world_to_screen(*p)
            d = math.hypot(sx - ev.sx, sy - ev.sy)
            if d <= best_d:
                best, best_d = i, d
        return best

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def press(self, ev: ToolEvent) -> None:
        self.start = self.current = (ev.x, ev.y)
        self.moved = False
        self.click_shape = None
        h = self.handle_at(ev)
        if h is not None:
            self._begin_transform(h, ev)
            return
        sel = self.ctl.editable_selection()
        tol = 5 * ev.px
        # clicar dentro de um objeto já selecionado (mesmo dentro de um grupo) move a seleção
        inside_sel = next((s for s in sel if shape_hit(s, ev.x, ev.y, tol)), None)
        shape = inside_sel or hit_test(self.doc, ev.x, ev.y, tol)
        if shape is not None:
            if ev.shift:
                self.ctl.toggle_selection(shape)
                self.mode = None
                return
            if shape not in self.ctl.selection:
                self.ctl.set_selection([shape])
            else:
                self.click_shape = shape
            self._begin_move()
            return
        if not ev.shift:
            self.ctl.clear_selection()
        self.mode = "band"

    def _snapshot(self):
        self.targets = self.ctl.editable_selection()
        self.w0 = {s.id: world_matrix(s) for s in self.targets}
        self.p_inv = {s.id: parent_world_matrix(s).inverse() for s in self.targets}
        self.t0 = {s.id: s.transform.copy() for s in self.targets}

    def _begin_move(self) -> None:
        self._snapshot()
        self.mode = "move" if self.targets else None
        b = ops.selection_bbox(self.targets) if self.targets else None
        self.ref0 = (b[0], b[1]) if b else self.start

    def _begin_transform(self, h: int, ev: ToolEvent) -> None:
        self._snapshot()
        self.frame0 = self.frame()
        self.handle = h
        if h == ROTATE:
            self.mode = "rotate"
            self.center = self.uv_point(self.frame0, 0.5, 0.5)
            self.angle0 = math.degrees(math.atan2(ev.y - self.center[1], ev.x - self.center[0]))
        else:
            self.mode = "scale"

    def move(self, ev: ToolEvent, dragging: bool) -> None:
        if not dragging or self.mode is None:
            self._hover(ev)
            return
        self.current = (ev.x, ev.y)
        if not self.moved:
            sx0, sy0 = self.canvas.camera.world_to_screen(*self.start)
            if math.hypot(ev.sx - sx0, ev.sy - sy0) < 3:
                return
            self.moved = True
        if self.mode == "move":
            self._do_move(ev)
        elif self.mode == "scale":
            self._do_scale(ev)
        elif self.mode == "rotate":
            self._do_rotate(ev)
        if self.mode in ("move", "scale", "rotate"):
            self.ctl.notify_modified()
        self.canvas.update()

    def release(self, ev: ToolEvent) -> None:
        mode, self.mode = self.mode, None
        self.angle_text = ""
        if mode == "band":
            if self.moved:
                x0, y0 = self.start
                rect = (min(x0, ev.x), min(y0, ev.y), max(x0, ev.x), max(y0, ev.y))
                found = objects_in_rect(self.doc, rect)
                if ev.shift:
                    self.ctl.set_selection(self.ctl.selection + found)
                else:
                    self.ctl.set_selection(found)
        elif mode in ("move", "scale", "rotate"):
            if self.moved:
                self.ctl.commit({"move": "Mover", "scale": "Escalar", "rotate": "Rodar"}[mode])
            elif mode == "move" and self.click_shape is not None:
                self.ctl.set_selection([self.click_shape])
        self.canvas.update()

    def double_click(self, ev: ToolEvent) -> None:
        sel = self.ctl.selection
        if len(sel) == 1 and isinstance(sel[0], GroupShape):
            for c in reversed(sel[0].children):
                if shape_hit(c, ev.x, ev.y, 5 * ev.px):
                    self.ctl.set_selection([c])
                    self.ctl.message.emit(f"Dentro do grupo: '{c.name}' selecionado (Esc para sair)")
                    return

    def key_press(self, key: int, shift: bool) -> bool:
        if key == Qt.Key.Key_Escape:
            sel = self.ctl.selection
            if len(sel) == 1 and isinstance(sel[0].parent, GroupShape):
                self.ctl.set_selection([sel[0].parent])
            else:
                self.ctl.clear_selection()
            return True
        return False

    # ------------------------------------------------------------------
    # Operações
    # ------------------------------------------------------------------
    def _apply_world(self, s, m: Mat3) -> None:
        s.transform = Transform.from_matrix(self.p_inv[s.id] @ m, reference=self.t0[s.id])

    def _do_move(self, ev: ToolEvent) -> None:
        dx, dy = ev.x - self.start[0], ev.y - self.start[1]
        if ev.shift:  # restringir ao eixo dominante
            if abs(dx) > abs(dy):
                dy = 0.0
            else:
                dx = 0.0
        if self.ctl.snap_to_grid:
            g = self.doc.grid_size
            dx = geo.snap(self.ref0[0] + dx, g) - self.ref0[0]
            dy = geo.snap(self.ref0[1] + dy, g) - self.ref0[1]
        for s in self.targets:
            s.transform = self.t0[s.id].copy()
            ops.translate_world(s, dx, dy)

    def _do_scale(self, ev: ToolEvent) -> None:
        u, v = HANDLE_UV[self.handle]
        au, av = (0.5, 0.5) if ev.alt else (1 - u, 1 - v)
        kind = self.frame0[0]
        edge_x = v == 0.5     # alças laterais: só escala em x
        edge_y = u == 0.5     # alças de cima/baixo: só escala em y
        if kind == "single":
            x0, y0, x1, y1 = self.frame0[3]
            a = (x0 + au * (x1 - x0), y0 + av * (y1 - y0))
            h = (x0 + u * (x1 - x0), y0 + v * (y1 - y0))
            s = self.targets[0]
            m0 = self.w0[s.id]
            try:
                q = m0.inverse().apply(ev.x, ev.y)       # cursor nas coordenadas locais
            except ZeroDivisionError:
                return
        else:
            b = self.frame0[3]
            a = (b[0] + au * (b[2] - b[0]), b[1] + av * (b[3] - b[1]))
            h = (b[0] + u * (b[2] - b[0]), b[1] + v * (b[3] - b[1]))
            q = (ev.x, ev.y)
        ex, ey = h[0] - a[0], h[1] - a[1]
        fx = (q[0] - a[0]) / ex if abs(ex) > 1e-9 else 1.0
        fy = (q[1] - a[1]) / ey if abs(ey) > 1e-9 else 1.0
        if edge_x:
            fy = abs(fx) if ev.shift else 1.0
        elif edge_y:
            fx = abs(fy) if ev.shift else 1.0
        elif ev.shift:
            f = max(abs(fx), abs(fy))
            fx, fy = math.copysign(f, fx), math.copysign(f, fy)
        fx = fx if abs(fx) > 1e-3 else math.copysign(1e-3, fx or 1.0)
        fy = fy if abs(fy) > 1e-3 else math.copysign(1e-3, fy or 1.0)
        m = Mat3.scaling_about(fx, fy, a[0], a[1])
        if kind == "single":
            s = self.targets[0]
            self._apply_world(s, self.w0[s.id] @ m)
        else:
            for s in self.targets:
                self._apply_world(s, m @ self.w0[s.id])
        self.angle_text = f"{fx * 100:.0f}% × {fy * 100:.0f}%"

    def _do_rotate(self, ev: ToolEvent) -> None:
        cx, cy = self.center
        ang = math.degrees(math.atan2(ev.y - cy, ev.x - cx)) - self.angle0
        if ev.shift:
            ang = round(ang / 15.0) * 15.0
        r = Mat3.rotation_about(ang, cx, cy)
        for s in self.targets:
            self._apply_world(s, r @ self.w0[s.id])
        a = (ang + 180.0) % 360.0 - 180.0
        self.angle_text = f"{a:+.1f}°"

    # ------------------------------------------------------------------
    # Cursor e desenho
    # ------------------------------------------------------------------
    def _hover(self, ev: ToolEvent) -> None:
        h = self.handle_at(ev)
        cv = self.canvas
        if h == ROTATE:
            cv.setCursor(cv.rotate_cursor)
        elif h is not None:
            f, pts = self.handle_points(ev.px)
            c = self.uv_point(f, 0.5, 0.5)
            sx, sy = cv.camera.world_to_screen(*pts[h])
            cx, cy = cv.camera.world_to_screen(*c)
            ang = math.degrees(math.atan2(-(sy - cy), sx - cx)) % 180.0
            if ang < 22.5 or ang >= 157.5:
                cv.setCursor(Qt.CursorShape.SizeHorCursor)
            elif ang < 67.5:
                cv.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif ang < 112.5:
                cv.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                cv.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            shape = hit_test(self.doc, ev.x, ev.y, 5 * ev.px)
            cv.setCursor(Qt.CursorShape.SizeAllCursor if shape is not None and shape in self.ctl.selection
                         else Qt.CursorShape.ArrowCursor)
            if shape is not cv.hover:
                cv.hover = shape
                cv.update()

    def draw_overlay(self, r, px: float) -> None:
        if self.mode == "band" and self.moved:
            (x0, y0), (x1, y1) = self.start, self.current
            r.fill_rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), (0.36, 0.56, 1.0, 0.12))
            r.rect_outline(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), ACCENT, px, 1.0)
            return
        f, pts = self.handle_points(px)
        if not pts:
            return
        corners = [pts[0], pts[2], pts[4], pts[6]]
        r.polyline(corners, ACCENT, px, 1.5, True)
        r.polyline([pts[5], pts[8]], ACCENT, px, 1.5, False)
        for i, p in enumerate(pts[:8]):
            r.handle(p[0], p[1], px, 9.0)
        r.handle(pts[8][0], pts[8][1], px, 11.0, round_=True)
        c = self.uv_point(f, 0.5, 0.5)
        if self.mode == "rotate":
            c = self.center
        r.polyline([(c[0] - 5 * px, c[1]), (c[0] + 5 * px, c[1])], ACCENT, px, 1.2, False)
        r.polyline([(c[0], c[1] - 5 * px), (c[0], c[1] + 5 * px)], ACCENT, px, 1.2, False)
