"""Conversão da geometria em malhas de triângulos (arrays numpy para o OpenGL).

- Preenchimento: triângulos em coordenadas locais + coordenadas de textura
  (u, v) obtidas pelo mapeamento planar da caixa envolvente da forma.
- Contorno: uma "fita" (GL_TRIANGLE_STRIP) com a espessura pedida, com
  junções em esquadria (miter). É gerada em coordenadas do mundo, por isso a
  espessura não muda quando o objeto é escalado.
"""

from __future__ import annotations

import numpy as np


def fill_arrays(shape):
    """(vértices, uvs) do preenchimento em coordenadas locais, ou (None, None)."""
    tris = shape.fill_triangles()
    if not tris:
        return None, None
    verts = np.asarray(tris, dtype=np.float32).reshape(-1, 2)
    x0, y0, x1, y1 = shape.local_bbox()
    w = max(x1 - x0, 1e-9)
    h = max(y1 - y0, 1e-9)
    u = (verts[:, 0] - x0) / w
    v = (y1 - verts[:, 1]) / h          # v invertido: o topo da imagem fica no topo da forma
    uvs = np.stack([u, v], axis=1).astype(np.float32)
    return np.ascontiguousarray(verts), np.ascontiguousarray(uvs)


def transform_points(points: np.ndarray, m) -> np.ndarray:
    """Aplica uma Mat3 a um array N×2: p' = A·p + t (forma vetorizada)."""
    a, b, tx, c, d, ty = m.m[0], m.m[1], m.m[2], m.m[3], m.m[4], m.m[5]
    x = points[:, 0]
    y = points[:, 1]
    return np.stack([a * x + b * y + tx, c * x + d * y + ty], axis=1)


def _unit(v: np.ndarray) -> np.ndarray:
    length = np.hypot(v[:, 0], v[:, 1])[:, None]
    length[length < 1e-12] = 1.0
    return v / length


def stroke_strip(points, half_width: float, closed: bool, miter_limit: float = 4.0):
    """Fita de triângulos que contorna a linha poligonal `points` (N×2)."""
    p = np.asarray(points, dtype=np.float64)
    if len(p) >= 2:
        d = np.diff(p, axis=0)
        keep = np.ones(len(p), dtype=bool)
        keep[1:] = np.hypot(d[:, 0], d[:, 1]) > 1e-9
        p = p[keep]
    if closed and len(p) > 2 and np.hypot(*(p[0] - p[-1])) < 1e-9:
        p = p[:-1]
    n = len(p)
    if n < 2:
        return None
    if closed:
        d_in = p - np.roll(p, 1, axis=0)
        d_out = np.roll(p, -1, axis=0) - p
    else:
        d_out = np.empty_like(p)
        d_out[:-1] = p[1:] - p[:-1]
        d_out[-1] = d_out[-2]
        d_in = np.empty_like(p)
        d_in[1:] = p[1:] - p[:-1]
        d_in[0] = d_out[0]
    t_in, t_out = _unit(d_in), _unit(d_out)
    n_in = np.stack([-t_in[:, 1], t_in[:, 0]], axis=1)      # normais à esquerda
    n_out = np.stack([-t_out[:, 1], t_out[:, 0]], axis=1)
    m = n_in + n_out                                        # direção da esquadria (bissetriz)
    ml = np.hypot(m[:, 0], m[:, 1])
    bad = ml < 1e-9                                         # inversão de 180°
    m[bad] = n_out[bad]
    ml[bad] = 1.0
    m = m / ml[:, None]
    cos_half = np.clip(np.sum(m * n_out, axis=1), 1.0 / miter_limit, None)
    offset = m * (half_width / cos_half)[:, None]
    strip = np.empty((2 * n, 2))
    strip[0::2] = p + offset
    strip[1::2] = p - offset
    if closed:
        strip = np.vstack([strip, strip[:2]])
    return np.ascontiguousarray(strip, dtype=np.float32)
