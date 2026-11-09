"""Guardar e carregar projetos (.geo).

Formato: um único ficheiro JSON legível, com as imagens importadas
embutidas em base64 — o projeto pode ser copiado para outro computador
sem perder nada.

    {
      "formato": "editor-grafico-geometrico",
      "versao": 1,
      "documento": { "largura": ..., "camadas": [ { "objetos": [...] } ] },
      "imagens": { "<id>": "<base64 do PNG/JPG original>" }
    }
"""

from __future__ import annotations

import base64
import hashlib
import json
import os

from .. import APP_NAME, __version__
from .document import Document

FORMAT = "editor-grafico-geometrico"
VERSION = 1


def image_id_for(data: bytes) -> str:
    return "img" + hashlib.sha1(data).hexdigest()[:12]


def document_to_data(doc: Document) -> dict:
    images = {iid: base64.b64encode(doc.images[iid]).decode("ascii")
              for iid in sorted(doc.used_image_ids()) if iid in doc.images}
    return {"formato": FORMAT, "versao": VERSION,
            "aplicacao": f"{APP_NAME} {__version__}",
            "documento": doc.to_dict(), "imagens": images}


def data_to_document(data: dict) -> Document:
    if not isinstance(data, dict) or data.get("formato") != FORMAT:
        raise ValueError("Este ficheiro não é um projeto do Editor Gráfico Geométrico.")
    if int(data.get("versao", 1)) > VERSION:
        raise ValueError("O projeto foi criado por uma versão mais recente do editor.")
    images = {k: base64.b64decode(v) for k, v in data.get("imagens", {}).items()}
    return Document.from_dict(data.get("documento", {}), images)


def save_document(doc: Document, path: str) -> None:
    data = document_to_data(doc)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)  # escrita atómica: nunca fica um ficheiro meio escrito


def load_document(path: str) -> Document:
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Ficheiro corrompido ou inválido ({e}).") from e
    return data_to_document(data)
