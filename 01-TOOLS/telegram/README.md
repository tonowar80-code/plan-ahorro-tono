# Telegram

> El bot de Telegram que recibe tus notas de voz.

## Cuándo se usa

Siempre: es la puerta de entrada. Tú y las personas que autorices le mandáis audios.

## Puesta en marcha (una sola vez)

1. En Telegram, abre un chat con **@BotFather** y escribe `/newbot`.
2. Elige un nombre (por ejemplo «Mis notas de voz») y un usuario que acabe en `bot`.
3. BotFather te da un **token** (algo como `123456:ABC-...`). Es una contraseña: no lo compartas.
4. Abre un chat con **@userinfobot**: te dice tu **número de usuario** (Id).
5. En esta carpeta: `cp .env.example .env && chmod 600 .env` y escribe ahí el token y tu número.
6. `./test_connection.sh` — tiene que terminar con `OK — …`.

## Scripts

| Script | Qué hace | Ejemplo |
|--------|----------|---------|
| `test_connection.sh` | Comprueba que el token funciona. | `./test_connection.sh` |

## Notas

- Gratis. Telegram solo deja a un bot descargar archivos de hasta 20 MB.
- Si el ordenador está apagado más de unas 24 horas, Telegram puede borrar los mensajes pendientes.
