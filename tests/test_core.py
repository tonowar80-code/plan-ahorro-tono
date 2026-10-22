from datetime import datetime
from pathlib import Path

import pytest

from notas_voz.core import MAX_AUDIO_BYTES, VoiceNoteService
from notas_voz.store import Store

OWNER = 1
OWNER_EMAIL = "dueno@example.com"
WHEN = datetime(2026, 10, 22, 20, 30)


class FakeTranscriber:
    def __init__(self, text: str = "hola, esto es una prueba") -> None:
        self.text = text
        self.calls: list[Path] = []

    def transcribe(self, audio_path: Path) -> str:
        self.calls.append(audio_path)
        return self.text


class FakeArchive:
    def __init__(self) -> None:
        self.folders: list[str] = []
        self.saved: list[dict] = []
        self.fail = False

    def ensure_folder(self, name: str) -> str:
        self.folders.append(name)
        return f"folder:{name}"

    def save(self, folder_id, title, text, audio_path, audio_mime) -> str:
        if self.fail:
            raise RuntimeError("drive caído")
        self.saved.append(
            dict(folder_id=folder_id, title=title, text=text, audio=audio_path, mime=audio_mime)
        )
        return f"https://docs.google.com/{len(self.saved)}"


class FakeMailer:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.fail = False

    def send(self, to, subject, body) -> None:
        if self.fail:
            raise RuntimeError("correo caído")
        self.sent.append(dict(to=to, subject=subject, body=body))


@pytest.fixture
def env(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    transcriber, archive, mailer = FakeTranscriber(), FakeArchive(), FakeMailer()
    service = VoiceNoteService(store, transcriber, archive, mailer, OWNER, OWNER_EMAIL)

    def new_job(user_id=OWNER, name="Tono"):
        audio = tmp_path / f"audio-{len(list(tmp_path.iterdir()))}.ogg"
        audio.write_bytes(b"ogg")
        return service.register(user_id, name, user_id * 10, WHEN, audio, "audio/ogg"), audio

    return dict(
        store=store,
        service=service,
        transcriber=transcriber,
        archive=archive,
        mailer=mailer,
        new_job=new_job,
    )


# --- Acceso (criterios #4, #5, #5b) ---


def test_owner_is_always_allowed(env):
    assert env["service"].is_allowed(OWNER)
    assert not env["service"].is_allowed(2)


def test_refusal_for_unknown_person_and_notice_to_owner(env):
    reply, notice = env["service"].refusal(2, "Luis")
    assert notice is not None
    assert "no tienes acceso" in reply.lower()
    assert "/autorizar 2" in notice and "Luis" in notice
    assert env["store"].requested_name(2) == "Luis"
    assert env["archive"].saved == [] and env["mailer"].sent == []


def test_owner_authorizes_and_revokes_with_requested_name(env):
    service = env["service"]
    service.refusal(2, "Luis")
    reply = service.command(OWNER, "autorizar", ["2"])
    assert "Luis" in reply
    assert service.is_allowed(2)
    assert "Luis" in service.command(OWNER, "personas", [])
    reply = service.command(OWNER, "retirar", ["2"])
    assert not service.is_allowed(2)


def test_owner_can_give_a_name(env):
    env["service"].command(OWNER, "autorizar", ["3", "María", "José"])
    assert env["store"].list_people() == [(3, "María José")]


def test_autorizar_needs_a_number(env):
    reply = env["service"].command(OWNER, "autorizar", ["abc"])
    assert "/autorizar" in reply
    assert env["store"].list_people() == []


def test_retirar_unknown_person(env):
    assert "no estaba" in env["service"].command(OWNER, "retirar", ["5"]).lower()


@pytest.mark.parametrize("command", ["autorizar", "retirar", "personas"])
def test_non_owner_cannot_manage_access(env, command):
    env["store"].add_person(2, "Luis")
    reply = env["service"].command(2, command, ["3"])
    assert "solo el dueño" in reply.lower()
    assert env["store"].list_people() == [(2, "Luis")]


def test_help_command_for_everyone(env):
    assert "nota de voz" in env["service"].command(2, "start", []).lower()


# --- Tamaño ---


def test_size_limit(env):
    service = env["service"]
    assert service.check_size(None) is None
    assert service.check_size(MAX_AUDIO_BYTES) is None
    assert "20 MB" in service.check_size(MAX_AUDIO_BYTES + 1)


# --- Procesado (criterios #1, #2, #3, #6) ---


def test_owner_voice_note_is_saved_mailed_and_answered(env):
    job_id, audio = env["new_job"]()
    reply = env["service"].process(job_id)

    assert "hola, esto es una prueba" in reply
    assert "https://docs.google.com/1" in reply  # el dueño ve el enlace

    [saved] = env["archive"].saved
    assert env["archive"].folders == ["Tono (1)"]
    assert saved["folder_id"] == "folder:Tono (1)"
    assert saved["title"] == "2026-10-22 20.30 - Tono"
    assert saved["text"] == "hola, esto es una prueba"
    assert saved["audio"] == audio and saved["mime"] == "audio/ogg"

    [mail] = env["mailer"].sent
    assert mail["to"] == OWNER_EMAIL
    assert "Tono" in mail["subject"] and "2026-10-22 20:30" in mail["subject"]
    assert "hola, esto es una prueba" in mail["body"]
    assert "https://docs.google.com/1" in mail["body"]

    # Entregado: no queda nada pendiente y se borra el audio local
    assert env["store"].get_job(job_id) is None
    assert not audio.exists()


def test_other_person_gets_text_but_not_the_owner_drive_link(env):
    env["store"].add_person(2, "Luis")
    job_id, _ = env["new_job"](user_id=2, name="Luis")
    reply = env["service"].process(job_id)
    assert "hola, esto es una prueba" in reply
    assert "docs.google.com" not in reply
    assert "guardad" in reply.lower()
    assert env["archive"].folders == ["Luis (2)"]
    assert env["mailer"].sent[0]["to"] == OWNER_EMAIL


def test_folder_is_created_once_per_person(env):
    for _ in range(2):
        job_id, _ = env["new_job"]()
        env["service"].process(job_id)
    assert env["archive"].folders == ["Tono (1)"]


def test_long_text_is_shortened_in_telegram_only(env):
    env["transcriber"].text = "palabra " * 1000
    job_id, _ = env["new_job"]()
    reply = env["service"].process(job_id)
    assert len(reply) < 4096
    assert env["archive"].saved[0]["text"] == ("palabra " * 1000).strip()


def test_no_speech_creates_nothing(env):
    env["transcriber"].text = "   "
    job_id, audio = env["new_job"]()
    reply = env["service"].process(job_id)
    assert "no he encontrado voz" in reply.lower()
    assert env["archive"].saved == [] and env["mailer"].sent == []
    assert env["store"].get_job(job_id) is None
    assert not audio.exists()


def test_transcription_failure_is_reported_and_job_kept(env):
    def boom(_):
        raise RuntimeError("modelo roto")

    env["transcriber"].transcribe = boom
    job_id, _ = env["new_job"]()
    reply = env["service"].process(job_id)
    assert "no he podido transcribir" in reply.lower()
    assert env["store"].unfinished_jobs() == [job_id]


def test_process_unknown_job_is_harmless(env):
    assert env["service"].process(999) == ""


# --- Fallos y reintentos (criterio #8) ---


def test_drive_failure_warns_and_retry_delivers_once(env):
    env["archive"].fail = True
    job_id, audio = env["new_job"]()
    reply = env["service"].process(job_id)
    assert "drive" in reply.lower() and "reintentar" in reply.lower()
    assert "hola, esto es una prueba" in reply  # el texto no se pierde
    assert env["mailer"].sent != []  # el correo sí se envió
    assert audio.exists()

    env["archive"].fail = False
    notices = env["service"].retry_pending()
    assert len(notices) == 1 and notices[0][0] == 10
    assert "entregad" in notices[0][1].lower()
    assert len(env["archive"].saved) == 1
    assert len(env["mailer"].sent) == 1  # sin correo duplicado
    assert env["store"].get_job(job_id) is None
    assert not audio.exists()


def test_mail_failure_warns_and_retry_sends_once(env):
    env["mailer"].fail = True
    job_id, _ = env["new_job"]()
    reply = env["service"].process(job_id)
    assert "correo" in reply.lower()
    assert len(env["archive"].saved) == 1

    env["mailer"].fail = False
    env["service"].retry_pending()
    assert len(env["archive"].saved) == 1  # sin duplicar en Drive
    assert len(env["mailer"].sent) == 1


def test_retry_while_still_failing_is_silent(env):
    env["mailer"].fail = True
    job_id, _ = env["new_job"]()
    env["service"].process(job_id)
    assert env["service"].retry_pending() == []
    assert env["store"].pending_deliveries() == [job_id]


def test_unfinished_jobs_are_reported_for_restart(env):
    job_id, _ = env["new_job"]()
    assert env["service"].unfinished_jobs() == [job_id]


def test_owner_is_notified_only_the_first_time(env):
    service = env["service"]
    _, first = service.refusal(2, "Luis")
    reply, second = service.refusal(2, "Luis")
    assert first and second is None
    assert "no tienes acceso" in reply.lower()


def test_retry_during_delivery_does_not_duplicate(env):
    import threading

    service, archive = env["service"], env["archive"]
    results = {}
    original_save = archive.save

    def slow_save(*args):
        # Mientras se guarda, salta el reintento en otro hilo (como en el bot real).
        worker = threading.Thread(target=lambda: results.update(r=service.retry_pending()))
        worker.start()
        worker.join(timeout=0.2)
        results["thread"] = worker
        return original_save(*args)

    archive.save = slow_save
    job_id, _ = env["new_job"]()
    service.process(job_id)
    results["thread"].join(timeout=2)
    assert len(env["archive"].saved) == 1
    assert len(env["mailer"].sent) == 1
    assert results["r"] == []
