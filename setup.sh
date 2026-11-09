#!/usr/bin/env bash
# Preparar o ambiente em Linux/macOS: cria .venv e instala as dependências fixas.
set -e
cd "$(dirname "$0")"
PY=""
for v in 3.12 3.13 3.11 3.14 3.10; do
  if command -v "python$v" >/dev/null 2>&1; then PY="python$v"; break; fi
done
PY="${PY:-python3}"
echo "A usar: $($PY --version)"
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py --selftest autoteste
echo "Pronto! Para abrir o editor: ./run.sh"
