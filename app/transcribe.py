import os
from pathlib import Path
from typing import Callable

MODEL = "large-v3-turbo"
DEFAULT_HOTWORDS = "Claude Code, Claude, Anthropic, MCP"


def hotwords() -> str:
    return os.environ.get("HOTWORDS", DEFAULT_HOTWORDS)


class Transcriber:
    def __init__(self) -> None:
        self.model = None

    def load(self) -> None:
        from faster_whisper import WhisperModel

        self.model = WhisperModel(MODEL, device="cuda", compute_type="float16")

    def run(self, audio: Path, on_progress: Callable[[float], None]) -> str:
        segments, info = self.model.transcribe(
            str(audio),
            language=None,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
            hotwords=hotwords(),
        )
        parts = []
        for segment in segments:
            parts.append(segment.text.strip())
            if info.duration:
                on_progress(min(segment.end / info.duration, 1.0))
        return " ".join(p for p in parts if p)
