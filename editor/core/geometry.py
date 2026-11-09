"""Algoritmos geométricos usados pelo editor (sem dependências de Qt/OpenGL).

- Geração de primitivas (retângulo, elipse, polígono regular, estrela).
- Triangulação de polígonos simples por "ear clipping" (corte de orelhas),
  necessária para preencher polígonos côncavos.
- Ponto-dentro-de-polígono por lançamento de raio (regra par-ímpar).
- Distância ponto-segmento (seleção de linhas).
- Simplificação de traços à mão livre (Ramer–Douglas–Peucker).
"""

from __future__ import annotations

import math

Point = tuple[float, float]


# ----------------------------------------------------------------------
# Primitivas (pontos em coordenadas locais, centradas na origem)
# ----------------------------------------------------------------------
def rect_points(w: float, h: float) -> list[Point]:
    hw, hh = w / 2.0, h / 2.0
    return [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]


def triangle_points(w: float, h: float) -> list[Point]:
    hw, hh = w / 2.0, h / 2.0
    return [(-hw, -hh), (hw, -hh), (0.0, hh)]


def ellipse_points(rx: float, ry: float, segments: int = 96) -> list[Point]:
    """Pontos da elipse pela forma paramétrica x = rx·cos t, y = ry·sin t."""
    return [(rx * math.cos(2 * math.pi * i / segments),
             ry * math.sin(2 * math.pi * i / segments)) for i in range(segments)]


def regular_polygon_points(sides: int, radius: float, inner_ratio: float = 0.0,
                           start_deg: float = 90.0) -> list[Point]:
    """Polígono regular de `sides` lados; com inner_ratio > 0 gera uma estrela."""
    sides = max(3, int(sides))
    pts: list[Point] = []
    if inner_ratio and inner_ratio > 0:
        n = sides * 2
        for i in range(n):
            r = radius if i % 2 == 0 else radius * inner_ratio
            a = math.radians(start_deg) + math.pi * i / sides
            pts.append((r * math.cos(a), r * math.sin(a)))
    else:
        for i in range(sides):
            a = math.radians(start_deg) + 2 * math.pi * i / sides
            pts.append((radius * math.cos(a), radius * math.sin(a)))
    return pts


# ----------------------------------------------------------------------
# Caixas envolventes
# ----------------------------------------------------------------------
def bbox(points) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    if not xs:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def bbox_union(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def bbox_corners(b) -> list[Point]:
    x0, y0, x1, y1 = b
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def rects_intersect(a, b) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def centroid_of_bbox(points) -> Point:
    x0, y0, x1, y1 = bbox(points)
    return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)


# ----------------------------------------------------------------------
# Testes de pertença e distâncias
# ----------------------------------------------------------------------
def polygon_area(points) -> float:
    """Área com sinal (fórmula do laço / shoelace): > 0 se anti-horário."""
    s = 0.0
    n = len(points)
    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def point_in_polygon(x: float, y: float, points) -> bool:
    """Lançamento de raio horizontal (regra par-ímpar)."""
    inside = False
    n = len(points)
    j = n - 1
    for i in range(n):
        xi, yi = points[i]
        xj, yj = points[j]
        if (yi > y) != (yj > y):
            x_cross = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def dist_point_segment(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 <= 1e-18:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def dist_point_polyline(px, py, points, closed: bool) -> float:
    n = len(points)
    if n == 0:
        return float("inf")
    if n == 1:
        return math.hypot(px - points[0][0], py - points[0][1])
    best = float("inf")
    last = n if closed else n - 1
    for i in range(last):
        ax, ay = points[i]
        bx, by = points[(i + 1) % n]
        best = min(best, dist_point_segment(px, py, ax, ay, bx, by))
    return best


# ----------------------------------------------------------------------
# Triangulação por ear clipping
# ----------------------------------------------------------------------
def _cross(a: Point, b: Point, c: Point) -> float:
    """Produto vetorial (b − a) × (c − b): > 0 se a curva em b é para a esquerda."""
    return (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])


def _point_in_triangle(p: Point, a: Point, b: Point, c: Point) -> bool:
    """Teste estrito para um triângulo em sentido anti-horário."""
    def side(p1, p2, p3):
        return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
    return side(a, b, p) > 1e-12 and side(b, c, p) > 1e-12 and side(c, a, p) > 1e-12


def dedupe(points, closed: bool = True, eps: float = 1e-9) -> list[Point]:
    out: list[Point] = []
    for p in points:
        if not out or abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append((float(p[0]), float(p[1])))
    if closed and len(out) > 1 and abs(out[0][0] - out[-1][0]) <= eps and abs(out[0][1] - out[-1][1]) <= eps:
        out.pop()
    return out


def triangulate(points) -> list[tuple[int, int, int]] | None:
    """Triangula um polígono simples (convexo ou côncavo) por corte de orelhas.

    Uma "orelha" é um vértice convexo cujo triângulo (anterior, vértice,
    seguinte) não contém nenhum outro vértice do polígono. Corta-se uma
    orelha de cada vez até restar um triângulo.
    Devolve triplos de índices, ou None se o polígono não for simples.
    """
    n = len(points)
    if n < 3:
        return []
    idx = list(range(n))
    if polygon_area(points) < 0:      # garantir sentido anti-horário
        idx.reverse()
    tris: list[tuple[int, int, int]] = []
    guard = 0
    while len(idx) > 3:
        guard += 1
        if guard > 4 * n * n + 10:
            return None
        m = len(idx)
        clipped = False
        for k in range(m):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = points[i0], points[i1], points[i2]
            cr = _cross(a, b, c)
            if abs(cr) <= 1e-12:          # vértice colinear: retira-se sem triângulo
                del idx[k]
                clipped = True
                break
            if cr < 0:                     # vértice reflexo: não é orelha
                continue
            if any(_point_in_triangle(points[j], a, b, c)
                   for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            del idx[k]
            clipped = True
            break
        if not clipped:
            return None
    if len(idx) == 3 and abs(_cross(points[idx[0]], points[idx[1]], points[idx[2]])) > 1e-12:
        tris.append((idx[0], idx[1], idx[2]))
    return tris


def fan_triangles(points, center: Point | None = None) -> list[Point]:
    """Leque de triângulos a partir do centro (válido para formas estreladas)."""
    if center is None:
        center = centroid_of_bbox(points)
    out: list[Point] = []
    n = len(points)
    for i in range(n):
        out.extend((center, points[i], points[(i + 1) % n]))
    return out


def triangles_from_indices(points, tris) -> list[Point]:
    out: list[Point] = []
    for i0, i1, i2 in tris:
        out.extend((points[i0], points[i1], points[i2]))
    return out


# ----------------------------------------------------------------------
# Simplificação Ramer–Douglas–Peucker
# ----------------------------------------------------------------------
def simplify_rdp(points, epsilon: float) -> list[Point]:
    """Mantém só os pontos que se afastam mais de `epsilon` da reta simplificada."""
    pts = list(points)
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        s, e = stack.pop()
        dmax, imax = 0.0, -1
        ax, ay = pts[s]
        bx, by = pts[e]
        for i in range(s + 1, e):
            d = dist_point_segment(pts[i][0], pts[i][1], ax, ay, bx, by)
            if d > dmax:
                dmax, imax = d, i
        if imax > 0 and dmax > epsilon:
            keep[imax] = True
            stack.append((s, imax))
            stack.append((imax, e))
    return [p for p, k in zip(pts, keep) if k]


# ----------------------------------------------------------------------
# Auxiliares de interação
# ----------------------------------------------------------------------
def snap(value: float, step: float) -> float:
    if step <= 0:
        return value
    return round(value / step) * step


def snap_angle(dx: float, dy: float, step_deg: float = 15.0) -> tuple[float, float]:
    """Arredonda a direção do vetor (dx, dy) a múltiplos de step_deg."""
    length = math.hypot(dx, dy)
    if length < 1e-12:
        return dx, dy
    ang = math.degrees(math.atan2(dy, dx))
    ang = round(ang / step_deg) * step_deg
    return length * math.cos(math.radians(ang)), length * math.sin(math.radians(ang))
