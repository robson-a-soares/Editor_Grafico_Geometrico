"""Seleção de objetos com o mouse (picking).

Para saber se um clique (x, y) do mundo cai dentro de um objeto, levamos o
ponto para as coordenadas locais do objeto com a matriz inversa,

    p_local = (M_mundo)^-1 · p_mundo

e testamos contra a forma original (retângulo, elipse, polígono). Assim o
teste funciona para qualquer rotação, escala ou cisalhamento.
"""

from __future__ import annotations

from . import geometry as geo
from .document import Document
from .shapes import GroupShape, Shape, world_bbox, world_matrix


def shape_hit(shape: Shape, x: float, y: float, tol: float) -> bool:
    if not shape.visible:
        return False
    if isinstance(shape, GroupShape):
        return any(shape_hit(c, x, y, tol) for c in reversed(shape.children))
    wm = world_matrix(shape)
    try:
        lx, ly = wm.inverse().apply(x, y)
    except ZeroDivisionError:
        return False
    if shape.has_fill and shape.style.fill_mode != "none" and shape.contains_local(lx, ly):
        return True
    # perto do contorno (também serve para linhas e formas sem preenchimento)
    pts = wm.apply_many(shape.outline())
    sw = max(0.0, shape.style.stroke_width)
    return geo.dist_point_polyline(x, y, pts, shape.closed) <= tol + sw / 2.0


def hit_test(doc: Document, x: float, y: float, tol: float) -> Shape | None:
    """Objeto de topo mais acima (camada e ordem) que contém o ponto."""
    for layer in reversed(doc.layers):
        if not layer.visible or layer.locked:
            continue
        for s in reversed(layer.objects):
            if s.visible and not s.locked and shape_hit(s, x, y, tol):
                return s
    return None


def objects_in_rect(doc: Document, rect) -> list[Shape]:
    """Objetos de topo cuja caixa envolvente interseta o retângulo (seleção por área)."""
    out = []
    for layer in doc.layers:
        if not layer.visible or layer.locked:
            continue
        for s in layer.objects:
            if s.visible and not s.locked and geo.rects_intersect(world_bbox(s), rect):
                out.append(s)
    return out
