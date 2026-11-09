"""Modelo dos objetos geométricos do editor.

Cada forma é definida no seu próprio sistema de coordenadas locais,
centrada na origem. A posição, orientação e tamanho no desenho vêm da
matriz de transformação (ver matrix.Transform). Os grupos aplicam a sua
matriz a todos os filhos (padrão Composite / modelação hierárquica):

    M_mundo(filho) = M_mundo(grupo) · M_local(filho)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from . import geometry as geo
from .matrix import Mat3, Transform

Color = tuple  # (r, g, b, a) com componentes em [0, 1]


def new_id(prefix: str = "o") -> str:
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def _color(v, default) -> tuple:
    try:
        c = tuple(float(x) for x in v)
        if len(c) == 3:
            c = c + (1.0,)
        return c[:4]
    except Exception:
        return default


@dataclass
class Style:
    """Aparência de uma forma."""

    fill_mode: str = "color"            # "color" | "texture" | "none"
    fill: Color = (0.36, 0.55, 1.0, 1.0)
    texture: str = "builtin:xadrez"     # "builtin:<nome>" ou "img:<id>"
    texture_repeat: float = 2.0
    stroke: Color = (0.10, 0.12, 0.16, 1.0)
    stroke_width: float = 2.0           # unidades do mundo (0 = sem contorno)
    opacity: float = 1.0

    def copy(self) -> "Style":
        return Style(self.fill_mode, tuple(self.fill), self.texture, self.texture_repeat,
                     tuple(self.stroke), self.stroke_width, self.opacity)

    def to_dict(self) -> dict:
        return {"modo": self.fill_mode, "cor": list(self.fill), "textura": self.texture,
                "repeticoes": self.texture_repeat, "contorno": list(self.stroke),
                "espessura": self.stroke_width, "opacidade": self.opacity}

    @staticmethod
    def from_dict(d: dict) -> "Style":
        s = Style()
        s.fill_mode = d.get("modo", s.fill_mode)
        s.fill = _color(d.get("cor", s.fill), s.fill)
        s.texture = d.get("textura", s.texture)
        s.texture_repeat = float(d.get("repeticoes", s.texture_repeat))
        s.stroke = _color(d.get("contorno", s.stroke), s.stroke)
        s.stroke_width = float(d.get("espessura", s.stroke_width))
        s.opacity = float(d.get("opacidade", s.opacity))
        return s


@dataclass
class Animation:
    """Comportamentos animados de um objeto (transformações em função do tempo)."""

    rotate: float = 0.0       # graus por segundo
    pulse: float = 0.0        # amplitude relativa da escala (0.2 = ±20 %)
    pulse_freq: float = 1.0   # Hz
    osc_x: float = 0.0        # amplitude da oscilação horizontal (unidades do mundo)
    osc_y: float = 0.0        # amplitude da oscilação vertical
    osc_freq: float = 0.5     # Hz
    hue: float = 0.0          # rotação da matiz da cor, graus por segundo

    def active(self) -> bool:
        return bool(self.rotate or self.pulse or self.osc_x or self.osc_y or self.hue)

    def copy(self) -> "Animation":
        return Animation(self.rotate, self.pulse, self.pulse_freq, self.osc_x,
                         self.osc_y, self.osc_freq, self.hue)

    def to_dict(self) -> dict:
        return {"rodar": self.rotate, "pulsar": self.pulse, "freq_pulsar": self.pulse_freq,
                "oscilar_x": self.osc_x, "oscilar_y": self.osc_y, "freq_oscilar": self.osc_freq,
                "matiz": self.hue}

    @staticmethod
    def from_dict(d: dict) -> "Animation":
        return Animation(float(d.get("rodar", 0)), float(d.get("pulsar", 0)),
                         float(d.get("freq_pulsar", 1.0)), float(d.get("oscilar_x", 0)),
                         float(d.get("oscilar_y", 0)), float(d.get("freq_oscilar", 0.5)),
                         float(d.get("matiz", 0)))


class Shape:
    """Classe base de todas as formas."""

    kind = "shape"
    label = "Forma"

    def __init__(self, name: str | None = None):
        self.id = new_id()
        self.name = name or self.label
        self.transform = Transform()
        self.style = Style()
        self.anim = Animation()
        self.visible = True
        self.locked = False
        self.parent = None          # Layer ou GroupShape (não é guardado no ficheiro)
        self._cache: dict = {}      # malhas pré-calculadas pelo renderizador

    # --- geometria local (implementada pelas subclasses) ---------------
    def outline(self) -> list:
        raise NotImplementedError

    @property
    def closed(self) -> bool:
        return True

    @property
    def has_fill(self) -> bool:
        return self.closed

    def fill_triangles(self) -> list:
        """Triângulos do preenchimento (lista plana de pontos, 3 por triângulo)."""
        return geo.fan_triangles(self.outline(), (0.0, 0.0))

    def geom_key(self) -> tuple:
        raise NotImplementedError

    def local_bbox(self):
        return geo.bbox(self.outline())

    def contains_local(self, x: float, y: float) -> bool:
        return self.has_fill and geo.point_in_polygon(x, y, self.outline())

    # --- serialização -------------------------------------------------
    def params_dict(self) -> dict:
        return {}

    def set_params(self, d: dict) -> None:
        pass

    def to_dict(self) -> dict:
        d = {"tipo": self.kind, "id": self.id, "nome": self.name,
             "transformacao": self.transform.to_dict(), "estilo": self.style.to_dict(),
             "animacao": self.anim.to_dict(), "visivel": self.visible, "bloqueado": self.locked}
        d.update(self.params_dict())
        return d

    def clone(self) -> "Shape":
        return shape_from_dict(self.to_dict(), keep_ids=False)

    def invalidate(self) -> None:
        self._cache.clear()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name!r} {self.id}>"


class RectShape(Shape):
    kind = "retangulo"
    label = "Retângulo"

    def __init__(self, w: float = 100.0, h: float = 100.0, name=None):
        super().__init__(name)
        self.w, self.h = float(w), float(h)

    def outline(self):
        return geo.rect_points(self.w, self.h)

    def fill_triangles(self):
        a, b, c, d = self.outline()
        return [a, b, c, a, c, d]

    def contains_local(self, x, y):
        return abs(x) <= self.w / 2 and abs(y) <= self.h / 2

    def geom_key(self):
        return ("rect", self.w, self.h)

    def params_dict(self):
        return {"largura": self.w, "altura": self.h}

    def set_params(self, d):
        self.w = float(d.get("largura", self.w))
        self.h = float(d.get("altura", self.h))


class EllipseShape(Shape):
    kind = "elipse"
    label = "Elipse"
    SEGMENTS = 96

    def __init__(self, rx: float = 50.0, ry: float = 50.0, name=None):
        super().__init__(name)
        self.rx, self.ry = float(rx), float(ry)

    def outline(self):
        return geo.ellipse_points(self.rx, self.ry, self.SEGMENTS)

    def contains_local(self, x, y):
        if self.rx <= 0 or self.ry <= 0:
            return False
        return (x / self.rx) ** 2 + (y / self.ry) ** 2 <= 1.0

    def local_bbox(self):
        return (-self.rx, -self.ry, self.rx, self.ry)

    def geom_key(self):
        return ("ellipse", self.rx, self.ry)

    def params_dict(self):
        return {"rx": self.rx, "ry": self.ry}

    def set_params(self, d):
        self.rx = float(d.get("rx", self.rx))
        self.ry = float(d.get("ry", self.ry))


class TriangleShape(Shape):
    kind = "triangulo"
    label = "Triângulo"

    def __init__(self, w: float = 100.0, h: float = 100.0, name=None):
        super().__init__(name)
        self.w, self.h = float(w), float(h)

    def outline(self):
        return geo.triangle_points(self.w, self.h)

    def fill_triangles(self):
        return list(self.outline())

    def geom_key(self):
        return ("triangle", self.w, self.h)

    def params_dict(self):
        return {"largura": self.w, "altura": self.h}

    def set_params(self, d):
        self.w = float(d.get("largura", self.w))
        self.h = float(d.get("altura", self.h))


class RegularPolygonShape(Shape):
    """Polígono regular; com inner_ratio > 0 é uma estrela."""

    kind = "poligono_regular"
    label = "Polígono regular"

    def __init__(self, sides: int = 6, radius: float = 50.0, inner_ratio: float = 0.0, name=None):
        super().__init__(name)
        self.sides = max(3, int(sides))
        self.radius = float(radius)
        self.inner_ratio = float(inner_ratio)
        if self.inner_ratio > 0 and name is None:
            self.name = "Estrela"

    @property
    def is_star(self) -> bool:
        return self.inner_ratio > 0

    def outline(self):
        return geo.regular_polygon_points(self.sides, self.radius, self.inner_ratio)

    def geom_key(self):
        return ("ngon", self.sides, self.radius, self.inner_ratio)

    def params_dict(self):
        return {"lados": self.sides, "raio": self.radius, "raio_interno": self.inner_ratio}

    def set_params(self, d):
        self.sides = max(3, int(d.get("lados", self.sides)))
        self.radius = float(d.get("raio", self.radius))
        self.inner_ratio = float(d.get("raio_interno", self.inner_ratio))


class PathShape(Shape):
    """Linha poligonal aberta (linha, mão livre) ou fechada (polígono livre)."""

    kind = "caminho"
    label = "Polígono"

    def __init__(self, points=None, closed: bool = True, name=None):
        super().__init__(name)
        self.points = [(float(x), float(y)) for x, y in (points or [])]
        self._closed = bool(closed)
        if not closed and name is None:
            self.name = "Linha" if len(self.points) == 2 else "Traço"

    @property
    def closed(self):
        return self._closed

    def outline(self):
        return list(self.points)

    def fill_triangles(self):
        pts = geo.dedupe(self.points, closed=True)
        if len(pts) < 3:
            return []
        tris = geo.triangulate(pts)
        if tris is None:  # polígono com auto-interseções: aproximação por leque
            return geo.fan_triangles(pts)
        return geo.triangles_from_indices(pts, tris)

    def geom_key(self):
        return ("path", self._closed, tuple(self.points))

    def params_dict(self):
        return {"pontos": [list(p) for p in self.points], "fechado": self._closed}

    def set_params(self, d):
        self.points = [(float(x), float(y)) for x, y in d.get("pontos", self.points)]
        self._closed = bool(d.get("fechado", self._closed))


class ImageShape(Shape):
    """Imagem digital (PNG/JPG) desenhada como um retângulo com textura."""

    kind = "imagem"
    label = "Imagem"

    def __init__(self, w: float = 200.0, h: float = 150.0, image_id: str = "", name=None):
        super().__init__(name)
        self.w, self.h = float(w), float(h)
        self.image_id = image_id
        self.filters: list[str] = []
        self.style.stroke_width = 0.0
        self.style.fill_mode = "image"

    def outline(self):
        return geo.rect_points(self.w, self.h)

    def fill_triangles(self):
        a, b, c, d = self.outline()
        return [a, b, c, a, c, d]

    def contains_local(self, x, y):
        return abs(x) <= self.w / 2 and abs(y) <= self.h / 2

    def geom_key(self):
        return ("rect", self.w, self.h)

    def params_dict(self):
        return {"largura": self.w, "altura": self.h, "imagem": self.image_id,
                "filtros": list(self.filters)}

    def set_params(self, d):
        self.w = float(d.get("largura", self.w))
        self.h = float(d.get("altura", self.h))
        self.image_id = d.get("imagem", self.image_id)
        self.filters = list(d.get("filtros", self.filters))
        self.style.fill_mode = "image"


class GroupShape(Shape):
    """Agrupamento: aplica a sua matriz a todos os filhos."""

    kind = "grupo"
    label = "Grupo"

    def __init__(self, children=None, name=None):
        super().__init__(name)
        self.children: list[Shape] = []
        self.style.stroke_width = 0.0
        self.style.fill_mode = "none"
        for c in children or []:
            self.add(c)

    def add(self, child: Shape, index: int | None = None) -> None:
        child.parent = self
        if index is None:
            self.children.append(child)
        else:
            self.children.insert(index, child)

    def remove(self, child: Shape) -> None:
        self.children.remove(child)
        child.parent = None

    @property
    def has_fill(self):
        return False

    def local_bbox(self):
        b = None
        for c in self.children:
            m = c.transform.matrix()
            cb = geo.bbox(m.apply_many(geo.bbox_corners(c.local_bbox())))
            b = geo.bbox_union(b, cb)
        return b or (0.0, 0.0, 0.0, 0.0)

    def outline(self):
        return geo.bbox_corners(self.local_bbox())

    def fill_triangles(self):
        return []

    def contains_local(self, x, y):
        for c in self.children:
            if not c.visible:
                continue
            try:
                lx, ly = c.transform.matrix().inverse().apply(x, y)
            except ZeroDivisionError:
                continue
            if c.contains_local(lx, ly):
                return True
        return False

    def geom_key(self):
        return ("group", self.id)

    def params_dict(self):
        return {"filhos": [c.to_dict() for c in self.children]}

    def set_params(self, d, keep_ids: bool = True):
        self.children = []
        for cd in d.get("filhos", []):
            self.add(shape_from_dict(cd, keep_ids=keep_ids))


SHAPE_TYPES = {cls.kind: cls for cls in
               (RectShape, EllipseShape, TriangleShape, RegularPolygonShape,
                PathShape, ImageShape, GroupShape)}


def shape_from_dict(d: dict, keep_ids: bool = True) -> Shape:
    cls = SHAPE_TYPES.get(d.get("tipo"))
    if cls is None:
        raise ValueError(f"tipo de objeto desconhecido: {d.get('tipo')!r}")
    s = cls.__new__(cls)
    Shape.__init__(s, d.get("nome"))
    # valores por omissão específicos de cada classe
    if cls is RectShape or cls is TriangleShape:
        s.w = s.h = 100.0
    elif cls is EllipseShape:
        s.rx = s.ry = 50.0
    elif cls is RegularPolygonShape:
        s.sides, s.radius, s.inner_ratio = 6, 50.0, 0.0
    elif cls is PathShape:
        s.points, s._closed = [], True
    elif cls is ImageShape:
        s.w, s.h, s.image_id, s.filters = 200.0, 150.0, "", []
    elif cls is GroupShape:
        s.children = []
    if keep_ids and d.get("id"):
        s.id = d["id"]
    s.transform = Transform.from_dict(d.get("transformacao", {}))
    s.style = Style.from_dict(d.get("estilo", {}))
    s.anim = Animation.from_dict(d.get("animacao", {}))
    s.visible = bool(d.get("visivel", True))
    s.locked = bool(d.get("bloqueado", False))
    if cls is GroupShape:
        s.set_params(d, keep_ids=keep_ids)
    else:
        s.set_params(d)
    return s


# ----------------------------------------------------------------------
# Navegação na hierarquia
# ----------------------------------------------------------------------
def world_matrix(shape: Shape) -> Mat3:
    """Matriz local → mundo: produto das matrizes de todos os grupos acima."""
    m = shape.transform.matrix()
    p = shape.parent
    while isinstance(p, GroupShape):
        m = p.transform.matrix() @ m
        p = p.parent
    return m


def parent_world_matrix(shape: Shape) -> Mat3:
    p = shape.parent
    if isinstance(p, GroupShape):
        return world_matrix(p)
    return Mat3.identity()


def iter_tree(shapes):
    """Percorre as formas e todos os descendentes (pré-ordem)."""
    for s in shapes:
        yield s
        if isinstance(s, GroupShape):
            yield from iter_tree(s.children)


def leaves(shape: Shape):
    if isinstance(shape, GroupShape):
        for c in shape.children:
            yield from leaves(c)
    else:
        yield shape


def world_outline(shape: Shape) -> list:
    return world_matrix(shape).apply_many(shape.outline())


def world_bbox(shape: Shape):
    """Caixa envolvente alinhada aos eixos, em coordenadas do mundo."""
    if isinstance(shape, GroupShape):
        b = None
        for c in shape.children:
            b = geo.bbox_union(b, world_bbox(c))
        return b or (0.0, 0.0, 0.0, 0.0)
    return geo.bbox(world_outline(shape))
