import os
from collections.abc import Callable
from dataclasses import dataclass, field
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
class Segment:
    start: float
    end: float
    text: str


@dataclass
class Transcript:
    text: str
    segments: list[Segment] = field(default_factory=list)
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
        kept = []
        progress = 0.0
        for segment in segments:
            text = segment.text.strip()
            if text:
                kept.append(Segment(start=segment.start, end=segment.end, text=text))
            # Called for every segment, the caller uses it as a checkpoint to stop the job.
            if info.duration:
                progress = min(segment.end / info.duration, 1.0)
            on_progress(progress)
        return Transcript(
            text=" ".join(s.text for s in kept),
            segments=kept,
            language=info.language,
            language_probability=info.language_probability,
        )
