#!/usr/bin/env bash
# Prueba de verdad Drive y Gmail: crea la carpeta de prueba y envía un correo al dueño.
# Salida: 0 si todo funciona; distinto de 0 con detalle en stderr si no.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

[ -f "$SCRIPT_DIR/.env" ] || { echo "ERROR: falta $SCRIPT_DIR/.env (copia .env.example)" >&2; exit 1; }
[ -f "$SCRIPT_DIR/keys/token.json" ] || {
  echo "ERROR: falta conectar Google. Ejecuta: uv run notas-voz-conectar-google" >&2; exit 1; }

cd "$PROJECT_DIR"
uv run notas-voz-probar-google
