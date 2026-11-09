"""Transformação janela → visor (window-to-viewport) sem distorção.

A "janela" é o retângulo do mundo que se quer ver, [xw_min, xw_max] × [yw_min, yw_max];
o "visor" é a área do ecrã onde é desenhado, [0, largura] × [0, altura] pixels.

    xv = (xw − xw_min) · sx         sx = largura / (xw_max − xw_min)
    yv = (yw_max − yw) · sy         sy = altura  / (yw_max − yw_min)

Não há distorção quando sx = sy. Para o garantir, a janela é calculada a
partir do visor: centro (cx, cy) e zoom (pixels por unidade do mundo) fixos,
e a largura/altura da janela = tamanho do visor / zoom. Quando o utilizador
redimensiona a janela do programa, o desenho não estica: vê-se mais ou
menos área do mundo, sempre com a mesma escala nos dois eixos.

Para demonstração existe um modo "com distorção", em que a janela do mundo
fica fixa e o desenho estica quando o visor muda de proporção.
"""

from __future__ import annotations


class Camera:
    MIN_ZOOM = 0.02
    MAX_ZOOM = 64.0

    def __init__(self):
        self.cx = 640.0
        self.cy = 360.0
        self.zoom = 1.0          # pixels por unidade do mundo
        self.vw = 1              # tamanho do visor (pixels lógicos)
        self.vh = 1
        self.keep_aspect = True
        self._fixed = None       # janela fixa (modo com distorção)

    # ------------------------------------------------------------------
    def resize(self, w: int, h: int) -> None:
        self.vw, self.vh = max(1, int(w)), max(1, int(h))

    def window(self) -> tuple[float, float, float, float]:
        """Janela do mundo visível: (esquerda, direita, baixo, cima)."""
        if not self.keep_aspect and self._fixed is not None:
            return self._fixed
        hw = self.vw / (2.0 * self.zoom)
        hh = self.vh / (2.0 * self.zoom)
        return (self.cx - hw, self.cx + hw, self.cy - hh, self.cy + hh)

    def scale_factors(self) -> tuple[float, float]:
        l, r, b, t = self.window()
        return self.vw / (r - l), self.vh / (t - b)

    def px(self) -> float:
        """Tamanho de um pixel em unidades do mundo (média dos dois eixos)."""
        sx, sy = self.scale_factors()
        return 2.0 / (sx + sy)

    def is_distorted(self) -> bool:
        sx, sy = self.scale_factors()
        return abs(sx - sy) > 1e-6 * max(sx, sy)

    # ------------------------------------------------------------------
    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        l, r, b, t = self.window()
        return (l + sx * (r - l) / self.vw, t - sy * (t - b) / self.vh)

    def world_to_screen(self, x: float, y: float) -> tuple[float, float]:
        l, r, b, t = self.window()
        return ((x - l) * self.vw / (r - l), (t - y) * self.vh / (t - b))

    # ------------------------------------------------------------------
    def zoom_at(self, sx: float, sy: float, factor: float) -> None:
        """Zoom mantendo fixo o ponto do mundo que está sob o cursor."""
        wx, wy = self.screen_to_world(sx, sy)
        if self.keep_aspect:
            self.zoom = min(self.MAX_ZOOM, max(self.MIN_ZOOM, self.zoom * factor))
            self.cx = wx - (sx - self.vw / 2.0) / self.zoom
            self.cy = wy + (sy - self.vh / 2.0) / self.zoom
        else:
            l, r, b, t = self._fixed
            k = 1.0 / factor
            self._fixed = (wx + (l - wx) * k, wx + (r - wx) * k, wy + (b - wy) * k, wy + (t - wy) * k)

    def set_zoom(self, zoom: float) -> None:
        self.zoom = min(self.MAX_ZOOM, max(self.MIN_ZOOM, zoom))

    def pan(self, dx_px: float, dy_px: float) -> None:
        """Desloca a vista (dx, dy em pixels do ecrã)."""
        if self.keep_aspect:
            self.cx -= dx_px / self.zoom
            self.cy += dy_px / self.zoom
        else:
            sx, sy = self.scale_factors()
            l, r, b, t = self._fixed
            ddx, ddy = -dx_px / sx, dy_px / sy
            self._fixed = (l + ddx, r + ddx, b + ddy, t + ddy)

    def center_on(self, x: float, y: float) -> None:
        if self.keep_aspect:
            self.cx, self.cy = x, y
        else:
            l, r, b, t = self._fixed
            hw, hh = (r - l) / 2, (t - b) / 2
            self._fixed = (x - hw, x + hw, y - hh, y + hh)

    def fit(self, x0: float, y0: float, x1: float, y1: float, margin: float = 0.9) -> None:
        """Enquadra o retângulo no visor com a maior escala uniforme possível."""
        w, h = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
        if self.keep_aspect:
            self.zoom = min(self.MAX_ZOOM, max(self.MIN_ZOOM, margin * min(self.vw / w, self.vh / h)))
            self.cx, self.cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        else:
            mx, my = w * (1 - margin) / 2, h * (1 - margin) / 2
            self._fixed = (x0 - mx, x1 + mx, y0 - my, y1 + my)

    def set_keep_aspect(self, keep: bool) -> None:
        if keep == self.keep_aspect:
            return
        if not keep:
            self._fixed = self.window()
            self.keep_aspect = False
        else:
            l, r, b, t = self._fixed or self.window()
            self.keep_aspect = True
            self.cx, self.cy = (l + r) / 2.0, (b + t) / 2.0
            self.zoom = min(self.vw / (r - l), self.vh / (t - b))
            self._fixed = None
