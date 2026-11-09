"""Arranque da aplicação.

Opções da linha de comandos:
    ficheiro.geo        abre o projeto
    --software-gl       usa OpenGL por software (para computadores com drivers fracos)
    --selftest [pasta]  autoteste sem janelas (usado no GitHub Actions)
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback

from . import APP_NAME, ORG_NAME, __version__


def _configure_platform() -> None:
    # O PyOpenGL usa GLX no Linux; numa sessão Wayland pedimos ao Qt a camada X11 (XWayland).
    if sys.platform.startswith("linux") and os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"


def _windows_software_gl() -> bool:
    """OpenGL por software no Windows.

    O PyOpenGL usa sempre a biblioteca "opengl32.dll". Se o Qt usasse o seu
    OpenGL por software (opengl32sw.dll) e o PyOpenGL o do sistema, cada um
    falaria com um OpenGL diferente. Por isso carregamos uma cópia do Mesa
    (opengl32sw.dll, que vem com o PySide6) com o nome opengl32.dll antes de
    tudo: o Windows reutiliza o módulo já carregado e o Qt e o PyOpenGL passam
    a usar o mesmo OpenGL.
    """
    import ctypes
    import shutil

    import PySide6
    src = os.path.join(os.path.dirname(PySide6.__file__), "opengl32sw.dll")
    if not os.path.exists(src):
        return False
    folder = os.path.join(tempfile.gettempdir(), "editor_geometrico_mesa")
    os.makedirs(folder, exist_ok=True)
    dst = os.path.join(folder, "opengl32.dll")
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
        shutil.copyfile(src, dst)
    ctypes.WinDLL(dst)
    return True


def _surface_format(software: bool) -> None:
    from PySide6.QtCore import QCoreApplication, Qt
    from PySide6.QtGui import QSurfaceFormat
    if software:
        if sys.platform == "win32":
            if not _windows_software_gl():
                QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)
        else:
            os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"   # Mesa (Linux)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    fmt = QSurfaceFormat()
    fmt.setSamples(4)            # antialiasing por multiamostragem
    fmt.setStencilBufferSize(8)
    fmt.setSwapInterval(1)
    QSurfaceFormat.setDefaultFormat(fmt)


def _install_excepthook() -> None:
    """Mostra os erros numa janela em vez de fechar o programa (importante no .exe)."""
    from PySide6.QtWidgets import QApplication, QMessageBox

    log_path = os.path.join(tempfile.gettempdir(), "editor_geometrico_erros.log")
    state = {"last": 0.0, "msg": ""}

    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(time.strftime("\n[%Y-%m-%d %H:%M:%S]\n") + text)
        except OSError:
            pass
        if sys.stderr is not None:
            try:
                sys.stderr.write(text)
            except Exception:  # noqa: BLE001
                pass
        now = time.monotonic()
        msg = f"{exc_type.__name__}: {exc}"
        if QApplication.instance() is None or (now - state["last"] < 3.0) or msg == state["msg"] and now - state["last"] < 30:
            return
        state["last"], state["msg"] = now, msg
        box = QMessageBox(QMessageBox.Icon.Warning, "Erro inesperado",
                          "Ocorreu um erro, mas o editor continua aberto.\n"
                          f"Se puder, guarde o trabalho.\n\n{msg}\n\nRegisto: {log_path}")
        box.setDetailedText(text)
        box.exec()

    sys.excepthook = hook


def _opengl_is_usable() -> bool:
    """Cria um contexto e faz uma chamada real com o PyOpenGL (OpenGL ≥ 2.0?)."""
    from PySide6.QtGui import QOffscreenSurface, QOpenGLContext, QSurfaceFormat
    ctx = QOpenGLContext()
    ctx.setFormat(QSurfaceFormat.defaultFormat())
    if not ctx.create():
        return False
    surface = QOffscreenSurface()
    surface.setFormat(ctx.format())
    surface.create()
    if not ctx.makeCurrent(surface):
        return False
    try:
        from .render import renderer  # noqa: F401  (configura o PyOpenGL antes de importar o GL)
        from OpenGL import GL as gl
        version = gl.glGetString(gl.GL_VERSION) or b""
        major = int(version.split(b".")[0].split()[-1]) if version else 0
        return major >= 2
    except Exception:  # noqa: BLE001
        return False
    finally:
        ctx.doneCurrent()


def _restart_with_software_gl(argv) -> None:
    from PySide6.QtCore import QProcess
    if getattr(sys, "frozen", False):
        QProcess.startDetached(sys.executable, list(argv[1:]) + ["--software-gl"])
    else:
        script = os.path.abspath(argv[0])
        QProcess.startDetached(sys.executable, [script] + list(argv[1:]) + ["--software-gl"])


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    software = "--software-gl" in argv or os.environ.get("EDITOR_SOFTWARE_GL") == "1"
    _configure_platform()

    if "--selftest" in argv:
        i = argv.index("--selftest")
        out = argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("--") else "autoteste"
        _surface_format(software)
        from .selftest import run_selftest
        return run_selftest(out)

    _surface_format(software)
    from PySide6.QtWidgets import QApplication, QMessageBox

    from .ui.i18n import install_translations
    from .ui.icons import icon
    from .ui.main_window import MainWindow
    from .ui.theme import apply_theme

    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(ORG_NAME)
    install_translations(app)
    apply_theme(app)
    app.setWindowIcon(icon("logo"))
    _install_excepthook()

    if not software and not _opengl_is_usable():
        r = QMessageBox.question(None, APP_NAME,
                                 "O OpenGL deste computador não parece suficiente (é preciso OpenGL 2.0 ou superior).\n\n"
                                 "Reiniciar o editor com OpenGL por software? (mais lento, mas funciona em qualquer PC)")
        if r == QMessageBox.StandardButton.Yes:
            _restart_with_software_gl(argv)
            return 0

    win = MainWindow()
    win.show()
    files = [a for a in argv[1:] if not a.startswith("--") and os.path.isfile(a)]
    if files:
        win.open_project(files[0])
    return app.exec()
