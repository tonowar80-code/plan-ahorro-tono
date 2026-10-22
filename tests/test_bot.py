from types import SimpleNamespace as NS

from notas_voz.bot import AudioInfo, classify, display_name
from notas_voz.core import receipt_message


def msg(**kwargs):
    base = dict(voice=None, audio=None, document=None)
    base.update(kwargs)
    return NS(**base)


def test_voice_note_is_audio():
    info = classify(msg(voice=NS(file_id="v1", file_size=1000, mime_type="audio/ogg", duration=5)))
    assert info == AudioInfo("v1", 1000, "audio/ogg", 5, ".ogg")


def test_audio_file_is_audio():
    audio = NS(file_id="a1", file_size=9, mime_type="audio/mpeg", duration=90, file_name="r.mp3")
    assert classify(msg(audio=audio)) == AudioInfo("a1", 9, "audio/mpeg", 90, ".mp3")


def test_audio_sent_as_document_is_audio():
    doc = NS(file_id="d1", file_size=9, mime_type="audio/x-m4a", file_name="reunion.m4a")
    assert classify(msg(document=doc)) == AudioInfo("d1", 9, "audio/x-m4a", None, ".m4a")


def test_other_documents_and_text_are_not_audio():
    pdf = NS(file_id="d2", file_size=9, mime_type="application/pdf", file_name="x.pdf")
    assert classify(msg(document=pdf)) is None
    assert classify(msg(text="hola")) is None


def test_display_name():
    assert display_name(NS(full_name="Ana Pérez", username="ana")) == "Ana Pérez"
    assert display_name(NS(full_name="", username="ana")) == "ana"
    assert display_name(NS(full_name="", username=None, id=5)) == "Persona 5"


def test_receipt_warns_for_long_audio():
    assert "recibido" in receipt_message(10).lower()
    assert "tardar" not in receipt_message(10).lower()
    assert "tardar" in receipt_message(300).lower()
    assert "tardar" in receipt_message(None).lower()
