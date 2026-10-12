"""Fake transcriber and downloader, enabled by YT_FAKE=1, with no GPU and no network."""

import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from .audio import Download
from .frames import write_webp
from .runs import Frame
from .transcribe import Segment, Transcript

FAKE_TEXT = (
    "Ceci est une transcription factice. "
    "Elle sert aux tests de bout en bout de la page, sans GPU. "
    "Le texte est assez long pour vérifier la copie en entier."
)
# Long enough to reload the page and cut the network during the job.
FAKE_DURATION = 10.0
# Long enough for the page, which polls every 2 s, to show the extracting stage.
FAKE_CAPTURE_DELAY = 3.0
_STEPS = 10
_SENTENCES = FAKE_TEXT.split(". ")


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


def fake_capture(url: str, work_dir: Path, out_dir: Path) -> list[Frame]:
    """Two synthetic WebP images, one per half of the fake video."""
    time.sleep(FAKE_CAPTURE_DELAY)
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for position, shade in enumerate((60, 200)):
        path = out_dir / f"{position:04d}.webp"
        write_webp(np.full((72, 128, 3), shade, dtype=np.uint8), path)
        frames.append(Frame(position=position, time=position * FAKE_DURATION / 2, path=path))
    return frames


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
