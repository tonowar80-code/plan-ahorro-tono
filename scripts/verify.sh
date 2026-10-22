#!/usr/bin/env bash
# Comprobación completa del proyecto: formato, estilo y pruebas.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
uv run ruff format --check .
uv run ruff check .
uv run pytest -q
