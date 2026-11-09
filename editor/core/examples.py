"""Projetos de exemplo, construídos por código.

Servem para demonstrar o editor (e para o vídeo): modelação com primitivas,
agrupamento hierárquico, camadas, texturas, imagens e animação.
"""

from __future__ import annotations

import io
import math
import random

from .document import Document, Layer
from .shapes import (EllipseShape, GroupShape, ImageShape, PathShape, RectShape,
                     RegularPolygonShape, Shape, TriangleShape)


# ----------------------------------------------------------------------
# Auxiliares
# ----------------------------------------------------------------------
def rgba(hex_color: str, alpha: float = 1.0) -> tuple:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


def styled(s: Shape, fill=None, stroke=None, width=0.0, texture=None, repeat=2.0,
           opacity=1.0, name=None) -> Shape:
    if texture:
        s.style.fill_mode = "texture"
        s.style.texture = f"builtin:{texture}"
        s.style.texture_repeat = repeat
    elif fill is None:
        s.style.fill_mode = "none"
    else:
        s.style.fill_mode = "color"
        s.style.fill = fill if isinstance(fill, tuple) else rgba(fill)
    if stroke:
        s.style.stroke = stroke if isinstance(stroke, tuple) else rgba(stroke)
        s.style.stroke_width = width or 2.0
    else:
        s.style.stroke_width = 0.0
    s.style.opacity = opacity
    if name:
        s.name = name
    return s


def at(s: Shape, x: float, y: float, rot: float = 0.0, sx: float = 1.0, sy: float | None = None,
       shear: float = 0.0) -> Shape:
    t = s.transform
    t.tx, t.ty, t.rotation, t.sx, t.sy, t.shear = x, y, rot, sx, sx if sy is None else sy, shear
    return s


def group(name: str, x: float, y: float, children, rot: float = 0.0) -> GroupShape:
    """Grupo com pivô em (x, y); os filhos são dados em coordenadas relativas ao pivô."""
    g = GroupShape(name=name)
    at(g, x, y, rot)
    for c in children:
        g.add(c)
    return g


def polygon_from_world(points, **style) -> PathShape:
    """Polígono a partir de pontos do mundo: centra os pontos e põe a posição na matriz."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    p = PathShape([(x - cx, y - cy) for x, y in points], closed=True)
    at(p, cx, cy)
    return styled(p, **style)


def line(x0, y0, x1, y1, color, width=3.0, name="Linha") -> PathShape:
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    p = PathShape([(x0 - cx, y0 - cy), (x1 - cx, y1 - cy)], closed=False, name=name)
    at(p, cx, cy)
    return styled(p, fill=None, stroke=color, width=width)


def sample_image_bytes(w: int = 480, h: int = 320) -> bytes:
    """Gera uma 'fotografia' sintética (PNG) para os exemplos de imagens digitais."""
    from PIL import Image, ImageDraw, ImageFilter

    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h * 0.62)
        for x in range(w):
            if y < h * 0.62:  # céu em gradiente
                r = int(40 + 215 * t)
                g = int(80 + 120 * t)
                b = int(170 - 60 * t)
            else:             # lago
                tt = (y - h * 0.62) / (h * 0.38)
                r, g, b = int(30 + 40 * tt), int(70 + 50 * tt), int(110 + 40 * tt)
            px[x, y] = (r, g, b)
    d = ImageDraw.Draw(img)
    d.ellipse((w * 0.62, h * 0.30, w * 0.80, h * 0.57), fill=(255, 214, 120))
    d.polygon([(0, h * 0.62), (w * 0.18, h * 0.32), (w * 0.38, h * 0.62)], fill=(70, 60, 90))
    d.polygon([(w * 0.22, h * 0.62), (w * 0.48, h * 0.22), (w * 0.74, h * 0.62)], fill=(95, 75, 110))
    d.polygon([(w * 0.55, h * 0.62), (w * 0.82, h * 0.38), (w, h * 0.55), (w, h * 0.62)], fill=(60, 50, 80))
    for i in range(8):  # reflexos do sol na água
        y = h * 0.66 + i * 9
        d.line((w * 0.62 + i * 3, y, w * 0.80 - i * 3, y), fill=(255, 200, 120), width=2)
    img = img.filter(ImageFilter.SMOOTH)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ----------------------------------------------------------------------
# Exemplo 1 — Casa e paisagem
# ----------------------------------------------------------------------
def build_house() -> Document:
    doc = Document(1280, 720)
    sky = doc.layers[0]
    sky.name = "Céu"
    land = Layer("Paisagem")
    house_layer = Layer("Casa")
    details = Layer("Detalhes")
    doc.layers += [land, house_layer, details]

    sky.add(styled(at(RectShape(1280, 720), 640, 360), fill="#7EC8F0", name="Céu"))
    sky.add(styled(at(RectShape(1280, 200), 640, 260), fill=rgba("#CFEFFF", 0.6), name="Horizonte"))
    sky.add(polygon_from_world([(0, 150), (0, 300), (150, 380), (290, 300), (430, 410), (600, 310),
                                (760, 400), (930, 300), (1080, 370), (1280, 290), (1280, 150)],
                               fill="#9DBEDD", name="Montanhas ao longe"))
    rays = styled(at(RegularPolygonShape(14, 125, 0.72), 1050, 560), fill=rgba("#FFE08A", 0.85), name="Raios do sol")
    rays.anim.rotate = 14
    sky.add(rays)
    sun = styled(at(EllipseShape(70, 70), 1050, 560), fill="#FFC93C", stroke="#F4A300", width=4, name="Sol")
    sun.anim.pulse, sun.anim.pulse_freq = 0.05, 0.6
    sky.add(sun)
    for i, (x, y, k, amp, f) in enumerate([(300, 600, 1.0, 45, 0.08), (780, 640, 0.7, 35, 0.11)]):
        cloud = group(f"Nuvem {i + 1}", x, y, [
            styled(at(EllipseShape(55, 35), -55, 0), fill="#FFFFFF"),
            styled(at(EllipseShape(68, 46), 8, 14), fill="#FFFFFF"),
            styled(at(EllipseShape(52, 32), 70, 0), fill="#FFFFFF"),
        ])
        cloud.transform.sx = cloud.transform.sy = k
        cloud.anim.osc_x, cloud.anim.osc_freq = amp, f
        sky.add(cloud)

    land.add(styled(at(EllipseShape(540, 200), 250, 125), fill="#77C35F", name="Colina"))
    land.add(styled(at(EllipseShape(620, 230), 1120, 105), fill="#5DAF4F", name="Colina 2"))
    land.add(styled(at(RectShape(1280, 165), 640, 82), texture="relva", repeat=6, name="Relva"))
    land.add(polygon_from_world([(612, 162), (688, 162), (790, 0), (510, 0)],
                                fill="#D9C9A3", stroke="#B9A57A", width=2, name="Caminho"))

    window_parts = []
    for name, x in (("Janela esquerda", -110), ("Janela direita", 110)):
        window_parts.append(group(name, x, 25, [
            styled(RectShape(84, 72), fill="#BFE6FF", stroke="#FFFFFF", width=6),
            line(-42, 0, 42, 0, "#FFFFFF", 4),
            line(0, -36, 0, 36, "#FFFFFF", 4),
        ]))
    house = group("Casa", 650, 280, [
        styled(at(RectShape(42, 95), 110, 230), fill="#8B4A3C", stroke="#4A2B1E", width=3, name="Chaminé"),
        styled(RectShape(360, 230), texture="tijolo", repeat=3, stroke="#5A3B2E", width=3, name="Paredes"),
        styled(at(TriangleShape(440, 160), 0, 195), texture="madeira", repeat=2,
               stroke="#4A2B1E", width=3, name="Telhado"),
        styled(at(RectShape(72, 122), 0, -54), texture="madeira", repeat=1,
               stroke="#3B2416", width=3, name="Porta"),
        styled(at(EllipseShape(6, 6), 22, -54), fill="#F2C14E", name="Maçaneta"),
        *window_parts,
    ])
    house_layer.add(house)

    tree = group("Árvore", 190, 260, [
        styled(at(RectShape(36, 130), 0, -40), texture="madeira", repeat=1, name="Tronco"),
        styled(at(EllipseShape(82, 70), 0, 70), fill="#2E8B57", name="Copa"),
        styled(at(EllipseShape(60, 50), -45, 40), fill="#3CA55C", name="Copa"),
        styled(at(EllipseShape(60, 50), 45, 40), fill="#3CA55C", name="Copa"),
    ])
    details.add(tree)
    rnd = random.Random(7)
    colors = ["#FF5D8F", "#FFD166", "#C77DFF", "#FF7F51", "#4CC9F0"]
    for i in range(9):
        x = 60 + i * 47 + rnd.uniform(-8, 8)
        if 480 < x < 820:
            continue
        f = styled(at(RegularPolygonShape(5, 13, 0.45), x, 40 + rnd.uniform(0, 45)),
                   fill=colors[i % len(colors)], stroke="#FFFFFF", width=1.5, name="Flor")
        f.anim.rotate = rnd.choice([-40, 40])
        f.anim.hue = 50
        details.add(f)
    for i in range(6):
        x = 880 + i * 62 + rnd.uniform(-10, 10)
        f = styled(at(RegularPolygonShape(6, 11, 0.5), x, 45 + rnd.uniform(0, 40)),
                   fill=colors[(i + 2) % len(colors)], name="Flor")
        f.anim.pulse, f.anim.pulse_freq = 0.15, 0.8 + 0.1 * i
        details.add(f)
    doc.active_layer_id = details.id
    return doc


# ----------------------------------------------------------------------
# Exemplo 2 — Sistema solar (transformações hierárquicas)
# ----------------------------------------------------------------------
def build_solar_system() -> Document:
    doc = Document(1280, 720)
    doc.background = (0.04, 0.05, 0.13, 1.0)
    stars = doc.layers[0]
    stars.name = "Estrelas"
    orbits = Layer("Órbitas")
    bodies = Layer("Astros")
    doc.layers += [orbits, bodies]

    rnd = random.Random(42)
    for _ in range(70):
        x, y = rnd.uniform(0, 1280), rnd.uniform(0, 720)
        if math.hypot(x - 640, y - 360) < 120:
            continue
        if rnd.random() < 0.25:
            s = styled(at(RegularPolygonShape(4, rnd.uniform(4, 7), 0.35), x, y, rnd.uniform(0, 90)),
                       fill="#FFFFFF", name="Estrela")
            s.anim.pulse, s.anim.pulse_freq = 0.45, rnd.uniform(0.3, 1.2)
        else:
            r = rnd.uniform(1.0, 2.4)
            s = styled(at(EllipseShape(r, r), x, y), fill=rgba("#FFFFFF", rnd.uniform(0.5, 1)), name="Estrela")
        stars.add(s)

    cx, cy = 640, 360
    planets = [  # nome, distância, raio, cor, velocidade angular (°/s), ângulo inicial
        ("Mercúrio", 82, 8, "#BDBDBD", 48, 30),
        ("Vénus", 120, 13, "#E8C07D", 35, 200),
        ("Terra", 165, 15, "#3D8BFD", 29, 120),
        ("Marte", 210, 11, "#E2643A", 24, 300),
        ("Júpiter", 262, 26, "#D8A47F", 13, 60),
        ("Saturno", 318, 17, "#E9D18A", 9, 240),
    ]
    for name, dist, r, color, speed, a0 in planets:
        orbits.add(styled(at(EllipseShape(dist, dist), cx, cy), fill=None,
                          stroke=(1, 1, 1, 0.22), width=1.5, name=f"Órbita de {name}"))
        if name == "Terra":
            moon = styled(at(EllipseShape(5, 5), 28, 0), fill="#E6E6E6", name="Lua")
            body = group("Terra e Lua", dist, 0, [
                styled(EllipseShape(r, r), fill=color, stroke="#9ED0FF", width=2, name="Terra"),
                moon,
            ])
            body.anim.rotate = 110       # a Lua orbita a Terra
        elif name == "Saturno":
            body = group("Saturno", dist, 0, [
                styled(EllipseShape(r, r), fill=color, name="Planeta"),
                styled(EllipseShape(32, 9), fill=None, stroke="#F3E3B5", width=3, name="Anéis"),
            ], rot=25)
        else:
            body = styled(at(EllipseShape(r, r), dist, 0), fill=color, name=name)
        orbit = group(f"Translação de {name}", cx, cy, [body], rot=a0)
        orbit.anim.rotate = speed       # rodar o grupo = o planeta orbita o Sol
        bodies.add(orbit)

    corona = styled(at(RegularPolygonShape(16, 92, 0.78), cx, cy), fill=rgba("#FFB703", 0.9), name="Coroa solar")
    corona.anim.rotate = 12
    sun = styled(at(EllipseShape(60, 60), cx, cy), fill="#FFD23F", stroke="#FFB000", width=4, name="Sol")
    sun.anim.pulse, sun.anim.pulse_freq = 0.04, 0.5
    bodies.add(corona)
    bodies.add(sun)
    doc.active_layer_id = bodies.id
    return doc


# ----------------------------------------------------------------------
# Exemplo 3 — Transformações geométricas
# ----------------------------------------------------------------------
ARROW = [(-60, -20), (20, -20), (20, -45), (70, 0), (20, 45), (20, 20), (-60, 20)]


def build_transformations() -> Document:
    doc = Document(1280, 720)
    doc.background = rgba("#F6F7FB")
    guides = doc.layers[0]
    guides.name = "Guias"
    shapes_layer = Layer("Transformações")
    markers = Layer("Pivôs")
    doc.layers += [shapes_layer, markers]

    cells = [  # (nome, tx, ty, rot, sx, sy, k, cor)
        ("Original", 0, 0, 0, 1, 1, 0, "#5B8CFF"),
        ("Translação T(60, 50)", 60, 50, 0, 1, 1, 0, "#2EC4B6"),
        ("Rotação R(45°)", 0, 0, 45, 1, 1, 0, "#FF9F1C"),
        ("Escala S(1.5; 0.6)", 0, 0, 0, 1.5, 0.6, 0, "#E71D36"),
        ("Cisalhamento Sh(0.6)", 0, 0, 0, 1, 1, 0.6, "#9B5DE5"),
        ("Espelho horizontal S(-1; 1)", 0, 0, 0, -1, 1, 0, "#00BBF9"),
        ("Espelho vertical S(1; -1)", 0, 0, 30, 1, -1, 0, "#F15BB5"),
        ("Composta T·R·Sh·S", 30, -20, -30, 1.3, 0.9, 0.35, None),
    ]
    for i, (name, tx, ty, rot, sx, sy, k, color) in enumerate(cells):
        col, row = i % 4, i // 4
        cx, cy = 160 + col * 320, 540 - row * 340
        guides.add(styled(at(RectShape(296, 300), cx, cy), fill="#FFFFFF", stroke="#D5D9E5",
                          width=2, name=f"Célula: {name}"))
        guides.add(line(cx - 130, cy, cx + 130, cy, "#E4E7EF", 1.5, "Eixo x"))
        guides.add(line(cx, cy - 130, cx, cy + 130, "#E4E7EF", 1.5, "Eixo y"))
        ghost = styled(at(PathShape(ARROW), cx, cy), fill=rgba("#8A93A6", 0.18), name=f"Referência: {name}")
        guides.add(ghost)
        arrow = PathShape(ARROW, name=name)
        if color:
            styled(arrow, fill=color, stroke="#1D2433", width=2.5)
        else:
            styled(arrow, texture="marmore", repeat=1.5, stroke="#1D2433", width=2.5)
        at(arrow, cx + tx, cy + ty, rot, sx, sy, k)
        shapes_layer.add(arrow)
        markers.add(styled(at(EllipseShape(4.5, 4.5), cx, cy), fill="#FFFFFF", stroke="#1D2433",
                           width=2, name="Pivô (origem)"))
    doc.active_layer_id = shapes_layer.id
    return doc


# ----------------------------------------------------------------------
# Exemplo 4 — Imagens digitais e texturas
# ----------------------------------------------------------------------
def build_images_and_textures() -> Document:
    from .fileio import image_id_for

    doc = Document(1280, 720)
    doc.background = rgba("#20232B")
    photos = doc.layers[0]
    photos.name = "Imagens"
    textures = Layer("Texturas")
    doc.layers.append(textures)

    data = sample_image_bytes()
    iid = image_id_for(data)
    doc.images[iid] = data
    for i, (name, filters) in enumerate([("Original", []), ("Tons de cinzento", ["cinzento"]),
                                         ("Negativo", ["negativo"]), ("Sépia", ["sepia"])]):
        img = ImageShape(270, 180, iid, name=f"Imagem — {name}")
        img.filters = list(filters)
        img.style.stroke = rgba("#FFFFFF")
        img.style.stroke_width = 4
        at(img, 170 + i * 313, 560, rot=(-4, 3, -2, 4)[i])
        photos.add(img)

    names = ["xadrez", "tijolo", "madeira", "marmore", "listras", "bolinhas", "relva", "pedra"]
    for i, tex in enumerate(names):
        col, row = i % 4, i // 4
        x, y = 170 + col * 313, 315 - row * 190
        if i % 3 == 0:
            s = RegularPolygonShape(6, 74, 0.0)
        elif i % 3 == 1:
            s = EllipseShape(92, 66)
        else:
            s = RectShape(180, 130)
        styled(s, texture=tex, repeat=2, stroke="#FFFFFF", width=3, name=f"Textura {tex}")
        at(s, x, y)
        if i == 4:
            s.anim.rotate = 20
        textures.add(s)
    doc.active_layer_id = textures.id
    return doc


EXAMPLES = [
    ("Casa e paisagem", "Camadas, agrupamento, texturas e animação", build_house),
    ("Sistema solar", "Transformações hierárquicas: grupos que rodam", build_solar_system),
    ("Transformações geométricas", "T, R, S, cisalhamento e espelhos", build_transformations),
    ("Imagens e texturas", "Imagens digitais, filtros e texturas", build_images_and_textures),
]
