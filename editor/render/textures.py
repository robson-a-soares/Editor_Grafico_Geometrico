"""Texturas: geração procedural (numpy), filtros de imagem (Pillow) e envio para o OpenGL.

As texturas incluídas são geradas por código, sem ficheiros de imagem:
todas são "repetíveis" (o lado direito encaixa no esquerdo e o de cima no
de baixo) para poderem ser usadas com GL_REPEAT.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

SIZE = 256

BUILTIN_TEXTURES = [
    ("xadrez", "Xadrez"),
    ("tijolo", "Tijolo"),
    ("madeira", "Madeira"),
    ("marmore", "Mármore"),
    ("listras", "Listras"),
    ("bolinhas", "Bolinhas"),
    ("relva", "Relva"),
    ("pedra", "Pedra"),
]

FILTERS = [
    ("cinzento", "Tons de cinzento"),
    ("negativo", "Negativo"),
    ("sepia", "Sépia"),
    ("brilho+", "Mais brilho"),
    ("brilho-", "Menos brilho"),
    ("contraste+", "Mais contraste"),
    ("desfocar", "Desfocar"),
    ("nitidez", "Nitidez"),
    ("espelhar_h", "Espelhar ↔"),
    ("espelhar_v", "Espelhar ↕"),
]
FILTER_LABELS = dict(FILTERS)


# ----------------------------------------------------------------------
# Ruído repetível (value noise com interpolação suave)
# ----------------------------------------------------------------------
def _noise(size: int, cells: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    grid = rng.random((cells, cells))
    pos = np.arange(size) * cells / size
    i0 = np.floor(pos).astype(int)
    f = pos - i0
    f = f * f * (3 - 2 * f)                     # smoothstep
    i1 = (i0 + 1) % cells                       # "dar a volta" torna o ruído repetível
    rows = grid[:, i0] * (1 - f) + grid[:, i1] * f
    return rows[i0, :] * (1 - f)[:, None] + rows[i1, :] * f[:, None]


def _fbm(size: int, seed: int, octaves: int = 4, base: int = 4) -> np.ndarray:
    total = np.zeros((size, size))
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        total += amp * _noise(size, base * 2 ** o, seed + o)
        norm += amp
        amp *= 0.5
    return total / norm


def _mix(c0, c1, t: np.ndarray) -> np.ndarray:
    c0 = np.asarray(c0, float)
    c1 = np.asarray(c1, float)
    return c0 + (c1 - c0) * t[..., None]


def _to_image(rgb: np.ndarray) -> Image.Image:
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    alpha = np.full(rgb.shape[:2] + (1,), 255, np.uint8)
    return Image.fromarray(np.concatenate([rgb, alpha], axis=2), "RGBA")


def generate_builtin(name: str) -> Image.Image:
    n = SIZE
    y, x = np.mgrid[0:n, 0:n]
    if name == "xadrez":
        t = (((x // 32) + (y // 32)) % 2).astype(float)
        return _to_image(_mix((43, 45, 66), (237, 242, 244), t))
    if name == "tijolo":
        row = y // 32
        off = (row % 2) * 32
        bx = (x + off) % 64
        by = y % 32
        mortar = (bx < 4) | (by < 4)
        brick_id = row * 7 + (x + off) // 64
        tint = np.random.default_rng(3).random(64)[brick_id % 64]
        noise = _fbm(n, 11, 3, 8)
        base = _mix((150, 58, 40), (196, 92, 62), tint * 0.7 + noise * 0.3)
        rgb = np.where(mortar[..., None], _mix((185, 180, 170), (215, 210, 200), noise), base)
        return _to_image(rgb)
    if name == "madeira":
        noise = _fbm(n, 21, 4, 4)
        rings = np.sin(2 * np.pi * (y / n * 6 + noise * 1.6))
        grain = _noise(n, 64, 29)
        t = (rings + 1) / 2 * 0.8 + grain * 0.2
        return _to_image(_mix((110, 66, 36), (198, 142, 86), t))
    if name == "marmore":
        noise = _fbm(n, 31, 5, 4)
        v = np.abs(np.sin(2 * np.pi * (x / n * 2 + y / n * 1 + noise * 2.2)))
        t = v ** 0.35
        return _to_image(_mix((105, 108, 122), (240, 240, 245), t))
    if name == "listras":
        t = (((x + y) // 16) % 2).astype(float)
        return _to_image(_mix((251, 133, 0), (255, 200, 60), t))
    if name == "bolinhas":
        cx = (x % 32) - 16
        cy = (y % 32) - 16
        d = np.sqrt(cx * cx + cy * cy)
        t = np.clip(9.5 - d, 0, 1)                 # borda suavizada (anti-aliasing)
        return _to_image(_mix((58, 134, 255), (255, 255, 255), t))
    if name == "relva":
        noise = _fbm(n, 41, 4, 4)
        blades = _noise(n, 128, 43)
        t = noise * 0.6 + blades * 0.4
        return _to_image(_mix((40, 110, 45), (120, 196, 90), t))
    if name == "pedra":
        rng = np.random.default_rng(51)
        seeds = rng.random((28, 2)) * n
        dx = np.abs(x[..., None] - seeds[:, 0])
        dy = np.abs(y[..., None] - seeds[:, 1])
        dx = np.minimum(dx, n - dx)                # distâncias "com volta": repetível
        dy = np.minimum(dy, n - dy)
        d = np.sqrt(dx * dx + dy * dy)
        part = np.partition(d, 1, axis=2)
        edge = np.clip((part[..., 1] - part[..., 0]) / 6.0, 0, 1)
        cell = np.argmin(d, axis=2)
        tone = rng.random(28)[cell]
        noise = _fbm(n, 57, 3, 8)
        stone = _mix((120, 118, 112), (190, 186, 176), tone * 0.7 + noise * 0.3)
        mortar = np.array((70.0, 66.0, 60.0))
        rgb = mortar * (1 - edge[..., None]) + stone * edge[..., None]
        return _to_image(rgb)
    if name == "transparencia":
        t = (((x // 16) + (y // 16)) % 2).astype(float)
        return _to_image(_mix((204, 204, 204), (255, 255, 255), t))
    raise KeyError(name)


# ----------------------------------------------------------------------
# Imagens digitais
# ----------------------------------------------------------------------
def load_rgba(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    return img.convert("RGBA")


def image_size(data: bytes) -> tuple[int, int]:
    return load_rgba(data).size


def apply_filters(img: Image.Image, filters) -> Image.Image:
    """Manipulação de imagens com Pillow (cada filtro opera sobre os píxeis RGB)."""
    for f in filters:
        r, g, b, a = img.split()
        rgb = Image.merge("RGB", (r, g, b))
        if f == "cinzento":
            rgb = ImageOps.grayscale(rgb).convert("RGB")
        elif f == "negativo":
            rgb = ImageOps.invert(rgb)
        elif f == "sepia":
            rgb = ImageOps.colorize(ImageOps.grayscale(rgb), black="#2b1d0e", white="#f6e7c8")
        elif f == "brilho+":
            rgb = ImageEnhance.Brightness(rgb).enhance(1.25)
        elif f == "brilho-":
            rgb = ImageEnhance.Brightness(rgb).enhance(0.8)
        elif f == "contraste+":
            rgb = ImageEnhance.Contrast(rgb).enhance(1.35)
        elif f == "desfocar":
            rgb = rgb.filter(ImageFilter.GaussianBlur(2.5))
        elif f == "nitidez":
            rgb = rgb.filter(ImageFilter.SHARPEN)
        elif f == "espelhar_h":
            rgb, a = ImageOps.mirror(rgb), ImageOps.mirror(a)
        elif f == "espelhar_v":
            rgb, a = ImageOps.flip(rgb), ImageOps.flip(a)
        img = Image.merge("RGBA", (*rgb.split(), a))
    return img


# ----------------------------------------------------------------------
# Cache de texturas OpenGL
# ----------------------------------------------------------------------
class TextureCache:
    """Cria texturas OpenGL a pedido e reutiliza-as (uma por contexto OpenGL)."""

    MAX_SIDE = 2048

    def __init__(self):
        self._tex: dict = {}

    def forget(self) -> None:
        """Esquece as texturas sem as apagar (o contexto que as continha já não existe)."""
        self._tex.clear()

    def clear(self) -> None:
        from OpenGL import GL as gl
        ids = [v for v in self._tex.values() if v]
        if ids:
            try:
                gl.glDeleteTextures(ids)
            except Exception:
                pass
        self._tex.clear()

    def _upload(self, img: Image.Image, repeat: bool) -> int:
        from OpenGL import GL as gl
        w, h = img.size
        k = min(1.0, self.MAX_SIDE / max(w, h))
        if k < 1.0:
            img = img.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
            w, h = img.size
        tex = int(gl.glGenTextures(1))
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex)
        wrap = gl.GL_REPEAT if repeat else gl.GL_CLAMP_TO_EDGE
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, wrap)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, wrap)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        # a 1.ª linha da imagem (topo) fica em t = 0; as coordenadas UV compensam (v invertido)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, w, h, 0, gl.GL_RGBA,
                        gl.GL_UNSIGNED_BYTE, img.tobytes())
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 4)   # valor por omissão (o Qt conta com ele)
        mip = False
        try:
            if bool(gl.glGenerateMipmap):
                gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
                mip = True
        except Exception:
            mip = False
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER,
                           gl.GL_LINEAR_MIPMAP_LINEAR if mip else gl.GL_LINEAR)
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)
        return tex

    def builtin(self, name: str) -> int | None:
        key = ("builtin", name)
        if key not in self._tex:
            try:
                self._tex[key] = self._upload(generate_builtin(name), repeat=True)
            except KeyError:
                self._tex[key] = 0
        return self._tex[key] or None

    def image(self, image_id: str, filters, images: dict, repeat: bool = False) -> int | None:
        key = ("image", image_id, tuple(filters), repeat)
        if key not in self._tex:
            data = images.get(image_id)
            if not data:
                self._tex[key] = 0
            else:
                try:
                    self._tex[key] = self._upload(apply_filters(load_rgba(data), filters), repeat)
                except Exception:
                    self._tex[key] = 0
        return self._tex[key] or None

    def fill_texture(self, ref: str, images: dict) -> int | None:
        if ref.startswith("builtin:"):
            return self.builtin(ref[8:])
        if ref.startswith("img:"):
            return self.image(ref[4:], (), images, repeat=True)
        return None
