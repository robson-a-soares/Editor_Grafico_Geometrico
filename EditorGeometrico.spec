# -*- mode: python ; coding: utf-8 -*-
# Receita do PyInstaller: gera dist/EditorGeometrico.exe, um único ficheiro que
# corre sem Python instalado.  Uso:  build_exe.bat   (ou: pyinstaller EditorGeometrico.spec)
import sys

hidden = ["OpenGL.arrays.numpymodule", "OpenGL.arrays.ctypesarrays", "OpenGL.arrays.ctypespointers",
          "OpenGL.arrays.strings", "OpenGL.arrays.numbers", "OpenGL.arrays.lists", "OpenGL.arrays.nones"]
if sys.platform == "win32":
    hidden.append("OpenGL.platform.win32")
elif sys.platform == "darwin":
    hidden.append("OpenGL.platform.darwin")
else:
    hidden += ["OpenGL.platform.glx", "OpenGL.platform.egl"]

import os

import PySide6

binaries = []
# OpenGL por software (Mesa) para PCs sem driver gráfico adequado: opção --software-gl
_mesa = os.path.join(os.path.dirname(PySide6.__file__), "opengl32sw.dll")
if sys.platform == "win32" and os.path.exists(_mesa):
    binaries.append((_mesa, "PySide6"))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=[("assets", "assets")],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EditorGeometrico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=["assets/icon.ico"],
)
