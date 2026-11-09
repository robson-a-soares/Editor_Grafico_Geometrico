"""Autoteste sem janelas: valida a matemática, os ficheiros e a renderização OpenGL.

Uso:
    python main.py --selftest [pasta]
    EditorGeometrico.exe --selftest [pasta]

Renderiza os exemplos para PNG, grava um GIF animado e escreve
autoteste.txt com o resultado. Devolve o código de saída 0 se tudo correu bem.
É usado pelo GitHub Actions para confirmar que o .exe funciona no Windows.
"""

from __future__ import annotations

import os
import sys
import traceback


def run_selftest(out_dir: str) -> int:
    os.makedirs(out_dir, exist_ok=True)
    lines: list[str] = []

    def log(msg: str) -> None:
        lines.append(msg)
        if sys.stdout is not None:
            try:
                print(msg, flush=True)
            except Exception:
                pass

    ok = True
    try:
        import numpy
        import OpenGL
        import PIL
        import PySide6
        from PySide6.QtGui import QGuiApplication, QOffscreenSurface, QOpenGLContext, QSurfaceFormat

        from . import __version__
        _app = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])  # mantém a aplicação viva
        log(f"Editor Gráfico Geométrico {__version__} — autoteste")
        log(f"Python {sys.version.split()[0]} | PySide6 {PySide6.__version__} | PyOpenGL {OpenGL.__version__}"
            f" | numpy {numpy.__version__} | Pillow {PIL.__version__} | {'executável' if getattr(sys, 'frozen', False) else 'código-fonte'}")

        # 1. Matemática
        from .core.matrix import Mat3, Transform
        t = Transform(10, 20, 30, 1.5, -0.5, 0.3)
        m = t.matrix()
        assert (m @ m.inverse()).almost_equal(Mat3.identity(), 1e-9), "inversa"
        assert Transform.from_matrix(m, reference=t).matrix().almost_equal(m, 1e-7), "decomposição"
        log("[ok] matrizes: composição, inversa e decomposição")

        # 2. Ficheiros
        from .core.examples import EXAMPLES
        from .core.fileio import data_to_document, document_to_data
        for name, _desc, build in EXAMPLES:
            doc = build()
            assert data_to_document(document_to_data(doc)).to_dict() == doc.to_dict(), name
        log(f"[ok] guardar/carregar {len(EXAMPLES)} projetos de exemplo")

        # 3. OpenGL fora do ecrã
        ctx = QOpenGLContext()
        ctx.setFormat(QSurfaceFormat.defaultFormat())
        if not ctx.create():
            raise RuntimeError("não foi possível criar um contexto OpenGL")
        surface = QOffscreenSurface()
        surface.setFormat(ctx.format())
        surface.create()
        if not ctx.makeCurrent(surface):
            raise RuntimeError("não foi possível ativar o contexto OpenGL")
        from .render.exporter import export_gif, qimage_to_pil, render_image, save_image
        from .render.renderer import Renderer
        renderer = Renderer()
        renderer.init_gl()
        log(f"[ok] OpenGL {renderer.info.get('versao')} — {renderer.info.get('renderizador')}")
        for i, (name, _desc, build) in enumerate(EXAMPLES):
            doc = build()
            region = (0.0, doc.width, 0.0, doc.height)
            img = render_image(renderer, doc, region, 960, 540, t=1.5)
            path = os.path.join(out_dir, f"exemplo_{i + 1}.png")
            save_image(img, path)
            colors = len(set(qimage_to_pil(img).convert("RGB").resize((96, 54)).getdata()))
            if colors < 8:
                raise RuntimeError(f"a imagem do exemplo '{name}' saiu vazia")
            log(f"[ok] exemplo '{name}' → {os.path.basename(path)} ({colors} cores)")
        n = export_gif(renderer, EXAMPLES[1][2](), os.path.join(out_dir, "animacao.gif"), 360, 2.0, 12)
        if n < 2:
            raise RuntimeError("GIF sem quadros")
        log(f"[ok] GIF animado com {n} quadros → animacao.gif")
        renderer.textures.clear()
        ctx.doneCurrent()
    except Exception:
        ok = False
        log(traceback.format_exc())
    log("RESULTADO: OK" if ok else "RESULTADO: FALHOU")
    try:
        with open(os.path.join(out_dir, "autoteste.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass
    return 0 if ok else 1
