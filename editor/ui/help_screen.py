"""Cena de ajuda: atalhos, ferramentas e os conceitos de Computação Gráfica usados."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from .. import __version__
from .icons import icon

HELP_HTML = """
<style>
 h1 { color:#F2F4F8; font-size:20pt; margin-bottom:2px; }
 h2 { color:#8FB3FF; font-size:13pt; margin-top:18px; margin-bottom:6px; }
 td { padding:3px 14px 3px 0; vertical-align:top; }
 .k { font-family: Consolas, 'DejaVu Sans Mono', monospace; color:#FFD166; white-space:nowrap; }
 p, li { line-height:140%; }
 code { color:#9BE8B0; }
</style>
<h1>Ajuda e atalhos</h1>
<p>Editor Gráfico e Modelador Geométrico · versão {version}. Desenhe na prancheta branca com as
ferramentas da barra da esquerda; o painel <b>Propriedades</b> (direita) mostra e altera o objeto
selecionado e o painel <b>Camadas</b> organiza o desenho.</p>

<h2>Ferramentas</h2>
<table>
<tr><td class="k">V</td><td>Selecionar e transformar: arrastar move; as alças quadradas escalam; a alça redonda roda.</td></tr>
<tr><td class="k">H</td><td>Mão: deslocar a vista (também botão do meio, ou Espaço + arrastar).</td></tr>
<tr><td class="k">R · E · T</td><td>Retângulo · Elipse · Triângulo: arraste para desenhar (Shift = proporcional, Alt = a partir do centro; um clique cria o tamanho padrão).</td></tr>
<tr><td class="k">L</td><td>Linha (Shift = ângulos de 15°).</td></tr>
<tr><td class="k">P</td><td>Polígono livre: clique em cada vértice; duplo clique, Enter ou clique no 1.º ponto fecha. Backspace apaga o último ponto.</td></tr>
<tr><td class="k">F</td><td>Mão livre: o traço é simplificado com o algoritmo de Ramer–Douglas–Peucker.</td></tr>
<tr><td class="k">N · S</td><td>Polígono regular · Estrela: arraste a partir do centro (o nº de lados muda-se nas Propriedades).</td></tr>
<tr><td class="k">Ctrl+I</td><td>Importar imagem (PNG/JPG) — também pode arrastar o ficheiro para a janela.</td></tr>
</table>

<h2>Mouse</h2>
<table>
<tr><td class="k">Clique</td><td>Selecionar · <span class="k">Shift+clique</span> acrescenta/retira da seleção.</td></tr>
<tr><td class="k">Arrastar no vazio</td><td>Seleção por área.</td></tr>
<tr><td class="k">Alças</td><td>Shift = escala proporcional (ou rotação em passos de 15°) · Alt = escala a partir do centro.</td></tr>
<tr><td class="k">Duplo clique</td><td>Num grupo: seleciona o objeto de dentro (Esc volta ao grupo).</td></tr>
<tr><td class="k">Roda</td><td>Zoom centrado no cursor.</td></tr>
<tr><td class="k">Botão direito</td><td>Menu de contexto.</td></tr>
<tr><td class="k">Minimapa</td><td>Clique/arraste no minimapa (canto inferior direito) para navegar.</td></tr>
</table>

<h2>Teclado</h2>
<table>
<tr><td class="k">Ctrl+N / O / S</td><td>Novo · Abrir · Guardar (<span class="k">Ctrl+Shift+S</span> guardar como)</td></tr>
<tr><td class="k">Ctrl+Z / Ctrl+Y</td><td>Desfazer · Refazer</td></tr>
<tr><td class="k">Ctrl+C / X / V / D</td><td>Copiar · Cortar · Colar · Duplicar</td></tr>
<tr><td class="k">Delete</td><td>Apagar a seleção</td></tr>
<tr><td class="k">Ctrl+G / Ctrl+Shift+G</td><td>Agrupar · Desagrupar</td></tr>
<tr><td class="k">Ctrl+↑ / Ctrl+↓</td><td>Avançar · Recuar na ordem (com Shift: para a frente / para trás de tudo)</td></tr>
<tr><td class="k">Setas</td><td>Mover 1 px (Shift: 10 px)</td></tr>
<tr><td class="k">, &nbsp; .</td><td>Rodar −15° · +15°</td></tr>
<tr><td class="k">+ &nbsp; −</td><td>Aumentar · Diminuir 10 %</td></tr>
<tr><td class="k">Shift+H / Shift+V</td><td>Espelhar horizontal · vertical</td></tr>
<tr><td class="k">F5 / Shift+F5</td><td>Reproduzir/parar a animação · voltar ao instante 0</td></tr>
<tr><td class="k">Ctrl+E / Ctrl+Shift+E</td><td>Exportar imagem · Exportar animação GIF</td></tr>
<tr><td class="k">Ctrl+0 / Ctrl+1</td><td>Ajustar à janela · Zoom 100 %</td></tr>
<tr><td class="k">G / Shift+G / M</td><td>Grelha · Ajustar à grelha · Minimapa</td></tr>
<tr><td class="k">F1</td><td>Esta ajuda</td></tr>
</table>

<h2>Camadas e agrupamento</h2>
<p>Cada camada tem visibilidade (olho), bloqueio (cadeado) e opacidade. Os objetos novos são criados na
<b>camada ativa</b> (marcada com ●). Clique numa camada para a ativar; duplo clique para mudar o nome.
O menu de contexto de um objeto permite movê-lo para outra camada. Um <b>grupo</b> tem a sua própria matriz,
que é aplicada a todos os objetos que contém.</p>

<h2>Conceitos de Computação Gráfica no editor</h2>
<ul>
<li><b>Matrizes homogéneas 3×3</b>: cada objeto tem M = T·R·Sh·S. O painel Propriedades mostra a matriz
em tempo real (local ou do mundo). O OpenGL recebe a matriz pronta com <code>glMultMatrixf</code>.</li>
<li><b>Modelação hierárquica</b>: num grupo, M_mundo(filho) = M_grupo · M_filho, com
<code>glPushMatrix/glPopMatrix</code>. Veja o exemplo "Sistema solar".</li>
<li><b>Seleção com a matriz inversa</b>: o clique é levado às coordenadas do objeto com M⁻¹.</li>
<li><b>Janela → visor sem distorção</b>: a escala é sempre igual nos dois eixos. Em <i>Ver ▸ Manter proporção</i>
pode desligar esta garantia para ver a distorção (demonstração).</li>
<li><b>Viewports</b>: o minimapa é um segundo visor (<code>glViewport</code>) com a sua própria janela do mundo.</li>
<li><b>Texturas</b>: geradas por código (repetíveis) e mapeadas com coordenadas UV; imagens importadas são
texturas em retângulos.</li>
<li><b>Ear clipping</b> para preencher polígonos côncavos e <b>Ramer–Douglas–Peucker</b> para simplificar traços.</li>
<li><b>Animação</b>: as mesmas transformações em função do tempo t (rotação, pulsação, oscilação, ciclo de cor).</li>
</ul>
"""


class HelpScreen(QWidget):
    backRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 16, 24, 16)
        top = QHBoxLayout()
        back = QPushButton(icon("home"), "  Voltar")
        back.clicked.connect(self.backRequested)
        top.addWidget(back)
        top.addStretch(1)
        hint = QLabel("Também disponível no menu Ajuda (F1)")
        hint.setObjectName("muted")
        top.addWidget(hint)
        v.addLayout(top)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(HELP_HTML.replace("{version}", __version__))
        v.addWidget(self.browser, 1)
