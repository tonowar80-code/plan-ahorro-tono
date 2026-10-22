#!/usr/bin/env bash
# Prueba la conexión con Telegram: pregunta al API quién es el bot (solo lectura).
# Salida: 0 si el token funciona; distinto de 0 con detalle en stderr si no.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_PATH="$SCRIPT_DIR/.env"

[ -f "$ENV_PATH" ] || { echo "ERROR: falta $ENV_PATH (copia .env.example)" >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "$ENV_PATH"
set +a

: "${TELEGRAM_BOT_TOKEN:?Falta TELEGRAM_BOT_TOKEN en $ENV_PATH}"
: "${OWNER_TELEGRAM_ID:?Falta OWNER_TELEGRAM_ID en $ENV_PATH}"

response="$(curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe")"
if ! grep -q '"ok":true' <<<"$response"; then
  echo "ERROR: Telegram no acepta el token. Revisa TELEGRAM_BOT_TOKEN." >&2
  exit 1
fi
username="$(sed -n 's/.*"username":"\([^"]*\)".*/\1/p' <<<"$response")"
echo "OK — token válido para @${username}."
