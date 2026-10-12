"""Fake transcriber and downloader, enabled by YT_FAKE=1, with no GPU and no network."""

import time
from collections.abc import Callable
from pathlib import Path

from .audio import Download
from .transcribe import Segment, Transcript

FAKE_TEXT = (
    "Ceci est une transcription factice. "
    "Elle sert aux tests de bout en bout de la page, sans GPU. "
    "Le texte est assez long pour vérifier la copie en entier."
)
# Long enough to reload the page and cut the network during the job.
FAKE_DURATION = 10.0
_STEPS = 10
_SENTENCES = [s for s in FAKE_TEXT.split(". ")]


def fake_download(url: str, dest_dir: Path) -> Download:
    path = dest_dir / "audio.webm"
    path.touch()
    return Download(
        path=path, title="Vidéo factice", channel="Chaîne factice", duration=FAKE_DURATION
    )


def fake_segments() -> list[Segment]:
    """One segment per sentence of FAKE_TEXT, spread evenly over FAKE_DURATION."""
    last = len(_SENTENCES) - 1
    step = FAKE_DURATION / len(_SENTENCES)
    return [
        Segment(
            start=round(i * step, 3),
            end=round((i + 1) * step, 3) if i < last else FAKE_DURATION,
            text=sentence if i == last else sentence + ".",
        )
        for i, sentence in enumerate(_SENTENCES)
    ]


class FakeTranscriber:
    model = object()  # not None: the lifespan does not call load()

    def run(self, audio: Path, on_progress: Callable[[float], None]) -> Transcript:
        for step in range(1, _STEPS + 1):
            time.sleep(FAKE_DURATION / _STEPS)
            on_progress(step / _STEPS)
        return Transcript(
            text=FAKE_TEXT,
            segments=fake_segments(),
            language="fr",
            language_probability=1.0,
        )
