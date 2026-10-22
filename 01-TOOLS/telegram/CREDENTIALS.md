# Credenciales — Telegram

## Panel del proveedor

- Dónde: chat con @BotFather dentro de Telegram.
- Cuenta: la cuenta de Telegram del dueño.

## Variables

| Variable | Tipo | Dónde se genera | Rotación |
|----------|------|-----------------|----------|
| `TELEGRAM_BOT_TOKEN` | secreto | @BotFather → `/newbot` | Si se filtra: @BotFather → `/revoke` |
| `OWNER_TELEGRAM_ID` | no secreto | @userinfobot | Nunca cambia |

## Excepciones a la convención `<TOOL>_<VAR>`

- `OWNER_TELEGRAM_ID`: identifica al dueño, no a la herramienta; el bot lo lee con ese nombre.

## Si se filtra el token

1. En @BotFather: `/revoke` y elige el bot.
2. Copia el token nuevo en `.env` y reinicia el bot.
3. Apunta aquí la fecha del incidente.
