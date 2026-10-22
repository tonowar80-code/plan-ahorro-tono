# Bot de notas de voz

Un bot de Telegram que pasa tus notas de voz a texto, guarda el texto (como documento de
Google Docs) y el audio en tu Google Drive, y te lo envía por correo.

- La transcripción se hace **en tu ordenador**: es gratis y tus audios no van a ninguna empresa
  de transcripción.
- Solo lo pueden usar tú y las personas que autorices.
- Funciona mientras tu ordenador está encendido y el bot en marcha.

## Qué necesitas

- Un ordenador (Windows, Mac o Linux) con unos 2 GB de espacio libre.
- Una cuenta de Telegram y una cuenta de Google (Gmail).

## Instalación (una sola vez)

1. **Instala `uv`**, el programa que prepara Python por ti:
   - Mac o Linux: abre la Terminal y pega
     `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows: abre PowerShell y pega
     `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. **Descarga este proyecto** y abre una terminal dentro de su carpeta.
3. Ejecuta `uv sync`. Descarga todo lo necesario (unos minutos la primera vez).
4. **Telegram**: sigue `01-TOOLS/telegram/README.md` (5 minutos).
5. **Google**: sigue `01-TOOLS/google/README.md` (unos 15 minutos).

## Uso

En la carpeta del proyecto:

```
uv run notas-voz
```

La primera vez descarga el modelo de voz (unos 500 MB). Deja la ventana abierta: mientras
esté abierta, el bot funciona. Para pararlo, pulsa `Ctrl+C`.

En Telegram:

- Mándale (o reenvíale) una nota de voz o un archivo de audio. Te contesta «recibido» y,
  al terminar, el texto.
- `/autorizar <número> [nombre]`: da acceso a una persona. Cuando alguien sin acceso le escribe
  al bot, te llega un aviso con su número y el comando listo para copiar.
- `/retirar <número>`: quita el acceso.
- `/personas`: lista quién tiene acceso.

## Ajustes opcionales

En `01-TOOLS/telegram/.env` puedes añadir:

- `WHISPER_MODEL=base`: más rápido pero menos preciso. `medium` es más preciso pero más lento.
  Por defecto: `small`.

## Para quien programa

- Código en `src/notas_voz/`, pruebas en `tests/`.
- `scripts/verify.sh` comprueba formato, estilo y pruebas.
- Documentación del proyecto: `02-DOCS/wiki/index.md`.
