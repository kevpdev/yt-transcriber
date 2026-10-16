"""The response shapes the API publishes in /openapi.json.

They describe what the routes return, they never build it: the routes are declared with
`responses=` and not `response_model=`, so no body is filtered or re-serialized.
`tests/test_contract.py` validates the real bodies against them, which keeps them true.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Stage = Literal["queued", "downloading", "transcribing", "extracting", "done", "error"]
State = Literal["done", "error"]
Level = Literal["text", "frames"]


class Shape(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Detail(Shape):
    detail: str = Field(description="Message in French for the end user, never a stack trace.")


class RequestError(Shape):
    detail: str | list[dict[str, Any]] = Field(
        description="French message for an invalid URL or level. A body that is not the "
        "expected JSON gets the list of errors of the validation library instead."
    )


class JobCreated(Shape):
    id: str


class JobCancel(Shape):
    id: str = Field(description="The job whose stop was requested, poll it for the final state.")


class TimedSegment(Shape):
    start: float = Field(description="Seconds from the start of the video.")
    end: float = Field(description="Seconds from the start of the video.")
    text: str


class JobView(Shape):
    id: str
    stage: Stage = Field(description="`extracting` only exists at level `frames`.")
    progress: float = Field(
        ge=0, le=1, description="Share of the transcription done, no percentage while extracting."
    )
    text: str = Field(description="Empty until the job is `done`.")
    segments: list[TimedSegment] = Field(description="Empty until the job is `done`.")
    error: str = Field(description="French message, empty unless the job is in `error`.")
    title: str | None = Field(description="Null until the download step knows the video.")
    channel: str | None = Field(description="Null until the download step knows the video.")
    duration: float | None = Field(description="Seconds, null until the download step knows it.")


class Hotwords(Shape):
    default: str = Field(description="The hotwords used when a job sends none (`HOTWORDS`).")


class RunSummary(Shape):
    id: str
    video_id: str
    url: str
    title: str | None
    channel: str | None
    video_duration: float | None = Field(description="Seconds.")
    state: State
    level: Level
    language: str | None
    word_count: int | None
    started_at: str = Field(description="ISO 8601 time, in UTC.")
    total_s: float | None


class RunList(Shape):
    runs: list[RunSummary] = Field(description="Newest first.")
    total: int = Field(description="Number of runs in the database, all states.")
    limit: int
    offset: int


class FrameOut(Shape):
    position: int
    time: float = Field(description="Seconds from the start of the video.")
    path: str = Field(description="Relative to the folder of the database.")
    url: str = Field(description="Relative route that serves the image.")


class Run(Shape):
    id: str
    video_id: str
    url: str
    title: str | None
    channel: str | None
    video_duration: float | None = Field(description="Seconds.")
    description: str | None = Field(
        description="Video description as YouTube shows it, "
        "null for a run recorded before it was stored."
    )
    state: State
    error: str | None
    text: str | None
    word_count: int | None
    char_count: int | None
    language: str | None
    language_probability: float | None
    started_at: str = Field(description="ISO 8601 time, in UTC.")
    download_s: float | None
    transcribe_s: float | None
    total_s: float | None
    speed_ratio: float | None = Field(description="Video duration over transcription time.")
    level: Level
    settings: dict[str, Any] | None = Field(description="Whisper settings used for the run.")
    machine: dict[str, Any] | None = Field(description="Hardware and system of the host.")
    versions: dict[str, Any] | None = Field(description="Versions of the main packages.")
    segments: list[TimedSegment] = Field(description="Empty unless the run is `done`.")
    frames: list[FrameOut] = Field(description="Empty without slide capture.")


TEXT: dict[str, Any] = {"type": "string"}
BINARY: dict[str, Any] = {"type": "string", "format": "binary"}

# `GET /runs` reads them itself to answer in French, so FastAPI cannot infer them.
PAGINATION: list[dict[str, Any]] = [
    {
        "name": "limit",
        "in": "query",
        "required": False,
        "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
    },
    {
        "name": "offset",
        "in": "query",
        "required": False,
        "schema": {"type": "integer", "minimum": 0, "default": 0},
    },
]


def error(description: str, model: type[BaseModel] = Detail) -> dict[str, Any]:
    """One entry of a route's `responses=`, for a `{"detail"}` error."""
    return {"model": model, "description": description}


def content(media_type: str, schema: dict[str, Any], description: str) -> dict[str, Any]:
    """One entry of a route's `responses=`, for a body that is not JSON."""
    return {"content": {media_type: {"schema": schema}}, "description": description}
