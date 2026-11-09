"""Localização de recursos (funciona a partir do código-fonte e do .exe do PyInstaller)."""

import os
import sys


def base_dir() -> str:
    """Pasta raiz do projeto (ou a pasta temporária do PyInstaller no .exe)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def asset(*parts: str) -> str:
    return os.path.join(base_dir(), "assets", *parts)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))
