# Decisões técnicas

Registo das decisões tomadas pelo Grupo 5 (base para as secções 5, 6 e 7 do relatório).

## 1. Plataforma: desktop, 2D

O enunciado define *"Sistemas Gráficos Interativos com OpenGL em Python"*, por isso a
aplicação é desktop, em Python, com OpenGL. Entre 2D e 3D (ambos permitidos) escolhemos
**2D**: um modelador 3D exigiria seleção e manipuladores em 3D, incompatíveis com o prazo,
e o 2D permite cobrir todos os requisitos com qualidade.

## 2. Tecnologias

| Peça | Escolha | Porquê |
|---|---|---|
| Linguagem | Python 3.12 (suporta 3.10–3.14) | Versão do grupo; todas as bibliotecas têm pacotes prontos para Windows |
| Interface | PySide6-Essentials 6.11.3 (Qt 6) | Um editor precisa de menus, barras, painéis, seletor de cor e diálogos de ficheiro — o Qt dá tudo isto pronto. A versão *Essentials* é a mais leve |
| OpenGL | PyOpenGL 3.1.10 dentro de `QOpenGLWidget` | Toda a área de desenho é OpenGL |
| Vetores | numpy | Arrays de vértices para o OpenGL e geração de texturas |
| Imagens | Pillow 11.3.0 | Abrir PNG/JPG, filtros, gravar GIF |
| Executável | PyInstaller 6.22.3 | `.exe` de um só ficheiro, sem Python instalado |

**Alternativas consideradas e rejeitadas:** Pygame ou GLUT (só dão a janela — teríamos de
desenhar botões e painéis à mão; o GLUT tem ainda problemas de instalação no Windows);
GLFW + Dear ImGui (menos documentação, mais risco no prazo); versão web (sairia do enunciado).

## 3. Estilo de OpenGL

Usamos o **pipeline clássico** (`glOrtho`, `glPushMatrix`, `glMultMatrixf`, arrays de vértices),
mas **sem** `glTranslatef/glRotatef/glScalef`: as matrizes são calculadas por nós
(`editor/core/matrix.py`) e o OpenGL recebe a matriz final. Assim o conceito *Matrizes* — o
primeiro listado para o Grupo 5 — fica explícito no código. Os vértices vão em arrays
(`glVertexPointer` + `glDrawArrays`), uma chamada por forma, em vez de `glVertex` por ponto.

## 4. Modelo geométrico

- Cada forma é definida no seu sistema local, centrada na origem.
- Parâmetros: `tx, ty, θ, sx, sy, k` → **M = T(tx,ty) · R(θ) · Sh(k) · S(sx,sy)**.
- Grupos: **M_mundo(filho) = M_mundo(grupo) · M_local(filho)** (padrão *Composite*;
  no OpenGL, `glPushMatrix/glPopMatrix`).
- Ao agrupar/desagrupar, a matriz local nova é `(M_mundo_pai)⁻¹ · M_mundo` e é decomposta de
  volta em T·R·Sh·S. Com o cisalhamento incluído, a decomposição é exata para qualquer matriz
  afim, por isso desagrupar um grupo rodado e escalado nunca deforma os objetos.
- Seleção: o clique é levado às coordenadas locais com **M⁻¹** e testado contra a forma.
- Polígonos côncavos: triangulação por **ear clipping**. Traços à mão livre:
  simplificação **Ramer–Douglas–Peucker**.
- Contornos: fita de triângulos com junções em esquadria, gerada em coordenadas do mundo
  (espessura constante e igual em todos os drivers, ao contrário de `glLineWidth`).

## 5. Janela → visor

A câmara guarda centro e zoom; a janela do mundo é `tamanho do visor / zoom`, por isso
`sx = sy` sempre (**sem distorção**). Para o relatório e o vídeo existe o modo de demonstração
*Ver ▸ Manter proporção* (desligado = janela fixa → o desenho estica). O minimapa é um segundo
visor (`glViewport` + `glScissor`). A exportação é outra transformação janela → visor, para um
framebuffer (FBO) com a resolução pedida.

## 6. Ficheiros e histórico

- Projeto `.geo` = JSON legível com as imagens embutidas em base64 (um único ficheiro portátil).
  Escrita atómica (ficheiro temporário + `os.replace`).
- Desfazer/refazer por **instantâneos** do documento em JSON (100 passos). Simples e robusto:
  qualquer operação nova fica coberta sem código extra. Alterações rápidas (setas, campos
  numéricos) são agrupadas num só passo.

## 7. Ambiente reproduzível

- Ambiente virtual `.venv` por projeto + versões fixas em `requirements.txt` (com marcadores
  para o numpy conforme a versão do Python). Scripts `setup.bat` / `run.bat` / `build_exe.bat`.
- `setup.bat` termina com um **autoteste** (`main.py --selftest`) que renderiza os exemplos fora
  do ecrã: se passar, o OpenGL dessa máquina funciona com o editor.
- OpenGL por software (`--software-gl`): no Windows carrega-se o Mesa do PySide6
  (`opengl32sw.dll`) com o nome `opengl32.dll` antes do Qt e do PyOpenGL, para que ambos usem o
  mesmo OpenGL. O editor deteta automaticamente um OpenGL insuficiente e oferece este modo.
- GitHub Actions (Windows): testes, criação do `.exe` e autoteste do `.exe` em cada *push*.

## 8. Não incluído (melhorias futuras)

Curvas de Bézier, texto, operações booleanas entre formas, gradientes, edição de vértices
individuais, exportação SVG.
