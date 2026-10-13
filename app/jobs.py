import threading
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from .transcribe import Segment

QUEUED, DOWNLOADING, TRANSCRIBING, EXTRACTING, DONE, ERROR = (
    "queued",
    "downloading",
    "transcribing",
    "extracting",
    "done",
    "error",
)
_FINISHED = {DONE, ERROR}
_KEEP = 20
# Measured in data/runs.db: a text run of a 1 847 s video took 48 s (about 19 times margin),
# a frames run of a 785 s video took 130 s, 98 s of it the capture (the 56 min reference video
# extrapolates to about 510 s, a margin of about 1.8 times).
JOB_TIMEOUT_S = 900.0


class JobBusy(Exception):
    """A job is already running, there is only one GPU."""


class JobStopped(Exception):
    """The job was cancelled or ran past its time limit, the message is meant for the end user."""

    def __init__(self, message: str, cancelled: bool = False) -> None:
        super().__init__(message)
        self.cancelled = cancelled


@dataclass
class Job:
    id: str
    stage: str = QUEUED
    progress: float = 0.0
    text: str = ""
    segments: list[Segment] = field(default_factory=list)
    error: str = ""
    frames: bool = False
    timeout: float = JOB_TIMEOUT_S
    cancel: threading.Event = field(default_factory=threading.Event)
    started: float = field(default_factory=time.monotonic)

    def check(self) -> None:
        """Called at the checkpoints of every long step: stops the job when it must end."""
        if self.cancel.is_set():
            raise JobStopped("Transcription annulée.", cancelled=True)
        if time.monotonic() - self.started > self.timeout:
            raise JobStopped(
                f"La transcription a dépassé la limite de {round(self.timeout / 60)} minutes."
            )

    def view(self) -> dict:
        return {
            "id": self.id,
            "stage": self.stage,
            "progress": round(self.progress, 4),
            "text": self.text,
            "segments": [{"start": s.start, "end": s.end, "text": s.text} for s in self.segments],
            "error": self.error,
        }


class JobStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}
        self._active: Job | None = None

    def start(self, frames: bool = False, timeout: float = JOB_TIMEOUT_S) -> Job:
        with self._lock:
            if self._active and self._active.stage not in _FINISHED:
                raise JobBusy("Une transcription est déjà en cours, attends qu'elle se termine.")
            job = Job(id=uuid.uuid4().hex, frames=frames, timeout=timeout)
            self._active = job
            self._jobs[job.id] = job
            while len(self._jobs) > _KEEP:
                self._jobs.pop(next(iter(self._jobs)))
            return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool | None:
        """None for an unknown job, False for a finished one, True once the stop is requested."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.stage in _FINISHED:
                return False
            job.cancel.set()
            return True

    def set_stage(self, job: Job, stage: str, progress: float = 0.0) -> None:
        with self._lock:
            job.stage = stage
            job.progress = progress

    def set_progress(self, job: Job, progress: float) -> None:
        job.progress = progress

    def finish(self, job: Job, text: str, segments: Sequence[Segment]) -> None:
        with self._lock:
            job.text = text
            job.segments = list(segments)
            job.progress = 1.0
            job.stage = DONE

    def fail(self, job: Job, message: str) -> None:
        with self._lock:
            job.error = message
            job.stage = ERROR
