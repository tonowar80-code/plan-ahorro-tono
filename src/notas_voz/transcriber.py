"""Transcripción local con faster-whisper: el audio no sale del ordenador."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _load_whisper(size: str) -> Any:
    from faster_whisper import WhisperModel

    # int8 en CPU: funciona en cualquier ordenador sin tarjeta gráfica.
    return WhisperModel(size, device="cpu", compute_type="int8")


class WhisperTranscriber:
    def __init__(
        self, model_size: str = "small", model_factory: Callable[[str], Any] = _load_whisper
    ) -> None:
        self._size = model_size
        self._factory = model_factory
        self._model = None
        self._lock = threading.Lock()

    def transcribe(self, audio_path: Path) -> str:
        with self._lock:
            if self._model is None:
                self._model = self._factory(self._size)
            segments, _info = self._model.transcribe(
                str(audio_path), language="es", vad_filter=True
            )
            return "".join(segment.text for segment in segments).strip()
