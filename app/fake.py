"""Transcripteur et téléchargeur factices, activés par YT_FAKE=1, sans GPU ni réseau."""

import time
from collections.abc import Callable
from pathlib import Path

FAKE_TEXT = (
    "Ceci est une transcription factice. "
    "Elle sert aux tests de bout en bout de la page, sans GPU. "
    "Le texte est assez long pour vérifier la copie en entier."
)
# Assez long pour recharger la page et couper le réseau pendant le job.
FAKE_DURATION = 10.0
_STEPS = 10


def fake_download(url: str, dest_dir: Path) -> Path:
    path = dest_dir / "audio.webm"
    path.touch()
    return path


class FakeTranscriber:
    model = object()  # non None : le lifespan n'appelle pas load()

    def run(self, audio: Path, on_progress: Callable[[float], None]) -> str:
        for step in range(1, _STEPS + 1):
            time.sleep(FAKE_DURATION / _STEPS)
            on_progress(step / _STEPS)
        return FAKE_TEXT
