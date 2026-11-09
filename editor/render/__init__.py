"""Renderização com OpenGL (PyOpenGL), pipeline clássico com matrizes próprias.

A verificação de erros do PyOpenGL (glGetError após cada chamada) fica ligada
durante o desenvolvimento e desligada no executável, para que um aviso menor
de um driver não interrompa o programa.
"""

import sys

import OpenGL

OpenGL.ERROR_CHECKING = not getattr(sys, "frozen", False)
