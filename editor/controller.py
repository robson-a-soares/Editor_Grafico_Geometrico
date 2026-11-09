"""Estado da aplicação e comandos de edição.

O controlador liga o modelo (editor.core) à interface: guarda o documento,
a seleção, o histórico de desfazer e o estado da animação, e avisa os
painéis através de sinais Qt quando alguma coisa muda.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Signal

from .core import operations as ops
from .core.document import Document, Layer
from .core.fileio import image_id_for, load_document, save_document
from .core.history import History
from .core.shapes import GroupShape, ImageShape, Shape, Style, leaves, shape_from_dict

PALETTE = ["#5B8CFF", "#FF6B6B", "#FFD166", "#06D6A0", "#9B5DE5",
           "#F15BB5", "#00BBF9", "#FF9F1C", "#2EC4B6", "#E71D36"]


def hex_to_rgba(h: str, a: float = 1.0) -> tuple:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


class EditorController(QObject):
    documentReplaced = Signal()      # documento novo/aberto
    structureChanged = Signal()      # camadas ou objetos criados, apagados, reordenados, renomeados
    selectionChanged = Signal()
    objectsChanged = Signal()        # transformações/propriedades alteradas
    historyChanged = Signal()
    fileStateChanged = Signal()      # nome do ficheiro / alterações por guardar
    animationChanged = Signal(bool)  # reprodução ligada/desligada
    animationTick = Signal()
    viewOptionsChanged = Signal()
    message = Signal(str)

    def __init__(self):
        super().__init__()
        self.doc = Document()
        self.history = History(self.doc)
        self.selection: list[Shape] = []
        self.file_path: str | None = None
        self.show_grid = True
        self.snap_to_grid = False
        self.show_minimap = True
        self.clip_to_artboard = True
        self.playing = False
        self.anim_time = 0.0
        self.clipboard: list[dict] = []
        # estilo para formas novas
        self.auto_colors = True
        self.fill_color = hex_to_rgba(PALETTE[0])
        self.stroke_color = (0.11, 0.13, 0.18, 1.0)
        self.stroke_width = 2.0
        self._palette_i = 0

        self._clock = QElapsedTimer()
        self._last_ms = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(15)
        self._anim_timer.timeout.connect(self._tick)
        self._commit_timer = QTimer(self)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.setInterval(450)
        self._commit_timer.timeout.connect(self.flush_commit)
        self._pending_label: str | None = None

    # ------------------------------------------------------------------
    # Documento e ficheiros
    # ------------------------------------------------------------------
    def set_document(self, doc: Document, path: str | None = None) -> None:
        self.stop_animation()
        self._commit_timer.stop()
        self._pending_label = None
        self.doc = doc
        self.history = History(doc)
        self.selection = []
        self.file_path = path
        self.anim_time = 0.0
        self.documentReplaced.emit()
        self.structureChanged.emit()
        self.selectionChanged.emit()
        self.historyChanged.emit()
        self.fileStateChanged.emit()

    def new_document(self, width: float = 1280, height: float = 720) -> None:
        self.set_document(Document(width, height))

    def open_file(self, path: str) -> None:
        doc = load_document(path)
        self.set_document(doc, path)
        self.message.emit(f"Projeto aberto: {os.path.basename(path)}")

    def save_file(self, path: str) -> None:
        self.flush_commit()
        save_document(self.doc, path)
        self.file_path = path
        self.history.mark_saved()
        self.fileStateChanged.emit()
        self.message.emit(f"Projeto guardado: {os.path.basename(path)}")

    @property
    def dirty(self) -> bool:
        return self.history.dirty or self._pending_label is not None

    # ------------------------------------------------------------------
    # Histórico (desfazer / refazer)
    # ------------------------------------------------------------------
    def commit(self, label: str) -> None:
        self._commit_timer.stop()
        self._pending_label = None
        if self.history.commit(label):
            self.historyChanged.emit()
            self.fileStateChanged.emit()

    def commit_later(self, label: str) -> None:
        """Agrupa alterações rápidas (setas, campos numéricos) num único passo."""
        self._pending_label = label
        self._commit_timer.start()
        self.fileStateChanged.emit()

    def flush_commit(self) -> None:
        if self._pending_label is not None:
            self.commit(self._pending_label)

    def _restore_after_history(self) -> None:
        ids = [s.id for s in self.selection]
        self.selection = [s for s in (self.doc.find(i) for i in ids) if s is not None]
        self.structureChanged.emit()
        self.selectionChanged.emit()
        self.objectsChanged.emit()
        self.historyChanged.emit()
        self.fileStateChanged.emit()

    def undo(self) -> None:
        self.flush_commit()
        label = self.history.undo_label()
        if self.history.undo():
            self._restore_after_history()
            self.message.emit(f"Desfeito: {label}")

    def redo(self) -> None:
        self.flush_commit()
        if self.history.redo():
            self._restore_after_history()
            self.message.emit(f"Refeito: {self.history.labels[self.history.index]}")

    # ------------------------------------------------------------------
    # Seleção
    # ------------------------------------------------------------------
    def set_selection(self, shapes) -> None:
        new = []
        for s in shapes:
            if s is not None and s not in new and self._in_document(s):
                new.append(s)
        if new != self.selection:
            self.selection = new
            if new:  # a camada do objeto selecionado passa a ser a ativa
                layer = self.doc.layer_of(new[0])
                if layer is not None and layer.id != self.doc.active_layer_id:
                    self.doc.active_layer_id = layer.id
                    self.structureChanged.emit()
            self.selectionChanged.emit()

    def toggle_selection(self, shape: Shape) -> None:
        if shape in self.selection:
            self.set_selection([s for s in self.selection if s is not shape])
        else:
            self.set_selection(self.selection + [shape])

    def select_all(self) -> None:
        sel = []
        for layer in self.doc.layers:
            if layer.visible and not layer.locked:
                sel += [s for s in layer.objects if s.visible and not s.locked]
        self.set_selection(sel)

    def clear_selection(self) -> None:
        self.set_selection([])

    def editable_selection(self) -> list[Shape]:
        return [s for s in ops.without_descendants(self.selection) if self.doc.is_editable(s)]

    # ------------------------------------------------------------------
    # Notificações de alteração
    # ------------------------------------------------------------------
    def notify_modified(self, label: str | None = None, now: bool = False) -> None:
        self.objectsChanged.emit()
        if label:
            if now:
                self.commit(label)
            else:
                self.commit_later(label)

    def notify_structure(self, label: str | None = None) -> None:
        self.selection = [s for s in self.selection if self._in_document(s)]
        self.structureChanged.emit()
        self.selectionChanged.emit()
        self.objectsChanged.emit()
        if label:
            self.commit(label)

    def _in_document(self, s: Shape) -> bool:
        p = s
        while isinstance(p, Shape):
            p = p.parent
        return isinstance(p, Layer) and p in self.doc.layers

    # ------------------------------------------------------------------
    # Criação de objetos
    # ------------------------------------------------------------------
    def new_style(self, filled: bool = True) -> Style:
        st = Style()
        if self.auto_colors:
            st.fill = hex_to_rgba(PALETTE[self._palette_i % len(PALETTE)])
            self._palette_i += 1
        else:
            st.fill = tuple(self.fill_color)
        st.stroke = tuple(self.stroke_color)
        st.stroke_width = self.stroke_width
        if not filled:
            st.fill_mode = "none"
            st.stroke = st.fill if self.auto_colors else tuple(self.stroke_color)
            st.stroke_width = max(3.0, self.stroke_width)
        return st

    def add_shape(self, shape: Shape, label: str | None = None, select: bool = True) -> None:
        layer = self.doc.active_layer()
        if layer.locked or not layer.visible:
            layer.locked = False
            layer.visible = True
            self.message.emit(f"A camada '{layer.name}' foi desbloqueada e mostrada para receber o objeto.")
        layer.add(shape)
        if select:
            self.selection = [shape]
        self.notify_structure(label or f"Criar {shape.label.lower()}")

    def import_image(self, path: str, center=None) -> ImageShape:
        from .render.textures import image_size
        with open(path, "rb") as f:
            data = f.read()
        w, h = image_size(data)          # valida o ficheiro (lança exceção se não for imagem)
        iid = image_id_for(data)
        self.doc.images[iid] = data
        k = min(1.0, 0.6 * self.doc.width / w, 0.6 * self.doc.height / h)
        img = ImageShape(w * k, h * k, iid, name=os.path.splitext(os.path.basename(path))[0][:40] or "Imagem")
        cx, cy = center or (self.doc.width / 2.0, self.doc.height / 2.0)
        img.transform.tx, img.transform.ty = cx, cy
        self.add_shape(img, "Importar imagem")
        return img

    def import_texture(self, path: str) -> str:
        from .render.textures import image_size
        with open(path, "rb") as f:
            data = f.read()
        image_size(data)
        iid = image_id_for(data)
        self.doc.images[iid] = data
        return f"img:{iid}"

    # ------------------------------------------------------------------
    # Comandos de edição
    # ------------------------------------------------------------------
    def delete_selection(self) -> None:
        sel = self.editable_selection()
        if not sel:
            return
        ops.delete_shapes(sel)
        self.selection = []
        self.notify_structure("Apagar")

    def duplicate_selection(self) -> None:
        sel = self.editable_selection()
        if not sel:
            return
        self.selection = ops.duplicate_shapes(self.doc, sel)
        self.notify_structure("Duplicar")

    def copy_selection(self) -> None:
        sel = ops.sort_by_drawing_order(self.doc, ops.without_descendants(self.selection))
        if sel:
            self.clipboard = [s.to_dict() for s in sel]
            self.message.emit(f"{len(sel)} objeto(s) copiado(s)")

    def cut_selection(self) -> None:
        self.copy_selection()
        self.delete_selection()

    def paste(self) -> None:
        if not self.clipboard:
            return
        layer = self.doc.active_layer()
        new = []
        for d in self.clipboard:
            s = shape_from_dict(d, keep_ids=False)
            s.transform.tx += 20
            s.transform.ty -= 20
            layer.add(s)
            new.append(s)
        self.clipboard = [s.to_dict() for s in new]   # colar de novo desloca mais um pouco
        self.selection = new
        self.notify_structure("Colar")

    def group_selection(self) -> None:
        g = ops.group_shapes(self.doc, self.editable_selection())
        if g is None:
            self.message.emit("Selecione pelo menos dois objetos para agrupar.")
            return
        self.selection = [g]
        self.notify_structure("Agrupar")

    def ungroup_selection(self) -> None:
        groups = [s for s in self.editable_selection() if isinstance(s, GroupShape)]
        if not groups:
            self.message.emit("A seleção não contém grupos.")
            return
        new_sel = []
        for g in groups:
            new_sel += ops.ungroup(g)
        self.selection = new_sel
        self.notify_structure("Desagrupar")

    def reorder(self, how: str) -> None:
        sel = self.editable_selection()
        if not sel:
            return
        {"forward": ops.bring_forward, "backward": ops.send_backward,
         "front": ops.bring_to_front, "back": ops.send_to_back}[how](sel)
        self.notify_structure("Mudar a ordem")

    def nudge(self, dx: float, dy: float) -> None:
        sel = self.editable_selection()
        for s in sel:
            ops.translate_world(s, dx, dy)
        if sel:
            self.notify_modified("Mover")

    def rotate_selection(self, deg: float) -> None:
        sel = self.editable_selection()
        if sel:
            ops.rotate_shapes(sel, deg)
            self.notify_modified("Rodar")

    def scale_selection(self, factor: float) -> None:
        sel = self.editable_selection()
        if sel:
            ops.scale_shapes(sel, factor)
            self.notify_modified("Escalar")

    def flip_selection(self, horizontal: bool) -> None:
        sel = self.editable_selection()
        if sel:
            ops.flip_shapes(sel, horizontal)
            self.notify_modified("Espelhar", now=True)

    def reset_transform(self) -> None:
        sel = self.editable_selection()
        for s in sel:
            t = s.transform
            t.rotation, t.sx, t.sy, t.shear = 0.0, 1.0, 1.0, 0.0
        if sel:
            self.notify_modified("Repor transformação", now=True)

    def apply_fill(self, rgba) -> None:
        targets = [leaf for s in self.editable_selection() for leaf in leaves(s)]
        for s in targets:
            if s.has_fill and s.style.fill_mode != "image":
                s.style.fill = tuple(rgba)
                s.style.fill_mode = "color"
        if targets:
            self.notify_modified("Alterar cor", now=True)

    def apply_stroke(self, rgba) -> None:
        targets = [leaf for s in self.editable_selection() for leaf in leaves(s)]
        for s in targets:
            s.style.stroke = tuple(rgba)
            if s.style.stroke_width <= 0:
                s.style.stroke_width = max(1.0, self.stroke_width)
        if targets:
            self.notify_modified("Alterar contorno", now=True)

    def move_selection_to_layer(self, layer: Layer) -> None:
        sel = self.editable_selection()
        if sel:
            ops.move_to_layer(self.doc, sel, layer)
            self.doc.active_layer_id = layer.id
            self.notify_structure(f"Mover para '{layer.name}'")

    # ------------------------------------------------------------------
    # Camadas
    # ------------------------------------------------------------------
    def add_layer(self) -> None:
        self.doc.add_layer(above=self.doc.active_layer())
        self.notify_structure("Nova camada")

    def duplicate_layer(self) -> None:
        src = self.doc.active_layer()
        layer = self.doc.add_layer(f"{src.name} (cópia)", above=src)
        layer.opacity, layer.visible = src.opacity, src.visible
        for s in src.objects:
            layer.add(s.clone())
        self.notify_structure("Duplicar camada")

    def delete_layer(self) -> None:
        if len(self.doc.layers) <= 1:
            self.message.emit("O documento precisa de pelo menos uma camada.")
            return
        layer = self.doc.active_layer()
        i = self.doc.layers.index(layer)
        self.doc.layers.remove(layer)
        self.doc.active_layer_id = self.doc.layers[max(0, i - 1)].id
        self.notify_structure("Apagar camada")

    def move_layer(self, delta: int) -> None:
        layer = self.doc.active_layer()
        i = self.doc.layers.index(layer)
        j = max(0, min(len(self.doc.layers) - 1, i + delta))
        if i != j:
            self.doc.layers.insert(j, self.doc.layers.pop(i))
            self.notify_structure("Mover camada")

    def set_active_layer(self, layer: Layer) -> None:
        if self.doc.active_layer_id != layer.id:
            self.doc.active_layer_id = layer.id
            self.structureChanged.emit()

    def set_layer_flag(self, layer: Layer, visible=None, locked=None) -> None:
        if visible is not None:
            layer.visible = visible
        if locked is not None:
            layer.locked = locked
        self.notify_structure("Camada: visibilidade" if visible is not None else "Camada: bloqueio")

    def set_layer_opacity(self, layer: Layer, value: float) -> None:
        layer.opacity = max(0.0, min(1.0, value))
        self.notify_modified("Opacidade da camada")

    def rename(self, target, name: str) -> None:
        name = name.strip()
        if name and name != target.name:
            target.name = name
            self.notify_structure("Renomear")

    # ------------------------------------------------------------------
    # Animação
    # ------------------------------------------------------------------
    def has_animation(self) -> bool:
        return any(s.anim.active() for s in self.doc.iter_objects())

    def toggle_animation(self) -> None:
        if self.playing:
            self.stop_animation()
        else:
            self.start_animation()

    def start_animation(self) -> None:
        if self.playing:
            return
        self.flush_commit()
        self.playing = True
        self._clock.start()
        self._last_ms = 0
        self._anim_timer.start()
        self.animationChanged.emit(True)
        if not self.has_animation():
            self.message.emit("Nenhum objeto tem animação: defina-a no painel Propriedades → Animação.")

    def stop_animation(self) -> None:
        if not self.playing:
            return
        self.playing = False
        self._anim_timer.stop()
        self.animationChanged.emit(False)

    def reset_animation(self) -> None:
        self.anim_time = 0.0
        self.animationTick.emit()

    def _tick(self) -> None:
        ms = self._clock.elapsed()
        self.anim_time += (ms - self._last_ms) / 1000.0
        self._last_ms = ms
        self.animationTick.emit()
