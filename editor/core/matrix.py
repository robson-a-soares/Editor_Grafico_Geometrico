"""Matrizes 3x3 em coordenadas homogéneas para transformações geométricas 2D.

Um ponto (x, y) é representado pelo vetor coluna [x, y, 1]^T e uma
transformação afim 2D é uma matriz 3x3:

        | a  b  tx |        x' = a·x + b·y + tx
    M = | c  d  ty |        y' = c·x + d·y + ty
        | 0  0  1  |

Cada objeto do editor guarda os seus parâmetros (translação, rotação,
cisalhamento e escala) e a sua matriz é obtida pela composição

    M = T(tx, ty) · R(θ) · Sh(k) · S(sx, sy)

isto é, sobre o ponto atua primeiro a escala, depois o cisalhamento, depois
a rotação e por fim a translação.

Toda a matemática é feita aqui, à mão. O OpenGL recebe apenas a matriz
final (glMultMatrixf); o código não usa glTranslatef/glRotatef/glScalef.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

EPS = 1e-12


class Mat3:
    """Matriz 3x3 guardada por linhas: [m00, m01, m02, m10, m11, m12, m20, m21, m22]."""

    __slots__ = ("m",)

    def __init__(self, values=None):
        if values is None:
            self.m = [1.0, 0.0, 0.0,
                      0.0, 1.0, 0.0,
                      0.0, 0.0, 1.0]
        else:
            self.m = [float(v) for v in values]
            if len(self.m) != 9:
                raise ValueError("uma Mat3 precisa de 9 valores")

    # ------------------------------------------------------------------
    # Matrizes elementares
    # ------------------------------------------------------------------
    @staticmethod
    def identity() -> "Mat3":
        return Mat3()

    @staticmethod
    def translation(tx: float, ty: float) -> "Mat3":
        """T(tx, ty)."""
        return Mat3([1, 0, tx,
                     0, 1, ty,
                     0, 0, 1])

    @staticmethod
    def rotation(degrees: float) -> "Mat3":
        """R(θ): rotação em torno da origem, sentido anti-horário."""
        r = math.radians(degrees)
        c, s = math.cos(r), math.sin(r)
        return Mat3([c, -s, 0,
                     s, c, 0,
                     0, 0, 1])

    @staticmethod
    def scaling(sx: float, sy: float) -> "Mat3":
        """S(sx, sy): escala em relação à origem (valores negativos espelham)."""
        return Mat3([sx, 0, 0,
                     0, sy, 0,
                     0, 0, 1])

    @staticmethod
    def shearing(k: float) -> "Mat3":
        """Sh(k): cisalhamento horizontal, x' = x + k·y."""
        return Mat3([1, k, 0,
                     0, 1, 0,
                     0, 0, 1])

    @staticmethod
    def rotation_about(degrees: float, px: float, py: float) -> "Mat3":
        """Rotação em torno de um ponto arbitrário P: T(P) · R(θ) · T(-P)."""
        return Mat3.translation(px, py) @ Mat3.rotation(degrees) @ Mat3.translation(-px, -py)

    @staticmethod
    def scaling_about(sx: float, sy: float, px: float, py: float) -> "Mat3":
        """Escala em relação a um ponto fixo P: T(P) · S(sx, sy) · T(-P)."""
        return Mat3.translation(px, py) @ Mat3.scaling(sx, sy) @ Mat3.translation(-px, -py)

    # ------------------------------------------------------------------
    # Operações
    # ------------------------------------------------------------------
    def __matmul__(self, other: "Mat3") -> "Mat3":
        """Produto matricial C = A·B, com C[i][j] = Σk A[i][k]·B[k][j]."""
        a, b = self.m, other.m
        c = [0.0] * 9
        for i in range(3):
            for j in range(3):
                c[3 * i + j] = (a[3 * i] * b[j]
                                + a[3 * i + 1] * b[3 + j]
                                + a[3 * i + 2] * b[6 + j])
        return Mat3(c)

    def apply(self, x: float, y: float) -> tuple[float, float]:
        """Transforma o ponto (x, y): [x', y', 1]^T = M · [x, y, 1]^T."""
        m = self.m
        return (m[0] * x + m[1] * y + m[2],
                m[3] * x + m[4] * y + m[5])

    def apply_vector(self, x: float, y: float) -> tuple[float, float]:
        """Transforma um vetor (direção): a translação não se aplica."""
        m = self.m
        return (m[0] * x + m[1] * y, m[3] * x + m[4] * y)

    def apply_many(self, points) -> list[tuple[float, float]]:
        return [self.apply(x, y) for x, y in points]

    def determinant(self) -> float:
        m = self.m
        return (m[0] * (m[4] * m[8] - m[5] * m[7])
                - m[1] * (m[3] * m[8] - m[5] * m[6])
                + m[2] * (m[3] * m[7] - m[4] * m[6]))

    def linear_scale(self) -> float:
        """Fator de escala médio da parte linear: sqrt(|det|)."""
        return math.sqrt(abs(self.m[0] * self.m[4] - self.m[1] * self.m[3]))

    def inverse(self) -> "Mat3":
        """Inversa de uma matriz afim.

            | A  t |^-1   | A^-1   -A^-1·t |
            | 0  1 |    = |  0        1    |

        com A^-1 = 1/det · |  d  -b |
                           | -c   a |
        """
        a, b, tx = self.m[0], self.m[1], self.m[2]
        c, d, ty = self.m[3], self.m[4], self.m[5]
        det = a * d - b * c
        if abs(det) < EPS:
            raise ZeroDivisionError("matriz singular (escala nula)")
        ia, ib = d / det, -b / det
        ic, id_ = -c / det, a / det
        return Mat3([ia, ib, -(ia * tx + ib * ty),
                     ic, id_, -(ic * tx + id_ * ty),
                     0, 0, 1])

    def to_gl(self) -> list[float]:
        """Matriz 4x4 por colunas (column-major), o formato que glMultMatrixf espera."""
        a, b, tx = self.m[0], self.m[1], self.m[2]
        c, d, ty = self.m[3], self.m[4], self.m[5]
        return [a, c, 0.0, 0.0,
                b, d, 0.0, 0.0,
                0.0, 0.0, 1.0, 0.0,
                tx, ty, 0.0, 1.0]

    def rows(self) -> list[list[float]]:
        return [self.m[0:3], self.m[3:6], self.m[6:9]]

    def key(self, digits: int = 6) -> tuple:
        """Chave estável (para caches)."""
        return tuple(round(v, digits) for v in self.m[:6])

    def decompose(self) -> tuple[float, float, float, float, float, float]:
        """Decompõe M = T·R(θ)·Sh(k)·S(sx, sy) e devolve (tx, ty, θ°, sx, sy, k).

        A parte linear é R·Sh·S = | sx·cosθ   sy·(k·cosθ − sinθ) |
                                  | sx·sinθ   sy·(k·sinθ + cosθ) |
        A 1.ª coluna dá sx e θ; projetando a 2.ª coluna nos eixos rodados
        obtém-se sy e k. Funciona para qualquer matriz afim invertível,
        incluindo espelhamentos (sy fica negativo).
        """
        a, b, tx = self.m[0], self.m[1], self.m[2]
        c, d, ty = self.m[3], self.m[4], self.m[5]
        sx = math.hypot(a, c)
        if sx < EPS:
            return tx, ty, 0.0, 0.0, d, 0.0
        theta = math.atan2(c, a)
        cs, sn = math.cos(theta), math.sin(theta)
        sy = -b * sn + d * cs
        k = (b * cs + d * sn) / sy if abs(sy) > EPS else 0.0
        return tx, ty, math.degrees(theta), sx, sy, k

    def almost_equal(self, other: "Mat3", tol: float = 1e-6) -> bool:
        return all(abs(p - q) <= tol for p, q in zip(self.m, other.m))

    def __eq__(self, other) -> bool:
        return isinstance(other, Mat3) and self.m == other.m

    def __repr__(self) -> str:
        r = self.rows()
        return "Mat3(" + "; ".join(" ".join(f"{v:.4g}" for v in row) for row in r) + ")"


def _clean(v: float) -> float:
    """Remove ruído numérico (ex.: 1e-17 → 0)."""
    if abs(v) < 1e-9:
        return 0.0
    return round(v, 9)


def _normalize_angle(deg: float, near: float = 0.0) -> float:
    """Ângulo equivalente a `deg` mais próximo de `near` (evita saltos de 360°)."""
    while deg - near > 180.0:
        deg -= 360.0
    while deg - near <= -180.0:
        deg += 360.0
    return deg


@dataclass
class Transform:
    """Parâmetros de transformação de um objeto (relativos ao objeto pai)."""

    tx: float = 0.0
    ty: float = 0.0
    rotation: float = 0.0   # graus, sentido anti-horário
    sx: float = 1.0
    sy: float = 1.0
    shear: float = 0.0      # fator k do cisalhamento horizontal

    def matrix(self) -> Mat3:
        """M = T · R · Sh · S."""
        return (Mat3.translation(self.tx, self.ty)
                @ Mat3.rotation(self.rotation)
                @ Mat3.shearing(self.shear)
                @ Mat3.scaling(self.sx, self.sy))

    @staticmethod
    def from_matrix(m: Mat3, reference: "Transform | None" = None) -> "Transform":
        """Constrói os parâmetros a partir de uma matriz (decomposição).

        A decomposição tem uma ambiguidade de sinal: (θ, sx, sy) e
        (θ+180°, −sx, −sy) dão a mesma matriz. Com `reference` mantemos o
        sinal de sx da transformação anterior, para que um objeto espelhado
        não "salte" para 180° quando é movido ou rodado.
        """
        tx, ty, rot, sx, sy, k = m.decompose()
        if reference is not None:
            if reference.sx < 0 < sx:
                rot, sx, sy = rot + 180.0, -sx, -sy
            rot = _normalize_angle(rot, reference.rotation)
        else:
            rot = _normalize_angle(rot)
        return Transform(_clean(tx), _clean(ty), _clean(rot), _clean(sx), _clean(sy), _clean(k))

    def copy(self) -> "Transform":
        return Transform(self.tx, self.ty, self.rotation, self.sx, self.sy, self.shear)

    def to_dict(self) -> dict:
        return {"tx": self.tx, "ty": self.ty, "rot": self.rotation,
                "sx": self.sx, "sy": self.sy, "k": self.shear}

    @staticmethod
    def from_dict(d: dict) -> "Transform":
        return Transform(float(d.get("tx", 0)), float(d.get("ty", 0)), float(d.get("rot", 0)),
                         float(d.get("sx", 1)), float(d.get("sy", 1)), float(d.get("k", 0)))
