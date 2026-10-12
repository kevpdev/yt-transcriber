import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

MODEL = "large-v3-turbo"
COMPUTE_TYPE = "float16"
BEAM_SIZE = 5
VAD_FILTER = True
CONDITION_ON_PREVIOUS_TEXT = False
DEFAULT_HOTWORDS = "Claude Code, Claude, Anthropic, MCP"


def hotwords() -> str:
    return os.environ.get("HOTWORDS", DEFAULT_HOTWORDS)


def settings() -> dict:
    return {
        "model": MODEL,
        "compute_type": COMPUTE_TYPE,
        "beam_size": BEAM_SIZE,
        "vad_filter": VAD_FILTER,
        "condition_on_previous_text": CONDITION_ON_PREVIOUS_TEXT,
        "hotwords": hotwords(),
    }


@dataclass
class Transcript:
    text: str
    language: str | None = None
    language_probability: float | None = None


class Transcriber:
    def __init__(self) -> None:
        self.model = None

    def load(self) -> None:
        from faster_whisper import WhisperModel

        self.model = WhisperModel(MODEL, device="cuda", compute_type=COMPUTE_TYPE)

    def run(self, audio: Path, on_progress: Callable[[float], None]) -> Transcript:
        if self.model is None:
            raise RuntimeError("The model is not loaded, call load() first.")
        segments, info = self.model.transcribe(
            str(audio),
            language=None,
            beam_size=BEAM_SIZE,
            vad_filter=VAD_FILTER,
            condition_on_previous_text=CONDITION_ON_PREVIOUS_TEXT,
            hotwords=hotwords(),
        )
        parts = []
        for segment in segments:
            parts.append(segment.text.strip())
            if info.duration:
                on_progress(min(segment.end / info.duration, 1.0))
        return Transcript(
            text=" ".join(p for p in parts if p),
            language=info.language,
            language_probability=info.language_probability,
        )
