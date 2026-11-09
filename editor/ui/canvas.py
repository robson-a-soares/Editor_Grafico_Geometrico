"""Área de desenho: um QOpenGLWidget onde tudo é desenhado com OpenGL.

Usa dois visores (viewports) na mesma janela: o principal, com zoom e
deslocamento, e o minimapa no canto, que mostra a prancheta inteira e o
retângulo da janela do mundo que está a ser vista.
"""

from __future__ import annotations

from OpenGL import GL as gl
from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from ..core.picking import hit_test
from ..core.shapes import GroupShape, world_matrix
from ..render.camera import Camera
from ..render.renderer import ACCENT, WORKSPACE, Renderer
from ..tools import TOOL_CLASSES
from ..tools.base import ToolEvent
from .icons import rotate_cursor

LEFT = Qt.MouseButton.LeftButton
MIDDLE = Qt.MouseButton.MiddleButton


class Canvas(QOpenGLWidget):
    cursorMoved = Signal(float, float)
    viewChanged = Signal()
    toolChanged = Signal(str)
    contextMenuRequested = Signal(object)
    glReady = Signal(dict)
    glFailed = Signal(str)

    def __init__(self, ctl, parent=None):
        super().__init__(parent)
        self.ctl = ctl
        self.camera = Camera()
        self.renderer = Renderer()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(320, 240)
        self.rotate_cursor = rotate_cursor()
        self.tools = {cls.name: cls(self) for cls in TOOL_CLASSES}
        self.tool = self.tools["select"]
        self.hover = None
        self.gl_ok = False
        self._space = False
        self._pan_last = None
        self._mini_drag = False
        self._need_fit = True
        self.auto_fit = True      # enquanto o utilizador não mexer na vista, a prancheta acompanha a janela
        self._frames = 0
        self._fps_clock = QElapsedTimer()
        self._fps_clock.start()
        self.fps = 0.0
        ctl.objectsChanged.connect(self.update)
        ctl.selectionChanged.connect(self.update)
        ctl.structureChanged.connect(self.update)
        ctl.animationTick.connect(self.update)
        ctl.viewOptionsChanged.connect(self.update)
        ctl.animationChanged.connect(self._on_animation)
        ctl.documentReplaced.connect(self._on_document_replaced)

    # ------------------------------------------------------------------
    # Ciclo de vida OpenGL
    # ------------------------------------------------------------------
    def initializeGL(self) -> None:
        self.renderer.textures.forget()   # contexto novo: as texturas antigas já não existem
        try:
            self.renderer.init_gl()
            fmt = self.context().format()
            if (fmt.majorVersion(), fmt.minorVersion()) < (2, 0):
                raise RuntimeError(f"OpenGL {fmt.majorVersion()}.{fmt.minorVersion()} é demasiado antigo")
            self.gl_ok = True
            self.glReady.emit(self.renderer.info)
        except Exception as e:  # noqa: BLE001
            self.gl_ok = False
            self.glFailed.emit(str(e))

    def resizeGL(self, w: int, h: int) -> None:
        self.camera.resize(self.width(), self.height())
        if self.auto_fit:
            self._need_fit = True
        self.viewChanged.emit()

    def paintGL(self) -> None:
        if not self.gl_ok:
            return
        self.camera.resize(self.width(), self.height())
        if self._need_fit:
            self._need_fit = False
            self.fit_view(keep_auto=self.auto_fit)
        dpr = self.devicePixelRatioF()
        r = self.renderer
        r.begin()
        gl.glViewport(0, 0, int(self.width() * dpr), int(self.height() * dpr))
        r.clear(WORKSPACE)
        r.set_projection(self.camera.window())
        px = self.camera.px()
        doc = self.ctl.doc
        playing = self.ctl.playing
        r.draw_artboard(doc, px)
        if self.ctl.show_grid and not playing:
            r.draw_grid(doc, px)
        if self.ctl.clip_to_artboard:
            self._scissor_artboard(dpr)
        r.draw_document(doc, t=self.ctl.anim_time if playing else None, px=px)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        if not playing:
            self._draw_overlays(r, px)
        if self.ctl.show_minimap:
            self._draw_minimap(r, dpr)
        r.end()
        self._count_fps()
        self._draw_hud()

    def _scissor_artboard(self, dpr: float) -> None:
        """Recorta o desenho ao retângulo da prancheta (teste de tesoura em pixels do visor)."""
        doc = self.ctl.doc
        x0, y0 = self.camera.world_to_screen(0.0, doc.height)
        x1, y1 = self.camera.world_to_screen(doc.width, 0.0)
        hd = int(self.height() * dpr)
        sx, sy = int(round(x0 * dpr)), int(round(y0 * dpr))
        sw, sh = int(round((x1 - x0) * dpr)), int(round((y1 - y0) * dpr))
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glScissor(sx, hd - sy - sh, max(0, sw), max(0, sh))

    def _count_fps(self) -> None:
        self._frames += 1
        ms = self._fps_clock.elapsed()
        if ms >= 1000:
            self.fps = self._frames * 1000.0 / ms
            self._frames = 0
            self._fps_clock.restart()

    def clear_textures(self) -> None:
        if self.gl_ok and self.context() is not None:
            self.makeCurrent()
            self.renderer.textures.clear()
            self.doneCurrent()

    # ------------------------------------------------------------------
    # Desenho das sobreposições
    # ------------------------------------------------------------------
    def _outline(self, r, s, px, color, width) -> None:
        if not s.visible:
            return
        if isinstance(s, GroupShape):
            for c in s.children:
                self._outline(r, c, px, (color[0], color[1], color[2], color[3] * 0.55), width)
            return
        r.polyline(r.world_outline(s, world_matrix(s)), color, px, width, s.closed)

    def _draw_overlays(self, r, px: float) -> None:
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        sel = self.ctl.selection
        if self.hover is not None and self.hover not in sel and self.tool.name == "select":
            self._outline(r, self.hover, px, (0.36, 0.56, 1.0, 0.85), 1.5)
        for s in sel:
            self._outline(r, s, px, ACCENT, 1.0)
        self.tool.draw_overlay(r, px)

    def minimap_rect(self) -> tuple[float, float, float, float]:
        doc = self.ctl.doc
        mw = 190.0
        mh = mw * doc.height / max(doc.width, 1e-6)
        if mh > 150:
            mh = 150.0
            mw = mh * doc.width / max(doc.height, 1e-6)
        return self.width() - mw - 14, self.height() - mh - 14, mw, mh

    def _minimap_region(self):
        doc = self.ctl.doc
        m = 0.06   # margem igual nos dois eixos → a proporção do visor é mantida
        return (-m * doc.width, doc.width * (1 + m), -m * doc.height, doc.height * (1 + m))

    def _draw_minimap(self, r, dpr: float) -> None:
        x, y, w, h = self.minimap_rect()
        if w < 20 or h < 20 or self.width() < 420:
            return
        doc = self.ctl.doc
        gx, gy = int(round(x * dpr)), int(round((self.height() - y - h) * dpr))
        gw, gh = int(round(w * dpr)), int(round(h * dpr))
        b = max(1, int(round(2 * dpr)))
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glScissor(gx - b, gy - b, gw + 2 * b, gh + 2 * b)
        r.clear((0.30, 0.33, 0.40, 1.0))
        gl.glScissor(gx, gy, gw, gh)
        r.clear((0.085, 0.09, 0.105, 1.0))
        gl.glViewport(gx, gy, gw, gh)          # segundo visor
        region = self._minimap_region()
        r.set_projection(region)
        pxm = (region[1] - region[0]) / w
        r.draw_artboard(doc, pxm, shadow=False)
        if self.ctl.clip_to_artboard:   # interseção do visor do minimapa com a prancheta
            ax = gx + (0.0 - region[0]) / (region[1] - region[0]) * gw
            ay = gy + (0.0 - region[2]) / (region[3] - region[2]) * gh
            aw = doc.width / (region[1] - region[0]) * gw
            ah = doc.height / (region[3] - region[2]) * gh
            gl.glScissor(int(round(ax)), int(round(ay)), int(round(aw)), int(round(ah)))
        r.draw_document(doc, t=self.ctl.anim_time if self.ctl.playing else None, px=pxm)
        gl.glScissor(gx, gy, gw, gh)
        left, right, bottom, top = self.camera.window()
        r.fill_rect(left, bottom, right, top, (0.36, 0.56, 1.0, 0.10))
        r.rect_outline(left, bottom, right, top, ACCENT, pxm, 1.5)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        gl.glViewport(0, 0, int(self.width() * dpr), int(self.height() * dpr))

    def _draw_hud(self) -> None:
        lines = []
        if self.ctl.playing:
            fps = f"{self.fps:4.0f} FPS" if self.fps > 0 else "… FPS"
            lines.append((f"▶  Animação   t = {self.ctl.anim_time:5.1f} s   ·   {fps}   ·   F5 para parar",
                          QColor("#4ADE80")))
        if not self.camera.keep_aspect:
            sx, sy = self.camera.scale_factors()
            lines.append((f"Janela→visor COM distorção (demonstração): sx = {sx:.2f}, sy = {sy:.2f}"
                          "   ·   Ver ▸ Manter proporção", QColor("#FF6B6B")))
        angle = getattr(self.tool, "angle_text", "")
        if not lines and not angle:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        f = QFont()
        f.setPointSizeF(9.5)
        f.setBold(True)
        p.setFont(f)
        fm = p.fontMetrics()
        y = 12.0
        for text, color in lines:
            w = fm.horizontalAdvance(text) + 20
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 165))
            p.drawRoundedRect(QRectF(12, y, w, 26), 8, 8)
            p.setPen(color)
            p.drawText(QRectF(22, y, w, 26), Qt.AlignmentFlag.AlignVCenter, text)
            y += 32
        if angle:
            pos = self.mapFromGlobal(self.cursor().pos())
            w = fm.horizontalAdvance(angle) + 14
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(20, 24, 32, 220))
            p.drawRoundedRect(QRectF(pos.x() + 18, pos.y() + 14, w, 22), 6, 6)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(QRectF(pos.x() + 25, pos.y() + 14, w, 22), Qt.AlignmentFlag.AlignVCenter, angle)
        p.end()

    # ------------------------------------------------------------------
    # Vista
    # ------------------------------------------------------------------
    def fit_view(self, keep_auto: bool = True) -> None:
        doc = self.ctl.doc
        self.camera.resize(self.width(), self.height())
        self.camera.fit(0, 0, doc.width, doc.height, 0.9)
        self.auto_fit = keep_auto
        self.update()
        self.viewChanged.emit()

    def zoom_100(self) -> None:
        self.camera.set_zoom(1.0)
        self.camera.center_on(self.ctl.doc.width / 2, self.ctl.doc.height / 2)
        self.view_changed()

    def zoom_step(self, factor: float) -> None:
        self.camera.zoom_at(self.width() / 2, self.height() / 2, factor)
        self.view_changed()

    def view_changed(self) -> None:
        """O utilizador mexeu na vista (zoom/deslocamento): deixa de reajustar automaticamente."""
        self.auto_fit = False
        self.update()
        self.viewChanged.emit()

    def set_keep_aspect(self, keep: bool) -> None:
        self.camera.set_keep_aspect(keep)
        self.update()
        self.viewChanged.emit()

    def set_tool(self, name: str) -> None:
        if name not in self.tools:
            return
        if self.tool.name != name:
            self.tool.deactivate()
            self.tool = self.tools[name]
            self.hover = None
        self.tool.activate()
        self.update()
        self.toolChanged.emit(name)

    def _on_animation(self, playing: bool) -> None:
        self.hover = None
        self._fps_clock.restart()
        self._frames = 0
        self.update()

    def _on_document_replaced(self) -> None:
        self.hover = None
        for t in self.tools.values():
            t.cancel()
        self.clear_textures()
        self.auto_fit = True
        self._need_fit = True
        self.update()

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def _event(self, e) -> ToolEvent:
        pos = e.position()
        x, y = self.camera.screen_to_world(pos.x(), pos.y())
        m = e.modifiers()
        return ToolEvent(x, y, pos.x(), pos.y(), e.button(),
                         bool(m & Qt.KeyboardModifier.ShiftModifier),
                         bool(m & Qt.KeyboardModifier.ControlModifier),
                         bool(m & Qt.KeyboardModifier.AltModifier), self.camera.px())

    def _in_minimap(self, pos: QPointF) -> bool:
        if not self.ctl.show_minimap or self.width() < 420:
            return False
        x, y, w, h = self.minimap_rect()
        return x <= pos.x() <= x + w and y <= pos.y() <= y + h

    def _minimap_jump(self, pos: QPointF) -> None:
        x, y, w, h = self.minimap_rect()
        left, right, bottom, top = self._minimap_region()
        wx = left + (pos.x() - x) / w * (right - left)
        wy = top - (pos.y() - y) / h * (top - bottom)
        self.camera.center_on(wx, wy)
        self.view_changed()

    def mousePressEvent(self, e) -> None:
        self.setFocus()
        pos = e.position()
        if e.button() == LEFT and self._in_minimap(pos):
            self._mini_drag = True
            self._minimap_jump(pos)
            return
        if e.button() == MIDDLE or (e.button() == LEFT and self._space):
            self._pan_last = (pos.x(), pos.y())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if e.button() != LEFT:
            return
        if self.ctl.playing:
            self.ctl.message.emit("A animação está a correr: prima F5 para parar e poder editar.")
            return
        self.tool.press(self._event(e))
        self.update()

    def mouseMoveEvent(self, e) -> None:
        ev = self._event(e)
        self.cursorMoved.emit(ev.x, ev.y)
        if self._pan_last is not None:
            self.camera.pan(ev.sx - self._pan_last[0], ev.sy - self._pan_last[1])
            self._pan_last = (ev.sx, ev.sy)
            self.view_changed()
            return
        if self._mini_drag:
            self._minimap_jump(e.position())
            return
        if self.ctl.playing:
            return
        self.tool.move(ev, bool(e.buttons() & LEFT))
        if getattr(self.tool, "angle_text", ""):
            self.update()

    def mouseReleaseEvent(self, e) -> None:
        if self._pan_last is not None and e.button() in (MIDDLE, LEFT):
            self._pan_last = None
            self.setCursor(Qt.CursorShape.OpenHandCursor if self._space else self.tool.cursor)
            return
        if self._mini_drag:
            self._mini_drag = False
            return
        if e.button() == LEFT and not self.ctl.playing:
            self.tool.release(self._event(e))
            self.update()

    def mouseDoubleClickEvent(self, e) -> None:
        if e.button() == LEFT and not self.ctl.playing and not self._in_minimap(e.position()):
            self.tool.double_click(self._event(e))
            self.update()

    def wheelEvent(self, e) -> None:
        d = e.angleDelta().y() or e.angleDelta().x()
        if not d:
            return
        pos = e.position()
        self.camera.zoom_at(pos.x(), pos.y(), 1.0015 ** d)
        self.view_changed()

    def keyPressEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        if not self.ctl.playing and self.tool.key_press(e.key(), bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
            self.update()
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_Space and not e.isAutoRepeat():
            self._space = False
            self.setCursor(self.tool.cursor)
            return
        super().keyReleaseEvent(e)

    def contextMenuEvent(self, e) -> None:
        if self.ctl.playing:
            return
        x, y = self.camera.screen_to_world(e.pos().x(), e.pos().y())
        hit = hit_test(self.ctl.doc, x, y, 5 * self.camera.px())
        if hit is not None and hit not in self.ctl.selection:
            self.ctl.set_selection([hit])
        self.contextMenuRequested.emit(e.globalPos())

    def leaveEvent(self, e) -> None:
        if self.hover is not None:
            self.hover = None
            self.update()
        super().leaveEvent(e)
