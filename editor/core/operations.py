"""Operações de edição sobre o documento (agrupar, ordenar, apagar, ...).

Todas as operações preservam a posição dos objetos no mundo: quando um
objeto muda de contentor (por exemplo, ao entrar num grupo), a sua nova
matriz local é calculada por

    M_local_novo = (M_mundo_do_novo_pai)^-1 · M_mundo_do_objeto

e depois decomposta nos parâmetros T, R, Sh e S.
"""

from __future__ import annotations

from . import geometry as geo
from .document import Document, Layer
from .matrix import Mat3, Transform
from .shapes import GroupShape, Shape, parent_world_matrix, world_bbox, world_matrix


def children_of(container) -> list[Shape]:
    return container.objects if isinstance(container, Layer) else container.children


def container_world_matrix(container) -> Mat3:
    if isinstance(container, GroupShape):
        return world_matrix(container)
    return Mat3.identity()


def set_world_matrix(shape: Shape, new_world: Mat3) -> None:
    """Altera os parâmetros do objeto para que a sua matriz do mundo seja new_world."""
    local = parent_world_matrix(shape).inverse() @ new_world
    shape.transform = Transform.from_matrix(local, reference=shape.transform)


def translate_world(shape: Shape, dx: float, dy: float) -> None:
    """Translação no referencial do mundo (convertida para o referencial do pai)."""
    p = parent_world_matrix(shape)
    if p.almost_equal(Mat3.identity(), 1e-12):
        ldx, ldy = dx, dy
    else:
        ldx, ldy = p.inverse().apply_vector(dx, dy)
    shape.transform.tx += ldx
    shape.transform.ty += ldy


def drawing_order(doc: Document) -> dict[str, int]:
    return {s.id: i for i, s in enumerate(doc.iter_objects())}


def sort_by_drawing_order(doc: Document, shapes) -> list[Shape]:
    order = drawing_order(doc)
    return sorted(shapes, key=lambda s: order.get(s.id, -1))


def without_descendants(shapes) -> list[Shape]:
    """Remove da lista os objetos cujo antecessor também está na lista."""
    ids = {s.id for s in shapes}
    out = []
    for s in shapes:
        p = s.parent
        nested = False
        while isinstance(p, GroupShape):
            if p.id in ids:
                nested = True
                break
            p = p.parent
        if not nested:
            out.append(s)
    return out


def selection_bbox(shapes):
    b = None
    for s in shapes:
        b = geo.bbox_union(b, world_bbox(s))
    return b


# ----------------------------------------------------------------------
# Agrupar / desagrupar
# ----------------------------------------------------------------------
def group_shapes(doc: Document, shapes) -> GroupShape | None:
    shapes = without_descendants(list(shapes))
    if len(shapes) < 2:
        return None
    ordered = sort_by_drawing_order(doc, shapes)
    top = ordered[-1]
    container = top.parent
    index = children_of(container).index(top)
    worlds = {s.id: world_matrix(s) for s in ordered}
    b = selection_bbox(ordered)
    cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0

    for s in ordered:
        lst = children_of(s.parent)
        if s.parent is container and lst.index(s) < index:
            index -= 1
        s.parent.remove(s)

    group = GroupShape(name="Grupo")
    container.add(group, index)
    # o grupo nasce com o pivô no centro da seleção
    pw = container_world_matrix(container)
    group.transform = Transform.from_matrix(pw.inverse() @ Mat3.translation(cx, cy))
    g_inv = world_matrix(group).inverse()
    for s in ordered:
        group.add(s)
        s.transform = Transform.from_matrix(g_inv @ worlds[s.id], reference=s.transform)
    return group


def ungroup(group: GroupShape) -> list[Shape]:
    container = group.parent
    lst = children_of(container)
    index = lst.index(group)
    gm = group.transform.matrix()
    container.remove(group)
    children = list(group.children)
    for i, c in enumerate(children):
        local = gm @ c.transform.matrix()
        c.parent = None
        c.transform = Transform.from_matrix(local, reference=c.transform)
        c.style.opacity *= group.style.opacity
        container.add(c, index + i)
    group.children = []
    return children


# ----------------------------------------------------------------------
# Apagar / duplicar / mover entre camadas
# ----------------------------------------------------------------------
def delete_shapes(shapes) -> None:
    for s in without_descendants(list(shapes)):
        if s.parent is not None:
            s.parent.remove(s)


def duplicate_shapes(doc: Document, shapes, offset=(20.0, -20.0)) -> list[Shape]:
    out = []
    for s in sort_by_drawing_order(doc, without_descendants(list(shapes))):
        c = s.clone()
        container = s.parent
        idx = children_of(container).index(s)
        container.add(c, idx + 1)
        translate_world(c, offset[0], offset[1])
        out.append(c)
    return out


def move_to_layer(doc: Document, shapes, layer: Layer) -> None:
    for s in sort_by_drawing_order(doc, without_descendants(list(shapes))):
        w = world_matrix(s)
        if s.parent is not None:
            s.parent.remove(s)
        layer.add(s)
        s.transform = Transform.from_matrix(w, reference=s.transform)


# ----------------------------------------------------------------------
# Ordem de desenho (z-order)
# ----------------------------------------------------------------------
def _by_container(shapes):
    groups: dict[int, tuple] = {}
    for s in without_descendants(list(shapes)):
        key = id(s.parent)
        groups.setdefault(key, (s.parent, []))[1].append(s)
    return groups.values()


def bring_forward(shapes) -> None:
    for container, items in _by_container(shapes):
        lst = children_of(container)
        for s in sorted(items, key=lst.index, reverse=True):
            i = lst.index(s)
            if i < len(lst) - 1 and lst[i + 1] not in items:
                lst[i], lst[i + 1] = lst[i + 1], lst[i]


def send_backward(shapes) -> None:
    for container, items in _by_container(shapes):
        lst = children_of(container)
        for s in sorted(items, key=lst.index):
            i = lst.index(s)
            if i > 0 and lst[i - 1] not in items:
                lst[i], lst[i - 1] = lst[i - 1], lst[i]


def bring_to_front(shapes) -> None:
    for container, items in _by_container(shapes):
        lst = children_of(container)
        ordered = sorted(items, key=lst.index)
        for s in ordered:
            lst.remove(s)
        lst.extend(ordered)


def send_to_back(shapes) -> None:
    for container, items in _by_container(shapes):
        lst = children_of(container)
        ordered = sorted(items, key=lst.index)
        for s in ordered:
            lst.remove(s)
        lst[0:0] = ordered


# ----------------------------------------------------------------------
# Transformações aplicadas a uma seleção (teclado e menus)
# ----------------------------------------------------------------------
def rotate_shapes(shapes, degrees: float) -> None:
    shapes = without_descendants(list(shapes))
    b = selection_bbox(shapes)
    if b is None:
        return
    c = ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)
    r = Mat3.rotation_about(degrees, *c)
    for s in shapes:
        set_world_matrix(s, r @ world_matrix(s))


def scale_shapes(shapes, factor: float) -> None:
    shapes = without_descendants(list(shapes))
    b = selection_bbox(shapes)
    if b is None:
        return
    c = ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)
    m = Mat3.scaling_about(factor, factor, *c)
    for s in shapes:
        set_world_matrix(s, m @ world_matrix(s))


def flip_shapes(shapes, horizontal: bool = True) -> None:
    """Espelha. Um objeto sozinho espelha nos seus eixos locais (sx ou sy muda
    de sinal); vários objetos espelham em conjunto em torno do centro da seleção."""
    shapes = without_descendants(list(shapes))
    if len(shapes) == 1:
        t = shapes[0].transform
        if horizontal:
            t.sx = -t.sx
        else:
            t.sy = -t.sy
        return
    b = selection_bbox(shapes)
    if b is None:
        return
    c = ((b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0)
    m = Mat3.scaling_about(-1.0 if horizontal else 1.0, 1.0 if horizontal else -1.0, *c)
    for s in shapes:
        set_world_matrix(s, m @ world_matrix(s))
