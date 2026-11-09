"""Desenho do documento com OpenGL (pipeline clássico).

Projeção: glOrtho com a janela do mundo calculada pela câmara (camera.py).
Modelação: para cada objeto,

    glPushMatrix()
    glMultMatrixf(M_local.to_gl())     # matriz calculada por nós (matrix.py)
    ... desenhar filhos (grupos) ou o preenchimento ...
    glPopMatrix()

A pilha de matrizes do OpenGL acumula as matrizes dos grupos, por isso um
filho é desenhado com M_mundo = M_grupo · M_filho (modelação hierárquica).
Os vértices seguem em arrays (glVertexPointer + glDrawArrays), uma chamada
por forma, em vez de glVertex por ponto.
"""

from __future__ import annotations

import math

import numpy as np
from OpenGL import GL as gl

from ..core.animation import animated_color, animated_matrix
from ..core.matrix import Mat3
from ..core.shapes import GroupShape, Shape
from .tessellation import fill_arrays, stroke_strip, transform_points
from .textures import TextureCache

ACCENT = (0.36, 0.56, 1.0, 1.0)
WHITE = (1.0, 1.0, 1.0, 1.0)
WORKSPACE = (0.125, 0.13, 0.15, 1.0)
MISSING = (0.85, 0.3, 0.6, 1.0)


def _gl_str(name) -> str:
    try:
        v = gl.glGetString(name)
        return v.decode("utf-8", "replace") if isinstance(v, bytes) else str(v)
    except Exception:
        return "?"


class Renderer:
    def __init__(self):
        self.textures = TextureCache()
        self.info: dict[str, str] = {}
        self._images: dict = {}

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------
    def init_gl(self) -> None:
        self.info = {"versao": _gl_str(gl.GL_VERSION),
                     "renderizador": _gl_str(gl.GL_RENDERER),
                     "fabricante": _gl_str(gl.GL_VENDOR)}
        self.begin()

    def begin(self) -> None:
        """Repõe o estado do OpenGL usado pelo editor (chamado em cada frame)."""
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_CULL_FACE)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_BLEND)
        # alfa "pré-multiplicado" no destino: dá transparência correta ao exportar PNG
        gl.glBlendFuncSeparate(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA,
                               gl.GL_ONE, gl.GL_ONE_MINUS_SRC_ALPHA)
        try:
            gl.glEnable(gl.GL_MULTISAMPLE)
        except Exception:
            pass
        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)

    @staticmethod
    def end() -> None:
        """Desliga o estado do pipeline clássico antes de o Qt (QPainter) desenhar por cima."""
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 4)
        gl.glBlendFunc(gl.GL_ONE, gl.GL_ONE_MINUS_SRC_ALPHA)

    def set_projection(self, window) -> None:
        left, right, bottom, top = window
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(left, right, bottom, top, -1.0, 1.0)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

    @staticmethod
    def clear(rgba) -> None:
        gl.glClearColor(*rgba)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

    # ------------------------------------------------------------------
    # Documento
    # ------------------------------------------------------------------
    def draw_document(self, doc, t: float | None = None, px: float = 1.0) -> None:
        self._images = doc.images
        identity = Mat3.identity()
        for layer in doc.layers:
            if not layer.visible or layer.opacity <= 0:
                continue
            for s in layer.objects:
                self.draw_shape(s, identity, layer.opacity, t, px)

    def draw_shape(self, s: Shape, parent_world: Mat3, alpha: float, t, px: float) -> None:
        if not s.visible:
            return
        local = s.transform.matrix()
        if t is not None and s.anim.active():
            local = animated_matrix(local, s.anim, t)
        world = parent_world @ local
        a = alpha * s.style.opacity
        if a <= 0.002:
            return
        gl.glPushMatrix()
        gl.glMultMatrixf(local.to_gl())
        if isinstance(s, GroupShape):
            for c in s.children:
                self.draw_shape(c, world, a, t, px)
            gl.glPopMatrix()
            return
        self._draw_fill(s, a, t)
        gl.glPopMatrix()
        self._draw_stroke(s, world, a, t, px)

    def _fill_mesh(self, s: Shape):
        key = s.geom_key()
        cached = s._cache.get("fill")
        if cached is None or cached[0] != key:
            verts, uvs = fill_arrays(s)
            cached = (key, verts, uvs)
            s._cache["fill"] = cached
        return cached[1], cached[2]

    def _draw_fill(self, s: Shape, a: float, t) -> None:
        st = s.style
        if not s.has_fill or st.fill_mode == "none":
            return
        verts, uvs = self._fill_mesh(s)
        if verts is None or len(verts) == 0:
            return
        tex = None
        repeat = 1.0
        if st.fill_mode == "image":
            tex = self.textures.image(getattr(s, "image_id", ""), getattr(s, "filters", ()), self._images)
            color = (1.0, 1.0, 1.0, a) if tex else MISSING[:3] + (a,)
        elif st.fill_mode == "texture":
            tex = self.textures.fill_texture(st.texture, self._images)
            repeat = max(0.01, st.texture_repeat)
            tint = animated_color((1.0, 1.0, 1.0, 1.0), s.anim, t) if t is not None else (1, 1, 1, 1)
            color = (tint[0], tint[1], tint[2], a) if tex else MISSING[:3] + (a,)
        else:
            c = animated_color(st.fill, s.anim, t) if t is not None else st.fill
            color = (c[0], c[1], c[2], c[3] * a)
        gl.glColor4f(*color)
        if tex:
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glBindTexture(gl.GL_TEXTURE_2D, tex)
            gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
            tc = uvs if repeat == 1.0 else np.ascontiguousarray(uvs * repeat, dtype=np.float32)
            gl.glTexCoordPointer(2, gl.GL_FLOAT, 0, tc)
        gl.glVertexPointer(2, gl.GL_FLOAT, 0, verts)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, len(verts))
        if tex:
            gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)
            gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
            gl.glDisable(gl.GL_TEXTURE_2D)

    def _local_outline(self, s: Shape) -> np.ndarray:
        key = s.geom_key()
        cached = s._cache.get("outline")
        if cached is None or cached[0] != key:
            cached = (key, np.asarray(s.outline(), dtype=np.float64).reshape(-1, 2))
            s._cache["outline"] = cached
        return cached[1]

    def world_outline(self, s: Shape, world: Mat3) -> np.ndarray:
        return transform_points(self._local_outline(s), world)

    def _draw_stroke(self, s: Shape, world: Mat3, a: float, t, px: float) -> None:
        st = s.style
        if st.stroke_width <= 0:
            return
        hw = max(st.stroke_width / 2.0, 0.5 * px)
        key = (s.geom_key(), world.key(), round(hw, 5))
        cached = s._cache.get("stroke")
        if cached is None or cached[0] != key:
            pts = self.world_outline(s, world)
            cached = (key, stroke_strip(pts, hw, s.closed))
            s._cache["stroke"] = cached
        strip = cached[1]
        if strip is None:
            return
        c = animated_color(st.stroke, s.anim, t) if t is not None else st.stroke
        gl.glColor4f(c[0], c[1], c[2], c[3] * a)
        gl.glPushMatrix()
        gl.glLoadIdentity()                 # a fita já está em coordenadas do mundo
        gl.glVertexPointer(2, gl.GL_FLOAT, 0, strip)
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, len(strip))
        gl.glPopMatrix()

    # ------------------------------------------------------------------
    # Prancheta e grelha
    # ------------------------------------------------------------------
    def draw_artboard(self, doc, px: float, shadow: bool = True) -> None:
        x0, y0, x1, y1 = doc.artboard
        if shadow:
            o = 5 * px
            self.fill_rect(x0 + o, y0 - o, x1 + o, y1 - o, (0, 0, 0, 0.35))
        bg = doc.background
        if bg[3] < 1.0:
            self.checkerboard(x0, y0, x1, y1, px)
        self.fill_rect(x0, y0, x1, y1, bg)

    def checkerboard(self, x0, y0, x1, y1, px) -> None:
        tex = self.textures.builtin("transparencia")
        if not tex:
            self.fill_rect(x0, y0, x1, y1, WHITE)
            return
        k = 1.0 / (320.0 * px)   # cada quadrado com ~20 px no ecrã
        verts = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y0], [x1, y1], [x0, y1]], np.float32)
        uvs = np.ascontiguousarray(verts * k, dtype=np.float32)
        gl.glColor4f(1, 1, 1, 1)
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex)
        gl.glEnableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        gl.glTexCoordPointer(2, gl.GL_FLOAT, 0, uvs)
        gl.glVertexPointer(2, gl.GL_FLOAT, 0, verts)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)
        gl.glDisableClientState(gl.GL_TEXTURE_COORD_ARRAY)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        gl.glDisable(gl.GL_TEXTURE_2D)

    def draw_grid(self, doc, px: float) -> None:
        step = float(doc.grid_size)
        if step <= 0:
            return
        while step / px < 8:
            step *= 2
        x0, y0, x1, y1 = doc.artboard
        bg = doc.background
        dark = (0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]) < 0.5 and bg[3] > 0.5
        base = (1.0, 1.0, 1.0) if dark else (0.1, 0.12, 0.2)
        xs = np.arange(math.ceil(x0 / step) * step, x1 + 1e-6, step)
        ys = np.arange(math.ceil(y0 / step) * step, y1 + 1e-6, step)
        for major in (False, True):
            sel_x = xs[(np.round(xs / step) % 5 == 0) == major]
            sel_y = ys[(np.round(ys / step) % 5 == 0) == major]
            segs = []
            for x in sel_x:
                segs += [(x, y0), (x, y1)]
            for y in sel_y:
                segs += [(x0, y), (x1, y)]
            if not segs:
                continue
            arr = np.asarray(segs, np.float32)
            gl.glColor4f(*base, 0.16 if major else 0.07)
            gl.glLineWidth(1.0)
            gl.glVertexPointer(2, gl.GL_FLOAT, 0, arr)
            gl.glDrawArrays(gl.GL_LINES, 0, len(arr))

    # ------------------------------------------------------------------
    # Primitivas para sobreposições (seleção, pré-visualizações)
    # ------------------------------------------------------------------
    @staticmethod
    def fill_rect(x0, y0, x1, y1, rgba) -> None:
        verts = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y0], [x1, y1], [x0, y1]], np.float32)
        gl.glColor4f(*rgba)
        gl.glVertexPointer(2, gl.GL_FLOAT, 0, verts)
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 6)

    @staticmethod
    def fill_polygon(points, rgba) -> None:
        """Preenche um polígono convexo (leque de triângulos)."""
        arr = np.asarray(points, np.float32).reshape(-1, 2)
        if len(arr) < 3:
            return
        gl.glColor4f(*rgba)
        gl.glVertexPointer(2, gl.GL_FLOAT, 0, np.ascontiguousarray(arr))
        gl.glDrawArrays(gl.GL_TRIANGLE_FAN, 0, len(arr))

    @staticmethod
    def polyline(points, rgba, px: float, width_px: float = 1.5, closed: bool = True) -> None:
        strip = stroke_strip(np.asarray(points, np.float64).reshape(-1, 2), width_px * px / 2.0, closed)
        if strip is None:
            return
        gl.glColor4f(*rgba)
        gl.glVertexPointer(2, gl.GL_FLOAT, 0, strip)
        gl.glDrawArrays(gl.GL_TRIANGLE_STRIP, 0, len(strip))

    def rect_outline(self, x0, y0, x1, y1, rgba, px, width_px=1.5) -> None:
        self.polyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], rgba, px, width_px, True)

    def handle(self, x, y, px, size_px=9.0, round_=False, fill=WHITE, stroke=ACCENT) -> None:
        h = size_px * px / 2.0
        if round_:
            pts = [(x + h * math.cos(a), y + h * math.sin(a))
                   for a in np.linspace(0, 2 * math.pi, 20, endpoint=False)]
        else:
            pts = [(x - h, y - h), (x + h, y - h), (x + h, y + h), (x - h, y + h)]
        self.fill_polygon(pts, fill)
        self.polyline(pts, stroke, px, 1.5, True)

    def dot(self, x, y, px, size_px, rgba) -> None:
        h = size_px * px / 2.0
        pts = [(x + h * math.cos(a), y + h * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
        self.fill_polygon(pts, rgba)
