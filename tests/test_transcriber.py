import ast
from pathlib import Path
from types import SimpleNamespace

from notas_voz import transcriber as transcriber_module
from notas_voz.transcriber import WhisperTranscriber


class FakeModel:
    def __init__(self):
        self.calls = []

    def transcribe(self, path, **kwargs):
        self.calls.append((path, kwargs))
        segments = iter([SimpleNamespace(text=" Hola"), SimpleNamespace(text=" qué tal. ")])
        return segments, SimpleNamespace(language="es")


def test_transcribes_locally_in_spanish():
    model = FakeModel()
    created = []

    def factory(size):
        created.append(size)
        return model

    t = WhisperTranscriber("small", model_factory=factory)
    assert created == []  # el modelo se carga solo cuando hace falta
    assert t.transcribe(Path("a.ogg")) == "Hola qué tal."
    t.transcribe(Path("b.ogg"))
    assert created == ["small"]  # y una sola vez
    path, kwargs = model.calls[0]
    assert path == "a.ogg"
    assert kwargs["language"] == "es"
    assert kwargs["vad_filter"] is True


def test_transcriber_module_uses_no_network_client():
    source = Path(transcriber_module.__file__).read_text()
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"requests", "httpx", "urllib", "openai", "google", "googleapiclient", "telegram"}
    assert imported.isdisjoint(forbidden)
