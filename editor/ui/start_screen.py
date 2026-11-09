"""Cena inicial: fundo animado em OpenGL + menu (Novo, Abrir, Exemplos, Ajuda, Sair).

O fundo reutiliza o mesmo renderizador do editor: é um documento com formas
geradas aleatoriamente, cada uma com animação (rotação, pulsação, oscilação).
A janela do mundo é escolhida para "cobrir" o visor mantendo a proporção.
"""

from __future__ import annotations

import random

from OpenGL import GL as gl
from PySide6.QtCore import QElapsedTimer, QTimer, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from .. import __version__
from ..controller import PALETTE, hex_to_rgba
from ..core.document import Document
from ..core.examples import EXAMPLES
from ..core.shapes import EllipseShape, RectShape, RegularPolygonShape, TriangleShape
from ..render.camera import Camera
from ..render.renderer import Renderer
from .icons import icon


def background_document() -> Document:
    doc = Document(1280, 720)
    layer = doc.active_layer()
    rnd = random.Random(2026)
    makers = [lambda r: RegularPolygonShape(rnd.choice([3, 5, 6, 8]), r),
              lambda r: RegularPolygonShape(rnd.choice([4, 5, 6]), r, 0.5),
              lambda r: EllipseShape(r, r * rnd.uniform(0.6, 1.0)),
              lambda r: RectShape(r * 1.6, r * rnd.uniform(0.6, 1.4)),
              lambda r: TriangleShape(r * 1.7, r * 1.5)]
    for _ in range(46):
        s = rnd.choice(makers)(rnd.uniform(18, 95))
        s.transform.tx, s.transform.ty = rnd.uniform(-60, 1340), rnd.uniform(-60, 780)
        s.transform.rotation = rnd.uniform(0, 360)
        s.style.fill = hex_to_rgba(rnd.choice(PALETTE), rnd.uniform(0.10, 0.30))
        s.style.stroke = (1.0, 1.0, 1.0, rnd.uniform(0.12, 0.3))
        s.style.stroke_width = rnd.uniform(1.0, 2.5)
        s.anim.rotate = rnd.choice([-1, 1]) * rnd.uniform(6, 30)
        if rnd.random() < 0.5:
            s.anim.pulse, s.anim.pulse_freq = rnd.uniform(0.05, 0.18), rnd.uniform(0.1, 0.5)
        s.anim.osc_x, s.anim.osc_y = rnd.uniform(0, 40), rnd.uniform(0, 40)
        s.anim.osc_freq = rnd.uniform(0.03, 0.12)
        if rnd.random() < 0.3:
            s.anim.hue = rnd.uniform(5, 20)
        layer.add(s)
    return doc


class AnimatedBackground(QOpenGLWidget):
    glInfo = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.renderer = Renderer()
        self.camera = Camera()
        self.doc = background_document()
        self.clock = QElapsedTimer()
        self.clock.start()
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.update)
        self.ok = False

    def initializeGL(self) -> None:
        self.renderer.textures.forget()
        try:
            self.renderer.init_gl()
            self.ok = True
            self.glInfo.emit(self.renderer.info)
        except Exception:  # noqa: BLE001
            self.ok = False

    def paintGL(self) -> None:
        if not self.ok:
            return
        dpr = self.devicePixelRatioF()
        r = self.renderer
        r.begin()
        gl.glViewport(0, 0, int(self.width() * dpr), int(self.height() * dpr))
        r.clear((0.075, 0.08, 0.105, 1.0))
        cam = self.camera
        cam.resize(self.width(), self.height())
        cam.zoom = max(self.width() / 1280.0, self.height() / 720.0)   # "cobrir" sem distorcer
        cam.cx, cam.cy = 640.0, 360.0
        r.set_projection(cam.window())
        r.draw_document(self.doc, t=self.clock.elapsed() / 1000.0, px=cam.px())

    def showEvent(self, e) -> None:
        self.timer.start()
        super().showEvent(e)

    def hideEvent(self, e) -> None:
        self.timer.stop()
        super().hideEvent(e)


class StartScreen(QWidget):
    newRequested = Signal()
    openRequested = Signal()
    exampleRequested = Signal(int)
    helpRequested = Signal()
    quitRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bg = AnimatedBackground(self)
        self.card = QFrame(self)
        self.card.setObjectName("card")
        self.card.setStyleSheet("""
            QFrame#card { background: rgba(22, 24, 31, 228); border: 1px solid #3A3F4A; border-radius: 18px; }
            QLabel { background: transparent; }
            QPushButton { padding: 9px 14px; text-align: left; }
        """)
        v = QVBoxLayout(self.card)
        v.setContentsMargins(30, 26, 30, 22)
        v.setSpacing(8)
        logo = QLabel()
        logo.setPixmap(icon("logo").pixmap(56, 56))
        title = QLabel("Editor Gráfico e\nModelador Geométrico")
        title.setStyleSheet("font-size: 25pt; font-weight: 700; color: #F2F4F8;")
        sub = QLabel("Computação Gráfica · Trabalho Prático Final · Grupo 5")
        sub.setStyleSheet("color: #8FB3FF; font-weight: 600;")
        desc = QLabel("Python + OpenGL. Formas, transformações com matrizes 3×3, camadas, "
                      "agrupamento, texturas, imagens digitais, animação e exportação PNG/GIF.")
        desc.setWordWrap(True)
        desc.setObjectName("muted")
        v.addWidget(logo)
        v.addWidget(title)
        v.addWidget(sub)
        v.addWidget(desc)
        v.addSpacing(8)

        b_new = QPushButton(icon("new"), "  Novo projeto")
        b_new.setObjectName("primary")
        b_open = QPushButton(icon("open"), "  Abrir projeto…")
        b_new.clicked.connect(self.newRequested)
        b_open.clicked.connect(self.openRequested)
        v.addWidget(b_new)
        v.addWidget(b_open)
        v.addSpacing(6)
        ex_label = QLabel("Exemplos")
        ex_label.setStyleSheet("color: #9AA1AF; font-weight: 600;")
        v.addWidget(ex_label)
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, (name, description, _b) in enumerate(EXAMPLES):
            b = QPushButton(name)
            b.setToolTip(description)
            b.clicked.connect(lambda _c=False, k=i: self.exampleRequested.emit(k))
            grid.addWidget(b, i // 2, i % 2)
        v.addLayout(grid)
        v.addSpacing(6)
        row = QGridLayout()
        b_help = QPushButton(icon("help"), "  Ajuda e atalhos (F1)")
        b_quit = QPushButton("  Sair")
        b_help.clicked.connect(self.helpRequested)
        b_quit.clicked.connect(self.quitRequested)
        row.addWidget(b_help, 0, 0)
        row.addWidget(b_quit, 0, 1)
        v.addLayout(row)
        self.footer = QLabel(f"Versão {__version__}")
        self.footer.setObjectName("muted")
        self.footer.setStyleSheet("font-size: 8.5pt;")
        self.footer.setWordWrap(True)
        v.addWidget(self.footer)
        self.bg.glInfo.connect(self._gl_info)

    def _gl_info(self, info: dict) -> None:
        self.footer.setText(f"Versão {__version__} · OpenGL {info.get('versao', '?').split(' ')[0]} · "
                            f"{info.get('renderizador', '')}")

    def resizeEvent(self, e) -> None:
        self.bg.setGeometry(self.rect())
        w = min(520, max(380, int(self.width() * 0.4)))
        self.card.setFixedWidth(w)
        self.card.adjustSize()
        h = self.card.sizeHint().height()
        x = max(24, int(self.width() * 0.07))
        y = max(16, (self.height() - h) // 2)
        self.card.setGeometry(x, y, w, h)
        self.card.raise_()
        super().resizeEvent(e)
