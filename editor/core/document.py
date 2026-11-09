"""Documento do editor: prancheta, camadas e objetos.

Ordem de desenho: as camadas são desenhadas da primeira (fundo) para a
última (topo) e, dentro de cada camada, os objetos pela ordem da lista.
"""

from __future__ import annotations

from .shapes import GroupShape, Shape, iter_tree, new_id, shape_from_dict


class Layer:
    """Camada: um contentor de objetos com visibilidade, bloqueio e opacidade."""

    def __init__(self, name: str = "Camada", layer_id: str | None = None):
        self.id = layer_id or new_id("L")
        self.name = name
        self.visible = True
        self.locked = False
        self.opacity = 1.0
        self.objects: list[Shape] = []

    def add(self, shape: Shape, index: int | None = None) -> None:
        shape.parent = self
        if index is None:
            self.objects.append(shape)
        else:
            self.objects.insert(index, shape)

    def remove(self, shape: Shape) -> None:
        self.objects.remove(shape)
        shape.parent = None

    # um Layer comporta-se como um contentor tal como GroupShape
    @property
    def children(self) -> list[Shape]:
        return self.objects

    def to_dict(self) -> dict:
        return {"id": self.id, "nome": self.name, "visivel": self.visible,
                "bloqueada": self.locked, "opacidade": self.opacity,
                "objetos": [o.to_dict() for o in self.objects]}

    @staticmethod
    def from_dict(d: dict) -> "Layer":
        layer = Layer(d.get("nome", "Camada"), d.get("id"))
        layer.visible = bool(d.get("visivel", True))
        layer.locked = bool(d.get("bloqueada", False))
        layer.opacity = float(d.get("opacidade", 1.0))
        for od in d.get("objetos", []):
            layer.add(shape_from_dict(od))
        return layer

    def __repr__(self) -> str:
        return f"<Layer {self.name!r} ({len(self.objects)} objetos)>"


class Document:
    """Desenho completo: prancheta + camadas + imagens embutidas."""

    def __init__(self, width: float = 1280, height: float = 720):
        self.width = float(width)
        self.height = float(height)
        self.background = (1.0, 1.0, 1.0, 1.0)
        self.grid_size = 20.0
        self.layers: list[Layer] = [Layer("Camada 1")]
        self.active_layer_id = self.layers[0].id
        # imagens importadas: id -> bytes do ficheiro original (PNG/JPG).
        # Não entram no histórico de desfazer (são só acrescentadas).
        self.images: dict[str, bytes] = {}

    # ------------------------------------------------------------------
    # Camadas
    # ------------------------------------------------------------------
    @property
    def artboard(self) -> tuple[float, float, float, float]:
        return (0.0, 0.0, self.width, self.height)

    def active_layer(self) -> Layer:
        for layer in self.layers:
            if layer.id == self.active_layer_id:
                return layer
        if not self.layers:
            self.layers.append(Layer("Camada 1"))
        self.active_layer_id = self.layers[-1].id
        return self.layers[-1]

    def layer_by_id(self, layer_id: str) -> Layer | None:
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    def add_layer(self, name: str | None = None, above: Layer | None = None) -> Layer:
        layer = Layer(name or self.next_layer_name())
        if above is not None and above in self.layers:
            self.layers.insert(self.layers.index(above) + 1, layer)
        else:
            self.layers.append(layer)
        self.active_layer_id = layer.id
        return layer

    def next_layer_name(self) -> str:
        names = {layer.name for layer in self.layers}
        i = len(self.layers) + 1
        while f"Camada {i}" in names:
            i += 1
        return f"Camada {i}"

    # ------------------------------------------------------------------
    # Objetos
    # ------------------------------------------------------------------
    def iter_objects(self, include_children: bool = True):
        for layer in self.layers:
            if include_children:
                yield from iter_tree(layer.objects)
            else:
                yield from layer.objects

    def find(self, obj_id: str) -> Shape | None:
        for s in self.iter_objects():
            if s.id == obj_id:
                return s
        return None

    @staticmethod
    def layer_of(shape: Shape) -> Layer | None:
        p = shape.parent
        while isinstance(p, GroupShape):
            p = p.parent
        return p if isinstance(p, Layer) else None

    @staticmethod
    def top_level(shape: Shape) -> Shape:
        while isinstance(shape.parent, GroupShape):
            shape = shape.parent
        return shape

    def is_editable(self, shape: Shape) -> bool:
        """Visível e desbloqueado (ele, os grupos acima e a camada)."""
        s = shape
        while isinstance(s, Shape):
            if not s.visible or s.locked:
                return False
            s = s.parent
        layer = s if isinstance(s, Layer) else None
        return layer is not None and layer.visible and not layer.locked

    def used_image_ids(self) -> set[str]:
        ids: set[str] = set()
        for s in self.iter_objects():
            image_id = getattr(s, "image_id", None)
            if image_id:
                ids.add(image_id)
            tex = s.style.texture
            if s.style.fill_mode == "texture" and tex.startswith("img:"):
                ids.add(tex[4:])
        return ids

    def content_bbox(self):
        from .geometry import bbox_union
        from .shapes import world_bbox
        b = None
        for s in self.iter_objects(include_children=False):
            b = bbox_union(b, world_bbox(s))
        return b

    # ------------------------------------------------------------------
    # Serialização (sem imagens: essas vão à parte, ver fileio.py)
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"largura": self.width, "altura": self.height,
                "fundo": list(self.background), "grelha": self.grid_size,
                "camada_ativa": self.active_layer_id,
                "camadas": [layer.to_dict() for layer in self.layers]}

    def load_dict(self, d: dict) -> None:
        """Substitui o conteúdo (mantém as imagens já carregadas)."""
        self.width = float(d.get("largura", 1280))
        self.height = float(d.get("altura", 720))
        bg = d.get("fundo", [1, 1, 1, 1])
        self.background = tuple(float(v) for v in bg) + ((1.0,) if len(bg) == 3 else ())
        self.grid_size = float(d.get("grelha", 20))
        self.layers = [Layer.from_dict(ld) for ld in d.get("camadas", [])] or [Layer("Camada 1")]
        self.active_layer_id = d.get("camada_ativa", self.layers[-1].id)
        if self.layer_by_id(self.active_layer_id) is None:
            self.active_layer_id = self.layers[-1].id

    @staticmethod
    def from_dict(d: dict, images: dict | None = None) -> "Document":
        doc = Document()
        doc.load_dict(d)
        if images:
            doc.images.update(images)
        return doc
