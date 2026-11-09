"""Editor Gráfico e Modelador Geométrico — ponto de entrada.

    python main.py                  abre o editor
    python main.py desenho.geo      abre um projeto
    python main.py --software-gl    OpenGL por software (PCs sem driver gráfico adequado)
    python main.py --selftest       autoteste sem janelas
"""

import sys

from editor.app import main

if __name__ == "__main__":
    sys.exit(main())
