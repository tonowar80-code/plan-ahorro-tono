"""Reglas del bot, sin depender de Telegram ni de Google.

Cada método devuelve el texto que hay que contestar; quien lo llama decide cómo enviarlo.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Protocol

from notas_voz.store import Job, Store

log = logging.getLogger(__name__)

# Telegram solo deja descargar a un bot archivos de hasta 20 MB.
MAX_AUDIO_BYTES = 20 * 1024 * 1024
# Telegram admite 4096 caracteres por mensaje; dejamos margen para el resto del texto.
MAX_TEXT_IN_CHAT = 3500

HELP = (
    "Hola. Mándame una nota de voz (o reenvíame una) y te la paso a texto. "
    "La guardo en Google Drive y la envío por correo."
)
OWNER_HELP = (
    "\n\nComandos del dueño:\n"
    "/autorizar <número> [nombre] — dar acceso a una persona\n"
    "/retirar <número> — quitar el acceso\n"
    "/personas — ver quién tiene acceso"
)


# A partir de esta duración avisamos de que la transcripción tardará.
LONG_AUDIO_SECONDS = 120


def receipt_message(duration_seconds: int | None) -> str:
    if duration_seconds is not None and duration_seconds <= LONG_AUDIO_SECONDS:
        return "Audio recibido. Te mando el texto en un momento."
    return "Audio recibido. Puede tardar unos minutos en estar listo; te aviso al terminar."


class Transcriber(Protocol):
    def transcribe(self, audio_path: Path) -> str: ...


class Archive(Protocol):
    def ensure_folder(self, name: str) -> str: ...

    def save(
        self, folder_id: str, title: str, text: str, audio_path: Path, audio_mime: str
    ) -> str: ...


class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class VoiceNoteService:
    def __init__(
        self,
        store: Store,
        transcriber: Transcriber,
        archive: Archive,
        mailer: Mailer,
        owner_id: int,
        owner_email: str,
    ) -> None:
        self.store = store
        self.transcriber = transcriber
        self.archive = archive
        self.mailer = mailer
        self.owner_id = owner_id
        self.owner_email = owner_email
        # Evita que un reintento y una entrega en curso manden lo mismo dos veces.
        self._delivery_lock = threading.Lock()

    # --- Acceso ---

    def is_allowed(self, user_id: int) -> bool:
        return user_id == self.owner_id or self.store.is_person(user_id)

    def refusal(self, user_id: int, name: str) -> tuple[str, str | None]:
        """Respuesta para alguien sin acceso y aviso para el dueño (sin el contenido).

        El aviso solo se da la primera vez, para no llenar de mensajes al dueño.
        """
        first_time = self.store.requested_name(user_id) is None
        self.store.remember_request(user_id, name)
        reply = (
            "Lo siento, no tienes acceso a este bot. "
            f"Si conoces al dueño, pásale este número: {user_id}"
        )
        notice = (
            f"{name} (número {user_id}) ha intentado usar el bot.\n"
            f"Para darle acceso, escribe: /autorizar {user_id}"
        )
        return reply, (notice if first_time else None)

    def command(self, user_id: int, name: str, args: list[str]) -> str:
        if name in ("start", "ayuda"):
            return HELP + (OWNER_HELP if user_id == self.owner_id else "")
        if name not in ("autorizar", "retirar", "personas"):
            return "No conozco ese comando. Escribe /ayuda."
        if user_id != self.owner_id:
            return "Solo el dueño del bot puede usar este comando."
        if name == "personas":
            people = self.store.list_people()
            if not people:
                return "Todavía no has dado acceso a nadie."
            return "Tienen acceso:\n" + "\n".join(f"• {n} ({uid})" for uid, n in people)

        if not args or not args[0].lstrip("-").isdigit():
            return f"Escribe el número de la persona, por ejemplo: /{name} 123456789"
        target = int(args[0])
        if name == "autorizar":
            person = " ".join(args[1:]).strip() or self.store.requested_name(target)
            person = person or f"Persona {target}"
            self.store.add_person(target, person)
            return f"Hecho: {person} ya puede usar el bot."
        if self.store.remove_person(target):
            return "Hecho: esa persona ya no puede usar el bot."
        return "Esa persona no estaba en la lista."

    # --- Audios ---

    def check_size(self, size_bytes: int | None) -> str | None:
        if size_bytes is not None and size_bytes > MAX_AUDIO_BYTES:
            return (
                "Este audio es demasiado grande: Telegram solo me deja descargar hasta 20 MB. "
                "Prueba a mandarlo en partes más cortas."
            )
        return None

    def register(
        self,
        user_id: int,
        name: str,
        chat_id: int,
        received_at: datetime,
        audio_path: Path,
        mime: str,
    ) -> int:
        return self.store.create_job(user_id, name, chat_id, received_at, audio_path, mime)

    def unfinished_jobs(self) -> list[int]:
        return self.store.unfinished_jobs()

    def process(self, job_id: int) -> str:
        """Transcribe y entrega una nota de voz. Nunca lanza excepciones."""
        job = self.store.get_job(job_id)
        if job is None:
            return ""
        if job.transcript is None:
            try:
                text = self.transcriber.transcribe(job.audio_path).strip()
            except Exception:
                log.exception("Fallo al transcribir el trabajo %s", job_id)
                return (
                    "No he podido transcribir este audio. "
                    "Lo volveré a intentar cuando se reinicie el bot."
                )
            if not text:
                self._finish(job)
                return "No he encontrado voz en este audio, así que no he guardado nada."
        else:
            text = job.transcript

        with self._delivery_lock:
            self.store.set_transcript(job_id, text)
            job = self.store.get_job(job_id)
            failures, doc_link = self._deliver(job)
        return self._result_message(job, doc_link, failures)

    def retry_pending(self) -> list[tuple[int, str]]:
        """Reintenta las entregas pendientes. Devuelve avisos (chat, texto) de las completadas."""
        notices = []
        with self._delivery_lock:
            jobs = [self.store.get_job(job_id) for job_id in self.store.pending_deliveries()]
            results = [(job, self._deliver(job)[0]) for job in jobs]
        for job, failures in results:
            if failures:
                continue
            stamp = job.received_at.strftime("%d/%m a las %H:%M")
            notices.append(
                (job.chat_id, f"Ya está entregada la transcripción del audio del {stamp}.")
            )
        return notices

    # --- Interno ---

    def _deliver(self, job: Job) -> tuple[list[str], str | None]:
        """Entrega lo que falte. Devuelve qué destinos han fallado y el enlace de Drive."""
        failures = []
        doc_link = job.doc_link
        if not job.drive_done:
            try:
                folder = self._folder_for(job)
                title = f"{job.received_at:%Y-%m-%d %H.%M} - {job.name}"
                doc_link = self.archive.save(
                    folder, title, job.transcript, job.audio_path, job.mime
                )
                self.store.mark_drive_done(job.id, doc_link)
            except Exception:
                log.exception("Fallo al guardar en Drive el trabajo %s", job.id)
                failures.append("Drive")
        if not job.mail_done:
            try:
                self.mailer.send(self.owner_email, *self._email(job, doc_link))
                self.store.mark_mail_done(job.id)
            except Exception:
                log.exception("Fallo al enviar el correo del trabajo %s", job.id)
                failures.append("correo")
        if not failures:
            self._finish(job)
        return failures, doc_link

    def _folder_for(self, job: Job) -> str:
        folder = self.store.folder_for(job.user_id)
        if folder is None:
            folder = self.archive.ensure_folder(f"{job.name} ({job.user_id})")
            self.store.set_folder(job.user_id, folder)
        return folder

    def _email(self, job: Job, doc_link: str | None) -> tuple[str, str]:
        subject = f"Transcripción de {job.name} — {job.received_at:%Y-%m-%d %H:%M}"
        link = doc_link or "(todavía no está guardada en Drive; se reintentará)"
        body = (
            f"De: {job.name} (número {job.user_id})\n"
            f"Recibida: {job.received_at:%Y-%m-%d %H:%M}\n"
            f"En Google Drive: {link}\n\n"
            f"{job.transcript}\n"
        )
        return subject, body

    def _finish(self, job: Job) -> None:
        self.store.delete_job(job.id)
        job.audio_path.unlink(missing_ok=True)

    def _result_message(self, job: Job, doc_link: str | None, failures: list[str]) -> str:
        text = job.transcript
        if len(text) > MAX_TEXT_IN_CHAT:
            text = text[:MAX_TEXT_IN_CHAT].rstrip() + "… (texto completo en Drive y en el correo)"
        lines = ["Transcripción:", "", text, ""]
        if failures:
            lines.append(
                f"No he podido entregarla en: {' y '.join(failures)}. "
                "Lo voy a reintentar automáticamente y te aviso cuando esté."
            )
        elif job.user_id == self.owner_id:
            lines.append(f"Guardada en Drive: {doc_link}")
            lines.append("También te la he enviado por correo.")
        else:
            lines.append("Guardada en el Drive del dueño y enviada a su correo.")
        return "\n".join(lines)
