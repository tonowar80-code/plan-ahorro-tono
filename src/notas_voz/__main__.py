"""Arranca el bot: uv run notas-voz"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from notas_voz.bot import TelegramBot
from notas_voz.config import ConfigError, load_settings
from notas_voz.core import VoiceNoteService
from notas_voz.google_api import build_services
from notas_voz.store import Store
from notas_voz.transcriber import WhisperTranscriber


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Las librerías de red registran URLs con el token del bot: las dejamos en avisos.
    for noisy in ("httpx", "telegram", "googleapiclient"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    try:
        settings = load_settings(Path.cwd())
        archive, mailer = build_services(settings.google_token)
    except (ConfigError, RuntimeError) as error:
        sys.exit(str(error))

    store = Store(settings.data_dir / "notas_voz.db")
    service = VoiceNoteService(
        store,
        WhisperTranscriber(settings.whisper_model),
        archive,
        mailer,
        settings.owner_id,
        settings.owner_email,
    )
    print("Bot en marcha. Para pararlo, pulsa Ctrl+C.")
    TelegramBot(service, settings.telegram_token, settings.data_dir / "audio").run()


if __name__ == "__main__":
    main()
