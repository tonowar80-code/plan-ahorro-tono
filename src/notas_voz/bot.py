"""Conexión con Telegram: recibe mensajes, descarga audios y contesta."""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from notas_voz.core import VoiceNoteService, receipt_message

log = logging.getLogger(__name__)

RETRY_EVERY_SECONDS = 5 * 60
COMMANDS = ["start", "ayuda", "autorizar", "retirar", "personas"]


@dataclass(frozen=True)
class AudioInfo:
    file_id: str
    size: int | None
    mime: str
    duration: int | None
    extension: str


def _extension(file_name: str | None, mime: str) -> str:
    if file_name and "." in file_name:
        return "." + file_name.rsplit(".", 1)[1].lower()
    return mimetypes.guess_extension(mime) or ".audio"


def classify(message: Any) -> AudioInfo | None:
    """Devuelve los datos del audio, o None si el mensaje no es un audio."""
    if message.voice is not None:
        v = message.voice
        mime = v.mime_type or "audio/ogg"
        return AudioInfo(v.file_id, v.file_size, mime, v.duration, ".ogg")
    if message.audio is not None:
        a = message.audio
        mime = a.mime_type or "audio/mpeg"
        return AudioInfo(a.file_id, a.file_size, mime, a.duration, _extension(a.file_name, mime))
    doc = message.document
    if doc is not None and (doc.mime_type or "").startswith("audio/"):
        ext = _extension(doc.file_name, doc.mime_type)
        return AudioInfo(doc.file_id, doc.file_size, doc.mime_type, None, ext)
    return None


def display_name(user: Any) -> str:
    return user.full_name or user.username or f"Persona {user.id}"


class TelegramBot:
    def __init__(self, service: VoiceNoteService, token: str, audio_dir: Path) -> None:
        self.service = service
        self.audio_dir = audio_dir
        self.queue: asyncio.Queue[int] = asyncio.Queue()
        self.app = Application.builder().token(token).post_init(self._start_background).build()
        # Solo chats privados con personas: los grupos y canales quedan fuera.
        private = filters.ChatType.PRIVATE & filters.USER
        self.app.add_handler(CommandHandler(COMMANDS, self.on_command, filters=private))
        audio = filters.VOICE | filters.AUDIO | filters.Document.AUDIO
        self.app.add_handler(MessageHandler(private & audio, self.on_audio))
        self.app.add_handler(MessageHandler(private & ~filters.COMMAND, self.on_other))

    def run(self) -> None:
        # No se descartan los mensajes pendientes: los que llegaron con el ordenador
        # apagado se procesan al arrancar.
        self.app.run_polling(drop_pending_updates=False)

    async def _start_background(self, app: Application) -> None:
        for job_id in self.service.unfinished_jobs():
            self.queue.put_nowait(job_id)
        app.create_task(self._worker())
        app.create_task(self._retry_loop())

    async def _refuse(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        reply, notice = self.service.refusal(user.id, display_name(user))
        await update.effective_message.reply_text(reply)
        if notice:
            await context.bot.send_message(self.service.owner_id, notice)

    async def on_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        name = update.effective_message.text.split()[0].lstrip("/").split("@")[0].lower()
        if not self.service.is_allowed(user.id):
            await self._refuse(update, context)
            return
        await update.effective_message.reply_text(
            self.service.command(user.id, name, list(context.args or []))
        )

    async def on_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user, message = update.effective_user, update.effective_message
        if not self.service.is_allowed(user.id):
            await self._refuse(update, context)
            return
        info = classify(message)
        too_big = self.service.check_size(info.size)
        if too_big:
            await message.reply_text(too_big)
            return
        await message.reply_text(receipt_message(info.duration))
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        path = self.audio_dir / f"{uuid.uuid4().hex}{info.extension}"
        try:
            tg_file = await context.bot.get_file(info.file_id)
            await tg_file.download_to_drive(path)
        except Exception:
            log.exception("Fallo al descargar un audio")
            await message.reply_text("No he podido descargar el audio. Prueba a mandarlo otra vez.")
            return
        received = message.date.astimezone() if message.date else datetime.now().astimezone()
        job_id = self.service.register(
            user.id,
            display_name(user),
            message.chat_id,
            received.replace(tzinfo=None),
            path,
            info.mime,
        )
        await self.queue.put(job_id)

    async def on_other(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self.service.is_allowed(update.effective_user.id):
            await self._refuse(update, context)
            return
        await update.effective_message.reply_text(
            "Solo sé transcribir audios. Mándame una nota de voz o un archivo de audio."
        )

    async def _worker(self) -> None:
        # Un solo trabajador: los audios se transcriben de uno en uno, en orden de llegada.
        while True:
            job_id = await self.queue.get()
            job = self.service.store.get_job(job_id)
            if job is None:
                continue
            try:
                reply = await asyncio.to_thread(self.service.process, job_id)
                if reply:
                    await self.app.bot.send_message(job.chat_id, reply)
            except Exception:
                log.exception("Fallo al contestar el trabajo %s", job_id)

    async def _retry_loop(self) -> None:
        while True:
            await asyncio.sleep(RETRY_EVERY_SECONDS)
            try:
                notices = await asyncio.to_thread(self.service.retry_pending)
                for chat_id, text in notices:
                    await self.app.bot.send_message(chat_id, text)
            except Exception:
                log.exception("Fallo en los reintentos")
