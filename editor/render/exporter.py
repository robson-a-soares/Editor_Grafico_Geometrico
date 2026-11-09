"""Exportação de imagens (PNG/JPG/BMP) e de animações (GIF).

O desenho é feito fora do ecrã, num framebuffer object (FBO) do tamanho
pedido. A janela do mundo é a prancheta (ou a área escolhida) e o visor é a
imagem final: é outra vez a transformação janela → visor, agora com uma
resolução independente do tamanho da janela do programa.

Todas as funções assumem que há um contexto OpenGL atual.
"""

from __future__ import annotations

from OpenGL import GL as gl
from PIL import Image
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat

MAX_SIDE = 8192


class OffscreenTarget:
    """FBO reutilizável (com antialiasing por multiamostragem quando disponível)."""

    def __init__(self, width: int, height: int, samples: int = 4):
        self.width, self.height = int(width), int(height)
        self.fbo = None
        for s in (samples, 0):
            fmt = QOpenGLFramebufferObjectFormat()
            fmt.setSamples(s)
            fmt.setAttachment(QOpenGLFramebufferObject.Attachment.NoAttachment)
            fbo = QOpenGLFramebufferObject(QSize(self.width, self.height), fmt)
            if fbo.isValid():
                self.fbo = fbo
                break
        if self.fbo is None:
            raise RuntimeError("Não foi possível criar o framebuffer para exportar.")

    def render(self, renderer, doc, region, t=None, transparent: bool = False) -> QImage:
        self.fbo.bind()
        gl.glViewport(0, 0, self.width, self.height)
        renderer.begin()
        renderer.set_projection(region)
        if transparent:
            renderer.clear((0.0, 0.0, 0.0, 0.0))
        else:
            r, g, b, a = doc.background
            # fundo semitransparente sobre branco
            renderer.clear((r * a + (1 - a), g * a + (1 - a), b * a + (1 - a), 1.0))
        px = (region[1] - region[0]) / self.width
        renderer.draw_document(doc, t=t, px=px)
        gl.glFlush()
        img = self.fbo.toImage()
        self.fbo.release()
        return img

    def release(self) -> None:
        self.fbo = None


def export_region(doc, mode: str, selection=None, margin: float = 10.0):
    """Janela do mundo a exportar: 'prancheta', 'conteudo' ou 'selecao'."""
    from ..core.operations import selection_bbox
    if mode == "selecao" and selection:
        b = selection_bbox(selection)
    elif mode == "conteudo":
        b = doc.content_bbox()
    else:
        b = None
    if b is None:
        return doc.artboard[0], doc.artboard[2], doc.artboard[1], doc.artboard[3]
    return b[0] - margin, b[2] + margin, b[1] - margin, b[3] + margin


def size_for(region, scale: float) -> tuple[int, int]:
    w = max(1, round((region[1] - region[0]) * scale))
    h = max(1, round((region[3] - region[2]) * scale))
    k = min(1.0, MAX_SIDE / max(w, h))
    return max(1, round(w * k)), max(1, round(h * k))


def render_image(renderer, doc, region, width: int, height: int, t=None,
                 transparent: bool = False) -> QImage:
    target = OffscreenTarget(width, height)
    try:
        return target.render(renderer, doc, region, t=t, transparent=transparent).copy()
    finally:
        target.release()


def qimage_to_pil(img: QImage) -> Image.Image:
    img = img.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = img.width(), img.height()
    data = bytes(img.constBits())
    return Image.frombuffer("RGBA", (w, h), data, "raw", "RGBA", img.bytesPerLine(), 1).copy()


def save_image(img: QImage, path: str) -> None:
    pil = qimage_to_pil(img)
    lower = path.lower()
    if lower.endswith((".jpg", ".jpeg", ".bmp")):
        bg = Image.new("RGB", pil.size, (255, 255, 255))
        bg.paste(pil, mask=pil.split()[3])
        bg.save(path, quality=95) if lower.endswith((".jpg", ".jpeg")) else bg.save(path)
    else:
        pil.save(path, "PNG")


def export_gif(renderer, doc, path: str, width: int, duration: float, fps: float,
               region=None, progress=None) -> int:
    """Renderiza a animação quadro a quadro e grava um GIF animado (em ciclo).

    `progress(i, n)` é chamado após cada quadro; se devolver False, cancela.
    Devolve o número de quadros gravados (0 se cancelado).
    """
    region = region or (doc.artboard[0], doc.artboard[2], doc.artboard[1], doc.artboard[3])
    rw, rh = region[1] - region[0], region[3] - region[2]
    width = int(max(16, min(width, 2048)))
    height = max(16, round(width * rh / rw))
    fps = max(1.0, min(float(fps), 50.0))
    n = max(1, round(duration * fps))
    target = OffscreenTarget(width, height)
    frames = []
    try:
        for i in range(n):
            qimg = target.render(renderer, doc, region, t=i / fps)
            rgb = qimage_to_pil(qimg).convert("RGB")
            frames.append(rgb.quantize(colors=255, method=Image.Quantize.MEDIANCUT,
                                       dither=Image.Dither.FLOYDSTEINBERG))
            if progress is not None and progress(i + 1, n) is False:
                return 0
    finally:
        target.release()
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=int(round(1000.0 / fps)), loop=0, optimize=False)
    return len(frames)
