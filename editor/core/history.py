"""Desfazer / refazer por instantâneos (snapshots).

Depois de cada ação concluída guardamos o estado completo do documento em
JSON (o mesmo formato do ficheiro .geo, mas sem as imagens). Desfazer é
simplesmente voltar a carregar o instantâneo anterior. É uma estratégia
simples e robusta: qualquer operação nova fica automaticamente coberta.
"""

from __future__ import annotations

import json


class History:
    def __init__(self, doc, limit: int = 100):
        self.doc = doc
        self.limit = limit
        self.states: list[str] = []
        self.labels: list[str] = []
        self.index = 0
        self.saved_index = 0
        self.reset()

    def _snapshot(self) -> str:
        return json.dumps(self.doc.to_dict(), separators=(",", ":"), ensure_ascii=False)

    def reset(self, label: str = "Início") -> None:
        self.states = [self._snapshot()]
        self.labels = [label]
        self.index = 0
        self.saved_index = 0

    def commit(self, label: str) -> bool:
        """Regista o estado atual. Devolve False se nada mudou."""
        snap = self._snapshot()
        if snap == self.states[self.index]:
            return False
        del self.states[self.index + 1:]
        del self.labels[self.index + 1:]
        self.states.append(snap)
        self.labels.append(label)
        self.index += 1
        if len(self.states) > self.limit:
            self.states.pop(0)
            self.labels.pop(0)
            self.index -= 1
            self.saved_index -= 1
        return True

    def can_undo(self) -> bool:
        return self.index > 0

    def can_redo(self) -> bool:
        return self.index < len(self.states) - 1

    def undo_label(self) -> str:
        return self.labels[self.index] if self.can_undo() else ""

    def redo_label(self) -> str:
        return self.labels[self.index + 1] if self.can_redo() else ""

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        self.index -= 1
        self.doc.load_dict(json.loads(self.states[self.index]))
        return True

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        self.index += 1
        self.doc.load_dict(json.loads(self.states[self.index]))
        return True

    def mark_saved(self) -> None:
        self.saved_index = self.index

    @property
    def dirty(self) -> bool:
        return self.index != self.saved_index
